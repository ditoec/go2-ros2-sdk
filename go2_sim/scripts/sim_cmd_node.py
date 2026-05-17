#!/usr/bin/env python3
# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

"""
sim_cmd_node — high-level command interface for the GO2 simulation.

Subscribes to /sim_cmd as go2_interfaces/msg/WebRtcReq — the same
message type and format as /webrtc_req on hardware.  The same
`ros2 topic pub` command therefore works in both modes:

  Hardware:   ros2 topic pub /webrtc_req go2_interfaces/msg/WebRtcReq "{api_id: 1004}" --once
  Simulation: ros2 topic pub /sim_cmd   go2_interfaces/msg/WebRtcReq "{api_id: 1004}" --once

Supported api_ids
─────────────────
 1001  Damp            → REST (safe stop)
 1002  BalanceStand    → STAND controller
 1003  StopMove        → REST (force stop)
 1004  StandUp         → REST mode
 1005  StandDown       → lower body (sit pose)
 1006  RecoveryStand   → REST → TROT transition
 1007  Euler           → set body roll/pitch/yaw  parameter: "roll,pitch,yaw" in radians
 1009  Sit             → lower body (same as StandDown)
 1010  RiseSit         → REST (rise from sit)
 1011  SwitchGait      → switch gait  parameter: "0"=REST "1"=TROT "2"=CRAWL "3"=STAND
 1013  BodyHeight      → body height offset in metres  parameter: float, clamped to ±0.15
 1015  SpeedLevel      → velocity multiplier  parameter: "0"=slow(×0.5) "1"=normal "2"=fast(×1.5)
 1017  Stretch         → extended standing pose (body forward + raised)
 1019  ContinuousGait  → autoRest toggle  parameter: "0"=always-trot  "1"=rest-when-still

Not implemented (hardware animation only):
  Move(1008), FootRaiseHeight(1014), Hello(1016), TrajectoryFollow(1018),
  Content(1020), Wallow(1021), Dance1(1022), Dance2(1023), Scrape(1029),
  FrontFlip(1030), FrontJump(1031), FrontPounce(1032), WiggleHips(1033),
  FingerHeart(1036), Handstand(1301), MoonWalk(1305), and others.
"""

import rclpy
from rclpy.node import Node
from go2_interfaces.msg import WebRtcReq
from quadropted_msgs.msg import RobotModeCommand
from quadropted_msgs.srv import RobotBehaviorCommand

# api_id values routed directly to the gait mode topic (no body-position side-effects)
_API_TO_MODE = {
    1001: 'REST',   # Damp — safe stop; does NOT reset body height
    1002: 'STAND',  # BalanceStand
    1003: 'REST',   # StopMove — safe stop; does NOT reset body height
}

# SwitchGait (1011) parameter → gait mode
# Unitree gait type numbering: 0=idle, 1=trot, 2=run/crawl, 3=balance-stand, 4=obstacle
_GAIT_TYPE_MAP = {
    '0': 'REST',
    '1': 'TROT',
    '2': 'CRAWL',
    '3': 'STAND',
    '4': 'CRAWL',   # obstacle/stair → CRAWL (closest sim equivalent)
}

# api_id values routed to the RobotBehaviorCommand service.
# Commands that change both gait mode AND body position must go here, not _API_TO_MODE,
# so that body_local_position is reset alongside the controller switch.
_API_TO_BEHAVIOR = {
    1004: 'up',             # StandUp — REST + body_local_position reset to 0
    1005: 'sit',            # StandDown
    1006: 'recoverystand',
    1007: 'euler',
    1009: 'sit',            # Sit
    1010: 'up',             # RiseSit — same as StandUp
    1013: 'bodyheight',
    1015: 'speedlevel',
    1017: 'stretch',
    1019: 'continuousgait',
}

# api_ids that require hardware-side animations — not implementable in sim
_NOT_IMPL = {
    1008: 'Move', 1012: 'Trigger', 1014: 'FootRaiseHeight',
    1016: 'Hello', 1018: 'TrajectoryFollow', 1020: 'Content',
    1021: 'Wallow', 1022: 'Dance1', 1023: 'Dance2',
    1024: 'GetBodyHeight', 1025: 'GetFootRaiseHeight',
    1026: 'GetSpeedLevel', 1027: 'SwitchJoystick', 1028: 'Pose',
    1029: 'Scrape', 1030: 'FrontFlip', 1031: 'FrontJump',
    1032: 'FrontPounce', 1033: 'WiggleHips', 1034: 'GetState',
    1035: 'EconomicGait', 1036: 'FingerHeart', 1039: 'StandOut',
    1045: 'FreeWalk', 1050: 'Standup', 1051: 'CrossWalk',
    1301: 'Handstand', 1302: 'CrossStep', 1303: 'OnesidedStep',
    1304: 'Bound', 1305: 'MoonWalk',
}


class SimCmdNode(Node):

    def __init__(self):
        super().__init__('sim_cmd_node')

        self.declare_parameter('robot_id', 1)
        self._robot_id = self.get_parameter('robot_id').get_parameter_value().integer_value

        self._mode_pub = self.create_publisher(RobotModeCommand, '/go2/robot_mode', 10)
        self._behavior_client = self.create_client(
            RobotBehaviorCommand, '/go2/robot_behavior_command'
        )
        self.create_subscription(WebRtcReq, '/sim_cmd', self._on_sim_cmd, 10)

        self.get_logger().info(
            'sim_cmd_node ready — publish go2_interfaces/msg/WebRtcReq to /sim_cmd'
        )

    def _on_sim_cmd(self, msg: WebRtcReq) -> None:
        api_id = msg.api_id
        parameter = msg.parameter.strip()

        if api_id in _API_TO_MODE:
            self._send_mode(_API_TO_MODE[api_id])

        elif api_id == 1011:  # SwitchGait — gait type in parameter
            gait = _GAIT_TYPE_MAP.get(parameter, 'TROT')
            self.get_logger().info(f'SwitchGait parameter="{parameter}" → {gait}')
            self._send_mode(gait)

        elif api_id in _API_TO_BEHAVIOR:
            self._call_behavior(_API_TO_BEHAVIOR[api_id], parameter)

        elif api_id in _NOT_IMPL:
            self.get_logger().warn(
                f"api_id {api_id} ({_NOT_IMPL[api_id]}) is hardware-only — "
                f"not implemented in simulation."
            )

        else:
            self.get_logger().warn(f"Unknown api_id: {api_id}")

    def _send_mode(self, mode: str) -> None:
        msg = RobotModeCommand()
        msg.mode = mode
        msg.robot_id = self._robot_id
        self._mode_pub.publish(msg)
        self.get_logger().info(f'Gait mode → {mode}')

    def _call_behavior(self, command: str, parameter: str = '') -> None:
        if not self._behavior_client.service_is_ready():
            self.get_logger().warn(
                f"Behavior service not immediately ready for '{command}' — waiting up to 5 s"
            )
            if not self._behavior_client.wait_for_service(timeout_sec=5.0):
                self.get_logger().error(
                    "/go2/robot_behavior_command unavailable after 5 s — "
                    "is robot_controller_gazebo running?"
                )
                return

        req = RobotBehaviorCommand.Request()
        req.command = command
        req.parameter = parameter

        future = self._behavior_client.call_async(req)
        future.add_done_callback(lambda f: self._on_behavior_response(command, f))

    def _on_behavior_response(self, command: str, future) -> None:
        try:
            result = future.result()
            if result.success:
                self.get_logger().info(f"'{command}': {result.message}")
            else:
                self.get_logger().warn(f"'{command}' failed: {result.message}")
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
