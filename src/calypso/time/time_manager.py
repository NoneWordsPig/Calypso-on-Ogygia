"""Local clock and scheduled transitions for the companion."""

from datetime import datetime
from enum import Enum


class TimeMode(str, Enum):
    DEBUG_TIME = "DEBUG_TIME"
    REAL_TIME = "REAL_TIME"


class TimeManager:
    def __init__(self, start_hour=8.0, mode=TimeMode.REAL_TIME,
                 time_scale=120.0, datetime_provider=None,
                 sleep_minute=1260, wake_minute=360):
        self.mode = TimeMode(mode)
        self.time_scale = float(time_scale)
        self.sleep_minute = int(sleep_minute)
        self.wake_minute = int(wake_minute)
        if not 0 <= self.sleep_minute < 1440 or not 0 <= self.wake_minute < 1440:
            raise ValueError("sleep and wake minutes must be within one day")
        self.provider = datetime_provider or datetime.now
        self._total_minutes = float(start_hour) * 60.0
        self._last_real = self.provider()

    @staticmethod
    def _wall_minutes(value):
        return (value.toordinal() * 1440 + value.hour * 60 + value.minute
                + value.second / 60 + value.microsecond / 60_000_000)

    @property
    def minutes(self):
        if self.mode == TimeMode.REAL_TIME:
            now = self.provider()
            return now.hour * 60 + now.minute
        return int(self._total_minutes) % 1440

    @property
    def hour(self):
        return self.minutes / 60.0

    def format_time(self):
        minutes = self.minutes
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

    def is_sleep_period(self):
        minutes = self.minutes
        if self.sleep_minute > self.wake_minute:
            return minutes >= self.sleep_minute or minutes < self.wake_minute
        return self.sleep_minute <= minutes < self.wake_minute

    def advance(self, real_seconds):
        """Return schedule markers crossed since the previous tick."""
        if self.mode == TimeMode.DEBUG_TIME:
            previous = self._total_minutes
            self._total_minutes += max(0.0, float(real_seconds)) * self.time_scale / 60.0
            current = self._total_minutes
        else:
            previous = self._wall_minutes(self._last_real)
            self._last_real = self.provider()
            current = self._wall_minutes(self._last_real)
        if current <= previous:
            return []  # A clock rollback is handled by the current-period check.

        events = []
        for day in range(int(previous // 1440), int(current // 1440) + 1):
            for marker, name in ((self.sleep_minute, "sleep"),
                                 (self.wake_minute, "wake")):
                point = day * 1440 + marker
                if previous < point <= current:
                    events.append((point, name))
        return [name for _, name in sorted(events)]
