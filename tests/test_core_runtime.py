import unittest
import json
import time
from pathlib import Path
from uuid import uuid4
from calypso.config import Config
from calypso.config import PROJECT_ROOT
from calypso.runtime import Runtime
from calypso.behavior.states import State
from calypso.hermes.registry_bridge import RegistryAgentBridge
class RuntimeTests(unittest.TestCase):
 def runtime(self):
  runtime=Runtime(config=Config(hermes_provider='fake')); self.addCleanup(runtime.close); return runtime
 def test_construct(self): self.assertIsNotNone(self.runtime().navigation)
 def test_go_to(self):
  r=self.runtime(); r.go_to('bed'); self.assertEqual(r.behavior.target,'bed')
 def test_reaching_fishing_spot_selects_fishing_animation(self):
  class DayClock:
   def advance(self, dt): pass
   def is_sleep_period(self): return False
  r=Runtime(config=Config(hermes_provider='fake'), time=DayClock())
  self.addCleanup(r.close)
  r.go_to('fishing')
  for _ in range(600):
   r.tick(.1)
   if r.behavior.state == State.FISHING: break
  self.assertEqual(r.behavior.state, State.FISHING)
  self.assertEqual(r.animation_intent, 'fish_cast')
  r.tick(.8)
  self.assertEqual(r.animation_intent, 'fish_wait')
 def test_fake_start(self):
  r=self.runtime(); r.fake_task_start(); self.assertTrue(r.behavior.task)
 def test_fake_finish(self):
  r=self.runtime(); r.fake_task_start(); r.fake_task_finish(); self.assertFalse(r.behavior.task)
 def test_existing_hermes_session_is_applied_before_first_tick(self):
  root=Path(__file__).parent/'fixtures/hermes_registry'
  r=Runtime(config=Config(hermes_provider='registry',hermes_registry_root=str(root)))
  self.addCleanup(r.close)
  self.assertTrue(r.behavior.task)
  self.assertEqual(r.behavior.target,'computer_use')
 def test_busy_provider_ignores_open_session_registry(self):
  missing=Path(__file__).parent/'fixtures/hermes_registry/runtime/no-busy-file.json'
  r=Runtime(config=Config(hermes_provider='busy',hermes_busy_file=str(missing)))
  self.addCleanup(r.close)
  self.assertFalse(r.behavior.task)
 def test_busy_snapshot_drives_work_and_releases_after_turn(self):
  path=PROJECT_ROOT/'logs'/f'busy-runtime-test-{uuid4().hex}.json'
  path.parent.mkdir(parents=True,exist_ok=True)
  def publish(ids):
   path.write_text(json.dumps({'version':1,'updated_at':time.time(),
                               'busy_session_ids':ids}),encoding='utf-8')
  try:
   publish(['thinking-turn'])
   r=Runtime(config=Config(hermes_provider='busy',hermes_busy_file=str(path),
                           hermes_poll_seconds=60.0))
   try:
    self.assertTrue(r.behavior.task)
    self.assertEqual(r.behavior.target,'computer_use')
    for _ in range(300):
     r.tick(.1)
     if r.computer.on: break
    self.assertTrue(r.computer.on)
    publish([])
    r.bridge._observe(r.bridge._read_active_ids())
    r.bridge._observe(r.bridge._read_active_ids())
    r.tick(.1)
    self.assertFalse(r.behavior.task)
    self.assertFalse(r.computer.on)
   finally:
    r.close()
  finally:
   path.unlink(missing_ok=True)
 def test_hermes_work_lifecycle_reaches_computer_and_turns_screen_on(self):
  class DayClock:
   def advance(self, dt): pass
   def is_sleep_period(self): return False
  r=Runtime(config=Config(hermes_provider='fake'), time=DayClock())
  self.addCleanup(r.close)
  bridge=RegistryAgentBridge(r.behavior,'unused')
  bridge._observe(['job']); bridge.drain()
  self.assertTrue(r.behavior.task); self.assertFalse(r.computer.on)
  self.assertEqual(r.behavior.target,'computer_use')
  for _ in range(300):
   r.tick(.1)
   if r.computer.on: break
  self.assertTrue(r.computer.on)
  self.assertEqual(r.animation_intent,'work')
  self.assertEqual(r.character.position, r.navigation.point('computer_use'))
  self.assertGreater(r.character.position[1], r.navigation.point('computer')[1])
  bridge._observe([]); bridge._observe([]); bridge.drain()
  self.assertFalse(r.behavior.task); self.assertFalse(r.computer.on)
  self.assertEqual(r.behavior.target,'spawn')
  for _ in range(300):
   r.tick(.1)
   if r.behavior.state == State.IDLE: break
  self.assertEqual(r.behavior.state,State.IDLE)
  self.assertTrue(r.animation_intent.startswith('idle_'))
