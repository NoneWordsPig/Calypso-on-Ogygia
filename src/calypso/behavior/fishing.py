"""The short, interruptible cast / wait / pull fishing action."""

import random
from enum import Enum


class FishingPhase(str, Enum):
    CAST = "cast"
    WAIT = "wait"
    PULL = "pull"


class FishingAction:
    def __init__(self, rng=None, duration_range=(10.0, 20.0),
                 cast_seconds=0.7, pull_seconds=0.7):
        self.rng = rng or random.Random()
        self.duration_range = duration_range
        self.cast_seconds = max(0.0, float(cast_seconds))
        self.pull_seconds = max(0.0, float(pull_seconds))
        self.cancel()

    @property
    def animation(self):
        return f"fish_{self.phase.value}" if self.phase else None

    def start(self):
        total = max(0.0, self.rng.uniform(*self.duration_range))
        self.phase = FishingPhase.CAST
        self.remaining = self.cast_seconds
        self.wait_seconds = max(0.0, total - self.cast_seconds - self.pull_seconds)

    def cancel(self):
        self.phase = None
        self.remaining = 0.0
        self.wait_seconds = 0.0

    def tick(self, dt):
        """Return true when the cast, wait, and pull have all completed."""
        if self.phase is None:
            return False
        elapsed = max(0.0, float(dt))
        while elapsed >= self.remaining:
            elapsed -= self.remaining
            if self.phase == FishingPhase.CAST:
                self.phase = FishingPhase.WAIT
                self.remaining = self.wait_seconds
            elif self.phase == FishingPhase.WAIT:
                self.phase = FishingPhase.PULL
                self.remaining = self.pull_seconds
            else:
                self.cancel()
                return True
        self.remaining -= elapsed
        return False
