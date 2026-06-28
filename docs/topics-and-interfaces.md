# Topics and Interfaces

## Published Topics (hardware mode, single robot)

| Topic | Type | QoS | Rate | Notes |
|---|---|---|---|---|
| `/joint_states` | `sensor_msgs/JointState` | RELIABLE depth 10 | 1 Hz | Firmware v1.1.7 limit |
| `/go2_states` | `go2_interfaces/Go2State` | RELIABLE depth 10 | ~10 Hz | |
| `/imu` | `go2_interfaces/IMU` | RELIABLE depth 10 | ~50 Hz | Fields: quaternion, accelerometer, gyroscope, rpy, temperature |
| `/odom` | `nav_msgs/Odometry` | RELIABLE depth 10 | ~10 Hz | Also broadcasts `odom→base_link` TF |
| `/point_cloud2` | `sensor_msgs/PointCloud2` | BEST_EFFORT depth 1 | ~7 Hz | XYZ float32 |
| `/scan` | `sensor_msgs/LaserScan` | — | ~7 Hz | Derived from `/point_cloud2` by `pointcloud_to_laserscan_node` |
| `/camera/image_raw` | `sensor_msgs/Image` | BEST_EFFORT depth 1 | ~30 Hz | BGR8. Source depends on mode: hardware WebRTC driver (robot camera); `cam_bridge_node` (browser webcam, `CAM_BRIDGE=true`, Windows); not published in bare simulation (sim uses `/go2_camera/color/image_raw`) |
| `/camera/camera_info` | `sensor_msgs/CameraInfo` | BEST_EFFORT depth 1 | ~30 Hz | Published by hardware driver (calibrated) or `cam_bridge_node` (identity calibration, adequate for detection/recognition) |
| `/utlidar/voxel_map_compressed` | `go2_interfaces/VoxelMapCompressed` | BEST_EFFORT depth 1 | ~7 Hz | Only when `publish_raw_voxel:=true` |
| `/detected_objects` | `vision_msgs/Detection2DArray` | depth 10 | on demand | Published by `yolo_detector_node` (default detector) |
| `/annotated_image` | `sensor_msgs/Image` | depth 10 | on demand | Published by `yolo_detector_node` |

## Speech & Vision Topics (opt-in)

Published only when the relevant node is enabled (`ENABLE_STT`, `ENABLE_VOICE_CMD`, `ENABLE_GEMMA_VISION`, `ENABLE_FACE`, `CAM_BRIDGE`). See [packages.md](packages.md#speech_processor-ament_python) for the providers and the Path A/B/C pipeline shapes.

### Voice / STT

| Topic | Type | Direction | Notes |
|---|---|---|---|
| `/robot_audio` | `std_msgs/UInt8MultiArray` | published by driver, consumed by `stt_node` | GO2 onboard mic captured from the WebRTC audio track (mono s16 @ 16 kHz). Only when `STT_SOURCE=robot` (needs `CONN_TYPE=webrtc` + `MIC_BRIDGE=false`) |
| `/speech_text` | `std_msgs/String` | published | Transcript from `stt_node`/`mic_bridge_node` (pure-STT providers only) |
| `/tts` | `std_msgs/String` | consumed by `tts_node` | Text to synthesize |
| `/tts_audio` | `std_msgs/UInt8MultiArray` | published | MP3 bytes → `mic_bridge_node` → browser speaker |
| `/cmd_vel_voice` | `geometry_msgs/Twist` | published | Voice movement → twist_mux priority 7 |
| `/sim_cmd` | `go2_interfaces/WebRtcReq` | consumed (sim) | Voice/command routing in simulation (mirrors `/webrtc_req`) |

### Vision — Scene Description (`ENABLE_GEMMA_VISION=true`)

| Topic | Type | Direction | Notes |
|---|---|---|---|
| `/scene_description` | `std_msgs/String` | published | `gemma_vision_node` natural-language scene text (~0.5 Hz) |
| `/gemma_annotated_image` | `sensor_msgs/Image` | published | `gemma_vision_node` camera frame with description overlay |

### Vision — Face Recognition (`ENABLE_FACE=true`)

| Topic | Type | Direction | Notes |
|---|---|---|---|
| `/recognized_faces` | `vision_msgs/Detection2DArray` | published by `face_recognition_node` | One detection per face; `class_id` = person name, `score` = cosine similarity (0–1), `bbox` = face bounding box. Excludes "Unknown" faces. |
| `/recognized_face_names` | `std_msgs/String` | published by `face_recognition_node` | Comma-joined list of names currently in frame (empty string if none). Consumed by `voice_cmd_node` for conversational greetings (Modul 4.4). |
| `/face_annotated_image` | `sensor_msgs/Image` | published by `face_recognition_node` | Camera frame with bounding boxes and name labels overlaid. |
| `/reload_faces` | `std_msgs/Empty` | consumed by `face_recognition_node` | Triggers a live re-scan of `face_db/` and re-embedding of all photos — no restart needed. Auto-published by `face_enrollment_node` after a new enroll. |
| `/face_threshold` | `std_msgs/Float32` | published by `face_enrollment_node`, consumed by `face_recognition_node` | Live cosine-similarity match floor (0–1, default 0.35). Published by the threshold slider in the enrollment UI at `http://localhost:8890`. |

### Behavior Modes (`ENABLE_BEHAVIOR_COORDINATOR=true`)

Published by `behavior_coordinator_node` with TRANSIENT_LOCAL QoS so late subscribers see the current state immediately.

| Topic | Type | Direction | Values |
|---|---|---|---|
| `/behavior_mode` | `std_msgs/String` | published | `IDLE` · `VOICE_MOVE` · `FOLLOWING` · `NAVIGATING` · `APPROACHING` · `PATROL` |

### Patrol (`ENABLE_PATROL=true`)

`patrol_node` cycles through named waypoints defined in `WAYPOINTS_FILE` indefinitely until stopped.

| Topic | Type | Direction | Notes |
|---|---|---|---|
| `/patrol_enable` | `std_msgs/Bool` | consumed | `true` = start patrol from first waypoint; `false` = cancel |
| `/patrol_status` | `std_msgs/String` | published | `"patrolling:<key>/<idx>/<total>"` · `"patrol_done"` (one round complete, looping) · `"patrol_cancelled"` · `"patrol_failed:<key>"` |

`/reload_waypoints` (`std_msgs/Empty`) is shared with `nav_waypoint_node` — one topic reloads the YAML file for both nodes without restarting either.

### Object Approach (`ENABLE_APPROACH_OBJECT=true`)

`approach_object_node` performs a one-shot visual servo toward any YOLO-detected class. It publishes velocity on `/cmd_vel_follow` (priority 6), the same channel as `follow_me_node`. `CommandDispatcher` enforces mutual exclusion — both nodes never publish simultaneously.

| Topic | Type | Direction | Notes |
|---|---|---|---|
| `/approach_target` | `std_msgs/String` | consumed | YOLO class name to approach (e.g. `"sports ball"`, `"chair"`); empty string cancels |
| `/approach_status` | `std_msgs/String` | published | `"approaching:<class>"` · `"reached:<class>"` (stopped; object filled `target_area` fraction) · `"lost:<class>"` (not seen for `lost_timeout` s) · `"cancelled"` |
| `/cmd_vel_follow` | `geometry_msgs/Twist` | published | Shared with `follow_me_node` (twist_mux priority 6). Not published when no approach is active. |

### Custom Voice Commands (`CUSTOM_COMMANDS_FILE`)

Operator-defined triggers are loaded from `speech_processor/config/custom_commands.yaml` (or `CUSTOM_COMMANDS_FILE` override) at startup and hot-reloaded on demand.

| Topic | Type | Direction | Notes |
|---|---|---|---|
| `/reload_custom_commands` | `std_msgs/Empty` | consumed by `voice_cmd_node` | Re-reads YAML from disk; no restart needed |

### Vision — Camera Bridge (`CAM_BRIDGE=true`, Windows)

`cam_bridge_node` is the Windows substitute for the robot's hardware camera. It serves a browser page that captures the host webcam via `getUserMedia` and streams JPEG frames over WebSocket into the container. `face_recognition_node` and `yolo_detector_node` subscribe to `/camera/image_raw` unchanged — no remapping needed.

| Topic | Type | Direction | Notes |
|---|---|---|---|
| `/camera/image_raw` | `sensor_msgs/Image` | published by `cam_bridge_node` | BGR8, rate set by browser FPS slider (1–30 FPS, default 10). Same topic as the hardware driver — downstream nodes need no reconfiguration. |
| `/camera/camera_info` | `sensor_msgs/CameraInfo` | published by `cam_bridge_node` | Identity calibration (no distortion; focal length estimated from typical 70° webcam FOV). Suitable for detection and recognition; not accurate enough for 3-D reconstruction. Rebuilt automatically on resolution change. |

## Published Topics (simulation mode)

Sensor topics appear **~15–30 s after launch** — Gazebo sensor bridges are lazy and only create the ROS topic when the first message arrives.

| Topic | Type | Rate | Source |
|---|---|---|---|
| `/imu` | `sensor_msgs/Imu` | 100 Hz | Gazebo IMU sensor → `ros_gz_bridge` → `relay_imu`. Fields: orientation, angular_velocity, linear_acceleration |
| `/scan` | `sensor_msgs/LaserScan` | 10 Hz | Gazebo LiDAR sensor → `ros_gz_bridge` → `relay_scan` |
| `/go2_camera/color/image_raw` | `sensor_msgs/Image` | 10 Hz | Gazebo camera → `ros_gz_bridge` → `relay_camera` |
| `/go2_camera/color/camera_info` | `sensor_msgs/CameraInfo` | 10 Hz | Gazebo camera → `ros_gz_bridge` → `relay_camera_info` |
| `/joint_states` | `sensor_msgs/JointState` | ~50 Hz | `joint_state_broadcaster` → `relay_joint_states` |
| `/odom` | `nav_msgs/Odometry` | 50 Hz | `QuadrupedOdometryNode` |
| `/clock` | `rosgraph_msgs/Clock` | — | Gazebo |

Intermediate bridge topics (`/go2/imu_plugin/out`, `/go2/scan`, `/go2/color/image_raw`, `/go2/color/camera_info`) are also available for diagnostics.

## Subscribed Topics

| Topic | Type | Consumer | Notes |
|---|---|---|---|
| `/cmd_vel_out` | `geometry_msgs/Twist` | `Go2DriverNode` | Actual movement commands after mux |
| `/webrtc_req` | `go2_interfaces/WebRtcReq` | `Go2DriverNode` | Arbitrary robot API commands |
| `/joy` | `sensor_msgs/Joy` | `Go2DriverNode` | Stand up (button 0) / stand down (button 1) |

### CycloneDDS mode (`CONN_TYPE=cyclonedds`)

When connected over Ethernet, the driver subscribes to the robot's native DDS topics instead of opening a WebRTC connection (republished to the same SDK topics as WebRTC mode):

| DDS topic | Type | Rate | Republished to |
|---|---|---|---|
| `sportmodestate` | `go2_interfaces/SportModeState` | ~50 Hz | `/go2_states`, `/imu` |
| `lowstate` | `go2_interfaces/LowState` | ~500 Hz (best-effort) | `/joint_states`, `/imu` |
| `/utlidar/robot_pose` | `geometry_msgs/PoseStamped` | — | `/odom` + TF |
| `/utlidar/cloud` | `sensor_msgs/PointCloud2` | — (best-effort) | `/point_cloud2` |
| `wirelesscontroller` | `go2_interfaces/WirelessController` | — | (debug log) |

Commands are routed back via `CycloneDDSAdapter` → `/api/sport/request`.

## Velocity Command Pipeline

```
Joystick       → joy_node → teleop_twist_joy → /cmd_vel_joy      (priority 10) ─┐
Foxglove       → Publish panel              → /cmd_vel_foxglove  (priority  8) ─┤
Voice          → voice_cmd / mic_bridge     → /cmd_vel_voice     (priority  7) ─┤
Follow / Appr. → follow_me / approach_obj   → /cmd_vel_follow    (priority  6) ─┤
Nav2           → velocity_smoother          → /cmd_vel           (priority  5) ─┘
                                                      ↓
                                                twist_mux
                                                      ↓ /cmd_vel_out
                                               Go2DriverNode  (hardware)
                                               relay_cmd_vel  (simulation → /go2/cmd_vel)
                                                      ↓
                                               robot hardware
```

`twist_mux.yaml` controls the priority levels. Higher-numbered priority wins; joystick (10) overrides Foxglove (8), voice (7), follow/approach (6), and Nav2 (5). `/cmd_vel_follow` is shared by `follow_me_node` and `approach_object_node` — `CommandDispatcher` ensures only one publishes at a time. `twist_mux` outputs on `/cmd_vel_out`.

## Multi-Robot Topic Namespacing

When `ROBOT_IP` contains more than one IP (`conn_mode = "multi"`), all topics get a `robot{N}/` prefix:

```
/robot0/joint_states     /robot1/joint_states
/robot0/odom             /robot1/odom
/robot0/point_cloud2     /robot1/point_cloud2
/robot0/camera/image_raw /robot1/camera/image_raw
…
```

Incoming control topics are also namespaced:
```
/robot0/cmd_vel_out      /robot1/cmd_vel_out
/robot0/webrtc_req       /robot1/webrtc_req
```

## WebRtcReq Message Fields

```
go2_interfaces/msg/WebRtcReq
  int32   api_id       # command ID from ROBOT_CMD dict
  string  parameter    # JSON string payload (optional)
  string  topic        # WebRTC topic string from RTC_TOPIC dict
  int32   priority     # 0 or 1
```

## TF Frame Tree

```
odom
 └── base_link
      ├── imu_link
      ├── lidar_link
      └── camera_link
           └── camera_optical
```

In multi mode, frames become `robot0/base_link`, `robot0/imu_link`, etc.

The `odom→base_link` transform is broadcast by `ROS2Publisher.publish_odometry()` on every odometry message. Static sensor transforms are published by `robot_state_publisher` from the URDF.
