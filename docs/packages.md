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
| `sim_cmd_node.py` | Root-level command interface — subscribes to `/sim_cmd` (`std_msgs/String`) and routes to the gait controller. Mirrors the `/webrtc_req` pattern from hardware mode. |
| `RobotController/` | Trot, crawl, stand, rest gait state machines + PID controller. |
| `InverseKinematics/robot_IK.py` | Leg IK used by gait controllers. |
| `ForwardKinematics/robot_FK.py` | Leg FK used by odometry node. |

**`sim_cmd_node` commands:**

| Command string | Effect |
|---|---|
| `TROT` | Switch to trot gait (default at startup) |
| `CRAWL` | Switch to crawl gait (slow, stable) |
| `STAND` | Stand in place |
| `REST` | Lower to rest position |
| `sit` | Sit down (via behavior service) |
| `up` | Rise from sit (via behavior service) |
| `walk` | Resume walking after sit (via behavior service) |

```bash
ros2 topic pub /sim_cmd std_msgs/msg/String "{data: 'TROT'}" --once
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

TTS node — subscribes to text requests, publishes audio output. Supports ElevenLabs (requires `ELEVENLABS_API_KEY`), Google, and OpenAI backends.
