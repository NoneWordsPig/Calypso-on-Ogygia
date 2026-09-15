import unittest
from calypso.runtime import Runtime
class RuntimeTests(unittest.TestCase):
 def test_construct(self): self.assertIsNotNone(Runtime().navigation)
 def test_go_to(self):
  r=Runtime(); r.go_to('bed'); self.assertEqual(r.behavior.target,'bed')
 def test_fake_start(self):
  r=Runtime(); r.fake_task_start(); self.assertTrue(r.behavior.task)
 def test_fake_finish(self):
  r=Runtime(); r.fake_task_start(); r.fake_task_finish(); self.assertFalse(r.behavior.task)
