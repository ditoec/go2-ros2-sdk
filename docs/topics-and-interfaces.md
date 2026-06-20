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
| `/camera/image_raw` | `sensor_msgs/Image` | BEST_EFFORT depth 1 | ~30 Hz | BGR8; hardware mode only |
| `/camera/camera_info` | `sensor_msgs/CameraInfo` | BEST_EFFORT depth 1 | ~30 Hz | Hardware mode only |
| `/utlidar/voxel_map_compressed` | `go2_interfaces/VoxelMapCompressed` | BEST_EFFORT depth 1 | ~7 Hz | Only when `publish_raw_voxel:=true` |
| `/detected_objects` | `vision_msgs/Detection2DArray` | depth 10 | on demand | Published by `yolo_detector_node` (default detector) |
| `/annotated_image` | `sensor_msgs/Image` | depth 10 | on demand | Published by `yolo_detector_node` |

## Speech & Vision Topics (opt-in)

Published only when the relevant node is enabled (`ENABLE_STT`, `ENABLE_VOICE_CMD`, `ENABLE_GEMMA_VISION`). See [packages.md](packages.md#speech_processor-ament_python) for the providers and the Path A/B/C pipeline shapes.

| Topic | Type | Direction | Notes |
|---|---|---|---|
| `/robot_audio` | `std_msgs/UInt8MultiArray` | published by driver, consumed by `stt_node` | GO2 onboard mic captured from the WebRTC audio track (mono s16 @ 16 kHz). Only when `STT_SOURCE=robot` (needs `CONN_TYPE=webrtc` + `MIC_BRIDGE=false`) |
| `/speech_text` | `std_msgs/String` | published | Transcript from `stt_node`/`mic_bridge_node` (pure-STT providers only) |
| `/tts` | `std_msgs/String` | consumed by `tts_node` | Text to synthesize |
| `/tts_audio` | `std_msgs/UInt8MultiArray` | published | MP3 bytes → `mic_bridge_node` → browser speaker |
| `/cmd_vel_voice` | `geometry_msgs/Twist` | published | Voice movement → twist_mux priority 7 |
| `/sim_cmd` | `go2_interfaces/WebRtcReq` | consumed (sim) | Voice/command routing in simulation (mirrors `/webrtc_req`) |
| `/scene_description` | `std_msgs/String` | published | `gemma_vision_node` natural-language scene text |
| `/gemma_annotated_image` | `sensor_msgs/Image` | published | `gemma_vision_node` frame with description overlay |

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
Joystick  → joy_node → teleop_twist_joy → /cmd_vel_joy      (priority 10) ─┐
Foxglove  → Publish panel              → /cmd_vel_foxglove  (priority  8) ─┤
Voice     → voice_cmd / mic_bridge     → /cmd_vel_voice     (priority  7) ─┤
Nav2      → velocity_smoother          → /cmd_vel           (priority  5) ─┘
                                                  ↓
                                            twist_mux
                                                  ↓ /cmd_vel_out
                                           Go2DriverNode  (hardware)
                                           relay_cmd_vel  (simulation → /go2/cmd_vel)
                                                  ↓
                                            robot hardware
```

`twist_mux.yaml` controls the priority levels. Higher-numbered priority wins; joystick (10) overrides Foxglove (8), voice (7), and Nav2 (5). `twist_mux` outputs on `/cmd_vel_out`.

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
