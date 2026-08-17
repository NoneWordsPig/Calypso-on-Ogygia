extends Sprite2D

## Overlays the computer sprite on the desk already drawn on the map.
## computer.png contains two frames: off and on.

signal state_changed(is_on: bool)

var is_on := false
var _off_texture: Texture2D
var _on_texture: Texture2D


func _ready() -> void:
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
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
	turn_off()


func turn_on() -> void:
	if is_on:
		return
	is_on = true
	texture = _on_texture
	state_changed.emit(true)


func turn_off() -> void:
	if not is_on:
		return
	is_on = false
	texture = _off_texture
	state_changed.emit(false)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.physical_keycode == KEY_F9:
			turn_on()
		elif event.physical_keycode == KEY_F10:
			turn_off()

