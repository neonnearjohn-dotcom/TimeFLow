"""
Планировщик и менеджер таймеров для фокус-сессий.
Управляет асинхронными задачами без блокировки event loop.
"""
import asyncio
from typing import Dict, Callable, Optional, Any, Set, List
from datetime import datetime, timezone, timedelta
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TimerState(Enum):
    """Состояния таймера"""
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


@dataclass
class TimerInfo:
    """Информация о таймере"""
    session_id: str
    user_id: str
    total_minutes: int
    elapsed_minutes: int
    state: TimerState
    task: Optional[asyncio.Task] = None
    pause_time: Optional[datetime] = None
    tick_interval: int = 5  # секунд между тиками


class FocusScheduler:
    """
    Планировщик для управления таймерами фокус-сессий.
    Использует asyncio для неблокирующей работы.
    """
    
    def __init__(self, tick_interval: int = 5):
        """
        Args:
            tick_interval: Интервал между тиками в секундах (1-60)
        """
        self.timers: Dict[str, TimerInfo] = {}
        self.default_tick_interval = max(1, min(60, tick_interval))
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Запускает планировщик"""
        if not self._running:
            self._running = True
            self._monitor_task = asyncio.create_task(self._monitor_timers())
            logger.info("Планировщик запущен")
    
    async def stop(self):
        """Останавливает планировщик и все таймеры"""
        self._running = False
        
        # Останавливаем все таймеры
        for timer_id in list(self.timers.keys()):
            await self.stop_timer(timer_id)
        
        # Останавливаем монитор
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Планировщик остановлен")
    
    async def start_timer(
        self,
        session_id: str,
        user_id: str,
        duration_minutes: int,
        on_complete: Callable,
        on_tick: Optional[Callable] = None,
        tick_interval: Optional[int] = None
    ) -> bool:
        """
        Запускает новый таймер для сессии.
        
        Args:
            session_id: ID сессии
            user_id: ID пользователя
            duration_minutes: Длительность в минутах
            on_complete: Callback при завершении (session_id, user_id, completed_minutes)
            on_tick: Callback при тике (session_id, user_id, remaining_minutes)
            tick_interval: Интервал тиков в секундах
            
        Returns:
            True если таймер запущен успешно
        """
        try:
            # Проверяем, нет ли уже таймера
            if session_id in self.timers:
                logger.warning(f"Таймер {session_id} уже существует")
                return False
            
            # Создаем информацию о таймере
            timer_info = TimerInfo(
                session_id=session_id,
                user_id=user_id,
                total_minutes=duration_minutes,
                elapsed_minutes=0,
                state=TimerState.RUNNING,
                tick_interval=tick_interval or self.default_tick_interval
            )
            
            # Создаем задачу таймера
            timer_info.task = asyncio.create_task(
                self._run_timer(timer_info, on_complete, on_tick)
            )
            
            # Сохраняем таймер
            self.timers[session_id] = timer_info
            
            logger.info(
                f"Запущен таймер {session_id} для пользователя {user_id} "
                f"на {duration_minutes} минут"
            )
            return True
            
        except Exception as e:
            logger.error(f"Ошибка запуска таймера {session_id}: {e}")
            return False
    
    async def pause_timer(self, session_id: str) -> Optional[int]:
        """
        Ставит таймер на паузу.
        
        Returns:
            Количество прошедших минут или None
        """
        timer = self.timers.get(session_id)
        if not timer or timer.state != TimerState.RUNNING:
            return None
        
        timer.state = TimerState.PAUSED
        timer.pause_time = datetime.now(timezone.utc)
        
        logger.info(f"Таймер {session_id} поставлен на паузу")
        return timer.elapsed_minutes
    
    async def resume_timer(
        self,
        session_id: str,
        user_id: str,
        remaining_minutes: int,
        on_complete: Callable,
        on_tick: Optional[Callable] = None
    ) -> bool:
        """
        Возобновляет таймер после паузы.
        
        Args:
            session_id: ID сессии
            user_id: ID пользователя  
            remaining_minutes: Оставшееся время в минутах
            on_complete: Callback при завершении
            on_tick: Callback при тике
            
        Returns:
            True если успешно возобновлен
        """
        try:
            # Удаляем старый таймер если есть
            if session_id in self.timers:
                old_timer = self.timers[session_id]
                if old_timer.task and not old_timer.task.done():
                    old_timer.task.cancel()
                del self.timers[session_id]
            
            # Создаем новый таймер с оставшимся временем
            timer_info = TimerInfo(
                session_id=session_id,
                user_id=user_id,
                total_minutes=remaining_minutes,
                elapsed_minutes=0,
                state=TimerState.RUNNING,
                tick_interval=self.default_tick_interval
            )
            
            # Запускаем задачу
            timer_info.task = asyncio.create_task(
                self._run_timer(timer_info, on_complete, on_tick)
            )
            
            self.timers[session_id] = timer_info
            
            logger.info(
                f"Таймер {session_id} возобновлен с {remaining_minutes} минут"
            )
            return True
            
        except Exception as e:
            logger.error(f"Ошибка возобновления таймера {session_id}: {e}")
            return False
    
    async def stop_timer(self, session_id: str) -> Optional[int]:
        """
        Останавливает таймер.
        
        Returns:
            Количество прошедших минут или None
        """
        timer = self.timers.get(session_id)
        if not timer:
            return None
        
        elapsed = timer.elapsed_minutes
        
        # Отменяем задачу
        if timer.task and not timer.task.done():
            timer.task.cancel()
            try:
                await timer.task
            except asyncio.CancelledError:
                pass
        
        # Удаляем таймер
        del self.timers[session_id]
        
        logger.info(f"Таймер {session_id} остановлен, прошло {elapsed} минут")
        return elapsed
    
    def get_remaining_time(self, session_id: str) -> Optional[int]:
        """
        Возвращает оставшееся время в минутах.
        
        Returns:
            Оставшиеся минуты или None
        """
        timer = self.timers.get(session_id)
        if not timer:
            return None
        
        if timer.state == TimerState.RUNNING:
            return max(0, timer.total_minutes - timer.elapsed_minutes)
        elif timer.state == TimerState.PAUSED:
            return timer.total_minutes - timer.elapsed_minutes
        else:
            return 0
    
    def get_timer_state(self, session_id: str) -> Optional[TimerState]:
        """Возвращает состояние таймера"""
        timer = self.timers.get(session_id)
        return timer.state if timer else None
    
    def get_active_timers_count(self) -> int:
        """Возвращает количество активных таймеров"""
        return len([t for t in self.timers.values() 
                   if t.state == TimerState.RUNNING])
    
    def get_active_timers(self) -> List[str]:
        """
        Возвращает список ID активных таймеров
        ДОБАВЛЕНО: Метод для получения списка активных таймеров
        """
        return [session_id for session_id, timer in self.timers.items() 
                if timer.state == TimerState.RUNNING]
    
    async def schedule_task(
        self,
        delay_seconds: int,
        callback: Callable[[], Any]
    ) -> asyncio.Task:
        """
        Планирует выполнение задачи через указанное время.
        
        Args:
            delay_seconds: Задержка в секундах
            callback: Функция для выполнения
            
        Returns:
            Созданная задача
        """
        async def delayed_task():
            await asyncio.sleep(delay_seconds)
            if asyncio.iscoroutinefunction(callback):
                await callback()
            else:
                callback()
        
        task = asyncio.create_task(delayed_task())
        return task
    
    # === Приватные методы ===
    
    async def _run_timer(
        self,
        timer: TimerInfo,
        on_complete: Callable,
        on_tick: Optional[Callable]
    ):
        """Основной цикл таймера"""
        try:
            start_time = datetime.now(timezone.utc)
            last_tick_time = start_time
            
            while timer.elapsed_minutes < timer.total_minutes:
                # Проверяем состояние
                if timer.state == TimerState.STOPPED:
                    break
                
                if timer.state == TimerState.PAUSED:
                    await asyncio.sleep(1)
                    continue
                
                # Ждем интервал тика
                await asyncio.sleep(timer.tick_interval)
                
                # Обновляем время
                now = datetime.now(timezone.utc)
                elapsed_seconds = (now - start_time).total_seconds()
                timer.elapsed_minutes = int(elapsed_seconds / 60)
                
                # Проверяем, нужен ли тик
                if on_tick and (now - last_tick_time).total_seconds() >= 60:
                    remaining = timer.total_minutes - timer.elapsed_minutes
                    
                    # Вызываем callback
                    if asyncio.iscoroutinefunction(on_tick):
                        await on_tick(
                            timer.session_id,
                            timer.user_id,
                            remaining
                        )
                    else:
                        on_tick(
                            timer.session_id,
                            timer.user_id,
                            remaining
                        )
                    
                    last_tick_time = now
                
                # Проверяем завершение
                if timer.elapsed_minutes >= timer.total_minutes:
                    break
            
            # Таймер завершен
            if timer.state == TimerState.RUNNING:
                timer.state = TimerState.STOPPED
                
                # Вызываем callback завершения
                if asyncio.iscoroutinefunction(on_complete):
                    await on_complete(
                        timer.session_id,
                        timer.user_id,
                        timer.total_minutes
                    )
                else:
                    on_complete(
                        timer.session_id,
                        timer.user_id,
                        timer.total_minutes
                    )
                
                # Удаляем таймер
                if timer.session_id in self.timers:
                    del self.timers[timer.session_id]
                
                logger.info(f"Таймер {timer.session_id} завершен")
                
        except asyncio.CancelledError:
            logger.info(f"Таймер {timer.session_id} отменен")
            timer.state = TimerState.STOPPED
        except Exception as e:
            logger.error(f"Ошибка в таймере {timer.session_id}: {e}")
            timer.state = TimerState.STOPPED
    
    async def _monitor_timers(self):
        """Мониторинг состояния таймеров"""
        try:
            while self._running:
                # Очищаем завершенные таймеры
                to_remove = []
                for session_id, timer in self.timers.items():
                    if timer.task and timer.task.done():
                        to_remove.append(session_id)
                
                for session_id in to_remove:
                    del self.timers[session_id]
                
                # Логируем статистику
                active_count = self.get_active_timers_count()
                if active_count > 0:
                    logger.debug(
                        f"Активных таймеров: {active_count}, "
                        f"всего: {len(self.timers)}"
                    )
                
                # Ждем перед следующей проверкой
                await asyncio.sleep(30)
                
        except asyncio.CancelledError:
            logger.info("Монитор таймеров остановлен")
        except Exception as e:
            logger.error(f"Ошибка в мониторе таймеров: {e}")


# Глобальный экземпляр планировщика
focus_scheduler = FocusScheduler(tick_interval=5)