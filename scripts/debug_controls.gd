extends Node

## Debug controls for Life Simulation v0.2
## Provides keyboard shortcuts for testing behaviors

func _ready() -> void:
	print("[DebugControls] Initialized")
	set_process_input(true)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		match event.physical_keycode:
			KEY_F8:
				# F8: Fast time test
				_fast_time_test()
			KEY_F9:
				# F9: Go to computer
				_go_to_computer()
			KEY_F10:
				# F10: Go to sleep
				_go_to_sleep()
			KEY_F11:
				# F11: Force wake up
				_force_wake_up()
			KEY_F12:
				# F12: Reset to idle
				_reset_to_idle()


func _fast_time_test() -> void:
	print("[DebugControls] F8: Fast time test")
	
	# Fast forward 3 hours to test time-based events
	var current_hour = TimeManager.current_hour
	var target_hour = current_hour + 3.0
	
	if target_hour >= 24.0:
		target_hour -= 24.0
		TimeManager.day += 1
	
	TimeManager.current_hour = target_hour
	print("[DebugControls] Time set to ", TimeManager.format_time(), " (day ", TimeManager.day, ")")


func _go_to_computer() -> void:
	print("[DebugControls] F9: Go to computer")
	var behavior_manager = get_tree().get_first_node_in_group("behavior_manager")
	if behavior_manager:
		behavior_manager.force_test_work()
	else:
		print("[DebugControls] Error: BehaviorManager not found")


func _go_to_sleep() -> void:
	print("[DebugControls] F10: Go to sleep")
	var behavior_manager = get_tree().get_first_node_in_group("behavior_manager")
	if behavior_manager:
		behavior_manager.force_test_sleep()
	else:
		print("[DebugControls] Error: BehaviorManager not found")


func _force_wake_up() -> void:
	print("[DebugControls] F11: Force wake up")
	var behavior_manager = get_tree().get_first_node_in_group("behavior_manager")
	if behavior_manager:
		# Force state to IDLE if sleeping
		if behavior_manager.state == behavior_manager.State.SLEEPING:
			behavior_manager._wake_up()
	else:
		print("[DebugControls] Error: BehaviorManager not found")


func _reset_to_idle() -> void:
	print("[DebugControls] F12: Reset to idle")
	var behavior_manager = get_tree().get_first_node_in_group("behavior_manager")
	if behavior_manager:
		# Force state to IDLE
		behavior_manager._force_state(behavior_manager.State.IDLE)
		# Schedule next activity
		behavior_manager._schedule_next_activity()
	else:
		print("[DebugControls] Error: BehaviorManager not found")


func print_status() -> void:
	var behavior_manager = get_tree().get_first_node_in_group("behavior_manager")
	if behavior_manager:
		print("=== Current Status ===")
		print("Time: ", TimeManager.format_time(), " (Day ", TimeManager.day, ")")
		print("State: ", _state_to_string(behavior_manager.state))
		print("Position: ", behavior_manager.calypso.global_position if behavior_manager.calypso else "N/A")
		
		if behavior_manager.computer_controller:
			print("Computer: ", "ON" if behavior_manager.computer_controller.is_on_state() else "OFF")
		
		print("Next activity in: ", behavior_manager._idle_timer, " seconds")
	else:
		print("[DebugControls] BehaviorManager not found for status")


func _state_to_string(state_code: int) -> String:
	match state_code:
		0: return "IDLE"
		1: return "WALKING"
		2: return "SLEEPING"
		3: return "WORKING"
		4: return "FISHING"
		return "UNKNOWN"
