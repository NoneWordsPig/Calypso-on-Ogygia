extends CharacterBody2D

## Calypso: movement + pixel-art animations built at runtime from the
## sprite sheets in pictures/Calypso. Frames are detected from the sheets,
## so exact frame counts/sizes don't need to be hard-coded.

signal arrived
signal path_failed

enum Facing { DOWN, UP, LEFT, RIGHT }

@onready var sprite: AnimatedSprite2D = $Sprite

var speed: float = 90.0
var arrive_radius: float = 12.0
var walk_fps: float = 8.0
var idle_fps: float = 4.0
var sleep_fps: float = 2.0

var facing: Facing = Facing.DOWN
var _moving: bool = false
var _path: PackedVector2Array = PackedVector2Array()
var _path_index: int = 0
var _visual_width: float = 0.0


func _ready() -> void:
	speed = float(Config.get_value("movement", "speed", 90.0))
	arrive_radius = float(Config.get_value("movement", "arrive_radius", 12.0))
	walk_fps = float(Config.get_value("movement", "walk_fps", 8.0))
	idle_fps = float(Config.get_value("movement", "idle_fps", 4.0))
	sleep_fps = float(Config.get_value("movement", "sleep_fps", 2.0))
	sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	_build_sprite_frames()
	sprite.play("idle_down")


func _physics_process(_delta: float) -> void:
	if not _moving:
		velocity = Vector2.ZERO
		_play_idle()
		return
	if _path_index >= _path.size():
		_finish_walk()
		return
	var target: Vector2 = _path[_path_index]
	var to_target := target - global_position
	if to_target.length() <= arrive_radius:
		_path_index += 1
		if _path_index >= _path.size():
			_finish_walk()
			return
		target = _path[_path_index]
		to_target = target - global_position
	velocity = to_target.normalized() * speed
	_update_facing(to_target)
	_play_walk()
	move_and_slide()


func walk_to(target: Vector2) -> void:
	var path := NavManager.find_path(global_position, target)
	if path.size() < 2:
		if global_position.distance_to(target) <= arrive_radius * 2.0:
			arrived.emit()
		else:
			path_failed.emit()
		return
	_path = path
	_path_index = 0
	_moving = true


func stop() -> void:
	_moving = false
	_path = PackedVector2Array()
	velocity = Vector2.ZERO


func play_sleep() -> void:
	stop()
	sprite.play("sleep")


func wake_up() -> void:
	facing = Facing.DOWN
	sprite.play("idle_down")


func play_typing() -> void:
	stop()
	sprite.play("typing")


func get_visual_width() -> float:
	return _visual_width


func _finish_walk() -> void:
	_moving = false
	_path = PackedVector2Array()
	velocity = Vector2.ZERO
	arrived.emit()


func _update_facing(dir: Vector2) -> void:
	if absf(dir.x) > absf(dir.y):
		facing = Facing.LEFT if dir.x < 0.0 else Facing.RIGHT
	else:
		facing = Facing.UP if dir.y < 0.0 else Facing.DOWN


func _walk_anim_name() -> String:
	match facing:
		Facing.UP:
			return "walk_up"
		Facing.LEFT:
			return "walk_left"
		Facing.RIGHT:
			return "walk_right"
		_:
			return "walk_down"


func _idle_anim_name() -> String:
	match facing:
		Facing.UP:
			return "idle_up"
		_:
			return "idle_down"


func _play_walk() -> void:
	var name := _walk_anim_name()
	if sprite.animation != name:
		sprite.play(name)


func _play_idle() -> void:
	var name := _idle_anim_name()
	if sprite.animation != name:
		sprite.play(name)


func _build_sprite_frames() -> void:
	var base: String = Config.get_value("resources", "character_dir", "res://pictures/Calypso")
	var animations := {
		"walk_down": base + "/front_walk.png",
		"walk_up": base + "/back_walk.png",
		"walk_left": base + "/left_walk.png",
		"walk_right": base + "/right_walk.png",
		"idle_down": base + "/front_rest.png",
		"idle_up": base + "/back_rest .png",
		"sleep": base + "/sleep.png",
		"typing": base + "/typing.png",
	}
	var fps_by_anim := {
		"walk_down": walk_fps,
		"walk_up": walk_fps,
		"walk_left": walk_fps,
		"walk_right": walk_fps,
		"idle_down": idle_fps,
		"idle_up": idle_fps,
		"sleep": sleep_fps,
		"typing": walk_fps,
	}
	var infos := {}
	var max_cell_h := 0
	for anim in animations:
		var tex := load(animations[anim]) as Texture2D
		if tex == null:
			push_error("Calypso: cannot load " + animations[anim])
			continue
		var opts := {}
		if anim == "sleep":
			opts["split"] = 2
		var info := SpriteSheetUtils.detect_frames(tex, opts)
		infos[anim] = info
		var rects: Array = info["frames"]
		for rect in rects:
			max_cell_h = maxi(max_cell_h, rect.size.y)

	# Standing width only comes from the walk sheets; the sleep sheet is
	# a wide lying pose and must not be used as the character's width.
	_visual_width = 0.0
	for anim in ["walk_down", "walk_up", "walk_left", "walk_right"]:
		if infos.has(anim):
			for rect in infos[anim]["frames"]:
				_visual_width = maxf(_visual_width, float(rect.size.x))

	var frames := SpriteFrames.new()
	for anim in infos:
		var info: Dictionary = infos[anim]
		var rects: Array = info["frames"]
		frames.add_animation(anim)
		frames.set_animation_speed(anim, float(fps_by_anim.get(anim, walk_fps)))
		var textures := SpriteSheetUtils.aligned_textures(rects, info["image"], max_cell_h)
		for tex in textures:
			frames.add_frame(anim, tex)

	sprite.sprite_frames = frames
	sprite.offset = Vector2(0.0, -float(max_cell_h) / 2.0)
