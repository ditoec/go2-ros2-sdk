#!/usr/bin/env python3

# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

"""
approach_object_node — Modul 2.1/2.2: one-shot visual servo toward a YOLO-detected object.

Mirrors follow_me_node's proportional controller but:
  - Target class is set at runtime via /approach_target (String) instead of being hardcoded.
  - One-shot: stops automatically when the object fills target_area fraction of the image.
  - Reports /approach_status so behavior_coordinator can track APPROACHING state.

Publishes velocity on /cmd_vel_follow (same twist_mux priority 6 as follow_me_node).
CommandDispatcher enforces mutual exclusion: approach_object disables follow_me before
activating, so both never publish simultaneously.

Subscribes to:
  /detected_objects  (vision_msgs/Detection2DArray)  YOLO detections
  /camera/camera_info (sensor_msgs/CameraInfo)        image dimensions (no frame data)
  /approach_target   (std_msgs/String)                YOLO class name to approach;
                                                       empty string = cancel

Publishes to:
  /cmd_vel_follow    (geometry_msgs/Twist)            velocity → twist_mux priority 6
  /approach_status   (std_msgs/String)
      "approaching:<class>"  — target set, searching / approaching
      "reached:<class>"      — close enough, stopped
      "lost:<class>"         — target not seen for lost_timeout seconds
      "cancelled"            — approach cancelled via empty /approach_target
  /tts               (std_msgs/String)                spoken feedback

Control law (identical to follow_me_node):
  angular.z = -kp * ((bbox_center_x - img_w/2) / (img_w/2))  [clamped ±max_angular]
  linear.x  = linear_speed  if bbox_area_fraction < target_area - deadband  else 0

Stop condition: bbox_area_fraction >= target_area - deadband  → _on_reached()
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from geometry_msgs.msg import Twist
from sensor_msgs.msg import CameraInfo
from std_msgs.msg import String
from vision_msgs.msg import Detection2DArray


class ApproachObjectNode(Node):

    def __init__(self) -> None:
        super().__init__('approach_object_node')

        self.declare_parameter('objects_topic',      '/detected_objects')
        self.declare_parameter('camera_info_topic',  '/camera/camera_info')
        self.declare_parameter('linear_speed',       0.25)
        self.declare_parameter('angular_kp',         1.0)
        self.declare_parameter('max_angular_speed',  0.8)
        self.declare_parameter('target_area',        0.12)
        self.declare_parameter('area_deadband',      0.03)
        self.declare_parameter('min_confidence',     0.5)
        self.declare_parameter('lost_timeout',       2.0)
        self.declare_parameter('publish_rate',       10.0)

        self._lin_speed = float(self.get_parameter('linear_speed').value)
        self._kp        = float(self.get_parameter('angular_kp').value)
        self._max_ang   = float(self.get_parameter('max_angular_speed').value)
        self._tgt_area  = float(self.get_parameter('target_area').value)
        self._deadband  = float(self.get_parameter('area_deadband').value)
        self._min_conf  = float(self.get_parameter('min_confidence').value)
        self._lost_to   = float(self.get_parameter('lost_timeout').value)

        self._target_class: str   = ''
        self._current_twist: Twist = Twist()
        self._last_det_ns: int    = 0
        self._img_w: float        = 640.0
        self._img_h: float        = 480.0

        objs_topic  = self.get_parameter('objects_topic').value
        cam_topic   = self.get_parameter('camera_info_topic').value
        rate        = float(self.get_parameter('publish_rate').value)

        self.create_subscription(
            Detection2DArray, objs_topic, self._on_detections, qos_profile_sensor_data
        )
        self.create_subscription(
            CameraInfo, cam_topic, self._on_camera_info, qos_profile_sensor_data
        )
        self.create_subscription(String, '/approach_target', self._on_target, 10)

        self._follow_pub  = self.create_publisher(Twist,  '/cmd_vel_follow',   10)
        self._status_pub  = self.create_publisher(String, '/approach_status',   10)
        self._tts_pub     = self.create_publisher(String, '/tts',               10)

        self.create_timer(1.0 / rate, self._publish_tick)

        self.get_logger().info('approach_object_node ready')

    # ------------------------------------------------------------------
    # Subscribers
    # ------------------------------------------------------------------

    def _on_target(self, msg: String) -> None:
        cls = msg.data.strip().lower()
        if not cls:
            if self._target_class:
                self._follow_pub.publish(Twist())
                self._status_pub.publish(String(data='cancelled'))
                self.get_logger().info(f'Approach to {self._target_class!r} cancelled')
                self._target_class = ''
            return
        self._target_class  = cls
        self._current_twist = Twist()
        self._last_det_ns   = self.get_clock().now().nanoseconds
        self._status_pub.publish(String(data=f'approaching:{cls}'))
        self._tts_pub.publish(String(data=f'Approaching {cls.replace("_", " ")}.'))
        self.get_logger().info(f'Approach target set: {cls!r}')

    def _on_camera_info(self, msg: CameraInfo) -> None:
        self._img_w = float(msg.width)  or self._img_w
        self._img_h = float(msg.height) or self._img_h

    def _on_detections(self, msg: Detection2DArray) -> None:
        if not self._target_class:
            return

        targets = [
            d for d in msg.detections
            if d.results
            and d.results[0].hypothesis.class_id == self._target_class
            and d.results[0].hypothesis.score >= self._min_conf
        ]
        if not targets:
            return  # timer handles lost timeout

        best = max(targets, key=lambda d: d.bbox.size_x * d.bbox.size_y)
        self._last_det_ns = self.get_clock().now().nanoseconds

        cx       = best.bbox.center.position.x
        error_x  = (cx - self._img_w / 2.0) / (self._img_w / 2.0)
        area_frac = (best.bbox.size_x * best.bbox.size_y) / max(
            self._img_w * self._img_h, 1.0
        )

        if area_frac >= self._tgt_area - self._deadband:
            self._on_reached()
            return

        twist = Twist()
        raw_az          = -self._kp * error_x
        twist.angular.z = max(-self._max_ang, min(self._max_ang, raw_az))
        twist.linear.x  = self._lin_speed
        self._current_twist = twist

    # ------------------------------------------------------------------
    # Timer — publish velocity and detect lost target
    # ------------------------------------------------------------------

    def _publish_tick(self) -> None:
        if not self._target_class:
            return
        now_ns = self.get_clock().now().nanoseconds
        age_s  = (now_ns - self._last_det_ns) * 1e-9
        if age_s > self._lost_to:
            self._on_lost()
        else:
            self._follow_pub.publish(self._current_twist)

    # ------------------------------------------------------------------
    # Terminal conditions
    # ------------------------------------------------------------------

    def _on_reached(self) -> None:
        cls = self._target_class
        self._follow_pub.publish(Twist())
        self._target_class  = ''
        self._current_twist = Twist()
        self._status_pub.publish(String(data=f'reached:{cls}'))
        self._tts_pub.publish(
            String(data=f'Reached the {cls.replace("_", " ")}.')
        )
        self.get_logger().info(f'Reached target {cls!r}')

    def _on_lost(self) -> None:
        cls = self._target_class
        self._follow_pub.publish(Twist())
        self._target_class  = ''
        self._current_twist = Twist()
        self._status_pub.publish(String(data=f'lost:{cls}'))
        self._tts_pub.publish(
            String(data=f'Lost sight of {cls.replace("_", " ")}.')
        )
        self.get_logger().warn(f'Lost target {cls!r} after {self._lost_to:.1f}s')


def main(args=None) -> None:
    rclpy.init(args=args)
    node = ApproachObjectNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
