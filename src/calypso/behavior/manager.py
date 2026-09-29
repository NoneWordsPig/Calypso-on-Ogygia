"""Priority rules: active Hermes work, local sleep, then roaming."""

import logging

from .fishing import FishingAction
from .states import ACTIVITIES, State


LOGGER = logging.getLogger(__name__)


class BehaviorManager:
    def __init__(self, character, computer, time, navigation=None, scheduler=None,
                 fishing=None):
        self.character = character
        self.computer = computer
        self.time = time
        self.navigation = navigation
        self.scheduler = scheduler
        self.fishing = fishing or FishingAction(rng=scheduler.rng if scheduler else None)
        self.state = State.IDLE
        self._task_sources = set()
        self.target = None
        self._arrival_handlers = {
            ACTIVITIES[State.FISHING].destination: self._arrive_fish,
            ACTIVITIES[State.WORKING].destination: self._arrive_work,
            ACTIVITIES[State.SLEEPING].destination: self._arrive_sleep,
        }

    @property
    def task(self):
        return bool(self._task_sources)

    def _state(self, value):
        if value != self.state:
            LOGGER.info("behavior state: %s -> %s", self.state.value, value.value)
            self.state = value

    def go_to(self, name):
        if self.navigation is None:
            raise RuntimeError("navigation is required")
        path = self.navigation.go_to(name, self.character.position)
        self.fishing.cancel()
        self.target = name
        self._state(State.WALKING)
        self.character.set_path(path)
        if not self.character.path:
            self.target = None
            self.arrived(name)

    def set_task_active(self, source, active, task_id=None):
        """Keep independent Hermes and local debug requests from cancelling each other."""
        was_active = self.task
        if active:
            self._task_sources.add(source)
        else:
            self._task_sources.discard(source)
        if self.task == was_active:
            return
        if self.task:
            self.character.running = True
            self.computer.turn_off()
            self.go_to(ACTIVITIES[State.WORKING].destination)
        else:
            self.character.running = False
            self.computer.turn_off()
            self.go_to(ACTIVITIES[State.SLEEPING].destination
                       if self.time.is_sleep_period() else "spawn")

    def task_started(self, task_id=None, metadata=None):
        self.set_task_active("manual", True, task_id)

    def task_finished(self, task_id=None, result=None):
        self.set_task_active("manual", False, task_id)

    def arrived(self, name):
        self._arrival_handlers.get(name, self._arrive_idle)()

    def _arrive_fish(self):
        if self.task:
            self.go_to(ACTIVITIES[State.WORKING].destination)
        elif self.time.is_sleep_period():
            self.go_to(ACTIVITIES[State.SLEEPING].destination)
        else:
            self.fishing.start()
            self._state(State.FISHING)

    def _arrive_work(self):
        if self.task:
            self.character.running = False
            self.computer.turn_on()
            self._state(State.WORKING)
        else:
            self._arrive_idle()

    def _arrive_sleep(self):
        if not self.task and self.time.is_sleep_period():
            self._state(State.SLEEPING)
        else:
            self._arrive_idle()

    def _arrive_idle(self):
        self._state(State.IDLE)
        if self.scheduler:
            self.scheduler.reset()

    def _sync_sleep(self):
        if self.task:
            return
        bed = ACTIVITIES[State.SLEEPING].destination
        if self.time.is_sleep_period():
            if self.state != State.SLEEPING and self.target != bed:
                self.go_to(bed)
        elif self.state == State.SLEEPING or self.target == bed:
            self.go_to("spawn")

    def tick(self, dt):
        self.time.advance(dt)
        self._sync_sleep()
        if self.state == State.FISHING:
            if self.fishing.tick(dt):
                self.go_to("spawn")
            return
        if self.state == State.IDLE and not self.task and not self.time.is_sleep_period() and self.scheduler:
            if self.scheduler.tick(dt) == "WALKING":
                choices = [name for name in ("fishing", "campfire", "spawn")
                           if name in self.navigation.points]
                if choices:
                    self.go_to(self.scheduler.rng.choice(choices))
