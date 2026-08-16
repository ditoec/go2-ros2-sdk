#!/usr/bin/env python3

# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

"""
nav_waypoint_node — Voice → Nav2 NavigateToPose goal (Modul 5.2 / 5.3).

Subscribes to:
  /navigate_to_room  (std_msgs/String) — room name to navigate to;
                                         empty string = cancel current goal
  /reload_waypoints  (std_msgs/Empty)  — hot-reload waypoints_file from disk

Publishes to:
  /navigation_status (std_msgs/String) — "navigating:<room>", "arrived:<room>",
                                         "failed:<room>", "cancelled", "unknown:<room>"
  /tts               (std_msgs/String) — spoken feedback for start / arrival / failure

Parameters:
  waypoints_file  (str)   — path to the YAML waypoint file (required)
  nav_action      (str)   — Nav2 action server name  [default: navigate_to_pose]
  nav_timeout     (float) — seconds to wait for action server at startup [default: 120.0]

Waypoint YAML format:
  waypoints:
    lobby:
      x: 3.0
      y: 2.0
      yaw: 1.57        # radians, optional (default 0)
      label_en: "lobby"
      label_id: "lobi"

Fuzzy name matching: the room name from /navigate_to_room is normalised
(lowercase, spaces → underscores) then matched against waypoint keys, label_en,
and label_id with substring fallback.
"""

from __future__ import annotations

import functools
import math
import os

import rclpy
import yaml
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import Quaternion
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.node import Node
from std_msgs.msg import Empty, String


def _yaw_to_quaternion(yaw: float) -> Quaternion:
    q = Quaternion()
    q.z = math.sin(yaw / 2.0)
    q.w = math.cos(yaw / 2.0)
    return q


class NavWaypointNode(Node):

    def __init__(self) -> None:
        super().__init__('nav_waypoint_node')

        self.declare_parameter('waypoints_file', '')
        self.declare_parameter('nav_action', 'navigate_to_pose')
        self.declare_parameter('nav_timeout', 120.0)

        wp_file = self.get_parameter('waypoints_file').value
        self._waypoints: dict = {}
        if wp_file:
            self._waypoints_file = wp_file
            self._load_waypoints()
        else:
            self.get_logger().warn(
                'nav_waypoint_node: waypoints_file parameter not set — '
                'no waypoints loaded. Set WAYPOINTS_FILE env var.'
            )
            self._waypoints_file = ''

        action_name = self.get_parameter('nav_action').value
        self._nav_client = ActionClient(self, NavigateToPose, action_name)
        self._goal_handle = None

        self._nav_status_pub = self.create_publisher(String, '/navigation_status', 10)
        self._tts_pub = self.create_publisher(String, '/tts', 10)

        self.create_subscription(String, '/navigate_to_room', self._on_navigate, 10)
        self.create_subscription(Empty, '/reload_waypoints', self._on_reload, 10)

        self.get_logger().info(
            f'nav_waypoint_node ready — {len(self._waypoints)} waypoints loaded'
        )

    # ------------------------------------------------------------------
    # Waypoint loading
    # ------------------------------------------------------------------

    def _load_waypoints(self) -> None:
        path = self._waypoints_file
        if not path or not os.path.isfile(path):
            self.get_logger().warn(f'Waypoints file not found: {path!r}')
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            self._waypoints = data.get('waypoints', {}) or {}
            self.get_logger().info(
                f'Loaded {len(self._waypoints)} waypoints from {path!r}'
            )
        except Exception as exc:
            self.get_logger().error(f'Failed to load waypoints from {path!r}: {exc}')

    def _on_reload(self, _msg: Empty) -> None:
        self.get_logger().info('Reloading waypoints from disk...')
        self._load_waypoints()

    # ------------------------------------------------------------------
    # Fuzzy lookup
    # ------------------------------------------------------------------

    def _lookup(self, room: str) -> dict | None:
        key = room.lower().replace(' ', '_').replace('-', '_')
        if key in self._waypoints:
            return self._waypoints[key]
        for k, wp in self._waypoints.items():
            if (
                key in k
                or key in wp.get('label_en', '').lower().replace(' ', '_')
                or key in wp.get('label_id', '').lower().replace(' ', '_')
            ):
                return wp
        return None

    # ------------------------------------------------------------------
    # Navigation callbacks
    # ------------------------------------------------------------------

    def _on_navigate(self, msg: String) -> None:
        room = msg.data.strip()
        if not room:
            self._cancel_current()
            return

        wp = self._lookup(room)
        if wp is None:
            self.get_logger().warn(f'Unknown room: {room!r}')
            self._tts_pub.publish(String(data=f"I don't know where {room} is."))
            self._nav_status_pub.publish(String(data=f'unknown:{room}'))
            return

        self._cancel_current()

        label = wp.get('label_en', room)
        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = 'map'
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = float(wp.get('x', 0.0))
        goal.pose.pose.position.y = float(wp.get('y', 0.0))
        goal.pose.pose.orientation = _yaw_to_quaternion(float(wp.get('yaw', 0.0)))

        self.get_logger().info(
            f'Navigating to {room!r} ({label}) '
            f'x={goal.pose.pose.position.x:.2f} y={goal.pose.pose.position.y:.2f}'
        )
        self._tts_pub.publish(String(data=f'Navigating to {label}.'))
        self._nav_status_pub.publish(String(data=f'navigating:{room}'))

        if not self._nav_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error(
                'Nav2 action server not available — is Nav2 running?'
            )
            self._tts_pub.publish(String(data='Navigation server not available.'))
            self._nav_status_pub.publish(String(data=f'failed:{room}'))
            return

        future = self._nav_client.send_goal_async(goal)
        future.add_done_callback(
            functools.partial(self._on_goal_response, room=room, label=label)
        )

    def _on_goal_response(self, future, *, room: str, label: str) -> None:
        handle = future.result()
        if not handle.accepted:
            self.get_logger().warn(f'Navigation goal to {room!r} was rejected by Nav2')
            self._tts_pub.publish(String(data=f'Navigation to {label} was rejected.'))
            self._nav_status_pub.publish(String(data=f'failed:{room}'))
            return
        self._goal_handle = handle
        result_future = handle.get_result_async()
        result_future.add_done_callback(
            functools.partial(self._on_result, room=room, label=label)
        )

    def _on_result(self, future, *, room: str, label: str) -> None:
        status = future.result().status
        self._goal_handle = None
        if status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info(f'Arrived at {room!r}')
            self._tts_pub.publish(String(data=f'Arrived at {label}.'))
            self._nav_status_pub.publish(String(data=f'arrived:{room}'))
        elif status == GoalStatus.STATUS_CANCELED:
            self.get_logger().info(f'Navigation to {room!r} was cancelled')
            self._nav_status_pub.publish(String(data='cancelled'))
        else:
            self.get_logger().warn(f'Navigation to {room!r} failed (status={status})')
            self._tts_pub.publish(String(data=f'Navigation to {label} failed.'))
            self._nav_status_pub.publish(String(data=f'failed:{room}'))

    def _cancel_current(self) -> None:
        if self._goal_handle is not None:
            self.get_logger().info('Cancelling current navigation goal')
            self._goal_handle.cancel_goal_async()
            self._goal_handle = None
            self._nav_status_pub.publish(String(data='cancelled'))


def main(args=None) -> None:
    rclpy.init(args=args)
    node = NavWaypointNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
