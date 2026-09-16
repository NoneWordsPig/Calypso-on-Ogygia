"""Non-blocking loopback Hermes bridge."""
from __future__ import annotations
import json, queue, threading, urllib.request

_MAP = {"running":"working", "working":"working", "in_progress":"working",
        "queued":"working", "action_required":"waiting",
        "ready":"review", "review":"review", "completed":"completed",
        "success":"completed", "failed":"failed", "idle":"idle"}

class HttpAgentBridge:
    def __init__(self, manager, url, interval=1.0, timeout=2.0):
        self.manager, self.url, self.interval, self.timeout = manager, str(url), max(.1, float(interval)), float(timeout)
        self._events, self._stop, self._thread = queue.Queue(), threading.Event(), None
        self._idle_samples = 0; self._active = False
    def start(self):
        if self._thread and self._thread.is_alive(): return
        self._stop.clear(); self._thread = threading.Thread(target=self._run, name="hermes-poll", daemon=True); self._thread.start()
    def stop(self, timeout=2.0):
        self._stop.set()
        if self._thread: self._thread.join(timeout)
        return not (self._thread and self._thread.is_alive())
    close = stop
    def drain(self):
        while True:
            try: event = self._events.get_nowait()
            except queue.Empty: break
            if event[0] == "start": self.manager.task_started(event[1])
            elif event[0] == "finish": self.manager.task_finished(event[1])
    def _observe(self, data):
        """Consume one valid HTTP snapshot and enqueue stable edge events."""
        if not isinstance(data, dict):
            data = {}
        rows = data.get("sessions", [])
        if not isinstance(rows, list):
            rows = []
        if data.get("status") and not rows:
            rows = [data]
        current = {}
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            sid = str(row.get("session_id") or row.get("id") or f"hermes-{index}")
            current[sid] = _MAP.get(str(row.get("status", "idle")).lower(), "idle")
        active_ids = [sid for sid, status in current.items() if status == "working"]
        if active_ids:
            self._idle_samples = 0
            if not self._active:
                self._active = True
                self._events.put(("start", active_ids[0]))
            return
        # A successful response with no active session is an explicit idle
        # sample. Two samples prevent one stale payload from causing a flicker.
        self._idle_samples = min(2, self._idle_samples + 1)
        if self._active and self._idle_samples >= 2:
            self._active = False
            self._events.put(("finish", "hermes"))
    def _run(self):
        while not self._stop.is_set():
            try:
                with urllib.request.urlopen(self.url, timeout=self.timeout) as response:
                    data = json.loads(response.read().decode("utf-8"))
                self._observe(data)
            except (OSError, ValueError, TypeError, AttributeError, json.JSONDecodeError):
                pass  # connection failure is unknown; never emit task completion
            self._stop.wait(self.interval)
