"""Runtime configuration loaded from JSON."""
from dataclasses import dataclass
import json
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[2]

@dataclass
class Config:
    debug_mode: bool = True
    time_mode: str = "DEBUG_TIME"
    time_scale: float = 120.0
    walk_speed: float = 90.0
    run_speed: float = 180.0
    sleep_time: int = 1260
    wake_time: int = 360
    @classmethod
    def load(cls, path=None):
        p=Path(path) if path else PROJECT_ROOT / "data" / "runtime_config.json"
        if not p.exists(): return cls()
        values=json.loads(p.read_text(encoding="utf-8")); values["debug_mode"]=values.get("debug_mode",values.get("debug_overlay",True))
        for key in ('sleep_time','wake_time'):
            if isinstance(values.get(key), str):
                h,m=map(int,values[key].split(':')); values[key]=h*60+m
        return cls(**{k:v for k,v in values.items() if k in cls.__dataclass_fields__})
def load_config(path=None): return Config.load(path)
