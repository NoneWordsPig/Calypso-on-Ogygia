"""Build data/navigation.json from the COVER map (map_cover.jpg, the 色罩版).

The cover map is the authoritative map binding: colored regions map to terrain
features (compared against map.png). Walkable colors are derived from the
actual cover palette and Godot's documented intent (青色道路/绿色田地可走):

  walkable: cyan(road), green(bed/field), magenta, purple, blue(computer),
            orange(campfire x2 tones)
  not walkable: yellow(fields), dark/black(sea & land), white

All named POIs from data/locations.json must be mutually reachable; the tool
verifies this. Runtime deps: numpy + scipy (rebuild only).
"""
from __future__ import annotations

import heapq
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import label as ndlabel

ROOT = Path(__file__).resolve().parent.parent
COVER_PATH = ROOT / "assets" / "map" / "map_cover.jpg"
LOCATIONS_PATH = ROOT / "data" / "locations.json"
OUT_PATH = ROOT / "data" / "navigation.json"

CELL_SIZE = 16
COLOR_TOLERANCE = 20
CELL_FILL_RATIO = 0.20

# Actual cover palette -> terrain (verified against map.png + POI centroids).
WALKABLE_COLORS = [
    (0, 248, 248),    # cyan   -> road network
    (0, 248, 0),      # green  -> bed / field
    (248, 0, 248),    # magenta
    (248, 0, 240),    # magenta (light variant)
    (144, 72, 184),   # purple
    (2, 1, 255),      # blue   -> computer
    (248, 208, 48),   # orange
    (252, 146, 2),    # orange -> campfire
]
NON_WALKABLE_EXAMPLES = [
    (248, 248, 0),    # yellow -> fields
    (24, 24, 24),     # dark   -> sea / land
    (0, 0, 0),        # black  -> sea
]


def _color_mask(arr: np.ndarray, colors, tol: int) -> np.ndarray:
    mask = np.zeros(arr.shape[:2], bool)
    for t in colors:
        m = np.ones(arr.shape[:2], bool)
        for i in range(3):
            m &= np.abs(arr[:, :, i] - t[i]) <= tol
        mask |= m
    return mask


def _build_grid(mask: np.ndarray) -> np.ndarray:
    h, w = mask.shape
    cols, rows = w // CELL_SIZE, h // CELL_SIZE
    grid = np.zeros((rows, cols), bool)
    for cy in range(rows):
        for cx in range(cols):
            sub = mask[cy * CELL_SIZE:(cy + 1) * CELL_SIZE, cx * CELL_SIZE:(cx + 1) * CELL_SIZE]
            grid[cy, cx] = sub.mean() >= CELL_FILL_RATIO
    return grid


def _nearest_cell(grid: np.ndarray, point) -> tuple | None:
    x, y = int(point[0]), int(point[1])
    rows, cols = grid.shape
    best, best_d = None, float("inf")
    for dy in range(-10, 11):
        for dx in range(-10, 11):
            cx, cy = x // CELL_SIZE + dx, y // CELL_SIZE + dy
            if 0 <= cx < cols and 0 <= cy < rows and grid[cy, cx]:
                d = (cx * CELL_SIZE + CELL_SIZE / 2 - x) ** 2 + (cy * CELL_SIZE + CELL_SIZE / 2 - y) ** 2
                if d < best_d:
                    best_d, best = d, (cx, cy)
    return best


def _a_star(grid: np.ndarray, a: tuple, b: tuple):
    rows, cols = grid.shape
    if not grid[a[1], a[0]] or not grid[b[1], b[0]]:
        return None
    if a == b:
        return [a]
    open_heap = [(0.0, a)]
    came, g = {}, {a: 0.0}
    while open_heap:
        _, cur = heapq.heappop(open_heap)
        if cur == b:
            path = []
            while cur in came:
                path.append(cur)
                cur = came[cur]
            path.append(a)
            return path[::-1]
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            nx, ny = cur[0] + dx, cur[1] + dy
            if not (0 <= nx < cols and 0 <= ny < rows) or not grid[ny, nx]:
                continue
            ng = g[cur] + (1.41421356 if dx and dy else 1.0)
            if ng < g.get((nx, ny), float("inf")):
                g[(nx, ny)] = ng
                came[(nx, ny)] = cur
                heapq.heappush(open_heap, (ng + ((nx - b[0]) ** 2 + (ny - b[1]) ** 2) ** 0.5, (nx, ny)))
    return None


def main() -> int:
    image = Image.open(COVER_PATH).convert("RGB")
    arr = np.asarray(image).astype(np.int32)
    h, w = arr.shape[:2]

    mask = _color_mask(arr, WALKABLE_COLORS, COLOR_TOLERANCE)
    grid = _build_grid(mask)
    rows, cols = grid.shape
    free_cells = int(grid.sum())

    locations = json.loads(LOCATIONS_PATH.read_text(encoding="utf-8"))
    pois = dict(locations["positions"])
    pois["spawn"] = locations["spawn"]

    cells = {}
    for name, pt in pois.items():
        cell = _nearest_cell(grid, pt)
        if cell is None:
            print(f"ERROR: POI {name} {pt} has no walkable cell nearby")
            return 1
        cells[name] = {"world": [int(pt[0]), int(pt[1])], "cell": [int(cell[0]), int(cell[1])]}

    names = list(cells)
    failures = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = tuple(cells[names[i]]["cell"]), tuple(cells[names[j]]["cell"])
            if _a_star(grid, a, b) is None:
                failures.append(f"{names[i]} <-> {names[j]}")
    if failures:
        print("ERROR: unreachable POI pairs:", failures)
        return 1

    grid_rows = ["".join("1" if grid[y, x] else "0" for x in range(cols)) for y in range(rows)]
    payload = {
        "map_size": [w, h],
        "cell_size": CELL_SIZE,
        "source": str(COVER_PATH.relative_to(ROOT)).replace("\\", "/"),
        "source_kind": "cover",
        "params": {
            "walkable_colors": WALKABLE_COLORS,
            "color_tolerance": COLOR_TOLERANCE,
            "cell_fill_ratio": CELL_FILL_RATIO,
        },
        "grid_cols": cols,
        "grid_rows": rows,
        "walkable_cells": free_cells,
        "poi_cells": cells,
        "grid": grid_rows,
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT_PATH.relative_to(ROOT)}: {cols}x{rows} grid, {free_cells} walkable cells")
    print("POI cells:", {k: v["cell"] for k, v in cells.items()})
    print("reachability: OK (%d pairs)" % (len(names) * (len(names) - 1) // 2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
