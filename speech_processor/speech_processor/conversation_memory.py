#!/usr/bin/env python3

# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

"""
Multi-turn conversation memory (Modul 3.4) — pure Python, no ROS2 imports.

Keeps a short rolling window of recent user<->robot exchanges so the conversational
LLM can resolve follow-ups and anaphora ("and on weekends?", "how much is that?")
that single-shot processing loses.

Two bounds, both tuned for a public venue (museum / park / event) where different
visitors take turns with the robot:

* **window** — keep only the last ``max_turns`` exchanges. Venue Q&A follow-ups are
  shallow (1-2 back-references), and a short window keeps prompts cheap on the
  local Gemma path and limits how far one visitor's topic can bleed forward.
* **idle reset** — if more than ``idle_timeout`` seconds pass with no conversation,
  the history is cleared on the next access, so a new visitor stepping up starts
  fresh instead of inheriting the previous person's context.

This module has **no ``rclpy`` imports** so it stays unit-testable without a ROS2
environment (see ``test/test_conversation_memory.py``). ``voice_cmd_node`` owns the
ROS2 wiring and converts the returned ``(role, content)`` turns into each
provider's message format.
"""

from __future__ import annotations

import time
from collections import deque
from typing import List, Optional, Tuple

# A history entry as (role, content); role is "user" or "assistant".
Message = Tuple[str, str]


class ConversationMemory:
    """A rolling window of recent exchanges with an idle-reset policy."""

    def __init__(self, max_turns: int = 3, idle_timeout: float = 60.0):
        self._max_turns = max(0, int(max_turns))
        self._idle_timeout = float(idle_timeout)
        # Each item is one completed exchange: (user_text, assistant_text).
        self._turns: deque = deque(maxlen=self._max_turns or None)
        self._last_activity: Optional[float] = None

    # -- public API --------------------------------------------------------

    def history(self, now: Optional[float] = None) -> List[Message]:
        """Return the rolling history as ``(role, content)`` messages.

        Applies the idle reset first: if the conversation has been quiet longer
        than ``idle_timeout``, the window is cleared and an empty list returned.
        """
        if self._max_turns == 0:
            return []
        if self._expired(self._resolve(now)):
            self.clear()
        msgs: List[Message] = []
        for user_text, assistant_text in self._turns:
            msgs.append(("user", user_text))
            msgs.append(("assistant", assistant_text))
        return msgs

    def add(self, user_text: str, assistant_text: str,
            now: Optional[float] = None) -> None:
        """Record a completed exchange, evicting the oldest beyond the window."""
        if self._max_turns == 0 or not user_text or not assistant_text:
            return
        now = self._resolve(now)
        if self._expired(now):  # defensive — usually already reset by history()
            self.clear()
        self._turns.append((user_text, assistant_text))
        self._last_activity = now

    def clear(self) -> None:
        self._turns.clear()
        self._last_activity = None

    @property
    def num_turns(self) -> int:
        return len(self._turns)

    # -- internals ---------------------------------------------------------

    def _expired(self, now: float) -> bool:
        return (
            self._last_activity is not None
            and self._idle_timeout > 0
            and (now - self._last_activity) > self._idle_timeout
        )

    @staticmethod
    def _resolve(now: Optional[float]) -> float:
        return time.monotonic() if now is None else float(now)
