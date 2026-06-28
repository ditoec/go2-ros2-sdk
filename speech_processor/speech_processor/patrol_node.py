#!/usr/bin/env python3

# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

"""
patrol_node — Modul 2.1: cycle through named waypoints indefinitely.

Subscribes to:
  /patrol_enable   (std_msgs/Bool)   True = start; False = stop
  /reload_waypoints (std_msgs/Empty)  hot-reload waypoints_file from disk

Publishes to:
  /patrol_status (std_msgs/String)
      "patrolling:<key>/<idx>/<total>"  — currently heading to this waypoint
      "patrol_done"                     — one round complete, looping
      "patrol_failed:<key>"             — a waypoint was unreachable
      "patrol_cancelled"                — stopped by user or error
  /tts (std_msgs/String)              spoken feedback

Parameters:
  waypoints_file  (str)   path to the YAML waypoint file (shared with nav_waypoint_node)
  patrol_route    (str)   comma-separated waypoint keys to visit; empty = all in YAML order
  nav_action      (str)   Nav2 action server name [default: navigate_to_pose]
  nav_timeout     (float) seconds to wait for Nav2 on startup [default: 120.0]
  skip_on_failure (bool)  advance to next waypoint on failure [default: true]
"""

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
from std_msgs.msg import Bool, Empty, String


def _yaw_to_quaternion(yaw: float) -> Quaternion:
    q = Quaternion()
    q.z = math.sin(yaw / 2.0)
    q.w = math.cos(yaw / 2.0)
    return q


class PatrolNode(Node):

    def __init__(self) -> None:
        super().__init__('patrol_node')

        self.declare_parameter('waypoints_file', '')
        self.declare_parameter('patrol_route', '')
        self.declare_parameter('nav_action', 'navigate_to_pose')
        self.declare_parameter('nav_timeout', 120.0)
        self.declare_parameter('skip_on_failure', True)

        self._waypoints: dict = {}
        self._route: list = []
        self._waypoints_file: str = self.get_parameter('waypoints_file').value
        self._patrol_route_param: str = self.get_parameter('patrol_route').value
        self._skip_on_failure: bool = bool(self.get_parameter('skip_on_failure').value)

        self._load_waypoints()

        action_name = self.get_parameter('nav_action').value
        self._nav_client = ActionClient(self, NavigateToPose, action_name)
        self._goal_handle = None
        self._running = False
        self._idx = 0

        self._patrol_status_pub = self.create_publisher(String, '/patrol_status', 10)
        self._tts_pub = self.create_publisher(String, '/tts', 10)

        self.create_subscription(Bool, '/patrol_enable', self._on_enable, 10)
        self.create_subscription(Empty, '/reload_waypoints', self._on_reload, 10)

        self.get_logger().info(
            f'patrol_node ready — {len(self._waypoints)} waypoints, '
            f'route={self._route or "all"}'
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
            self._build_route()
            self.get_logger().info(
                f'Loaded {len(self._waypoints)} waypoints from {path!r}'
            )
        except Exception as exc:
            self.get_logger().error(f'Failed to load waypoints from {path!r}: {exc}')

    def _build_route(self) -> None:
        if self._patrol_route_param:
            keys = [k.strip() for k in self._patrol_route_param.split(',') if k.strip()]
            self._route = [k for k in keys if k in self._waypoints]
            missing = [k for k in keys if k not in self._waypoints]
            if missing:
                self.get_logger().warn(f'patrol_route keys not in YAML: {missing}')
        else:
            self._route = list(self._waypoints.keys())

    def _on_reload(self, _msg: Empty) -> None:
        self.get_logger().info('Reloading waypoints from disk...')
        self._load_waypoints()

    # ------------------------------------------------------------------
    # Enable / disable
    # ------------------------------------------------------------------

    def _on_enable(self, msg: Bool) -> None:
        if msg.data:
            if self._running:
                self.get_logger().info('Patrol already running — ignoring enable')
                return
            if not self._route:
                self.get_logger().warn('No patrol route configured — cannot start')
                self._tts_pub.publish(String(data='No waypoints configured for patrol.'))
                return
            self.get_logger().info('Starting patrol')
            self._tts_pub.publish(String(data='Starting patrol.'))
            self._running = True
            self._idx = 0
            self._send_next_goal()
        else:
            self._stop_patrol()

    def _stop_patrol(self) -> None:
        if not self._running:
            return
        self._running = False
        self._cancel_current()
        self._tts_pub.publish(String(data='Patrol stopped.'))
        self._patrol_status_pub.publish(String(data='patrol_cancelled'))
        self.get_logger().info('Patrol stopped by user')

    # ------------------------------------------------------------------
    # Navigation loop (chained async callbacks — no blocking)
    # ------------------------------------------------------------------

    def _send_next_goal(self) -> None:
        if not self._running:
            return
        if not self._route:
            self.get_logger().warn('Patrol route is empty — stopping')
            self._running = False
            return

        key = self._route[self._idx]
        wp = self._waypoints.get(key)
        if wp is None:
            self.get_logger().warn(f'Waypoint {key!r} missing in YAML — skipping')
            self._advance_and_continue()
            return

        total = len(self._route)
        label = wp.get('label_en', key)
        display = f'{self._idx + 1}/{total}'
        self.get_logger().info(f'Patrol → {key!r} ({label}) [{display}]')
        self._tts_pub.publish(String(data=f'Heading to {label} ({display}).'))
        self._patrol_status_pub.publish(
            String(data=f'patrolling:{key}/{self._idx + 1}/{total}')
        )

        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = 'map'
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = float(wp.get('x', 0.0))
        goal.pose.pose.position.y = float(wp.get('y', 0.0))
        goal.pose.pose.orientation = _yaw_to_quaternion(float(wp.get('yaw', 0.0)))

        if not self._nav_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error('Nav2 action server not available — stopping patrol')
            self._tts_pub.publish(String(data='Navigation server not available.'))
            self._running = False
            self._patrol_status_pub.publish(String(data=f'patrol_failed:{key}'))
            return

        future = self._nav_client.send_goal_async(goal)
        future.add_done_callback(
            functools.partial(self._on_goal_response, key=key, label=label)
        )

    def _on_goal_response(self, future, *, key: str, label: str) -> None:
        handle = future.result()
        if not handle.accepted:
            self.get_logger().warn(f'Nav2 rejected goal to {key!r}')
            self._tts_pub.publish(String(data=f'Navigation to {label} was rejected.'))
            self._patrol_status_pub.publish(String(data=f'patrol_failed:{key}'))
            self._skip_or_abort(key)
            return
        self._goal_handle = handle
        result_future = handle.get_result_async()
        result_future.add_done_callback(
            functools.partial(self._on_result, key=key, label=label)
        )

    def _on_result(self, future, *, key: str, label: str) -> None:
        status = future.result().status
        self._goal_handle = None

        if not self._running:
            return  # cancelled by user; _stop_patrol() already published status

        if status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info(f'Arrived at {key!r}')
            self._tts_pub.publish(String(data=f'Arrived at {label}.'))
            self._advance_and_continue()
        elif status == GoalStatus.STATUS_CANCELED:
            self._running = False
            self._patrol_status_pub.publish(String(data='patrol_cancelled'))
        else:
            self.get_logger().warn(
                f'Navigation to {key!r} failed (status={status})'
            )
            self._patrol_status_pub.publish(String(data=f'patrol_failed:{key}'))
            self._skip_or_abort(key)

    def _advance_and_continue(self) -> None:
        if not self._running:
            return
        next_idx = (self._idx + 1) % len(self._route)
        if next_idx == 0:
            self.get_logger().info('Patrol completed one round — looping')
            self._patrol_status_pub.publish(String(data='patrol_done'))
            self._tts_pub.publish(String(data='Patrol completed one round.'))
        self._idx = next_idx
        self._send_next_goal()

    def _skip_or_abort(self, key: str) -> None:
        if self._skip_on_failure:
            self.get_logger().info(f'Skipping failed waypoint {key!r}')
            self._advance_and_continue()
        else:
            self.get_logger().warn(f'Patrol aborted at {key!r}')
            self._running = False
            self._patrol_status_pub.publish(String(data='patrol_cancelled'))

    def _cancel_current(self) -> None:
        if self._goal_handle is not None:
            self.get_logger().info('Cancelling current patrol goal')
            self._goal_handle.cancel_goal_async()
            self._goal_handle = None


def main(args=None) -> None:
    rclpy.init(args=args)
    node = PatrolNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
