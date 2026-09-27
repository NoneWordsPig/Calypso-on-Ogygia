"""Shared polling and debounce for Hermes activity snapshot providers."""

import logging
import queue
import threading


LOGGER = logging.getLogger(__name__)


class SessionSnapshotBridge:
    def __init__(self, manager, interval=1.0):
        self.manager = manager
        self.interval = max(0.1, float(interval))
        self._events = queue.Queue()
        self._stop = threading.Event()
        self._thread = None
        self._active = False
        self._idle_samples = 0

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="hermes-sessions", daemon=True)
        self._thread.start()

    def stop(self, timeout=2.0):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout)
        return not (self._thread and self._thread.is_alive())

    close = stop

    def prime(self):
        """Apply one local snapshot before the UI's first frame."""
        try:
            self._observe(self._read_active_ids())
        except Exception:
            LOGGER.exception("initial Hermes session read failed")
        self.drain()

    def drain(self):
        while True:
            try:
                active, task_id = self._events.get_nowait()
            except queue.Empty:
                break
            if hasattr(self.manager, "set_task_active"):
                self.manager.set_task_active("hermes", active, task_id)
            elif active:
                self.manager.task_started(task_id)
            else:
                self.manager.task_finished(task_id)

    def _observe(self, active_ids):
        if active_ids is None:
            return  # Unknown or temporarily unreadable snapshot.
        if active_ids:
            self._idle_samples = 0
            if not self._active:
                self._active = True
                LOGGER.info("Hermes busy turns detected: %d", len(active_ids))
                self._events.put((True, active_ids[0]))
        else:
            self._idle_samples = min(2, self._idle_samples + 1)
            if self._active and self._idle_samples >= 2:
                self._active = False
                LOGGER.info("Hermes busy turns cleared")
                self._events.put((False, "hermes"))

    def _read_active_ids(self):
        raise NotImplementedError

    def _run(self):
        while not self._stop.is_set():
            try:
                self._observe(self._read_active_ids())
            except Exception:
                LOGGER.exception("Hermes session poll failed")
            self._stop.wait(self.interval)
