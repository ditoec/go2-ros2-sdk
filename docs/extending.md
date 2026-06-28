# Extending the SDK

## Adding a New ROS2 Node

Follow the Clean Architecture rules:

1. If the node only consumes or republishes existing ROS2 topics, add it as a standalone `ament_python` package (see `yolo_detector` as a template).
2. If the node needs to send commands to the robot, publish to `/webrtc_req` (`go2_interfaces/msg/WebRtcReq`) — no driver modification needed.
3. If the node must hook into the driver's data pipeline (e.g., to process raw LiDAR before it reaches ROS2), implement `IRobotDataPublisher` in `infrastructure/ros2/` and inject it via `Go2DriverNode`.

**Never add ROS2 imports to `domain/` or `application/`.** Those layers must remain testable without a ROS2 environment.

## Adding a New Robot Command

```python
# 1. go2_robot_sdk/domain/constants/robot_commands.py
ROBOT_CMD = {
    ...
    "MyCommand": 1099,   # add your ID
}

# 2. go2_robot_sdk/domain/constants/webrtc_topics.py
RTC_TOPIC = {
    ...
    "MY_TOPIC": "rt/api/myfeature/request",   # add only if new topic
}
```

Then publish via CLI or code:
```bash
ros2 topic pub /webrtc_req go2_interfaces/msg/WebRtcReq \
  "{api_id: 1099, topic: 'rt/api/sport/request'}" --once
```

## Processing a New WebRTC Message Type

`RobotDataService.process_webrtc_message()` in `application/services/robot_data_service.py` is the single routing point for all inbound robot data.

To handle a new topic:

```python
elif topic == RTC_TOPIC["MY_NEW_TOPIC"]:
    self._process_my_data(msg, robot_data)
    self.publisher.publish_my_data(robot_data)
```

Then:
1. Add `_process_my_data()` to `RobotDataService` — populate fields on `robot_data`.
2. Add a new typed field to `RobotData` in `domain/entities/robot_data.py` if the data doesn't fit an existing dataclass.
3. Add `publish_my_data()` to `IRobotDataPublisher` in `domain/interfaces/robot_data_publisher.py`.
4. Implement `publish_my_data()` in `ROS2Publisher` in `infrastructure/ros2/ros2_publisher.py`.

## Adding a Voice Command

### Option A — YAML custom commands (no code changes, operator-friendly)

Edit `speech_processor/config/custom_commands.yaml` (or the file pointed to by
`CUSTOM_COMMANDS_FILE`) and hot-reload without restarting:

```yaml
custom_commands:
  my_command:
    trigger_en: "go to reception, reception desk"
    trigger_id: "ke resepsionis, antar ke resepsionis"
    action_type: navigate_to_room   # api_id | navigate_to_room | patrol_start |
    room: reception                  # patrol_stop | follow_start | follow_stop |
    feedback_en: "Heading to reception"  # approach_object
    feedback_id: "Menuju resepsionis"
```

```bash
ros2 topic pub /reload_custom_commands std_msgs/Empty "{}" --once
```

Custom commands are matched before the built-in table — use longer, specific phrases
to avoid collisions. Supported `action_type` values: `api_id`, `navigate_to_room`,
`patrol_start`, `patrol_stop`, `follow_start`, `follow_stop`, `approach_object`.

### Option B — Hard-coded command (developer path, all NLU providers)

To add a truly new command type that needs to be available to every NLU path
(keyword regex, cloud LLM, and unified Gemma), edit `command_dispatcher.py`:

1. Add the command key → action to `CMD_MAP` (an `{"api_id", "parameter"}` dict, a
   `("move", lin, ang)` tuple, or `"hw_only": True` for hardware-only gestures).
2. Add a spoken-feedback string to `FEEDBACK_MAP`.
3. For Indonesian (`VOICE_LANG=id`), add the phrase(s) to `COMMAND_GLOSSARY` so the
   deterministic `command_for_text()` fallback can map it.

The command then works across `voice_cmd_node`, `mic_bridge_node`, and `stt_node`
with no further changes — `command` is grammar-constrained to the `CMD_MAP` keys in
the unified tool schema.

## Adding a Custom Message Type

1. Create `go2_interfaces/msg/MyMessage.msg`.
2. Register it in `go2_interfaces/CMakeLists.txt` under `rosidl_generate_interfaces`.
3. Rebuild: `colcon build --packages-select go2_interfaces`.
4. Import in Python: `from go2_interfaces.msg import MyMessage`.

## Adding a New Launch Argument

`robot.launch.py` uses `Go2NodeFactory.create_launch_arguments()` to declare arguments. Add a `DeclareLaunchArgument` there and a corresponding `IfCondition`-gated node in the factory's create methods.

## Writing Tests

The architecture is designed for testability:

- **Domain / Application tests** (`test/unit/`) — pure `pytest`, no `rclpy`. Mock `IRobotDataPublisher` with a simple stub.
- **Node integration tests** (`test/integration/`) — require `rclpy.init()`. Use `pytest` fixtures; see `.claude/rules/testing.md` for the pattern.

Run tests:
```bash
colcon test --packages-select go2_robot_sdk
colcon test-result --all --verbose
```

CI skips tests (`skip-tests: true` in `.github/workflows/ros_build.yaml`) — only build is verified in CI.
