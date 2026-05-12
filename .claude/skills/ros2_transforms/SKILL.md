---
name: ROS2 Transforms (TF2)
description: ROS2 TF2 and Transform management with Clean Architecture (Python & C++)
---

# ROS2 Transforms (TF2) Skill

## Domain Layer (no TF2 dependency)

```python
# domain/entities/pose.py
from dataclasses import dataclass

@dataclass
class Pose:
    position: tuple   # (x, y, z)
    orientation: tuple  # (x, y, z, w)
    frame_id: str
    timestamp: float
```

```cpp
// domain/entities/pose.hpp
namespace domain::entities {
struct Point3D { double x, y, z; };
struct Quaternion { double x, y, z, w; };
struct Pose {
    Point3D position;
    Quaternion orientation;
    std::string frame_id;
    double timestamp;
};
}
```

## Infrastructure — TF2 Wrapper (Python)

```python
# infrastructure/ros2/services/tf_service.py
import tf2_ros
from geometry_msgs.msg import TransformStamped
from domain.entities.pose import Pose

class TFService:
    def __init__(self, node):
        self._node = node
        self._tf_buffer = tf2_ros.Buffer()
        self._tf_listener = tf2_ros.TransformListener(self._tf_buffer, node)
        self._static_broadcaster = tf2_ros.StaticTransformBroadcaster(node)
        self._dynamic_broadcaster = tf2_ros.TransformBroadcaster(node)

    def lookup_transform(self, target_frame: str, source_frame: str) -> Pose | None:
        try:
            t = self._tf_buffer.lookup_transform(target_frame, source_frame, rclpy.time.Time())
            return Pose(
                position=(t.transform.translation.x,
                           t.transform.translation.y,
                           t.transform.translation.z),
                orientation=(t.transform.rotation.x, t.transform.rotation.y,
                              t.transform.rotation.z, t.transform.rotation.w),
                frame_id=t.header.frame_id,
                timestamp=0.0
            )
        except Exception as e:
            self._node.get_logger().warn(f'TF lookup failed: {e}')
            return None

    def publish_transform(self, parent: str, child: str,
                           x: float, y: float, z: float,
                           qx: float = 0.0, qy: float = 0.0,
                           qz: float = 0.0, qw: float = 1.0,
                           static: bool = False):
        t = TransformStamped()
        t.header.stamp = self._node.get_clock().now().to_msg()
        t.header.frame_id = parent
        t.child_frame_id = child
        t.transform.translation.x = x
        t.transform.translation.y = y
        t.transform.translation.z = z
        t.transform.rotation.x = qx
        t.transform.rotation.y = qy
        t.transform.rotation.z = qz
        t.transform.rotation.w = qw
        if static:
            self._static_broadcaster.sendTransform(t)
        else:
            self._dynamic_broadcaster.sendTransform(t)
```

## Infrastructure — TF2 Wrapper (C++)

```cpp
// infrastructure/ros2/services/tf_service.cpp
#include "tf_service.hpp"

std::optional<domain::entities::Pose> TFService::get_transform(
    const std::string& target_frame, const std::string& source_frame) {

    try {
        geometry_msgs::msg::TransformStamped t =
            tf_buffer_->lookupTransform(target_frame, source_frame, tf2::TimePointZero);

        return domain::entities::Pose{
            {t.transform.translation.x, t.transform.translation.y, t.transform.translation.z},
            {t.transform.rotation.x, t.transform.rotation.y,
             t.transform.rotation.z, t.transform.rotation.w},
            t.header.frame_id,
            rclcpp::Time(t.header.stamp).seconds()
        };
    } catch (const tf2::TransformException& ex) {
        RCLCPP_WARN(node_->get_logger(), "TF lookup failed: %s", ex.what());
        return std::nullopt;
    }
}
```

## GO2 TF Frame Tree

```
odom
 └── base_link
      ├── imu_link
      ├── lidar_link
      └── camera_link
           └── camera_optical_frame
```

Publish static transforms for fixed sensors (lidar, camera, IMU) in the driver launch file.

## Best Practices

1. Domain Use Cases must never import `tf2_ros` — only infrastructure layer touches TF2.
2. Always catch `tf2::TransformException` (C++) / equivalent (Python).
3. Default buffer cache is 10 seconds; adequate for most sensor transforms.
4. Use static broadcasters for fixed sensor offsets; dynamic for odometry/moving frames.
