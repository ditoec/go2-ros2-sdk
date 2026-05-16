# Packages

## go2_robot_sdk (`ament_python`)

Main driver package. Source lives in `go2_robot_sdk/go2_robot_sdk/`.

| Sub-path | Contents |
|---|---|
| `domain/constants/` | `RTC_TOPIC` dict (all WebRTC topic strings), `ROBOT_CMD` dict (command IDs 1001–1305), `DATA_CHANNEL_TYPE`, `AUDIO_HUB_COMMANDS` |
| `domain/entities/` | `RobotConfig`, `RobotData`, `RobotState`, `IMUData`, `OdometryData`, `JointData`, `LidarData`, `CameraData` — pure Python dataclasses |
| `domain/interfaces/` | `IRobotDataPublisher`, `IRobotDataReceiver`, `IRobotController` — ABCs with no ROS2 dependency |
| `domain/math/` | `geometry.py`, `kinematics.py` — pure math helpers |
| `application/services/` | `RobotDataService` — routes WebRTC messages to publisher; `RobotControlService` — translates cmd_vel / joy / webrtc_req to robot commands |
| `application/utils/` | `command_generator.py` — `gen_command()`, `gen_mov_command()` JSON payload builders |
| `infrastructure/webrtc/` | `Go2Connection` (WebRTC peer + HTTP signaling), `WebRTCAdapter` (implements interfaces), `WebRTCDataDecoder`, `crypto/` (AES-GCM validation) |
| `infrastructure/ros2/` | `ROS2Publisher` — implements `IRobotDataPublisher`, owns all `sensor_msgs`/`nav_msgs` construction |
| `infrastructure/sensors/` | `LidarDecoder` (voxel decompression), `camera_config.py` (loads `CameraInfo`) |
| `presentation/` | `Go2DriverNode` — the ROS2 node; wires all layers; declares parameters; creates publishers/subscribers |

**Launch files** (`go2_robot_sdk/launch/`):

| File | Purpose |
|---|---|
| `robot.launch.py` | Full hardware stack (driver + LiDAR + Nav2 + SLAM + joystick + RViz + Foxglove) |
| `simulation.launch.py` | Gazebo stack — replaces driver with `go2_ros2_sim_py`, adds topic bridges |
| `mapping.launch.py` | SLAM-only launch |
| `navigation.launch.py` | Nav2-only launch (load a pre-built map) |
| `robot_cpp.launch.py` | Hardware stack with C++ LiDAR nodes instead of Python |
| `webrtc_web.launch.py` | WebRTC web interface |

`robot.launch.py` uses `Go2LaunchConfig` (config factory) and `Go2NodeFactory` (node factory) to select URDF, RViz config, and topic names based on `ROBOT_IP` / `CONN_TYPE`.

**Config files** (`go2_robot_sdk/config/`):

| File | Used by |
|---|---|
| `joystick.yaml` | `joy_node` — device_id, deadzone |
| `twist_mux.yaml` | `twist_mux` — joy priority 10, nav priority 5 |
| `mapper_params_online_async.yaml` | `slam_toolbox` online async mapper |
| `nav2_params.yaml` | Nav2 hardware mode (`use_sim_time: false`) |
| `nav2_params_sim.yaml` | Nav2 simulation mode (`use_sim_time: true` throughout) |
| `*.rviz` | RViz2 layouts (single, multi, cyclonedds variants) |

## go2_interfaces (`ament_cmake`)

32 custom message definitions. Key types:

| Message | Purpose |
|---|---|
| `Go2State.msg` | Robot state (mode, gait, velocity, foot forces) |
| `IMU.msg` | Quaternion, accelerometer, gyroscope, RPY |
| `LowState.msg` / `LowCmd.msg` | Low-level motor states and commands |
| `SportModeState.msg` | High-level motion mode state |
| `BmsState.msg` | Battery management system |
| `WebRtcReq.msg` | Fields: `api_id`, `parameter`, `topic`, `priority` — used to send arbitrary robot commands |
| `VoxelMapCompressed.msg` | Raw voxel data passthrough |

## go2_sim (`ament_python`)

Self-contained Gazebo Harmonic simulation — replaces the former external `go2_ros2_sim_py` dependency. All files live in this repo; `colcon build` is sufficient, no `git clone` required.

Scripts in `go2_sim/scripts/`:

| Script | Role |
|---|---|
| `robot_controller_gazebo.py` | 60 Hz gait controller (trot, crawl, stand, rest modes). Subscribes to `/go2/robot_velocity` (`RobotVelocity`), publishes joint position commands to `ros2_control`. |
| `cmd_vel_pub.py` | Converts `/go2/cmd_vel` (Twist) → `/go2/robot_velocity` (RobotVelocity) for the gait controller. |
| `QuadrupedOdometryNode.py` | Computes `/odom` + `odom→base_link` TF at 50 Hz using IMU and forward kinematics. |
| `sim_cmd_node.py` | Root-level command interface — subscribes to `/sim_cmd` (`go2_interfaces/msg/WebRtcReq`) and routes `api_id` values to the gait controller. Same message type as `/webrtc_req` on hardware. |
| `RobotController/` | Trot, crawl, stand, rest gait state machines + PID controller. |
| `InverseKinematics/robot_IK.py` | Leg IK used by gait controllers. |
| `ForwardKinematics/robot_FK.py` | Leg FK used by odometry node. |

**`sim_cmd_node` — selected api_ids:**

| api_id | Effect |
|---|---|
| 1001/1003/1004 | REST / stop |
| 1002 | BalanceStand (STAND controller) |
| 1005/1009 | Sit (body lowered) |
| 1006 | RecoveryStand → TROT |
| 1007 | Euler body orientation (`parameter: "r,p,y"` rad) |
| 1011 | SwitchGait (`parameter: "0"`=REST `"1"`=TROT `"2"`=CRAWL `"3"`=STAND) |
| 1013 | BodyHeight offset in metres (`parameter: float`) |
| 1015 | SpeedLevel (`parameter: "0"` slow / `"1"` normal / `"2"` fast) |
| 1017 | Stretch pose |
| 1019 | ContinuousGait toggle (`parameter: "0"` always trot) |

```bash
ros2 topic pub /sim_cmd go2_interfaces/msg/WebRtcReq "{api_id: 1009}" --once  # Sit
ros2 topic pub /sim_cmd go2_interfaces/msg/WebRtcReq "{api_id: 1011, parameter: '1'}" --once  # TROT
```

The launch file `go2_sim/launch/go2_sim.launch.py` wires all of these together with Gazebo, `robot_state_publisher`, `ros_gz_bridge`, and two relay nodes. See [simulation.md](simulation.md) for the full startup sequence.

## go2_description (`ament_cmake`)

Robot URDF/xacro description package. Contains:
- `xacro/robot.xacro` — main robot description (parameterised by `robot_name`)
- `xacro/leg.xacro`, `gazebo.xacro`, `laser.xacro`, etc. — sensor and joint definitions
- `meshes/` + `dae/` — visual and collision geometry
- `config/ros_control.yaml` — `ros2_control` hardware interface config used by `go2_sim`

Used by `go2_sim` at build time via `xacro.process_file()` — not referenced by the hardware driver, which uses the pre-built `go2_robot_sdk/urdf/go2.urdf`.

## quadropted_msgs (`ament_cmake`)

Custom message/service definitions used internally by `go2_sim`:

| Type | Name | Fields |
|---|---|---|
| msg | `RobotVelocity` | Linear/angular velocity commands for gait controller |
| msg | `RobotModeCommand` | Mode switching (stand, trot, crawl, rest) |
| msg | `RobotGaitCommand` | Gait parameters |
| msg | `RobotFootContact` | Foot contact state (used by odometry) |
| srv | `RobotBehaviorCommand` | Request/response for behavior switching |

These types are **not published on any SDK root topic** — they are internal to the `go2_sim` pipeline and should not be referenced outside that package.

## lidar_processor (`ament_python`)

Python LiDAR processing. Two nodes:

- `lidar_to_pointcloud_node` — subscribes to `/point_cloud2`, applies voxel downsampling (0.01 m grid), optionally saves `.ply` snapshots every 10 s.
- `pointcloud_aggregator_node` — accumulates and publishes aggregated cloud.

`LidarConfig` dataclass controls `max_points` (1,000,000), `voxel_size` (0.01 m), `save_interval` (10 s).

## lidar_processor_cpp (`ament_cmake`)

Drop-in C++ / PCL replacement for the Python LiDAR nodes. Faster for high-density clouds. Use `robot_cpp.launch.py` to select it.

## yolo_detector (`ament_python`)

Object detection node — `YoloDetectorNode` — using [Ultralytics](https://github.com/ultralytics/ultralytics). This is the current default detector.

- Subscribes: `/camera/image_raw` (`sensor_msgs/Image`)
- Publishes: `/detected_objects` (`vision_msgs/Detection2DArray`), `/annotated_image` (`sensor_msgs/Image`)
- Model: configurable via `model` parameter; weights are downloaded to `~/.cache/ultralytics/` on first run

| Parameter | Default | Notes |
|---|---|---|
| `model` | `yolo11n.pt` | Any Ultralytics model: `yolo11n/s/m/l/x.pt`, `yolov8n.pt`, etc. |
| `device` | `cpu` | `cpu` or `cuda` |
| `detection_threshold` | `0.5` | Confidence threshold 0–1. Use 0.7+ for stricter filtering. |
| `publish_annotated_image` | `true` | Disable to save bandwidth |

**Topic remap required for simulation** (driver publishes on `/go2_camera/color/image`):
```bash
ros2 run yolo_detector yolo_detector_node \
    --ros-args -r /camera/image_raw:=/go2_camera/color/image
```

## coco_detector (`ament_python`)

Legacy object detection node — `CocoDetectorNode` — using FasterRCNN via TorchVision. Superseded by `yolo_detector` but still functional.

- Parameters: `device` (default `cpu`), `detection_threshold` (default `0.9`), `publish_annotated_image` (default `true`)
- Same topic remap caveat as `yolo_detector`.

## speech_processor (`ament_python`)

Voice I/O package — TTS (text → speech) and STT (speech → text).

### tts_node

Subscribes to `/tts` (`std_msgs/String`), synthesises speech, sends to the robot speaker via `WebRtcReq` (api_ids 4001–4003) or plays locally via `pydub`. MP3 results are cached in `tts_cache/` to avoid repeated API calls.

| Parameter | Default | Description |
|---|---|---|
| `provider` | `openai` | `openai` \| `elevenlabs` \| `gemini` |
| `api_key` | `""` | `OPENAI_API_KEY` (openai), `ELEVENLABS_API_KEY` (elevenlabs), or `GEMINI_API_KEY` (gemini) |
| `voice_name` | `nova` | OpenAI: `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`; ElevenLabs: voice ID; Gemini: `Kore`, `Zephyr`, `Puck`, `Charon`, `Fenrir`, `Leda`, `Orus`, `Aoede`, `Callirrhoe` |
| `local_playback` | `false` | `true` → play on the host PC speaker instead of robot |
| `audio_quality` | `standard` | `high` → uses `tts-1-hd` model (OpenAI only) |

Provider notes:
- `openai` (default) — `tts-1-hd`, same `OPENAI_API_KEY` as the STT and voice NLU nodes
- `elevenlabs` — more expressive voice, requires `ELEVENLABS_API_KEY`
- `gemini` — `gemini-2.5-flash-tts-preview`, requires `GEMINI_API_KEY`; returns PCM converted to MP3 internally
- `amazon` — declared in code, not yet implemented

### stt_node

Captures microphone audio via `sounddevice`, applies energy-threshold VAD, then transcribes utterances. Publishes to `/speech_text` (`std_msgs/String`).

| Parameter | Default | Description |
|---|---|---|
| `stt_provider` | `openai` | `openai` \| `faster_whisper` \| `vosk` |
| `whisper_model` | `base` | `tiny` / `base` / `small` / `medium` — ignored for `openai` and `vosk` |
| `device` | `cuda` | `cuda` (Jetson NX GPU) or `cpu` |
| `compute_type` | `float16` | `float16` (GPU) or `int8` (CPU) |
| `language` | `en` | Whisper language code |
| `api_key` | `""` | OpenAI key — same as TTS `api_key` when using Tier 1 |
| `vad_threshold` | `0.02` | RMS energy level to detect voice onset |
| `silence_duration` | `0.8` | Seconds of silence that close an utterance |

Provider tiers:

| Provider | Tier | Backend | Latency | Offline |
|---|---|---|---|---|
| `openai` | 1 (internet) | OpenAI Whisper API | 500 ms – 2 s | ✗ |
| `gemini` | 1 (internet) | Gemini 2.5 Flash | ~1–2 s | ✗ |
| `faster_whisper` | 2 (local) | CTranslate2 + CUDA | ~30–60 ms (Jetson GPU) | ✓ |
| `vosk` | 2 (local) | Kaldi/LSTM streaming | ~50 ms | ✓ |

Environment variables consumed by `robot.launch.py`:

| Variable | Default | Effect |
|---|---|---|
| `ENABLE_STT` | `false` | Set `true` to start `stt_node` |
| `STT_PROVIDER` | `openai` | `openai` \| `gemini` \| `faster_whisper` \| `vosk` |
| `STT_DEVICE` | `cpu` | `cuda` for Jetson NX (faster_whisper only) |
| `WHISPER_MODEL` | `base` | Model size (faster-whisper only) |
| `TTS_PROVIDER` | `openai` | `openai` \| `elevenlabs` \| `gemini` |
| `TTS_VOICE` | `nova` | OpenAI: `nova`, `alloy`, …; ElevenLabs: voice ID; Gemini: `Kore`, `Zephyr`, … |
| `OPENAI_API_KEY` | `""` | Shared by TTS/STT/NLU when using OpenAI |
| `ELEVENLABS_API_KEY` | `""` | Required when `TTS_PROVIDER=elevenlabs` |
| `GEMINI_API_KEY` | `""` | Required when using any `gemini` provider |
| `ANTHROPIC_API_KEY` | `""` | Required when `NLU_PROVIDER=claude` |
| `ENABLE_VOICE_CMD` | `false` | Set `true` to start `voice_cmd_node` |
| `NLU_PROVIDER` | `keyword` | `keyword` (offline) \| `openai` \| `gemini` \| `claude` |
| `VOICE_MOVE_DURATION` | `2.0` | Seconds to drive for a movement command |
| `VOICE_LINEAR_SPEED` | `0.3` | m/s for forward/backward voice commands |
| `VOICE_ANGULAR_SPEED` | `0.5` | rad/s for turn left/right voice commands |

### voice_cmd_node

Subscribes to `/speech_text` (`std_msgs/String`), parses the text, and dispatches robot commands.

| Output | Topic | Condition |
|---|---|---|
| Robot state/gait/posture | `/webrtc_req` (hardware) or `/sim_cmd` (simulation) | `WebRtcReq` |
| Movement | `/cmd_vel_voice` (`geometry_msgs/Twist`) | via twist_mux at priority 7 |

Hardware-only gestures (Hello, Dance, FrontFlip, Handstand, MoonWalk, WiggleHips, FingerHeart) are silently skipped when `cmd_topic=/sim_cmd`.

| Parameter | Default | Description |
|---|---|---|
| `cmd_topic` | `/webrtc_req` | `/sim_cmd` for simulation |
| `nlu_provider` | `keyword` | `keyword` \| `openai` |
| `api_key` | `""` | OpenAI key (for `openai` NLU only) |
| `move_duration` | `2.0` | Seconds to drive before auto-stopping |
| `linear_speed` | `0.3` | m/s scale for forward/backward |
| `angular_speed` | `0.5` | rad/s scale for turns |

**NLU providers:**
- `keyword` (default) — regex pattern matching; instant, fully offline; ~30 command phrases
- `openai` — GPT-4o-mini structured output; handles free-form phrasing; requires `OPENAI_API_KEY`
- `gemini` — gemini-2.5-flash JSON output; handles free-form phrasing; requires `GEMINI_API_KEY`
- `claude` — claude-haiku-4-5 JSON output; handles free-form phrasing; requires `ANTHROPIC_API_KEY`
