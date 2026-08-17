extends Node

## Builds a walkable grid from data/locations.json and provides
## random-walk targets and A* paths for Calypso.

var locations: Dictionary = {}
var grid := AStarGrid2D.new()
var cell_size := 16
var _map_size := Vector2i(1312, 816)


func _ready() -> void:
	locations = _load_json("res://data/locations.json")
	if locations.is_empty():
		push_error("NavManager: failed to load res://data/locations.json")
		return
	var size_arr: Array = locations.get("map_size", [1312, 816])
	_map_size = Vector2i(int(size_arr[0]), int(size_arr[1]))
	cell_size = int(Config.get_value("navigation", "cell_size", 16))
	_build_grid()


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
