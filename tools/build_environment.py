"""Bake small day/night animation strips from the painted wallpaper.

The runtime only selects a frame from each strip.  Tree crowns and falling
water deform their original painted pixels; cliffs, trunks and tile borders
stay aligned with the wallpaper.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from math import pi, sin, sqrt
from pathlib import Path
import sys

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from calypso.desktop.wallpaper import night_map_image  # noqa: E402


SOURCE = ROOT / "assets" / "map" / "map.png"
DEST = ROOT / "assets" / "environment"
TREE_FRAMES = 12
WATER_FRAMES = 10
FIRE_FRAMES = 8


@dataclass(frozen=True)
class Crown:
    x: int
    y: int
    rx: int
    ry: int
    sway: float
    phase: float = 0.0


TREE_AREAS = (
    ("west_trees", (350, 40, 355, 345), (
        Crown(557, 129, 55, 45, 3.0, 0.1),
        Crown(486, 182, 61, 53, 3.4, 0.5),
        Crown(452, 256, 65, 59, 3.6, 1.0),
        Crown(644, 129, 34, 42, 2.6, 1.4),
        Crown(650, 220, 31, 44, 2.7, 0.8),
    )),
    ("north_trees", (620, 0, 325, 104), (
        Crown(699, 13, 45, 41, 2.8, 0.3),
        Crown(786, 15, 51, 45, 3.0, 1.1),
        Crown(886, 10, 50, 39, 2.8, 1.8),
    )),
    ("east_pines", (940, 0, 265, 214), (
        Crown(986, 54, 26, 50, 2.7, 0.2),
        Crown(1038, 82, 31, 58, 3.0, 0.9),
        Crown(1084, 94, 29, 54, 2.8, 1.6),
        Crown(1128, 111, 28, 57, 2.8, 0.6),
        Crown(1161, 133, 23, 55, 2.4, 1.2),
    )),
    ("bed_tree", (1020, 325, 210, 205), (
        Crown(1126, 423, 69, 57, 3.7, 0.4),
    )),
    ("south_pines", (780, 465, 120, 215), (
        Crown(839, 545, 32, 54, 2.8, 0.4),
        Crown(845, 606, 33, 52, 2.9, 1.2),
    )),
)

WATER_AREAS = (
    ("upper_fall", (788, 49, 82, 140), (805, 62, 31, 96)),
    ("lower_fall", (991, 588, 79, 133), (1010, 609, 43, 92)),
)


def _edge_alpha(width, height, border=6):
    """Feather only the outside tile edge where the wallpaper shows through."""
    alpha = Image.new("L", (width, height))
    pixels = alpha.load()
    for y in range(height):
        for x in range(width):
            distance = min(x, y, width - 1 - x, height - 1 - y)
            pixels[x, y] = min(255, round(255 * distance / border))
    return alpha


def _sample_pair(day, night, indices):
    size = day.size
    day_pixels = list(day.getdata())
    night_pixels = list(night.getdata())
    result = []
    for source in (day_pixels, night_pixels):
        frame = Image.new("RGB", size)
        frame.putdata([source[index] for index in indices])
        result.append(frame)
    return result


def _tree_mapping(rect, crowns, frame):
    x0, y0, width, height = rect
    count = width * height
    shift_x = [0.0] * count
    shift_y = [0.0] * count
    angle = 2 * pi * frame / TREE_FRAMES
    for crown in crowns:
        # A crown moves as a whole. The displacement fades in the surrounding
        # air/grass, well beyond its silhouette, and is zero at tile borders.
        wind = crown.sway * (sin(angle + crown.phase) - sin(crown.phase)) * 0.65
        if abs(wind) < 1e-9:
            continue
        cx, cy = crown.x - x0, crown.y - y0
        xmin = max(0, int(cx - crown.rx * 1.35))
        xmax = min(width, int(cx + crown.rx * 1.35) + 1)
        ymin = max(0, int(cy - crown.ry * 1.35))
        ymax = min(height, int(cy + crown.ry * 1.35) + 1)
        for y in range(ymin, ymax):
            ny = (y - cy) / crown.ry
            row = y * width
            for x in range(xmin, xmax):
                nx = (x - cx) / crown.rx
                radius = sqrt(nx * nx + ny * ny)
                if radius >= 1.35:
                    continue
                if radius <= 1:
                    weight = 1.0
                else:
                    t = (radius - 1) / .35
                    weight = 1 - t * t * (3 - 2 * t)
                shift_x[row + x] += wind * weight
                shift_y[row + x] += wind * .18 * weight
    indices = []
    for y in range(height):
        row = y * width
        for x in range(width):
            index = row + x
            source_x = max(0, min(width - 1, round(x - shift_x[index])))
            source_y = max(0, min(height - 1, round(y - shift_y[index])))
            indices.append(source_y * width + source_x)
    return indices


def _tree_frames(day, night, rect, crowns):
    box = (rect[0], rect[1], rect[0] + rect[2], rect[1] + rect[3])
    day_crop, night_crop = day.crop(box), night.crop(box)
    for frame in range(TREE_FRAMES):
        yield _sample_pair(day_crop, night_crop, _tree_mapping(rect, crowns, frame))


def _water_frame(source, rect, core, frame):
    x0, y0, width, height = rect
    left, top, water_width, water_height = core
    image = source.crop((x0, y0, x0 + width, y0 + height)).copy()
    result = image.load()
    pixels = source.load()
    phase = 2 * pi * frame / WATER_FRAMES
    for y in range(top, top + water_height):
        vertical = min(1.0, (y - top) / 9, (top + water_height - 1 - y) / 9)
        for x in range(left, left + water_width):
            horizontal = min(1.0, (x - left) / 4,
                             (left + water_width - 1 - x) / 4)
            opacity = max(0.0, horizontal) * max(0.0, vertical)
            if opacity == 0:
                continue
            # Traveling ripples deform the painted water itself. No repeating
            # strip or drawn white streak can introduce a horizontal seam.
            wave = (3.0 * sin(2 * pi * (y - top) / 26 - phase)
                    + 1.1 * sin(2 * pi * (y - top) / 13 - 2 * phase))
            sx = round(x - .8 * sin(2 * pi * (y - top) / 31 - phase) * opacity)
            moving_y = round(y - wave * opacity)
            original = pixels[x, y]
            moving = pixels[sx, moving_y]
            blend = .9 * opacity
            result[x - x0, y - y0] = tuple(
                round(a * (1 - blend) + b * blend)
                for a, b in zip(original, moving)
            )
    return image


def _fire_frame(source, frame):
    rect = (1046, 185, 57, 68)
    x0, y0, width, height = rect
    image = source.crop((x0, y0, x0 + width, y0 + height)).copy()
    output, pixels = image.load(), source.load()
    angle = 2 * pi * frame / FIRE_FRAMES
    dx, dy = sin(angle) * 1.8, cos(angle) * 1.7
    for y in range(y0, y0 + height):
        for x in range(x0, x0 + width):
            radius = ((x - 1074) / 16) ** 2 + ((y - 219) / 22) ** 2
            if radius >= 1.45:
                continue
            opacity = 1.0 if radius <= .85 else max(0.0, (1.45 - radius) / .6)
            sx = max(x0, min(x0 + width - 1, round(x - dx * opacity)))
            sy = max(y0, min(y0 + height - 1, round(y - dy * opacity)))
            old, moving = pixels[x, y], pixels[sx, sy]
            brightness = 1 + .12 * sin(angle + .7)
            output[x - x0, y - y0] = tuple(
                max(0, min(255, round((a * (1 - opacity) + b * opacity) * brightness)))
                for a, b in zip(old, moving)
            )
    return image


def _save_strips(name, rect, frames, step):
    frames = list(frames)
    count = len(frames)
    width, height = rect[2:]
    alpha = _edge_alpha(width, height)
    for palette_index, palette in enumerate(("day", "night")):
        strip = Image.new("RGBA", (width * count, height))
        for index, pair in enumerate(frames):
            tile = pair[palette_index].convert("RGBA")
            tile.putalpha(alpha)
            strip.paste(tile, (index * width, 0))
        directory = DEST / palette
        directory.mkdir(parents=True, exist_ok=True)
        strip.save(directory / f"{name}.png", optimize=True)
    return {"name": name, "rect": list(rect), "frames": count,
            "step": step, "day": f"day/{name}.png", "night": f"night/{name}.png"}


def build():
    with Image.open(SOURCE) as original:
        day = original.convert("RGB")
    night = night_map_image(day)
    effects = []
    for name, rect, crowns in TREE_AREAS:
        effects.append(_save_strips(name, rect, _tree_frames(day, night, rect, crowns), 2))
    for name, rect, core in WATER_AREAS:
        frames = ((_water_frame(day, rect, core, index),
                   _water_frame(night, rect, core, index))
                  for index in range(WATER_FRAMES))
        effects.append(_save_strips(name, rect, frames, 1))
    fire_rect = (1046, 185, 57, 68)
    effects.append(_save_strips("campfire", fire_rect,
                                ((_fire_frame(day, index), _fire_frame(night, index))
                                 for index in range(FIRE_FRAMES)), 1))
    manifest = {"version": 1, "source": "assets/map/map.png",
                "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                "source_size": list(day.size), "effects": effects}
    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build()
