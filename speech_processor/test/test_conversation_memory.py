#!/usr/bin/env python3

# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

"""
Unit tests for the rolling conversation memory (Modul 3.4).

Pure pytest — no ``rclpy`` (per .claude/rules/testing.md). Time is injected via the
``now`` argument so the idle-reset behaviour is tested deterministically without
sleeping.
"""

from speech_processor.conversation_memory import ConversationMemory


def test_records_and_returns_turns():
    mem = ConversationMemory(max_turns=3, idle_timeout=60.0)
    mem.add("what time do you open?", "Nine to five, Tuesday to Sunday.", now=0.0)
    hist = mem.history(now=1.0)
    assert hist == [
        ("user", "what time do you open?"),
        ("assistant", "Nine to five, Tuesday to Sunday."),
    ]
    assert mem.num_turns == 1


def test_window_evicts_oldest_beyond_max_turns():
    mem = ConversationMemory(max_turns=3, idle_timeout=60.0)
    for i in range(5):
        mem.add(f"q{i}", f"a{i}", now=float(i))
    hist = mem.history(now=5.0)
    # Only the last 3 exchanges (q2..q4) survive → 6 messages.
    assert mem.num_turns == 3
    assert hist[0] == ("user", "q2")
    assert hist[-1] == ("assistant", "a4")


def test_idle_reset_clears_after_timeout():
    mem = ConversationMemory(max_turns=3, idle_timeout=60.0)
    mem.add("hi", "Hello!", now=0.0)
    # A new utterance 61 s later → previous visitor's context is dropped.
    assert mem.history(now=61.0) == []
    assert mem.num_turns == 0


def test_within_timeout_is_retained():
    mem = ConversationMemory(max_turns=3, idle_timeout=60.0)
    mem.add("hi", "Hello!", now=0.0)
    assert len(mem.history(now=59.0)) == 2


def test_new_turn_after_idle_starts_fresh():
    mem = ConversationMemory(max_turns=3, idle_timeout=60.0)
    mem.add("first visitor question", "answer one", now=0.0)
    # history() at t=100 resets; the next add starts a clean window.
    mem.history(now=100.0)
    mem.add("second visitor question", "answer two", now=101.0)
    hist = mem.history(now=102.0)
    assert hist == [
        ("user", "second visitor question"),
        ("assistant", "answer two"),
    ]


def test_disabled_when_zero_turns():
    mem = ConversationMemory(max_turns=0, idle_timeout=60.0)
    mem.add("q", "a", now=0.0)
    assert mem.num_turns == 0
    assert mem.history(now=1.0) == []


def test_blank_turns_ignored():
    mem = ConversationMemory(max_turns=3, idle_timeout=60.0)
    mem.add("", "non-empty", now=0.0)
    mem.add("non-empty", "", now=0.0)
    assert mem.num_turns == 0


def test_no_idle_reset_when_timeout_zero():
    mem = ConversationMemory(max_turns=3, idle_timeout=0.0)
    mem.add("q", "a", now=0.0)
    assert len(mem.history(now=10_000.0)) == 2
