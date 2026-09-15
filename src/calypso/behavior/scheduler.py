import random
class Scheduler:
    def __init__(self,rng=None,idle_range=(6,15)):
        self.rng=rng or random.Random(); self.idle_range=idle_range
        self.reset()
    def tick(self,dt):
        self.remaining-=dt
        if self.remaining<=0:
            self.remaining=self.rng.uniform(*self.idle_range); return 'WALKING'
        return 'IDLE'
    def reset(self):
        self.remaining = self.rng.uniform(*self.idle_range)
