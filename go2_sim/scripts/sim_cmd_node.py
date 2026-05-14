#!/usr/bin/env python3
# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

"""
sim_cmd_node — high-level command interface for the GO2 simulation.

Mirrors the /webrtc_req pattern used in hardware mode.
Publishes/calls the gait controller's internal topics from a single
root-level topic so users don't need to know the /go2/* namespace.

Usage:
  # Gait mode commands (case-insensitive)
  ros2 topic pub /sim_cmd std_msgs/msg/String "{data: 'TROT'}"  --once
  ros2 topic pub /sim_cmd std_msgs/msg/String "{data: 'REST'}"  --once
  ros2 topic pub /sim_cmd std_msgs/msg/String "{data: 'CRAWL'}" --once
  ros2 topic pub /sim_cmd std_msgs/msg/String "{data: 'STAND'}" --once

  # Behavior commands (case-insensitive)
  ros2 topic pub /sim_cmd std_msgs/msg/String "{data: 'sit'}"   --once
  ros2 topic pub /sim_cmd std_msgs/msg/String "{data: 'up'}"    --once
  ros2 topic pub /sim_cmd std_msgs/msg/String "{data: 'walk'}"  --once

Gait modes map to quadropted_msgs/RobotModeCommand on /go2/robot_mode.
Behavior commands call the quadropted_msgs/RobotBehaviorCommand service
on /go2/robot_behavior_command.
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from quadropted_msgs.msg import RobotModeCommand
from quadropted_msgs.srv import RobotBehaviorCommand

GAIT_MODES = {'REST', 'TROT', 'CRAWL', 'STAND'}
BEHAVIOR_CMDS = {'sit', 'up', 'walk'}


class SimCmdNode(Node):

    def __init__(self):
        super().__init__('sim_cmd_node')

        self.declare_parameter('robot_id', 1)
        self._robot_id = (
            self.get_parameter('robot_id').get_parameter_value().integer_value
        )

        self._mode_pub = self.create_publisher(
            RobotModeCommand, '/go2/robot_mode', 10
        )

        self._behavior_client = self.create_client(
            RobotBehaviorCommand, '/go2/robot_behavior_command'
        )

        self.create_subscription(String, '/sim_cmd', self._on_sim_cmd, 10)

        self.get_logger().info(
            'sim_cmd_node ready — publish to /sim_cmd '
            f'(modes: {GAIT_MODES}, behaviors: {BEHAVIOR_CMDS})'
        )

    def _on_sim_cmd(self, msg: String) -> None:
        cmd = msg.data.strip()
        upper = cmd.upper()

        if upper in GAIT_MODES:
            self._send_mode(upper)
        elif cmd.lower() in BEHAVIOR_CMDS:
            self._call_behavior(cmd.lower())
        else:
            self.get_logger().warn(
                f"Unknown sim command: '{cmd}'. "
                f"Valid: {sorted(GAIT_MODES | BEHAVIOR_CMDS)}"
            )

    def _send_mode(self, mode: str) -> None:
        msg = RobotModeCommand()
        msg.mode = mode
        msg.robot_id = self._robot_id
        self._mode_pub.publish(msg)
        self.get_logger().info(f'Gait mode → {mode}')

    def _call_behavior(self, command: str) -> None:
        if not self._behavior_client.service_is_ready():
            self.get_logger().warn(
                f"Behavior service not ready, dropping command '{command}'"
            )
            return

        req = RobotBehaviorCommand.Request()
        req.command = command

        future = self._behavior_client.call_async(req)
        future.add_done_callback(
            lambda f: self._on_behavior_response(command, f)
        )

    def _on_behavior_response(self, command: str, future) -> None:
        try:
            result = future.result()
            if result.success:
                self.get_logger().info(f"Behavior '{command}': {result.message}")
            else:
                self.get_logger().warn(f"Behavior '{command}' failed: {result.message}")
        except Exception as e:
            self.get_logger().error(f"Behavior service call failed: {e}")


def main(args=None):
    rclpy.init(args=args)
    node = SimCmdNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
