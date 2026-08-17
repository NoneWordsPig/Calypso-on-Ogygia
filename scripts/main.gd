extends Node2D

@onready var world: Node2D = $World
@onready var calypso: CharacterBody2D = $World/Calypso
@onready var computer: Sprite2D = $World/Computer
@onready var behavior_manager: Node = $BehaviorManager


func _ready() -> void:
	var map_node: Sprite2D = $World/Map
	map_node.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	var offset_arr: Array = Config.get_value("computer", "offset", [0, 0])
	var offset := Vector2(float(offset_arr[0]), float(offset_arr[1]))
	computer.global_position = NavManager.get_position("computer") + offset
	calypso.global_position = NavManager.get_spawn()
	_apply_display_scaling()
	behavior_manager.setup(calypso)
	print(
		"Calypso's Ogygia started at ", TimeManager.format_time(), " (day ", TimeManager.day,
		"), character scale=", calypso.scale.x, ", world scale=", world.scale.x
	)


func _apply_display_scaling() -> void:
	## Fullscreen scaling is handled by the canvas_items stretch mode
	## (uniform, no distortion). The World node is scaled so the map
	## covers the whole screen in "cover" mode (cropping overflow) or
	## fits with letterbox bars in "fit" mode.
	var map_node: Sprite2D = $World/Map
	var map_size := NavManager.get_map_size()
	var map_center := Vector2(map_size) * 0.5
	map_node.position = map_center

	var win_size := DisplayServer.window_get_size()
	var mode := str(Config.get_value("display", "map_mode", "cover"))
	var world_scale := 1.0
	if win_size.x > 0 and win_size.y > 0:
		var base_scale := minf(
			float(win_size.x) / float(map_size.x),
			float(win_size.y) / float(map_size.y)
		)
		if mode == "cover":
			world_scale = maxf(
				float(win_size.x) / (base_scale * float(map_size.x)),
				float(win_size.y) / (base_scale * float(map_size.y))
			)
	world.scale = Vector2(world_scale, world_scale)
	world.position = map_center * (1.0 - world_scale)

	## Character and computer overlay scale relative to the map.
	var road_width := float(Config.get_value("display", "road_width", 14.0))
	var scale_multiplier := float(Config.get_value("display", "character_scale_multiplier", 1.0))
	var char_width: float = calypso.get_visual_width()
	var char_scale := 0.1
	if char_width > 0.0:
		char_scale = road_width / char_width * scale_multiplier
	calypso.scale = Vector2(char_scale, char_scale)

	var computer_scale := float(Config.get_value("display", "computer_scale", 0.0))
	if computer_scale <= 0.0:
		computer_scale = char_scale
	computer.scale = Vector2(computer_scale, computer_scale)
