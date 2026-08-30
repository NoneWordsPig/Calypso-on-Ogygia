"""Hermes status providers.

Mirrors the reference hermes-pet behaviour: the pet polls an attention source
every ~1s and reacts to task state. Two providers are available:

- MockHermesProvider: simulates a Hermes task lifecycle (idle -> working ->
  success -> ... -> action_required -> ...) so the state machine can be demoed
  without a real Hermes WebUI.
- HttpHermesProvider: polls the reference loopback endpoint
  (hermes-webui-desktop-companion's /api/pet/attention shape) when available.

Internal statuses: idle | working | success | waiting | review | failed.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Optional

from app.config import Config

STATUS_IDLE = "idle"
STATUS_WORKING = "working"
STATUS_SUCCESS = "success"
STATUS_WAITING = "waiting"
STATUS_REVIEW = "review"
STATUS_FAILED = "failed"


class HermesSnapshot:
    """One poll result: current aggregate status plus a transient event."""

    def __init__(self, status: str = STATUS_IDLE, event: Optional[str] = None,
                 sessions: Optional[list[dict]] = None) -> None:
        self.status = status
        self.event = event  # None | "success" | "failed"
        self.sessions = sessions or []

    @property
    def active_count(self) -> int:
        return len(self.sessions)


class HermesProvider:
    def poll(self) -> HermesSnapshot:
        raise NotImplementedError


class MockHermesProvider(HermesProvider):
    """Cycles through scripted phases (real seconds)."""

    def __init__(self, config: Config) -> None:
        loop = config.get("mock_hermes", "loop", [])
        self._phases = [dict(p) for p in loop] if loop else [{"status": "idle", "seconds": 5}]
        self._phase_index = 0
        self._phase_elapsed = 0.0
        self._phase = dict(self._phases[0])
        self._prev_status = self._phase["status"]
        self._session_id = "mock-session-1"

    def poll(self) -> HermesSnapshot:
        duration = float(self._phase.get("seconds", 5))
        self._phase_elapsed += 1.0
        if self._phase_elapsed >= duration:
            self._phase_elapsed = 0.0
            self._phase_index = (self._phase_index + 1) % len(self._phases)
            self._phase = dict(self._phases[self._phase_index])

        status = self._phase["status"]
        # Normalize reference status names to internal ones.
        internal = {
            "running": STATUS_WORKING,
            "working": STATUS_WORKING,
            "action_required": STATUS_WAITING,
            "ready": STATUS_REVIEW,
            "review": STATUS_REVIEW,
            "completed": STATUS_SUCCESS,
            "success": STATUS_SUCCESS,
            "failed": STATUS_FAILED,
            "idle": STATUS_IDLE,
        }.get(status, STATUS_IDLE)

        event = None
        if internal == STATUS_SUCCESS and self._prev_status in (STATUS_WORKING, STATUS_IDLE):
            event = "success"
        elif internal == STATUS_FAILED:
            event = "failed"
        self._prev_status = internal

        sessions = [{"session_id": self._session_id, "status": internal}]
        return HermesSnapshot(status=internal, event=event, sessions=sessions)


class HttpHermesProvider(HermesProvider):
    """Polls the reference hermes-pet /api/pet/attention endpoint."""

    def __init__(self, config: Config) -> None:
        self.url = str(config.get("hermes", "http_url", ""))
        self._prev_by_session: dict[str, str] = {}
        self._last_event: Optional[str] = None
        self._event_age = 0.0

    def poll(self) -> HermesSnapshot:
        if not self.url:
            return HermesSnapshot()
        try:
            with urllib.request.urlopen(self.url, timeout=2.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError):
            return HermesSnapshot(status=STATUS_IDLE, event=self._last_event)

        sessions = []
        statuses = set()
        for row in data.get("sessions", []) if isinstance(data, dict) else []:
            raw = str(row.get("status", "idle"))
            internal = {
                "running": STATUS_WORKING,
                "action_required": STATUS_WAITING,
                "ready": STATUS_REVIEW,
                "idle": STATUS_IDLE,
            }.get(raw, STATUS_IDLE)
            sid = str(row.get("session_id", ""))
            sessions.append({"session_id": sid, "status": internal, **row})
            statuses.add(internal)

        # completed/failed events detected by status transitions
        event = None
        now = time.time()
        if self._last_event and self._event_age < 2.0:
            event = self._last_event
        for s in sessions:
            sid = s["session_id"]
            prev = self._prev_by_session.get(sid)
            if prev == STATUS_WORKING and s["status"] in (STATUS_SUCCESS, STATUS_REVIEW):
                event = "success"
            elif prev and s["status"] == STATUS_FAILED:
                event = "failed"
            if event:
                self._last_event = event
                self._event_age = now
        self._prev_by_session = {s["session_id"]: s["status"] for s in sessions}
        if not event:
            self._event_age = now - self._event_age  # decay
        if self._event_age >= 2.0:
            self._last_event = None

        aggregate = STATUS_IDLE
        if STATUS_WAITING in statuses:
            aggregate = STATUS_WAITING
        elif STATUS_WORKING in statuses:
            aggregate = STATUS_WORKING
        elif STATUS_REVIEW in statuses:
            aggregate = STATUS_REVIEW
        elif STATUS_SUCCESS in statuses:
            aggregate = STATUS_SUCCESS
        elif STATUS_FAILED in statuses:
            aggregate = STATUS_FAILED
        return HermesSnapshot(status=aggregate, event=event, sessions=sessions)


def make_provider(config: Config) -> HermesProvider:
    provider = str(config.get("hermes", "provider", "mock")).lower()
    if provider == "http":
        return HttpHermesProvider(config)
    return MockHermesProvider(config)
