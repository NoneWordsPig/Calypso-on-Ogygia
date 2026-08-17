extends Node

## Game time system.
## Game time is driven by a real-time multiplier (default: 1 game hour = 30 real seconds).
## Active time is 06:00 - 21:00.

signal hour_changed(hour: int)
signal day_changed(day: int)

var current_hour: float = 8.0
var day: int = 1

var _last_full_hour: int = -1


func _ready() -> void:
	current_hour = float(Config.get_value("time", "start_hour", 8.0))
	_last_full_hour = int(floor(current_hour))
	hour_changed.emit(_last_full_hour)


func _process(delta: float) -> void:
	var seconds_per_hour := float(Config.get_value("time", "real_seconds_per_game_hour", 30.0))
	current_hour += delta / seconds_per_hour
	if current_hour >= 24.0:
		current_hour -= 24.0
		day += 1
		day_changed.emit(day)
	var full_hour := int(floor(current_hour))
	if full_hour != _last_full_hour:
		_last_full_hour = full_hour
		hour_changed.emit(full_hour)


func is_active_time() -> bool:
	var start := float(Config.get_value("time", "active_start_hour", 6.0))
	var end := float(Config.get_value("time", "active_end_hour", 21.0))
	return current_hour >= start and current_hour < end


func format_time() -> String:
	var hours := int(floor(current_hour))
	var minutes := int(floor(fmod(current_hour, 1.0) * 60.0))
	return "%02d:%02d" % [hours, minutes]

