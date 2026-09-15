import unittest
from datetime import datetime
from calypso.time.time_manager import TimeManager, TimeMode
class TimeTests(unittest.TestCase):
 def test_sleep(self): self.assertIn('sleep',TimeManager(20,time_scale=120).advance(60))
 def test_wake(self): self.assertIn('wake',TimeManager(5,time_scale=120).advance(60))
 def test_midnight(self): self.assertTrue(TimeManager(23).is_sleep_period())
 def test_real(self): self.assertEqual(TimeManager(mode=TimeMode.REAL_TIME,datetime_provider=lambda:datetime(2020,1,1,7)).format_time(),'07:00')
