"""Configuration loader for Calypso's Ogygia.

Reads data/config.json once and exposes typed accessors, mirroring the draft's
config.gd. All paths are resolved relative to the repository root.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "data" / "config.json"


class Config:
    def __init__(self, data: dict[str, Any], root: Path = ROOT) -> None:
        self.data = data
        self.root = root

    @classmethod
    def load(cls, path: Path | str | None = None) -> "Config":
        p = Path(path) if path else CONFIG_PATH
        data = json.loads(Path(p).read_text(encoding="utf-8"))
        return cls(data)

    def get(self, section: str, key: str, default: Any = None) -> Any:
        sec = self.data.get(section)
        if not isinstance(sec, dict):
            return default
        return sec.get(key, default)

    def resource_path(self, key: str, default: str = "") -> Path:
        raw = self.get("resources", key, default)
        return self.root / raw if raw else self.root

    def section(self, name: str) -> dict[str, Any]:
        sec = self.data.get(name)
        return sec if isinstance(sec, dict) else {}
