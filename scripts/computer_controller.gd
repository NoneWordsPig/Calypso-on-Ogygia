extends Sprite2D

## Enhanced ComputerController with interaction support
## Manages computer state and provides interface for BehaviorManager

signal state_changed(is_on: bool)
signal interaction_ready(position: Vector2, facing: String)

var is_on := false
var _off_texture: Texture2D
var _on_texture: Texture2D

# Interaction configuration
var interaction_position: Vector2
var interaction_facing: String = "left"
var is_ready_for_interaction: bool = false


func _ready() -> void:
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	_load_textures()
	_setup_interaction_config()
	print("[Computer] Initialized at position ", global_position)
	turn_off()


func _load_textures() -> void:
	var path: String = Config.get_value("resources", "computer", "res://pictures/object/computer.png")
	var tex := load(path) as Texture2D
	if tex == null:
		push_error("Computer: cannot load " + path)
		return
	var info := SpriteSheetUtils.detect_frames(tex, {})
	var rects: Array = info["frames"]
	if rects.size() >= 2:
		_off_texture = SpriteSheetUtils.region_texture(info["image"], rects[0])
		_on_texture = SpriteSheetUtils.region_texture(info["image"], rects[1])
	else:
		_off_texture = tex
		_on_texture = tex


func _setup_interaction_config() -> void:
	# Load positions from locations.json
	var locations_data = Config._load_json("res://data/locations.json")
	if not locations_data.has("positions"):
		push_error("Computer: no positions found in locations.json")
		return
	
	var positions: Dictionary = locations_data.get("positions", {})
	if positions.has("computer"):
		var comp_pos: Array = positions["computer"]
		interaction_position = Vector2(float(comp_pos[0]), float(comp_pos[1]))
		
		# Load interaction configuration from config
		var interaction_config: Dictionary = Config.get_value("computer", "interaction", {})
		var interaction_offset: Vector2 = Vector2(-30, 0)  # Default: stand to the left
		
		if interaction_config.has("position"):
			var offset_arr: Array = interaction_config["position"]
			interaction_offset = Vector2(float(offset_arr[0]), float(offset_arr[1]))
		if interaction_config.has("facing"):
			interaction_facing = interaction_config["facing"]
		
		# Calculate interaction position (where Calypso should stand)
		interaction_position += interaction_offset
		is_ready_for_interaction = true
		interaction_ready.emit(interaction_position, interaction_facing)
		print("[Computer] Interaction position: ", interaction_position, ", facing: ", interaction_facing)


func turn_on() -> void:
	if is_on:
		return
	print("[Computer] Turning ON")
	is_on = true
	texture = _on_texture
	state_changed.emit(true)


func turn_off() -> void:
	if not is_on:
		return
	print("[Computer] Turning OFF")
	is_on = false
	texture = _off_texture
	state_changed.emit(false)


func get_interaction_position() -> Vector2:
	return interaction_position


func get_interaction_facing() -> String:
	return interaction_facing


func is_on_state() -> bool:
	return is_on


# Interface for BehaviorManager
def start_interaction():
	"""Called by BehaviorManager when Calypso wants to use computer"""
	if not is_on:
		turn_on()
	return is_on


def stop_interaction():
	"""Called by BehaviorManager when Calypso stops using computer"""
	if is_on:
		turn_off()


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.physical_keycode == KEY_F9:
			# F9: Request work - this will be handled by BehaviorManager
			print("[Computer] F9 pressed - signaling BehaviorManager")
			# Emit signal for BehaviorManager to handle
			get_parent().get_node("BehaviorManager")._on_computer_request_work()
		elif event.physical_keycode == KEY_F10:
			# F10: Stop work - this will be handled by BehaviorManager
			print("[Computer] F10 pressed - signaling BehaviorManager")
			# Emit signal for BehaviorManager to handle
			get_parent().get_node("BehaviorManager")._on_computer_stop_work()
