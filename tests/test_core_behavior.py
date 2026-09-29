import unittest
import random

from calypso.behavior.manager import BehaviorManager
from calypso.behavior.fishing import FishingAction, FishingPhase
from calypso.behavior.states import State


class Character:
    position = (0, 0)
    running = False

    def set_path(self, path):
        self.path = path


class Navigation:
    points = {"computer": (1, 1), "computer_use": (1, 2),
              "bed": (2, 2), "fishing": (3, 3), "spawn": (0, 0)}

    def go_to(self, name, start):
        return [self.points[name]]


class Clock:
    night = False

    def advance(self, dt):
        return []

    def is_sleep_period(self):
        return self.night


class Computer:
    on = False

    def turn_on(self):
        self.on = True

    def turn_off(self):
        self.on = False


class BehaviorTests(unittest.TestCase):
    def setUp(self):
        self.character = Character()
        self.computer = Computer()
        self.clock = Clock()
        self.behavior = BehaviorManager(self.character, self.computer,
                                        self.clock, Navigation(),
                                        fishing=FishingAction(duration_range=(5.0, 5.0)))

    def test_fishing_runs_cast_wait_pull_then_leaves_rock(self):
        self.behavior.go_to("fishing")
        self.assertEqual(self.behavior.target, "fishing")
        self.behavior.arrived("fishing")
        self.assertEqual(self.behavior.state, State.FISHING)
        self.assertEqual(self.behavior.fishing.animation, "fish_cast")
        self.behavior.tick(0.7)
        self.assertEqual(self.behavior.fishing.phase, FishingPhase.WAIT)
        self.behavior.tick(3.6)
        self.assertEqual(self.behavior.fishing.animation, "fish_pull")
        self.behavior.tick(0.7)
        self.assertEqual(self.behavior.state, State.WALKING)
        self.assertEqual(self.behavior.target, "spawn")

    def test_default_fishing_wait_is_long_and_zero_phases_finish(self):
        action = FishingAction(duration_range=(10.0, 10.0))
        action.start()
        self.assertFalse(action.tick(.7))
        self.assertEqual(action.phase, FishingPhase.WAIT)
        self.assertFalse(action.tick(7.0))
        self.assertEqual(action.phase, FishingPhase.WAIT)
        self.assertFalse(action.tick(1.61))
        self.assertEqual(action.phase, FishingPhase.PULL)
        self.assertTrue(action.tick(.7))
        instant = FishingAction(duration_range=(0, 0), cast_seconds=0, pull_seconds=0)
        instant.start()
        self.assertTrue(instant.tick(0))

    def test_hermes_task_immediately_interrupts_fishing(self):
        self.behavior.go_to("fishing")
        self.behavior.arrived("fishing")
        self.behavior.set_task_active("hermes", True)
        self.assertEqual(self.behavior.state, State.WALKING)
        self.assertEqual(self.behavior.target, "computer_use")
        self.assertIsNone(self.behavior.fishing.phase)

    def test_sleep_period_interrupts_fishing(self):
        self.behavior.go_to("fishing")
        self.behavior.arrived("fishing")
        self.clock.night = True
        self.behavior.tick(0.1)
        self.assertEqual(self.behavior.target, "bed")
        self.assertIsNone(self.behavior.fishing.phase)

    def test_work_uses_separate_interaction_point_and_lights_computer_on_arrival(self):
        self.behavior.set_task_active("hermes", True)
        self.assertEqual(self.behavior.target, "computer_use")
        self.assertFalse(self.computer.on)
        self.behavior.arrived("computer_use")
        self.assertEqual(self.behavior.state, State.WORKING)
        self.assertTrue(self.computer.on)

    def test_debug_finish_does_not_cancel_active_hermes_session(self):
        self.behavior.set_task_active("hermes", True)
        self.behavior.task_started()
        self.behavior.arrived("computer_use")
        self.behavior.task_finished()
        self.assertTrue(self.behavior.task)
        self.assertEqual(self.behavior.state, State.WORKING)
        self.assertTrue(self.computer.on)
        self.behavior.set_task_active("hermes", False)
        self.assertFalse(self.behavior.task)
        self.assertFalse(self.computer.on)
        self.assertEqual(self.behavior.target, "spawn")

    def test_launch_at_night_goes_to_bed_and_wake_leaves_bed(self):
        self.clock.night = True
        self.behavior.tick(0.1)
        self.assertEqual(self.behavior.target, "bed")
        self.behavior.arrived("bed")
        self.assertEqual(self.behavior.state, State.SLEEPING)
        self.clock.night = False
        self.behavior.tick(0.1)
        self.assertEqual(self.behavior.target, "spawn")
        self.assertEqual(self.behavior.state, State.WALKING)

    def test_hermes_work_overrides_sleep_and_returns_to_bed(self):
        self.clock.night = True
        self.behavior.tick(0.1)
        self.behavior.arrived("bed")
        self.behavior.set_task_active("hermes", True)
        self.assertEqual(self.behavior.target, "computer_use")
        self.behavior.arrived("computer_use")
        self.behavior.set_task_active("hermes", False)
        self.assertEqual(self.behavior.target, "bed")
        self.assertFalse(self.computer.on)

    def test_random_roam_only_runs_while_idle(self):
        from calypso.behavior.scheduler import Scheduler
        scheduler = Scheduler(rng=random.Random(3), idle_range=(0, 0))
        behavior = BehaviorManager(self.character, self.computer, self.clock,
                                   Navigation(), scheduler=scheduler)
        behavior.tick(.1)
        self.assertEqual(behavior.state, State.WALKING)
        self.assertIn(behavior.target, ("fishing", "campfire", "spawn"))
        behavior.set_task_active("hermes", True)
        self.assertEqual(behavior.target, "computer_use")
        behavior.arrived("computer_use")
        behavior.tick(100)
        self.assertEqual(behavior.state, State.WORKING)
        self.assertEqual(behavior.target, "computer_use")
