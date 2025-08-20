"""
Асинхронный таймер для фокус-сессий
"""

import asyncio
from typing import Dict, Callable, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class FocusTimer:
    """Менеджер таймеров для фокус-сессий"""

    def __init__(self):
        self.active_timers: Dict[str, asyncio.Task] = {}
        self.session_data: Dict[str, Dict] = {}

    async def start_timer(
        self,
        session_id: str,
        duration_minutes: int,
        on_complete: Callable,
        on_tick: Optional[Callable] = None,
        tick_interval: int = 60,
    ):
        """
        Запускает новый таймер

        Args:
            session_id: ID сессии
            duration_minutes: Длительность в минутах
            on_complete: Callback при завершении
            on_tick: Callback каждую минуту (опционально)
            tick_interval: Интервал вызова on_tick в секундах
        """
        if session_id in self.active_timers:
            await self.stop_timer(session_id)

        # Сохраняем данные сессии
        self.session_data[session_id] = {
            "start_time": datetime.utcnow(),
            "duration": duration_minutes,
            "elapsed": 0,
            "is_paused": False,
            "pause_time": None,
        }

        # Создаем задачу таймера
        timer_task = asyncio.create_task(
            self._run_timer(session_id, duration_minutes, on_complete, on_tick, tick_interval)
        )
        self.active_timers[session_id] = timer_task

        logger.info(f"Запущен таймер для сессии {session_id} на {duration_minutes} минут")

    async def _run_timer(
        self,
        session_id: str,
        duration_minutes: int,
        on_complete: Callable,
        on_tick: Optional[Callable],
        tick_interval: int,
    ):
        """
        Внутренний метод для запуска таймера
        """
        try:
            total_seconds = duration_minutes * 60
            elapsed_seconds = 0

            while elapsed_seconds < total_seconds:
                # Проверяем, не остановлен ли таймер
                if session_id not in self.active_timers:
                    break

                # Проверяем паузу
                session = self.session_data.get(session_id)
                if session and session["is_paused"]:
                    await asyncio.sleep(1)
                    continue

                # Ждем интервал
                await asyncio.sleep(tick_interval)
                elapsed_seconds += tick_interval

                # Обновляем elapsed time
                if session:
                    session["elapsed"] = elapsed_seconds // 60

                # Вызываем callback если есть
                if on_tick and elapsed_seconds % 60 == 0:
                    remaining_minutes = (total_seconds - elapsed_seconds) // 60
                    await on_tick(session_id, remaining_minutes)

            # Сессия завершена
            if session_id in self.active_timers:
                await on_complete(session_id, duration_minutes)
                self.stop_timer_sync(session_id)

        except asyncio.CancelledError:
            logger.info(f"Таймер {session_id} был отменен")
        except Exception as e:
            logger.error(f"Ошибка в таймере {session_id}: {e}")

    def pause_timer(self, session_id: str) -> bool:
        """
        Ставит таймер на паузу
        """
        if session_id in self.session_data:
            session = self.session_data[session_id]
            if not session["is_paused"]:
                session["is_paused"] = True
                session["pause_time"] = datetime.utcnow()
                logger.info(f"Таймер {session_id} поставлен на паузу")
                return True
        return False

    def resume_timer(self, session_id: str) -> bool:
        """
        Возобновляет таймер после паузы
        """
        if session_id in self.session_data:
            session = self.session_data[session_id]
            if session["is_paused"]:
                session["is_paused"] = False
                session["pause_time"] = None
                logger.info(f"Таймер {session_id} возобновлен")
                return True
        return False

    async def stop_timer(self, session_id: str) -> int:
        """
        Останавливает таймер и возвращает elapsed минуты
        """
        elapsed_minutes = 0

        if session_id in self.session_data:
            elapsed_minutes = self.session_data[session_id]["elapsed"]

        if session_id in self.active_timers:
            self.active_timers[session_id].cancel()
            await asyncio.sleep(0.1)  # Даем время на отмену

        self.stop_timer_sync(session_id)
        return elapsed_minutes

    def stop_timer_sync(self, session_id: str):
        """
        Синхронная остановка таймера (очистка данных)
        """
        if session_id in self.active_timers:
            del self.active_timers[session_id]
        if session_id in self.session_data:
            del self.session_data[session_id]

    def get_remaining_time(self, session_id: str) -> Optional[int]:
        """
        Возвращает оставшееся время в минутах
        """
        if session_id in self.session_data:
            session = self.session_data[session_id]
            remaining = session["duration"] - session["elapsed"]
            return max(0, remaining)
        return None

    def is_timer_active(self, session_id: str) -> bool:
        """
        Проверяет, активен ли таймер
        """
        return session_id in self.active_timers

    def is_timer_paused(self, session_id: str) -> bool:
        """
        Проверяет, на паузе ли таймер
        """
        if session_id in self.session_data:
            return self.session_data[session_id]["is_paused"]
        return False


# Глобальный экземпляр менеджера таймеров
focus_timer_manager = FocusTimer()
