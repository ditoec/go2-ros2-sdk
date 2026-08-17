# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

"""
CycloneDDS command adapter.

Publishes robot commands to /api/sport/request (Unitree sport-mode API) when
CONN_TYPE=cyclonedds.  Implements the same IRobotController interface as
WebRTCAdapter so the rest of the stack is unchanged.

Topic layout (matches the official unitree_ros2 cyclonedds_ws):
  /api/sport/request     (unitree_api/Request)   — sport-mode API commands
  /api/sport/response    (unitree_api/Response)  — sport-mode API responses (subscribed)
  /api/audiohub/request  (unitree_api/Request)   — TTS playback commands (tts_node.py)
  /api/audiohub/response (unitree_api/Response)  — audiohub API responses (subscribed)

Two more robot-native DDS topics exist in this same audio family:
  /audiohub/player/state — the robot's own playback-state broadcast. WebRTC
    mode now consumes it: RobotDataService.process_webrtc_message() has an
    elif branch for RTC_TOPIC["AUDIO_HUB_PLAY_STATE"]
    (domain/constants/webrtc_topics.py) that republishes it (passthrough,
    schema not confirmed) to the SDK-level /audiohub_player_state topic,
    which tts_node.py subscribes to for a real completion signal instead of
    a guessed sleep. CycloneDDS mode does NOT subscribe to the real
    /audiohub/player/state DDS topic yet -- its message type has not been
    confirmed against hardware (ros2 topic info -v /audiohub/player/state,
    once the robot is reachable), and guessing wrong here would repeat the
    unitree_go-vs-unitree_api type-mismatch class of bug this file already
    fixed once for /api/sport/request. Until that subscription exists,
    tts_node.py's timing-based fallback is what actually runs in
    CycloneDDS mode -- functionally fine (same wait ceiling as before, just
    non-blocking now), just not the real signal yet.
  /audioreceiver (unused) — presumably the raw-audio mirror of /audiosender
    (unitree_go/AudioData; robot mic is /audiosender, so /audioreceiver would
    be client→robot raw audio into the speaker). This SDK's TTS pipeline
    doesn't use it -- _play_on_robot() streams base64 WAV chunks through the
    audiohub Request/Response command channel instead (see tts_node.py).
    Not confirmed against hardware; listed here so it isn't mistaken for
    already-integrated.

audiohub (request/response) is a second, separate native DDS topic, not a
logical sub-channel of sport/request: confirmed live that /api/audiohub/request exists as its
own topic with 3 native robot-side publishers and 1 native subscriber, all
unitree_api/msg/Request, distinct from /api/sport/request's 10
publishers/1 subscriber. tts_node.py's _send_audio_command() already sets
req.topic = "rt/api/audiohub/request" (the WebRTC-style RTC topic string)
on every WebRtcReq it sends, but that field is a data-channel multiplexing
artifact with no DDS meaning on its own -- earlier versions of this adapter
only ever had one publisher (hardcoded to /api/sport/request), so TTS audio
commands were being physically published to the wrong DDS topic entirely
regardless of message type. _publish() now reads the same field to pick
the matching real publisher.

Request/Response come from unitree_api, not unitree_go's Req/Res (an earlier
version of this file used unitree_go/Req+Res, which fixed the DDS type-name
collision against go2_interfaces but turned out to still be the wrong type):
confirmed live on hardware that /api/sport/request has 10 publishers and
exactly 1 subscriber, and that lone subscriber -- the actual command
receiver on the robot -- is typed unitree_api/msg/Request, not
unitree_go/msg/Req. Every one of the 9 native robot-side publishers on that
topic also uses unitree_api/msg/Request. unitree_go/Req+Res (uuid + body
string) is a simpler, apparently-unused legacy schema; unitree_api/Request+
Response (nested header.identity.{id,api_id}, header.lease.id,
header.policy.{priority,noreply}, parameter, binary) is what the robot's
command processor and every other onboard service actually speak.

create_command_structure() (application/utils/command_generator.py) already
builds this exact header/identity/parameter shape as a plain dict (it was
written to mirror the WebRTC wire format, which turns out to be structurally
identical) -- _publish() below just copies those fields onto the real
unitree_api.msg.Request instead of re-serializing them into a flat string.
"""

import logging
from typing import Any, Optional

from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy

from unitree_api.msg import Request, Response

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
    _API_SWITCH_GAIT = 1011   # SwitchGait -- parameter '1' = TROT (matches
                               # the CLAUDE.md-documented /sim_cmd example:
                               # "api_id: 1011, parameter: '1'  # TROT")

    # RTC-style topic string (as embedded by tts_node.py / command_generator.py)
    # -> (request DDS topic, response DDS topic), for anything other than
    # plain sport-mode commands. Sport-mode itself isn't listed here; it's
    # the fallback in _publish() below.
    _AUDIOHUB_RTC_TOPIC = "rt/api/audiohub/request"
    _TOPIC_ROUTES = {
        _AUDIOHUB_RTC_TOPIC: ("/api/audiohub/request", "/api/audiohub/response"),
    }

    # Matches the native robot-side publishers observed live on
    # /api/sport/request (RELIABLE, KEEP_LAST(1)). A RELIABLE publisher is
    # compatible with the real subscriber's BEST_EFFORT QoS either way.
    _PUB_QOS = QoSProfile(
        reliability=QoSReliabilityPolicy.RELIABLE,
        history=QoSHistoryPolicy.KEEP_LAST,
        depth=10,
    )
    # BEST_EFFORT so this is compatible regardless of whether the robot's
    # response publisher turns out RELIABLE or BEST_EFFORT (a BEST_EFFORT
    # subscriber accepts either; a RELIABLE one would only accept RELIABLE).
    _SUB_QOS = QoSProfile(
        reliability=QoSReliabilityPolicy.BEST_EFFORT,
        history=QoSHistoryPolicy.KEEP_LAST,
        depth=10,
    )

    def __init__(self, node: Node, config: RobotConfig):
        self._node   = node
        self._config = config

        # Publisher: /api/sport/request
        self._sport_pub = node.create_publisher(Request, '/api/sport/request', self._PUB_QOS)

        # Subscriber: /api/sport/response (log errors / async replies)
        self._sport_sub = node.create_subscription(
            Response, '/api/sport/response', self._on_sport_response, self._SUB_QOS
        )

        # Extra publishers/subscribers for non-sport-mode DDS topics (see
        # _TOPIC_ROUTES and the module docstring) -- keyed by the same
        # RTC-style topic string _publish() looks up.
        self._extra_pubs = {}
        for rtc_topic, (req_topic, resp_topic) in self._TOPIC_ROUTES.items():
            self._extra_pubs[rtc_topic] = node.create_publisher(Request, req_topic, self._PUB_QOS)
            node.create_subscription(Response, resp_topic, self._on_sport_response, self._SUB_QOS)

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
        # StandUp alone leaves the robot in mode=0/gait_type=0 -- a static
        # standing lock (Unitree's own docs: "the motor joint remains
        # locked"), not the active balance-control loop MoveCmd needs
        # ("unlock the joint motor... switch to balanced standing mode").
        # Confirmed live: MoveCmd got Response.header.status.code=0 (request
        # accepted/routed) on every tick sent after a bare StandUp, but the
        # robot never physically moved and /sportmodestate.error_code read
        # 1002 the whole time. Chaining BalanceStand onto StandUp mirrors
        # webrtc_adapter.py's send_stand_up_command() exactly (it has always
        # sent this pair).
        #
        # BalanceStand alone still wasn't consistently enough: MoveCmd
        # worked immediately after one manual StandUp test, then failed
        # again after a scripted Sit->StandUp->Move chain a few seconds
        # later -- confirmed by direct operator observation that the robot
        # visibly locks after standing and needs an explicit gait selection
        # before it will walk. SwitchGait (api_id 1011, parameter "1" =
        # TROT -- the same api_id/parameter this repo's own CLAUDE.md
        # already documents for /sim_cmd) is sent last to actually enter
        # locomotion mode.
        self._publish_api(self._API_STAND)
        self._publish_api(self._API_BALANCE)
        self._publish_api(self._API_SWITCH_GAIT, "1")

    def send_stand_down_command(self, robot_id: str) -> None:
        self._publish_api(self._API_SIT)

    def send_webrtc_request(
        self, robot_id: str, api_id: int, parameter: Any, topic: str
    ) -> None:
        """Route a generic WebRtcReq to the sport-mode API topic."""
        # send_stand_up_command()/send_stand_down_command() are the only
        # IRobotController entry points reachable from /joy button presses
        # (robot_control_service.py's handle_joy_command()) -- every other
        # command source in this codebase (voice commands via
        # command_dispatcher.py, the CLAUDE.md-documented
        # `ros2 topic pub /webrtc_req ...` manual test pattern, Foxglove,
        # any external tool) goes through handle_webrtc_request() instead,
        # which always called straight through to this generic passthrough
        # with no equivalent chaining. That meant the BalanceStand+SwitchGait
        # fix in send_stand_up_command() only ever fired for joystick input.
        # Delegating here instead makes every entry path converge on the
        # same corrected behavior.
        if api_id == self._API_STAND:
            self.send_stand_up_command(robot_id)
            return
        if api_id == self._API_SIT:
            self.send_stand_down_command(robot_id)
            return

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
        # command_dict is create_command_structure()'s
        # {"type", "topic", "data": {"header": {"identity": {"id", "api_id"}}, "parameter"}}
        # -- "type" is a WebRTC data-channel multiplexing artifact with no
        # DDS equivalent; "data" maps onto the real unitree_api.msg.Request
        # wire fields. The top-level "topic" *does* still matter here (unlike
        # "type"): it's how tts_node.py (and anything else routing through
        # send_webrtc_request()) marks a command for a non-sport-mode DDS
        # topic -- see _TOPIC_ROUTES and the module docstring.
        data = command_dict["data"]
        identity = data["header"]["identity"]

        req = Request()
        req.header.identity.id = int(identity["id"])
        req.header.identity.api_id = int(identity["api_id"])
        req.header.lease.id = 0
        req.header.policy.priority = 0
        req.header.policy.noreply = False
        req.parameter = data.get("parameter", "")

        pub = self._extra_pubs.get(command_dict.get("topic"), self._sport_pub)
        pub.publish(req)
        logger.debug(
            f"CycloneDDS published: api_id={req.header.identity.api_id} "
            f"parameter={req.parameter[:120]}"
        )

    def _on_sport_response(self, msg: Response) -> None:
        """Log non-zero response codes from the sport-mode API."""
        code = msg.header.status.code
        if code != 0:
            logger.warning(
                f"Sport API response code {code} "
                f"(api_id={msg.header.identity.api_id}): {msg.data[:200]}"
            )
