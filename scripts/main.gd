extends Node2D

@onready var world: Node2D = 
@onready var calypso: CharacterBody2D = /Calypso
@onready var computer: Sprite2D = /Objects/Computer
@onready var behavior_manager: Node = 
@onready var camera: Camera2D = /Calypso/Camera2D

func _ready() -> void:
	_setup_map()
	_setup_computer()
	_setup_characters()
	_setup_behavior_system()
	_setup_camera()
	
	print(
		"Calypso's Ogygia v0.2 started at ", TimeManager.format_time(), " (day ", TimeManager.day,
		"), character scale=", calypso.scale.x, ", world scale=", world.scale.x
	)


func _setup_map() -> void:
	var map_node: Sprite2D = /Map
	map_node.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST


func _setup_computer() -> void:
	# Configure computer position and scaling
	var offset_arr: Array = Config.get_value("computer", "offset", [0, 0])
	var offset := Vector2(float(offset_arr[0]), float(offset_arr[1]))
	computer.global_position = NavManager.get_position("computer") + offset
	
	# Set computer scaling
	var computer_scale := float(Config.get_value("display", "computer_scale", 0.0))
	var char_scale: float = calypso.scale.x
	if computer_scale <= 0.0:
		computer_scale = char_scale
	computer.scale = Vector2(computer_scale, computer_scale)
	
	print("[Main] Computer configured at position ", computer.global_position, " with scale ", computer_scale)


func _setup_characters() -> void:
	# Set Calypso starting position
	calypso.global_position = NavManager.get_spawn()
	
	# Apply display scaling
	_apply_display_scaling()


func _setup_behavior_system() -> void:
	# Setup BehaviorManager with Calypso reference
	behavior_manager.setup(calypso)
	
	# Connect debug keys
	_setup_debug_controls()


func _setup_camera() -> void:
	# Configure camera to follow Calypso
	if camera:
		camera.make_current()
		camera.limit_left = 0
		camera.limit_top = 0
		camera.limit_right = 1312
		camera.limit_bottom = 816
		print("[Main] Camera configured to follow Calypso")


func _apply_display_scaling() -> void:
	## Remove world scaling - let the camera handle the view
	## The world is at its native size (1312x816) and the camera will follow Calypso
	var map_node: Sprite2D = /Map
	var map_size := NavManager.get_map_size()
	var map_center := Vector2(map_size) * 0.5
	
	# Center the world
	world.position = map_center
	map_node.position = map_center

	## Character scaling
	var road_width := float(Config.get_value("display", "road_width", 14.0))
	var scale_multiplier := float(Config.get_value("display", "character_scale_multiplier", 1.0))
	var char_width: float = calypso.get_visual_width()
	var char_scale := 0.1
	if char_width > 0.0:
		char_scale = road_width / char_width * scale_multiplier
	calypso.scale = Vector2(char_scale, char_scale)

	## Computer scaling
	var computer_scale := float(Config.get_value("display", "computer_scale", 0.0))
	if computer_scale <= 0.0:
		computer_scale = char_scale
	computer.scale = Vector2(computer_scale, computer_scale)


func _setup_debug_controls() -> void:
	# Setup debug key handling
	var input_handler = Node.new()
	input_handler.set_script(load("res://scripts/debug_controls.gd") if ResourceLoader.exists("res://scripts/debug_controls.gd") else null)
	if input_handler.get_script():
		add_child(input_handler)
		print("[Main] Debug controls enabled")
	else:
		print("[Main] Debug controls not available")


# Debug functions for testing
func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.physical_keycode == KEY_F8:
			# F8: Fast test one day cycle
			print("[Main] F8: Fast test day cycle")
			_test_day_cycle()
		elif event.physical_keycode == KEY_F9:
			# F9: Go to computer (handled by BehaviorManager)
			print("[Main] F9: Request work")
			behavior_manager.force_test_work()
		elif event.physical_keycode == KEY_F10:
			# F10: Go to sleep (handled by BehaviorManager)
			print("[Main] F10: Force sleep")
			behavior_manager.force_test_sleep()


func _test_day_cycle() -> void:
	# Fast forward time to test daily routines
	print("[Main] Testing day cycle...")
	var current_hour = TimeManager.current_hour
	
	# If it's evening, fast forward to next morning
	if current_hour >= 20.0:
		# Set to 6:00 AM next day
		TimeManager.current_hour = 6.0
		TimeManager.day += 1
		print("[Main] Fast forwarded to 6:00 AM, day ", TimeManager.day)
	else:
		# If it's daytime, fast forward to 9:00 PM
		TimeManager.current_hour = 21.0
		print("[Main] Fast forwarded to 9:00 PM")
