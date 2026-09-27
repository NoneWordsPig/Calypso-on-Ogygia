"""Observe Hermes turns that are actually busy, not merely open sessions."""

from __future__ import annotations

import json
import math
import os
import time
from pathlib import Path

from .session_bridge import SessionSnapshotBridge


class StreamAgentBridge(SessionSnapshotBridge):
    """Read an atomic, heartbeat-backed snapshot published by Hermes."""

    def __init__(self, manager, path, interval=1.0, max_age=8.0, clock=None):
        super().__init__(manager, interval)
        self.path = Path(os.path.expandvars(str(path)))
        self.max_age = max(1.0, float(max_age))
        self.clock = clock or time.time
        self._last_valid_at = None

    def _unknown_or_expired(self, now):
        # An invalid write may be transient. Never hold an old busy state forever.
        if self._last_valid_at is None or now - self._last_valid_at > self.max_age:
            return []
        return None

    def _read_active_ids(self):
        now = self.clock()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return []
        except (OSError, ValueError):
            return self._unknown_or_expired(now)

        if not isinstance(payload, dict) or payload.get("version") != 1:
            return self._unknown_or_expired(now)
        updated_at = payload.get("updated_at")
        ids = payload.get("busy_session_ids")
        if (isinstance(updated_at, bool) or not isinstance(updated_at, (int, float))
                or not math.isfinite(updated_at) or not isinstance(ids, list)
                or any(not isinstance(item, str) or not item.strip() for item in ids)):
            return self._unknown_or_expired(now)
        if updated_at > now + 5 or now - updated_at > self.max_age:
            return []
        self._last_valid_at = now
        return list(dict.fromkeys(ids))
