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

**Hardware** — publish to `/webrtc_req`:
```bash
# Wave hello
ros2 topic pub /webrtc_req go2_interfaces/msg/WebRtcReq \
  "{api_id: 1016, topic: 'rt/api/sport/request'}" --once

# Sit
ros2 topic pub /webrtc_req go2_interfaces/msg/WebRtcReq \
  "{api_id: 1009, topic: 'rt/api/sport/request'}" --once

# Stand up
ros2 topic pub /webrtc_req go2_interfaces/msg/WebRtcReq \
  "{api_id: 1004, topic: 'rt/api/sport/request'}" --once
```

**Simulation** — publish to `/sim_cmd` (mirrors the `/webrtc_req` pattern):
```bash
# Gait modes
ros2 topic pub /sim_cmd std_msgs/msg/String "{data: 'TROT'}"  --once
ros2 topic pub /sim_cmd std_msgs/msg/String "{data: 'REST'}"  --once
ros2 topic pub /sim_cmd std_msgs/msg/String "{data: 'CRAWL'}" --once
ros2 topic pub /sim_cmd std_msgs/msg/String "{data: 'STAND'}" --once

# Behavior commands
ros2 topic pub /sim_cmd std_msgs/msg/String "{data: 'sit'}"  --once
ros2 topic pub /sim_cmd std_msgs/msg/String "{data: 'up'}"   --once
ros2 topic pub /sim_cmd std_msgs/msg/String "{data: 'walk'}" --once
```

`sim_cmd_node` (started automatically by `go2_sim.launch.py`) routes gait modes to the gait controller via `quadropted_msgs/RobotModeCommand` and behavior commands via the `RobotBehaviorCommand` service. Unknown commands are logged as warnings.

**Behavior command notes:**
- `sit` → STAND controller, body lowered (-0.15 m). Robot visibly crouches.
- `up` → REST controller, body at normal height. Robot stands still.
- `walk` → resets to TROT gait mode (legs begin cycling). The gait controller has `autoRest` enabled: if velocity remains zero the leg cycling stops after the first phase completes. Send velocity commands immediately after `walk` to move the robot:
  ```bash
  ros2 topic pub /sim_cmd std_msgs/msg/String "{data: 'walk'}" --once
  ros2 topic pub /cmd_vel_joy geometry_msgs/msg/Twist "{linear: {x: 0.2}}" --rate 10
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

**Hardware** — audio is sent to the robot's speaker:
```bash
source install/setup.bash
ros2 run speech_processor tts_node \
  --ros-args -p api_key:=$ELEVENLABS_API_KEY

# Send a text string
ros2 topic pub /tts std_msgs/msg/String "{data: 'Hello from GO2'}" --once
```

**Simulation** — play through the computer's speaker with `local_playback:=true`:
```bash
ros2 run speech_processor tts_node \
  --ros-args -p api_key:=$ELEVENLABS_API_KEY \
             -p local_playback:=true

ros2 topic pub /tts std_msgs/msg/String "{data: 'Hello from simulation'}" --once
```

`local_playback` uses `pydub` to play directly through the system's default audio device — no robot connection needed. `ELEVENLABS_API_KEY` is still required for speech synthesis. Audio is cached in `tts_cache/` after the first synthesis call.

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
| Robot commands | ✓ `/webrtc_req` | ✓ `/sim_cmd` | Different topic/format; same capability |
| TTS | ✓ robot speaker | ✓ computer speaker | Add `-p local_playback:=true` for sim |
| Foxglove | ✓ | ✓ (disabled by default) | Pass `foxglove:=true` |
