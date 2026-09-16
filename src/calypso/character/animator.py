import json
from pathlib import Path
from ..config import PROJECT_ROOT

class Animator:
    def __init__(self, manifest='assets/calypso/manifest.json', fps=8.0, run_factor=1.8,
                 idle_fps=2.0, work_fps=6.0, sleep_fps=1.0):
        path=Path(manifest)
        if not path.is_absolute(): path=PROJECT_ROOT/path
        self.manifest_path=str(path.resolve()); self.manifest=json.loads(path.read_text()) if path.exists() else {'animations':{}}
        self.fps=float(fps); self.run_factor=float(run_factor); self.idle_fps=float(idle_fps); self.work_fps=float(work_fps); self.sleep_fps=float(sleep_fps); self.state='idle_down'; self.frame=0; self._elapsed=0.0
    def _entry(self):
        entry=self.manifest.get('animations',{}).get(self.state,{})
        return self.manifest.get('animations',{}).get(entry['alias'],{}) if 'alias' in entry else entry
    def select(self, direction='down', walking=False):
        state=('walk_' if walking else 'idle_')+direction
        if state != self.state: self.state=state; self.frame=0; self._elapsed=0.0
        return self.state
    def set_state(self, state):
        if state != self.state: self.state=state; self.frame=0; self._elapsed=0.0
    def tick(self, dt, running=False):
        self._elapsed += max(0.0,float(dt))*(self.run_factor if running else 1.0)
        rate = self.idle_fps if self.state.startswith('idle_') else self.sleep_fps if self.state == 'sleep' else self.work_fps if self.state == 'work' else self.fps
        step=int(self._elapsed*rate)
        if step: self.frame=(self.frame+step)%max(1,self._entry().get('count',4)); self._elapsed-=step/rate
        return self.frame
    def frame_path(self):
        frames=self._entry().get('frames',[])
        return str((Path(self.manifest_path).parent / frames[self.frame%len(frames)]).resolve()) if frames else None
