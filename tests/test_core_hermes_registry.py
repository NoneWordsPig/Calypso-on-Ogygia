import unittest
from pathlib import Path

from calypso.hermes.registry_bridge import RegistryAgentBridge


class Manager:
    def __init__(self): self.events=[]
    def task_started(self, task_id=None, metadata=None): self.events.append(("start",task_id))
    def task_finished(self, task_id=None, result=None): self.events.append(("finish",task_id))


class RegistryBridgeTests(unittest.TestCase):
    def setUp(self):
        self.root=Path(__file__).parent/'fixtures/hermes_registry'
        self.manager=Manager(); self.bridge=RegistryAgentBridge(self.manager,self.root)
    def observe(self,active_ids): self.bridge._observe(active_ids); self.bridge.drain()
    def test_root_and_profile_entries_are_merged(self):
        self.assertEqual(self.bridge._read_active_ids(),['root','profile'])
    def test_lifecycle_and_idle_debounce(self):
        self.observe(['job']); self.observe(['job'])
        self.assertEqual(self.manager.events,[("start","job")])
        self.observe([]); self.assertEqual(len(self.manager.events),1)
        self.observe([]); self.assertEqual(self.manager.events[-1],("finish","hermes"))
    def test_malformed_snapshot_is_unknown(self):
        bridge=RegistryAgentBridge(self.manager,Path(__file__).parent/'fixtures/hermes_registry_malformed')
        self.assertIsNone(bridge._read_active_ids())


if __name__ == '__main__': unittest.main()
