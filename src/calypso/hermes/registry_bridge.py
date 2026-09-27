"""Observe Hermes' cross-process active-session lease registry."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .session_bridge import SessionSnapshotBridge


def default_hermes_home() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    return Path(local) / "hermes" if local else Path.home() / "AppData" / "Local" / "hermes"


class RegistryAgentBridge(SessionSnapshotBridge):
    """A present entry in Hermes' active registry represents a live session."""

    def __init__(self, manager, root=None, interval=1.0):
        super().__init__(manager, interval)
        self.root = Path(os.path.expandvars(str(root))) if root else default_hermes_home()

    def _registry_paths(self):
        yield self.root / "runtime" / "active_sessions.json"
        profiles = self.root / "profiles"
        if profiles.is_dir():
            yield from profiles.glob("*/runtime/active_sessions.json")

    def _read_active_ids(self):
        """Return active session IDs, or None if an existing file is unreadable."""
        active = []
        for path in self._registry_paths():
            if not path.exists():
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return None
            entries = payload.get("entries") if isinstance(payload, dict) else payload
            if not isinstance(entries, list):
                return None
            for entry in entries:
                if not isinstance(entry, dict):
                    return None
                session_id = entry.get("session_id") or entry.get("lease_id")
                if not session_id:
                    return None
                active.append(str(session_id))
        return active
