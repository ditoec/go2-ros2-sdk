---
description: Robot-Specific Standards (URDF, TF2, Navigation, GO2 SDK)
---

# Robot-Specific Standards

## GO2 TF Frame Tree

```
odom
 └── base_link
      ├── imu_link
      ├── lidar_link
      └── camera_link
           └── camera_optical
```

## URDF/Xacro Best Practices

```xml
<?xml version="1.0"?>
<robot xmlns:xacro="http://ros.org/wiki/xacro" name="go2">

  <xacro:property name="lidar_offset_z" value="0.36"/>

  <link name="base_link">
    <visual>
      <geometry><mesh filename="package://go2_robot_sdk/urdf/meshes/body.dae"/></geometry>
    </visual>
  </link>

  <link name="lidar_link"/>
  <joint name="lidar_joint" type="fixed">
    <parent link="base_link"/>
    <child link="lidar_link"/>
    <origin xyz="0 0 ${lidar_offset_z}" rpy="0 0 0"/>
  </joint>

</robot>
```

Multi-robot uses `multi_go2.urdf` (selected automatically when `ROBOT_IP` has multiple IPs).

## Navigation Stack Configuration (Nav2)

```yaml
# nav2_params.yaml
bt_navigator:
  ros__parameters:
    global_frame: map
    robot_base_frame: base_link
    odom_topic: /odom

controller_server:
  ros__parameters:
    controller_frequency: 20.0
    FollowPath:
      plugin: dwb_core::DWBLocalPlanner
      max_vel_x: 0.5
      max_vel_theta: 1.0

planner_server:
  ros__parameters:
    GridBased:
      plugin: nav2_navfn_planner/NavfnPlanner
      tolerance: 0.5
      use_astar: true
```

## Sensor Integration Pattern

```python
from sensor_msgs.msg import LaserScan, Imu, Image
from rclpy.qos import qos_profile_sensor_data

class SensorNode(Node):
    def __init__(self):
        super().__init__('sensor_node')
        self.lidar_pub = self.create_publisher(LaserScan, 'scan', qos_profile_sensor_data)
        self.camera_pub = self.create_publisher(Image, 'go2_camera/color/image', qos_profile_sensor_data)
        self.imu_pub = self.create_publisher(Imu, 'imu', qos_profile_sensor_data)
```

## WebRTC Command Pattern (GO2-specific)

Send robot API commands without modifying driver code via `/webrtc_req`:

```bash
ros2 topic pub /webrtc_req go2_interfaces/msg/WebRtcReq \
    "{api_id: 1016, topic: 'rt/api/sport/request'}" --once
```

New commands are defined in:
- `go2_robot_sdk/domain/constants/robot_commands.py` — `ROBOT_CMD` IDs
- `go2_robot_sdk/domain/constants/webrtc_topics.py` — `RTC_TOPIC` strings

## Motor/Velocity Control Pattern

```python
from geometry_msgs.msg import Twist

class MotorController(Node):
    def __init__(self):
        super().__init__('motor_controller')
        self.cmd_sub = self.create_subscription(
            Twist, 'cmd_vel_muxed', self.cmd_callback, 10
        )

    def cmd_callback(self, msg: Twist):
        linear = msg.linear.x
        angular = msg.angular.z
        # Forward to robot hardware/WebRTC
```

## LiDAR Processing Notes

- Python pipeline: `lidar_processor` package (slow but flexible)
- C++/PCL pipeline: `lidar_processor_cpp` package (faster)
- Output: `/point_cloud2` at ~7 Hz
- `pointcloud_to_laserscan` converts to `/scan` for Nav2
