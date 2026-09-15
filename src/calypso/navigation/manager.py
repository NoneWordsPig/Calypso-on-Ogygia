"""Small, deterministic eight-way grid navigator."""
from pathlib import Path
import heapq, json, math
from calypso.desktop.coordinate_mapper import ScreenTransform
PROJECT_ROOT = Path(__file__).resolve().parents[3]

class NavigationManager:
    def __init__(self, path=None, transform=None, locations_path=None):
        self.transform = transform or ScreenTransform()
        data = json.loads((Path(path) if path else PROJECT_ROOT / "data" / "navigation.json").read_text(encoding="utf-8"))
        self.cols = int(data.get("grid_cols", 0)); self.rows = int(data.get("grid_rows", 0))
        self.cell_size = int(data.get("cell_size", 16)); self.grid = data.get("grid", [])
        self.poi_cells = {name: tuple(value["cell"]) for name, value in data.get("poi_cells", {}).items() if "cell" in value}
        locations_file = Path(locations_path) if locations_path else PROJECT_ROOT / "data" / "locations.json"
        locations = json.loads(locations_file.read_text(encoding="utf-8")) if locations_file.exists() else {}
        positions = dict(locations.get("positions", {}))
        if "spawn" in locations: positions["spawn"] = locations["spawn"]
        self.points = {name: self.transform.source_to_world(value) for name, value in positions.items()}
        for name, value in data.get("poi_cells", {}).items():
            self.points.setdefault(name, self.transform.source_to_world(value.get("world", value)))
        self.poi_cells.update({name: self._source_cell(value) for name, value in positions.items()})

    def _source_cell(self, value):
        return (int(value[0] / self.cell_size), int(value[1] / self.cell_size))
    def _open(self, cell):
        x, y = cell
        return 0 <= x < self.cols and 0 <= y < self.rows and str(self.grid[y][x]) in ("1", "True")
    def is_walkable_world(self, point):
        return self._open(self._cell(point))
    def point(self, name):
        if name not in self.points:
            raise KeyError(f"Unknown location: {name}")
        return self.points[name]
    def _nearest_open(self, cell):
        if self._open(cell):
            return cell
        candidates = [(abs(x-cell[0])+abs(y-cell[1]), (x,y)) for y in range(self.rows) for x in range(self.cols) if self._open((x,y))]
        if not candidates:
            raise ValueError("navigation grid contains no walkable cells")
        return min(candidates)[1]
    def _cell(self, point):
        return (min(self.cols-1, max(0, int(point[0] / self.transform.world_size[0] * self.cols))), min(self.rows-1, max(0, int(point[1] / self.transform.world_size[1] * self.rows))))
    def _world(self, cell):
        return ((cell[0] + .5) * self.transform.world_size[0] / self.cols, (cell[1] + .5) * self.transform.world_size[1] / self.rows)
    def go_to(self, name, start):
        if name not in self.points: raise KeyError(f"Unknown location: {name}")
        begin = self._nearest_open(self._cell(start))
        goal = self._nearest_open(self.poi_cells.get(name, self._cell(self.points[name])))
        frontier=[(0.0, begin)]; came={begin: None}; cost={begin: 0.0}
        while frontier:
            _, current=heapq.heappop(frontier)
            if current == goal: break
            for dx, dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
                nxt=(current[0]+dx,current[1]+dy)
                if not self._open(nxt): continue
                if dx and dy and (not self._open((current[0]+dx,current[1])) or not self._open((current[0],current[1]+dy))): continue
                new=cost[current] + (math.sqrt(2) if dx and dy else 1)
                if new < cost.get(nxt, float("inf")):
                    cost[nxt]=new; came[nxt]=current; heapq.heappush(frontier,(new+math.dist(nxt,goal),nxt))
        if goal not in came: raise ValueError(f"No route to {name}")
        path=[]; cell=goal
        while cell is not None: path.append(self._world(cell)); cell=came[cell]
        path.reverse()
        path[0] = tuple(start)
        path[-1] = self.points[name]
        return path
    go_to_named = go_to
