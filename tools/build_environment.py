"""Bake independent tree, waterfall and fire sprite strips for both map palettes.

The wallpaper is a painted landscape with no trees or falling water. Every
moving subject is rendered into a transparent strip before the app starts.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from math import hypot, pi, sin
from pathlib import Path
import sys

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from calypso.desktop.lighting import night_grade  # noqa: E402
from calypso.desktop.wallpaper import night_map_image  # noqa: E402


SOURCE = ROOT / "assets" / "map" / "map_bare.png"
ART = ROOT / "assets" / "source" / "environment"
DEST = ROOT / "assets" / "environment"
TREE_FRAMES = 12
WATER_FRAMES = 8
FIRE_FRAMES = 8
PADDING = 12
FIRE_CENTER = (1073, 223)


@dataclass(frozen=True)
class Tree:
    art: int
    foot_x: int
    foot_y: int
    width: int
    height: int
    phase: float
    flip: bool = False


TREE_GROUPS = (
    ("west_trees", (
        Tree(0, 561, 205, 116, 140, .1),
        Tree(1, 481, 291, 125, 157, .7),
        Tree(2, 452, 354, 122, 153, 1.3),
        Tree(1, 648, 184, 74, 112, 1.8, True),
        Tree(0, 650, 299, 74, 115, 2.3),
    )),
    ("north_trees", (
        Tree(2, 663, 43, 76, 106, .5),
        Tree(0, 734, 53, 85, 112, 1.2),
        Tree(1, 785, 96, 94, 127, 2.0),
        Tree(2, 884, 62, 93, 113, 2.8, True),
    )),
    ("east_trees", (
        Tree(3, 970, 167, 83, 167, .2),
        Tree(1, 1018, 162, 91, 126, .8, True),
        Tree(4, 1065, 155, 82, 145, 1.4),
        Tree(5, 1126, 179, 79, 137, 2.1),
        Tree(3, 1165, 201, 68, 119, 2.7, True),
    )),
    ("bed_tree", (
        Tree(2, 1124, 516, 132, 154, .4),
    )),
    ("south_pines", (
        Tree(4, 838, 626, 73, 136, .4),
        Tree(5, 845, 674, 68, 118, 1.6, True),
    )),
    ("fruit_tree", (
        Tree(0, 744, 401, 79, 101, 1.1),
    )),
)

# The source sheet contains eight fixed-position frames of downward motion.
WATER_AREAS = (
    ("upper_fall", (796, 60, 48, 106)),
    ("lower_fall", (1003, 606, 54, 109)),
)
FIRE_RECT = (1045, 187, 60, 66)


def _crop(source, rect):
    x, y, width, height = rect
    return source.crop((x, y, x + width, y + height))


def _load_tree_art():
    with Image.open(ART / "tree_variants.png") as source:
        sheet = source.convert("RGBA")
    cell_w, cell_h = sheet.width // 3, sheet.height // 2
    variants = []
    for row in range(2):
        for column in range(3):
            cell = sheet.crop((column * cell_w, row * cell_h,
                               (column + 1) * cell_w, (row + 1) * cell_h))
            alpha = cell.getchannel("A").point(lambda value: value if value >= 45 else 0)
            bounds = alpha.getbbox()
            if bounds is None:
                raise ValueError("Tree source sheet has an empty sprite")
            cell.putalpha(alpha)
            variants.append(cell.crop(bounds))
    return variants


def _tree_rect(trees):
    left = max(0, min(tree.foot_x - tree.width // 2 - PADDING
                      for tree in trees))
    top = max(0, min(tree.foot_y - tree.height - PADDING
                     for tree in trees))
    right = min(1312, max(tree.foot_x + tree.width // 2 + PADDING
                          for tree in trees))
    bottom = min(816, max(tree.foot_y + PADDING for tree in trees))
    return left, top, right - left, bottom - top


def _paste_clipped(canvas, sprite, left, top):
    x0, y0 = max(0, left), max(0, top)
    x1 = min(canvas.width, left + sprite.width)
    y1 = min(canvas.height, top + sprite.height)
    if x1 <= x0 or y1 <= y0:
        return
    canvas.alpha_composite(sprite.crop((x0 - left, y0 - top,
                                        x1 - left, y1 - top)), (x0, y0))


def _tree_frame(rect, trees, variants, frame):
    canvas = Image.new("RGBA", rect[2:], (0, 0, 0, 0))
    turn = 2 * pi * frame / TREE_FRAMES
    for tree in sorted(trees, key=lambda item: item.foot_y):
        sprite = variants[tree.art].resize((tree.width, tree.height),
                                            Image.Resampling.LANCZOS)
        if tree.flip:
            sprite = sprite.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        padded = Image.new("RGBA", (tree.width + 2 * PADDING,
                                    tree.height + 2 * PADDING), (0, 0, 0, 0))
        padded.alpha_composite(sprite, (PADDING, PADDING))
        # Rotate the complete tree about its rooted base. The empty ground
        # beneath the sprite means no old canopy can show through while it sways.
        angle = 1.25 * (sin(turn + tree.phase) - sin(tree.phase))
        rotated = padded.rotate(angle, Image.Resampling.BICUBIC,
                                center=(PADDING + tree.width / 2,
                                        PADDING + tree.height - 4),
                                expand=False)
        left = round(tree.foot_x - tree.width / 2 - PADDING - rect[0])
        top = tree.foot_y - tree.height - PADDING - rect[1]
        _paste_clipped(canvas, rotated, left, top)
    return canvas


def _night_tree_frame(day_frame, rect):
    night = night_grade(day_frame)
    day_pixels, night_pixels = day_frame.load(), night.load()
    for y in range(day_frame.height):
        world_y = rect[1] + y
        for x in range(day_frame.width):
            world_x = rect[0] + x
            distance = hypot(world_x - FIRE_CENTER[0], world_y - FIRE_CENTER[1])
            if distance >= 90:
                continue
            red, green, blue, alpha = day_pixels[x, y]
            if alpha == 0:
                continue
            weight = .85 * (1 - distance / 90) ** 1.5
            lit = (min(255, int(red * 1.12 + 35)),
                   min(255, int(green * .88 + 24)),
                   min(255, int(blue * .45 + 6)))
            base = night_pixels[x, y]
            night_pixels[x, y] = tuple(round(base[i] * (1 - weight)
                                              + lit[i] * weight)
                                       for i in range(3)) + (alpha,)
    return night


def _water_art():
    with Image.open(ART / "waterfall_frames_raw.png") as source:
        sheet = source.convert("RGBA")
    cell_w, cell_h = sheet.width // 4, sheet.height // 2
    frames = []
    for row in range(2):
        for column in range(4):
            cell = sheet.crop((column * cell_w, row * cell_h,
                               (column + 1) * cell_w, (row + 1) * cell_h))
            cell = cell.crop((92, 31, 292, 485))
            alpha = cell.getchannel("A").point(lambda value: value if value >= 35 else 0)
            cell.putalpha(alpha)
            frames.append(cell)
    return frames


def _water_frame(art, rect):
    return art.resize(rect[2:], Image.Resampling.LANCZOS)


def _fire_mask(day_crop):
    # The flame alone animates. Its stone ring and the ground stay on the map.
    rows = {
        201: (1073, 1076), 202: (1071, 1078), 203: (1070, 1079),
        204: (1069, 1081), 205: (1068, 1082), 206: (1068, 1083),
        207: (1068, 1084), 208: (1069, 1085), 209: (1067, 1085),
        210: (1066, 1086), 211: (1065, 1087), 212: (1065, 1088),
        213: (1064, 1088), 214: (1064, 1089), 215: (1064, 1089),
        216: (1065, 1089), 217: (1065, 1089), 218: (1065, 1089),
        219: (1066, 1088), 220: (1066, 1088), 221: (1067, 1087),
        222: (1068, 1086), 223: (1069, 1085), 224: (1070, 1084),
        225: (1070, 1084), 226: (1071, 1083), 227: (1072, 1082),
    }
    x0, y0, width, _ = FIRE_RECT
    pixels = list(day_crop.getdata())
    mask = []
    for y, (left, right) in rows.items():
        for x in range(left, right + 1):
            index = (y - y0) * width + x - x0
            red, green, blue = pixels[index]
            if red > 105 and red > blue * 1.35 and green > blue * 1.10:
                mask.append((index, x, y))
    return mask


def _fire_frame(source, mask, frame):
    width, height = FIRE_RECT[2:]
    pixels = list(_crop(source, FIRE_RECT).getdata())
    output = [(0, 0, 0, 0)] * (width * height)
    angle = 2 * pi * frame / FIRE_FRAMES
    for index, x, y in mask:
        phase = x * .31 + y * .17
        flicker = sin(angle + phase) - sin(phase)
        red, green, blue = pixels[index]
        output[index] = (min(255, round(red * (1 + .055 * flicker))),
                         min(255, round(green * (1 + .14 * flicker))),
                         min(255, round(blue * (1 + .04 * flicker))), 255)
    image = Image.new("RGBA", (width, height))
    image.putdata(output)
    return image


def _save_strips(name, rect, frames, step):
    frames = list(frames)
    count = len(frames)
    width, height = rect[2:]
    for palette_index, palette in enumerate(("day", "night")):
        strip = Image.new("RGBA", (width * count, height))
        for index, pair in enumerate(frames):
            strip.paste(pair[palette_index], (index * width, 0))
        directory = DEST / palette
        directory.mkdir(parents=True, exist_ok=True)
        strip.save(directory / f"{name}.png", optimize=True)
    return {"name": name, "rect": list(rect), "frames": count,
            "step": step, "day": f"day/{name}.png", "night": f"night/{name}.png"}


def build():
    with Image.open(SOURCE) as original:
        day = original.convert("RGB")
    night = night_map_image(day)
    variants = _load_tree_art()
    effects = []
    for name, trees in TREE_GROUPS:
        rect = _tree_rect(trees)
        day_frames = (_tree_frame(rect, trees, variants, index)
                      for index in range(TREE_FRAMES))
        frames = ((frame, _night_tree_frame(frame, rect))
                  for frame in day_frames)
        effects.append(_save_strips(name, rect, frames, 2))
    water_frames = _water_art()
    for name, rect in WATER_AREAS:
        day_frames = (_water_frame(art, rect) for art in water_frames)
        frames = ((frame, night_grade(frame)) for frame in day_frames)
        effects.append(_save_strips(name, rect, frames, 1))
    mask = _fire_mask(_crop(day, FIRE_RECT))
    effects.append(_save_strips("campfire", FIRE_RECT,
                                ((_fire_frame(day, mask, index),
                                  _fire_frame(night, mask, index))
                                 for index in range(FIRE_FRAMES)), 1))
    manifest = {"version": 2, "source": "assets/map/map_bare.png",
                "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                "source_size": list(day.size), "effects": effects}
    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build()
