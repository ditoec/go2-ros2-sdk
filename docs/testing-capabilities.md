# Testing SDK Capabilities

This guide covers how to verify each SDK feature works after launching, in both hardware and simulation modes. Run these commands in a second terminal after the main launch.

## Quick Health Check — Topics After Launch

After either launch, the following topics should be active within ~10 s (hardware) or ~30 s (simulation — Gazebo sensor topics are lazy and appear only when the first message arrives):

```bash
# List all active topics
ros2 topic list

# Topics common to both modes
ros2 topic hz /imu           # hardware ~50 Hz  |  sim ~100 Hz
ros2 topic hz /odom          # expect ~10–50 Hz
ros2 topic hz /scan          # hardware ~7 Hz   |  sim ~10 Hz
ros2 topic hz /joint_states  # hardware ~1 Hz (firmware limit)  |  sim ~50 Hz
```

**Hardware-only topics:**
```bash
ros2 topic hz /point_cloud2        # expect ~7 Hz  (not published in sim)
ros2 topic hz /camera/image_raw    # expect ~30 Hz
```

**Simulation-only topics:**
```bash
ros2 topic hz /go2_camera/color/image_raw   # expect ~10 Hz
ros2 topic hz /clock                        # Gazebo sim clock
```

---

## 1. IMU

**Hardware** (`go2_interfaces/IMU`):
```bash
ros2 topic echo /imu --once
```
Expected fields: `quaternion`, `accelerometer`, `gyroscope`, `rpy`. `temperature` should read ~30–60 °C.

**Simulation** (`sensor_msgs/msg/Imu`):
```bash
# The topic appears only after Gazebo loads the robot (~15–30 s after launch).
# Verify it exists first:
ros2 topic list | grep imu

ros2 topic echo /imu --once
```
Expected fields: `orientation` (quaternion x/y/z/w), `angular_velocity`, `linear_acceleration`. The `header.frame_id` will be `imu_link`.

If `/imu` is missing, check the intermediate bridge topic:
```bash
ros2 topic echo /go2/imu_plugin/out --once
```
If that also missing, Gazebo's IMU sensor hasn't initialised yet — wait another 10–15 s and retry.

---

## 2. Odometry

```bash
ros2 topic echo /odom --once
```

Expected: `pose.pose.position` and `orientation` populated. In simulation, move the robot (see Teleoperation below) and verify position changes.

```bash
# Confirm odom→base_link TF is broadcasting
ros2 run tf2_ros tf2_echo odom base_link
```

---

## 3. LiDAR / Point Cloud

**Hardware:**

The hardware pipeline decodes raw Unitree LiDAR frames → 3-D point cloud → 2-D scan.

```bash
# 3-D point cloud (hardware only)
ros2 topic echo /point_cloud2 --once
# Expected: height, width, fields=[x,y,z float32], non-zero data

# 2-D scan derived from point cloud
ros2 topic echo /scan --once
# Expected: ranges array with float32 distances, few or no inf values near walls/floors

# Confirm LiDAR pipeline nodes are running
ros2 node list | grep lidar
# expect: /lidar_to_pointcloud  /go2_pointcloud_to_laserscan
```

In RViz: `PointCloud2` display → 3-D ring of points. `LaserScan` → 2-D horizontal ring.

**Simulation:**

`/point_cloud2` is **not published in simulation**. Gazebo's GPU LiDAR directly produces a `LaserScan` — no point cloud intermediate step. SLAM and Nav2 both read `/scan`.

```bash
ros2 topic echo /scan --once
```

Expected: a `sensor_msgs/LaserScan` with `frame_id: laser_frame`, `range_max: 12.0`. Many `ranges` entries will be `inf` — this is **normal** and means the beam did not hit any obstacle within 12 m (open space in the café world). Valid hits appear as finite values between `range_min` (0.05) and `range_max` (12.0).

Drive the robot toward a wall with teleop and re-echo: the sector facing the wall should change from `inf` to a finite distance.

In RViz: add a `LaserScan` display on topic `/scan`. Beams pointing at walls appear; open-space beams are absent (filtered as `inf`). There is no `PointCloud2` display in simulation.

```bash
# Confirm /scan is flowing (should match LiDAR update rate from xacro: 10 Hz)
ros2 topic hz /scan   # expect ~10 Hz
```

---

## 4. Camera

**Hardware:**
```bash
ros2 topic echo /camera/image_raw --once
```

**Simulation:**

The camera topic is `/go2_camera/color/image_raw` (not `/camera/image_raw`). The simulation RViz config (`single_robot_conf_sim.rviz`) is pre-set to this topic. If you see "No Image" in RViz, open the Image panel properties and confirm the topic is `/go2_camera/color/image_raw`.

**Viewing the stream — options in order of availability:**

Option 1 — **RViz Image panel** (always available, no extra packages):
In the running RViz window, the Image panel at the bottom already subscribes to the camera topic. If it shows "No Image", click the topic field and set it to `/go2_camera/color/image_raw` (simulation) or `/camera/image_raw` (hardware).

Option 2 — **Foxglove** (always available via Docker):
In Foxglove Studio, add an **Image** panel and set its topic to `/go2_camera/color/image_raw`. No extra packages needed.

Option 3 — **`image_tools`** :
```bash
ros2 run image_tools showimage \
  --ros-args -r /image:=/go2_camera/color/image_raw   # simulation
# or:
ros2 run image_tools showimage \
  --ros-args -r /image:=/camera/image_raw              # hardware
```

Option 4 — **`rqt_image_view`** :
```bash
apt-get install -y ros-jazzy-rqt-image-view
ros2 run rqt_image_view rqt_image_view /go2_camera/color/image_raw
```

Expected: a live colour image from the robot's front-facing camera. In simulation the image appears ~15–30 s after launch (Gazebo lazy init).

---

## 5. Joint States

```bash
ros2 topic echo /joint_states --once
```

Expected: 12 joint names (FL_hip, FL_thigh, FL_calf × 4 legs) with `position` values. On hardware, updates arrive at ~1 Hz due to a firmware limit — this is normal. In simulation, the rate is higher.

In RViz, the `RobotModel` display should show the URDF correctly oriented and moving when the robot walks.

---

## 6. Teleoperation (Joystick)

With a gamepad connected:

```bash
# Verify joy node sees the controller
ros2 run joy joy_enumerate_devices

# Confirm joy messages are publishing
ros2 topic echo /joy --once
```

Expected: `buttons` and `axes` arrays with values. Drive the robot using the left stick. The command pipeline:

```
Joystick  → joy_node → teleop_twist_joy → /cmd_vel_joy      (priority 10) ─┐
Foxglove  → Publish panel              → /cmd_vel_foxglove  (priority  8) ─┤→ twist_mux → /cmd_vel_out → driver → robot
Nav2      → velocity_smoother          → /cmd_vel           (priority  5) ─┘
```

Verify the mux output is flowing:
```bash
ros2 topic echo /cmd_vel_out
```

**Special joystick buttons (direct to driver):**
- Button 0: Stand up
- Button 1: Stand down

**Foxglove teleop** — in Foxglove Studio, open a **Publish** panel, set the topic to `/cmd_vel_foxglove`, schema to `geometry_msgs/msg/Twist`, and publish `{linear: {x: 0.2}}` to drive forward. Priority 8 means it overrides Nav2 but yields to a connected joystick.

**Without a physical joystick** — publish directly into the highest-priority mux input:
```bash
# Move forward for a few seconds (bypasses Nav2, highest priority)
ros2 topic pub /cmd_vel_joy geometry_msgs/msg/Twist \
  "{linear: {x: 0.2}, angular: {z: 0.0}}" --rate 10
# Stop
ros2 topic pub /cmd_vel_joy geometry_msgs/msg/Twist "{}" --once
```

---

## 7. Robot Commands

`/sim_cmd` now accepts **the same message type as `/webrtc_req`** — `go2_interfaces/msg/WebRtcReq`. The same `ros2 topic pub` command works in both modes; only the topic name changes.

```bash
# Sit
ros2 topic pub /webrtc_req go2_interfaces/msg/WebRtcReq "{api_id: 1009}" --once   # hardware
ros2 topic pub /sim_cmd    go2_interfaces/msg/WebRtcReq "{api_id: 1009}" --once   # simulation

# Stand up
ros2 topic pub /webrtc_req go2_interfaces/msg/WebRtcReq "{api_id: 1004}" --once
ros2 topic pub /sim_cmd    go2_interfaces/msg/WebRtcReq "{api_id: 1004}" --once
```

### Supported api_ids in simulation

| api_id | Hardware name | Simulation behaviour |
|---|---|---|
| 1001 | Damp | Switch to REST (safe stop) |
| 1002 | BalanceStand | Switch to STAND controller |
| 1003 | StopMove | Switch to REST |
| 1004 | StandUp | Switch to REST (stand still) |
| 1005 | StandDown | Sit pose (body lowered −0.15 m) |
| 1006 | RecoveryStand | REST → TROT transition |
| 1007 | Euler | Set body roll/pitch/yaw — `parameter: "roll,pitch,yaw"` in radians |
| 1009 | Sit | Same as StandDown |
| 1010 | RiseSit | Switch to REST |
| 1011 | SwitchGait | Switch gait — `parameter: "0"`=REST `"1"`=TROT `"2"`=CRAWL `"3"`=STAND |
| 1013 | BodyHeight | Body height offset — `parameter: float` metres, clamped ±0.15 |
| 1015 | SpeedLevel | Velocity multiplier — `parameter: "0"`=slow(×0.5) `"1"`=normal `"2"`=fast(×1.5) |
| 1017 | Stretch | STAND pose: body extended forward + raised |
| 1019 | ContinuousGait | autoRest toggle — `parameter: "0"`=always trot `"1"`=rest when still |

Commands with a `parameter` field:
```bash
# Body roll 15° (0.26 rad), no pitch/yaw
ros2 topic pub /sim_cmd go2_interfaces/msg/WebRtcReq \
  "{api_id: 1007, parameter: '0.26,0.0,0.0'}" --once

# Raise body 10 cm
ros2 topic pub /sim_cmd go2_interfaces/msg/WebRtcReq \
  "{api_id: 1013, parameter: '0.10'}" --once

# Fast speed
ros2 topic pub /sim_cmd go2_interfaces/msg/WebRtcReq \
  "{api_id: 1015, parameter: '2'}" --once

# Switch to CRAWL gait
ros2 topic pub /sim_cmd go2_interfaces/msg/WebRtcReq \
  "{api_id: 1011, parameter: '2'}" --once

# Always trot (disable autoRest) — legs keep cycling even at zero velocity
ros2 topic pub /sim_cmd go2_interfaces/msg/WebRtcReq \
  "{api_id: 1019, parameter: '0'}" --once
```

**Walking after sit/up:**
After switching to TROT mode (`api_id: 1006` or `1011 parameter:'1'`), the robot won't translate until velocity commands arrive. The gait controller's `autoRest` feature pauses leg cycling when velocity is zero:
```bash
ros2 topic pub /sim_cmd go2_interfaces/msg/WebRtcReq "{api_id: 1006}" --once
ros2 topic pub /cmd_vel_joy geometry_msgs/msg/Twist "{linear: {x: 0.2}}" --rate 10
```

**Hardware-only** (not implemented in simulation — logs a warning):
`Hello(1016)`, `Dance1(1022)`, `Dance2(1023)`, `FrontFlip(1030)`, `FrontJump(1031)`,
`WiggleHips(1033)`, `FingerHeart(1036)`, `Handstand(1301)`, `MoonWalk(1305)`, and other animation commands.

**Hardware** — same api_ids work directly on the real robot:
```bash
ros2 topic pub /webrtc_req go2_interfaces/msg/WebRtcReq \
  "{api_id: 1016, topic: 'rt/api/sport/request'}" --once   # Wave hello (hardware only)
```

---

## 8. SLAM (Map Building)

Both modes use the same `slam_toolbox` stack.

```bash
# Check SLAM is publishing a map
ros2 topic hz /map
# expect: ~0.2 Hz (updates every 5 s per slam config)

# Echo map metadata
ros2 topic echo /map --once --no-arr
```

In RViz: the `Map` display should show a growing occupancy grid as the robot moves. Cells turn white (free), black (occupied), or grey (unknown).

**Save a map** (via RViz SlamToolboxPlugin → "Save Map" + "Serialize Map") or via CLI:
```bash
ros2 service call /slam_toolbox/save_map slam_toolbox/srv/SaveMap \
  "{name: {data: 'my_map'}}"
```

---

## 9. Autonomous Navigation (Nav2)

After SLAM has built a map or a saved map has been loaded:

```bash
# Confirm Nav2 lifecycle nodes are active
ros2 lifecycle get /bt_navigator

# Check costmaps are publishing
ros2 topic hz /global_costmap/costmap
ros2 topic hz /local_costmap/costmap
```

Send a navigation goal without RViz:
```bash
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: 'map'}, pose: {position: {x: 1.0, y: 0.5, z: 0.0}, orientation: {w: 1.0}}}}"
```

Monitor progress:
```bash
ros2 topic echo /plan --once --no-arr   # global path
ros2 topic echo /cmd_vel                # Nav2 velocity output (twist_mux input, priority 5)
ros2 topic echo /cmd_vel_out            # twist_mux output → driver
```

---

## 10. Object Detection (YOLO)

Start `yolo_detector_node` in a separate terminal after the main launch.

**Hardware:**
```bash
source install/setup.bash
ros2 run yolo_detector yolo_detector_node \
  --ros-args -p model:=yolo11n.pt -p device:=cpu -p detection_threshold:=0.5
```

**Simulation** (camera topic differs):
```bash
ros2 run yolo_detector yolo_detector_node \
  --ros-args -r /camera/image_raw:=/go2_camera/color/image_raw \
             -p model:=yolo11n.pt -p device:=cpu
```

Verify detections:
```bash
ros2 topic echo /detected_objects
# Fields: class_id (string label e.g. "person"), score (0–1), bbox center + size
```

View annotated stream:
```bash
ros2 run image_tools showimage --ros-args -r /image:=/annotated_image
```

First run downloads the model weights to `~/.cache/ultralytics/` — allow ~10 s.

---

## 11. Foxglove Bridge

Foxglove lets you inspect all topics remotely without RViz.

```bash
# Confirm the bridge is running
ros2 node list | grep foxglove

# Check it is listening
ros2 topic list | grep foxglove   # (bridge doesn't publish topics but node should be present)
```

Open Foxglove Studio → "Open Connection" → "Foxglove WebSocket" → `ws://localhost:8765`.

To enable Foxglove if it was disabled at launch:
```bash
ros2 launch go2_robot_sdk robot.launch.py foxglove:=true
```

---

## 12. TTS (Speech Processor)

TTS is started automatically by every launch file. The default provider is **piper** — offline neural TTS, no API key, no internet required after the first build (model is pre-baked into the Docker image). Cloud providers are optional upgrades for higher expressivity.

### Default — Piper (offline neural TTS, no key required)

Piper produces natural-sounding speech locally using an ONNX voice model. The Docker image ships `en_US-lessac-medium` (~65 MB) pre-baked so there is no first-run download.

```bash
# No env vars needed — piper is the default
ros2 topic pub /tts std_msgs/msg/String "{data: 'Hello from GO2'}" --once
```

Run the node manually (hardware, audio to robot speaker):
```bash
ros2 run speech_processor tts_node \
  --ros-args -p provider:=piper -p voice_name:=en_US-lessac-medium
ros2 topic pub /tts std_msgs/msg/String "{data: 'Hello from GO2'}" --once
```

Simulation — play through the computer's speaker:
```bash
ros2 run speech_processor tts_node \
  --ros-args -p provider:=piper -p voice_name:=en_US-lessac-medium \
             -p local_playback:=true
ros2 topic pub /tts std_msgs/msg/String "{data: 'Hello from simulation'}" --once
```

**Piper voice options** — follows the `lang_COUNTRY-speaker-quality` convention:

| Voice | Language | Size | Quality |
|---|---|---|---|
| `en_US-lessac-medium` | English US | ~65 MB | ⭐⭐⭐ (default) |
| `en_US-ryan-high` | English US | ~120 MB | ⭐⭐⭐⭐ |
| `en_GB-alan-medium` | English GB | ~65 MB | ⭐⭐⭐ |
| `de_DE-thorsten-medium` | German | ~65 MB | ⭐⭐⭐ |
| `fr_FR-upmc-medium` | French | ~65 MB | ⭐⭐⭐ |
| `es_ES-mls_10246-low` | Spanish | ~30 MB | ⭐⭐ |

Full voice list: `https://huggingface.co/rhasspy/piper-voices`

To use a non-default voice at runtime (model auto-downloaded on first use):
```bash
TTS_VOICE=en_US-ryan-high ros2 launch go2_robot_sdk robot.launch.py
```

To use a non-default voice baked into the Docker image at build time:
```bash
docker build --build-arg PIPER_VOICE=en_US-ryan-high -f docker/Dockerfile .
```

**Jetson NX** — CUDA-accelerated inference (`PIPER_USE_CUDA=true` is set automatically by `docker-compose.jetson.yml`):
```bash
# Jetson: CUDA inference enabled automatically
ROBOT_IP=192.168.x.x \
  docker-compose -f docker/docker-compose.yml -f docker/docker-compose.jetson.yml up
```

### Fallback — espeak (offline legacy TTS, no key, no model download)

espeak-ng is still available as `TTS_PROVIDER=espeak`. Quality is robotic but it always works with zero setup — useful if piper model download fails or disk space is constrained.

```bash
ros2 run speech_processor tts_node \
  --ros-args -p provider:=espeak -p voice_name:=en
ros2 topic pub /tts std_msgs/msg/String "{data: 'Hello from GO2'}" --once
```

espeak voice options: any `espeak-ng` voice string — `en`, `en-us`, `en-gb`, `de`, `fr`, `es`, etc.
Check available voices: `espeak-ng --voices`

### Cloud providers (highest expressivity, API key required)

**OpenAI** (`tts-1` / `tts-1-hd`, voice `nova`):
```bash
export OPENAI_API_KEY=sk-...
ros2 run speech_processor tts_node \
  --ros-args -p provider:=openai -p api_key:=$OPENAI_API_KEY -p voice_name:=nova
ros2 topic pub /tts std_msgs/msg/String "{data: 'Hello from GO2'}" --once
```
Voice options: `alloy`, `echo`, `fable`, `onyx`, `nova` (default), `shimmer`

**ElevenLabs** (expressive, higher latency):
```bash
export ELEVENLABS_API_KEY=...
ros2 run speech_processor tts_node \
  --ros-args -p provider:=elevenlabs -p api_key:=$ELEVENLABS_API_KEY \
             -p voice_name:=XrExE9yKIg1WjnnlVkGX
```

**Gemini** (`gemini-2.5-flash-tts-preview`):
```bash
export GEMINI_API_KEY=...
ros2 run speech_processor tts_node \
  --ros-args -p provider:=gemini -p api_key:=$GEMINI_API_KEY -p voice_name:=Kore
ros2 topic pub /tts std_msgs/msg/String "{data: 'Hello from Gemini'}" --once
```
Voice options: `Kore` (default), `Zephyr`, `Puck`, `Charon`, `Fenrir`, `Leda`, `Orus`, `Aoede`, `Callirrhoe`

### Selecting the provider at launch

```bash
# Bare metal — use OpenAI instead of piper
TTS_PROVIDER=openai OPENAI_API_KEY=sk-... ros2 launch go2_robot_sdk robot.launch.py

# Bare metal — use espeak legacy fallback
TTS_PROVIDER=espeak ros2 launch go2_robot_sdk robot.launch.py

# Docker — use Gemini
TTS_PROVIDER=gemini GEMINI_API_KEY=... docker-compose up
```

`local_playback` plays through the system's default audio device (pydub). Audio is cached in `tts_cache/` after the first synthesis call — repeated phrases skip the API or piper subprocess.

---

## 13. STT (Speech Processor — Speech-to-Text)

Start `stt_node` in a separate terminal after the main launch. The microphone must be attached to the host PC or Jetson NX.

### Tier 1 — OpenAI Whisper API (internet required, same key as TTS)

```bash
export OPENAI_API_KEY=sk-...
ros2 run speech_processor stt_node \
  --ros-args -p stt_provider:=openai -p api_key:=$OPENAI_API_KEY
```

### Tier 1 — Gemini STT (internet required)

```bash
export GEMINI_API_KEY=...
ros2 run speech_processor stt_node \
  --ros-args -p stt_provider:=gemini -p api_key:=$GEMINI_API_KEY
```

### Tier 2 — Local offline, Jetson NX GPU

```bash
ros2 run speech_processor stt_node \
  --ros-args -p stt_provider:=faster_whisper \
             -p device:=cuda \
             -p compute_type:=float16 \
             -p whisper_model:=base
```

### CPU fallback (standard PC, no GPU)

```bash
ros2 run speech_processor stt_node \
  --ros-args -p stt_provider:=faster_whisper \
             -p device:=cpu \
             -p compute_type:=int8
```

**Verify transcription is publishing:**

```bash
ros2 topic echo /speech_text
# Speak into the microphone → transcript appears within ~30 ms (Jetson GPU) to ~2 s (API)
```

**Voice echo test** — pipe transcription back to the TTS speaker:

```bash
ros2 run topic_tools relay /speech_text /tts
# Speak → robot repeats what it heard
```

**Via docker-compose** (`ENABLE_STT=true` also starts `voice_cmd_node` automatically):

```bash
# Tier 1 — OpenAI unified (internet, same API key for STT + TTS + NLU)
ROBOT_IP=192.168.x.x OPENAI_API_KEY=sk-... ENABLE_STT=true \
  STT_PROVIDER=openai TTS_PROVIDER=openai NLU_PROVIDER=openai docker-compose up

# Tier 2 — Jetson NX offline (GPU-accelerated, no internet)
ROBOT_IP=192.168.x.x ENABLE_STT=true \
  STT_PROVIDER=faster_whisper STT_DEVICE=cuda WHISPER_MODEL=small \
  docker-compose -f docker/docker-compose.yml -f docker/docker-compose.jetson.yml up
```

**Via launch file** (`enable_stt:=true` also starts `voice_cmd_node`):

```bash
ENABLE_STT=true STT_PROVIDER=faster_whisper STT_DEVICE=cuda \
  ros2 launch go2_robot_sdk robot.launch.py enable_stt:=true
```

### Troubleshooting

**`PortAudioError: Error querying device -1` on startup**

`stt_node` logs this traceback and the capture thread dies silently if no microphone is accessible:

```
[stt_node-5] Exception in thread Thread-3 (_capture_loop):
[stt_node-5] ...
[stt_node-5] sounddevice.PortAudioError: Error querying device -1
```

The ROS2 node itself stays alive (no crash), but `/speech_text` will never publish. Causes and fixes:

| Symptom | Cause | Fix |
|---|---|---|
| Native Linux, no mic plugged in | No audio input device at index −1 | Plug in a USB/3.5 mm microphone |
| Docker on Windows (no override file) | WSL2 does not expose `/dev/snd` by default | Add `docker-compose.windows.yml` override (passes WSLg PulseAudio socket) |
| Docker on Linux, `/dev/snd` missing | Container `devices:` block not matched | Ensure `privileged: true` and `/dev/snd:/dev/snd` in compose file |
| Jetson NX, device shows up but errors | Wrong ALSA device index | Set `STT_DEVICE_INDEX` env var to the correct index from `python3 -m sounddevice` |

To list available audio input devices inside the container:
```bash
python3 -c "import sounddevice as sd; print(sd.query_devices())"
```

---

## 14. Voice Commands (Speech → Robot Action)

`voice_cmd_node` subscribes to `/speech_text` and routes recognised phrases to the robot.  
It must be started alongside `stt_node`.

### Start the full voice pipeline

**Bare metal (launch file):** `enable_voice_cmd` defaults to the same value as `enable_stt` — one flag starts both nodes.

**Hardware:**
```bash
ros2 launch go2_robot_sdk robot.launch.py enable_stt:=true
```

**Simulation:**
```bash
ros2 launch go2_robot_sdk simulation.launch.py enable_stt:=true
```

**Docker:** `ENABLE_STT` and `ENABLE_VOICE_CMD` both default to `true` in `docker-compose.yml` — no extra flags needed. Both nodes start unless explicitly disabled:
```bash
# Both STT and voice commands active (default Docker behaviour)
ROBOT_IP=192.168.x.x docker-compose up

# STT only, no command routing
ROBOT_IP=192.168.x.x ENABLE_VOICE_CMD=false docker-compose up
```

To run STT-only (transcription without command routing, bare metal):
```bash
ros2 launch go2_robot_sdk robot.launch.py enable_stt:=true enable_voice_cmd:=false
```

**Manually (two terminals):**
```bash
# Terminal 1 — transcription
ros2 run speech_processor stt_node \
  --ros-args -p stt_provider:=faster_whisper -p device:=cpu

# Terminal 2 — command router (hardware)
ros2 run speech_processor voice_cmd_node \
  --ros-args -p cmd_topic:=/webrtc_req

# Terminal 2 — command router (simulation)
ros2 run speech_processor voice_cmd_node \
  --ros-args -p cmd_topic:=/sim_cmd
```

### Supported voice phrases

| Category | Example phrases | Effect |
|---|---|---|
| **Posture** | "sit", "sit down", "lie down" | api_id 1009 |
| | "stand", "stand up", "get up", "rise" | api_id 1004 |
| | "balance", "balance stand" | api_id 1002 |
| | "recover", "recovery stand" | api_id 1006 |
| | "stretch" | api_id 1017 |
| | "stop", "halt", "freeze" | api_id 1003 |
| **Gait** | "trot", "jog", "walk mode" | api_id 1011 param=1 |
| | "crawl", "crawl mode" | api_id 1011 param=2 |
| | "stand gait", "stand mode" | api_id 1011 param=3 |
| **Speed** | "slow", "slow down" | api_id 1015 param=0 |
| | "normal speed", "medium speed" | api_id 1015 param=1 |
| | "fast", "speed up", "full speed" | api_id 1015 param=2 |
| **Height** | "raise body", "higher", "lift body" | api_id 1013 param=+0.05 m |
| | "lower body", "lower", "duck" | api_id 1013 param=−0.05 m |
| **Movement** | "go forward", "forward", "advance" | `/cmd_vel_voice` linear.x + |
| | "go back", "backward", "reverse" | `/cmd_vel_voice` linear.x − |
| | "turn left", "rotate left" | `/cmd_vel_voice` angular.z + |
| | "turn right", "rotate right" | `/cmd_vel_voice` angular.z − |
| | "stop moving", "stop walking" | `/cmd_vel_voice` zero |
| **Gestures** (hardware only) | "hello", "wave" | api_id 1016 |
| | "dance", "dance one" | api_id 1022 |
| | "wiggle", "wiggle hips" | api_id 1033 |
| | "handstand" | api_id 1301 |
| | "moonwalk" | api_id 1305 |

Gestures marked hardware-only are **silently skipped in simulation** (warning logged).

### NLU provider selection

**Keyword (default, offline):** regex pattern matching, instant response, no API key.

**OpenAI (natural language):** GPT-4o-mini parses free-form speech, e.g. "could you please sit down?" — needs `OPENAI_API_KEY` and internet.

```bash
# OpenAI NLU
ros2 run speech_processor voice_cmd_node \
  --ros-args -p cmd_topic:=/webrtc_req \
             -p nlu_provider:=openai \
             -p api_key:=$OPENAI_API_KEY
```

**Gemini (natural language):** gemini-2.5-flash parses free-form speech — needs `GEMINI_API_KEY` and internet.

```bash
# Gemini NLU
ros2 run speech_processor voice_cmd_node \
  --ros-args -p cmd_topic:=/webrtc_req \
             -p nlu_provider:=gemini \
             -p api_key:=$GEMINI_API_KEY
```

**Claude (natural language):** claude-haiku-4-5 parses free-form speech — needs `ANTHROPIC_API_KEY` and internet. Claude does not offer TTS or STT, so pair it with a different STT provider.

```bash
# Claude NLU
ros2 run speech_processor voice_cmd_node \
  --ros-args -p cmd_topic:=/webrtc_req \
             -p nlu_provider:=claude \
             -p api_key:=$ANTHROPIC_API_KEY
```

### Verify commands are firing

```bash
# Watch the command topic (hardware)
ros2 topic echo /webrtc_req

# Watch the command topic (simulation)
ros2 topic echo /sim_cmd

# Watch movement velocity
ros2 topic echo /cmd_vel_voice

# Inject a test phrase without speaking (bypass STT)
ros2 topic pub /speech_text std_msgs/msg/String "{data: 'sit down'}" --once
ros2 topic pub /speech_text std_msgs/msg/String "{data: 'go forward'}" --once
ros2 topic pub /speech_text std_msgs/msg/String "{data: 'trot'}" --once
```

### Movement priority in twist_mux

Voice movement commands are published to `/cmd_vel_voice` at **priority 7** — between Foxglove (8) and Nav2 (5). A connected joystick always overrides voice.

```
Joystick   → /cmd_vel_joy      priority 10  ┐
Foxglove   → /cmd_vel_foxglove priority  8  ├─→ twist_mux → /cmd_vel_out → driver
Voice      → /cmd_vel_voice    priority  7  │
Nav2       → /cmd_vel          priority  5  ┘
```

### Docker

`ENABLE_STT` and `ENABLE_VOICE_CMD` both default to `true` in `docker-compose.yml`, so you only need to supply the provider and key.

```bash
# Tier 1 — OpenAI STT + OpenAI NLU (same key, internet required)
ROBOT_IP=192.168.x.x OPENAI_API_KEY=sk-... \
  STT_PROVIDER=openai NLU_PROVIDER=openai docker-compose up

# Tier 1 — Gemini STT + Gemini NLU (same key, internet required)
ROBOT_IP=192.168.x.x GEMINI_API_KEY=... \
  STT_PROVIDER=gemini NLU_PROVIDER=gemini TTS_PROVIDER=gemini docker-compose up

# Tier 1 — OpenAI STT + Claude NLU (Claude for best command understanding)
ROBOT_IP=192.168.x.x OPENAI_API_KEY=sk-... ANTHROPIC_API_KEY=sk-ant-... \
  STT_PROVIDER=openai NLU_PROVIDER=claude docker-compose up

# Tier 2 — local STT (faster-whisper) + keyword NLU, fully offline
ROBOT_IP=192.168.x.x \
  STT_PROVIDER=faster_whisper STT_DEVICE=cuda WHISPER_MODEL=base \
  NLU_PROVIDER=keyword docker-compose up

# Windows 11 — include the WSLg mic override to get microphone access
ROBOT_IP=192.168.x.x OPENAI_API_KEY=sk-... STT_PROVIDER=openai \
  docker-compose -f docker/docker-compose.yml -f docker/docker-compose.windows.yml up
```

---

## Mode Differences at a Glance

| Capability | Hardware | Simulation | Notes |
|---|---|---|---|
| IMU | ✓ `/imu` (`go2_interfaces/IMU`) | ✓ `/imu` (`sensor_msgs/Imu`) | Different message type; appears ~15–30 s after launch in sim |
| Odometry | ✓ `/odom` | ✓ `/odom` | Same topic |
| 3-D point cloud | ✓ `/point_cloud2` | ✗ not published | Sim provides LaserScan directly; no point cloud step |
| 2-D scan | ✓ `/scan` (from `pointcloud_to_laserscan`) | ✓ `/scan` (GPU LiDAR direct) | Sim scan has many `inf` ranges — open beams, not errors |
| Camera image | ✓ `/camera/image_raw` | ✓ `/go2_camera/color/image_raw` | Different topic — remap yolo_detector for sim |
| Camera info | ✓ `/camera/camera_info` | ✓ `/go2_camera/color/camera_info` | Different topic |
| Joint states | ✓ `/joint_states` (~1 Hz) | ✓ `/joint_states` (~50 Hz) | Same topic; firmware limits hardware rate |
| Joystick/teleop | ✓ | ✓ | Identical |
| SLAM | ✓ | ✓ | Identical; both read `/scan` |
| Nav2 | ✓ | ✓ | Sim uses `nav2_params_sim.yaml` |
| YOLO detection | ✓ | ✓ (remap needed) | See section 10 |
| Robot commands | ✓ `/webrtc_req` | ✓ `/sim_cmd` | Same message type (`WebRtcReq`), same `api_id`s — only topic name differs |
| TTS | ✓ robot speaker | ✓ computer speaker | Add `-p local_playback:=true` for sim |
| STT | ✓ `/speech_text` | ✓ `/speech_text` | Start `stt_node` separately; mic must be on host PC or Jetson |
| Voice commands | ✓ → `/webrtc_req` | ✓ → `/sim_cmd` | Same phrases; hardware-only gestures skipped in sim |
| Foxglove | ✓ | ✓ (disabled by default) | Pass `foxglove:=true` |
