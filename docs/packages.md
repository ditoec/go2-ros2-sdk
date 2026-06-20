# Packages

## go2_robot_sdk (`ament_python`)

Main driver package. Source lives in `go2_robot_sdk/go2_robot_sdk/`.

| Sub-path | Contents |
|---|---|
| `domain/constants/` | `RTC_TOPIC` dict (all WebRTC topic strings), `ROBOT_CMD` dict (command IDs 1001–1305), `DATA_CHANNEL_TYPE`, `AUDIO_HUB_COMMANDS` |
| `domain/entities/` | `RobotConfig`, `RobotData`, `RobotState`, `IMUData`, `OdometryData`, `JointData`, `LidarData`, `CameraData`, `AudioData` — pure Python dataclasses |
| `domain/interfaces/` | `IRobotDataPublisher`, `IRobotDataReceiver`, `IRobotController` — ABCs with no ROS2 dependency |
| `domain/math/` | `geometry.py`, `kinematics.py` — pure math helpers |
| `application/services/` | `RobotDataService` — routes WebRTC messages to publisher; `RobotControlService` — translates cmd_vel / joy / webrtc_req to robot commands |
| `application/utils/` | `command_generator.py` — `gen_command()`, `gen_mov_command()` JSON payload builders |
| `infrastructure/webrtc/` | `Go2Connection` (WebRTC peer + HTTP signaling), `WebRTCAdapter` (implements interfaces), `WebRTCDataDecoder`, `crypto/` (AES-GCM validation) |
| `infrastructure/cyclonedds/` | `CycloneDDSAdapter` — implements `IRobotController`; routes commands to the sport-mode API (`/api/sport/request`) over native DDS when `CONN_TYPE=cyclonedds` |
| `infrastructure/ros2/` | `ROS2Publisher` — implements `IRobotDataPublisher`, owns all `sensor_msgs`/`nav_msgs` construction |
| `infrastructure/sensors/` | `LidarDecoder` (voxel decompression), `camera_config.py` (loads `CameraInfo`) |
| `presentation/` | `Go2DriverNode` — the ROS2 node; wires all layers; declares parameters; creates publishers/subscribers |

**Launch files** (`go2_robot_sdk/launch/`):

| File | Purpose |
|---|---|
| `robot.launch.py` | Full hardware stack (driver + LiDAR + Nav2 + SLAM + joystick + RViz + Foxglove) + optional rosbag session recording (`ENABLE_BAG`/`bag_record:=true` → `./bags`) |
| `simulation.launch.py` | Gazebo stack — delegates the Gazebo layer to the in-repo `go2_sim` package, then runs the same Nav2/SLAM/RViz/joystick/voice stack as hardware |
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

Full voice stack: STT (speech → text), NLU (text → command), TTS (text → speech),
plus a browser microphone bridge and an optional Gemma vision node. Nodes are
opt-in (`ENABLE_STT`, `ENABLE_VOICE_CMD`, `ENABLE_GEMMA_VISION`). Three pipeline
shapes exist depending on `STT_PROVIDER` — see [architecture.md](architecture.md)
for the Path A/B/C diagrams.

Executables (`speech_processor/`):

| Module | Role |
|---|---|
| `stt_node.py` | STT from a local mic (`sounddevice`, Jetson / bare-metal) **or** the GO2's onboard mic via `/robot_audio` (`audio_source:=topic`, set by `STT_SOURCE=robot`). Pure-STT providers publish `/speech_text`; unified `gemma_local` dispatches commands + `/tts` directly. |
| `mic_bridge_node.py` | Browser-mic bridge (HTTP UI on `:8888`, PCM WebSocket on `:8889`) for Windows/Docker where `/dev/snd` is unavailable. Same backends as `stt_node` plus the persistent-WebSocket providers (`openai_realtime`, `gemini_live`). Relays TTS audio back to the browser over `/tts_audio`. |
| `voice_cmd_node.py` | Keyword/cloud NLU for Path A: `/speech_text` → `/webrtc_req`\|`/sim_cmd` + `/cmd_vel_voice`. Not started for unified providers. |
| `tts_node.py` | `/tts` → synthesized speech → `/tts_audio` (browser) and/or robot speaker. |
| `gemma_vision_node.py` | Optional scene description via the Gemma sidecar (Windows GPU profile). |
| `command_dispatcher.py` | **Shared, no node** — see below. |

### command_dispatcher.py (shared module)

Single source of truth for the command vocabulary and dispatch, imported by
`voice_cmd_node`, `mic_bridge_node`, and `stt_node` so all providers behave
identically:

- `CMD_MAP` — 30+ command keys → action (api_id/parameter, or a movement tuple).
- `FEEDBACK_MAP` / `feedback_for_action()` — canned spoken-feedback strings.
- `COMMAND_GLOSSARY` — Indonesian→English command phrases (for `VOICE_LANG=id`).
- `CommandDispatcher` — stateful executor: routes to `/webrtc_req`\|`/sim_cmd` or
  `/cmd_vel_voice`, runs the 10 Hz velocity sustain + timed-stop timer, skips
  hardware-only gestures in simulation.
- `command_for_text()` — deterministic transcript→command matcher (Indonesian
  glossary + question guard). Used both as the `id`-scoped safety net when an LLM
  under-fires **and** as the offline Indonesian path for the `keyword` NLU provider.
- `system_prompt()` / `build_unified_tools()` / `command_enum_description()` —
  the (English) Gemma system prompt and two-tool schema shared by both unified
  backends.

### Language (`VOICE_LANG`)

`VOICE_LANG` (`en`* | `id`) is the master language knob: it sets the STT language,
the NLU framing, and the TTS synthesis language in one place. **Robot command
output always stays English** (the `CMD_MAP` keys / robot API). For `id`, command
mapping is delivered deterministically by `command_for_text()` (the LLM often
under-fires on Indonesian). `SUPERTONIC_LANG` can override the TTS language only
(defaults to `VOICE_LANG`).

### tts_node

Subscribes to `/tts` (`std_msgs/String`), synthesises speech, publishes MP3 bytes
to `/tts_audio` (`UInt8MultiArray`, relayed to the browser by `mic_bridge_node`)
and/or sends it to the robot speaker via `WebRtcReq` (api_ids 4001–4003). MP3
results are cached in `tts_cache/`.

| Parameter | Default | Description |
|---|---|---|
| `provider` | `supertonic` | `supertonic` \| `openai` \| `elevenlabs` \| `gemini` |
| `api_key` | `""` | `ELEVENLABS_API_KEY` / `GEMINI_API_KEY` / `OPENAI_API_KEY` per provider (none for supertonic) |
| `voice_name` | `F1` | supertonic: `M1`–`M5`, `F1`–`F5`; openai: `alloy`/`echo`/`fable`/`onyx`/`nova`/`shimmer`; elevenlabs: voice ID; gemini: `Kore`/`Zephyr`/… |
| `language` | follows `VOICE_LANG` | supertonic synthesis language (ISO code; `na` = auto-detect) |
| `supertonic_steps` | `8` | Flow-matching quality steps, 5 (fast) → 12 (best) |
| `local_playback` | `false` | `true` → play on the host PC speaker |
| `use_cache` | `true` | Cache MP3 output in `tts_cache/` |
| `audio_quality` | `standard` | `high` → `tts-1-hd` (OpenAI only) |

Provider notes:
- `supertonic` (default) — offline neural TTS (flow-matching, 31 languages), no API key; model pre-baked in the Docker image
- `openai` — `tts-1` / `tts-1-hd`, requires `OPENAI_API_KEY`
- `elevenlabs` — requires `ELEVENLABS_API_KEY`
- `gemini` — `gemini-2.5-flash-tts-preview`, requires `GEMINI_API_KEY`; PCM converted to MP3 internally

### stt_node / mic_bridge_node

Capture audio (physical mic via `sounddevice`, or browser mic via the WebSocket
bridge), apply energy-threshold VAD, then transcribe. Pure-STT providers publish
`/speech_text`; unified providers transcribe **and** dispatch the command +
`/tts` in one step.

| Parameter | Default | Description |
|---|---|---|
| `stt_provider` | `faster_whisper` | see table below |
| `whisper_model` | `base` | `tiny` / `base` / `small` / `medium` — faster_whisper only |
| `device` | `cpu` | `cuda` (Jetson NX GPU) or `cpu` |
| `compute_type` | `int8` | `float16` (GPU) or `int8` (CPU) |
| `language` | follows `VOICE_LANG` | transcription language |
| `wake_word` | `elliot` | utterances without it are discarded (echoed `[ignored]`) |
| `silence_duration` | `0.4` | seconds of silence that close an utterance |
| `audio_source` | `mic` | `mic` (local `sounddevice`) or `topic` (robot mic via `/robot_audio`) |
| `audio_topic` | `/robot_audio` | PCM topic read when `audio_source:=topic` |
| `llama_cpp_host` | `http://llama_cpp:8080` | Gemma sidecar (unified providers) |
| `gemma_model` | `gemma` | model label sent to the sidecar |
| `api_key` | `""` | `GEMINI_API_KEY` (gemini) else `OPENAI_API_KEY` |

| Provider | Mode | Backend | Offline | Nodes |
|---|---|---|---|---|
| `faster_whisper`* | STT only → `voice_cmd_node` | CTranslate2 | ✓ | both |
| `gemma_local` | unified (STT+NLU+TTS, 1 REST call) | Gemma 4 via llama.cpp (`GEMMA_SIZE`) | ✓ | both |
| `openai_realtime` | unified (audio in/out, persistent WS) | OpenAI gpt-realtime-2 | ✗ | mic_bridge only |
| `gemini_live` | unified (audio in/out, persistent WS) | Gemini 2.5 Flash Live | ✗ | mic_bridge only |
| `openai` | STT only (legacy) | OpenAI Whisper API | ✗ | both |
| `gemini` | STT only (legacy) | Gemini 2.5 Flash REST | ✗ | both |

Environment variables (consumed by the launch files):

| Variable | Default | Effect |
|---|---|---|
| `VOICE_LANG` | `en` | Master language for STT+NLU+TTS (`en` \| `id`) |
| `ENABLE_STT` | `false`† | Start `mic_bridge_node` (or `stt_node` if `MIC_BRIDGE=false`) |
| `MIC_BRIDGE` | `true`† | `true` → browser bridge; `false` → physical-mic `stt_node` |
| `STT_SOURCE` | `mic` | `mic` (local) \| `robot` (GO2 onboard mic via WebRTC → `/robot_audio`; needs `CONN_TYPE=webrtc` + `MIC_BRIDGE=false`) |
| `STT_PROVIDER` | `faster_whisper`† | see provider table |
| `STT_DEVICE` | `cpu`† | `cuda` for Jetson NX (faster_whisper only) |
| `WHISPER_MODEL` | `base` | Model size (faster_whisper only) |
| `WAKE_WORD` | `elliot` | STT wake word |
| `VAD_SILENCE_DURATION` | `0.4` | Silence (s) before an utterance is sent |
| `ENABLE_VOICE_CMD` | auto | Auto-disabled for unified `STT_PROVIDER`s |
| `NLU_PROVIDER` | `keyword`† | `keyword` \| `openai` \| `gemini` \| `gemma_local` |
| `ENABLE_WEB_SEARCH` | `true` | DuckDuckGo search for non-command speech (cloud/local LLM NLU) |
| `TTS_PROVIDER` | `supertonic` | `supertonic` \| `openai` \| `elevenlabs` \| `gemini` |
| `TTS_VOICE` | `F1` | Voice id (meaning depends on provider) |
| `SUPERTONIC_LANG` | follows `VOICE_LANG` | TTS-only language override (31 langs; `na` = auto) |
| `SUPERTONIC_STEPS` | `8` | TTS quality steps 5–12 |
| `LLAMA_CPP_HOST` | `http://llama_cpp:8080` | Gemma sidecar endpoint |
| `GEMMA_MODEL` | `gemma` | Model label for the sidecar |
| `ENABLE_GEMMA_VISION` | `false` | Start `gemma_vision_node` |
| `GEMMA_VISION_RATE` | `0.5` | Vision inference Hz |
| `OPENAI_API_KEY` / `ELEVENLABS_API_KEY` / `GEMINI_API_KEY` | `""` | Provider keys |
| `VOICE_MOVE_DURATION` / `VOICE_LINEAR_SPEED` / `VOICE_ANGULAR_SPEED` | `2.0` / `0.3` / `0.5` | Movement command scale |

† docker-compose defaults; bare-metal launch defaults `ENABLE_STT`/`MIC_BRIDGE` to their `os.getenv` fallbacks. The `windows-gpu` profile overrides `STT_PROVIDER`/`NLU_PROVIDER` to `gemma_local`; the `jetson` profile sets `MIC_BRIDGE=false` and `STT_DEVICE=cuda`.

### voice_cmd_node

Path A only (pure-STT providers). Subscribes to `/speech_text`, parses the text,
and dispatches via the shared `CommandDispatcher`.

| Output | Topic | Type |
|---|---|---|
| Robot state/gait/posture/gesture | `/webrtc_req` (hardware) or `/sim_cmd` (simulation) | `WebRtcReq` |
| Movement | `/cmd_vel_voice` | `geometry_msgs/Twist` (twist_mux priority 7) |

Hardware-only gestures (Hello, Dance, FrontFlip, Handstand, MoonWalk, WiggleHips,
FingerHeart) are silently skipped when `cmd_topic=/sim_cmd`.

| Parameter | Default | Description |
|---|---|---|
| `cmd_topic` | `/webrtc_req` | `/sim_cmd` for simulation |
| `nlu_provider` | `keyword` | `keyword` \| `openai` \| `gemini` \| `gemma_local` |
| `language` | follows `VOICE_LANG` | prepended to the cloud-NLU prompt |
| `api_key` | `""` | provider key (for LLM NLU) |
| `move_duration` / `linear_speed` / `angular_speed` | `2.0` / `0.3` / `0.5` | movement scale |

**NLU providers:**
- `keyword` (default) — instant, offline. English uses the regex table; for `id` it uses the shared glossary matcher (`command_for_text`), so the basic Indonesian commands resolve offline too (looser phrasing still needs an LLM provider)
- `openai` — GPT-4o-mini structured output; requires `OPENAI_API_KEY`
- `gemini` — gemini-2.5-flash JSON; requires `GEMINI_API_KEY`
- `gemma_local` — Gemma 4 via llama.cpp sidecar; offline

### gemma_vision_node

Optional scene-description node (Windows GPU profile, `ENABLE_GEMMA_VISION=true`).
Rate-limited camera frames → Gemma 4 (vision) via the llama.cpp sidecar.

- Subscribes: `camera_topic` (default `/camera/image_raw`)
- Publishes: `/scene_description` (`std_msgs/String`), `/gemma_annotated_image` (`sensor_msgs/Image`)
- Parameters: `llama_cpp_host`, `model` (`GEMMA_MODEL`), `inference_rate` (`GEMMA_VISION_RATE`, default 0.5 Hz)
