"""Show pre-baked map texture animations in small click-through windows."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QWidget

from ..config import PROJECT_ROOT
from .wallpaper import DAY_MAP
from .window_styles import apply_native_styles


ASSETS = PROJECT_ROOT / "assets" / "environment"


def wallpaper_style():
    """Read the style used by Windows to place the current wallpaper."""
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop") as key:
            style = int(winreg.QueryValueEx(key, "WallpaperStyle")[0])
            tiled = int(winreg.QueryValueEx(key, "TileWallpaper")[0])
        return "tile" if tiled else style
    except (ImportError, OSError, ValueError):
        return 10


class WallpaperPlacement:
    """Map pixel to logical screen pixel, including the wallpaper's crop/offset."""

    def __init__(self, transform, style=None):
        self.style = wallpaper_style() if style is None else style
        source_w, source_h = transform.source_size
        physical_w, physical_h = transform.actual_primary_physical
        dpi = transform.dpi
        if self.style == 2:  # Stretch
            scale_x, scale_y = physical_w / source_w, physical_h / source_h
        elif self.style == 6:  # Fit
            scale_x = scale_y = min(physical_w / source_w, physical_h / source_h)
        elif self.style == 0:  # Center
            scale_x = scale_y = 1.0
        else:  # Fill and unknown styles
            scale_x = scale_y = max(physical_w / source_w, physical_h / source_h)
        self.scale_x = scale_x / dpi
        self.scale_y = scale_y / dpi
        self.offset_x = (physical_w - source_w * scale_x) / (2 * dpi)
        self.offset_y = (physical_h - source_h * scale_y) / (2 * dpi)

    @property
    def supported(self):
        # Tiling repeats the map; Span uses the entire virtual desktop.
        return self.style not in ("tile", 22)

    def point(self, x, y):
        return self.offset_x + x * self.scale_x, self.offset_y + y * self.scale_y


class TextureWindow(QWidget):
    """One bounded source rectangle; each paint draws one strip frame."""

    def __init__(self, placement, asset_root: Path, spec: dict):
        super().__init__()
        self.name = spec["name"]
        self.source_rect = spec["rect"]
        self.frame_count = spec["frames"]
        self.step = spec["step"]
        self.frame = 0
        self.night = False
        self.strips = (QPixmap(str(asset_root / spec["day"])),
                       QPixmap(str(asset_root / spec["night"])))
        x, y, width, height = self.source_rect
        if any(strip.isNull() or strip.size().width() != width * self.frame_count
               or strip.size().height() != height for strip in self.strips):
            raise ValueError(f"Invalid environment texture strip: {self.name}")
        left, top = placement.point(x, y)
        right, bottom = placement.point(x + width, y + height)
        self.setGeometry(round(left), round(top),
                         max(1, round(right) - round(left)),
                         max(1, round(bottom) - round(top)))
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool |
                            Qt.WindowDoesNotAcceptFocus | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        apply_native_styles(self, click_through=True)

    def advance(self, tick):
        if tick % self.step == 0:
            self.frame = (tick // self.step) % self.frame_count
            self.update()

    def set_night(self, night):
        if self.night != bool(night):
            self.night = bool(night)
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.transparent)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        width, height = self.source_rect[2:]
        painter.drawPixmap(QRectF(self.rect()), self.strips[self.night],
                           QRectF(self.frame * width, 0, width, height))
        painter.end()


class EnvironmentAnimator:
    """A single 10 Hz timer for eight small, pre-rendered texture strips."""

    def __init__(self, transform, map_path=DAY_MAP, asset_root=ASSETS, parent=None):
        self.placement = WallpaperPlacement(transform)
        asset_root = Path(asset_root)
        manifest = json.loads((asset_root / "manifest.json").read_text(encoding="utf-8"))
        with Path(map_path).open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        self.source_matches = (manifest["source_sha256"] == digest and
                               tuple(manifest["source_size"]) == transform.source_size)
        self.windows = [TextureWindow(self.placement, asset_root, spec)
                        for spec in manifest["effects"]]
        self.timer = QTimer(parent)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self._advance)
        self.tick = 0
        self.active = False

    def set_active(self, active):
        active = bool(active and self.placement.supported and self.source_matches)
        if active == self.active:
            return
        self.active = active
        if active:
            for window in self.windows:
                window.show()
            self.timer.start()
        else:
            self.timer.stop()
            for window in self.windows:
                window.hide()

    def set_night(self, night):
        for window in self.windows:
            window.set_night(night)

    def _advance(self):
        self.tick += 1
        for window in self.windows:
            window.advance(self.tick)

    def close(self):
        self.set_active(False)
        for window in self.windows:
            window.close()
