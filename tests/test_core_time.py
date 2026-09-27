import unittest
from datetime import datetime

from calypso.time.time_manager import TimeManager, TimeMode


class TimeTests(unittest.TestCase):
    def test_debug_schedule_markers(self):
        self.assertIn("sleep", TimeManager(20, mode=TimeMode.DEBUG_TIME,
                                           time_scale=120).advance(60))
        self.assertIn("wake", TimeManager(5, mode=TimeMode.DEBUG_TIME,
                                          time_scale=120).advance(60))

    def test_real_clock_crosses_bedtime_and_wake(self):
        current = [datetime(2026, 9, 26, 20, 59, 59)]
        clock = TimeManager(mode=TimeMode.REAL_TIME,
                            datetime_provider=lambda: current[0])
        current[0] = datetime(2026, 9, 26, 21, 0)
        self.assertEqual(clock.advance(.1), ["sleep"])
        self.assertTrue(clock.is_sleep_period())
        current[0] = datetime(2026, 9, 27, 6, 0)
        self.assertEqual(clock.advance(.1), ["wake"])
        self.assertFalse(clock.is_sleep_period())

    def test_real_clock_starts_in_night_period(self):
        clock = TimeManager(datetime_provider=lambda: datetime(2026, 9, 26, 23, 30))
        self.assertEqual(clock.format_time(), "23:30")
        self.assertTrue(clock.is_sleep_period())

    def test_clock_rollback_reconciles_current_period(self):
        current = [datetime(2026, 9, 27, 7)]
        clock = TimeManager(datetime_provider=lambda: current[0])
        current[0] = datetime(2026, 9, 27, 3)
        self.assertEqual(clock.advance(.1), [])
        self.assertTrue(clock.is_sleep_period())
