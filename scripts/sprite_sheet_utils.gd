class_name SpriteSheetUtils
extends RefCounted

## Shared helpers for reading pixel-art sprite sheets.
## Frames are detected from alpha gaps instead of assuming a fixed grid,
## so sheets with different frame counts/sizes keep working.


static func detect_frames(texture: Texture2D, opts: Dictionary = {}) -> Dictionary:
	var img := texture.get_image()
	img.convert(Image.FORMAT_RGBA8)
	var w := img.get_width()
	var h := img.get_height()
	var data := img.get_data()
	var stride := w * 4

	var runs: Array[Vector2i] = []
	var in_run := false
	var start := 0
	for x in w:
		var has_alpha := false
		for y in h:
			if data[y * stride + x * 4 + 3] > 0:
				has_alpha = true
				break
		if has_alpha and not in_run:
			in_run = true
			start = x
		elif not has_alpha and in_run:
			in_run = false
			if x - start >= 4:
				runs.append(Vector2i(start, x - 1))
	if in_run and w - start >= 4:
		runs.append(Vector2i(start, w - 1))

	var frames: Array[Rect2i] = []
	if runs.size() >= 2:
		# Sheets with fully transparent gutters: one frame per content run.
		for run in runs:
			frames.append(_tight_rect(img, run.x, run.y))
	elif runs.size() == 1:
		# A single contiguous content block with no transparent separator
		# is one frame (e.g. the wide lying sleep pose), not a packed grid.
		frames.append(_tight_rect(img, runs[0].x, runs[0].y))
	else:
		# No detectable alpha gaps at all: the whole sheet is one frame,
		# unless the caller explicitly requests splitting a tightly packed
		# sheet into `split` equal columns.
		var split := maxi(1, int(opts.get("split", 1)))
		var span := int(floor(float(w) / split))
		for i in split:
			var rx0 := i * span
			var rx1 := i * span + span - 1
			if i == split - 1:
				rx1 = w - 1
			frames.append(_tight_rect(img, rx0, rx1))
	return {"frames": frames, "image": img}


static func aligned_textures(frames: Array[Rect2i], img: Image, cell_h: int) -> Array[Texture2D]:
	## Builds textures with a common height and bottom-aligned content,
	## so the character's feet sit on the node position for every frame.
	var cell_w := 0
	for rect in frames:
		cell_w = maxi(cell_w, rect.size.x)
	var out: Array[Texture2D] = []
	for rect in frames:
		var canvas := Image.create(cell_w, cell_h, false, Image.FORMAT_RGBA8)
		var dst := Vector2i((cell_w - rect.size.x) / 2, cell_h - rect.size.y)
		canvas.blit_rect(img, rect, dst)
		out.append(ImageTexture.create_from_image(canvas))
	return out


static func region_texture(img: Image, rect: Rect2i) -> ImageTexture:
	var canvas := Image.create(rect.size.x, rect.size.y, false, Image.FORMAT_RGBA8)
	canvas.blit_rect(img, rect, Vector2i.ZERO)
	return ImageTexture.create_from_image(canvas)


static func _tight_rect(img: Image, x0: int, x1: int) -> Rect2i:
	var w := img.get_width()
	var h := img.get_height()
	var data := img.get_data()
	var stride := w * 4
	var min_y := h
	var max_y := -1
	for x in range(x0, x1 + 1):
		for y in h:
			if data[y * stride + x * 4 + 3] > 0:
				min_y = mini(min_y, y)
				max_y = maxi(max_y, y)
	if max_y < 0:
		return Rect2i(x0, 0, x1 - x0 + 1, 1)
	return Rect2i(x0, min_y, x1 - x0 + 1, max_y - min_y + 1)
