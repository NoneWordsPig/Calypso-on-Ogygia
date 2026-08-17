extends Node

## Builds a walkable grid from data/locations.json and provides
## random-walk targets and A* paths for Calypso.

var locations: Dictionary = {}
var grid := AStarGrid2D.new()
var cell_size := 16
var _map_size := Vector2i(1312, 816)
var _cover_image: Image = null
var _cover_positions: Dictionary = {}


func _ready() -> void:
	locations = _load_json("res://data/locations.json")
	if locations.is_empty():
		push_error("NavManager: failed to load res://data/locations.json")
		return
	var size_arr: Array = locations.get("map_size", [1312, 816])
	_map_size = Vector2i(int(size_arr[0]), int(size_arr[1]))
	cell_size = int(Config.get_value("navigation", "cell_size", 16))
	_load_cover_map()
	_build_grid()
	if _cover_image != null:
		print("NavManager: walkability from cover map; positions=", _cover_positions)


func _load_json(path: String) -> Dictionary:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		push_error("NavManager: cannot open " + path)
		return {}
	var parsed = JSON.parse_string(file.get_as_text())
	return parsed if parsed is Dictionary else {}


func get_map_size() -> Vector2i:
	return _map_size


func get_position(name: String) -> Vector2:
	if _cover_positions.has(name):
		return _cover_positions[name]
	var positions: Dictionary = locations.get("positions", {})
	var p = positions.get(name)
	if p is Array and p.size() >= 2:
		return Vector2(float(p[0]), float(p[1]))
	return Vector2.ZERO


func get_spawn() -> Vector2:
	var p = locations.get("spawn")
	if p is Array and p.size() >= 2:
		return Vector2(float(p[0]), float(p[1]))
	return get_position("computer")


func _build_grid() -> void:
	grid.region = Rect2i(Vector2i.ZERO, _map_size)
	grid.cell_size = Vector2i(cell_size, cell_size)
	grid.diagonal_mode = AStarGrid2D.DIAGONAL_MODE_ONLY_IF_NO_OBSTACLES
	grid.update()
	var width := _map_size.x / cell_size
	var height := _map_size.y / cell_size
	for y in height:
		for x in width:
			var world := Vector2((x + 0.5) * cell_size, (y + 0.5) * cell_size)
			if not _is_walkable(world):
				grid.set_point_solid(Vector2i(x, y), true)
	_carve_paths()


func _is_walkable(world: Vector2) -> bool:
	if _cover_image != null:
		return _cover_cell_walkable(world)
	if world.x < 0.0 or world.y < 0.0 or world.x >= _map_size.x or world.y >= _map_size.y:
		return false
	var island: Array = locations.get("island_polygon", [])
	var poly := _to_polygon(island)
	if poly.size() >= 3 and not Geometry2D.is_point_in_polygon(world, poly):
		return false
	var forbidden: Array = locations.get("forbidden_areas", [])
	for area in forbidden:
		if not (area is Dictionary):
			continue
		var pts := _to_polygon(area.get("points", []))
		if pts.size() >= 3 and Geometry2D.is_point_in_polygon(world, pts):
			return false
	return true


func _load_cover_map() -> void:
	var path: String = Config.get_value("resources", "map_cover", "")
	if path.is_empty():
		return
	var tex := load(path) as Texture2D
	if tex == null:
		push_error("NavManager: cannot load cover map " + path)
		return
	var img := tex.get_image()
	img.convert(Image.FORMAT_RGB8)
	_cover_image = img
	var tol := int(Config.get_value("navigation", "color_tolerance", 30))
	var cover_colors: Dictionary = Config.get_value("navigation", "cover_colors", {})
	for key in ["computer", "bed", "campfire"]:
		var target: Array = cover_colors.get(key, [])
		if target.size() >= 3:
			var centroid := _color_centroid(
				img, int(target[0]), int(target[1]), int(target[2]), tol
			)
			if centroid != Vector2.INF:
				_cover_positions[key] = centroid
	var rock: Array = cover_colors.get("fishing", [102, 102, 102])
	var fishing := _largest_color_cluster_centroid(
		img, int(rock[0]), int(rock[1]), int(rock[2]), tol
	)
	if fishing != Vector2.INF:
		_cover_positions["fishing"] = fishing


func _cover_cell_walkable(world: Vector2) -> bool:
	var tol := int(Config.get_value("navigation", "color_tolerance", 30))
	var cover_colors: Dictionary = Config.get_value("navigation", "cover_colors", {})
	var walkable_colors: Array = cover_colors.get("walkable", [[124, 255, 255], [0, 255, 0]])
	var data := _cover_image.get_data()
	var w := _cover_image.get_width()
	var h := _cover_image.get_height()
	var stride := w * 3
	var cell_x := int(floor(world.x / cell_size)) * cell_size
	var cell_y := int(floor(world.y / cell_size)) * cell_size
	for sy in [2, 6, 10, 14]:
		for sx in [2, 6, 10, 14]:
			var px: int = cell_x + sx
			var py: int = cell_y + sy
			if px >= w or py >= h:
				continue
			var idx: int = py * stride + px * 3
			var pr := int(data[idx])
			var pg := int(data[idx + 1])
			var pb := int(data[idx + 2])
			for color in walkable_colors:
				if color is Array and color.size() >= 3:
					if _color_close(
						pr, pg, pb, int(color[0]), int(color[1]), int(color[2]), tol
					):
						return true
	return false


func _color_close(pr: int, pg: int, pb: int, tr: int, tg: int, tb: int, tol: int) -> bool:
	return absi(pr - tr) <= tol and absi(pg - tg) <= tol and absi(pb - tb) <= tol


func _color_centroid(img: Image, tr: int, tg: int, tb: int, tol: int) -> Vector2:
	var w := img.get_width()
	var h := img.get_height()
	var data := img.get_data()
	var stride := w * 3
	var sum_x := 0.0
	var sum_y := 0.0
	var count := 0
	for y in h:
		for x in w:
			var idx := y * stride + x * 3
			if _color_close(int(data[idx]), int(data[idx + 1]), int(data[idx + 2]), tr, tg, tb, tol):
				sum_x += x
				sum_y += y
				count += 1
	if count == 0:
		return Vector2.INF
	return Vector2(sum_x / float(count), sum_y / float(count))


func _largest_color_cluster_centroid(img: Image, tr: int, tg: int, tb: int, tol: int) -> Vector2:
	var w := img.get_width()
	var h := img.get_height()
	var data := img.get_data()
	var stride := w * 3
	var visited := PackedByteArray()
	visited.resize(w * h)
	var best := Vector2.INF
	var best_size := 0
	for y in h:
		for x in w:
			var flat := y * w + x
			if visited[flat] == 1:
				continue
			var idx := y * stride + x * 3
			if not _color_close(int(data[idx]), int(data[idx + 1]), int(data[idx + 2]), tr, tg, tb, tol):
				continue
			var stack: Array[Vector2i] = [Vector2i(x, y)]
			visited[flat] = 1
			var count := 0
			var sum_x := 0.0
			var sum_y := 0.0
			while not stack.is_empty():
				var c: Vector2i = stack.pop_back()
				count += 1
				sum_x += c.x
				sum_y += c.y
				for n in _neighbors(c, w, h):
					var nflat := n.y * w + n.x
					if visited[nflat] == 1:
						continue
					var nidx := n.y * stride + n.x * 3
					if _color_close(int(data[nidx]), int(data[nidx + 1]), int(data[nidx + 2]), tr, tg, tb, tol):
						visited[nflat] = 1
						stack.append(n)
			if count > best_size:
				best_size = count
				best = Vector2(sum_x / float(count), sum_y / float(count))
	return best


func _neighbors(cell: Vector2i, w: int, h: int) -> Array[Vector2i]:
	var out: Array[Vector2i] = []
	if cell.x > 0:
		out.append(cell + Vector2i(-1, 0))
	if cell.x < w - 1:
		out.append(cell + Vector2i(1, 0))
	if cell.y > 0:
		out.append(cell + Vector2i(0, -1))
	if cell.y < h - 1:
		out.append(cell + Vector2i(0, 1))
	return out


func _to_polygon(data: Array) -> PackedVector2Array:
	var out := PackedVector2Array()
	for p in data:
		if p is Array and p.size() >= 2:
			out.append(Vector2(float(p[0]), float(p[1])))
	return out


func _carve_paths() -> void:
	## Optional: polylines in walkable_paths are thickened into walkable cells.
	for path in locations.get("walkable_paths", []):
		if not (path is Dictionary):
			continue
		var pts: Array = path.get("points", [])
		var radius := int(path.get("width_cells", 1))
		if pts.size() < 2:
			continue
		for i in range(pts.size() - 1):
			var a := Vector2(float(pts[i][0]), float(pts[i][1]))
			var b := Vector2(float(pts[i + 1][0]), float(pts[i + 1][1]))
			var steps := int(ceil(a.distance_to(b) / (cell_size * 0.5)))
			for s in range(steps + 1):
				var p := a.lerp(b, float(s) / float(steps))
				var cell := _world_to_cell(p)
				_clear_solid_radius(cell, radius)


func _clear_solid_radius(cell: Vector2i, radius: int) -> void:
	for dy in range(-radius, radius + 1):
		for dx in range(-radius, radius + 1):
			var c := cell + Vector2i(dx, dy)
			if grid.is_in_boundsv(c):
				grid.set_point_solid(c, false)


func get_random_walkable_position(rng: RandomNumberGenerator) -> Vector2:
	var areas: Array = locations.get("random_walk_areas", [])
	for _attempt in 40:
		var area = null
		if areas.size() > 0:
			area = areas[rng.randi_range(0, areas.size() - 1)]
		var point := _random_point_in_area(area, rng)
		var cell := _world_to_cell(point)
		if _cell_free(cell):
			return grid.get_point_position(cell)
	var fallback := _nearest_free(_world_to_cell(get_position("computer")))
	return grid.get_point_position(fallback)


func _random_point_in_area(area, rng: RandomNumberGenerator) -> Vector2:
	if area is Dictionary:
		var pts: Array = area.get("points", [])
		if pts.size() >= 3:
			var min_x := INF
			var min_y := INF
			var max_x := -INF
			var max_y := -INF
			for p in pts:
				min_x = minf(min_x, float(p[0]))
				max_x = maxf(max_x, float(p[0]))
				min_y = minf(min_y, float(p[1]))
				max_y = maxf(max_y, float(p[1]))
			var poly := _to_polygon(pts)
			for _i in 80:
				var point := Vector2(
					rng.randf_range(min_x, max_x),
					rng.randf_range(min_y, max_y)
				)
				if Geometry2D.is_point_in_polygon(point, poly):
					return point
			return Vector2((min_x + max_x) * 0.5, (min_y + max_y) * 0.5)
		var rect: Array = area.get("rect", [])
		if rect.size() >= 4:
			return Vector2(
				rng.randf_range(float(rect[0]), float(rect[2])),
				rng.randf_range(float(rect[1]), float(rect[3]))
			)
	return get_position("computer")


func _cell_free(cell: Vector2i) -> bool:
	return grid.is_in_boundsv(cell) and not grid.is_point_solid(cell)


func _world_to_cell(pos: Vector2) -> Vector2i:
	return Vector2i(int(floor(pos.x / cell_size)), int(floor(pos.y / cell_size)))


func _nearest_free(cell: Vector2i) -> Vector2i:
	if _cell_free(cell):
		return cell
	for radius in range(1, 24):
		for dy in range(-radius, radius + 1):
			for dx in range(-radius, radius + 1):
				var c := cell + Vector2i(dx, dy)
				if _cell_free(c):
					return c
	return cell


func find_path(from: Vector2, to: Vector2) -> PackedVector2Array:
	var from_cell := _world_to_cell(from)
	var to_cell := _world_to_cell(to)
	if not _cell_free(from_cell):
		from_cell = _nearest_free(from_cell)
	if not _cell_free(to_cell):
		to_cell = _nearest_free(to_cell)
	if not _cell_free(from_cell) or not _cell_free(to_cell):
		return PackedVector2Array()
	if from_cell == to_cell:
		var same := PackedVector2Array()
		same.append(grid.get_point_position(from_cell))
		same.append(grid.get_point_position(to_cell))
		return same
	return grid.get_point_path(from_cell, to_cell)
