#!/usr/bin/env python3

# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

"""
Shared command dispatch logic for mic_bridge_node and voice_cmd_node.

Provides:
  CMD_MAP              — command name → action (used by unified LLM backends)
  FEEDBACK_MAP         — api_id / (api_id, param) → human-readable string
  ROBOT_CMD_SYSTEM_PROMPT — NLU system prompt (shared across all LLM providers)
  CONVERSATIONAL_SYSTEM   — conversational fallback system prompt
  feedback_for_action(action) → str
  CommandDispatcher    — stateful executor: holds publishers + movement timer
"""

import re
import threading
from typing import Optional

from geometry_msgs.msg import Twist
from go2_interfaces.msg import WebRtcReq
from std_msgs.msg import String


# ---------------------------------------------------------------------------
# Command map — name → action understood by CommandDispatcher.execute()
# ---------------------------------------------------------------------------

CMD_MAP: dict = {
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
# Supported languages
#
# The pipeline runs in ONE language at a time, selected at launch via the
# VOICE_LANG env var (en | id) and threaded into every backend's `language`
# parameter.  language_name() turns the code into a word for prompts; unknown
# codes pass through unchanged (e.g. a future "de" still reads "de").
# ---------------------------------------------------------------------------

LANG_NAME: dict = {"en": "English", "id": "Indonesian"}


def language_name(code: str) -> str:
    """Human-readable language name for a code; returns the code if unmapped."""
    return LANG_NAME.get((code or "en").lower(), code or "en")


# ---------------------------------------------------------------------------
# Command glossary (Indonesian → English command key)
#
# The `command` tool argument is grammar-constrained to the English CMD_MAP
# keys.  Under VOICE_LANG=id the speaker issues commands in Indonesian, so this
# glossary is rendered into the tool-schema `command` description to teach the
# Indonesian→English mapping.  Under VOICE_LANG=en the glossary is unused (the
# enum description stays English-only).  Keep entries in sync with CMD_MAP; any
# key without a gloss still works (English only).
# ---------------------------------------------------------------------------

COMMAND_GLOSSARY: dict = {
    "sit":             "duduk",
    "stand":           "berdiri, bangun, berdiri tegak",
    "balance":         "seimbang, keseimbangan",
    "stretch":         "regangkan, peregangan, menggeliat",
    "recover":         "pulih, bangkit, pemulihan",
    "stop":            "berhenti, stop, diam",
    "raise_body":      "naik, naikkan badan, angkat badan, lebih tinggi",
    "lower_body":      "turun, turunkan badan, lebih rendah",
    "trot":            "lari kecil, trot",
    "crawl":           "merangkak, merayap",
    "stand_gait":      "gaya berdiri",
    "rest_gait":       "gaya istirahat",
    "slow_speed":      "pelan, lambat, perlahan",
    "normal_speed":    "kecepatan normal, kecepatan biasa",
    "fast_speed":      "cepat, kencang",
    "forward":         "maju, ke depan",
    "backward":        "mundur, ke belakang",
    "turn_left":       "belok kiri, putar kiri, ke kiri",
    "turn_right":      "belok kanan, putar kanan, ke kanan",
    "stop_move":       "berhenti bergerak, berhenti jalan, stop jalan",
    "keep_forward":    "terus maju, maju terus, jalan terus",
    "keep_backward":   "terus mundur, mundur terus",
    "keep_turn_left":  "terus belok kiri, putar kiri terus",
    "keep_turn_right": "terus belok kanan, putar kanan terus",
    "hello":           "halo, hai, salam, beri salam, sapa",
    "dance1":          "menari, joget, nari, tarian",
    "dance2":          "menari dua, tarian kedua",
    "front_flip":      "salto, jungkir balik, salto depan",
    "wiggle_hips":     "goyang pinggul, goyang",
    "finger_heart":    "love, hati jari, salam cinta",
    "handstand":       "berdiri tangan, handstand",
    "moon_walk":       "moonwalk, jalan moonwalk",
    "continuous_gait": "gerak terus menerus, gaya berkelanjutan",
    "auto_rest":       "istirahat otomatis",
}


# A handful of representative Indonesian→English examples is enough to prime
# Gemma's (already multilingual) mapping. Dumping the full 35-entry glossary into
# the tool schema bloats the prompt by ~600 tokens and biases the audio model's
# language prior, which degrades transcription — so we only surface a few.
_GLOSSARY_EXAMPLES = (
    "sit", "stand", "forward", "backward",
    "turn_left", "turn_right", "stop", "hello", "dance1",
)


def command_enum_description(language: str = "en") -> str:
    """`command` enum description, focused on a single spoken language.

    The enum itself is grammar-constrained to the English CMD_MAP keys; this
    description only needs to teach the *mapping* pattern, not enumerate every
    command.

    - en: English-only. No foreign-language examples, so the audio model keeps a
      clean English prior (the bilingual hint used to degrade English).
    - id: Indonesian→English. A few representative examples plus a nudge to use
      the model's own Indonesian knowledge for phrases not listed.
    """
    if (language or "en").lower() != "id":
        return (
            "The single robot command to execute. The enum keys are English; "
            "map the spoken English phrase to the matching key."
        )
    examples = ", ".join(
        f"{COMMAND_GLOSSARY[k].split(',')[0].strip()}→{k}"
        for k in _GLOSSARY_EXAMPLES
        if k in COMMAND_GLOSSARY
    )
    return (
        "The single robot command to execute; the enum keys are always English. "
        "The speaker is speaking Indonesian — map the Indonesian phrase to the "
        f"matching key (e.g. {examples}). Use your own knowledge of Indonesian for "
        "phrases not in these examples."
    )


def command_tool_description(language: str = "en") -> str:
    """Description for the `execute_robot_command` tool, focused on one language.

    The model decides *which* tool to call from the tool descriptions, NOT from
    the nested `command` enum description. In Indonesian mode the spoken command
    words (duduk, maju, …) don't look like commands unless we name them here.

    NOTE: kept in English even for the Indonesian path. An all-Bahasa instruction
    context was tried and it destabilised Gemma's AUDIO transcription into
    degenerate repetition loops ("elliot_bed_bed_bed…"); the English context
    transcribes Indonesian audio cleanly. Indonesian command MAPPING is delivered
    by the deterministic id-scoped override, not the prompt language.
    """
    if (language or "en").lower() != "id":
        return (
            "Issue a movement, posture, gait, speed, or gesture command to the robot. "
            "Use when the speech requests one of these commands."
        )
    examples = ", ".join(
        f"{COMMAND_GLOSSARY[k].split(',')[0].strip()} ({k})"
        for k in _GLOSSARY_EXAMPLES
        if k in COMMAND_GLOSSARY
    )
    return (
        "Issue a movement, posture, gait, speed, or gesture command to the robot. "
        "Use when the speech requests one of these commands. The speaker is speaking "
        f"Indonesian; treat Indonesian command words as commands, not conversation "
        f"(e.g. {examples})."
    )


def conversational_tool_description(language: str = "en") -> str:
    """Description for the `respond_conversationally` tool (English for all languages —
    see command_tool_description for why the Indonesian path stays in English)."""
    return (
        "Reply with speech when the input is not a robot command — chit-chat, a "
        "question, or no wake word."
    )


def _field_text(language: str) -> dict:
    """Tool-schema field descriptions (English for all languages)."""
    return {
        "transcript": "Verbatim transcription of the speech.",
        "wake_word": "True if the wake word is present.",
        "spoken_reply": (
            "A 1-2 sentence reply suitable for text-to-speech. No markdown, no lists."
        ),
    }


def build_unified_tools(language: str = "en") -> list:
    """Two-tool schema (execute_robot_command + respond_conversationally), shared by
    mic_bridge_node and stt_node. Descriptions are in English for every language —
    an all-Bahasa instruction context destabilised Gemma's AUDIO transcription into
    repetition loops, while English context transcribes Indonesian audio cleanly.
    The command enum still carries Indonesian→English examples so Gemma maps when it
    fires; the deterministic id-scoped override is the reliable command path."""
    ft = _field_text(language)
    return [
        {
            "type": "function",
            "function": {
                "name": "execute_robot_command",
                "description": command_tool_description(language),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "transcript": {"type": "string", "description": ft["transcript"]},
                        "contains_wake_word": {"type": "boolean", "description": ft["wake_word"]},
                        "command": {
                            "type": "string",
                            "enum": list(CMD_MAP.keys()),
                            "description": command_enum_description(language),
                        },
                    },
                    "required": ["transcript", "contains_wake_word", "command"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "respond_conversationally",
                "description": conversational_tool_description(language),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "transcript": {"type": "string", "description": ft["transcript"]},
                        "contains_wake_word": {"type": "boolean", "description": ft["wake_word"]},
                        "spoken_reply": {"type": "string", "description": ft["spoken_reply"]},
                    },
                    "required": ["transcript", "contains_wake_word", "spoken_reply"],
                },
            },
        },
    ]


def system_prompt(language: str, wake_word: str) -> str:
    """Audio-path system prompt. English for every language: an all-Bahasa context
    destabilised Gemma's audio transcription into repetition loops, while English
    context transcribes Indonesian audio cleanly. The `language` only names the
    spoken language so the model keeps the right transcription prior."""
    return (
        "You are a Unitree GO2 quadruped robot that follows spoken commands.\n"
        f'The wake word is "{wake_word}".\n'
        "If the wake word is present and the speech clearly requests one of the "
        "available commands, call execute_robot_command with the matching command. "
        "Otherwise call respond_conversationally.\n"
        f"The speech is in {language_name(language)}."
    )


def system_prompt_text(language: str, wake_word: str) -> str:
    """Typed-text-path system prompt (English framing; see system_prompt)."""
    return (
        "You are a Unitree GO2 quadruped robot. The user typed the text directly "
        "(no audio).\n"
        f'The wake word is "{wake_word}".\n'
        "If the wake word is present and the text clearly requests one of the "
        "available commands, call execute_robot_command with the matching command. "
        "Otherwise call respond_conversationally.\n"
        f"The text is in {language_name(language)}."
    )


# Question markers — a transcript that asks a question is treated as conversation
# even when it happens to contain a command word ("bagaimana cara duduk?" must not
# fire `sit`). Indonesian interrogatives + a literal "?" are enough in practice.
_QUESTION_WORDS = frozenset((
    "apa", "apakah", "bagaimana", "gimana", "kenapa", "mengapa",
    "siapa", "kapan", "mana", "dimana", "berapa", "bisakah", "bolehkah",
))


def _looks_like_question(text: str) -> bool:
    if "?" in text:
        return True
    words = set(re.sub(r"[^\w\s]", " ", text.lower()).split())
    return bool(words & _QUESTION_WORDS)


def command_for_text(text: str, language: str = "en") -> Optional[str]:
    """Best-effort literal map of a transcript to a CMD_MAP key, or None.

    A deterministic safety net for when the LLM under-fires on a clear command
    (notably Indonesian, where it tends to pick the conversational tool even on a
    perfect transcript). Always matches the English command keys; under `id` also
    matches the COMMAND_GLOSSARY phrases. Longer phrases win so "belok kiri" beats
    "belok". Punctuation is ignored and matching is word-boundary aware so "sit"
    does not match "situation". Questions are skipped so a command word inside a
    question ("bagaimana cara duduk?") stays conversational rather than firing.
    """
    if not text or _looks_like_question(text):
        return None
    t = " " + re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", text.lower())).strip() + " "

    candidates: list = [(key.replace("_", " "), key) for key in CMD_MAP]
    if (language or "en").lower() == "id":
        for key, glosses in COMMAND_GLOSSARY.items():
            for gloss in glosses.split(","):
                gloss = gloss.strip().lower()
                if gloss:
                    candidates.append((gloss, key))

    for phrase, key in sorted(candidates, key=lambda kv: len(kv[0]), reverse=True):
        if phrase and f" {phrase} " in t:
            return key
    return None


# ---------------------------------------------------------------------------
# Sampling params for the unified llama.cpp /v1/chat/completions calls.
#
# Keep this MINIMAL. With `--jinja` native tool calling, llama.cpp does NOT
# hard-constrain the `command` field to the enum via a grammar — it relies on
# the model following the tool schema. Tool-call JSON is legitimately
# repetitive (quotes, commas, underscores, shared enum substrings), so any
# repetition / frequency penalty distorts it and the model degenerates —
# echoing the schema back as the argument value
# (`{"command": {"enum": [...]}}`) instead of picking one command. Pure greedy
# (temp 0) is the opposite trap: it cannot escape a degenerate token loop.
#
#   temperature  — low for reliable schema adherence, but NOT 0 (greedy can get
#                  stuck in a repetition loop it can never leave).
#   max_tokens   — bounds any residual runaway so a bad generation fails fast.
#
# Do NOT add repeat_penalty / frequency_penalty / presence_penalty here: they
# corrupt the structured tool-call output. The reasoning-preamble loop is
# addressed server-side (llama-server --reasoning off / --reasoning-budget 0),
# not with sampling hacks.
# ---------------------------------------------------------------------------

LLAMA_SAMPLING: dict = {
    "temperature": 0.3,
    "top_p": 0.95,
    "max_tokens": 256,
}


# ---------------------------------------------------------------------------
# Human-readable feedback strings
# ---------------------------------------------------------------------------

FEEDBACK_MAP: dict = {
    1009: "Sitting down",
    1004: "Standing up",
    1002: "Balance stand",
    1006: "Recovery stand",
    1017: "Stretching",
    1003: "Stopping",
    (1011, "1"): "Switching to trot",
    (1011, "2"): "Switching to crawl",
    (1011, "3"): "Stand gait",
    (1011, "0"): "Rest gait",
    (1015, "0"): "Slowing down",
    (1015, "1"): "Normal speed",
    (1015, "2"): "Speeding up",
    (1013, "0.05"):  "Raising body",
    (1013, "-0.05"): "Lowering body",
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

# ---------------------------------------------------------------------------
# Shared LLM prompts
# ---------------------------------------------------------------------------

ROBOT_CMD_SYSTEM_PROMPT = """
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


def robot_cmd_system_prompt(language: str = "en") -> str:
    """ROBOT_CMD_SYSTEM_PROMPT with a single-language statement prepended.

    The command keys stay English; this only tells the parser which language the
    user is speaking so it maps a single language cleanly (no bilingual hedging).
    """
    line = f"The user is speaking {language_name(language)}.\n"
    return f"{line}{ROBOT_CMD_SYSTEM_PROMPT}"

CONVERSATIONAL_SYSTEM = (
    "You are GO2, a Unitree quadruped robot assistant. "
    "Respond in 1–2 short sentences suitable for text-to-speech (no markdown, no lists). "
    "You can move, sit, stand, change gait, and perform gestures. "
    "If asked for something outside your physical abilities, say so politely."
)

CONVERSATIONAL_SYSTEM_WITH_SEARCH = (
    "You are GO2, a Unitree quadruped robot assistant. "
    "Respond in 1–2 short sentences suitable for text-to-speech (no markdown, no lists). "
    "You can move, sit, stand, change gait, and perform gestures. "
    "Use the search_web tool when the question requires current information, "
    "news, weather, or facts you are not certain about."
)

SEARCH_TOOL_OPENAI = {
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


# ---------------------------------------------------------------------------
# Stateless feedback helper
# ---------------------------------------------------------------------------

def coerce_str(value, default=None):
    """Return a stripped non-empty string, else `default`.

    Guards downstream `.strip()` calls against the model returning a non-string
    (dict/list/number) for a field that should be text.
    """
    if isinstance(value, str):
        return value.strip() or default
    return default


def coerce_command(value) -> str:
    """Normalise a model-provided command to a valid CMD_MAP key or 'unknown'.

    Native `--jinja` tool calling does not hard-constrain `command` to the enum,
    so the model can emit garbage — including echoing the schema back as a dict
    (`{"command": {"enum": [...]}}`). Anything that isn't an exact CMD_MAP key is
    treated as no command, which keeps `CMD_MAP[...]` lookups crash-safe.
    """
    return value if isinstance(value, str) and value in CMD_MAP else "unknown"


def feedback_for_action(action) -> str:
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
            FEEDBACK_MAP.get((api_id, param))
            or FEEDBACK_MAP.get(api_id)
            or "Command executed"
        )
    return "Command executed"


# ---------------------------------------------------------------------------
# Stateful command dispatcher (holds movement timer + publishers)
# ---------------------------------------------------------------------------

class CommandDispatcher:
    """
    Wraps command execution for both voice_cmd_node and mic_bridge_node.
    Owns the 10 Hz velocity sustain timer and timed-stop machinery.
    """

    def __init__(self, cmd_pub, vel_pub, lin_speed: float, ang_speed: float,
                 move_dur: float, is_sim: bool, node):
        self._cmd_pub   = cmd_pub
        self._vel_pub   = vel_pub
        self._lin_speed = lin_speed
        self._ang_speed = ang_speed
        self._move_dur  = move_dur
        self._is_sim    = is_sim
        self._node      = node
        self._move_lock: threading.Lock = threading.Lock()
        self._stop_timer: Optional[threading.Timer] = None
        self._current_twist: Optional[Twist] = None
        self._move_timer = node.create_timer(0.1, self._move_tick)

    # ------------------------------------------------------------------

    def execute(self, action) -> None:
        if isinstance(action, dict):
            self._send_robot_cmd(action)
        elif action[0] == "move":
            _, lin, ang = action
            self._send_move(lin, ang)
        elif action[0] == "keep":
            _, lin, ang = action
            self._send_keep_move(lin, ang)
        elif action[0] == "stop_move":
            self._send_stop_move()

    def feedback_for(self, action) -> str:
        return feedback_for_action(action)

    # ------------------------------------------------------------------

    def _move_tick(self) -> None:
        with self._move_lock:
            twist = self._current_twist
        if twist is not None:
            self._vel_pub.publish(twist)

    def _send_robot_cmd(self, action: dict) -> None:
        if action.get("hw_only") and self._is_sim:
            self._node.get_logger().warn(
                f"Command api_id={action['api_id']} is hardware-only — skipped in simulation"
            )
            return
        req = WebRtcReq()
        req.api_id    = action["api_id"]
        req.parameter = action.get("parameter", "")
        req.priority  = 0
        self._cmd_pub.publish(req)
        self._node.get_logger().info(
            f"Robot command: api_id={req.api_id} parameter={req.parameter!r}"
        )

    def _send_move(self, linear_x: float, angular_z: float) -> None:
        twist = Twist()
        twist.linear.x  = linear_x * self._lin_speed
        twist.angular.z = angular_z * self._ang_speed
        self._node.get_logger().info(
            f"Move: linear.x={twist.linear.x:.2f} angular.z={twist.angular.z:.2f} "
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
        twist.linear.x  = linear_x * self._lin_speed
        twist.angular.z = angular_z * self._ang_speed
        self._node.get_logger().info(
            f"Keep move: linear.x={twist.linear.x:.2f} angular.z={twist.angular.z:.2f}"
        )
        with self._move_lock:
            self._cancel_stop_timer()
            self._current_twist = twist

    def _send_stop_move(self) -> None:
        with self._move_lock:
            self._cancel_stop_timer()
            self._current_twist = None
        self._vel_pub.publish(Twist())
        self._node.get_logger().info("Stop move: zero velocity published")

    def _cancel_stop_timer(self) -> None:
        if self._stop_timer is not None:
            self._stop_timer.cancel()
            self._stop_timer = None

    def _stop_timer_cb(self) -> None:
        with self._move_lock:
            self._stop_timer = None
            self._current_twist = None
        self._vel_pub.publish(Twist())
        self._node.get_logger().info("Move duration elapsed — zero velocity published")
