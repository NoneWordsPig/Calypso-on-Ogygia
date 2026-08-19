extends SceneTree
## Headless scanner for pictures/Calypso sprite sheets.
##
## Usage: godot --headless --path . --script res://scripts/tools/scan_calypso_sheets.gd
##
## Prints each sheet's size, alpha mode and detected frames using the same
## SpriteSheetUtils.detect_frames() pipeline that calypso.gd uses at runtime,
## so the report always matches what the character actually plays.

const SHEET_DIR := "res://pictures/Calypso"


func _init() -> void:
	var dir := DirAccess.open(SHEET_DIR)
	if dir == null:
		push_error("scan_calypso_sheets: cannot open " + SHEET_DIR)
		quit(1)
		return
	dir.list_dir_begin()
	var files: PackedStringArray = []
	var file_name := dir.get_next()
	while file_name != "":
		if not dir.current_is_dir() and file_name.to_lower().ends_with(".png"):
			files.append(file_name)
		file_name = dir.get_next()
	dir.list_dir_end()
	files.sort()

	for sheet in files:
		_scan(sheet)
	quit()


func _scan(file_name: String) -> void:
	var tex := load(SHEET_DIR + "/" + file_name) as Texture2D
	if tex == null:
		push_error("scan_calypso_sheets: cannot load " + file_name)
		return
	var info := SpriteSheetUtils.detect_frames(tex)
	var img: Image = info["image"]
	var frames: Array = info["frames"]
	print(
		"== ", file_name, " :: ", img.get_width(), "x", img.get_height(),
		" :: alpha=", img.detect_alpha(), " :: ", frames.size(), " frame(s)"
	)
	for i in frames.size():
		var rect: Rect2i = frames[i]
		print("   #%d %s  size=%dx%d" % [i, rect, rect.size.x, rect.size.y])
