"""Local priority-based life and task behaviour."""
import logging
from .states import State

LOGGER = logging.getLogger(__name__)

class BehaviorManager:
    def __init__(self, character, computer, time, navigation=None, scheduler=None):
        self.character, self.computer = character, computer
        self.time, self.navigation, self.scheduler = time, navigation, scheduler
        self.state, self.task, self.target, self.sleep_due = State.IDLE, False, None, False

    def _state(self, value):
        if value != self.state:
            LOGGER.info("behavior state: %s -> %s", self.state.value, value.value)
            self.state = value

    def go_to(self, name):
        if self.navigation is None:
            raise RuntimeError("navigation is required")
        self.target = name
        self._state(State.WALKING)
        self.character.set_path(self.navigation.go_to(name, self.character.position))

    def task_started(self, task_id=None, metadata=None):
        if self.task: return
        self.task, self.character.running = True, True
        self.computer.turn_off()
        self.go_to("computer")

    def task_finished(self, task_id=None, result=None):
        if not self.task: return
        self.task, self.character.running = False, False
        self.computer.turn_off()
        self.go_to("bed" if self.sleep_due or self.time.is_sleep_period() else "spawn")

    def arrived(self, name):
        if name == "computer" and self.task:
            self.computer.turn_on(); self.character.running = False; self._state(State.WORKING)
        elif name == "bed":
            self.sleep_due = False; self._state(State.SLEEPING)
        else:
            self._state(State.IDLE)
            if self.scheduler: self.scheduler.reset()

    def tick(self, dt):
        for event in self.time.advance(dt):
            if event == "sleep":
                self.sleep_due = True
                if not self.task and self.state != State.SLEEPING: self.go_to("bed")
            elif event == "wake" and self.state == State.SLEEPING:
                self.target = None; self.character.set_path([]); self._state(State.IDLE)
        if self.state == State.IDLE and not self.task and not self.time.is_sleep_period() and self.scheduler:
            if self.scheduler.tick(dt) == "WALKING":
                choices = [n for n in ("fishing", "campfire", "spawn") if n in self.navigation.points]
                if choices: self.go_to(self.scheduler.rng.choice(choices))
