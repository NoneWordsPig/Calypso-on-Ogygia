"""Delta-time character movement using feet-centered world coordinates."""
from math import hypot
class CharacterController:
    def __init__(self, position=(1288.0,743.0), speed=90.0, run_speed=180.0):
        self.position=tuple(map(float,position)); self.speed=float(speed); self.run_speed=float(run_speed)
        self.running=False; self.direction="down"; self.path=[]
    @property
    def feet_position(self): return self.position
    def set_path(self,path): self.path=list(path)
    def follow(self,target,dt):
        dx,dy=target[0]-self.position[0],target[1]-self.position[1]; d=hypot(dx,dy)
        if d<1e-6: self.position=tuple(map(float,target)); return True
        self.direction=("right" if abs(dx)>=abs(dy) and dx>0 else "left" if abs(dx)>=abs(dy) else "down" if dy>0 else "up")
        step=(self.run_speed if self.running else self.speed)*max(0,float(dt))
        if step>=d: self.position=tuple(map(float,target)); return True
        self.position=(self.position[0]+dx/d*step,self.position[1]+dy/d*step); return False
    def tick(self,dt):
        remaining = max(0.0, float(dt))
        while self.path and remaining > 0:
            target = self.path[0]
            distance = hypot(target[0] - self.position[0], target[1] - self.position[1])
            speed = self.run_speed if self.running else self.speed
            if distance <= 1e-6:
                self.position = tuple(map(float, target))
                self.path.pop(0)
                continue
            used = distance / speed
            if used <= remaining:
                self.follow(target, used)
                self.path.pop(0)
                remaining -= used
            else:
                self.follow(target, remaining)
                remaining = 0.0
        return not self.path
