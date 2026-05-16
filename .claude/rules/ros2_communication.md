---
description: ROS2 Communication Standards (Topics, QoS, Messages)
---

# ROS2 Communication Standards

## Topic Naming Conventions

```
# Format: /<namespace>/<category>/<specific>

# GO2 SDK topics (existing)
/go2_state
/joint_states
/imu
/odom
/go2_camera/color/image
/point_cloud2
/scan
/cmd_vel_out
/cmd_vel_joy
/cmd_vel_foxglove
/webrtc_req
/detected_objects

# Multi-robot namespaced
/go2_0/go2_state
/go2_1/go2_state
```

### Naming Rules

| Rule | Example |
|---|---|
| Use lowercase | `/robot/cmd_vel` |
| Use underscores for multi-word | `/joint_states` |
| Avoid abbreviations | `/camera/image` not `/cam/img` |
| Use namespaces for multi-robot | `/go2_0/cmd_vel` |

## QoS Profiles

```python
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSDurabilityPolicy, QoSHistoryPolicy

# Sensor Data — high frequency, tolerate drops
SENSOR_QOS = QoSProfile(
    reliability=QoSReliabilityPolicy.BEST_EFFORT,
    durability=QoSDurabilityPolicy.VOLATILE,
    history=QoSHistoryPolicy.KEEP_LAST,
    depth=5
)

# Control Commands — reliable delivery
CONTROL_QOS = QoSProfile(
    reliability=QoSReliabilityPolicy.RELIABLE,
    durability=QoSDurabilityPolicy.VOLATILE,
    history=QoSHistoryPolicy.KEEP_LAST,
    depth=10
)

# State/Config — latched (new subscribers get last value)
STATE_QOS = QoSProfile(
    reliability=QoSReliabilityPolicy.RELIABLE,
    durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
    history=QoSHistoryPolicy.KEEP_LAST,
    depth=1
)
```

### QoS Selection Guide

| Data Type | Reliability | Durability | Depth | GO2 Example |
|---|---|---|---|---|
| Sensor (high freq) | BEST_EFFORT | VOLATILE | 1-5 | `/point_cloud2`, `/imu` |
| Commands | RELIABLE | VOLATILE | 10 | `/cmd_vel_out`, `/cmd_vel_joy` |
| State/Config | RELIABLE | TRANSIENT_LOCAL | 1 | `/go2_state` |
| Map | RELIABLE | TRANSIENT_LOCAL | 1 | `/map` |

## Custom Message Definition (go2_interfaces pattern)

```
# msg/Go2State.msg
std_msgs/Header header
string id
geometry_msgs/Twist twist
# ... etc
```

### CMakeLists.txt for Message Package

```cmake
cmake_minimum_required(VERSION 3.8)
project(go2_interfaces)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/Go2State.msg"
  "msg/IMU.msg"
  "srv/..."
  DEPENDENCIES std_msgs geometry_msgs
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
```

## TF2 Best Practices

```python
import tf2_ros
from geometry_msgs.msg import TransformStamped

class TransformPublisher:
    def __init__(self, node):
        self._node = node
        self._static_broadcaster = tf2_ros.StaticTransformBroadcaster(node)
        self._dynamic_broadcaster = tf2_ros.TransformBroadcaster(node)

    def publish_transform(self, parent: str, child: str, x: float, y: float, z: float):
        t = TransformStamped()
        t.header.stamp = self._node.get_clock().now().to_msg()
        t.header.frame_id = parent
        t.child_frame_id = child
        t.transform.translation.x = x
        t.transform.translation.y = y
        t.transform.translation.z = z
        t.transform.rotation.w = 1.0
        self._dynamic_broadcaster.sendTransform(t)
```
