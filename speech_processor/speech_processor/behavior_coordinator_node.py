#!/usr/bin/env python3
# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause
"""
Behavior coordinator — observational state machine.

Subscribes to existing status topics (/follow_enable, /navigation_status,
/cmd_vel_voice, /approach_status, /patrol_status) and publishes /behavior_mode
(TRANSIENT_LOCAL) so any node can always read the current robot intent without
waiting for the next event.

States:
  IDLE        — no active behavior
  VOICE_MOVE  — voice-commanded motion (timed or sustained)
  FOLLOWING   — follow_me_node is active
  NAVIGATING  — nav_waypoint_node has an active Nav2 goal
  APPROACHING — approach_object_node is actively pursuing an object
  PATROL      — patrol_node is cycling through waypoints

Transitions are driven purely by subscribing to the topics above; this node
issues no commands of its own.

Enable with: ENABLE_BEHAVIOR_COORDINATOR=true ros2 launch go2_robot_sdk robot.launch.py
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy

from geometry_msgs.msg import Twist
from std_msgs.msg import Bool, String

_LATCHED_QOS = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
    depth=1,
)


class BehaviorCoordinatorNode(Node):
    def __init__(self) -> None:
        super().__init__('behavior_coordinator')

        self._mode: str = "IDLE"
        self._last_vel_t: float = 0.0
        self._vel_idle_sec: float = (
            self.declare_parameter('vel_idle_timeout', 0.6).value
        )

        self.create_subscription(Bool,   '/follow_enable',     self._on_follow,        10)
        self.create_subscription(String, '/navigation_status', self._on_nav_status,    10)
        self.create_subscription(Twist,  '/cmd_vel_voice',     self._on_vel,            5)
        self.create_subscription(String, '/approach_status',   self._on_approach_status, 10)
        self.create_subscription(String, '/patrol_status',     self._on_patrol_status,  10)

        self._mode_pub = self.create_publisher(String, '/behavior_mode', _LATCHED_QOS)
        self.create_timer(0.2, self._tick)

        self._publish()
        self.get_logger().info('behavior_coordinator started — mode: IDLE')

    # ------------------------------------------------------------------
    # Subscribers
    # ------------------------------------------------------------------

    def _on_follow(self, msg: Bool) -> None:
        if msg.data:
            self._set('FOLLOWING')
        elif self._mode == 'FOLLOWING':
            self._set('IDLE')

    def _on_nav_status(self, msg: String) -> None:
        s = msg.data
        if s.startswith('navigating:'):
            self._set('NAVIGATING')
        elif self._mode == 'NAVIGATING' and (
            s.startswith(('arrived:', 'failed:', 'unknown:')) or s == 'cancelled'
        ):
            self._set('IDLE')

    def _on_vel(self, msg: Twist) -> None:
        if msg.linear.x or msg.linear.y or msg.angular.z:
            self._last_vel_t = self.get_clock().now().nanoseconds * 1e-9
            if self._mode == 'IDLE':
                self._set('VOICE_MOVE')

    def _on_approach_status(self, msg: String) -> None:
        s = msg.data
        if s.startswith('approaching:'):
            self._set('APPROACHING')
        elif self._mode == 'APPROACHING' and (
            s.startswith(('reached:', 'lost:')) or s == 'cancelled'
        ):
            self._set('IDLE')

    def _on_patrol_status(self, msg: String) -> None:
        s = msg.data
        if s.startswith('patrolling:'):
            self._set('PATROL')
        elif self._mode == 'PATROL' and s in ('patrol_cancelled', 'patrol_done'):
            self._set('IDLE')

    # ------------------------------------------------------------------
    # Timer — detect when voice motion has gone silent
    # ------------------------------------------------------------------

    def _tick(self) -> None:
        if self._mode == 'VOICE_MOVE':
            now = self.get_clock().now().nanoseconds * 1e-9
            if now - self._last_vel_t > self._vel_idle_sec:
                self._set('IDLE')

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------

    def _set(self, mode: str) -> None:
        if mode != self._mode:
            self.get_logger().info(f'behavior: {self._mode} → {mode}')
            self._mode = mode
            self._publish()

    def _publish(self) -> None:
        self._mode_pub.publish(String(data=self._mode))


def main(args=None) -> None:
    rclpy.init(args=args)
    node = BehaviorCoordinatorNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
