"""Behaviour tests: priority arbitration, schedule, hermes mapping."""
import unittest

from app.behavior import (CELEBRATING, IDLE, SLEEPING, WAITING, WALKING, WORKING, Actor, Behavior)
from app.config import ROOT, Config
from app.hermes_status import HermesSnapshot
from app.navigation import Navigation
from app.time_system import GameTime

NAV = ROOT / "data" / "navigation.json"


def _make_behavior(hour=8.0):
    config = Config.load()
    nav = Navigation(NAV)
    time = GameTime(config)
    time.current_hour = hour
    time._last_full_hour = int(hour)
    actor = Actor(nav.poi("spawn"), speed=67.5)
    bh = Behavior(nav, actor, time, config)
    return config, nav, time, actor, bh


def _step(bh, dt=0.1, status="idle", event=None, steps=600):
    for _ in range(steps):
        bh.update(dt, HermesSnapshot(status=status, event=event))
        if bh.actor.moving is False and bh.state != WALKING:
            pass
    return bh


class TestPriority(unittest.TestCase):
    def test_ordering(self):
        config = Config.load()
        bh_prio = Behavior.__new__(Behavior)
        bh_prio.priorities = config.get("behavior", "priorities", {})
        order = [WORKING, CELEBRATING, WAITING, SLEEPING, WALKING, IDLE]
        values = [bh_prio.priorities[s] for s in order]
        self.assertEqual(values, sorted(values, reverse=True), "user priority 工作>庆祝>睡眠>行走")

    def test_work_interrupts_sleep(self):
        _, _, _, actor, bh = _make_behavior(hour=22.0)
        bh._force_state(SLEEPING)
        _step(bh, status="working")
        self.assertIn(bh.state, (WALKING, WORKING))
        self.assertNotEqual(bh.state, SLEEPING)


class TestSchedule(unittest.TestCase):
    def test_bedtime_triggers_sleep(self):
        _, _, time, _, bh = _make_behavior(hour=20.9)
        time.jump_hours(0.2)  # crosses 21:00
        _step(bh, steps=800)
        self.assertEqual(bh.state, SLEEPING)
        self.assertLess(bh.actor.pos[1], 700)

    def test_wake_at_six(self):
        _, _, time, _, bh = _make_behavior(hour=5.9)
        bh._force_state(SLEEPING)
        time.jump_hours(0.2)
        _step(bh, steps=10)
        self.assertEqual(bh.state, IDLE)


class TestHermesMapping(unittest.TestCase):
    def test_working_walks_to_computer(self):
        _, nav, _, _, bh = _make_behavior()
        _step(bh, status="working", steps=2000)
        self.assertEqual(bh.state, WORKING)
        computer = nav.poi("computer")
        self.assertLess(abs(bh.actor.pos[0] - computer[0]), 60)
        self.assertLess(abs(bh.actor.pos[1] - computer[1]), 60)

    def test_success_triggers_celebration(self):
        _, _, _, _, bh = _make_behavior()
        _step(bh, status="idle", event="success", steps=5)
        self.assertEqual(bh.state, CELEBRATING)

    def test_waiting_enters_waiting(self):
        _, _, _, _, bh = _make_behavior()
        bh._force_state(IDLE)
        _step(bh, status="waiting", steps=5)
        self.assertEqual(bh.state, WAITING)

    def test_waiting_takes_over_when_hermes_moves_on(self):
        # Reference behaviour: action_required (waiting) outranks other statuses.
        _, _, _, _, bh = _make_behavior()
        _step(bh, status="working", steps=2000)
        self.assertEqual(bh.state, WORKING)
        bh.update(0.1, HermesSnapshot(status="waiting"))
        self.assertEqual(bh.state, WAITING)

    def test_work_interrupts_celebration(self):
        _, _, _, _, bh = _make_behavior()
        _step(bh, status="idle", event="success", steps=5)
        self.assertEqual(bh.state, CELEBRATING)
        bh.update(0.1, HermesSnapshot(status="working"))
        self.assertIn(bh.state, (WALKING, WORKING))


if __name__ == "__main__":
    unittest.main()
