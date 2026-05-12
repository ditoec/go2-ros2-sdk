# Architecture

## Clean Architecture Layers

The `go2_robot_sdk` package is organized into four strict layers. Dependencies only flow inward — outer layers depend on inner ones, never the reverse.

```
presentation/   Go2DriverNode         — ROS2 node, wires all layers together
application/    RobotDataService       — processes incoming WebRTC messages
                RobotControlService    — translates ROS2 commands to robot actions
infrastructure/ WebRTCAdapter          — manages Go2Connection(s), sends data to application
                ROS2Publisher          — converts domain entities to ROS2 messages
                LidarDecoder           — decodes compressed voxel frames
domain/         RobotConfig, RobotData — pure Python dataclasses, no external deps
                RTC_TOPIC, ROBOT_CMD   — all topic strings and command IDs
                IRobotDataPublisher    — interface implemented by ROS2Publisher
                IRobotController       — interface implemented by WebRTCAdapter
```

**Critical rule**: `domain/` must never import `rclpy` or any ROS2 type. Business logic in `application/` is testable without ROS2.

## Inbound Data Flow (robot → ROS2)

```
Robot hardware
  │  WebRTC data channel (binary/JSON frames)
  ▼
Go2Connection          infrastructure/webrtc/go2_connection.py
  │  decodes binary frames, calls on_message callback
  ▼
WebRTCAdapter          infrastructure/webrtc/webrtc_adapter.py
  │  _on_data_channel_message → RobotDataService.process_webrtc_message()
  ▼
RobotDataService       application/services/robot_data_service.py
  │  matches msg["topic"] against RTC_TOPIC constants
  │  builds typed RobotData entity (OdometryData, IMUData, LidarData, …)
  │  calls IRobotDataPublisher method
  ▼
ROS2Publisher          infrastructure/ros2/ros2_publisher.py
  │  maps entity fields → ROS2 message types, stamps headers, broadcasts TF
  ▼
ROS2 topics            /odom, /imu, /joint_states, /point_cloud2, …
```

## Outbound Data Flow (ROS2 → robot)

```
/cmd_vel_out  (Twist)          → Go2DriverNode._on_cmd_vel()
/webrtc_req   (WebRtcReq)      → Go2DriverNode._on_webrtc_req()
/joy          (Joy)            → Go2DriverNode._on_joy()
  │
  ▼
RobotControlService    application/services/robot_control_service.py
  │  handle_cmd_vel / handle_webrtc_request / handle_joy_command
  ▼
WebRTCAdapter.send_movement_command / send_webrtc_request
  ▼
Go2Connection.data_channel.send()
  ▼
Robot hardware
```

## Threading Model

`main.py` creates a single asyncio event loop via `asyncio.run(main_async())`.

- **ROS2 spin** runs inside a `threading.Thread` using `SingleThreadedExecutor`.
- **WebRTC coroutines** run on the asyncio event loop in the main thread.
- `Go2DriverNode` receives the event loop reference at construction and uses `event_loop.call_soon_threadsafe()` to schedule WebRTC sends from ROS2 callbacks safely.

Never call `asyncio.run()` or `rclpy.spin()` directly from an already-running loop — the existing design routes all cross-thread calls through `call_soon_threadsafe`.

## Multi-Robot Mode

`ROBOT_IP="ip1,ip2"` triggers multi mode: `RobotConfig.conn_mode = "multi"`.

- `WebRTCAdapter` creates one `Go2Connection` per IP, keyed by `robot_id` string (`"0"`, `"1"`, …).
- `Go2DriverNode._setup_publishers()` creates a separate publisher list per robot and prefixes topics: `/robot0/joint_states`, `/robot1/odom`, etc.
- The URDF is automatically switched to `multi_go2.urdf`.
- TF child frames become `robot0/base_link`, `robot1/base_link`.

## WebRTC Connection Internals

`Go2Connection` (infrastructure/webrtc/go2_connection.py):

1. Performs HTTP signaling with the robot at `http://<ip>:9991`.
2. Uses AES-GCM encryption (`crypto/encryption.py`) for the validation handshake.
3. Creates an `RTCPeerConnection` via `aiortc`, opens a data channel (`id=0`), and optionally adds a video transceiver.
4. LiDAR frames arrive as binary messages; `WebRTCDataDecoder` delegates to `LidarDecoder` when `decode_lidar=True`.

## LiDAR Pipeline

```
WebRTC binary frame
  ▼
WebRTCDataDecoder      infrastructure/webrtc/data_decoder.py
  │  detects binary vs JSON, delegates binary to LidarDecoder
  ▼
LidarDecoder           infrastructure/sensors/lidar_decoder.py
  │  decompresses voxel map, returns point positions + metadata
  ▼
RobotDataService       application — wraps as LidarData entity
  ▼
ROS2Publisher          publishes sensor_msgs/PointCloud2 on /point_cloud2 (~7 Hz)
  ▼
pointcloud_to_laserscan_node → /scan (used by SLAM + Nav2 costmaps)
```

Additionally, `lidar_processor/lidar_to_pointcloud_node.py` subscribes to the raw PointCloud2, applies voxel downsampling, and optionally saves `.ply` snapshots every 10 s when `MAP_SAVE=True`.
