"""Keep the Windows wallpaper in sync with the local day/night period."""

from __future__ import annotations

import ctypes
import hashlib
import logging
from math import hypot
import os
from pathlib import Path

from PIL import Image

from ..config import PROJECT_ROOT
from .lighting import night_grade


LOGGER = logging.getLogger(__name__)
DAY_MAP = PROJECT_ROOT / "assets" / "map" / "map.png"
NIGHT_MAP = PROJECT_ROOT / "logs" / "wallpaper_night.bmp"
FIRE_CENTER = (1073, 223)  # Pixel position of the painted flame in map.png.


def _light_campfire(day, night, center=FIRE_CENTER, radius=90):
    """Keep the painted flame bright and add a soft warm pool of light."""
    source = day.load()
    target = night.load()
    cx, cy = center
    for y in range(max(0, cy - radius), min(day.height, cy + radius + 1)):
        for x in range(max(0, cx - radius), min(day.width, cx + radius + 1)):
            distance = hypot(x - cx, y - cy)
            if distance >= radius:
                continue
            weight = 0.85 * (1 - distance / radius) ** 1.5
            red, green, blue = source[x, y]
            lit = (min(255, int(red * 1.12 + 35)),
                   min(255, int(green * .88 + 24)),
                   min(255, int(blue * .45 + 6)))
            base = target[x, y]
            target[x, y] = tuple(round(base[i] * (1 - weight) + lit[i] * weight)
                                 for i in range(3))


def make_night_map(source=DAY_MAP, destination=NIGHT_MAP):
    """Apply a fixed palette change; every landmark stays at its source pixel."""
    source, destination = Path(source), Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as original:
        day = original.convert("RGB")
        night = night_grade(day)
        _light_campfire(day, night)
        night.save(destination, format="BMP")
    return destination


def current_wallpaper():
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop") as key:
        value, _ = winreg.QueryValueEx(key, "WallPaper")
    return Path(value)


def set_wallpaper(path):
    if os.name != "nt":
        raise OSError("wallpaper switching requires Windows")
    # SPI_SETDESKWALLPAPER, SPIF_UPDATEINIFILE | SPIF_SENDCHANGE.
    if not ctypes.windll.user32.SystemParametersInfoW(20, 0, str(path), 3):
        raise ctypes.WinError()


def _same_file_content(left, right):
    try:
        left, right = Path(left), Path(right)
        if left.resolve() == right.resolve():
            return True
        if left.stat().st_size != right.stat().st_size:
            return False
        def digest(path):
            with path.open("rb") as handle:
                return hashlib.file_digest(handle, "sha256").digest()
        return digest(left) == digest(right)
    except OSError:
        return False


class WallpaperSwitcher:
    """Only switch a wallpaper matching this map; preserve the user's path."""

    def __init__(self, day_map=DAY_MAP, night_map=NIGHT_MAP,
                 getter=current_wallpaper, setter=set_wallpaper):
        self.day_map = Path(day_map)
        self.night_map = Path(night_map)
        self.getter = getter
        self.setter = setter
        self.original = None
        try:
            current = self.getter()
            if _same_file_content(current, self.day_map):
                self.original = Path(current)
            elif Path(current).resolve() == self.night_map.resolve():
                # Recover after an unclean exit, when the generated night map remains.
                self.original = self.day_map
        except (OSError, ImportError, TypeError) as exc:
            LOGGER.warning("wallpaper detection unavailable: %s", exc)

    def sync(self, night):
        if self.original is None:
            return False
        try:
            current = Path(self.getter())
            if night:
                if current.resolve() == self.night_map.resolve():
                    return True
                if not _same_file_content(current, self.day_map):
                    return False  # The user selected another wallpaper.
                make_night_map(self.day_map, self.night_map)
                self.setter(self.night_map)
                LOGGER.info("night wallpaper active")
            elif current.resolve() == self.night_map.resolve():
                self.setter(self.original)
                LOGGER.info("day wallpaper restored")
            return True
        except (OSError, ImportError, TypeError) as exc:
            LOGGER.warning("wallpaper switch failed: %s", exc)
            return False

    def close(self):
        self.sync(False)
