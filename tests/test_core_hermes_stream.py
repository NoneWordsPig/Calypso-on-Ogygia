import json
import unittest
from pathlib import Path
from uuid import uuid4

from calypso.config import PROJECT_ROOT
from calypso.hermes.stream_bridge import StreamAgentBridge


class Manager:
    def __init__(self):
        self.events = []

    def set_task_active(self, source, active, task_id=None):
        self.events.append((source, active, task_id))


class StreamBridgeTests(unittest.TestCase):
    def setUp(self):
        self.path = PROJECT_ROOT / "logs" / f"busy-test-{uuid4().hex}.json"
        self.now = [1000.0]
        self.manager = Manager()
        self.bridge = StreamAgentBridge(
            self.manager, self.path, max_age=8.0, clock=lambda: self.now[0])

    def tearDown(self):
        self.path.unlink(missing_ok=True)

    def write(self, ids, updated_at=None):
        self.path.write_text(json.dumps({
            "version": 1,
            "updated_at": self.now[0] if updated_at is None else updated_at,
            "busy_session_ids": ids,
        }), encoding="utf-8")

    def observe(self):
        self.bridge._observe(self.bridge._read_active_ids())
        self.bridge.drain()

    def test_open_session_registry_is_irrelevant_until_busy_snapshot_exists(self):
        self.assertEqual(self.bridge._read_active_ids(), [])
        self.observe()
        self.assertEqual(self.manager.events, [])

    def test_busy_turn_starts_and_two_idle_samples_finish(self):
        self.write(["turn-a", "turn-b"])
        self.observe()
        self.assertEqual(self.manager.events, [("hermes", True, "turn-a")])
        self.write([])
        self.observe()
        self.assertEqual(len(self.manager.events), 1)
        self.observe()
        self.assertEqual(self.manager.events[-1], ("hermes", False, "hermes"))

    def test_stale_or_corrupt_snapshot_cannot_hold_work_forever(self):
        self.write(["turn-a"])
        self.observe()
        self.path.write_text("{broken", encoding="utf-8")
        self.now[0] += 4
        self.assertIsNone(self.bridge._read_active_ids())
        self.now[0] += 5
        self.observe()
        self.observe()
        self.assertEqual(self.manager.events[-1], ("hermes", False, "hermes"))
        self.write(["turn-a"], updated_at=1000)
        self.assertEqual(self.bridge._read_active_ids(), [])


if __name__ == "__main__":
    unittest.main()
