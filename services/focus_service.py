"""
Сервис управления фокус-сессиями (Pomodoro).
Независимая от Telegram бизнес-логика для REST API.
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid
import logging

from database.focus_db import FocusDB

logger = logging.getLogger(__name__)


class SessionStatus(Enum):
    """Статусы фокус-сессии"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    BREAK = "break"


class SessionType(Enum):
    """Типы сессий"""
    WORK = "work"
    SHORT_BREAK = "short_break"
    LONG_BREAK = "long_break"


class FocusService:
    """
    Сервис управления фокус-сессиями.
    Вся бизнес-логика без привязки к Telegram.
    """
    
    def __init__(self, focus_db, scheduler, bot=None):
        """
        Args:
            focus_db: Экземпляр FocusDB для работы с БД
            scheduler: Экземпляр FocusScheduler для управления таймерами
            bot: Экземпляр Bot для обновления UI (опционально)
        """
        self.db = focus_db
        self.scheduler = scheduler
        self.bot = bot  # ДОБАВЛЕНО: Сохраняем экземпляр бота для обновления UI
        
    async def start_session(
        self,
        user_id: str,
        duration_minutes: Optional[int] = None,
        session_type: SessionType = SessionType.WORK,
        auto_start_break: bool = True
    ) -> Dict[str, Any]:
        """
        Запускает новую фокус-сессию.
        
        Args:
            user_id: ID пользователя
            duration_minutes: Длительность в минутах (если None - из настроек)
            session_type: Тип сессии (работа/перерыв)
            auto_start_break: Автоматически начинать перерыв после работы
            
        Returns:
            Данные созданной сессии
            
        Raises:
            ValueError: Если у пользователя уже есть активная сессия
        """
        # Проверяем активную сессию
        active_session = await self.db.get_active_session(user_id)
        if active_session:
            raise ValueError("У вас уже есть активная сессия")
        
        # Получаем настройки если не задана длительность
        if duration_minutes is None:
            settings = await self.db.get_user_settings(user_id)
            if session_type == SessionType.WORK:
                duration_minutes = settings['work_duration']
            elif session_type == SessionType.SHORT_BREAK:
                duration_minutes = settings['short_break_duration']
            else:
                duration_minutes = settings['long_break_duration']
        
        # Создаем сессию
        session_id = str(uuid.uuid4())
        session_data = {
            'id': session_id,
            'user_id': user_id,
            'type': session_type.value,
            'status': SessionStatus.ACTIVE.value,
            'duration_minutes': duration_minutes,
            'completed_minutes': 0,
            'started_at': datetime.now(timezone.utc),
            'auto_start_break': auto_start_break
        }
        
        # Сохраняем в БД
        await self.db.create_session(session_data)
        
        # Запускаем таймер
        # ИЗМЕНЕНО: Исправлено timer_id на session_id для соответствия FocusScheduler
        timer_started = await self.scheduler.start_timer(
            session_id=session_id,
            user_id=user_id,
            duration_minutes=duration_minutes,
            on_complete=self._on_session_complete,
            on_tick=self._on_session_tick
        )
        
        logger.info(
            f"Запущена {session_type.value} сессия {session_id} "
            f"для пользователя {user_id} на {duration_minutes} минут"
        )
        
        return session_data
    
    async def pause_session(self, user_id: str) -> Dict[str, Any]:
        """
        Ставит сессию на паузу.
        
        Returns:
            Обновленные данные сессии
            
        Raises:
            ValueError: Если нет активной сессии или она уже на паузе
        """
        session = await self.db.get_active_session(user_id)
        
        if not session:
            raise ValueError("У вас нет активной сессии")
        
        if session['status'] == SessionStatus.PAUSED.value:
            raise ValueError("Сессия уже на паузе")
        
        # Останавливаем таймер и получаем оставшееся время
        remaining = await self.scheduler.pause_timer(session['id'])
        
        # Обновляем сессию
        completed = session['duration_minutes'] - remaining if remaining else 0
        await self.db.update_session(
            session['id'],
            {
                'status': SessionStatus.PAUSED.value,
                'completed_minutes': completed,
                'paused_at': datetime.now(timezone.utc)
            }
        )
        
        session['status'] = SessionStatus.PAUSED.value
        session['completed_minutes'] = completed
        
        logger.info(f"Сессия {session['id']} поставлена на паузу")
        
        return session
    
    async def resume_session(self, user_id: str) -> Dict[str, Any]:
        """
        Возобновляет сессию после паузы.
        
        Returns:
            Обновленные данные сессии
            
        Raises:
            ValueError: Если нет активной сессии или она не на паузе
        """
        session = await self.db.get_active_session(user_id)
        
        if not session:
            raise ValueError("У вас нет активной сессии")
        
        if session['status'] != SessionStatus.PAUSED.value:
            raise ValueError("Сессия не на паузе")
        
        # Вычисляем оставшееся время
        remaining = session['duration_minutes'] - session['completed_minutes']
        
        # Возобновляем таймер
        # ИЗМЕНЕНО: Исправлено timer_id на session_id для соответствия FocusScheduler
        await self.scheduler.resume_timer(
            session_id=session['id'],
            user_id=user_id,
            remaining_minutes=remaining,
            on_complete=self._on_session_complete,
            on_tick=self._on_session_tick
        )
        
        # Обновляем статус
        await self.db.update_session(
            session['id'],
            {
                'status': SessionStatus.ACTIVE.value,
                'resumed_at': datetime.now(timezone.utc)
            }
        )
        
        session['status'] = SessionStatus.ACTIVE.value
        
        logger.info(f"Сессия {session['id']} возобновлена")
        
        return session
    
    async def stop_session(
        self,
        user_id: str,
        completed: bool = False
    ) -> Tuple[int, bool]:
        """
        Останавливает текущую сессию.
        
        Args:
            user_id: ID пользователя
            completed: True если сессия завершена, False если отменена
            
        Returns:
            Кортеж (количество завершенных минут, была ли завершена)
            
        Raises:
            ValueError: Если нет активной сессии
        """
        session = await self.db.get_active_session(user_id)
        
        if not session:
            raise ValueError("У вас нет активной сессии")
        
        # Останавливаем таймер
        remaining = await self.scheduler.stop_timer(session['id'])
        
        # Вычисляем завершенные минуты
        if remaining is not None:
            completed_minutes = session['duration_minutes'] - remaining
        else:
            completed_minutes = session.get('completed_minutes', 0)
        
        # Определяем статус
        if completed or completed_minutes >= session['duration_minutes']:
            status = SessionStatus.COMPLETED.value
            is_completed = True
        else:
            status = SessionStatus.CANCELLED.value
            is_completed = False
        
        # Обновляем сессию
        await self.db.update_session(
            session['id'],
            {
                'status': status,
                'completed_minutes': completed_minutes,
                'ended_at': datetime.now(timezone.utc)
            }
        )
        
        # Обновляем статистику
        if is_completed and session['type'] == SessionType.WORK.value:
            await self.db.increment_stats(user_id, completed_minutes)
        
        logger.info(
            f"Сессия {session['id']} остановлена. "
            f"Статус: {status}, завершено минут: {completed_minutes}"
        )
        
        # Автоматический запуск перерыва если нужно
        if (is_completed and 
            session['type'] == SessionType.WORK.value and
            session.get('auto_start_break', True)):
            try:
                # Определяем тип перерыва (короткий или длинный)
                sessions_count = await self._get_today_sessions_count(user_id)
                if sessions_count % 4 == 0:
                    break_type = SessionType.LONG_BREAK
                else:
                    break_type = SessionType.SHORT_BREAK
                
                # Запускаем перерыв
                await self.start_session(
                    user_id,
                    session_type=break_type,
                    auto_start_break=False
                )
                logger.info(f"Автоматически запущен {break_type.value}")
                
            except Exception as e:
                logger.error(f"Ошибка автозапуска перерыва: {e}")
        
        return completed_minutes, is_completed
    
    async def get_session_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает информацию об активной сессии.
        
        Returns:
            Данные сессии с remaining_minutes или None
        """
        session = await self.db.get_active_session(user_id)
        if not session:
            return None
        
        # Добавляем информацию о времени
        if session['status'] == SessionStatus.ACTIVE.value:
            remaining = self.scheduler.get_remaining_time(session['id'])
            session['remaining_minutes'] = remaining
            session['elapsed_minutes'] = (
                session['duration_minutes'] - remaining
                if remaining is not None 
                else session.get('completed_minutes', 0)
            )
        else:
            session['remaining_minutes'] = (
                session['duration_minutes'] - session.get('completed_minutes', 0)
            )
            session['elapsed_minutes'] = session.get('completed_minutes', 0)
        
        return session
    
    async def update_settings(
        self,
        user_id: str,
        settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Обновляет настройки пользователя.
        
        Args:
            user_id: ID пользователя
            settings: Словарь с настройками
            
        Returns:
            Обновленные настройки
        """
        # Валидация настроек
        valid_settings = {}
        
        # Длительности
        if 'work_duration' in settings:
            duration = int(settings['work_duration'])
            if 5 <= duration <= 120:
                valid_settings['work_duration'] = duration
        
        if 'short_break_duration' in settings:
            duration = int(settings['short_break_duration'])
            if 3 <= duration <= 30:
                valid_settings['short_break_duration'] = duration
        
        if 'long_break_duration' in settings:
            duration = int(settings['long_break_duration'])
            if 10 <= duration <= 60:
                valid_settings['long_break_duration'] = duration
        
        # Другие настройки
        if 'sound_enabled' in settings:
            valid_settings['sound_enabled'] = bool(settings['sound_enabled'])
        
        if 'auto_start_break' in settings:
            valid_settings['auto_start_break'] = bool(settings['auto_start_break'])
        
        # notifications removed - убрана проверка notifications_enabled
        
        # Обновляем в БД
        updated = await self.db.update_user_settings(user_id, valid_settings)
        
        logger.info(f"Обновлены настройки пользователя {user_id}: {valid_settings}")
        return updated
    
    async def get_statistics(
        self,
        user_id: str,
        period: str = "today"
    ) -> Dict[str, Any]:
        """
        Получает статистику пользователя.
        
        Args:
            user_id: ID пользователя
            period: Период (today, week, month, all)
            
        Returns:
            Словарь со статистикой
        """
        if period == "today":
            stats = await self.db.get_today_stats(user_id)
        elif period == "week":
            stats = await self.db.get_week_stats(user_id)
        elif period == "month":
            stats = await self.db.get_month_stats(user_id)
        else:
            stats = await self.db.get_all_time_stats(user_id)
        
        # Добавляем дополнительную информацию
        user_stats = await self.db.get_user_stats(user_id)
        stats.update({
            'current_streak': user_stats.get('current_streak', 0),
            'best_streak': user_stats.get('best_streak', 0)
        })
        
        return stats
    
    async def get_stats(self, user_id: str, period: str = "today") -> Dict[str, Any]:
        """Алиас для get_statistics для обратной совместимости"""
        return await self.get_statistics(user_id, period)
    
    async def restore_active_sessions(self) -> int:
        """
        Восстанавливает активные сессии после перезапуска.
        ИЗМЕНЕНО: Улучшенное восстановление с обработкой паузы и сохранением прогресса
        
        Returns:
            Количество восстановленных сессий
        """
        sessions = await self.db.get_all_active_sessions()
        restored_count = 0
        
        for session in sessions:
            try:
                # Восстанавливаем активные сессии
                if session['status'] == SessionStatus.ACTIVE.value:
                    # Вычисляем оставшееся время с учетом прошедшего
                    elapsed = (
                        datetime.now(timezone.utc) - session['started_at']
                    ).total_seconds() / 60
                    
                    remaining = session['duration_minutes'] - elapsed
                    
                    if remaining > 0:
                        # Восстанавливаем таймер
                        await self.scheduler.start_timer(
                            session_id=session['id'],
                            user_id=session['user_id'],
                            duration_minutes=int(remaining),
                            on_complete=self._on_session_complete,
                            on_tick=self._on_session_tick
                        )
                        restored_count += 1
                        logger.info(
                            f"Восстановлена активная сессия {session['id']} "
                            f"для пользователя {session['user_id']}, "
                            f"осталось {int(remaining)} минут"
                        )
                    else:
                        # Сессия истекла, завершаем её
                        await self.stop_session(session['user_id'], completed=True)
                        logger.info(f"Завершена истекшая сессия {session['id']}")
                
                # Восстанавливаем паузы
                elif session['status'] == SessionStatus.PAUSED.value:
                    # Сохраняем состояние паузы для возможности продолжения
                    logger.info(
                        f"Найдена сессия на паузе {session['id']} "
                        f"для пользователя {session['user_id']}, "
                        f"прошло {session.get('completed_minutes', 0)} минут"
                    )
                    # Паузу не нужно восстанавливать в таймере, 
                    # она будет доступна через интерфейс
                    restored_count += 1
                    
            except Exception as e:
                logger.error(
                    f"Ошибка восстановления сессии {session['id']}: {e}",
                    exc_info=True
                )
        
        logger.info(f"Восстановлено {restored_count} сессий (активных и на паузе)")
        return restored_count
    
    # === Приватные методы ===
    
    async def _on_session_complete(
        self,
        session_id: str,
        user_id: str,
        completed_minutes: int
    ):
        """Callback при завершении таймера сессии"""
        try:
            await self.stop_session(user_id, completed=True)
            logger.info(f"Сессия {session_id} автоматически завершена")
            
            # ДОБАВЛЕНО: Обновляем UI при завершении сессии
            if self.bot:
                try:
                    from handlers.focus import session_messages, create_progress_bar
                    from keyboards.focus import get_focus_menu_keyboard
                    
                    if session_id in session_messages:
                        msg_info = session_messages[session_id]
                        
                        # Создаем полный прогресс-бар
                        progress_bar = create_progress_bar(completed_minutes, completed_minutes)
                        
                        text = (
                            f"✅ <b>Сессия завершена!</b>\n\n"
                            f"{progress_bar}\n"
                            f"Отличная работа! Ты продержался {completed_minutes} минут.\n"
                            f"Время сделать перерыв 😊"
                        )
                        
                        await self.bot.edit_message_text(
                            text=text,
                            chat_id=msg_info['chat_id'],
                            message_id=msg_info['message_id'],
                            reply_markup=get_focus_menu_keyboard(),
                            parse_mode="HTML"
                        )
                        
                        # Удаляем связь сессии с сообщением
                        del session_messages[session_id]
                        
                except Exception as e:
                    logger.error(f"Ошибка обновления UI при завершении сессии {session_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Ошибка при завершении сессии {session_id}: {e}")
    
    async def _on_session_tick(
        self,
        session_id: str,
        user_id: str,
        remaining_minutes: int
    ):
        """Callback при тике таймера (каждую минуту)"""
        logger.debug(
            f"Тик сессии {session_id}: осталось {remaining_minutes} минут"
        )
        
        # ДОБАВЛЕНО: Обновляем UI с прогрессом если есть бот
        if self.bot:
            try:
                from handlers.focus import update_session_progress
                await update_session_progress(self.bot, session_id, remaining_minutes)
            except ImportError:
                logger.warning("Не удалось импортировать update_session_progress")
            except Exception as e:
                logger.error(f"Ошибка обновления UI для сессии {session_id}: {e}")
    
    async def _update_user_stats(
        self,
        user_id: str,
        completed_minutes: int
    ):
        """Обновляет статистику пользователя"""
        await self.db.increment_stats(user_id, completed_minutes)
        logger.info(
            f"Обновлена статистика пользователя {user_id}: "
            f"+{completed_minutes} минут"
        )
    
    async def _get_today_sessions_count(self, user_id: str) -> int:
        """Получает количество завершенных сессий за сегодня"""
        stats = await self.db.get_today_stats(user_id)
        return stats.get('completed_sessions', 0)