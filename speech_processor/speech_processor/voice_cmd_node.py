#!/usr/bin/env python3

# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

"""
Voice Command Node — translates /speech_text transcriptions into robot commands.

Subscribes to:
  /speech_text  (std_msgs/String)  — output of stt_node

Publishes to:
  /webrtc_req   (go2_interfaces/WebRtcReq)   — hardware mode  (cmd_topic default)
  /sim_cmd      (go2_interfaces/WebRtcReq)   — simulation mode (set cmd_topic:=/sim_cmd)
  /cmd_vel_voice (geometry_msgs/Twist)        — movement commands → twist_mux

NLU providers
-------------
keyword (default): regex pattern matching, instant, fully offline
openai           : GPT-4o-mini structured output, handles free-form phrasing, needs OPENAI_API_KEY
gemini           : gemini-2.0-flash JSON output, handles free-form phrasing, needs GEMINI_API_KEY
claude           : claude-haiku-4-5, JSON output, handles free-form phrasing, needs ANTHROPIC_API_KEY

Mode selection
--------------
Pass cmd_topic:=/webrtc_req  for hardware (default)
Pass cmd_topic:=/sim_cmd     for simulation

Hardware-only commands (Hello, Dance, FrontFlip, …) are skipped in sim mode with a warning.
"""

import json
import re
import threading
from typing import Optional

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import Twist
from go2_interfaces.msg import WebRtcReq


# ---------------------------------------------------------------------------
# Command table — each entry: (regex_pattern, action)
# action is one of:
#   {"api_id": int, "parameter": str}   → robot state/gait/posture
#   ("move", linear_x, angular_z)       → velocity command (unit speed, scaled by params)
#   ("stop_move",)                       → zero velocity
#   {"api_id": int, "hw_only": True}    → hardware-only, skipped in simulation
# ---------------------------------------------------------------------------

_CMD_TABLE = [
    # ---- Movement ----
    (r"\b(go\s+forward|move\s+forward|walk\s+forward|forward|advance|proceed)\b",
     ("move", 1.0, 0.0)),
    (r"\b(go\s+back(?:ward)?|move\s+back(?:ward)?|reverse|back\s+up|retreat)\b",
     ("move", -1.0, 0.0)),
    (r"\b(turn\s+left|rotate\s+left|spin\s+left|go\s+left)\b",
     ("move", 0.0, 1.0)),
    (r"\b(turn\s+right|rotate\s+right|spin\s+right|go\s+right)\b",
     ("move", 0.0, -1.0)),
    (r"\b(stop\s+moving|stop\s+walking|stop\s+walk|halt\s+move|cease\s+move)\b",
     ("stop_move",)),

    # ---- Posture ----
    (r"\b(sit|sit\s+down|lie\s+down|squat)\b",
     {"api_id": 1009, "parameter": ""}),
    (r"\b(stand\s+up|stand|get\s+up|rise|standup)\b",
     {"api_id": 1004, "parameter": ""}),
    (r"\b(balance|balance\s+stand|balance\s+mode)\b",
     {"api_id": 1002, "parameter": ""}),
    (r"\b(recover|recovery|recovery\s+stand|get\s+ready)\b",
     {"api_id": 1006, "parameter": ""}),
    (r"\b(stretch|stretch\s+out)\b",
     {"api_id": 1017, "parameter": ""}),
    (r"\b(stop|halt|freeze|cease|stop\s+all)\b",
     {"api_id": 1003, "parameter": ""}),

    # ---- Gait ----
    (r"\b(trot|jogging|jog|trot\s+mode|walk\s+mode|start\s+trot)\b",
     {"api_id": 1011, "parameter": "1"}),
    (r"\b(crawl|crawl\s+mode|slow\s+gait|creep)\b",
     {"api_id": 1011, "parameter": "2"}),
    (r"\b(stand\s+gait|stand\s+mode|static\s+stand)\b",
     {"api_id": 1011, "parameter": "3"}),
    (r"\b(rest\s+gait|rest\s+mode)\b",
     {"api_id": 1011, "parameter": "0"}),

    # ---- Speed ----
    (r"\b(slow\s+down|slow\s+speed|go\s+slow|slow)\b",
     {"api_id": 1015, "parameter": "0"}),
    (r"\b(normal\s+speed|medium\s+speed|regular\s+speed|default\s+speed)\b",
     {"api_id": 1015, "parameter": "1"}),
    (r"\b(speed\s+up|fast|full\s+speed|go\s+fast|fast\s+speed)\b",
     {"api_id": 1015, "parameter": "2"}),

    # ---- Body height ----
    (r"\b(raise\s+body|higher|raise\s+up|lift\s+body|go\s+higher)\b",
     {"api_id": 1013, "parameter": "0.05"}),
    (r"\b(lower\s+body|lower|duck|go\s+lower|crouch)\b",
     {"api_id": 1013, "parameter": "-0.05"}),

    # ---- Hardware-only gestures ----
    (r"\b(hello|wave|hi|greet|wave\s+hello)\b",
     {"api_id": 1016, "parameter": "", "hw_only": True}),
    (r"\b(dance|dance\s+one|first\s+dance)\b",
     {"api_id": 1022, "parameter": "", "hw_only": True}),
    (r"\b(dance\s+two|second\s+dance)\b",
     {"api_id": 1023, "parameter": "", "hw_only": True}),
    (r"\b(front\s+flip|flip)\b",
     {"api_id": 1030, "parameter": "", "hw_only": True}),
    (r"\b(wiggle|wiggle\s+hips)\b",
     {"api_id": 1033, "parameter": "", "hw_only": True}),
    (r"\b(finger\s+heart|heart)\b",
     {"api_id": 1036, "parameter": "", "hw_only": True}),
    (r"\b(handstand)\b",
     {"api_id": 1301, "parameter": "", "hw_only": True}),
    (r"\b(moon\s*walk)\b",
     {"api_id": 1305, "parameter": "", "hw_only": True}),
    (r"\b(continuous\s+gait|always\s+trot|keep\s+trotting)\b",
     {"api_id": 1019, "parameter": "0", "hw_only": True}),
    (r"\b(auto\s+rest|auto\s+stop)\b",
     {"api_id": 1019, "parameter": "1", "hw_only": True}),
]

# Pre-compile patterns once at import time
_COMPILED_TABLE = [(re.compile(pat, re.IGNORECASE), action) for pat, action in _CMD_TABLE]


# ---------------------------------------------------------------------------
# OpenAI NLU helper
# ---------------------------------------------------------------------------

_OPENAI_SYSTEM_PROMPT = """
You are a command parser for a quadruped robot (Unitree GO2).
Parse the user's speech and return ONLY a JSON object with no extra text.

Available commands:
  State/posture: sit, stand, balance, stretch, recover, stop, raise_body, lower_body
  Gait:          trot, crawl, stand_gait, rest_gait
  Speed:         slow_speed, normal_speed, fast_speed
  Movement:      forward, backward, turn_left, turn_right, stop_move
  Gestures (hardware only): hello, dance1, dance2, front_flip, wiggle_hips, finger_heart,
                             handstand, moon_walk, continuous_gait, auto_rest

Return format: {"command": "<one of the above>"}
If no command is recognizable, return: {"command": "unknown"}
""".strip()

_OPENAI_CMD_MAP = {
    "sit":              {"api_id": 1009, "parameter": ""},
    "stand":            {"api_id": 1004, "parameter": ""},
    "balance":          {"api_id": 1002, "parameter": ""},
    "stretch":          {"api_id": 1017, "parameter": ""},
    "recover":          {"api_id": 1006, "parameter": ""},
    "stop":             {"api_id": 1003, "parameter": ""},
    "raise_body":       {"api_id": 1013, "parameter": "0.05"},
    "lower_body":       {"api_id": 1013, "parameter": "-0.05"},
    "trot":             {"api_id": 1011, "parameter": "1"},
    "crawl":            {"api_id": 1011, "parameter": "2"},
    "stand_gait":       {"api_id": 1011, "parameter": "3"},
    "rest_gait":        {"api_id": 1011, "parameter": "0"},
    "slow_speed":       {"api_id": 1015, "parameter": "0"},
    "normal_speed":     {"api_id": 1015, "parameter": "1"},
    "fast_speed":       {"api_id": 1015, "parameter": "2"},
    "forward":          ("move", 1.0, 0.0),
    "backward":         ("move", -1.0, 0.0),
    "turn_left":        ("move", 0.0, 1.0),
    "turn_right":       ("move", 0.0, -1.0),
    "stop_move":        ("stop_move",),
    "hello":            {"api_id": 1016, "parameter": "", "hw_only": True},
    "dance1":           {"api_id": 1022, "parameter": "", "hw_only": True},
    "dance2":           {"api_id": 1023, "parameter": "", "hw_only": True},
    "front_flip":       {"api_id": 1030, "parameter": "", "hw_only": True},
    "wiggle_hips":      {"api_id": 1033, "parameter": "", "hw_only": True},
    "finger_heart":     {"api_id": 1036, "parameter": "", "hw_only": True},
    "handstand":        {"api_id": 1301, "parameter": "", "hw_only": True},
    "moon_walk":        {"api_id": 1305, "parameter": "", "hw_only": True},
    "continuous_gait":  {"api_id": 1019, "parameter": "0", "hw_only": True},
    "auto_rest":        {"api_id": 1019, "parameter": "1", "hw_only": True},
}


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class VoiceCmdNode(Node):

    def __init__(self):
        super().__init__("voice_cmd_node")

        self.declare_parameter("cmd_topic", "/webrtc_req")
        self.declare_parameter("nlu_provider", "keyword")
        self.declare_parameter("api_key", "")
        self.declare_parameter("move_duration", 2.0)
        self.declare_parameter("linear_speed", 0.3)
        self.declare_parameter("angular_speed", 0.5)

        cmd_topic          = self.get_parameter("cmd_topic").value
        self._nlu          = self.get_parameter("nlu_provider").value
        self._api_key      = self.get_parameter("api_key").value
        self._move_dur     = float(self.get_parameter("move_duration").value)
        self._lin_speed    = float(self.get_parameter("linear_speed").value)
        self._ang_speed    = float(self.get_parameter("angular_speed").value)
        self._is_sim       = (cmd_topic == "/sim_cmd")

        self._cmd_pub = self.create_publisher(WebRtcReq, cmd_topic, 10)
        self._vel_pub = self.create_publisher(Twist, "/cmd_vel_voice", 10)
        self.create_subscription(String, "/speech_text", self._on_speech, 10)

        self._move_lock = threading.Lock()
        self._stop_timer: Optional[threading.Timer] = None

        self._openai_client = None
        self._gemini_client = None
        self._claude_client = None

        if self._nlu == "openai":
            try:
                import openai
                self._openai_client = openai.OpenAI(api_key=self._api_key)
            except ImportError:
                self.get_logger().warn("openai not installed — falling back to keyword NLU")
                self._nlu = "keyword"
        elif self._nlu == "gemini":
            try:
                from google import genai
                from google.genai import types as genai_types
                self._gemini_client = genai.Client(api_key=self._api_key)
                self._genai_types = genai_types
            except ImportError:
                self.get_logger().warn("google-genai not installed — falling back to keyword NLU")
                self._nlu = "keyword"
        elif self._nlu == "claude":
            try:
                import anthropic
                self._claude_client = anthropic.Anthropic(api_key=self._api_key)
            except ImportError:
                self.get_logger().warn("anthropic not installed — falling back to keyword NLU")
                self._nlu = "keyword"

        self.get_logger().info(
            f"voice_cmd_node ready — mode={'simulation' if self._is_sim else 'hardware'}, "
            f"cmd_topic={cmd_topic}, nlu={self._nlu}"
        )

    # ------------------------------------------------------------------
    # Speech callback
    # ------------------------------------------------------------------

    def _on_speech(self, msg: String) -> None:
        text = msg.data.strip()
        if not text:
            return
        self.get_logger().info(f"Voice input: {text!r}")

        action = self._parse(text)
        if action is None:
            self.get_logger().info(f"No command matched for: {text!r}")
            return

        self._execute(action, text)

    # ------------------------------------------------------------------
    # NLU
    # ------------------------------------------------------------------

    def _parse(self, text: str):
        if self._nlu == "openai" and self._openai_client:
            return self._parse_openai(text)
        if self._nlu == "gemini" and self._gemini_client:
            return self._parse_gemini(text)
        if self._nlu == "claude" and self._claude_client:
            return self._parse_claude(text)
        return self._parse_keyword(text)

    def _parse_keyword(self, text: str):
        for pattern, action in _COMPILED_TABLE:
            if pattern.search(text):
                return action
        return None

    def _parse_openai(self, text: str):
        try:
            response = self._openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": _OPENAI_SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                response_format={"type": "json_object"},
                max_tokens=30,
            )
            raw = response.choices[0].message.content
            cmd = json.loads(raw).get("command", "unknown")
            if cmd == "unknown":
                return None
            action = _OPENAI_CMD_MAP.get(cmd)
            if action is None:
                self.get_logger().warn(f"OpenAI returned unknown command key: {cmd!r}")
            return action
        except Exception as exc:
            self.get_logger().error(f"OpenAI NLU error: {exc} — falling back to keyword")
            return self._parse_keyword(text)

    def _parse_gemini(self, text: str):
        try:
            response = self._gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"{_OPENAI_SYSTEM_PROMPT}\n\nUser speech: {text}",
                config=self._genai_types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            cmd = json.loads(response.text).get("command", "unknown")
            if cmd == "unknown":
                return None
            action = _OPENAI_CMD_MAP.get(cmd)
            if action is None:
                self.get_logger().warn(f"Gemini returned unknown command key: {cmd!r}")
            return action
        except Exception as exc:
            self.get_logger().error(f"Gemini NLU error: {exc} — falling back to keyword")
            return self._parse_keyword(text)

    def _parse_claude(self, text: str):
        try:
            message = self._claude_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=50,
                system=_OPENAI_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": text}],
            )
            raw = message.content[0].text.strip()
            cmd = json.loads(raw).get("command", "unknown")
            if cmd == "unknown":
                return None
            action = _OPENAI_CMD_MAP.get(cmd)
            if action is None:
                self.get_logger().warn(f"Claude returned unknown command key: {cmd!r}")
            return action
        except Exception as exc:
            self.get_logger().error(f"Claude NLU error: {exc} — falling back to keyword")
            return self._parse_keyword(text)

    # ------------------------------------------------------------------
    # Command execution
    # ------------------------------------------------------------------

    def _execute(self, action, text: str) -> None:
        if isinstance(action, dict):
            self._send_robot_cmd(action, text)
        elif action[0] == "move":
            _, lin, ang = action
            self._send_move(lin, ang)
        elif action[0] == "stop_move":
            self._send_stop_move()

    def _send_robot_cmd(self, action: dict, text: str) -> None:
        if action.get("hw_only") and self._is_sim:
            self.get_logger().warn(
                f"Command api_id={action['api_id']} is hardware-only and is skipped in simulation. "
                f"(Triggered by: {text!r})"
            )
            return

        req = WebRtcReq()
        req.api_id = action["api_id"]
        req.parameter = action.get("parameter", "")
        req.priority = 0
        self._cmd_pub.publish(req)
        self.get_logger().info(
            f"Robot command sent: api_id={req.api_id} parameter={req.parameter!r}"
        )

    def _send_move(self, linear_x: float, angular_z: float) -> None:
        twist = Twist()
        twist.linear.x = linear_x * self._lin_speed
        twist.angular.z = angular_z * self._ang_speed
        self._vel_pub.publish(twist)
        self.get_logger().info(
            f"Move command: linear.x={twist.linear.x:.2f} angular.z={twist.angular.z:.2f}, "
            f"duration={self._move_dur:.1f}s"
        )
        self._arm_stop_timer()

    def _send_stop_move(self) -> None:
        self._cancel_stop_timer()
        self._vel_pub.publish(Twist())
        self.get_logger().info("Stop move: zero velocity published")

    # ------------------------------------------------------------------
    # Auto-stop timer for movement commands
    # ------------------------------------------------------------------

    def _arm_stop_timer(self) -> None:
        with self._move_lock:
            self._cancel_stop_timer()
            self._stop_timer = threading.Timer(self._move_dur, self._stop_timer_cb)
            self._stop_timer.daemon = True
            self._stop_timer.start()

    def _cancel_stop_timer(self) -> None:
        if self._stop_timer is not None:
            self._stop_timer.cancel()
            self._stop_timer = None

    def _stop_timer_cb(self) -> None:
        self._vel_pub.publish(Twist())
        self.get_logger().info("Move duration elapsed — zero velocity published")


def main(args=None):
    rclpy.init(args=args)
    node = VoiceCmdNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
