from datetime import datetime
from enum import Enum

class TimeMode(str, Enum):
    DEBUG_TIME = 'DEBUG_TIME'
    REAL_TIME = 'REAL_TIME'

class TimeManager:
    def __init__(self, start_hour=8.0, mode=TimeMode.DEBUG_TIME,
                 time_scale=120.0, datetime_provider=None, sleep_minute=1260, wake_minute=360):
        self.mode = TimeMode(mode)
        self.time_scale = float(time_scale)
        self._total_minutes = float(start_hour) * 60.0
        self.sleep_minute, self.wake_minute = sleep_minute, wake_minute
        self.provider = datetime_provider or datetime.now
        self._last_real = self.provider()
        self._previous_minutes = self.minutes

    @property
    def hour(self):
        if self.mode == TimeMode.REAL_TIME:
            value = self.provider()
            return value.hour + value.minute / 60.0 + value.second / 3600.0
        return (self._total_minutes / 60.0) % 24

    @property
    def minutes(self):
        return int(self.hour * 60) % 1440

    def format_time(self):
        return f'{self.minutes // 60:02d}:{self.minutes % 60:02d}'

    def is_sleep_period(self):
        if self.sleep_minute >= self.wake_minute:
            return self.minutes >= self.sleep_minute or self.minutes < self.wake_minute
        return self.wake_minute <= self.minutes < self.sleep_minute

    def advance(self, real_seconds):
        """Advance debug time and return every schedule marker crossed."""
        old_total = self._total_minutes
        if self.mode == TimeMode.DEBUG_TIME:
            self._total_minutes += float(real_seconds) * self.time_scale / 60.0
        else:
            now = self.provider()
            delta = (now - self._last_real).total_seconds() / 60.0
            if delta >= 0: self._total_minutes += delta
            self._last_real = now
        new_total = self._total_minutes; elapsed = new_total - old_total
        old = int(old_total) % 1440
        new = int(new_total) % 1440
        self._previous_minutes = new
        elapsed = (new - old) % 1440
        if elapsed == 0 and new != old:
            elapsed = 1440
        events = []
        start_day = int(old_total // 1440); end_day = int(new_total // 1440)
        for day in range(start_day, end_day + 1):
            for marker, name in ((self.sleep_minute, 'sleep'), (self.wake_minute, 'wake')):
                point = day * 1440 + marker
                if old_total < point <= new_total: events.append((point, name))
        events.sort(); events = [name for _, name in events]
        return events
