# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

A ROS2 SDK for the Unitree GO2 quadruped robot (AIR/PRO/EDU variants). It bridges the robot to ROS2 over Wi-Fi (WebRTC via `aiortc`) or Ethernet (CycloneDDS). Capabilities include: joint/IMU state sync, LiDAR point clouds, camera feed, SLAM (`slam_toolbox`), autonomous navigation (Nav2), object detection (PyTorch/COCO), joystick teleop, and multi-robot support.

Tested on Ubuntu 22.04 with ROS2 Humble.

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
Fully implemented. Subscribes to `/sportmodestate` (50 Hz), `/lowstate` (500 Hz), `/utlidar/robot_pose`, `/utlidar/cloud`, and `/wirelesscontroller`. Commands are routed via `CycloneDDSAdapter` → `/api/sport/request`.

Docker (env vars pre-configured in `docker-compose.yml`):
```bash
CONN_TYPE=cyclonedds RMW_IMPLEMENTATION=rmw_cyclonedds_cpp CYCLONEDDS_IFACE=eth0 docker-compose up
```

Bare metal:
```bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file://$(pwd)/config/cyclonedds.xml
export CYCLONEDDS_IFACE=eth0   # change to your Ethernet interface
export CONN_TYPE=cyclonedds
ros2 launch go2_robot_sdk robot.launch.py
```

Full details, GO2 variant table, and Jetson deployment notes: [docs/connection-modes.md](docs/connection-modes.md).

## Running the System

For a per-capability verification checklist (topics to echo, commands to run, hardware vs simulation differences for each feature): [docs/testing-capabilities.md](docs/testing-capabilities.md).

```bash
export ROBOT_IP="192.168.x.x"     # comma-separated for multi-robot
export CONN_TYPE="webrtc"          # or "cyclonedds" for Ethernet
ros2 launch go2_robot_sdk robot.launch.py

# Optional env vars
export ROBOT_TOKEN="..."           # API token if required
export ENABLE_WEBRTC_CAMERA=true   # CONN_TYPE=cyclonedds only: also open a WebRTC session (needs
                                   # ROBOT_IP set to the robot's internal IP) purely for camera video
                                   # (/camera/image_raw) — commands/state stay CycloneDDS-owned.
                                   # Requires closing the Unitree mobile app first (one WebRTC
                                   # client at a time, robot-side limit — applies even onboard).
export MAP_SAVE=True               # save .ply pointcloud every 10s
export MAP_NAME="3d_map"           # .ply filename prefix
export ENABLE_BAG=True             # record a timestamped rosbag2 session for debugging → ./bags
                                   # BAG_TOPICS=-a also captures camera+LiDAR; BAG_STORAGE overrides backend
export VOICE_LANG=id               # master language knob: en (default) | id — focuses STT+NLU+TTS
                                   # on one language; robot command output always stays English
export LOOK_PATH_PRIORITY=yolo,openai,gemma  # `look_around` tool (openai_realtime only): the model
                                   # calls it when asked to look at, find, or count something, and the
                                   # node answers from the cheapest path holding FRESH data (VISION_TTL=5s):
                                   #   yolo   -- /detected_objects. Instant and free, but only offered when
                                   #             the question names a COCO class ("is there a person",
                                   #             "find the ball"); an open question skips it, since an
                                   #             object list is not scene understanding.
                                   #   openai -- the camera frame attached to the live Realtime session.
                                   #             Best reasoning (reads text, judges context) but costs
                                   #             image tokens per look.
                                   #   gemma  -- /scene_description from gemma_vision_node. Offline and
                                   #             free, but slow on a Jetson.
                                   # When no path has fresh data the robot says it cannot see rather than
                                   # inventing a scene. CAMERA_TOPIC=/camera/image_raw · VISION_TTL=5.0
export STT_SOURCE=auto             # auto (default) | mic | robot. auto picks the best microphone
                                   # available and re-checks every STT_SOURCE_PROBE_SEC=10, so
                                   # plugging one in takes effect without a restart:
                                   #   1. Bluetooth headset mic (bluez_source.*)
                                   #   2. USB mic on the Jetson (alsa_input.usb-*)
                                   #   3. the robot's own mic (/robot_audio) — noisiest, so last
                                   # Tiers 1-2 read the host's PulseAudio via PULSE_SERVER and only
                                   # apply to stt_node, i.e. they need MIC_BRIDGE=false; the browser
                                   # bridge has its own two sources (browser mic / robot mic).
                                   # Order is configurable: STT_SOURCE_PRIORITY=bluez_source,usb
                                   # NOTE: a Bluetooth mic needs the headset's HSP/HFP profile, which
                                   # is mono narrowband AND cannot coexist with A2DP — enabling it
                                   # drops TTS output quality to phone-call grade. Many earbuds also
                                   # report HSP as unavailable under BlueZ 5.53 without oFono.
                                   # See docs/bluetooth-audio.md.
                                   # robot — use the GO2's onboard mic (driver
                                   # republishes it on /robot_audio). CONN_TYPE=webrtc reads the WebRTC
                                   # audio track (needs MIC_BRIDGE=false); CONN_TYPE=cyclonedds decodes
                                   # the robot's native /audiosender DDS topic (Opus) instead — see
                                   # docs/connection-modes.md#audio-topics-cyclonedds-mode
export ENABLE_FACE=true            # start face_recognition_node + face_enrollment_node (Modul 4.2):
                                   # InsightFace SCRFD+ArcFace → /recognized_faces + /recognized_face_names;
                                   # voice_cmd_node proactively greets newly-seen known faces on /tts
                                   # ("Hello, <name>!"), independent of the person speaking first (4.4)
                                   # FACE_DEVICE=cpu (default) | cuda (Jetson) · FACE_MODEL_PACK=buffalo_sc · FACE_THRESHOLD=0.35
                                   # GREET_COOLDOWN_SEC=60 — seconds before the same recognized name is greeted
                                   # again. The clock runs from the last greeting OR the last exchange, whichever
                                   # is later, and greetings are suppressed outright while the robot is speaking —
                                   # so a conversation is never interrupted by a "Hello, <name>!".
                                   # While a known face is in sight, replies and command feedback also address
                                   # them by name ("Hello Dito, ..." / "Stopping movement, Dito"). Canned command
                                   # feedback is only personalized when exactly ONE person is recognized, since the
                                   # robot cannot tell which of several visible people actually spoke.
                                   # FACE_CONTEXT_TTL=30 — seconds a sighting stays valid for naming/grounding
                                   # Enrollment UI: http://localhost:8890 — webcam capture or photo upload, type a name, Enroll;
                                   # DB persists to ./face_db (bind-mounted). Threshold slider publishes /face_threshold live.
                                   # `ros2 topic pub /reload_faces std_msgs/Empty "{}" --once` to re-scan without restarting.
                                   # FACE_ENROLL_PORT=8890 (enrollment UI port)
                                   # NOTE: buffalo_* weights are licensed non-commercial-research only — see docs/proposal-face-recognition.md
export CAM_BRIDGE=true             # stream host browser webcam → /camera/image_raw (Windows Docker / dev without robot).
                                   # Open http://localhost:8891 in your browser after start, click Connect → Start Streaming.
                                   # face_recognition_node + yolo_detector subscribe to /camera/image_raw unchanged.
                                   # Default true in docker-compose.windows-gpu.yml; false everywhere else.
                                   # CAM_BRIDGE_HTTP_PORT=8891 · CAM_BRIDGE_WS_PORT=8892 · CAM_BRIDGE_TOPIC=/camera/image_raw
export ENABLE_MIC_DIAGNOSTIC=true  # start mic_diagnostic_node: Record/Stop web UI (http://localhost:8893) to
                                   # capture /robot_audio and play it back in-browser — judge robot-mic audio
                                   # quality without SSH. Purely observational (subscribes only, publishes
                                   # nothing); needs STT_SOURCE=robot to have anything to record.
                                   # MIC_DIAGNOSTIC_HTTP_PORT=8893 · MIC_DIAGNOSTIC_WS_PORT=8894
                                   # MIC_DIAGNOSTIC_TOPIC=/robot_audio · MIC_DIAGNOSTIC_MAX_CAPTURE_S=60.0
export ENABLE_FOLLOW=true          # start follow_me_node (Modul 4.3): tracks the nearest person detected by YOLO
                                   # and publishes /cmd_vel_follow (twist_mux priority 6 — voice/joy always override).
                                   # Also auto-enables YOLO (ENABLE_YOLO=true).
                                   # Enable at runtime: ros2 topic pub /follow_enable std_msgs/Bool "{data: true}" --once
                                   # Voice commands: "ikuti saya" / "follow me" → enable; "berhenti" → disable
                                   # FOLLOW_LINEAR_SPEED=0.2 · FOLLOW_ANGULAR_KP=1.0 · FOLLOW_TARGET_AREA=0.10
export ENABLE_YOLO=false           # start yolo_detector_node standalone (without follow_me_node); auto-enabled by ENABLE_FOLLOW
                                   # YOLO_MODEL=yolo11n.pt · YOLO_DEVICE=cpu · YOLO_THRESHOLD=0.5
export ENABLE_NAV_WAYPOINT=true    # start nav_waypoint_node (Modul 5.2/5.3): /navigate_to_room (String) → Nav2 NavigateToPose goal
                                   # Requires Nav2 running (enable_nav2=true) and a saved SLAM map.
                                   # WAYPOINTS_FILE=go2_robot_sdk/config/waypoints.yaml (YAML: name→pose, edit after SLAM mapping)
                                   # NAV_TIMEOUT=120.0 — seconds to wait for Nav2 action server on startup
                                   # Reload waypoints live: ros2 topic pub /reload_waypoints std_msgs/Empty "{}" --once
                                   # Voice (keyword): "go to the lobby" / "ke lobi" → navigate; "stop" cancels current goal
                                   # Voice (LLM): LLM returns {"command":"go_to_room:lobby"} → dispatcher publishes /navigate_to_room
export ENABLE_BEHAVIOR_COORDINATOR=true  # start behavior_coordinator_node: observes /follow_enable, /navigation_status,
                                   # /cmd_vel_voice, /approach_status, /patrol_status;
                                   # publishes /behavior_mode (TRANSIENT_LOCAL) — IDLE | VOICE_MOVE | FOLLOWING | NAVIGATING | APPROACHING | PATROL.
                                   # Purely observational. BEHAVIOR_VEL_IDLE=0.6 — seconds of zero /cmd_vel_voice before VOICE_MOVE → IDLE
export ENABLE_PATROL=true          # start patrol_node (Modul 2.1): cycles through all waypoints in WAYPOINTS_FILE indefinitely.
                                   # Voice: "patroli" / "mulai patroli" → start; "hentikan patroli" → stop.
                                   # PATROL_ROUTE= comma-separated waypoint keys (empty=all); PATROL_SKIP_ON_FAILURE=true
                                   # Status topic: /patrol_status — "patrolling:<key>/<idx>/<total>", "patrol_done", "patrol_cancelled"
                                   # Reload waypoints: same /reload_waypoints topic shared with nav_waypoint_node
export ENABLE_APPROACH_OBJECT=true # start approach_object_node (Modul 2.1/2.2): one-shot visual servo toward a YOLO-detected object.
                                   # Set target: ros2 topic pub /approach_target std_msgs/String "{data: 'sports ball'}" --once
                                   # Voice: "dekati bola" → sports ball; "dekati kursi" → chair; "dekati orang" → person; etc.
                                   # Publishes /cmd_vel_follow (priority 6, same as follow_me_node; mutual exclusion enforced).
                                   # APPROACH_LINEAR_SPEED=0.25 · APPROACH_ANGULAR_KP=1.0 · APPROACH_MAX_ANGULAR=0.8
                                   # APPROACH_TARGET_AREA=0.12 (bbox fraction of image → stop) · APPROACH_LOST_TIMEOUT=2.0
                                   # Status topic: /approach_status — "approaching:<class>", "reached:<class>", "lost:<class>", "cancelled"
                                   # Custom commands (Modul 2.3): CUSTOM_COMMANDS_FILE=path/to/custom_commands.yaml (default: package config/)
                                   # Reload live: ros2 topic pub /reload_custom_commands std_msgs/Empty "{}" --once
export OPENAI_API_KEY="..."        # for TTS (openai), STT (openai), and voice NLU
export ELEVENLABS_API_KEY="..."    # alternative TTS — set TTS_PROVIDER=elevenlabs
export GEMINI_API_KEY="..."        # Gemini TTS/STT/NLU — set TTS_PROVIDER/STT_PROVIDER/NLU_PROVIDER=gemini
# TTS_PROVIDER=supertonic is the default (offline neural TTS, no key, model pre-baked in Docker image)
# Jetson image defaults to TTS_PROVIDER=piper instead (offline, subprocess binary, en/id voices
# pre-baked) -- supertonic has no Python 3.8 release, see docker/Dockerfile.jetson and tts_node.py
# Override to openai/elevenlabs/gemini for cloud-quality voices
# SUPERTONIC_LANG overrides the TTS language only (follows VOICE_LANG when unset)
export TTS_BLUETOOTH=true          # default. Speak through a connected Bluetooth speaker when one
                                   # is present, else fall back to the robot's own speaker (the
                                   # WebRTC audiohub path). tts_node re-probes PulseAudio every
                                   # TTS_BLUETOOTH_PROBE_SEC=5.0 s, so connecting or powering off a
                                   # speaker takes effect at runtime with no restart; any playback
                                   # failure also falls back rather than dropping the reply.
                                   # TTS_BLUETOOTH_SINK=bluez_sink -- substring matched against sink names
                                   # Set TTS_BLUETOOTH=false to always use the robot speaker.
                                   # HOST SETUP (once per machine) -- BlueZ and PulseAudio run on the
                                   # host while ROS2 runs in the container, so the container reaches
                                   # them over loopback TCP (network_mode: host):
                                   #   pactl load-module module-native-protocol-tcp listen=127.0.0.1 auth-anonymous=1
                                   # Add that line to /etc/pulse/default.pa to persist it. The container
                                   # side is PULSE_SERVER, already wired in docker-compose.yml.
                                   # On Jetson/JetPack two extra host fixes are required -- see
                                   # docs/bluetooth-audio.md (A2DP is disabled by default there).
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

**Docker** (ROS Humble base, VNC included):
```bash
cd docker

# Windows 11 — Docker Desktop + WSL2 (hardware mode)
ROBOT_IP=<IP> CONN_TYPE=webrtc docker-compose up

# Windows 11 — Docker Desktop + WSL2 (simulation, no robot required)
USE_SIM=true docker-compose up

# Windows 11 — with microphone for STT (browser mic bridge, no PulseAudio needed)
# After the container starts, open https://localhost:8888 in your browser
# (self-signed cert -- click through the one-time browser warning). HTTPS
# also means a LAN client (e.g. a laptop, not just the machine running
# Docker) can grant mic access -- plain HTTP only works from localhost,
# since browsers require a secure context for getUserMedia().
ENABLE_STT=true ROBOT_IP=<IP> docker-compose up

# Windows 11 + 8 GB GPU — Gemma 4 E4B for STT/NLU/vision via Ollama (offline, no API keys)
# Path A — faster_whisper STT + keyword NLU (no llama.cpp, instant start)
ENABLE_STT=true ROBOT_IP=<IP> \
  docker-compose -f docker/docker-compose.yml -f docker/docker-compose.windows-gpu.yml up

# Path B — Gemma unified pipeline (llama.cpp sidecar)
# GEMMA_SIZE=12b (default) — gemma-4-12b-it-Q4_0.gguf (~6.5 GB), higher quality, ~12-15 t/s
# GEMMA_SIZE=e4b            — gemma-4-E4B-it-Q4_K_M.gguf (~5 GB), faster (~30+ t/s), ~6.2 GB VRAM total
ENABLE_STT=true ROBOT_IP=<IP> COMPOSE_PROFILES=gemma \
  docker-compose -f docker/docker-compose.yml -f docker/docker-compose.windows-gpu.yml up
# Switch to E4B:
ENABLE_STT=true ROBOT_IP=<IP> GEMMA_SIZE=e4b COMPOSE_PROFILES=gemma \
  docker-compose -f docker/docker-compose.yml -f docker/docker-compose.windows-gpu.yml up

# Jetson NX 16 GB — ARM64 + CUDA
ROBOT_IP=<IP> \
  docker-compose -f docker/docker-compose.yml -f docker/docker-compose.jetson.yml up

# VNC: connect to localhost:5901, password "ros2vnc" (override: VNC_PASSWORD=... docker-compose up)
```

Override files: `docker-compose.jetson.yml` (Jetson NX 16 GB, ARM64+CUDA, `MIC_BRIDGE=false` so `stt_node` uses `/dev/snd`); `docker-compose.windows-gpu.yml` (Windows 11 + 8 GB GPU, Ollama sidecar running Gemma 4 E4B). Full env var reference, platform guide, recipes, and troubleshooting: [docs/docker.md](docs/docker.md). Simulation-specific details: [docs/simulation.md](docs/simulation.md).

## Simulation (Gazebo)

The hardware path is **never needed** for simulation. The `go2_sim` package (included in this repo) provides a self-contained Gazebo Fortress simulation — no external clone required.

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
| **Windows 11 + 8 GB GPU (Path A)** | `ROBOT_IP=<IP> ENABLE_STT=true docker-compose -f docker/docker-compose.yml -f docker/docker-compose.windows-gpu.yml up` | `USE_SIM=true ENABLE_STT=true docker-compose -f docker/docker-compose.yml -f docker/docker-compose.windows-gpu.yml up` |
| **Windows 11 + 8 GB GPU (Path B / Gemma 12B)** | `ROBOT_IP=<IP> ENABLE_STT=true COMPOSE_PROFILES=gemma docker-compose -f docker/docker-compose.yml -f docker/docker-compose.windows-gpu.yml up` | `USE_SIM=true ENABLE_STT=true COMPOSE_PROFILES=gemma docker-compose -f docker/docker-compose.yml -f docker/docker-compose.windows-gpu.yml up` |
| **Windows 11 + 8 GB GPU (Path B / Gemma E4B)** | `ROBOT_IP=<IP> ENABLE_STT=true GEMMA_SIZE=e4b COMPOSE_PROFILES=gemma docker-compose -f docker/docker-compose.yml -f docker/docker-compose.windows-gpu.yml up` | `USE_SIM=true ENABLE_STT=true GEMMA_SIZE=e4b COMPOSE_PROFILES=gemma docker-compose -f docker/docker-compose.yml -f docker/docker-compose.windows-gpu.yml up` |
| **Jetson NX 16 GB (Path A)** | `ROBOT_IP=<IP> docker-compose -f docker/docker-compose.yml -f docker/docker-compose.jetson.yml up` | `USE_SIM=true docker-compose -f docker/docker-compose.yml -f docker/docker-compose.jetson.yml up` |
| **Jetson NX 16 GB (Path B / Gemma 12B)** | `ROBOT_IP=<IP> COMPOSE_PROFILES=gemma docker-compose -f docker/docker-compose.yml -f docker/docker-compose.jetson.yml up` | `USE_SIM=true COMPOSE_PROFILES=gemma docker-compose -f docker/docker-compose.yml -f docker/docker-compose.jetson.yml up` |
| **Jetson NX 16 GB (Path B / Gemma E4B)** | `ROBOT_IP=<IP> GEMMA_SIZE=e4b COMPOSE_PROFILES=gemma docker-compose -f docker/docker-compose.yml -f docker/docker-compose.jetson.yml up` | `USE_SIM=true GEMMA_SIZE=e4b COMPOSE_PROFILES=gemma docker-compose -f docker/docker-compose.yml -f docker/docker-compose.jetson.yml up` |

All downstream nodes (Nav2, SLAM, RViz, joystick, yolo_detector) work identically in both modes. See [docs/simulation.md](docs/simulation.md) for the topic bridge details.

---

**Switch between sim and real robot (bare metal)**:
```bash
# Real robot
export ROBOT_IP="192.168.x.x" && ros2 launch go2_robot_sdk robot.launch.py

# Simulation
ros2 launch go2_robot_sdk simulation.launch.py
```

**How it works**: `simulation.launch.py` delegates the entire Gazebo layer to `go2_sim` (an in-repo package). `go2_sim` starts Gazebo Fortress, spawns the robot via `go2_description` xacro, runs the gait controller and odometry node, and publishes all topics at SDK root-level names — no namespace bridging needed. `simulation.launch.py` then starts the same Nav2/SLAM/RViz/joystick stack as the hardware launch. Nav2 uses `config/nav2_params_sim.yaml` (`use_sim_time: True` throughout).

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
| `/camera/image_raw` | `sensor_msgs/Image` | published by robot driver (hardware WebRTC, or CycloneDDS + `ENABLE_WEBRTC_CAMERA=true` hybrid mode); by `cam_bridge_node` (browser webcam, `CAM_BRIDGE=true`); sim uses `/go2_camera/color/image` |
| `/camera/camera_info` | `sensor_msgs/CameraInfo` | published (by driver, or by cam_bridge_node with identity calibration) |
| `/point_cloud2` | `sensor_msgs/PointCloud2` | published (~7 Hz) |
| `/scan` | `sensor_msgs/LaserScan` | published (from pointcloud_to_laserscan) |
| `/cmd_vel_out` | `geometry_msgs/Twist` | consumed by driver (twist_mux output) |
| `/cmd_vel_follow` | `geometry_msgs/Twist` | published by follow_me_node and approach_object_node (twist_mux priority 6; mutual exclusion enforced in CommandDispatcher) |
| `/follow_enable` | `std_msgs/Bool` | consumed by follow_me_node — enable/disable follow mode at runtime |
| `/approach_target` | `std_msgs/String` | consumed by approach_object_node (`ENABLE_APPROACH_OBJECT=true`) — YOLO class name to approach; empty string cancels |
| `/approach_status` | `std_msgs/String` | published by approach_object_node — `"approaching:<class>"`, `"reached:<class>"`, `"lost:<class>"`, `"cancelled"` |
| `/patrol_enable` | `std_msgs/Bool` | consumed by patrol_node (`ENABLE_PATROL=true`) — True=start cycling waypoints, False=stop |
| `/patrol_status` | `std_msgs/String` | published by patrol_node — `"patrolling:<key>/<idx>/<total>"`, `"patrol_done"`, `"patrol_cancelled"`, `"patrol_failed:<key>"` |
| `/reload_custom_commands` | `std_msgs/Empty` | consumed by voice_cmd_node — reload `custom_commands.yaml` from disk without restarting |
| `/behavior_mode` | `std_msgs/String` | published by behavior_coordinator_node (`ENABLE_BEHAVIOR_COORDINATOR=true`, TRANSIENT_LOCAL) — `IDLE`, `VOICE_MOVE`, `FOLLOWING`, `NAVIGATING`, `APPROACHING`, `PATROL` |
| `/navigate_to_room` | `std_msgs/String` | consumed by nav_waypoint_node (`ENABLE_NAV_WAYPOINT=true`) — room name to navigate to; empty string cancels current goal |
| `/navigation_status` | `std_msgs/String` | published by nav_waypoint_node — `"navigating:<room>"`, `"arrived:<room>"`, `"failed:<room>"`, `"cancelled"`, `"unknown:<room>"` |
| `/reload_waypoints` | `std_msgs/Empty` | consumed by nav_waypoint_node — re-read `waypoints.yaml` from disk without restarting |
| `/webrtc_req` | `go2_interfaces/WebRtcReq` | consumed (send robot API commands) |
| `/detected_objects` | `vision_msgs/Detection2DArray` | published by yolo_detector |
| `/scene_description` | `std_msgs/String` | published by gemma_vision_node (Windows GPU profile, `ENABLE_GEMMA_VISION=true`) |
| `/recognized_faces` | `vision_msgs/Detection2DArray` | published by face_recognition_node (`ENABLE_FACE=true`); `class_id`=name, `score`=similarity |
| `/recognized_face_names` | `std_msgs/String` | published by face_recognition_node (comma-joined known names); consumed by voice_cmd_node for greetings (4.4) |
| `/face_annotated_image` | `sensor_msgs/Image` | published by face_recognition_node (camera frame with name labels) |
| `/reload_faces` | `std_msgs/Empty` | consumed by face_recognition_node — re-scan `face_db/` and re-embed all photos (after web enrollment) |
| `/face_threshold` | `std_msgs/Float32` | published by face_enrollment_node (threshold slider) → consumed by face_recognition_node to tune match floor live |
| `/gemma_annotated_image` | `sensor_msgs/Image` | published by gemma_vision_node (camera frame with description overlay) |
| `/speech_text` | `std_msgs/String` | published by stt_node or mic_bridge_node (enable with `ENABLE_STT=true`) |
| `/robot_audio` | `std_msgs/UInt8MultiArray` | published by driver (GO2 onboard mic — WebRTC audio track or CycloneDDS `/audiosender`, depending on `CONN_TYPE`), consumed by stt_node — only when `STT_SOURCE=robot` |
| `/audiohub_player_state` | `std_msgs/String` | published by driver (passthrough of the robot's `/audiohub/player/state`; WebRTC mode only today — CycloneDDS pending hardware verification of the DDS message type), consumed by tts_node for an early TTS-completion signal |
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
| `speech_processor` | `ament_python` | TTS (`supertonic`/`openai`/`elevenlabs`/`gemini`), STT (`openai`/`faster_whisper`/`gemini`/`gemma_local`), unified live speech-to-speech via `mic_bridge_node` only (`openai_realtime` — gpt-realtime-2.1, GA Realtime API; `gemini_live` — gemini-3.1-flash-live-preview; both bypass `voice_cmd_node`/`tts_node` and dispatch commands + speak replies directly from the persistent WebSocket session), browser mic bridge (`mic_bridge_node`, port 8888/8889), voice commands (`keyword`/`openai`/`gemini`/`gemma_local` NLU), Gemma vision (`gemma_vision_node`), face recognition (`face_recognition_node` — InsightFace SCRFD+ArcFace + `face_db`), face enrollment UI (`face_enrollment_node`, port 8890), **camera bridge** (`cam_bridge_node`, port 8891/8892 — browser webcam → `/camera/image_raw`, Windows default, `CAM_BRIDGE=true`), **mic diagnostic** (`mic_diagnostic_node`, port 8893/8894 — Record/Stop web UI to capture `/robot_audio` and play it back in-browser, no SSH needed, `ENABLE_MIC_DIAGNOSTIC=true`), **follow-me** (`follow_me_node` — person tracking via YOLO `/detected_objects` → `/cmd_vel_follow`, `ENABLE_FOLLOW=true`), **nav waypoint** (`nav_waypoint_node` — `/navigate_to_room` → Nav2 `NavigateToPose` goal, `ENABLE_NAV_WAYPOINT=true`), **behavior coordinator** (`behavior_coordinator_node` — observational state machine; publishes `/behavior_mode`, `ENABLE_BEHAVIOR_COORDINATOR=true`), **patrol** (`patrol_node` — loops through YAML waypoints via Nav2, voice "patroli", `ENABLE_PATROL=true`), **object approach** (`approach_object_node` — one-shot visual servo to YOLO class, voice "dekati <obj>", `ENABLE_APPROACH_OBJECT=true`), **custom commands** (`config/custom_commands.yaml` — operator-editable YAML voice triggers, hot-reloaded via `/reload_custom_commands`) |

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

GitHub Actions (`.github/workflows/ros_build.yaml`) runs `colcon build` (tests skipped) against ROS2 Humble on every push/PR to `master`. No lint step is configured.

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
