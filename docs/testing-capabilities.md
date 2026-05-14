# Testing SDK Capabilities

This guide covers how to verify each SDK feature works after launching, in both hardware and simulation modes. Run these commands in a second terminal after the main launch.

## Quick Health Check — Topics After Launch

After either launch, the following topics should be active within ~10 s:

```bash
# List all active topics
ros2 topic list

# Confirm data is flowing at expected rates
ros2 topic hz /imu             # expect ~50 Hz
ros2 topic hz /odom            # expect ~10 Hz
ros2 topic hz /point_cloud2    # expect ~7 Hz
ros2 topic hz /scan            # expect ~7 Hz
ros2 topic hz /joint_states    # expect ~1 Hz (firmware limit on hardware)
```

**Hardware-only topics:**
```bash
ros2 topic hz /camera/image_raw    # expect ~30 Hz
```

**Simulation-only topics:**
```bash
ros2 topic hz /go2_camera/color/image_raw   # expect ~30 Hz
ros2 topic hz /clock                        # Gazebo sim clock
```

---

## 1. IMU

```bash
ros2 topic echo /imu --once
```

Expected: `quaternion`, `accelerometer`, `gyroscope`, `rpy` fields populated. On hardware, `temperature` should read a plausible value (~30–60 °C).

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

```bash
ros2 topic echo /point_cloud2 --once
```

Expected: `height`, `width`, `fields` (x, y, z float32), non-zero `data`.

```bash
# Check scan (derived from point cloud)
ros2 topic echo /scan --once
```

In RViz: `PointCloud2` display should show a 3-D ring of points around the robot. `LaserScan` should show a 2-D ring in the horizontal plane.

**Hardware only — confirm LiDAR decoder is running:**
```bash
ros2 node list | grep lidar
# expect: /lidar_to_pointcloud  /go2_pointcloud_to_laserscan
```

---

## 4. Camera

**Hardware:**
```bash
ros2 topic echo /camera/image_raw --once
# or view the stream:
ros2 run image_tools showimage --ros-args -r /image:=/camera/image_raw
```

**Simulation:**
```bash
ros2 run image_tools showimage --ros-args -r /image:=/go2_camera/color/image_raw
```

Expected: live image window appears within a few seconds.

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
/joy → teleop_twist_joy → /cmd_vel_joy → twist_mux → /cmd_vel_muxed → driver → robot
```

Verify the muxed output:
```bash
ros2 topic echo /cmd_vel_muxed
```

**Special joystick buttons (direct to driver):**
- Button 0: Stand up
- Button 1: Stand down

**Without a physical joystick** — publish a velocity command manually:
```bash
# Move forward for a few seconds
ros2 topic pub /cmd_vel_muxed geometry_msgs/msg/Twist \
  "{linear: {x: 0.2}, angular: {z: 0.0}}" --rate 10
# Stop
ros2 topic pub /cmd_vel_muxed geometry_msgs/msg/Twist "{}" --once
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
ros2 topic echo /cmd_vel                # Nav2 velocity output
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
| IMU | ✓ `/imu` | ✓ `/imu` | Same topic |
| Odometry | ✓ `/odom` | ✓ `/odom` | Same topic |
| LiDAR | ✓ `/point_cloud2` | ✓ `/scan` (direct) | Sim skips point cloud; LiDAR bridge publishes LaserScan |
| Camera | ✓ `/camera/image_raw` | ✓ `/go2_camera/color/image_raw` | Different topic — remap yolo_detector |
| Joint states | ✓ `/joint_states` (~1 Hz) | ✓ `/joint_states` (higher rate) | Same topic |
| Joystick/teleop | ✓ | ✓ | Identical |
| SLAM | ✓ | ✓ | Identical |
| Nav2 | ✓ | ✓ | Sim uses `nav2_params_sim.yaml` |
| YOLO detection | ✓ | ✓ (remap needed) | See section 10 |
| Robot commands | ✓ `/webrtc_req` | ✓ `/sim_cmd` | Different topic/format; same capability |
| TTS | ✓ robot speaker | ✓ computer speaker | Add `-p local_playback:=true` for sim |
| Foxglove | ✓ | ✓ (disabled by default) | Pass `foxglove:=true` |
