"""Observe Hermes' cross-process active-session lease registry."""
from __future__ import annotations

import json
import os
import queue
import threading
from pathlib import Path


def default_hermes_home() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    return Path(local) / "hermes" if local else Path.home() / "AppData" / "Local" / "hermes"


class RegistryAgentBridge:
    """Turn Hermes active-session registry snapshots into task edge events."""

    def __init__(self, manager, root=None, interval=1.0):
        self.manager = manager
        self.root = Path(os.path.expandvars(str(root))) if root else default_hermes_home()
        self.interval = max(.1, float(interval))
        self._events = queue.Queue()
        self._stop = threading.Event()
        self._thread = None
        self._active = False
        self._idle_samples = 0

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="hermes-registry", daemon=True)
        self._thread.start()

    def stop(self, timeout=2.0):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout)
        return not (self._thread and self._thread.is_alive())

    close = stop

    def drain(self):
        while True:
            try:
                event, task_id = self._events.get_nowait()
            except queue.Empty:
                break
            if event == "start":
                self.manager.task_started(task_id)
            elif event == "finish":
                self.manager.task_finished(task_id)

    def _registry_paths(self):
        yield self.root / "runtime" / "active_sessions.json"
        profiles = self.root / "profiles"
        if profiles.is_dir():
            yield from profiles.glob("*/runtime/active_sessions.json")

    def _read_active_ids(self):
        """Return active session ids, or None when an existing file is unreadable."""
        active = []
        for path in self._registry_paths():
            if not path.exists():
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError, json.JSONDecodeError):
                return None
            entries = payload.get("entries", []) if isinstance(payload, dict) else payload
            if not isinstance(entries, list):
                return None
            for index, entry in enumerate(entries):
                if not isinstance(entry, dict):
                    continue
                active.append(str(entry.get("session_id") or entry.get("lease_id") or f"hermes-{index}"))
        return active

    def _observe(self, active_ids):
        if active_ids is None:
            return  # unknown: preserve the last published state
        if active_ids:
            self._idle_samples = 0
            if not self._active:
                self._active = True
                self._events.put(("start", active_ids[0]))
            return
        self._idle_samples = min(2, self._idle_samples + 1)
        if self._active and self._idle_samples >= 2:
            self._active = False
            self._events.put(("finish", "hermes"))

    def _run(self):
        while not self._stop.is_set():
            self._observe(self._read_active_ids())
            self._stop.wait(self.interval)
