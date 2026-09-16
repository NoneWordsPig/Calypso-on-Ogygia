"""Extract the 6x4 Calypso sheet into stable, transparent RGBA frames.

Background removal is a border flood-fill of bright neutral checkerboard pixels;
it deliberately does not remove bright pixels enclosed by the character.
"""
from __future__ import annotations
import json
from collections import deque
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets/source/calypso_walk_rest_sheet_v2.png"
OUT = ROOT / "assets/calypso_v2"
ROWS = ("down", "left", "right", "up")
BASELINE = 240

def remove_background(im: Image.Image) -> Image.Image:
    rgb = im.convert("RGB"); w, h = rgb.size; pix = rgb.load()
    def bg(x, y):
        r, g, b = pix[x, y]
        return max(r, g, b) - min(r, g, b) <= 14 and (r + g + b) / 3 >= 145
    seen = bytearray(w * h); q = deque()
    for x in range(w): q.extend(((x, 0), (x, h - 1)))
    for y in range(h): q.extend(((0, y), (w - 1, y)))
    while q:
        x, y = q.popleft(); i = y * w + x
        if seen[i] or not bg(x, y): continue
        seen[i] = 1
        if x: q.append((x-1, y))
        if x+1 < w: q.append((x+1, y))
        if y: q.append((x, y-1))
        if y+1 < h: q.append((x, y+1))
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0)); op = out.load()
    for y in range(h):
        for x in range(w):
            if not seen[y*w+x]: op[x, y] = (*pix[x, y], 255)
    return out

def keep_main_component(im: Image.Image) -> Image.Image:
    """Drop disconnected generated shadows and isolated one-pixel noise."""
    alpha = im.getchannel("A")
    w, h = im.size
    seen: set[tuple[int, int]] = set()
    components: list[list[tuple[int, int]]] = []
    for y in range(h):
        for x in range(w):
            if not alpha.getpixel((x, y)) or (x, y) in seen:
                continue
            component: list[tuple[int, int]] = []
            queue = [(x, y)]
            seen.add((x, y))
            while queue:
                px, py = queue.pop()
                component.append((px, py))
                for point in ((px-1, py), (px+1, py), (px, py-1), (px, py+1)):
                    if (0 <= point[0] < w and 0 <= point[1] < h
                            and point not in seen and alpha.getpixel(point)):
                        seen.add(point)
                        queue.append(point)
            components.append(component)
    if not components:
        return im
    keep = set(max(components, key=len))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    source = im.load()
    target = out.load()
    for x, y in keep:
        target[x, y] = source[x, y]
    return out

def main():
    sheet = remove_background(Image.open(SOURCE))
    frames = []
    for row, direction in enumerate(ROWS):
        for col in range(6):
            name = ("walk_" if col < 4 else "idle_") + direction
            if col >= 4: col_out = col - 4
            else: col_out = col
            cell = keep_main_component(
                sheet.crop((col*256, row*256, (col+1)*256, (row+1)*256))
            )
            box = cell.getchannel("A").getbbox()
            canvas = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
            if box:
                obj = cell.crop(box); x = max(0, (256-obj.width)//2)
                canvas.alpha_composite(obj, (x, BASELINE-obj.height))
            dest = OUT / name; dest.mkdir(parents=True, exist_ok=True)
            path = dest / f"{col_out:02d}.png"; canvas.save(path); frames.append((name, path, box))
    animations = {}
    for direction in ROWS:
      for name in ("walk_" + direction, "idle_" + direction):
        n = 4 if name.startswith("walk") else 2
        animations[name] = {"frames": [f"{name}/{i:02d}.png" for i in range(n)], "count": n,
                            "canvas_size": [256, 256], "anchor": [128, BASELINE], "anchor_type": "feet-center"}
    # Work and sleep are not being redrawn in this pass. Keep the existing
    # compatible assets so task/schedule states never make the sprite vanish.
    for name in ("work", "sleep"):
        animations[name] = {
            "frames": [f"../calypso/{name}/{i:02d}.png" for i in range(4)],
            "count": 4,
            "anchor_type": "feet-center",
        }
    (OUT / "manifest.json").write_text(json.dumps({"cell_size": [256, 256], "canvas_size": [256, 256], "animations": animations}, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__": main()
