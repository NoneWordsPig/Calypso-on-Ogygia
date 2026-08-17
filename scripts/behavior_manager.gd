extends Node

## Simple daily behavior state machine for Calypso.
## Stage 1 implements IDLE / WALKING / SLEEPING; WORKING and FISHING are
## priority-aware stubs ready for Hermes to drive later.

enum State { IDLE, WALKING, SLEEPING, WORKING, FISHING }

signal state_changed(new_state: int)

const PRIORITY := {
	State.SLEEPING: 5,
	State.WORKING: 4,
	State.FISHING: 3,
	State.WALKING: 2,
	State.IDLE: 1,
}

var calypso: CharacterBody2D
var state: int = State.IDLE

var _rng := RandomNumberGenerator.new()
var _idle_timer := 0.0
var _stub_timer := 0.0
var _sleep_pending := false


func setup(body: CharacterBody2D) -> void:
	calypso = body
	calypso.arrived.connect(_on_arrived)
	calypso.path_failed.connect(_on_path_failed)
	TimeManager.hour_changed.connect(_on_hour_changed)
	_rng.randomize()
	if TimeManager.is_active_time():
		_schedule_next_activity()
	else:
		_go_sleep()


func _process(delta: float) -> void:
	if state == State.SLEEPING:
		return
	if state == State.WORKING or state == State.FISHING:
		_stub_timer -= delta
		if _stub_timer <= 0.0:
			_force_state(State.IDLE)
			_schedule_next_activity()
		return
	if state == State.IDLE and _idle_timer > 0.0:
		_idle_timer -= delta
		if _idle_timer <= 0.0 and TimeManager.is_active_time():
			_start_random_walk()


func _start_random_walk() -> void:
	if not _try_set_state(State.WALKING):
		return
	var target := NavManager.get_random_walkable_position(_rng)
	calypso.walk_to(target)


func _on_arrived() -> void:
	if _sleep_pending:
		_sleep_pending = false
		_enter_sleep()
		return
	if state == State.WALKING:
		_force_state(State.IDLE)
		_schedule_next_activity()


func _on_path_failed() -> void:
	_sleep_pending = false
	_force_state(State.IDLE)
	_schedule_next_activity()


func _schedule_next_activity() -> void:
	var rng_range: Array = Config.get_value("behavior", "walk_interval_range", [6.0, 15.0])
	_idle_timer = _rng.randf_range(float(rng_range[0]), float(rng_range[1]))


func _on_hour_changed(hour: int) -> void:
	var end_hour := int(Config.get_value("time", "active_end_hour", 21.0))
	var start_hour := int(Config.get_value("time", "active_start_hour", 6.0))
	if hour == end_hour and state != State.SLEEPING:
		_go_sleep()
	elif hour == start_hour and state == State.SLEEPING:
		_wake_up()


func _go_sleep() -> void:
	if state == State.SLEEPING:
		return
	_sleep_pending = true
	_force_state(State.WALKING)
	var bed := NavManager.get_position("bed")
	calypso.walk_to(bed)


func _enter_sleep() -> void:
	_force_state(State.SLEEPING)
	calypso.play_sleep()


func _wake_up() -> void:
	_force_state(State.IDLE)
	calypso.wake_up()
	_schedule_next_activity()


## Public interfaces for future Hermes integration.
func request_work() -> void:
	if state == State.SLEEPING:
		return
	if _try_set_state(State.WORKING):
		calypso.play_typing()
		_stub_timer = float(Config.get_value("behavior", "stub_work_seconds", 2.0))


func request_fishing() -> void:
	if state == State.SLEEPING:
		return
	if _try_set_state(State.FISHING):
		_stub_timer = 2.0


func _try_set_state(new_state: int) -> bool:
	if state == new_state:
		return true
	if PRIORITY[new_state] < PRIORITY[state]:
		return false
	_force_state(new_state)
	return true


func _force_state(new_state: int) -> void:
	if state == new_state:
		return
	state = new_state
	state_changed.emit(state)
