"""Wallpaper placement: map image (the desktop wallpaper) -> screen coordinates.

Windows stores how the wallpaper is displayed in the registry
(HKCU\\Control Panel\\Desktop: WallpaperStyle / TileWallpaper). We read it so the
pet's map coordinates land on the right screen pixels without the user having
to measure anything. A manual override is available in config display.wallpaper.
"""
from __future__ import annotations

from typing import Optional

from app.config import Config


def _registry_wallpaper_style() -> tuple[int, int]:
    """Return (wallpaper_style, tile) from the registry; defaults to (10, 0) = fill."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop") as key:
            style = int(winreg.QueryValueEx(key, "WallpaperStyle")[0])
            tile = int(winreg.QueryValueEx(key, "TileWallpaper")[0])
            return style, tile
    except Exception:
        return 10, 0


class WallpaperPlacement:
    """Maps map-pixel coordinates to screen coordinates for a wallpaper image."""

    def __init__(self, config: Config, screen_w: int, screen_h: int,
                 map_w: int, map_h: int) -> None:
        self.map_w = map_w
        self.map_h = map_h
        self.screen_w = screen_w
        self.screen_h = screen_h

        wp = config.get("display", "wallpaper", {})
        mode = str(wp.get("mode", "auto")).lower()
        cfg_scale = wp.get("scale")
        cfg_offset = wp.get("offset", [None, None])

        style, tile = _registry_wallpaper_style()
        if mode == "auto":
            if tile == 1:
                mode = "tile"
            else:
                mode = {0: "center", 2: "stretch", 6: "fit", 10: "fill", 22: "fill"}.get(style, "fill")

        if mode == "stretch":
            self.scale_x = screen_w / map_w
            self.scale_y = screen_h / map_h
            self.offset_x = 0.0
            self.offset_y = 0.0
            self.scale = min(self.scale_x, self.scale_y)
        elif mode == "fit":
            self.scale = min(screen_w / map_w, screen_h / map_h)
            self.scale_x = self.scale_y = self.scale
            self.offset_x = (screen_w - map_w * self.scale) / 2.0
            self.offset_y = (screen_h - map_h * self.scale) / 2.0
        elif mode == "fill":
            self.scale = max(screen_w / map_w, screen_h / map_h)
            self.scale_x = self.scale_y = self.scale
            self.offset_x = (screen_w - map_w * self.scale) / 2.0
            self.offset_y = (screen_h - map_h * self.scale) / 2.0
        elif mode == "tile":
            self.scale = self.scale_x = self.scale_y = 1.0
            self.offset_x = 0.0
            self.offset_y = 0.0
        else:  # center
            self.scale = self.scale_x = self.scale_y = 1.0
            self.offset_x = (screen_w - map_w) / 2.0
            self.offset_y = (screen_h - map_h) / 2.0

        if cfg_scale is not None:
            self.scale = self.scale_x = self.scale_y = float(cfg_scale)
        if cfg_offset and cfg_offset[0] is not None and cfg_offset[1] is not None:
            self.offset_x = float(cfg_offset[0])
            self.offset_y = float(cfg_offset[1])

    def map_to_screen(self, x: float, y: float) -> tuple[float, float]:
        return x * self.scale_x + self.offset_x, y * self.scale_y + self.offset_y

    def screen_to_map(self, sx: float, sy: float) -> tuple[float, float]:
        if self.scale_x == 0 or self.scale_y == 0:
            return (0.0, 0.0)
        return (sx - self.offset_x) / self.scale_x, (sy - self.offset_y) / self.scale_y

    def describe(self) -> str:
        return (f"wallpaper: map {self.map_w}x{self.map_h} -> screen {self.screen_w}x{self.screen_h} "
                f"scale=({self.scale_x:.4f},{self.scale_y:.4f}) offset=({self.offset_x:.0f},{self.offset_y:.0f})")
