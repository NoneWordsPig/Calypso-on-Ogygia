"""Non-blocking loopback HTTP provider, kept for existing Hermes setups."""

from __future__ import annotations

import json
import urllib.request

from .session_bridge import SessionSnapshotBridge


ACTIVE_STATUSES = {"running", "working", "in_progress", "streaming"}


class HttpAgentBridge(SessionSnapshotBridge):
    def __init__(self, manager, url, interval=1.0, timeout=2.0):
        super().__init__(manager, interval)
        self.url = str(url)
        self.timeout = float(timeout)

    @staticmethod
    def active_ids(payload):
        if not isinstance(payload, dict):
            return None
        rows = payload.get("sessions")
        if rows is None:
            rows = [payload] if "status" in payload else []
        if not isinstance(rows, list):
            return None
        active = []
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                return None
            if str(row.get("status", "idle")).lower() in ACTIVE_STATUSES:
                active.append(str(row.get("session_id") or row.get("id") or f"hermes-{index}"))
        return active

    def _read_active_ids(self):
        try:
            with urllib.request.urlopen(self.url, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, ValueError, TypeError, AttributeError):
            return None
        return self.active_ids(payload)
