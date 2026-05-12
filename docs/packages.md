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

TTS node — subscribes to text requests, publishes audio output. Supports ElevenLabs (requires `ELEVENLABS_API_KEY`), Google, and OpenAI backends.
