#!/usr/bin/env python3

# SPDX-License-Identifier: BSD-3-Clause

"""
follow_me_node — Modul 4.3: person-tracking via YOLO detections.

Subscribes to /detected_objects (Detection2DArray from yolo_detector_node), selects the
largest "person" detection above a confidence threshold, and publishes a proportional
velocity command on /cmd_vel_follow (twist_mux priority 6 — below voice=7, above nav=5).

Enable/disable at runtime via /follow_enable (std_msgs/Bool). Voice wiring in
command_dispatcher.py publishes True on "ikuti saya" / "follow me" and False on "berhenti".

Control law:
  angular.z = -kp * ((bbox_center_x - img_w/2) / (img_w/2))   [clamped to ±max_angular]
  linear.x  = linear_speed  if bbox_area_fraction < target_area - deadband
             = 0.0           otherwise  (approach-only; no backing up for safety)

Image dimensions come from /camera/camera_info so the node never subscribes to full frames.
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from geometry_msgs.msg import Twist
from sensor_msgs.msg import CameraInfo
from std_msgs.msg import Bool
from vision_msgs.msg import Detection2DArray


class FollowMeNode(Node):

    def __init__(self) -> None:
        super().__init__('follow_me_node')

        self.declare_parameter('objects_topic',     '/detected_objects')
        self.declare_parameter('camera_info_topic', '/camera/camera_info')
        self.declare_parameter('follow_topic',      '/cmd_vel_follow')
        self.declare_parameter('linear_speed',      0.20)
        self.declare_parameter('angular_kp',        1.0)
        self.declare_parameter('max_angular_speed', 0.8)
        self.declare_parameter('target_area',       0.10)
        self.declare_parameter('area_deadband',     0.03)
        self.declare_parameter('min_confidence',    0.5)
        self.declare_parameter('lost_timeout',      1.0)
        self.declare_parameter('publish_rate',      10.0)

        self._lin_speed  = self.get_parameter('linear_speed').value
        self._kp         = self.get_parameter('angular_kp').value
        self._max_ang    = self.get_parameter('max_angular_speed').value
        self._tgt_area   = self.get_parameter('target_area').value
        self._deadband   = self.get_parameter('area_deadband').value
        self._min_conf   = self.get_parameter('min_confidence').value
        self._lost_to    = self.get_parameter('lost_timeout').value
        rate             = self.get_parameter('publish_rate').value

        objects_topic     = self.get_parameter('objects_topic').value
        camera_info_topic = self.get_parameter('camera_info_topic').value
        follow_topic      = self.get_parameter('follow_topic').value

        self._enabled        = False
        self._img_w: int     = 640
        self._img_h: int     = 480
        self._current_twist  = Twist()
        self._last_det_ns    = 0

        self._follow_pub = self.create_publisher(Twist, follow_topic, 10)

        self.create_subscription(
            Detection2DArray, objects_topic, self._on_detections, 10
        )
        self.create_subscription(
            CameraInfo, camera_info_topic, self._on_camera_info, qos_profile_sensor_data
        )
        self.create_subscription(Bool, '/follow_enable', self._on_enable, 10)

        self.create_timer(1.0 / rate, self._publish_tick)

        self.get_logger().info(
            f'follow_me_node ready — target_area={self._tgt_area:.2f} '
            f'linear={self._lin_speed:.2f} m/s  kp={self._kp:.2f}  '
            f'max_ang={self._max_ang:.2f} rad/s  '
            f'publish_topic={follow_topic} at {rate:.0f} Hz'
        )

    # ------------------------------------------------------------------

    def _on_enable(self, msg: Bool) -> None:
        self._enabled = msg.data
        if not msg.data:
            self._current_twist = Twist()
        self.get_logger().info(f"Follow mode {'ENABLED' if msg.data else 'DISABLED'}")

    def _on_camera_info(self, msg: CameraInfo) -> None:
        self._img_w = msg.width or self._img_w
        self._img_h = msg.height or self._img_h

    def _on_detections(self, msg: Detection2DArray) -> None:
        if not self._enabled:
            return

        persons = [
            d for d in msg.detections
            if d.results
            and d.results[0].hypothesis.class_id == 'person'
            and d.results[0].hypothesis.score >= self._min_conf
        ]
        if not persons:
            return

        best = max(persons, key=lambda d: d.bbox.size_x * d.bbox.size_y)
        self._last_det_ns = self.get_clock().now().nanoseconds

        cx = best.bbox.center.position.x
        error_x = (cx - self._img_w / 2.0) / (self._img_w / 2.0)

        area_frac = (best.bbox.size_x * best.bbox.size_y) / max(
            self._img_w * self._img_h, 1
        )

        twist = Twist()
        raw_az = -self._kp * error_x
        twist.angular.z = max(-self._max_ang, min(self._max_ang, raw_az))
        if area_frac < self._tgt_area - self._deadband:
            twist.linear.x = self._lin_speed

        self._current_twist = twist

    def _publish_tick(self) -> None:
        if not self._enabled:
            return
        now_ns = self.get_clock().now().nanoseconds
        age_s = (now_ns - self._last_det_ns) * 1e-9
        self._follow_pub.publish(
            Twist() if age_s > self._lost_to else self._current_twist
        )


def main(args=None) -> None:
    rclpy.init(args=args)
    node = FollowMeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
