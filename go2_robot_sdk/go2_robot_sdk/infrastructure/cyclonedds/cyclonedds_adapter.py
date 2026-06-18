# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

"""
CycloneDDS command adapter.

Publishes robot commands to /api/sport/request (Unitree sport-mode API) when
CONN_TYPE=cyclonedds.  Implements the same IRobotController interface as
WebRTCAdapter so the rest of the stack is unchanged.

Topic layout (matches the official unitree_ros2 cyclonedds_ws):
  /api/sport/request  (go2_interfaces/Req)  — sport-mode API commands
  /api/sport/response (go2_interfaces/Res)  — sport-mode API responses (subscribed)

The Req.body field carries a JSON string with the Unitree identity/parameter
structure, identical to what WebRTC sends over the data channel.
"""

import json
import logging
from typing import Any, Optional

from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy

from go2_interfaces.msg import Req, Res

from ...domain.interfaces import IRobotController
from ...domain.entities import RobotConfig
from ...application.utils.command_generator import (
    gen_command, gen_mov_command, generate_id, create_command_structure,
    SPORT_MODE_TOPIC, OBSTACLE_AVOIDANCE_TOPIC,
)

logger = logging.getLogger(__name__)


class CycloneDDSAdapter(IRobotController):
    """
    Routes robot commands via CycloneDDS topics instead of the WebRTC data channel.

    One adapter is shared for all robots in single mode; in multi mode the
    caller passes the robot_id to the appropriate API namespaced topic.
    """

    # Unitree sport-mode API IDs used for movement / posture commands
    _API_MOVE     = 1008   # MoveCmd: {"x": vx, "y": vy, "z": vyaw}
    _API_STAND    = 1004   # StandUp
    _API_SIT      = 1009   # StandDown / Sit
    _API_BALANCE  = 1002   # BalanceStand
    _API_STOP     = 1003   # StopMove

    _QOS = QoSProfile(
        reliability=QoSReliabilityPolicy.RELIABLE,
        history=QoSHistoryPolicy.KEEP_LAST,
        depth=10,
    )

    def __init__(self, node: Node, config: RobotConfig):
        self._node   = node
        self._config = config

        # Publisher: /api/sport/request
        self._sport_pub = node.create_publisher(Req, '/api/sport/request', self._QOS)

        # Subscriber: /api/sport/response (log errors / async replies)
        self._sport_sub = node.create_subscription(
            Res, '/api/sport/response', self._on_sport_response, self._QOS
        )

        logger.info("CycloneDDSAdapter ready — publishing to /api/sport/request")

    # ------------------------------------------------------------------
    # IRobotController implementation
    # ------------------------------------------------------------------

    def send_movement_command(self, robot_id: str, x: float, y: float, z: float) -> None:
        """Publish a velocity command (vx, vy, vyaw)."""
        body = create_command_structure(
            api_id=self._API_MOVE,
            parameter={"x": round(x, 3), "y": round(y, 3), "z": round(z, 3)},
            topic=SPORT_MODE_TOPIC,
        )
        self._publish(body)

    def send_stand_up_command(self, robot_id: str) -> None:
        self._publish_api(self._API_STAND)

    def send_stand_down_command(self, robot_id: str) -> None:
        self._publish_api(self._API_SIT)

    def send_webrtc_request(
        self, robot_id: str, api_id: int, parameter: Any, topic: str
    ) -> None:
        """Route a generic WebRtcReq to the sport-mode API topic."""
        body = create_command_structure(
            api_id=api_id,
            parameter=parameter if parameter is not None else str(api_id),
            topic=topic or SPORT_MODE_TOPIC,
        )
        self._publish(body)

    def set_obstacle_avoidance(self, enabled: bool, robot_id: str) -> None:
        """Enable / disable obstacle avoidance mode (no-op in basic sport mode)."""
        logger.info(
            f"CycloneDDS: obstacle_avoidance={'on' if enabled else 'off'} "
            f"(not supported in basic sport-mode API)"
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _publish_api(self, api_id: int, parameter: str = "") -> None:
        body = create_command_structure(
            api_id=api_id, parameter=parameter, topic=SPORT_MODE_TOPIC
        )
        self._publish(body)

    def _publish(self, command_dict: dict) -> None:
        msg = Req()
        msg.uuid = str(generate_id())
        # The Req.body holds the JSON of the command's "data" sub-object —
        # the same payload that WebRTC sends inside {"type":"msg","topic":..,"data":{..}}
        msg.body = json.dumps(command_dict.get("data", command_dict))
        self._sport_pub.publish(msg)
        logger.debug(f"CycloneDDS published: {msg.body[:120]}")

    def _on_sport_response(self, msg: Res) -> None:
        """Log non-zero response codes from the sport-mode API."""
        if msg.body:
            try:
                resp = json.loads(msg.body)
                code = resp.get("header", {}).get("status", {}).get("code", 0)
                if code != 0:
                    logger.warning(f"Sport API response code {code}: {msg.body[:200]}")
            except Exception:
                pass
