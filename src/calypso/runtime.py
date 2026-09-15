"""Headless core runtime; UI layers only observe this object."""
from .navigation.manager import NavigationManager
from .character.controller import CharacterController
from .behavior.manager import BehaviorManager
from .behavior.states import State
from .objects.computer import ComputerController
from .time.time_manager import TimeManager
from .hermes.fake_bridge import FakeAgentBridge
from .behavior.scheduler import Scheduler
from .config import load_config

class Runtime:
    def __init__(self, navigation=None, character=None, time=None, config=None):
        cfg = config or load_config()
        self.navigation = navigation or NavigationManager()
        spawn = self.navigation.points.get("spawn", (1288, 743))
        self.character = character or CharacterController(position=spawn, speed=cfg.walk_speed, run_speed=cfg.run_speed)
        self.computer = ComputerController()
        self.time = time or TimeManager(mode=cfg.time_mode, time_scale=cfg.time_scale, sleep_minute=cfg.sleep_time, wake_minute=cfg.wake_time)
        self.behavior = BehaviorManager(self.character, self.computer, self.time, self.navigation, Scheduler())
        self.bridge = FakeAgentBridge(self.behavior)

    def go_to(self, name): self.behavior.go_to(name)
    def fake_task_start(self): self.bridge.fake_task_start()
    def fake_task_finish(self): self.bridge.fake_task_finish()

    def tick(self, dt):
        self.behavior.tick(dt)
        had_path = bool(self.character.path)
        self.character.tick(dt)
        if had_path and not self.character.path and self.behavior.target:
            target = self.behavior.target; self.behavior.target = None; self.behavior.arrived(target)

    @property
    def animation_intent(self):
        if self.behavior.state == State.SLEEPING: return "sleep"
        if self.behavior.state == State.WORKING: return "work"
        return ("walk_" if self.character.path else "idle_") + self.character.direction
