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
	behavior_manager.setup(calypso)
	print("Calypso's Ogygia started at ", TimeManager.format_time(), " (day ", TimeManager.day, ")")

