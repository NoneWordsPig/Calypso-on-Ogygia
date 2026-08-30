"""Behaviour state machine for Calypso's Ogygia.

Replaces the draft's behavior_manager.gd: IDLE / WALKING / SLEEPING / WORKING /
CELEBRATING / WAITING / REVIEW / FAILED with explicit priorities
(工作 > 庆祝 > 等待/审查 > 睡眠 > 行走 > 空闲), a 06:00-21:00 schedule, and a
Hermes-status mapping that mirrors the reference hermes-pet behaviour.
"""
from __future__ import annotations

import random
from typing import Optional

from app.hermes_status import HermesSnapshot
from app.navigation import Navigation, PathFollower
from app.time_system import GameTime

IDLE = "IDLE"
WALKING = "WALKING"
SLEEPING = "SLEEPING"
WORKING = "WORKING"
CELEBRATING = "CELEBRATING"
WAITING = "WAITING"
REVIEW = "REVIEW"
FAILED = "FAILED"

ALL_STATES = (IDLE, WALKING, SLEEPING, WORKING, CELEBRATING, WAITING, REVIEW, FAILED)

STATE_LABELS_ZH = {
    IDLE: "空闲",
    WALKING: "行走",
    SLEEPING: "睡眠",
    WORKING: "工作",
    CELEBRATING: "庆祝",
    WAITING: "等待",
    REVIEW: "审查",
    FAILED: "失败",
}

DEFAULT_PRIORITIES = {
    WORKING: 6,
    CELEBRATING: 5,
    WAITING: 5,
    REVIEW: 4,
    FAILED: 4,
    SLEEPING: 3,
    WALKING: 2,
    IDLE: 1,
}


class Actor:
    """The pet's body: position, path following, facing."""

    def __init__(self, spawn: tuple[float, float], speed: float, arrive_radius: float = 12.0) -> None:
        self.pos: tuple[float, float] = spawn
        self.follower = PathFollower(speed, arrive_radius)
        self.facing: str = "down"
        self.moving = False

    def walk_to(self, path: list[tuple[float, float]]) -> None:
        self.follower.set_path(path)
        self.moving = bool(path)

    def stop(self) -> None:
        self.follower.stop()
        self.moving = False

    def update(self, dt: float) -> None:
        if self.follower.moving:
            self.pos = self.follower.update(self.pos, dt)
            self.moving = self.follower.moving
            self._update_facing(self.follower.direction)
        else:
            self.moving = False

    def arrived(self) -> bool:
        return self.follower.is_arrived()

    def _update_facing(self, direction: tuple[float, float]) -> None:
        dx, dy = direction
        if abs(dx) > abs(dy) * 1.2:
            self.facing = "left" if dx < 0 else "right"
        elif abs(dy) > abs(dx) * 1.2:
            self.facing = "up" if dy < 0 else "down"


class Behavior:
    def __init__(self, navigation: Navigation, actor: Actor, time: GameTime,
                 config, rng: Optional[random.Random] = None) -> None:
        self.nav = navigation
        self.actor = actor
        self.time = time
        self.config = config
        self.rng = rng or random.Random()

        raw_priorities = config.get("behavior", "priorities", {})
        self.priorities = {s: int(raw_priorities.get(s, DEFAULT_PRIORITIES[s])) for s in ALL_STATES}

        self.state: str = IDLE
        self._goal: Optional[str] = None          # computer | bed | random
        self._pending: Optional[str] = None       # state to enter after arrival
        self._idle_timer = 0.0
        self._state_timer = 0.0
        self._celebrate_phase = "jumping"
        self._forced_work_left = 0.0
        self._current_hermes: Optional[str] = None

        self._walk_interval = config.get("behavior", "walk_interval_range", [6.0, 15.0])
        self._celebrate_seconds = float(config.get("behavior", "celebrate_seconds", 6.0))
        self._failed_seconds = float(config.get("behavior", "failed_seconds", 4.0))
        self._stub_work_seconds = float(config.get("behavior", "stub_work_seconds", 2.0))
        self._schedule_next_idle()

    # -- public API ------------------------------------------------------
    def reset(self) -> None:
        self._force_state(IDLE)
        self._goal = None
        self._pending = None
        self.actor.stop()
        self._schedule_next_idle()

    def update(self, dt: float, snapshot: HermesSnapshot) -> None:
        self.actor.update(dt)
        self._handle_events(dt, snapshot)
        self._handle_persistent_status(dt, snapshot)
        self._handle_schedule()
        self._tick_state(dt)

    # -- hermes mapping --------------------------------------------------
    def _handle_events(self, dt: float, snapshot: HermesSnapshot) -> None:
        if snapshot.event == "success":
            self.celebrate()
        elif snapshot.event == "failed":
            self.fail()

    def _handle_persistent_status(self, dt: float, snapshot: HermesSnapshot) -> None:
        status = snapshot.status
        desired: Optional[str] = None
        if status == "working":
            desired = WORKING
        elif status == "waiting":
            desired = WAITING
        elif status == "review":
            desired = REVIEW

        if desired == WORKING:
            self._current_hermes = WORKING
            self._forced_work_left = 0.0
            self._enter_working()
            return

        # hermes no longer busy
        if self._current_hermes in (WORKING, WAITING, REVIEW):
            self._current_hermes = None
            self._forced_work_left = 0.0
            if self.state in (WORKING, WAITING, REVIEW):
                self._return_to_idle()

        if desired in (WAITING, REVIEW):
            self._current_hermes = desired
            self._enter_by_priority(desired, keep_position=True)

    # -- schedule --------------------------------------------------------
    def _handle_schedule(self) -> None:
        if self.time.is_bedtime() and self.state != SLEEPING:
            self.go_sleep()
        elif self.time.is_wake_time() and self.state == SLEEPING:
            self.wake_up()

    def _tick_state(self, dt: float) -> None:
        if self.state == IDLE:
            self._idle_timer -= dt
            if self._idle_timer <= 0.0 and self.time.is_active_time():
                self._start_random_walk()
        elif self.state == WALKING:
            if self.actor.arrived():
                self._on_arrived()
        elif self.state in (CELEBRATING, FAILED):
            self._state_timer -= dt
            if self.state == CELEBRATING and self._state_timer < self._celebrate_seconds / 2.0:
                if self._celebrate_phase != "waving":
                    self._celebrate_phase = "waving"
            if self._state_timer <= 0.0:
                self._return_to_idle()
        elif self.state == WORKING and self._forced_work_left > 0.0:
            self._forced_work_left -= dt
            if self._forced_work_left <= 0.0:
                self._return_to_idle()

    # -- state transitions ----------------------------------------------
    def _enter_working(self) -> None:
        if self.state == WORKING:
            return
        if self._goal == "computer" and self._pending == WORKING and self.state == WALKING:
            return  # already walking to the computer
        if not self._try_enter(WORKING):
            return
        # walk to the computer interaction spot
        computer = self.nav.poi("computer")
        interaction = self.config.get("computer", "interaction", {})
        offset = interaction.get("position", [-40, 0])
        target = (computer[0] + float(offset[0]), computer[1] + float(offset[1]))
        self._walk_to_target(target, goal="computer", pending=WORKING)

    def _enter_by_priority(self, state: str, keep_position: bool = True) -> None:
        if self.state == state:
            return
        if not self._try_enter(state):
            return
        if not keep_position:
            self.actor.stop()
        self._goal = None
        self._pending = None
        if state == CELEBRATING:
            self._state_timer = self._celebrate_seconds
            self._celebrate_phase = "jumping"
        elif state == FAILED:
            self._state_timer = self._failed_seconds
        self._force_state(state)
        self._schedule_next_idle()

    def celebrate(self) -> None:
        if self.state == WORKING:
            self._return_to_idle()  # brief transition out of work
        self._enter_by_priority(CELEBRATING)

    def fail(self) -> None:
        self._enter_by_priority(FAILED)

    def go_sleep(self) -> None:
        if self.state == SLEEPING:
            return
        if not self._try_enter(SLEEPING):
            return
        bed = self.nav.poi("bed")
        self._walk_to_target(bed, goal="bed", pending=SLEEPING)

    def wake_up(self) -> None:
        if self.state != SLEEPING:
            return
        self.actor.stop()
        self._force_state(IDLE)
        self._schedule_next_idle()

    def request_work(self, seconds: Optional[float] = None) -> None:
        """Manual work request (debug key F9 / external API)."""
        self._forced_work_left = seconds if seconds is not None else self._stub_work_seconds
        self._enter_working()

    def request_celebrate(self) -> None:
        self.celebrate()

    # -- walking ---------------------------------------------------------
    def _start_random_walk(self) -> None:
        if not self._try_enter(WALKING):
            return
        target = self.nav.random_walk_target(self.rng)
        self._walk_to_target(target, goal="random", pending=None)

    def _walk_to_target(self, target: tuple[float, float], goal: str, pending: Optional[str]) -> None:
        path = self.nav.find_path(self.actor.pos, target)
        if len(path) < 2:
            if pending:
                self._enter_arrived_state(pending, goal)
            else:
                self._force_state(IDLE)
                self._schedule_next_idle()
            return
        self._goal = goal
        self._pending = pending
        self._force_state(WALKING)
        self.actor.walk_to(path)

    def _on_arrived(self) -> None:
        if self._pending:
            pending, goal = self._pending, self._goal
            self._pending = None
            self._goal = None
            self._enter_arrived_state(pending, goal)
            return
        self._goal = None
        self._force_state(IDLE)
        self._schedule_next_idle()

    def _enter_arrived_state(self, state: str, goal: Optional[str]) -> None:
        if state == SLEEPING:
            self._force_state(SLEEPING)
        elif state == WORKING:
            facing = self.config.get("computer", "interaction", {}).get("facing", "left")
            self.actor.facing = facing
            self._force_state(WORKING)
            if self._current_hermes != WORKING:
                self._forced_work_left = self._forced_work_left or self._stub_work_seconds
        else:
            self._force_state(state)

    def _return_to_idle(self) -> None:
        self._goal = None
        self._pending = None
        self.actor.stop()
        self._force_state(IDLE)
        self._schedule_next_idle()

    # -- priority helpers ------------------------------------------------
    def _try_enter(self, state: str) -> bool:
        if self.priorities[state] < self.priorities[self.state]:
            return False
        return True

    def _force_state(self, state: str) -> None:
        if self.state == state:
            return
        self.state = state
        if state == IDLE:
            self.actor.stop()

    def _schedule_next_idle(self) -> None:
        lo, hi = float(self._walk_interval[0]), float(self._walk_interval[1])
        self._idle_timer = self.rng.uniform(lo, hi)

    # -- animation name --------------------------------------------------
    def animation_name(self) -> str:
        if self.state == WALKING:
            return "running-right" if self.actor.facing == "right" else "running-left"
        if self.state == WORKING:
            return "running"
        if self.state == SLEEPING:
            return "idle"
        if self.state == CELEBRATING:
            return self._celebrate_phase
        return self.state.lower()

    def fps(self, movement_fps: dict[str, float]) -> float:
        key = {
            IDLE: "idle",
            WALKING: "walk",
            SLEEPING: "sleep",
            WORKING: "work",
            CELEBRATING: "celebrate",
            WAITING: "waiting",
            REVIEW: "review",
            FAILED: "failed",
        }[self.state]
        return float(movement_fps.get(key, 6.0))

    def state_zh(self) -> str:
        return STATE_LABELS_ZH.get(self.state, self.state)

    def debug_summary(self) -> str:
        return (f"state={self.state} goal={self._goal} pending={self._pending} "
                f"pos=({self.actor.pos[0]:.0f},{self.actor.pos[1]:.0f}) facing={self.actor.facing}")
