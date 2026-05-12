# Topics and Interfaces

## Published Topics (hardware mode, single robot)

| Topic | Type | QoS | Rate | Notes |
|---|---|---|---|---|
| `/joint_states` | `sensor_msgs/JointState` | RELIABLE depth 10 | 1 Hz | Firmware v1.1.7 limit |
| `/go2_states` | `go2_interfaces/Go2State` | RELIABLE depth 10 | ~10 Hz | |
| `/imu` | `go2_interfaces/IMU` | RELIABLE depth 10 | ~50 Hz | Quaternion, accel, gyro, RPY |
| `/odom` | `nav_msgs/Odometry` | RELIABLE depth 10 | ~10 Hz | Also broadcasts `odom→base_link` TF |
| `/point_cloud2` | `sensor_msgs/PointCloud2` | BEST_EFFORT depth 1 | ~7 Hz | XYZ float32 |
| `/scan` | `sensor_msgs/LaserScan` | — | ~7 Hz | Derived from `/point_cloud2` by `pointcloud_to_laserscan_node` |
| `/camera/image_raw` | `sensor_msgs/Image` | BEST_EFFORT depth 1 | ~30 Hz | BGR8; hardware mode. Simulation bridge outputs to `/go2_camera/color/image` instead |
| `/camera/camera_info` | `sensor_msgs/CameraInfo` | BEST_EFFORT depth 1 | ~30 Hz | |
| `/utlidar/voxel_map_compressed` | `go2_interfaces/VoxelMapCompressed` | BEST_EFFORT depth 1 | ~7 Hz | Only when `publish_raw_voxel:=true` |
| `/detected_objects` | `vision_msgs/Detection2DArray` | depth 10 | on demand | Published by `coco_detector_node` |
| `/annotated_image` | `sensor_msgs/Image` | depth 10 | on demand | Published by `coco_detector_node` |

## Subscribed Topics

| Topic | Type | Consumer | Notes |
|---|---|---|---|
| `/cmd_vel_out` | `geometry_msgs/Twist` | `Go2DriverNode` | Actual movement commands after mux |
| `/webrtc_req` | `go2_interfaces/WebRtcReq` | `Go2DriverNode` | Arbitrary robot API commands |
| `/joy` | `sensor_msgs/Joy` | `Go2DriverNode` | Stand up (button 0) / stand down (button 1) |

## Velocity Command Pipeline

```
Joystick hardware
  → joy_node           /joy
  → teleop_twist_joy   /cmd_vel_joy  (priority 10)

Nav2 planner           /cmd_vel      (priority 5)

  → twist_mux          /cmd_vel_muxed   (highest-priority active source wins)
  → Go2DriverNode                       (subscribed as /cmd_vel_out)
  → robot hardware
```

`twist_mux.yaml` controls the priority levels. Joystick always overrides Nav2.

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
