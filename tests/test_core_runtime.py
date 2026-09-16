import unittest
from calypso.config import Config
from calypso.runtime import Runtime
from calypso.hermes.registry_bridge import RegistryAgentBridge
class RuntimeTests(unittest.TestCase):
 def runtime(self):
  runtime=Runtime(config=Config(hermes_provider='fake')); self.addCleanup(runtime.close); return runtime
 def test_construct(self): self.assertIsNotNone(self.runtime().navigation)
 def test_go_to(self):
  r=self.runtime(); r.go_to('bed'); self.assertEqual(r.behavior.target,'bed')
 def test_fake_start(self):
  r=self.runtime(); r.fake_task_start(); self.assertTrue(r.behavior.task)
 def test_fake_finish(self):
  r=self.runtime(); r.fake_task_start(); r.fake_task_finish(); self.assertFalse(r.behavior.task)
 def test_hermes_work_lifecycle_reaches_computer_and_turns_screen_on(self):
  r=self.runtime(); bridge=RegistryAgentBridge(r.behavior,'unused')
  bridge._observe(['job']); bridge.drain()
  self.assertTrue(r.behavior.task); self.assertFalse(r.computer.on)
  for _ in range(300):
   r.tick(.1)
   if r.computer.on: break
  self.assertTrue(r.computer.on)
  bridge._observe([]); bridge._observe([]); bridge.drain()
  self.assertFalse(r.behavior.task); self.assertFalse(r.computer.on)
