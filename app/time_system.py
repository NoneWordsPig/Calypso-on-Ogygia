"""Game time system (from the draft's time_manager.gd).

Game time advances with a real-time multiplier (default 1 game hour = 30 real
seconds). Active time is 06:00-21:00; the pet wakes at 06:00 and goes to bed
at 21:00.
"""
from __future__ import annotations

from app.config import Config


class GameTime:
    def __init__(self, config: Config) -> None:
        self.seconds_per_hour = float(config.get("time", "real_seconds_per_game_hour", 30.0))
        self.active_start = float(config.get("time", "active_start_hour", 6.0))
        self.active_end = float(config.get("time", "active_end_hour", 21.0))
        self.current_hour = float(config.get("time", "start_hour", 8.0))
        self.day = 1
        self._last_full_hour: int | None = None

    def update(self, dt: float) -> None:
        self.current_hour += dt / self.seconds_per_hour
        if self.current_hour >= 24.0:
            self.current_hour -= 24.0
            self.day += 1
        full = int(self.current_hour)
        if self._last_full_hour is None or full != self._last_full_hour:
            self._last_full_hour = full

    def hour_changed(self) -> bool:
        full = int(self.current_hour)
        if self._last_full_hour is None:
            self._last_full_hour = full
            return False
        if full != self._last_full_hour:
            self._last_full_hour = full
            return True
        return False

    def jump_hours(self, amount: float) -> None:
        self.current_hour = (self.current_hour + amount) % 24.0
        if self.current_hour < 0:
            self.current_hour += 24.0
        self._last_full_hour = int(self.current_hour)

    def is_active_time(self) -> bool:
        if self.active_start <= self.active_end:
            return self.active_start <= self.current_hour < self.active_end
        return self.current_hour >= self.active_start or self.current_hour < self.active_end

    def is_bedtime(self) -> bool:
        return int(self.current_hour) == int(self.active_end)

    def is_wake_time(self) -> bool:
        return int(self.current_hour) == int(self.active_start)

    def format_time(self) -> str:
        hours = int(self.current_hour)
        minutes = int(round((self.current_hour - hours) * 60))
        if minutes == 60:
            hours += 1
            minutes = 0
        return f"{hours:02d}:{minutes:02d}"
