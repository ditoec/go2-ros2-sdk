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

The camera source depends on which mode you are in:

| Mode | Source | Topic |
|---|---|---|
| Hardware (WebRTC) | Robot's front camera via WebRTC driver | `/camera/image_raw` |
| Windows Docker (`CAM_BRIDGE=true`) | Host browser webcam via `cam_bridge_node` | `/camera/image_raw` |
| Simulation (Gazebo) | Gazebo camera sensor via bridge | `/go2_camera/color/image_raw` |

**Hardware / Windows cam_bridge:**
```bash
ros2 topic echo /camera/image_raw --once
ros2 topic hz /camera/image_raw   # hardware ~30 Hz; cam_bridge default ~10 Hz
```

For Windows cam_bridge, confirm the node is streaming before echoing:
```bash
ros2 node list | grep cam_bridge      # Expected: /cam_bridge_node
```
Then open `http://localhost:8891` in your browser, click **Connect → Start Streaming**.

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
apt-get install -y ros-humble-rqt-image-view
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

Start `yolo_detector_node` in a separate terminal after the main launch. The node subscribes to `/camera/image_raw` in all modes.

**Hardware (robot camera) or Windows cam_bridge (`CAM_BRIDGE=true`):**
```bash
source install/setup.bash
ros2 run yolo_detector yolo_detector_node \
  --ros-args -p model:=yolo11n.pt -p device:=cpu -p detection_threshold:=0.5
# No remap needed — /camera/image_raw is published by either the driver or cam_bridge_node
```

For Windows cam_bridge: make sure the browser page is open and streaming (`http://localhost:8891`) before starting the detector — the node will block on the first image message.

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

## 11. Gemma Vision (Windows GPU profile)

`gemma_vision_node` subscribes to the camera and publishes natural-language scene descriptions at 0.5 Hz (default). It is only started when `ENABLE_GEMMA_VISION=true` (set automatically by `docker-compose.windows-gpu.yml`).

**Verify the node is running:**
```bash
ros2 node list | grep gemma_vision
# Expected: /gemma_vision_node
```

**Check scene descriptions:**
```bash
ros2 topic echo /scene_description
# Expect: natural-language descriptions such as:
# "A hallway with a chair on the left. A person is standing approximately 3 metres ahead."
```

**Check annotated image** (frame with description overlaid):
```bash
ros2 run image_tools showimage --ros-args -r /image:=/gemma_annotated_image
```

**Confirm inference rate:**
```bash
ros2 topic hz /scene_description
# Default: ~0.5 Hz (1 inference every 2 s). Override with GEMMA_VISION_RATE.
```

**Hardware** — uses `/camera/image_raw`. **Simulation** — uses `/go2_camera/color/image_raw` (remap if needed):
```bash
# Simulation (remap camera topic)
ros2 run speech_processor gemma_vision_node \
  --ros-args -p camera_topic:=/go2_camera/color/image_raw
```

**Topics:**

| Topic | Type | Notes |
|---|---|---|
| `/scene_description` | `std_msgs/String` | Human-readable scene description from Gemma |
| `/gemma_annotated_image` | `sensor_msgs/Image` | Camera frame with description text overlaid |

**Troubleshooting:**

| Symptom | Cause | Fix |
|---|---|---|
| Node starts but `/scene_description` empty | Ollama not running or model not loaded | Check `curl http://localhost:11434/api/tags`; ensure `ollama_init` completed |
| Node crashes on import | `cv_bridge` not installed | Already included in all Dockerfiles — rebuild the image |
| Very slow inference | GPU not used by Ollama | Check `docker-compose.windows-gpu.yml` GPU reservation; run `nvidia-smi` in the container |

---

## 12. Camera Bridge (`CAM_BRIDGE=true`, Windows)

`cam_bridge_node` lets you use the host laptop webcam as the robot's camera source inside a Windows Docker container. It is the correct starting point for testing face recognition or object detection on Windows without a connected robot.

**Start with cam_bridge enabled (Windows GPU compose defaults to `CAM_BRIDGE=true`):**
```bash
ENABLE_FACE=true docker-compose \
  -f docker/docker-compose.yml \
  -f docker/docker-compose.windows-gpu.yml up
# cam_bridge starts automatically (CAM_BRIDGE=true is the default)
```

Or on plain Windows (no GPU):
```bash
CAM_BRIDGE=true docker-compose up
```

**Verify the node is running:**
```bash
ros2 node list | grep cam_bridge
# Expected: /cam_bridge_node
```

**Start the webcam stream:**
1. Open `http://localhost:8891` in your Windows browser.
2. Click **Connect** — the page opens the WebSocket and requests webcam permission.
3. Click **Start Streaming** — frames flow to `/camera/image_raw`.

**Confirm messages are arriving:**
```bash
ros2 topic hz /camera/image_raw
# Expected: ~10 Hz (default FPS slider in the browser page)

ros2 topic echo /camera/camera_info --once
# Expected: width/height matching your webcam resolution, identity K matrix
```

**Adjust FPS and quality** — use the sliders in the browser page. Higher FPS increases latency on slow networks; lower quality reduces bandwidth.

**Troubleshooting:**

| Symptom | Fix |
|---|---|
| `/camera/image_raw` not publishing | Confirm browser page is open and "Streaming" indicator is green |
| `WebSocket error — is port 8892 reachable?` | Check `docker-compose.yml` maps port 8892; try `http://localhost:8891` (not 8892) |
| Camera permission denied in browser | Use Chrome/Edge; `localhost` is always allowed; HTTPS not required |
| Low FPS | Reduce JPEG quality in the browser slider (75 → 50) |

---

## 13. Face Recognition (`ENABLE_FACE=true`)

`face_recognition_node` runs InsightFace SCRFD detection + ArcFace embedding on `/camera/image_raw` and matches against the enrollment database. On Windows use cam_bridge as the camera source (see §12 above).

**Start with face recognition enabled:**
```bash
# Windows GPU (cam_bridge enabled automatically, face recognition on)
ENABLE_FACE=true docker-compose \
  -f docker/docker-compose.yml \
  -f docker/docker-compose.windows-gpu.yml up
```

**Verify nodes are running:**
```bash
ros2 node list | grep -E "face_recognition|face_enrollment"
# Expected: /face_recognition_node  /face_enrollment_node
```

**Enroll a face via the web UI:**
1. Open `http://localhost:8890` in your browser.
2. Click **Start Webcam** → **Capture** (or upload a JPEG photo).
3. Type a name (e.g. `Dito`) → click **Enroll**.
4. The node writes `face_db/Dito/0000.jpg` and auto-publishes `/reload_faces`. Watch the container log:
   ```
   [face_recognition_node]: Reloading face DB from disk…
   [face_recognition_node]: Face DB: 1 people, 1 embeddings at /ros2_ws/face_db
   ```

**Verify recognition:**
```bash
ros2 topic echo /recognized_face_names
# → "Dito"  when the enrolled face is in the webcam frame
# → ""      when no known face is visible

ros2 topic echo /recognized_faces
# Detection2DArray; class_id: "Dito", score: ~0.6–0.9 when matching

ros2 run image_tools showimage --ros-args -r /image:=/face_annotated_image
# Boxes with name labels rendered on the camera frame
```

**Tune the match threshold:**
- In the enrollment UI (`http://localhost:8890`), drag the **Threshold** slider and click **Apply**.
- The live table below shows names and real-time scores — raise the threshold if you see false positives.
- Manual override:
  ```bash
  ros2 topic pub /face_threshold std_msgs/Float32 "{data: 0.45}" --once
  ```

**Manual face DB reload** (if you drop photos into `face_db/` without using the UI):
```bash
ros2 topic pub /reload_faces std_msgs/Empty "{}" --once
```

**End-to-end greeting test (Modul 4.4):**
```bash
ENABLE_FACE=true ENABLE_STT=true NLU_PROVIDER=gemma_local docker-compose \
  -f docker/docker-compose.yml \
  -f docker/docker-compose.windows-gpu.yml up
# With enrolled face in view, say "elliot, hello, who am I?"
# → robot replies with the recognized name
```

**Topics:**

| Topic | Type | Notes |
|---|---|---|
| `/recognized_faces` | `vision_msgs/Detection2DArray` | `class_id`=name, `score`=similarity; excludes Unknown |
| `/recognized_face_names` | `std_msgs/String` | Comma-joined names; empty string if no known face |
| `/face_annotated_image` | `sensor_msgs/Image` | Camera frame with bounding boxes + name labels |
| `/reload_faces` | `std_msgs/Empty` | Trigger live re-embed (auto-sent by enrollment UI) |
| `/face_threshold` | `std_msgs/Float32` | Live threshold update (published by enrollment UI slider) |

**Troubleshooting:**

| Symptom | Cause | Fix |
|---|---|---|
| Node starts but `/recognized_faces` is empty | No camera frames on `/camera/image_raw` | Start cam_bridge or confirm robot camera is streaming |
| "Face DB: 0 people" at startup | `face_db/` is empty or missing | Enroll via `http://localhost:8890` or drop photos into `./face_db/<Name>/` + reload |
| Score always < threshold | Lighting, angle, or threshold too high | Check `FACE_THRESHOLD` (lower = easier match); use bright frontal light; tune via slider |
| `onnxruntime` missing CUDA EP | Windows GPU container has no CUDA toolkit | Expected — node logs this and falls back to CPU; normal behaviour |

---

## 14. Foxglove Bridge

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

## 13. TTS (Speech Processor)

TTS is started automatically by every launch file. The default provider is **supertonic** — offline neural TTS, no API key, no internet required after the first build (model is pre-baked into the Docker image). Cloud providers are optional upgrades.

### Default — Supertonic (offline neural TTS, no key required)

Supertonic is a flow-matching ONNX TTS model (99 M parameters, 31 languages, RTF ~0.012). The Docker image pre-bakes the model (~305 MB) so there is no first-run download.

```bash
# No env vars needed — supertonic is the default
ros2 topic pub /tts std_msgs/msg/String "{data: 'Hello from GO2'}" --once
```

Run the node manually (hardware, audio to robot speaker):
```bash
ros2 run speech_processor tts_node \
  --ros-args -p provider:=supertonic -p voice_name:=F1
ros2 topic pub /tts std_msgs/msg/String "{data: 'Hello from GO2'}" --once
```

Simulation — play through the computer's speaker:
```bash
ros2 run speech_processor tts_node \
  --ros-args -p provider:=supertonic -p voice_name:=F1 -p local_playback:=true
ros2 topic pub /tts std_msgs/msg/String "{data: 'Hello from simulation'}" --once
```

**Supertonic voice options:**

| Voice | Gender | Notes |
|---|---|---|
| `F1` | Female | Default — neutral, expressive |
| `F2`–`F5` | Female | Additional female personas |
| `M1`–`M5` | Male | Male personas |

Voice is selected at runtime via `TTS_VOICE` — no model download needed (all voices share the same ~305 MB model):
```bash
TTS_VOICE=M2 ros2 launch go2_robot_sdk robot.launch.py
```

**Expression tags** (add natural vocal characteristics inline):
```bash
ros2 topic pub /tts std_msgs/msg/String \
  "{data: 'Great news! <laugh> The robot is ready.'}" --once
```
Supported tags: `<laugh>`, `<breath>`, `<sigh>`

**Quality vs speed** — `SUPERTONIC_STEPS` controls diffusion steps (5 = fastest, 12 = best quality, default 8):
```bash
SUPERTONIC_STEPS=5 ros2 launch go2_robot_sdk robot.launch.py   # fastest
SUPERTONIC_STEPS=12 ros2 launch go2_robot_sdk robot.launch.py  # best quality
```

**Language** — `VOICE_LANG` is the master knob (`en` | `id`); it focuses STT, NLU, and TTS
on one language at a time (the robot command output always stays English):
```bash
VOICE_LANG=id ros2 launch go2_robot_sdk robot.launch.py   # Indonesian end to end
```
`SUPERTONIC_LANG` overrides the **TTS** language only (it follows `VOICE_LANG` when unset).
Set it to any of Supertonic's 31 codes for spoken replies in a different language than the
speech input:
```bash
SUPERTONIC_LANG=de ros2 launch go2_robot_sdk robot.launch.py
```

### Cloud providers (highest expressivity, API key required)

**OpenAI** (`tts-1-hd`, voice `nova`):
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
# Bare metal — use OpenAI instead of supertonic
TTS_PROVIDER=openai OPENAI_API_KEY=sk-... ros2 launch go2_robot_sdk robot.launch.py

# Docker — use Gemini
TTS_PROVIDER=gemini GEMINI_API_KEY=... docker-compose up
```

`local_playback` plays through the system's default audio device (pydub). Audio is cached in `tts_cache/` after the first synthesis call — repeated phrases skip the synthesis entirely.

---

## 14. STT (Speech Processor — Speech-to-Text)

Start `stt_node` in a separate terminal after the main launch. The microphone must be attached to the host PC or Jetson NX.

> **Robot onboard mic (`STT_SOURCE=robot`):** instead of a host/USB mic, use the GO2's own mic. The driver captures the WebRTC audio track and republishes it on `/robot_audio`; `stt_node` reads it with `audio_source:=topic`. Requires `CONN_TYPE=webrtc` + `MIC_BRIDGE=false`. Launch: `ENABLE_STT=true MIC_BRIDGE=false STT_SOURCE=robot ROBOT_IP=<IP> docker-compose up`, then confirm audio is flowing with `ros2 topic hz /robot_audio`.

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

### Tier 2 — Gemma 4 E4B unified (offline, 8 GB GPU, Windows GPU profile)

`gemma_local` is a **unified provider**: one llama.cpp REST call handles STT + NLU + TTS response. Set automatically by `docker-compose.windows-gpu.yml`. `voice_cmd_node` is not started.

```bash
# Via mic_bridge_node (browser mic → unified pipeline, llama.cpp sidecar must be running)
ros2 run speech_processor mic_bridge_node \
  --ros-args -p stt_provider:=gemma_local \
             -p llama_cpp_host:=http://localhost:8080 \
             -p gemma_model:=gemma \
             -p wake_word:=elliot

# Via stt_node (physical mic on Jetson, same unified path)
ros2 run speech_processor stt_node \
  --ros-args -p stt_provider:=gemma_local \
             -p llama_cpp_host:=http://localhost:8080 \
             -p gemma_model:=gemma \
             -p wake_word:=elliot
```

**What to expect:**
- Speak wake word + command (e.g. "Elliot sit down")
- llama.cpp (launched with `--jinja`) returns a native tool call:
  `execute_robot_command{contains_wake_word: true, command: "sit"}`
- `mic_bridge_node` dispatches the command to `/webrtc_req` and publishes the canned
  feedback `"Sitting down."` to `/tts`
- Ambiguous or unclear speech yields `respond_conversationally` instead (no command
  fired) — the model only emits `execute_robot_command` when confident

### Tier 3 — Local offline, Jetson NX GPU

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

**Via docker-compose:**

```bash
# faster_whisper (default) — transcription only, voice_cmd_node handles NLU
ROBOT_IP=192.168.x.x ENABLE_STT=true docker-compose up

# OpenAI Realtime unified — wake word + command + spoken reply in one WS session
ROBOT_IP=192.168.x.x OPENAI_API_KEY=sk-... ENABLE_STT=true \
  STT_PROVIDER=openai_realtime docker-compose up

# Gemini Live unified — same but Gemini 3.1 Flash Live
ROBOT_IP=192.168.x.x GEMINI_API_KEY=... ENABLE_STT=true \
  STT_PROVIDER=gemini_live docker-compose up

# Jetson NX — Gemma unified (llama.cpp sidecar on GPU, no internet)
ROBOT_IP=192.168.x.x \
  docker-compose -f docker/docker-compose.yml -f docker/docker-compose.jetson.yml up
```

**Via launch file** (`enable_stt:=true` also starts `voice_cmd_node`):

```bash
ENABLE_STT=true STT_PROVIDER=faster_whisper STT_DEVICE=cuda \
  ros2 launch go2_robot_sdk robot.launch.py enable_stt:=true
```

### Troubleshooting

**`PortAudioError: Error querying device -1` on startup**

`stt_node` logs this if it cannot open the microphone. In Docker the container now starts a local PulseAudio null-source daemon as a fallback, so this error should not occur. If it does:

| Symptom | Cause | Fix |
|---|---|---|
| Native Linux, no mic plugged in | No audio input device | Plug in a USB/3.5 mm microphone |
| Docker on Windows, `pa_context_connect() failed: Access denied` | WSLg PA UID mismatch (root vs uid 1000) | Use browser mic bridge — open `http://localhost:8888` |
| Docker on Linux, `/dev/snd` missing | Container `devices:` block not matched | Ensure `privileged: true` and `/dev/snd:/dev/snd` in compose file |
| Jetson NX, device shows up but errors | Wrong ALSA device index | Set `STT_DEVICE_INDEX` env var to the correct index from `python3 -m sounddevice` |

To list available audio input devices inside the container:
```bash
python3 -c "import sounddevice as sd; print(sd.query_devices())"
# Docker (after entrypoint.sh runs): should show "NullMicrophone" at minimum
```

---

## 15. Mic Bridge (Browser → Container Microphone)

`mic_bridge_node` provides a browser-based microphone route that bypasses Docker audio entirely. It starts automatically with `ENABLE_STT=true` (the default in `docker-compose.yml`).

### Verify the node is running

```bash
ros2 node list | grep mic_bridge
# Expected: /mic_bridge_node
```

### Open the browser page

Open `http://localhost:8888` in your host browser (Chrome, Firefox, or Edge on Windows). Click **Start Microphone** and grant mic permission.

```bash
# In a second terminal — confirm audio is reaching the container:
ros2 topic echo /speech_text
# Speak into the browser tab → transcript should appear within ~1–2 s
```

### Run standalone (bare metal or testing)

```bash
ros2 run speech_processor mic_bridge_node \
  --ros-args -p stt_provider:=faster_whisper -p device:=cpu

# Different STT backend
ros2 run speech_processor mic_bridge_node \
  --ros-args -p stt_provider:=openai -p api_key:=$OPENAI_API_KEY

# Custom ports
ros2 run speech_processor mic_bridge_node \
  --ros-args -p http_port:=9000 -p ws_port:=9001
```

### Pipe transcriptions to TTS (echo-back test)

```bash
ros2 run topic_tools relay /speech_text /tts
# Speak in browser → robot (or speakers) repeat what you said
```

### How it works

The browser page uses the Web Audio API's `ScriptProcessorNode` to capture microphone audio at 16 kHz mono. Samples are converted from float32 to Int16 PCM and sent as binary WebSocket frames to port 8889. `mic_bridge_node` applies energy-threshold VAD: voiced frames accumulate until a silence gap, then the utterance is sent to the configured backend.

For `faster_whisper`: transcript is published to `/speech_text` and echoed to the browser.  
For unified providers (`gemma_local`, `openai_realtime`, `gemini_live`): the backend returns a structured result; `mic_bridge_node` dispatches the command and forwards the TTS response directly — no `/speech_text` is published.

Both `stt_node` and `mic_bridge_node` are supported. When system audio is unavailable (Docker on Windows), `mic_bridge_node` handles all input from the browser.

---

## 16. Voice Commands (Speech → Robot Action)

`voice_cmd_node` subscribes to `/speech_text` and routes recognised phrases to the robot.

> **Note**: `voice_cmd_node` is **automatically disabled** when `STT_PROVIDER` is `gemma_local`, `openai_realtime`, or `gemini_live`. Those providers handle NLU + command dispatch + TTS response internally inside `mic_bridge_node`. To verify, run `ros2 node list | grep voice_cmd` — it should return nothing for unified providers.

### Start the full voice pipeline (faster_whisper path)

**Bare metal (launch file):**
```bash
# Hardware — voice_cmd_node starts automatically alongside stt_node
ENABLE_STT=true STT_PROVIDER=faster_whisper \
  ros2 launch go2_robot_sdk robot.launch.py enable_stt:=true

# Simulation
ENABLE_STT=true STT_PROVIDER=faster_whisper \
  ros2 launch go2_robot_sdk simulation.launch.py enable_stt:=true
```

**Docker:**
```bash
# faster_whisper (default) — voice_cmd_node auto-starts
ROBOT_IP=192.168.x.x ENABLE_STT=true docker-compose up

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
| **Movement** (timed) | "go forward", "forward", "advance" | `/cmd_vel_voice` linear.x + — stops after `move_duration` s (default 2 s) |
| | "go back", "backward", "reverse" | `/cmd_vel_voice` linear.x − |
| | "turn left", "rotate left" | `/cmd_vel_voice` angular.z + |
| | "turn right", "rotate right" | `/cmd_vel_voice` angular.z − |
| | "stop moving", "stop walking" | `/cmd_vel_voice` zero |
| **Movement** (persistent) | "keep going forward", "keep advancing" | `/cmd_vel_voice` linear.x + — no timeout, runs until "stop moving" |
| | "keep going back", "keep reversing" | `/cmd_vel_voice` linear.x − |
| | "keep turning left", "keep going left" | `/cmd_vel_voice` angular.z + |
| | "keep turning right", "keep going right" | `/cmd_vel_voice` angular.z − |
| **Gestures** (hardware only) | "hello", "wave" | api_id 1016 |
| | "dance", "dance one" | api_id 1022 |
| | "wiggle", "wiggle hips" | api_id 1033 |
| | "handstand" | api_id 1301 |
| | "moonwalk" | api_id 1305 |
| **Patrol** | "patroli", "mulai patroli", "start patrol", "keliling" | `/patrol_enable true` |
| | "hentikan patroli", "stop patrol", "berhenti patroli" | `/patrol_enable false` |
| **Object approach** | "dekati bola", "approach ball" | `/approach_target "sports ball"` |
| | "dekati kursi", "approach chair" | `/approach_target "chair"` |
| | "dekati orang", "approach person" | `/approach_target "person"` |
| | "dekati meja", "approach table" | `/approach_target "dining table"` |
| | "dekati botol", "approach bottle" | `/approach_target "bottle"` |
| | "cari kucing", "go near cat" | `/approach_target "cat"` |
| **Navigation** | "go to lobby", "ke lobi" | `/navigate_to_room "lobby"` |
| | "go to the office", "ke kantor" | `/navigate_to_room "office"` |
| **Follow-me** | "ikuti saya", "follow me" | `/follow_enable true` |
| | "berhenti", "stop following" | cancels follow/approach/patrol |

**Timed vs persistent movement:** timed commands (`go forward`, `turn left`, …) publish at 10 Hz for `move_duration` seconds (default 2 s) then send a zero-velocity stop automatically. Persistent commands (`keep going forward`, `keep turning right`, …) publish at 10 Hz indefinitely — you must say "stop moving" (or "halt move", "stop walking") to halt the robot.

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

**Gemma local (natural language, offline):** Gemma 4 E4B via Ollama — no API key, no internet. Used automatically in the Windows GPU profile (`docker-compose.windows-gpu.yml`). Falls back to keyword matching on any Ollama error.

```bash
# Gemma local NLU (Ollama must be running)
ros2 run speech_processor voice_cmd_node \
  --ros-args -p cmd_topic:=/webrtc_req \
             -p nlu_provider:=gemma_local \
             -p ollama_host:=http://localhost:11434 \
             -p gemma_model:=gemma4:e4b
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
ros2 topic pub /speech_text std_msgs/msg/String "{data: 'keep going forward'}" --once
ros2 topic pub /speech_text std_msgs/msg/String "{data: 'stop moving'}" --once
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

# Tier 2 — local STT (faster-whisper) + keyword NLU, fully offline
ROBOT_IP=192.168.x.x \
  STT_PROVIDER=faster_whisper STT_DEVICE=cuda WHISPER_MODEL=base \
  NLU_PROVIDER=keyword docker-compose up

# Windows 11 — browser mic bridge (open http://localhost:8888 after starting)
ROBOT_IP=192.168.x.x OPENAI_API_KEY=sk-... STT_PROVIDER=openai \
  docker-compose up
```

---

## 17. Patrol (`ENABLE_PATROL=true`)

`patrol_node` cycles through all named waypoints in `WAYPOINTS_FILE` indefinitely using Nav2 `NavigateToPose` goals. Requires Nav2 running (`enable_nav2=true`) and a saved SLAM map with waypoints configured.

**Start with patrol enabled:**
```bash
# Hardware
ENABLE_PATROL=true ROBOT_IP=<IP> docker-compose up

# Bare metal (Nav2 + SLAM must be running)
ENABLE_PATROL=true ENABLE_STT=true \
  ros2 launch go2_robot_sdk robot.launch.py enable_patrol:=true
```

**Verify the node is running:**
```bash
ros2 node list | grep patrol_node
# Expected: /patrol_node
```

**Start patrol manually:**
```bash
ros2 topic pub /patrol_enable std_msgs/Bool "{data: true}" --once
```

**Monitor status:**
```bash
ros2 topic echo /patrol_status
# Expect a sequence such as:
#   patrolling:lobby/1/4    — heading to "lobby", waypoint 1 of 4
#   patrolling:hallway/2/4  — heading to "hallway"
#   patrolling:office/3/4
#   patrolling:reception/4/4
#   patrol_done             — one full round complete, immediately loops
#   patrolling:lobby/1/4    — starts again
```

**Stop patrol:**
```bash
ros2 topic pub /patrol_enable std_msgs/Bool "{data: false}" --once
# → /patrol_status publishes "patrol_cancelled"
```

**Visit a subset of waypoints:**
```bash
# Via env var (before launch)
PATROL_ROUTE=lobby,hallway ENABLE_PATROL=true \
  ros2 launch go2_robot_sdk robot.launch.py enable_patrol:=true

# At runtime — stop, then restart with only certain rooms
# (PATROL_ROUTE is a launch-time parameter; re-launch to change it)
```

**Hot-reload waypoints** (shared with `nav_waypoint_node`):
```bash
ros2 topic pub /reload_waypoints std_msgs/Empty "{}" --once
```

**Voice triggers:**
- "patroli" / "mulai patroli" / "start patrol" → `/patrol_enable true`
- "hentikan patroli" / "stop patrol" / "berhenti patroli" → `/patrol_enable false`

**Topics:**

| Topic | Type | Notes |
|---|---|---|
| `/patrol_enable` | `std_msgs/Bool` | True = start, False = stop |
| `/patrol_status` | `std_msgs/String` | `"patrolling:<key>/<idx>/<total>"` · `"patrol_done"` · `"patrol_cancelled"` · `"patrol_failed:<key>"` |

**Troubleshooting:**

| Symptom | Cause | Fix |
|---|---|---|
| Node starts but does nothing | No waypoints in `WAYPOINTS_FILE` | Edit `config/waypoints.yaml`; check `ros2 param get /patrol_node waypoints_file` |
| `Nav2 action server not available` | Nav2 not running or not yet active | Wait for Nav2 to finish initialising; check `ros2 lifecycle get /bt_navigator` |
| Patrol stops at one waypoint with `patrol_failed:<key>` | Nav2 cannot plan a path | Obstacle blocking or map not loaded; check local/global costmap topics |
| `PATROL_SKIP_ON_FAILURE=false` and patrol aborts | Expected — node stops on first unreachable waypoint | Set `PATROL_SKIP_ON_FAILURE=true` to advance past failures |

---

## 18. Object Approach (`ENABLE_APPROACH_OBJECT=true`)

`approach_object_node` performs a one-shot visual servo toward any YOLO-detected class. It stops automatically when the object fills a configurable fraction of the camera image. Requires YOLO running (`ENABLE_YOLO=true`).

**Start with object approach enabled:**
```bash
# Hardware + YOLO + approach (cam_bridge for Windows)
ENABLE_APPROACH_OBJECT=true ENABLE_YOLO=true CAM_BRIDGE=true \
  ROBOT_IP=<IP> docker-compose up

# Bare metal
ENABLE_APPROACH_OBJECT=true ENABLE_YOLO=true \
  ros2 launch go2_robot_sdk robot.launch.py enable_approach_object:=true
```

**Verify the node is running:**
```bash
ros2 node list | grep approach_object
# Expected: /approach_object_node
```

**Set a target object (manual test — no STT required):**
```bash
# Approach a sports ball visible to the camera
ros2 topic pub /approach_target std_msgs/String "{data: 'sports ball'}" --once

# Other COCO classes
ros2 topic pub /approach_target std_msgs/String "{data: 'chair'}" --once
ros2 topic pub /approach_target std_msgs/String "{data: 'person'}" --once
ros2 topic pub /approach_target std_msgs/String "{data: 'bottle'}" --once
```

**Monitor approach status:**
```bash
ros2 topic echo /approach_status
# Expect:
#   approaching:sports ball  — moving toward the ball
#   reached:sports ball      — stopped; ball fills target_area (default 12%) of image
#
# If the ball disappears:
#   lost:sports ball         — not seen for 2 s (default); approach aborted
```

**Cancel an active approach:**
```bash
ros2 topic pub /approach_target std_msgs/String "{data: ''}" --once
# → /approach_status publishes "cancelled"
```

**Watch velocity output:**
```bash
ros2 topic echo /cmd_vel_follow
# Should show non-zero linear.x (forward) and angular.z (centering)
# Zeroes out on reach/lost/cancel
```

**Monitor behavior coordinator state (optional):**
```bash
ros2 topic echo /behavior_mode
# IDLE → APPROACHING (when target set) → IDLE (when reached/lost/cancelled)
```

**Voice triggers (`keyword` NLU):**
```
"dekati bola"     → approach sports ball
"dekati kursi"    → approach chair
"dekati orang"    → approach person
"dekati meja"     → approach dining table
"dekati botol"    → approach bottle
"dekati kucing"   → approach cat
"approach the ball"   → approach sports ball
"go near the chair"   → approach chair
```

**Inject via speech text topic (no microphone):**
```bash
ros2 topic pub /speech_text std_msgs/String "{data: 'dekati bola'}" --once
```

**Tuning parameters:**

| Env var | Default | Effect |
|---|---|---|
| `APPROACH_LINEAR_SPEED` | `0.25` | m/s forward speed |
| `APPROACH_ANGULAR_KP` | `1.0` | Proportional gain (higher = faster centering) |
| `APPROACH_MAX_ANGULAR` | `0.8` | rad/s angular ceiling |
| `APPROACH_TARGET_AREA` | `0.12` | 12% of image → "arrived" (increase to stop further away) |
| `APPROACH_LOST_TIMEOUT` | `2.0` | Seconds without detection before giving up |

**Troubleshooting:**

| Symptom | Cause | Fix |
|---|---|---|
| `/approach_status` never publishes | Node not started | Check `ros2 node list` and `ENABLE_APPROACH_OBJECT=true` |
| Always `lost:<class>` immediately | YOLO not detecting the class | Check `ros2 topic echo /detected_objects`; verify camera is publishing and threshold is reasonable |
| Robot circles but never reaches | `APPROACH_TARGET_AREA` too high | Lower threshold (e.g. `0.08`) or move camera closer to scene |
| "lost" after 2 s even when object is visible | Wrong YOLO class name | Class names are from COCO model (lowercase): `sports ball`, not `ball` |

---

## 19. Custom Voice Commands (`CUSTOM_COMMANDS_FILE`)

`config/custom_commands.yaml` lets operators add new voice triggers without editing source code. Commands hot-reload via `/reload_custom_commands`.

**Default file location:** `<ros2_ws>/install/speech_processor/share/speech_processor/config/custom_commands.yaml`

**Override with your own file:**
```bash
CUSTOM_COMMANDS_FILE=/path/to/my_commands.yaml docker-compose up
```

**Example: add a "welcome position" command**

Edit `custom_commands.yaml`:
```yaml
custom_commands:
  welcome_position:
    trigger_en: "welcome position, go to welcome, stand at entrance"
    trigger_id: "posisi sambut, posisi selamat datang, ambil posisi sambut"
    action_type: api_id
    api_id: 1004          # BalanceStand / stand up
    feedback_en: "Taking welcome position"
    feedback_id: "Mengambil posisi sambut"
```

Reload without restarting:
```bash
ros2 topic pub /reload_custom_commands std_msgs/Empty "{}" --once
# Look for: [voice_cmd_node]: Loaded N custom commands
```

Test without STT:
```bash
ros2 topic pub /speech_text std_msgs/String "{data: 'welcome position'}" --once
# → robot stands; /tts publishes "Taking welcome position"
```

**Navigate to a room:**
```yaml
custom_commands:
  guide_lobby:
    trigger_en: "guide to lobby, take me to lobby, lobby please"
    trigger_id: "pandu ke lobi, ke lobi, antar ke lobi"
    action_type: navigate_to_room
    room: lobby            # must match a key in waypoints.yaml
    feedback_en: "Guiding to lobby"
    feedback_id: "Menuju lobi"
```

**Approach an object:**
```yaml
custom_commands:
  find_ball:
    trigger_en: "find the ball, get the ball, go to ball"
    trigger_id: "cari bola, temukan bola, ke bola"
    action_type: approach_object
    class_name: sports ball   # YOLO COCO class name
    feedback_en: "Approaching ball"
    feedback_id: "Mendekati bola"
```

**Supported `action_type` values:**

| Value | Effect | Extra fields required |
|---|---|---|
| `api_id` | Send a robot posture / gesture command | `api_id` (int), optionally `parameter` (str) |
| `navigate_to_room` | Publish room name to `/navigate_to_room` | `room` |
| `patrol_start` | Start patrol | — |
| `patrol_stop` | Stop patrol | — |
| `follow_start` | Enable follow-me | — |
| `follow_stop` | Disable follow-me | — |
| `approach_object` | Approach a YOLO class | `class_name` |

**Priority:** custom commands are matched first, before any built-in regex table, so they override built-in phrases if there is a phrase collision.

**Reload on change:**
```bash
ros2 topic pub /reload_custom_commands std_msgs/Empty "{}" --once
```

---

## 20. Session Recording (rosbag2)

Capture a timestamped, replayable session for debugging (hardware mode). Recordings persist to `./bags` on the host via the compose volume.

```bash
# Curated lightweight topic set (state, cmd_vel*, tf, scan, map, plan, detections, voice, diagnostics)
ROBOT_IP=192.168.x.x ENABLE_BAG=true docker-compose up

# Everything, including camera + point cloud (large files)
ROBOT_IP=192.168.x.x ENABLE_BAG=true BAG_TOPICS=-a docker-compose up

# Bare metal
ros2 launch go2_robot_sdk robot.launch.py bag_record:=true
```

Verify and replay:

```bash
ls -t bags/                        # newest session_<timestamp> directory
ros2 bag info bags/session_<timestamp>   # topics + message counts (after stopping)
ros2 bag play bags/session_<timestamp>
```

Open the bag directly in Foxglove Studio for visual inspection. Storage follows the rosbag2 default (sqlite3 on Humble); set `BAG_STORAGE=mcap` to use the newer plugin instead.

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
| Gemma vision | ✓ (`ENABLE_GEMMA_VISION=true`) | ✓ (remap `camera_topic`) | Windows GPU profile only; see section 11 |
| Robot commands | ✓ `/webrtc_req` | ✓ `/sim_cmd` | Same message type (`WebRtcReq`), same `api_id`s — only topic name differs |
| TTS | ✓ robot speaker | ✓ computer speaker | Add `-p local_playback:=true` for sim |
| STT | ✓ `/speech_text` | ✓ `/speech_text` | Start `stt_node` separately; mic must be on host PC or Jetson |
| Voice commands | ✓ → `/webrtc_req` | ✓ → `/sim_cmd` | Same phrases; hardware-only gestures skipped in sim |
| Patrol | ✓ (`ENABLE_PATROL=true`) | ✓ (Nav2 required) | Same `patrol_node`; needs a saved map with waypoints |
| Object approach | ✓ (`ENABLE_APPROACH_OBJECT=true`) | ✓ (YOLO + cam) | Same `approach_object_node`; remap camera topic in sim |
| Custom commands | ✓ | ✓ | `custom_commands.yaml` works identically in both modes |
| Foxglove | ✓ | ✓ (disabled by default) | Pass `foxglove:=true` |
