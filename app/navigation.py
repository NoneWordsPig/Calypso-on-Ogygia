"""Grid navigation over the map-bound road network.

Loads the walkable grid produced by tools/build_navigation.py (derived from the
road pixels of assets/map/map.png) and provides A* pathfinding, nearest-cell
lookup, and random walk targets — the same ideas as the draft's
navigation_manager.gd, without Godot.
"""
from __future__ import annotations

import heapq
import json
import math
import random
from pathlib import Path
from typing import Optional, Sequence

DIAG = math.sqrt(2.0)


def _cell_center(cell, cell_size: float):
    return (cell[0] + 0.5) * cell_size, (cell[1] + 0.5) * cell_size


class Navigation:
    def __init__(self, nav_path: Path) -> None:
        data = json.loads(Path(nav_path).read_text(encoding="utf-8"))
        self.map_size: tuple[int, int] = tuple(data["map_size"])
        self.cell_size: float = float(data["cell_size"])
        self.cols: int = int(data["grid_cols"])
        self.rows: int = int(data["grid_rows"])
        self._walkable: set[tuple[int, int]] = set()
        self._free_cells: list[tuple[int, int]] = []
        rows_data: list[str] = data["grid"]
        for y, line in enumerate(rows_data[: self.rows]):
            for x, ch in enumerate(line[: self.cols]):
                if ch == "1":
                    self._walkable.add((x, y))
                    self._free_cells.append((x, y))
        self.poi_cells: dict[str, tuple[int, int]] = {
            name: tuple(v["cell"]) for name, v in data.get("poi_cells", {}).items()
        }
        self.poi_world: dict[str, tuple[float, float]] = {
            name: tuple(v["world"]) for name, v in data.get("poi_cells", {}).items()
        }

    # -- queries ---------------------------------------------------------
    def is_walkable_cell(self, cell: tuple[int, int]) -> bool:
        return cell in self._walkable

    def is_walkable(self, world: tuple[float, float]) -> bool:
        return self._world_to_cell(world) in self._walkable

    def _world_to_cell(self, world: tuple[float, float]) -> tuple[int, int]:
        return int(math.floor(world[0] / self.cell_size)), int(math.floor(world[1] / self.cell_size))

    def cell_to_world(self, cell: tuple[int, int]) -> tuple[float, float]:
        return _cell_center(cell, self.cell_size)

    def world_to_cell(self, world: tuple[float, float]) -> tuple[int, int]:
        return self._world_to_cell(world)

    def nearest_walkable(self, world: tuple[float, float]) -> Optional[tuple[float, float]]:
        start = self._world_to_cell(world)
        if start in self._walkable:
            return self.cell_to_world(start)
        for radius in range(1, 32):
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    c = (start[0] + dx, start[1] + dy)
                    if c in self._walkable:
                        return self.cell_to_world(c)
        return None

    def random_walk_target(self, rng: Optional[random.Random] = None) -> tuple[float, float]:
        rng = rng or random
        cell = rng.choice(self._free_cells)
        return self.cell_to_world(cell)

    def poi(self, name: str) -> tuple[float, float]:
        return self.poi_world.get(name, self.poi_world.get("spawn", (0.0, 0.0)))

    # -- pathfinding -----------------------------------------------------
    def find_path(self, from_world: tuple[float, float],
                  to_world: tuple[float, float],
                  arrive_radius: float = 12.0) -> list[tuple[float, float]]:
        start = self._world_to_cell(from_world)
        goal = self._world_to_cell(to_world)
        if not self.is_walkable_cell(start):
            start = self.nearest_cell_from(start)
        if not self.is_walkable_cell(goal):
            goal = self.nearest_cell_from(goal)
        if start is None or goal is None:
            return []
        if start == goal:
            return [self.cell_to_world(start)]
        path = self._a_star(start, goal)
        if not path:
            return []
        pts = [self.cell_to_world(c) for c in path]
        return self._smooth(pts, from_world, to_world, arrive_radius)

    def nearest_cell_from(self, start: tuple[int, int]) -> Optional[tuple[int, int]]:
        if start in self._walkable:
            return start
        for radius in range(1, 32):
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    c = (start[0] + dx, start[1] + dy)
                    if c in self._walkable:
                        return c
        return None

    def _a_star(self, a: tuple[int, int], b: tuple[int, int]) -> Optional[list[tuple[int, int]]]:
        open_heap = [(0.0, a)]
        came: dict[tuple[int, int], tuple[int, int]] = {}
        g: dict[tuple[int, int], float] = {a: 0.0}
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
                if not (0 <= nx < self.cols and 0 <= ny < self.rows) or not self.is_walkable_cell((nx, ny)):
                    continue
                ng = g[cur] + (DIAG if dx and dy else 1.0)
                if ng < g.get((nx, ny), float("inf")):
                    g[(nx, ny)] = ng
                    came[(nx, ny)] = cur
                    heapq.heappush(open_heap, (ng + math.hypot(nx - b[0], ny - b[1]), (nx, ny)))
        return None

    def _smooth(self, pts: Sequence[tuple[float, float]],
                origin: tuple[float, float],
                goal: tuple[float, float],
                arrive_radius: float) -> list[tuple[float, float]]:
        """Line-of-sight simplification so the character walks along straighter lines."""
        if len(pts) <= 2:
            return list(pts)
        out = [origin]
        i = 0
        n = len(pts)
        while i < n - 1:
            j = i + 1
            while j < n and self._line_of_sight(pts[i], pts[j]):
                j += 1
            k = j - 1
            if k > i:
                out.append(pts[k])
                i = k
            else:
                i += 1  # no shortcut available; advance one cell
        if self._dist(out[-1], goal) > arrive_radius:
            out.append(goal)
        return out

    def _line_of_sight(self, a: tuple[float, float], b: tuple[float, float]) -> bool:
        """Bresenham line-of-sight in cell space (corner-crossing diagonals allowed)."""
        x0 = a[0] / self.cell_size
        y0 = a[1] / self.cell_size
        x1 = b[0] / self.cell_size
        y1 = b[1] / self.cell_size
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x1 > x0 else (-1 if x1 < x0 else 0)
        sy = 1 if y1 > y0 else (-1 if y1 < y0 else 0)
        x, y = int(x0), int(y0)
        if not self.is_walkable_cell((x, y)):
            return False
        err = dx - dy
        while True:
            if x == int(x1) and y == int(y1):
                return True
            e2 = 2.0 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
            if not self.is_walkable_cell((x, y)):
                return False

    @staticmethod
    def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])


class PathFollower:
    """Moves a point along a path at a fixed speed (draft calypso.gd logic)."""

    def __init__(self, speed: float, arrive_radius: float = 12.0) -> None:
        self.speed = speed
        self.arrive_radius = arrive_radius
        self.path: list[tuple[float, float]] = []
        self._index = 0
        self.moving = False
        self.direction: tuple[float, float] = (1.0, 0.0)

    def set_path(self, path: list[tuple[float, float]]) -> None:
        self.path = list(path)
        self._index = 0
        self.moving = bool(self.path)

    def stop(self) -> None:
        self.path = []
        self._index = 0
        self.moving = False

    def update(self, pos: tuple[float, float], dt: float) -> tuple[float, float]:
        if not self.moving or self._index >= len(self.path):
            self.moving = False
            return pos
        target = self.path[self._index]
        dx, dy = target[0] - pos[0], target[1] - pos[1]
        dist = math.hypot(dx, dy)
        if dist <= self.arrive_radius:
            self._index += 1
            if self._index >= len(self.path):
                self.moving = False
                return target
            target = self.path[self._index]
            dx, dy = target[0] - pos[0], target[1] - pos[1]
            dist = math.hypot(dx, dy)
        if dist > 0:
            self.direction = (dx / dist, dy / dist)
        step = self.speed * dt
        if step >= dist:
            return target
        return pos[0] + self.direction[0] * step, pos[1] + self.direction[1] * step

    def is_arrived(self) -> bool:
        return not self.moving
