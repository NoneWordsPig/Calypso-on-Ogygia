"""Sprite sheet slicing + animation player (reference hermes-pet style).

The keeper spritesheet is a fixed 8x9 atlas of 192x208 frames. Each animation
state maps to one row with a known frame count (see config
resources.spritesheet_layout). Frames are rendered bottom-aligned so the
character's feet stay planted while walking.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QImage, QPixmap

try:
    from PIL import Image
    import numpy as np
except Exception:  # pragma: no cover - PIL is required
    Image = None
    np = None

ANIM_DEFAULT_LAYOUT: dict[str, Any] = {
    "columns": 8,
    "rows": 9,
    "frame_width": 192,
    "frame_height": 208,
    "states": [
        {"name": "idle", "row": 0, "frames": 6},
        {"name": "running-right", "row": 1, "frames": 8},
        {"name": "running-left", "row": 2, "frames": 8},
        {"name": "waving", "row": 3, "frames": 4},
        {"name": "jumping", "row": 4, "frames": 5},
        {"name": "failed", "row": 5, "frames": 8},
        {"name": "waiting", "row": 6, "frames": 6},
        {"name": "running", "row": 7, "frames": 6},
        {"name": "review", "row": 8, "frames": 6},
    ],
}


def _pil_image_to_qimage(pil_image) -> QImage:
    img = pil_image.convert("RGBA")
    data = img.tobytes("raw", "RGBA")
    qimg = QImage(data, img.width, img.height, img.width * 4, QImage.Format.Format_RGBA8888)
    return qimg.copy()


class SpriteSheet:
    """Loads a spritesheet image and slices it into animation frame pixmaps."""

    def __init__(self, path: Path, layout: Optional[dict[str, Any]] = None) -> None:
        self.path = Path(path)
        layout = layout or ANIM_DEFAULT_LAYOUT
        self.columns = int(layout["columns"])
        self.rows = int(layout["rows"])
        self.frame_width = int(layout["frame_width"])
        self.frame_height = int(layout["frame_height"])
        self.states: dict[str, dict[str, int]] = {}
        for st in layout.get("states", []):
            self.states[str(st["name"])] = {"row": int(st["row"]), "frames": int(st["frames"])}
        self._frames: dict[str, list[QPixmap]] = {}
        self._load()

    def _load(self) -> None:
        image = Image.open(self.path).convert("RGBA")
        w, h = image.size
        if w < self.frame_width * self.columns or h < self.frame_height * self.rows:
            raise ValueError(f"spritesheet {self.path} too small for layout {w}x{h}")
        for name, spec in self.states.items():
            row = spec["row"]
            frames: list[QPixmap] = []
            for col in range(spec["frames"]):
                box = (col * self.frame_width, row * self.frame_height,
                       (col + 1) * self.frame_width, (row + 1) * self.frame_height)
                qimg = _pil_image_to_qimage(image.crop(box))
                frames.append(QPixmap.fromImage(qimg))
            self._frames[name] = frames

    def frame(self, name: str, index: int = 0) -> QPixmap:
        frames = self._frames.get(name)
        if not frames:
            frames = self._frames.get("idle") or []
        if not frames:
            return QPixmap()
        return frames[index % len(frames)]

    def frame_count(self, name: str) -> int:
        frames = self._frames.get(name)
        return len(frames) if frames else 1

    def anim_names(self) -> list[str]:
        return list(self.states.keys())


class AnimationPlayer:
    """Simple frame-based animation player keyed by state name."""

    def __init__(self, sheet: SpriteSheet, fps_by_anim: dict[str, float] | None = None,
                 default_fps: float = 6.0) -> None:
        self.sheet = sheet
        self.fps_by_anim = dict(fps_by_anim or {})
        self.default_fps = default_fps
        self.state = "idle"
        self.frame = 0
        self._accum = 0.0

    def set_state(self, name: str) -> None:
        if name != self.state:
            self.state = name
            self.frame = 0
            self._accum = 0.0

    def fps(self, name: str | None = None) -> float:
        return self.fps_by_anim.get(name or self.state, self.default_fps)

    def update(self, dt: float) -> None:
        fps = self.fps()
        if fps <= 0:
            return
        self._accum += dt
        period = 1.0 / fps
        while self._accum >= period:
            self._accum -= period
            self.frame = (self.frame + 1) % self.sheet.frame_count(self.state)

    def current_pixmap(self) -> QPixmap:
        return self.sheet.frame(self.state, self.frame)


def anchor_point(frame: QPixmap, scale: float = 1.0) -> QPointF:
    """Bottom-center anchor for drawing a sprite (feet planted at origin)."""
    return QPointF(frame.width() * scale / 2.0, frame.height() * scale)
