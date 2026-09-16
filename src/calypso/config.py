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
    hermes_provider: str = "registry"
    hermes_registry_root: str = "%LOCALAPPDATA%/hermes"
    hermes_http_url: str = "http://127.0.0.1:17787/api/pet/attention"
    hermes_timeout: float = 2.0
    hermes_poll_seconds: float = 1.0
    character_height: int = 88
    computer_height: int = 48
    sleep_height: int = 38
    sprite_manifest: str = "assets/calypso_v2/manifest.json"
    @classmethod
    def load(cls, path=None):
        p=Path(path) if path else PROJECT_ROOT / "data" / "runtime_config.json"
        if not p.exists(): return cls()
        values=json.loads(p.read_text(encoding="utf-8")); values["debug_mode"]=values.get("debug_mode",values.get("debug_overlay",True))
        for key in ('sleep_time','wake_time'):
            if isinstance(values.get(key), str):
                h,m=map(int,values[key].split(':')); values[key]=h*60+m
        # Accept both the flat runtime schema and the nested hermes schema.
        hermes = values.get("hermes", {}) if isinstance(values.get("hermes"), dict) else {}
        values.setdefault("hermes_provider", hermes.get("provider", cls.hermes_provider))
        values.setdefault("hermes_registry_root", hermes.get("registry_root", cls.hermes_registry_root))
        values.setdefault("hermes_http_url", hermes.get("http_url", cls.hermes_http_url))
        values.setdefault("hermes_timeout", hermes.get("timeout", 2.0))
        values.setdefault("hermes_poll_seconds", hermes.get("poll_seconds", 1.0))
        return cls(**{k:v for k,v in values.items() if k in cls.__dataclass_fields__})
def load_config(path=None): return Config.load(path)
