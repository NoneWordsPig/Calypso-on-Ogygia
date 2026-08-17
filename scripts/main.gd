extends Node2D

@onready var calypso: CharacterBody2D = $Calypso
@onready var computer: Sprite2D = $Computer
@onready var behavior_manager: Node = $BehaviorManager


func _ready() -> void:
	$Map.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	var offset_arr: Array = Config.get_value("computer", "offset", [0, 0])
	var offset := Vector2(float(offset_arr[0]), float(offset_arr[1]))
	computer.global_position = NavManager.get_position("computer") + offset
	calypso.global_position = NavManager.get_spawn()
	_apply_display_scaling()
	behavior_manager.setup(calypso)
	print(
		"Calypso's Ogygia started at ", TimeManager.format_time(), " (day ", TimeManager.day,
		"), character scale=", calypso.scale.x
	)


func _apply_display_scaling() -> void:
	## Fullscreen scaling is handled by the canvas_items stretch mode
	## (map keeps its aspect, no distortion). Here we only scale the
	## character (and computer overlay) down to road width.
	var road_width := float(Config.get_value("display", "road_width", 14.0))
	var char_width: float = calypso.get_visual_width()
	var char_scale := 0.1
	if char_width > 0.0:
		char_scale = road_width / char_width
	calypso.scale = Vector2(char_scale, char_scale)

	var computer_scale := float(Config.get_value("display", "computer_scale", 0.0))
	if computer_scale <= 0.0:
		computer_scale = char_scale
	computer.scale = Vector2(computer_scale, computer_scale)
