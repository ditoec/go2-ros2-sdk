# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

A ROS2 SDK for the Unitree GO2 quadruped robot (AIR/PRO/EDU variants). It bridges the robot to ROS2 over Wi-Fi (WebRTC via `aiortc`) or Ethernet (CycloneDDS). Capabilities include: joint/IMU state sync, LiDAR point clouds, camera feed, SLAM (`slam_toolbox`), autonomous navigation (Nav2), object detection (PyTorch/COCO), joystick teleop, and multi-robot support.

Tested on Ubuntu 22.04 with ROS2 Humble and Jazzy.

## Build Commands

```bash
# One-time setup (inside ros2_ws with this repo cloned to src/)
source /opt/ros/$ROS_DISTRO/setup.bash
cd src
pip install -r requirements.txt        # numpy==1.26.4 pinned; open3d requires Python ≤3.11
cd ..
rosdep install --from-paths src --ignore-src -r -y
colcon build

# After build
source install/setup.bash
```

**Python version**: `numpy==1.26.4` is pinned. Python 3.10–3.11 recommended; 3.12+ may have compatibility issues with some deps.

## Connection Modes

| `CONN_TYPE` | Transport | When to use |
|---|---|---|
| `webrtc` (default) | Wi-Fi via aiortc | External PC on same Wi-Fi as robot |
| `cyclonedds` | Ethernet / native DDS | GO2 EDU Ethernet port or onboard Jetson |

**WebRTC**: close the Unitree mobile app before connecting — only one WebRTC client is allowed at a time.

**CycloneDDS**:
 subscriptions are wired up but all three data callbacks are currently empty stubs (`pass`). Use WebRTC onboard the Jetson as a working alternative until CycloneDDS is implemented.

Full details, GO2 variant table, and Jetson deployment notes: [docs/connection-modes.md](docs/connection-modes.md).

## Running the System

For a per-capability verification checklist (topics to echo, commands to run, hardware vs simulation differences for each feature): [docs/testing-capabilities.md](docs/testing-capabilities.md).

```bash
export ROBOT_IP="192.168.x.x"     # comma-separated for multi-robot
export CONN_TYPE="webrtc"          # or "cyclonedds" for Ethernet
ros2 launch go2_robot_sdk robot.launch.py

# Optional env vars
export ROBOT_TOKEN="..."           # API token if required
export MAP_SAVE=True               # save .ply pointcloud every 10s
export MAP_NAME="3d_map"           # .ply filename prefix
export OPENAI_API_KEY="..."        # for TTS (openai), STT (openai), and voice NLU
export ELEVENLABS_API_KEY="..."    # alternative TTS — set TTS_PROVIDER=elevenlabs
export GEMINI_API_KEY="..."        # Gemini TTS/STT/NLU — set TTS_PROVIDER/STT_PROVIDER/NLU_PROVIDER=gemini
# TTS_PROVIDER=piper is the default (offline neural TTS, no key, model pre-baked in Docker image)
# TTS_PROVIDER=espeak is the legacy fallback (robotic quality, no model download required)
# Override to openai/elevenlabs/gemini for cloud-quality voices
export ANTHROPIC_API_KEY="..."     # Claude NLU only — set NLU_PROVIDER=claude (no TTS/STT support)
```

**Individual nodes** (run after main launch):
```bash
# YOLO object detection (model downloaded on first run to ~/.cache/ultralytics/)
ros2 run yolo_detector yolo_detector_node \
    --ros-args -p model:=yolo11n.pt -p device:=cpu -p detection_threshold:=0.5
# Simulation: remap camera topic
ros2 run yolo_detector yolo_detector_node \
    --ros-args -r /camera/image_raw:=/go2_camera/color/image
ros2 run image_tools showimage --ros-args -r /image:=/annotated_image
```

**Docker** (ROS Jazzy base, VNC included):
```bash
cd docker

# Windows 11 — Docker Desktop + WSL2 (hardware mode)
ROBOT_IP=<IP> CONN_TYPE=webrtc docker-compose up

# Windows 11 — Docker Desktop + WSL2 (simulation, no robot required)
USE_SIM=true docker-compose up

# Windows 11 — with microphone for STT
# Route 1 (WSLg PulseAudio — may fail due to UID mismatch, see docs/docker.md)
ENABLE_STT=true ROBOT_IP=<IP> \
  docker-compose -f docker/docker-compose.yml -f docker/docker-compose.windows.yml up
# Route 2 (browser mic bridge — always works, open http://localhost:8888 after container starts)
ENABLE_STT=true ROBOT_IP=<IP> docker-compose up

# Jetson NX 16 GB — ARM64 + CUDA
ROBOT_IP=<IP> \
  docker-compose -f docker/docker-compose.yml -f docker/docker-compose.jetson.yml up

# VNC: connect to localhost:5901, password "ros2vnc" (override: VNC_PASSWORD=... docker-compose up)
```

Override files: `docker-compose.windows.yml` (WSLg mic on Windows 11), `docker-compose.jetson.yml` (Jetson NX 16 GB, ARM64+CUDA). Full env var reference, platform guide, recipes, and troubleshooting: [docs/docker.md](docs/docker.md). Simulation-specific details: [docs/simulation.md](docs/simulation.md).

## Simulation (Gazebo)

The hardware path is **never needed** for simulation. The `go2_sim` package (included in this repo) provides a self-contained Gazebo Harmonic simulation — no external clone required.

**Run simulation** (all SDK features — Nav2, SLAM, RViz, joystick — work unchanged):
```bash
colcon build && source install/setup.bash
ros2 launch go2_robot_sdk simulation.launch.py

# Optional: choose a different Gazebo world (default: cafe.world)
ros2 launch go2_robot_sdk simulation.launch.py world:=go2_empty.sdf
```

## Switching Between Simulation and Hardware

| Method | Hardware (real robot) | Simulation (Gazebo) |
|---|---|---|
| **Bare metal** | `export ROBOT_IP="192.168.x.x"` then `ros2 launch go2_robot_sdk robot.launch.py` | `ros2 launch go2_robot_sdk simulation.launch.py` |
| **Windows 11** | `ROBOT_IP=<IP> docker-compose up` | `USE_SIM=true docker-compose up` |
| **Jetson NX 16 GB** | `ROBOT_IP=<IP> docker-compose -f docker/docker-compose.yml -f docker/docker-compose.jetson.yml up` | `USE_SIM=true docker-compose -f docker/docker-compose.yml -f docker/docker-compose.jetson.yml up` |

All downstream nodes (Nav2, SLAM, RViz, joystick, yolo_detector) work identically in both modes. See [docs/simulation.md](docs/simulation.md) for the topic bridge details.

---

**Switch between sim and real robot (bare metal)**:
```bash
# Real robot
export ROBOT_IP="192.168.x.x" && ros2 launch go2_robot_sdk robot.launch.py

# Simulation
ros2 launch go2_robot_sdk simulation.launch.py
```

**How it works**: `simulation.launch.py` delegates the entire Gazebo layer to `go2_sim` (an in-repo package). `go2_sim` starts Gazebo Harmonic, spawns the robot via `go2_description` xacro, runs the gait controller and odometry node, and publishes all topics at SDK root-level names — no namespace bridging needed. `simulation.launch.py` then starts the same Nav2/SLAM/RViz/joystick stack as the hardware launch. Nav2 uses `config/nav2_params_sim.yaml` (`use_sim_time: True` throughout).

Full architecture and Docker VNC details: [docs/simulation.md](docs/simulation.md).

## Architecture

The main package (`go2_robot_sdk`) uses Clean Architecture with four layers:

```
presentation/   → Go2DriverNode  (ROS2 node, entry point)
application/    → RobotDataService, RobotControlService  (orchestration)
infrastructure/ → WebRTCAdapter, ROS2Publisher, LiDAR decoder  (external systems)
domain/         → RobotConfig, RobotData, interfaces, math  (pure business logic)
```

**Data flow (WebRTC path)**:
1. `Go2Connection` (infrastructure/webrtc) receives raw WebRTC data channel messages and decoded LiDAR frames.
2. `WebRTCAdapter` dispatches messages via `_on_data_channel_message` → calls `RobotDataService.process_webrtc_message()`.
3. `RobotDataService` inspects the `topic` field against `RTC_TOPIC` constants, constructs `RobotData` entities, and calls the appropriate `IRobotDataPublisher` method.
4. `ROS2Publisher` (infrastructure/ros2) converts entities to ROS2 message types and publishes to the topics listed below.

**Entry point**: `go2_robot_sdk/main.py` runs `main_async()`, which spins the ROS2 node in a thread while running `WebRTCAdapter` connection tasks in the asyncio event loop. The event loop is created once and shared — `Go2DriverNode` receives it as `event_loop` to schedule callbacks thread-safely.

**Multi-robot**: `ROBOT_IP="ip1,ip2"` creates one `Go2Connection` per IP (indexed by `robot_id` string). Topics are namespaced per robot in multi mode; the URDF switches to `multi_go2.urdf`.

## Key ROS2 Topics

| Topic | Type | Direction |
|---|---|---|
| `/go2_state` | `go2_interfaces/Go2State` | published |
| `/joint_states` | `sensor_msgs/JointState` | published (1 Hz, firmware limit) |
| `/imu` | `go2_interfaces/IMU` | published |
| `/odom` | `nav_msgs/Odometry` | published |
| `/camera/image_raw` | `sensor_msgs/Image` | published (hardware); sim uses `/go2_camera/color/image` via bridge |
| `/camera/camera_info` | `sensor_msgs/CameraInfo` | published |
| `/point_cloud2` | `sensor_msgs/PointCloud2` | published (~7 Hz) |
| `/scan` | `sensor_msgs/LaserScan` | published (from pointcloud_to_laserscan) |
| `/cmd_vel_out` | `geometry_msgs/Twist` | consumed by driver (twist_mux output) |
| `/webrtc_req` | `go2_interfaces/WebRtcReq` | consumed (send robot API commands) |
| `/detected_objects` | `vision_msgs/Detection2DArray` | published by yolo_detector |
| `/speech_text` | `std_msgs/String` | published by stt_node or mic_bridge_node (enable with `ENABLE_STT=true`) |
| `/cmd_vel_voice` | `geometry_msgs/Twist` | published by voice_cmd_node → twist_mux priority 7 |

## Package Layout

| Package | Build type | Purpose |
|---|---|---|
| `go2_robot_sdk` | `ament_python` | Main driver, launch files, URDF, config |
| `go2_interfaces` | `ament_cmake` | 32 custom ROS2 message definitions |
| `go2_sim` | `ament_python` | Self-contained Gazebo simulation (gait controller, odometry, sensor bridge) |
| `go2_description` | `ament_cmake` | Robot xacro/URDF + meshes used by go2_sim |
| `quadropted_msgs` | `ament_cmake` | Custom msgs for gait controller (`RobotVelocity`, `RobotModeCommand`, etc.) |
| `lidar_processor` | `ament_python` | Python LiDAR → PointCloud2 nodes |
| `lidar_processor_cpp` | `ament_cmake` | C++/PCL alternative LiDAR nodes |
| `yolo_detector` | `ament_python` | YOLOv11 (Ultralytics) object detection |
| `speech_processor` | `ament_python` | TTS (`openai`/`elevenlabs`/`gemini`), STT (`openai`/`faster_whisper`/`vosk`/`gemini`), browser mic bridge (`mic_bridge_node`, port 8888/8889), voice commands (`keyword`/`openai`/`gemini`/`claude` NLU) |

## Extending the SDK

### New robot commands

Add the ID to `ROBOT_CMD` in `go2_robot_sdk/domain/constants/robot_commands.py` and the topic string to `RTC_TOPIC` in `webrtc_topics.py` if it uses a new topic. Then send via CLI or code — no driver changes needed:
```bash
ros2 topic pub /webrtc_req go2_interfaces/msg/WebRtcReq \
    "{api_id: 1016, topic: 'rt/api/sport/request'}" --once
```

### New inbound WebRTC data type

All inbound routing goes through `RobotDataService.process_webrtc_message()`. To handle a new topic, follow this four-file chain in order:

1. `application/services/robot_data_service.py` — add `elif topic == RTC_TOPIC["X"]:` branch, call `_process_x()` to populate `robot_data`, then call `self.publisher.publish_x(robot_data)`.
2. `domain/entities/robot_data.py` — add a typed dataclass for the new data and an `Optional` field on `RobotData`.
3. `domain/interfaces/robot_data_publisher.py` — add `publish_x()` as an abstract method on `IRobotDataPublisher`.
4. `infrastructure/ros2/ros2_publisher.py` — implement `publish_x()`, constructing the ROS2 message from entity fields.

**Never add `rclpy` or ROS2 message imports to `domain/` or `application/`.** Those layers must stay testable without a ROS2 environment.

### Sim robot commands

In simulation, publish to `/sim_cmd` (`go2_interfaces/msg/WebRtcReq`) — same message type as `/webrtc_req` on hardware, same `api_id` values:
```bash
ros2 topic pub /sim_cmd go2_interfaces/msg/WebRtcReq "{api_id: 1009}" --once  # Sit
ros2 topic pub /sim_cmd go2_interfaces/msg/WebRtcReq "{api_id: 1004}" --once  # StandUp
ros2 topic pub /sim_cmd go2_interfaces/msg/WebRtcReq "{api_id: 1011, parameter: '1'}" --once  # TROT
ros2 topic pub /sim_cmd go2_interfaces/msg/WebRtcReq "{api_id: 1013, parameter: '0.10'}" --once  # BodyHeight +10cm
ros2 topic pub /sim_cmd go2_interfaces/msg/WebRtcReq "{api_id: 1015, parameter: '2'}" --once  # SpeedLevel fast
```
Handled by `go2_sim/scripts/sim_cmd_node.py`, started automatically by `go2_sim.launch.py`. See `docs/testing-capabilities.md` section 7 for the full api_id table.

### New standalone ROS2 node

Use `yolo_detector` as a template (`ament_python` package). If the node only consumes existing topics, no driver changes are needed. If it must send robot commands, publish to `/webrtc_req` (hardware) or `/sim_cmd` (simulation).

### New custom message type

1. Create `go2_interfaces/msg/MyMessage.msg`.
2. Register it in `go2_interfaces/CMakeLists.txt` under `rosidl_generate_interfaces`.
3. Rebuild: `colcon build --packages-select go2_interfaces`.

### New launch argument

Add a `DeclareLaunchArgument` in `Go2NodeFactory.create_launch_arguments()` inside `robot.launch.py`, then gate the corresponding node with `IfCondition(LaunchConfiguration('my_arg'))`.

### Tests

- **Unit** (`test/unit/`) — pure `pytest`, no `rclpy`. Mock `IRobotDataPublisher` with a stub to test `application/` logic in isolation.
- **Integration** (`test/integration/`) — call `rclpy.init()` / `rclpy.shutdown()` once per module via a `pytest` fixture.

```bash
colcon test --packages-select go2_robot_sdk
colcon test-result --all --verbose
```

CI (`ros_build.yaml`) skips tests — only the build is verified automatically.

## CI

GitHub Actions (`.github/workflows/ros_build.yaml`) runs `colcon build` (tests skipped) against ROS2 Humble and Jazzy on every push/PR to `master`. No lint step is configured.

## ROS2 Development Guidelines

General ROS2 rules, node patterns, communication standards, testing strategy, and Clean Architecture enforcement are defined in [.claude/CLAUDE.md](.claude/CLAUDE.md) and auto-loaded rule files:

| Rule File | Covers |
|---|---|
| [.claude/rules/clean_architecture.md](.claude/rules/clean_architecture.md) | Layer dependency rules, anti-patterns |
| [.claude/rules/ros2_general.md](.claude/rules/ros2_general.md) | Package naming, file structure, launch, logging |
| [.claude/rules/ros2_nodes.md](.claude/rules/ros2_nodes.md) | Node base classes, publisher/subscriber patterns |
| [.claude/rules/ros2_communication.md](.claude/rules/ros2_communication.md) | Topic naming, QoS profiles, TF2 |
| [.claude/rules/robot_specific.md](.claude/rules/robot_specific.md) | URDF, Nav2, sensor integration, WebRTC commands |
| [.claude/rules/testing.md](.claude/rules/testing.md) | Unit, integration, E2E test patterns |

Skill templates for common tasks (node creation, lifecycle, services, TF2, diagnostics, bag recording) are in [.claude/skills/](.claude/skills/).

ROS2 CLI quick reference is available as a custom command: [.claude/commands/ros2.md](.claude/commands/ros2.md).
