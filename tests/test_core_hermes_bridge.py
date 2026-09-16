import unittest

from calypso.hermes.http_bridge import HttpAgentBridge


class Manager:
    def __init__(self):
        self.events = []

    def task_started(self, task_id=None, metadata=None):
        self.events.append(("start", task_id))

    def task_finished(self, task_id=None, result=None):
        self.events.append(("finish", task_id))


class HermesBridgeTests(unittest.TestCase):
    def setUp(self):
        self.manager = Manager()
        self.bridge = HttpAgentBridge(self.manager, "http://127.0.0.1:17787", timeout=.25)

    def observe(self, payload):
        self.bridge._observe(payload)
        self.bridge.drain()

    def test_aggregate_edges_and_idle_debounce(self):
        self.observe({"sessions": [
            {"session_id": "done", "status": "completed"},
            {"session_id": "live", "status": "running"},
        ]})
        self.observe({"sessions": [{"session_id": "live", "status": "working"}]})
        self.observe({"sessions": [{"session_id": "live", "status": "idle"}]})
        self.assertEqual(self.manager.events, [("start", "live")])
        self.observe({"sessions": []})
        self.assertEqual(self.manager.events, [("start", "live"), ("finish", "hermes")])

    def test_top_level_and_in_progress_are_active(self):
        self.observe({"status": "in_progress"})
        self.assertEqual(self.manager.events[0][0], "start")

    def test_malformed_rows_are_safe_idle_samples(self):
        self.observe({"sessions": "not-a-list"})
        self.observe({"sessions": [None, "bad"]})
        self.assertEqual(self.manager.events, [])


if __name__ == "__main__":
    unittest.main()
