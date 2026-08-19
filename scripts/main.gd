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
	_setup_adaptive_scaling()
	
	print("Calypso's Ogygia v0.2 started at ", TimeManager.format_time(), " (day ", TimeManager.day, "), character scale=", calypso.scale.x, ", world scale=", world.scale.x)

func _setup_map() -> void:
	var map_node = /Map
	map_node.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST

func _setup_camera() -> void:
	# Configure camera to follow Calypso
	if camera:
		camera.make_current()
		camera.limit_left = 0
		camera.limit_top = 0
		camera.limit_right = 1312
		camera.limit_bottom = 816
		print("[Main] Camera configured to follow Calypso")

func _setup_adaptive_scaling() -> void:
	# Calculate scaling based on window size
	var win_size = DisplayServer.window_get_size()
	var map_size = NavManager.get_map_size()
	
	# Calculate scale to fit the map in the window
	var scale_x = float(win_size.x) / float(map_size.x)
	var scale_y = float(win_size.y) / float(map_size.y)
	var scale = min(scale_x, scale_y)  # Use the smaller scale to maintain aspect ratio
	
	# Apply scaling to the world
	world.scale = Vector2(scale, scale)
	
	# Center the world
	var map_center = Vector2(map_size) * 0.5 * scale
	world.position = map_center
	
	print("[Main] Adaptive scaling applied: scale=", scale, ", world position=", world.position)

func _setup_characters() -> void:
	# Set Calypso starting position
	calypso.global_position = NavManager.get_spawn()
	
	# Apply display scaling
	_apply_display_scaling()

func _apply_display_scaling() -> void:
	# Character scaling
	var road_width = float(Config.get_value("display", "road_width", 14.0))
	var scale_multiplier = float(Config.get_value("display", "character_scale_multiplier", 1.0))
	var char_width = calypso.get_visual_width()
	var char_scale = 0.1
	if char_width > 0.0:
		char_scale = road_width / char_width * scale_multiplier
	calypso.scale = Vector2(char_scale, char_scale)

	# Computer scaling
	var computer_scale = float(Config.get_value("display", "computer_scale", 0.0))
	if computer_scale <= 0.0:
		computer_scale = char_scale
	computer.scale = Vector2(computer_scale, computer_scale)

func _setup_computer() -> void:
	# Configure computer position and scaling
	var offset_arr = Config.get_value("computer", "offset", [0, 0])
	var offset = Vector2(float(offset_arr[0]), float(offset_arr[1]))
	computer.global_position = NavManager.get_position("computer") + offset
	
	# Computer scaling is handled in _apply_display_scaling()

func _setup_behavior_system() -> void:
	# Setup BehaviorManager with Calypso reference
	behavior_manager.setup(calypso)
	
	# Connect debug keys
	_setup_debug_controls()

func _setup_debug_controls() -> void:
	# Setup debug key handling
	var input_handler = Node.new()
	input_handler.set_script(load("res://scripts/debug_controls.gd") if ResourceLoader.exists("res://scripts/debug_controls.gd") else null)
	if input_handler.get_script():
		add_child(input_handler)
		print("[Main] Debug controls enabled")
	else:
		print("[Main] Debug controls not available")
