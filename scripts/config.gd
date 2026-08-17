extends Node

## Loads data/config.json once at startup and exposes typed accessors.
## Keeps all tunable settings out of scripts so they are easy to edit.

var data: Dictionary = {}


func _ready() -> void:
	data = _load_json("res://data/config.json")
	if data.is_empty():
		push_error("Config: failed to load res://data/config.json")


func _load_json(path: String) -> Dictionary:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		push_error("Config: cannot open " + path)
		return {}
	var parsed = JSON.parse_string(file.get_as_text())
	return parsed if parsed is Dictionary else {}


func get_value(section: String, key: String, default = null):
	if not data.has(section):
		return default
	var sec = data[section]
	if not (sec is Dictionary) or not sec.has(key):
		return default
	return sec[key]

