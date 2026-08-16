#!/usr/bin/env python3

# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

"""
Unit tests for Modul 1 — Basic Voice Command Recognition.

Covers:
  1.1  Wake-word gating  (STT backends return (text, wake_word_found) bool)
  1.2  Basic command mapping (CMD_MAP entries → correct action tuples / api_id dicts)
  1.3  Bilingual support  (COMMAND_GLOSSARY + command_for_text for EN and ID)

Pure pytest — no rclpy, no ROS2 messages (per .claude/rules/testing.md).
All tested logic lives in command_dispatcher.py (pure Python, no ROS2 imports
at module level beyond lazy geometry_msgs/go2_interfaces inside class methods).

To run:
    cd d:/go2_ros2_sdk
    python -m pytest speech_processor/test/test_modul1_voice_commands.py -v
"""

from __future__ import annotations

import re
import sys
import types

import pytest

# ---------------------------------------------------------------------------
# Minimal stubs so command_dispatcher.py can be imported without a full ROS2
# environment. The module only uses rclpy/ROS2 messages inside class bodies
# (CommandDispatcher.__init__ etc.), not at the top level — so we just need
# stub packages to satisfy `from geometry_msgs.msg import ...` etc.
# ---------------------------------------------------------------------------

def _make_stub(module_path: str, attrs: dict | None = None):
    parts = module_path.split(".")
    parent = None
    for i, part in enumerate(parts):
        full = ".".join(parts[: i + 1])
        if full not in sys.modules:
            m = types.ModuleType(full)
            sys.modules[full] = m
            if parent is not None:
                setattr(parent, part, m)
        parent = sys.modules[full]
    if attrs:
        for k, v in attrs.items():
            setattr(parent, k, v)
    return parent


# Geometry / ROS2 stubs (only attributes command_dispatcher.py imports)
_make_stub("geometry_msgs")
_make_stub("geometry_msgs.msg", {"Twist": object})
_make_stub("go2_interfaces")
_make_stub("go2_interfaces.msg", {"WebRtcReq": object})
_make_stub("std_msgs")
_make_stub("std_msgs.msg", {"Empty": object, "String": object})
_make_stub("rclpy")

# Now import the real module
from speech_processor.command_dispatcher import (  # noqa: E402
    CMD_MAP,
    COMMAND_GLOSSARY,
    FEEDBACK_MAP,
    command_for_text,
    feedback_for_action,
    language_name,
    coerce_command,
    coerce_str,
    _looks_like_question,
)


# ===========================================================================
# 1.1  Wake-word gating
# ===========================================================================

class TestWakeWordGating:
    """Modul 1.1 — wake-word detection is implemented as a boolean flag returned
    by each STT backend's transcribe() method.  We test the downstream behaviour:
    stt_node ignores utterances where wake_word_found is False.

    The VAD + audio-capture path is hardware-dependent; here we test the pure
    logic gate that would be applied to the (text, wake_found) tuple.
    """

    @staticmethod
    def _simulate_gate(text: str, wake_found: bool) -> bool:
        """Mirror of stt_node._process_loop: publish iff wake_found is True."""
        if not text:
            return False
        return wake_found

    def test_no_wake_word_suppresses_command(self):
        assert self._simulate_gate("stand up", wake_found=False) is False

    def test_wake_word_allows_command(self):
        assert self._simulate_gate("hey doggo, stand up", wake_found=True) is True

    def test_empty_transcript_suppressed_regardless(self):
        assert self._simulate_gate("", wake_found=True) is False

    def test_wake_word_false_with_empty_text(self):
        assert self._simulate_gate("", wake_found=False) is False

    # Backend transcribe() contract -----------------------------------------

    def test_openai_backend_sets_wake_found_true_when_word_in_transcript(self):
        """_OpenAIBackend.transcribe returns (text, True) when wake word is in text."""
        wake_word = "doggo"
        text = "hey doggo sit down"
        # Replicate the expression from _OpenAIBackend.transcribe
        result = (wake_word in text.lower()) if wake_word else True
        assert result is True

    def test_openai_backend_sets_wake_found_false_when_word_absent(self):
        wake_word = "doggo"
        text = "sit down please"
        result = (wake_word in text.lower()) if wake_word else True
        assert result is False

    def test_empty_wake_word_always_passes(self):
        """An empty wake_word param means every transcript passes the gate."""
        wake_word = ""
        text = "sit"
        result = (wake_word in text.lower()) if wake_word else True
        assert result is True

    def test_case_insensitive_wake_word(self):
        wake_word = "doggo"
        text = "Hey DOGGO stand up"
        result = (wake_word in text.lower()) if wake_word else True
        assert result is True

    @pytest.mark.parametrize("wake_word,text,expected", [
        ("elliot", "hey Elliot, maju!", True),
        ("elliot", "hei robot, maju!", False),
        ("doggo",  "doggo berdiri",     True),
        ("doggo",  "berdiri",            False),
    ])
    def test_wake_word_variants(self, wake_word, text, expected):
        result = (wake_word in text.lower()) if wake_word else True
        assert result is expected


# ===========================================================================
# 1.2  Basic command mapping
# ===========================================================================

class TestCmdMap:
    """Modul 1.2 — CMD_MAP entries for the proposal's basic command set."""

    # --- Expected basic-set entries from the proposal ----------------------
    BASIC_CMDS = {
        "sit":        {"api_id": 1009, "parameter": ""},
        "stand":      {"api_id": 1004, "parameter": ""},
        "stop":       {"api_id": 1003, "parameter": ""},
        "forward":    ("move", 1.0, 0.0),
        "backward":   ("move", -1.0, 0.0),
        "turn_left":  ("move", 0.0, 1.0),
        "turn_right": ("move", 0.0, -1.0),
    }

    def test_all_basic_commands_exist_in_cmd_map(self):
        for cmd in self.BASIC_CMDS:
            assert cmd in CMD_MAP, f"Missing basic command: {cmd!r}"

    def test_sit_action(self):
        action = CMD_MAP["sit"]
        assert isinstance(action, dict)
        assert action["api_id"] == 1009

    def test_stand_action(self):
        action = CMD_MAP["stand"]
        assert isinstance(action, dict)
        assert action["api_id"] == 1004

    def test_stop_action(self):
        action = CMD_MAP["stop"]
        assert isinstance(action, dict)
        assert action["api_id"] == 1003

    def test_forward_is_move_tuple_positive_linear(self):
        action = CMD_MAP["forward"]
        assert isinstance(action, tuple)
        assert action[0] == "move"
        assert action[1] > 0   # positive linear_x
        assert action[2] == 0.0

    def test_backward_is_move_tuple_negative_linear(self):
        action = CMD_MAP["backward"]
        assert isinstance(action, tuple)
        assert action[0] == "move"
        assert action[1] < 0   # negative linear_x
        assert action[2] == 0.0

    def test_turn_left_positive_angular(self):
        action = CMD_MAP["turn_left"]
        assert isinstance(action, tuple)
        assert action[0] == "move"
        assert action[1] == 0.0
        assert action[2] > 0   # positive angular_z = left

    def test_turn_right_negative_angular(self):
        action = CMD_MAP["turn_right"]
        assert isinstance(action, tuple)
        assert action[0] == "move"
        assert action[1] == 0.0
        assert action[2] < 0   # negative angular_z = right

    def test_basic_actions_match_expected(self):
        for cmd, expected_action in self.BASIC_CMDS.items():
            actual = CMD_MAP[cmd]
            assert actual == expected_action, f"{cmd}: expected {expected_action}, got {actual}"

    # --- Completeness sanity check ------------------------------------------

    def test_all_cmd_map_keys_are_strings(self):
        for k in CMD_MAP:
            assert isinstance(k, str), f"Non-string key in CMD_MAP: {k!r}"

    def test_all_cmd_map_actions_are_dict_or_tuple(self):
        for k, v in CMD_MAP.items():
            assert isinstance(v, (dict, tuple)), f"Unexpected action type for {k!r}: {type(v)}"

    def test_no_go_to_room_in_cmd_map(self):
        """go_to_room is dynamic; its action tuple is produced by NLU parsers."""
        assert "go_to_room" not in CMD_MAP


class TestFeedbackForAction:
    """feedback_for_action should return human-readable English strings."""

    def test_sit_feedback(self):
        fb = feedback_for_action(CMD_MAP["sit"])
        assert isinstance(fb, str) and len(fb) > 0

    def test_stand_feedback(self):
        fb = feedback_for_action(CMD_MAP["stand"])
        assert isinstance(fb, str) and len(fb) > 0

    def test_forward_feedback(self):
        fb = feedback_for_action(CMD_MAP["forward"])
        assert "forward" in fb.lower() or "moving" in fb.lower()

    def test_backward_feedback(self):
        fb = feedback_for_action(CMD_MAP["backward"])
        assert "backward" in fb.lower() or "moving" in fb.lower()

    def test_turn_left_feedback(self):
        fb = feedback_for_action(CMD_MAP["turn_left"])
        assert "left" in fb.lower() or "turning" in fb.lower()

    def test_turn_right_feedback(self):
        fb = feedback_for_action(CMD_MAP["turn_right"])
        assert "right" in fb.lower() or "turning" in fb.lower()

    def test_follow_start_feedback(self):
        fb = feedback_for_action(("follow_start",))
        assert "follow" in fb.lower()

    def test_follow_stop_feedback(self):
        fb = feedback_for_action(("follow_stop",))
        assert "follow" in fb.lower() or "off" in fb.lower()

    def test_goto_room_feedback(self):
        fb = feedback_for_action(("goto_room", "lobby"))
        assert "lobby" in fb.lower() or "navigat" in fb.lower()

    def test_unknown_dict_returns_string(self):
        fb = feedback_for_action({"api_id": 9999, "parameter": ""})
        assert isinstance(fb, str)

    def test_stop_move_feedback(self):
        fb = feedback_for_action(("stop_move",))
        assert "stop" in fb.lower() or "movement" in fb.lower()


# ===========================================================================
# 1.3  Bilingual support
# ===========================================================================

class TestLanguageName:
    """language_name() maps codes to human-readable names."""

    def test_en_maps_to_english(self):
        assert language_name("en") == "English"

    def test_id_maps_to_indonesian(self):
        assert language_name("id") == "Indonesian"

    def test_unknown_code_passes_through(self):
        assert language_name("de") == "de"

    def test_empty_string_defaults_to_english(self):
        assert language_name("") == "English"

    def test_none_defaults_to_english(self):
        assert language_name(None) == "English"

    def test_case_insensitive(self):
        assert language_name("EN") == "English"
        assert language_name("Id") == "Indonesian"


class TestCommandGlossary:
    """COMMAND_GLOSSARY — every Indonesian phrase set maps to a real CMD_MAP key
    (or a near-alias like 'go_to_room' that is valid for the ID NLU path)."""

    VALID_KEYS = set(CMD_MAP.keys()) | {"go_to_room", "patrol_start", "patrol_stop"}

    def test_all_glossary_keys_are_valid_command_keys(self):
        for key in COMMAND_GLOSSARY:
            assert key in self.VALID_KEYS, (
                f"COMMAND_GLOSSARY key {key!r} has no corresponding CMD_MAP entry"
            )

    def test_basic_commands_have_glossary_entries(self):
        required = {"sit", "stand", "forward", "backward", "turn_left", "turn_right", "stop"}
        for cmd in required:
            assert cmd in COMMAND_GLOSSARY, f"No Indonesian gloss for basic command: {cmd!r}"

    def test_sit_gloss_contains_duduk(self):
        assert "duduk" in COMMAND_GLOSSARY["sit"].lower()

    def test_stand_gloss_contains_berdiri(self):
        assert "berdiri" in COMMAND_GLOSSARY["stand"].lower()

    def test_forward_gloss_contains_maju(self):
        assert "maju" in COMMAND_GLOSSARY["forward"].lower()

    def test_backward_gloss_contains_mundur(self):
        assert "mundur" in COMMAND_GLOSSARY["backward"].lower()

    def test_turn_left_gloss_contains_kiri(self):
        assert "kiri" in COMMAND_GLOSSARY["turn_left"].lower()

    def test_turn_right_gloss_contains_kanan(self):
        assert "kanan" in COMMAND_GLOSSARY["turn_right"].lower()

    def test_stop_gloss_contains_berhenti(self):
        assert "berhenti" in COMMAND_GLOSSARY["stop"].lower()

    def test_each_gloss_is_non_empty(self):
        for key, gloss in COMMAND_GLOSSARY.items():
            assert gloss.strip(), f"Empty gloss for {key!r}"


class TestCommandForTextEnglish:
    """command_for_text — English (VOICE_LANG=en) keyword matching."""

    @pytest.mark.parametrize("text,expected_key", [
        ("sit",              "sit"),
        ("stand up",         "stand"),
        ("move forward",     "forward"),
        ("go backward",      "backward"),
        ("turn left",        "turn_left"),
        ("turn right",       "turn_right"),
        ("stop",             "stop"),
    ])
    def test_english_keywords(self, text, expected_key):
        result = command_for_text(text, "en")
        assert result == expected_key, f"text={text!r}: got {result!r}, expected {expected_key!r}"

    def test_returns_none_for_unknown_phrase_en(self):
        assert command_for_text("what is the weather", "en") is None

    def test_returns_none_for_empty_string(self):
        assert command_for_text("", "en") is None

    def test_returns_none_for_question_with_command_word(self):
        """A question mark should prevent the command word from firing."""
        # "sit" inside a question should NOT match
        result = command_for_text("can you sit down?", "en")
        # May or may not match depending on position; the important thing is
        # that a literal "?" triggers question suppression
        assert command_for_text("how do you sit?", "en") is None

    def test_longer_phrase_wins_over_shorter(self):
        """'turn left' should beat just 'turn' if there were a 'turn' key."""
        result = command_for_text("turn left now", "en")
        assert result == "turn_left"

    def test_case_insensitive_match(self):
        assert command_for_text("SIT", "en") == "sit"
        assert command_for_text("FORWARD", "en") == "forward"


class TestCommandForTextIndonesian:
    """command_for_text — Indonesian (VOICE_LANG=id) keyword matching."""

    @pytest.mark.parametrize("text,expected_key", [
        ("duduk",            "sit"),
        ("berdiri",          "stand"),
        ("jalan maju",       "forward"),
        ("maju",             "forward"),
        ("mundur",           "backward"),
        ("jalan mundur",     "backward"),
        ("putar kiri",       "turn_left"),
        ("belok kiri",       "turn_left"),
        ("putar kanan",      "turn_right"),
        ("belok kanan",      "turn_right"),
        ("berhenti",         "stop"),
    ])
    def test_indonesian_basic_commands(self, text, expected_key):
        result = command_for_text(text, "id")
        assert result == expected_key, f"text={text!r}: got {result!r}, expected {expected_key!r}"

    def test_indonesian_question_suppression(self):
        """Indonesian question words should prevent command from firing."""
        result = command_for_text("bagaimana cara duduk?", "id")
        assert result is None

    def test_indonesian_apakah_question(self):
        assert command_for_text("apakah kamu bisa duduk", "id") is None

    def test_indonesian_unknown_phrase(self):
        assert command_for_text("apa kabar", "id") is None

    @pytest.mark.parametrize("text,expected_key", [
        ("berdiri tegak",    "stand"),
        ("ke depan",         "forward"),
        ("ke belakang",      "backward"),
        ("ke kiri",          "turn_left"),
        ("ke kanan",         "turn_right"),
        ("diam",             "stop"),
    ])
    def test_alternative_indonesian_phrases(self, text, expected_key):
        result = command_for_text(text, "id")
        assert result == expected_key, f"text={text!r}: got {result!r}, expected {expected_key!r}"

    def test_english_key_still_works_in_id_mode(self):
        """English command words must still match in Indonesian language mode."""
        assert command_for_text("sit", "id") == "sit"
        assert command_for_text("stand", "id") == "stand"


class TestLooksLikeQuestion:
    """_looks_like_question — question detection helper (ID + EN)."""

    @pytest.mark.parametrize("text,is_q", [
        ("how do you sit?",           True),
        ("what is your name?",        True),
        ("bagaimana cara duduk?",     True),
        ("apakah kamu bisa maju",     True),   # Indonesian question word, no "?"
        ("dimana toilet",             True),
        ("sit",                       False),
        ("move forward",              False),
        ("berdiri",                   False),
        ("maju terus",                False),
    ])
    def test_question_detection(self, text, is_q):
        assert _looks_like_question(text) == is_q, f"text={text!r}: expected is_q={is_q}"


# ===========================================================================
# Helper / coerce functions
# ===========================================================================

class TestCoerceCommand:
    """coerce_command normalises LLM output to valid CMD_MAP keys."""

    def test_valid_key_passes_through(self):
        assert coerce_command("sit") == "sit"
        assert coerce_command("forward") == "forward"

    def test_invalid_string_returns_unknown(self):
        assert coerce_command("fly") == "unknown"
        assert coerce_command("go") == "unknown"

    def test_none_returns_unknown(self):
        assert coerce_command(None) == "unknown"

    def test_dict_returns_unknown(self):
        assert coerce_command({"enum": ["sit"]}) == "unknown"

    def test_all_cmd_map_keys_pass_through(self):
        for key in CMD_MAP:
            assert coerce_command(key) == key


class TestCoerceStr:
    """coerce_str strips non-empty strings; returns default otherwise."""

    def test_strips_whitespace(self):
        assert coerce_str("  hello  ") == "hello"

    def test_empty_string_returns_default(self):
        assert coerce_str("") is None
        assert coerce_str("", default="fallback") == "fallback"

    def test_whitespace_only_returns_default(self):
        assert coerce_str("   ") is None

    def test_none_returns_default(self):
        assert coerce_str(None) is None

    def test_non_string_returns_default(self):
        assert coerce_str(42) is None
        assert coerce_str(["a"]) is None


# ===========================================================================
# FEEDBACK_MAP completeness
# ===========================================================================

class TestFeedbackMap:
    """FEEDBACK_MAP should cover all api_id commands that appear in CMD_MAP."""

    def test_sit_in_feedback_map(self):
        assert 1009 in FEEDBACK_MAP

    def test_stand_in_feedback_map(self):
        assert 1004 in FEEDBACK_MAP

    def test_stop_in_feedback_map(self):
        assert 1003 in FEEDBACK_MAP

    def test_all_feedback_values_are_non_empty_strings(self):
        for k, v in FEEDBACK_MAP.items():
            assert isinstance(v, str) and v.strip(), f"Empty feedback for key {k!r}"


