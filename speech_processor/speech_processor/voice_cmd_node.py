#!/usr/bin/env python3

# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

"""
Voice Command Node — translates /speech_text transcriptions into robot commands.

Subscribes to:
  /speech_text  (std_msgs/String)  — output of stt_node / mic_bridge_node

Publishes to:
  /webrtc_req    (go2_interfaces/WebRtcReq)  — hardware mode  (cmd_topic default)
  /sim_cmd       (go2_interfaces/WebRtcReq)  — simulation mode (set cmd_topic:=/sim_cmd)
  /cmd_vel_voice (geometry_msgs/Twist)       — movement commands → twist_mux
  /tts           (std_msgs/String)           — spoken feedback after every recognised command;
                                               for cloud NLU providers a conversational reply
                                               is spoken when no command is matched.

NLU providers
-------------
keyword (default): regex pattern matching, instant, fully offline
openai           : GPT-4o-mini structured output, handles free-form phrasing, needs OPENAI_API_KEY
gemini           : gemini-2.5-flash JSON output, handles free-form phrasing, needs GEMINI_API_KEY
claude           : claude-haiku-4-5, JSON output, handles free-form phrasing, needs ANTHROPIC_API_KEY
gemma_local      : Gemma 4 E4B via local llama.cpp sidecar (Windows GPU profile)

TTS feedback behaviour
----------------------
Command matched (any NLU provider) → speak the human-readable command name, e.g. "Sitting down".
No match + keyword provider       → silent (keyword has no conversational capability).
No match + cloud/local NLU        → ask the same model for a short conversational reply and
                                    speak it, so non-command speech gets a natural response.

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

import requests
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
    # ---- Movement (timed — auto-stops after move_duration seconds) ----
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

    # ---- Keep moving (no timeout — runs until stop_move) ----
    (r"\b(keep\s+(?:going|moving|walking)?\s*forward|keep\s+advancing|keep\s+going)\b",
     ("keep", 1.0, 0.0)),
    (r"\b(keep\s+(?:going|moving)?\s*back(?:ward)?|keep\s+reversing|keep\s+retreating)\b",
     ("keep", -1.0, 0.0)),
    (r"\b(keep\s+turning\s+left|keep\s+(?:going|moving)\s+left|keep\s+rotating\s+left)\b",
     ("keep", 0.0, 1.0)),
    (r"\b(keep\s+turning\s+right|keep\s+(?:going|moving)\s+right|keep\s+rotating\s+right)\b",
     ("keep", 0.0, -1.0)),

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
# Human-readable feedback strings keyed by (api_id, parameter) or api_id alone.
# Tuple keys take precedence over plain int keys in _feedback_for_action().
# ---------------------------------------------------------------------------

_FEEDBACK_MAP: dict = {
    # Posture
    1009: "Sitting down",
    1004: "Standing up",
    1002: "Balance stand",
    1006: "Recovery stand",
    1017: "Stretching",
    1003: "Stopping",
    # Gait (parameter distinguishes mode)
    (1011, "1"): "Switching to trot",
    (1011, "2"): "Switching to crawl",
    (1011, "3"): "Stand gait",
    (1011, "0"): "Rest gait",
    # Speed
    (1015, "0"): "Slowing down",
    (1015, "1"): "Normal speed",
    (1015, "2"): "Speeding up",
    # Body height
    (1013, "0.05"):  "Raising body",
    (1013, "-0.05"): "Lowering body",
    # Gestures
    1016: "Hello!",
    1022: "Let's dance",
    1023: "Dance two",
    1030: "Front flip",
    1033: "Wiggle",
    1036: "Finger heart",
    1301: "Handstand",
    1305: "Moon walk",
    (1019, "0"): "Continuous gait on",
    (1019, "1"): "Auto rest on",
}

_CONVERSATIONAL_SYSTEM = (
    "You are GO2, a Unitree quadruped robot assistant. "
    "Respond in 1–2 short sentences suitable for text-to-speech (no markdown, no lists). "
    "You can move, sit, stand, change gait, and perform gestures. "
    "If asked for something outside your physical abilities, say so politely."
)

_CONVERSATIONAL_SYSTEM_WITH_SEARCH = (
    "You are GO2, a Unitree quadruped robot assistant. "
    "Respond in 1–2 short sentences suitable for text-to-speech (no markdown, no lists). "
    "You can move, sit, stand, change gait, and perform gestures. "
    "Use the search_web tool when the question requires current information, "
    "news, weather, or facts you are not certain about."
)

# Tool definition in OpenAI / llama.cpp format
_SEARCH_TOOL_OPENAI = {
    "type": "function",
    "function": {
        "name": "search_web",
        "description": "Search the web for current events, weather, news, or factual questions.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"},
            },
            "required": ["query"],
        },
    },
}

# Anthropic format
_SEARCH_TOOL_CLAUDE = {
    "name": "search_web",
    "description": "Search the web for current events, weather, news, or factual questions.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query"},
        },
        "required": ["query"],
    },
}


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
  Movement (timed):    forward, backward, turn_left, turn_right, stop_move
  Movement (no timeout): keep_forward, keep_backward, keep_turn_left, keep_turn_right
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
    "keep_forward":     ("keep", 1.0, 0.0),
    "keep_backward":    ("keep", -1.0, 0.0),
    "keep_turn_left":   ("keep", 0.0, 1.0),
    "keep_turn_right":  ("keep", 0.0, -1.0),
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
        self.declare_parameter("llama_cpp_host", "http://llama_cpp:8080")
        self.declare_parameter("gemma_model", "gemma")
        self.declare_parameter("move_duration", 2.0)
        self.declare_parameter("linear_speed", 0.3)
        self.declare_parameter("angular_speed", 0.5)
        self.declare_parameter("enable_web_search", True)

        cmd_topic          = self.get_parameter("cmd_topic").value
        self._nlu          = self.get_parameter("nlu_provider").value
        self._api_key      = self.get_parameter("api_key").value
        self._llama_cpp_host = self.get_parameter("llama_cpp_host").value
        self._gemma_model    = self.get_parameter("gemma_model").value
        self._move_dur     = float(self.get_parameter("move_duration").value)
        self._lin_speed    = float(self.get_parameter("linear_speed").value)
        self._ang_speed    = float(self.get_parameter("angular_speed").value)
        self._enable_web_search = bool(self.get_parameter("enable_web_search").value)
        self._is_sim       = (cmd_topic == "/sim_cmd")

        self._cmd_pub = self.create_publisher(WebRtcReq, cmd_topic, 10)
        self._vel_pub = self.create_publisher(Twist, "/cmd_vel_voice", 10)
        self._tts_pub = self.create_publisher(String, "/tts", 10)
        self.create_subscription(String, "/speech_text", self._on_speech, 10)

        self._move_lock = threading.Lock()
        self._stop_timer: Optional[threading.Timer] = None
        self._current_twist: Optional[Twist] = None
        self._move_timer = self.create_timer(0.1, self._move_tick)  # 10 Hz sustain

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
        elif self._nlu == "gemma_local":
            self.get_logger().info(
                f"NLU: Gemma local ({self._gemma_model} via {self._llama_cpp_host})"
            )

        self.get_logger().info(
            f"voice_cmd_node ready — mode={'simulation' if self._is_sim else 'hardware'}, "
            f"cmd_topic={cmd_topic}, nlu={self._nlu}, "
            f"web_search={'on' if self._enable_web_search else 'off'}"
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
            if self._nlu != "keyword":
                reply = self._ask_conversational(text)
                if reply:
                    self.get_logger().info(f"Conversational reply: {reply!r}")
                    self._tts_pub.publish(String(data=reply))
            return

        self._execute(action, text)
        feedback = self._feedback_for_action(action)
        self.get_logger().info(f"TTS feedback: {feedback!r}")
        self._tts_pub.publish(String(data=feedback))

    # ------------------------------------------------------------------
    # TTS feedback helpers
    # ------------------------------------------------------------------

    def _feedback_for_action(self, action) -> str:
        if isinstance(action, tuple):
            kind = action[0]
            if kind in ("move", "keep"):
                _, lin, ang = action
                prefix = "Keep " if kind == "keep" else ""
                if ang == 0.0:
                    return f"{prefix}Moving {'forward' if lin > 0 else 'backward'}"
                return f"{prefix}Turning {'left' if ang > 0 else 'right'}"
            if kind == "stop_move":
                return "Stopping movement"
        if isinstance(action, dict):
            api_id = action.get("api_id")
            param  = action.get("parameter", "")
            return (
                _FEEDBACK_MAP.get((api_id, param))
                or _FEEDBACK_MAP.get(api_id)
                or "Command executed"
            )
        return "Command executed"

    def _web_search(self, query: str) -> str:
        """Return a short block of web search snippets. Requires duckduckgo-search."""
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=3))
            if not results:
                return "No results found."
            return "\n".join(
                f"{r.get('title', '')}: {r.get('body', '')}"
                for r in results if r.get("body")
            )
        except ImportError:
            self.get_logger().warn(
                "duckduckgo-search not installed — pip install duckduckgo-search"
            )
            return ""
        except Exception as exc:
            self.get_logger().error(f"Web search error: {exc}")
            return ""

    def _ask_conversational(self, text: str) -> str:
        system = (
            _CONVERSATIONAL_SYSTEM_WITH_SEARCH
            if self._enable_web_search
            else _CONVERSATIONAL_SYSTEM
        )
        try:
            if self._nlu == "openai" and self._openai_client:
                return self._conv_openai(text, system)
            if self._nlu == "gemini" and self._gemini_client:
                return self._conv_gemini(text, system)
            if self._nlu == "claude" and self._claude_client:
                return self._conv_claude(text, system)
            if self._nlu == "gemma_local":
                return self._conv_gemma_local(text, system)
        except Exception as exc:
            self.get_logger().error(f"Conversational NLU error: {exc}")
        return ""

    def _conv_openai(self, text: str, system: str) -> str:
        messages = [{"role": "system", "content": system},
                    {"role": "user",   "content": text}]
        kwargs: dict = {"model": "gpt-4o-mini", "messages": messages, "max_tokens": 120}
        if self._enable_web_search:
            kwargs["tools"] = [_SEARCH_TOOL_OPENAI]
        r = self._openai_client.chat.completions.create(**kwargs)
        # Tool-call loop (LLM decides when to search)
        while r.choices[0].finish_reason == "tool_calls":
            tc = r.choices[0].message.tool_calls[0]
            query = json.loads(tc.function.arguments).get("query", text)
            self.get_logger().info(f"Web search (openai): {query!r}")
            results = self._web_search(query)
            messages.append(r.choices[0].message)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": results or "No results found.",
            })
            r = self._openai_client.chat.completions.create(
                model="gpt-4o-mini", messages=messages, max_tokens=120
            )
        return r.choices[0].message.content.strip()

    def _conv_gemini(self, text: str, system: str) -> str:
        gt = self._genai_types
        config_kwargs: dict = {"system_instruction": system}
        if self._enable_web_search:
            config_kwargs["tools"] = [gt.Tool(function_declarations=[
                gt.FunctionDeclaration(
                    name="search_web",
                    description="Search the web for current or factual information.",
                    parameters=gt.Schema(
                        type=gt.Type.OBJECT,
                        properties={"query": gt.Schema(
                            type=gt.Type.STRING, description="The search query"
                        )},
                        required=["query"],
                    ),
                )
            ])]
        r = self._gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=text,
            config=gt.GenerateContentConfig(**config_kwargs),
        )
        # Check for function call in the response parts
        if self._enable_web_search and r.candidates:
            fc_part = next(
                (p for p in r.candidates[0].content.parts
                 if hasattr(p, "function_call") and p.function_call),
                None,
            )
            if fc_part:
                query = fc_part.function_call.args.get("query", text)
                self.get_logger().info(f"Web search (gemini): {query!r}")
                results = self._web_search(query)
                r2 = self._gemini_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        gt.Content(role="user", parts=[gt.Part(text=text)]),
                        r.candidates[0].content,
                        gt.Content(role="function", parts=[gt.Part(
                            function_response=gt.FunctionResponse(
                                name="search_web",
                                response={"result": results or "No results found."},
                            )
                        )]),
                    ],
                    config=gt.GenerateContentConfig(system_instruction=system),
                )
                return r2.text.strip() if r2.text else ""
        return r.text.strip() if r.text else ""

    def _conv_claude(self, text: str, system: str) -> str:
        tools = [_SEARCH_TOOL_CLAUDE] if self._enable_web_search else []
        kwargs: dict = {
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 120,
            "system": system,
            "messages": [{"role": "user", "content": text}],
        }
        if tools:
            kwargs["tools"] = tools
        m = self._claude_client.messages.create(**kwargs)
        if m.stop_reason == "tool_use":
            tb = next((b for b in m.content if b.type == "tool_use"), None)
            if tb:
                query = tb.input.get("query", text)
                self.get_logger().info(f"Web search (claude): {query!r}")
                results = self._web_search(query)
                m2 = self._claude_client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=120,
                    system=system,
                    tools=tools,
                    messages=[
                        {"role": "user",      "content": text},
                        {"role": "assistant", "content": m.content},
                        {"role": "user",      "content": [{
                            "type": "tool_result",
                            "tool_use_id": tb.id,
                            "content": results or "No results found.",
                        }]},
                    ],
                )
                return m2.content[0].text.strip()
        return m.content[0].text.strip()

    def _conv_gemma_local(self, text: str, system: str) -> str:
        messages = [{"role": "system", "content": system},
                    {"role": "user",   "content": text}]
        payload: dict = {
            "model": self._gemma_model,
            "messages": messages,
            "stream": False,
            "max_tokens": 120,
        }
        if self._enable_web_search:
            payload["tools"] = [_SEARCH_TOOL_OPENAI]
        resp = requests.post(
            f"{self._llama_cpp_host}/v1/chat/completions", json=payload, timeout=30
        )
        resp.raise_for_status()
        choice = resp.json()["choices"][0]
        if choice.get("finish_reason") == "tool_calls":
            tc = choice["message"]["tool_calls"][0]
            query = json.loads(tc["function"]["arguments"]).get("query", text)
            self.get_logger().info(f"Web search (gemma): {query!r}")
            results = self._web_search(query)
            messages.append(choice["message"])
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": results or "No results found.",
            })
            resp2 = requests.post(
                f"{self._llama_cpp_host}/v1/chat/completions",
                json={"model": self._gemma_model, "messages": messages,
                      "stream": False, "max_tokens": 120},
                timeout=30,
            )
            resp2.raise_for_status()
            return resp2.json()["choices"][0]["message"]["content"].strip()
        return choice["message"]["content"].strip()

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
        if self._nlu == "gemma_local":
            return self._parse_gemma_local(text)
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

    def _parse_gemma_local(self, text: str):
        try:
            resp = requests.post(
                f"{self._llama_cpp_host}/v1/chat/completions",
                json={
                    "model": self._gemma_model,
                    "messages": [
                        {"role": "system", "content": _OPENAI_SYSTEM_PROMPT},
                        {"role": "user",   "content": text},
                    ],
                    "stream": False,
                    "response_format": {"type": "json_object"},
                },
                timeout=30,
            )
            resp.raise_for_status()
            cmd = json.loads(resp.json()["choices"][0]["message"]["content"]).get("command", "unknown")
            if cmd == "unknown":
                return None
            action = _OPENAI_CMD_MAP.get(cmd)
            if action is None:
                self.get_logger().warn(f"Gemma local returned unknown command key: {cmd!r}")
            return action
        except Exception as exc:
            self.get_logger().error(f"Gemma local NLU error: {exc} — falling back to keyword")
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
        elif action[0] == "keep":
            _, lin, ang = action
            self._send_keep_move(lin, ang)
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

    def _move_tick(self) -> None:
        with self._move_lock:
            twist = self._current_twist
        if twist is not None:
            self._vel_pub.publish(twist)

    def _send_move(self, linear_x: float, angular_z: float) -> None:
        twist = Twist()
        twist.linear.x = linear_x * self._lin_speed
        twist.angular.z = angular_z * self._ang_speed
        self.get_logger().info(
            f"Move command: linear.x={twist.linear.x:.2f} angular.z={twist.angular.z:.2f}, "
            f"duration={self._move_dur:.1f}s"
        )
        with self._move_lock:
            self._cancel_stop_timer()
            self._current_twist = twist
            self._stop_timer = threading.Timer(self._move_dur, self._stop_timer_cb)
            self._stop_timer.daemon = True
            self._stop_timer.start()

    def _send_keep_move(self, linear_x: float, angular_z: float) -> None:
        twist = Twist()
        twist.linear.x = linear_x * self._lin_speed
        twist.angular.z = angular_z * self._ang_speed
        self.get_logger().info(
            f"Keep move: linear.x={twist.linear.x:.2f} angular.z={twist.angular.z:.2f} (no timeout — say 'stop moving' to halt)"
        )
        with self._move_lock:
            self._cancel_stop_timer()
            self._current_twist = twist

    def _send_stop_move(self) -> None:
        with self._move_lock:
            self._cancel_stop_timer()
            self._current_twist = None
        self._vel_pub.publish(Twist())
        self.get_logger().info("Stop move: zero velocity published")

    # ------------------------------------------------------------------
    # Auto-stop timer for movement commands
    # ------------------------------------------------------------------

    def _cancel_stop_timer(self) -> None:
        if self._stop_timer is not None:
            self._stop_timer.cancel()
            self._stop_timer = None

    def _stop_timer_cb(self) -> None:
        with self._move_lock:
            self._stop_timer = None
            self._current_twist = None
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
