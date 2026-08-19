extends Node

## Enhanced BehaviorManager for Life Simulation v0.2
## Implements IDLE / WALKING / SLEEPING / WORKING with proper priority system

signal state_changed(new_state: int)

enum State { IDLE, WALKING, SLEEPING, WORKING, FISHING }

const PRIORITY := {
	State.SLEEPING: 5,
	State.WORKING: 4,
	State.FISHING: 3,
	State.WALKING: 2,
	State.IDLE: 1,
}

var calypso: CharacterBody2D
var computer_controller: Node
var state: int = State.IDLE

var _rng := RandomNumberGenerator.new()
var _idle_timer := 0.0
var _working_timer := 0.0
var _sleep_pending := false
var _computer_interaction_target: Vector2
var _computer_facing: String = "left"
var _previous_state: int = State.IDLE


func setup(body: CharacterBody2D) -> void:
	calypso = body
	# Find computer controller in the tree
	var computer_nodes = get_tree().get_nodes_in_group("computer")
	if computer_nodes.size() > 0:
		computer_controller = computer_nodes[0]
		print("[BehaviorManager] Computer controller found")
	else:
		print("[BehaviorManager] Warning: No computer controller found")
	
	calypso.arrived.connect(_on_arrived)
	calypso.path_failed.connect(_on_path_failed)
	TimeManager.hour_changed.connect(_on_hour_changed)
	
	# Connect to computer signals
	if computer_controller:
		computer_controller.state_changed.connect(_on_computer_state_changed)
	
	_rng.randomize()
	print("[BehaviorManager] Setup completed")
	
	if TimeManager.is_active_time():
		_schedule_next_activity()
	else:
		_go_sleep()


func _process(delta: float) -> void:
	match state:
		State.SLEEPING:
			# Sleeping state - no processing needed
			pass
			
		State.WORKING:
			_working_timer -= delta
			if _working_timer <= 0.0:
				print("[Behavior] Working session ended")
				_exit_working()
				
		State.IDLE:
			if _idle_timer > 0.0:
				_idle_timer -= delta
				if _idle_timer <= 0.0 and TimeManager.is_active_time():
					_start_random_walk()
					
		State.WALKING:
			# Walking handled by calypso's physics process
			pass
			
		State.FISHING:
			# Placeholder for future fishing implementation
			pass


# Computer interaction interface
func request_work() -> void:
	print("[Behavior] Work request received")
	if state == State.SLEEPING:
		print("[Behavior] Cannot work - sleeping")
		return
	
	if _try_set_state(State.WORKING):
		_start_computer_interaction()
		_working_timer = float(Config.get_value("behavior", "stub_work_seconds", 5.0))  # Extended work time


func stop_work() -> void:
	print("[Behavior] Work stop request received")
	if state == State.WORKING:
		_exit_working()


func _start_computer_interaction() -> void:
	if not computer_controller:
		print("[Behavior] Error: No computer controller found")
		_force_state(State.IDLE)
		return
	
	# Get computer interaction position
	_computer_interaction_target = computer_controller.get_interaction_position()
	_computer_facing = computer_controller.get_interaction_facing()
	
	print("[Behavior] Moving to computer at ", _computer_interaction_target)
	_force_state(State.WALKING)
	calypso.walk_to(_computer_interaction_target)


func _exit_working() -> void:
	# Turn off computer when exiting work state
	if computer_controller and computer_controller.is_on_state():
		computer_controller.turn_off()
	
	_force_state(State.IDLE)
	calypso.play_idle()  # Switch back to idle animation
	_schedule_next_activity()


func _on_arrived() -> void:
	if _sleep_pending:
		_sleep_pending = false
		_enter_sleep()
		return
		
	if state == State.WALKING:
		match _get_previous_state_target():
			"computer":
				# Arrived at computer, start interaction
				_arrive_at_computer()
			"bed":
				# Arrived at bed, go to sleep
				_enter_sleep()
			_:
				# Random walk completed
				_force_state(State.IDLE)
				_schedule_next_activity()


func _on_path_failed() -> void:
	print("[Behavior] Path failed, returning to idle")
	_sleep_pending = false
	_force_state(State.IDLE)
	_schedule_next_activity()


func _arrive_at_computer() -> void:
	print("[Behavior] Arrived at computer")
	
	# Set correct facing direction
	match _computer_facing:
		"left":
			calypso.facing = calypso.Facing.LEFT
		"right":
			calypso.facing = calypso.Facing.RIGHT
		"up":
			calypso.facing = calypso.Facing.UP
		"down":
			calypso.facing = calypso.Facing.DOWN
	
	# Play typing animation
	calypso.play_typing()
	
	# Turn on computer
	if computer_controller:
		computer_controller.turn_on()
	
	print("[Behavior] Computer interaction started")


func _get_previous_state_target() -> String:
	# Determine what we were walking to
	if _sleep_pending:
		return "bed"
	if state == State.WORKING or _working_timer > 0:
		return "computer"
	return "random"


func _on_computer_state_changed(is_on: bool) -> void:
	print("[Behavior] Computer state changed: ", "ON" if is_on else "OFF")


func _on_computer_request_work() -> void:
	request_work()


func _on_computer_stop_work() -> void:
	stop_work()


# Time-based behavior
func _on_hour_changed(hour: int) -> void:
	var end_hour := int(Config.get_value("time", "active_end_hour", 21.0))
	var start_hour := int(Config.get_value("time", "active_start_hour", 6.0))
	
	if hour == end_hour and state != State.SLEEPING:
		print("[Time] ", hour, ":00 - Bedtime")
		_go_sleep()
	elif hour == start_hour and state == State.SLEEPING:
		print("[Time] ", hour, ":00 - Wake up")
		_wake_up()


func _go_sleep() -> void:
	if state == State.SLEEPING:
		return
	
	print("[Behavior] Going to sleep")
	
	# If working, stop work first
	if state == State.WORKING:
		stop_work()
		# Wait a bit before going to bed
		await get_tree().create_timer(1.0).timeout
	
	# Clear any pending activities
	_sleep_pending = false
	
	# Start walking to bed
	var bed_position := NavManager.get_position("bed")
	print("[Behavior] Moving to bed at ", bed_position)
	_force_state(State.WALKING)
	calypso.walk_to(bed_position)


func _enter_sleep() -> void:
	print("[Behavior] Entering sleep state")
	_force_state(State.SLEEPING)
	calypso.play_sleep()


func _wake_up() -> void:
	print("[Behavior] Waking up")
	_force_state(State.IDLE)
	calypso.wake_up()
	_schedule_next_activity()


# Random activity
func _start_random_walk() -> void:
	if not _try_set_state(State.WALKING):
		return
	var target := NavManager.get_random_walkable_position(_rng)
	print("[Behavior] Random walk to ", target)
	calypso.walk_to(target)


func _schedule_next_activity() -> void:
	var rng_range: Array = Config.get_value("behavior", "walk_interval_range", [6.0, 15.0])
	_idle_timer = _rng.randf_range(float(rng_range[0]), float(rng_range[1]))
	print("[Behavior] Next activity scheduled in ", _idle_timer, " seconds")


# State management
func _try_set_state(new_state: int) -> bool:
	if state == new_state:
		return true
	if PRIORITY[new_state] < PRIORITY[state]:
		print("[Behavior] Cannot set state ", new_state, " - current priority ", state, " is higher")
		return false
	_force_state(new_state)
	return true


func _force_state(new_state: int) -> void:
	if state == new_state:
		return
	_previous_state = state
	var old_state = state
	state = new_state
	print("[Behavior] State changed: ", _state_to_string(old_state), " -> ", _state_to_string(new_state))
	state_changed.emit(state)


func _state_to_string(state_code: int) -> String:
	match state_code:
		State.IDLE: return "IDLE"
		State.WALKING: return "WALKING"
		State.SLEEPING: return "SLEEPING"
		State.WORKING: return "WORKING"
		State.FISHING: return "FISHING"
		return "UNKNOWN"


# Debug and testing
func force_test_work() -> void:
	"""Debug function - F9 key"""
	print("[Behavior] DEBUG: Force test work")
	request_work()


func force_test_sleep() -> void:
	"""Debug function - F10 key"""
	print("[Behavior] DEBUG: Force test sleep")
	_go_sleep()
