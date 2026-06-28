#!/usr/bin/env python3

# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

"""
Unit tests for Modul 3 — Conversational AI (LLM Integration).

Covers:
  3.1  LLM persona & prompt composition — CONVERSATIONAL_SYSTEM persona, ROBOT_CMD_SYSTEM_PROMPT,
       robot_cmd_system_prompt(lang), KB/face/scene grounding builders.
       Keyword NLU regexes: _GOTO_RE, _APPROACH_RE, _OBJECT_CLASS_MAP.
  3.2  RAG Knowledge Base — corpus chunking internals (_chunk_markdown, _chunk_json),
       _HashingBackend properties, min_score filtering, bilingual retrieval,
       format_context, cache-key invalidation on content change.
  3.3  TTS infrastructure — AudioCache (CRUD, deterministic hash key, stats, disabled mode),
       TTSConfig defaults, TTSProvider enum, AudioFormat enum.
  3.4  Multi-turn conversation memory — additional edge cases beyond test_conversation_memory.py
       (explicit clear, boundary timing, history API shape, large text round-trip).

Pure pytest — no rclpy, no ROS2 messages (per .claude/rules/testing.md).

Existing basic tests live in:
  test_knowledge_base.py    (9 tests)
  test_conversation_memory.py (8 tests)
These files are left intact; this file adds depth and breadth, not duplicates.

Run:
    $env:PYTHONPATH = "d:\\go2_ros2_sdk\\speech_processor"
    python -m pytest speech_processor/test/test_modul3_conversational_ai.py -v
"""

import hashlib
import json
import sys
import types

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# ROS2 / audio library stubs — must be in place before any import that pulls
# rclpy / geometry_msgs / go2_interfaces / pydub at module level.
# _make_stub is idempotent: if the module is already in sys.modules (e.g. from
# a previous test file loaded in the same session) it leaves it untouched.
# ---------------------------------------------------------------------------

def _make_stub(module_path: str, **attrs):
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
    for k, v in attrs.items():
        setattr(parent, k, v)
    return parent


_make_stub("rclpy")
_make_stub("rclpy.node", Node=object)
_make_stub("rclpy.qos")
_make_stub("geometry_msgs")
_make_stub("geometry_msgs.msg", Twist=object)
_make_stub("go2_interfaces")
_make_stub("go2_interfaces.msg", WebRtcReq=object)
_make_stub("std_msgs")
_make_stub("std_msgs.msg", Empty=object, String=object, UInt8MultiArray=object)
_make_stub("pydub", AudioSegment=object)
_make_stub("pydub.playback", play=lambda *a, **kw: None)

# ---------------------------------------------------------------------------
# Module imports (after stubs)
# ---------------------------------------------------------------------------

from speech_processor.knowledge_base import (  # noqa: E402
    KnowledgeBase,
    Chunk,
    RetrievedChunk,
    _chunk_markdown,
    _chunk_json,
    _HashingBackend,
    _load_corpus,
)
from speech_processor.conversation_memory import ConversationMemory  # noqa: E402
from speech_processor.command_dispatcher import (  # noqa: E402
    CONVERSATIONAL_SYSTEM,
    ROBOT_CMD_SYSTEM_PROMPT,
    robot_cmd_system_prompt,
    conversational_system_with_kb,
    conversational_system_with_faces,
    conversational_system_with_scene,
    KB_GROUNDING_TEMPLATE,
    FACE_GROUNDING_TEMPLATE,
    SCENE_GROUNDING_TEMPLATE,
)
from speech_processor.voice_cmd_node import (  # noqa: E402
    _GOTO_RE,
    _APPROACH_RE,
    _COMPILED_TABLE,
    _OBJECT_CLASS_MAP,
)
from speech_processor.tts_node import (  # noqa: E402
    AudioCache,
    TTSConfig,
    TTSProvider,
    AudioFormat,
)


# ===========================================================================
# 3.1  LLM Persona & Prompt Composition
# ===========================================================================

class TestConversationalSystemPersona:
    """CONVERSATIONAL_SYSTEM — the robot's baseline persona prompt (Modul 3.1)."""

    def test_is_non_empty_string(self):
        assert isinstance(CONVERSATIONAL_SYSTEM, str) and CONVERSATIONAL_SYSTEM.strip()

    def test_robot_name_or_identity_present(self):
        assert "GO2" in CONVERSATIONAL_SYSTEM or "robot" in CONVERSATIONAL_SYSTEM.lower()

    def test_no_markdown_instruction(self):
        """TTS constraint: the persona tells the model to avoid markdown."""
        text = CONVERSATIONAL_SYSTEM.lower()
        assert "markdown" in text or "no list" in text or "short" in text

    def test_tts_length_constraint(self):
        """Persona should instruct short replies — important for TTS latency."""
        text = CONVERSATIONAL_SYSTEM.lower()
        assert "sentence" in text or "short" in text or "1" in text or "2" in text

    def test_capabilities_mentioned(self):
        """Persona should hint at physical capabilities so users know what to ask."""
        text = CONVERSATIONAL_SYSTEM.lower()
        assert any(w in text for w in ("move", "sit", "stand", "gait", "gesture"))


class TestRobotCmdSystemPrompt:
    """ROBOT_CMD_SYSTEM_PROMPT — the NLU parser prompt for all LLM providers (Modul 3.1)."""

    def test_is_non_empty_string(self):
        assert isinstance(ROBOT_CMD_SYSTEM_PROMPT, str) and ROBOT_CMD_SYSTEM_PROMPT.strip()

    def test_command_categories_present(self):
        text = ROBOT_CMD_SYSTEM_PROMPT.lower()
        for category_hint in ("sit", "stand", "forward", "backward", "trot"):
            assert category_hint in text, f"Expected command hint {category_hint!r} in prompt"

    def test_navigation_command_present(self):
        assert "go_to_room" in ROBOT_CMD_SYSTEM_PROMPT or "navigate" in ROBOT_CMD_SYSTEM_PROMPT.lower()

    def test_patrol_command_present(self):
        assert "patrol" in ROBOT_CMD_SYSTEM_PROMPT.lower()

    def test_approach_object_command_present(self):
        assert "approach_object" in ROBOT_CMD_SYSTEM_PROMPT

    def test_unknown_fallback_documented(self):
        assert "unknown" in ROBOT_CMD_SYSTEM_PROMPT.lower()

    def test_json_return_format_specified(self):
        assert "json" in ROBOT_CMD_SYSTEM_PROMPT.lower() or "{" in ROBOT_CMD_SYSTEM_PROMPT

    def test_robot_cmd_system_prompt_en_prepends_language(self):
        prompt = robot_cmd_system_prompt("en")
        assert "English" in prompt
        assert ROBOT_CMD_SYSTEM_PROMPT in prompt

    def test_robot_cmd_system_prompt_id_prepends_language(self):
        prompt = robot_cmd_system_prompt("id")
        assert "Indonesian" in prompt
        assert ROBOT_CMD_SYSTEM_PROMPT in prompt

    def test_language_statement_at_beginning(self):
        """The language line should come before the command list."""
        prompt_en = robot_cmd_system_prompt("en")
        lang_idx = prompt_en.index("English")
        cmd_idx  = prompt_en.index("sit")
        assert lang_idx < cmd_idx


class TestKBGroundingPrompt:
    """conversational_system_with_kb — RAG context injection (Modul 3.1 + 3.2)."""

    BASE = "You are GO2, a robot assistant."
    CTX  = "1. [info.md › Hours] Open Tuesday–Sunday 09:00–17:00.\n2. [info.md › Tickets] Adults 50k IDR."

    def test_output_contains_base(self):
        result = conversational_system_with_kb(self.BASE, self.CTX)
        assert self.BASE in result

    def test_output_contains_context(self):
        result = conversational_system_with_kb(self.BASE, self.CTX)
        assert self.CTX in result

    def test_output_longer_than_base(self):
        result = conversational_system_with_kb(self.BASE, self.CTX)
        assert len(result) > len(self.BASE)

    def test_venue_knowledge_label_present(self):
        result = conversational_system_with_kb(self.BASE, self.CTX)
        assert "VENUE KNOWLEDGE" in result or "venue" in result.lower()

    def test_prefer_facts_instruction_present(self):
        result = conversational_system_with_kb(self.BASE, self.CTX).lower()
        assert "prefer" in result or "use" in result or "ground" in result

    def test_different_base_produces_different_output(self):
        r1 = conversational_system_with_kb("Base A", self.CTX)
        r2 = conversational_system_with_kb("Base B", self.CTX)
        assert r1 != r2

    def test_template_uses_format_fields(self):
        """KB_GROUNDING_TEMPLATE must have {base} and {context} placeholders."""
        assert "{base}" in KB_GROUNDING_TEMPLATE
        assert "{context}" in KB_GROUNDING_TEMPLATE


class TestFaceGroundingPrompt:
    """conversational_system_with_faces — visual greeting injection (Modul 3.1 + 4.4)."""

    BASE  = "You are GO2."
    NAMES = "Alice, Bob"

    def test_output_contains_names(self):
        result = conversational_system_with_faces(self.BASE, self.NAMES)
        assert "Alice" in result and "Bob" in result

    def test_output_contains_base(self):
        result = conversational_system_with_faces(self.BASE, self.NAMES)
        assert self.BASE in result

    def test_output_longer_than_base(self):
        result = conversational_system_with_faces(self.BASE, self.NAMES)
        assert len(result) > len(self.BASE)

    def test_greet_instruction_present(self):
        result = conversational_system_with_faces(self.BASE, self.NAMES).lower()
        assert "greet" in result or "address" in result or "name" in result

    def test_template_uses_format_fields(self):
        assert "{base}" in FACE_GROUNDING_TEMPLATE
        assert "{names}" in FACE_GROUNDING_TEMPLATE


class TestSceneGroundingPrompt:
    """conversational_system_with_scene — live camera description injection (Modul 3.1 + 4.4)."""

    BASE  = "You are GO2."
    SCENE = "a lobby with two chairs and a reception desk"

    def test_output_contains_scene(self):
        result = conversational_system_with_scene(self.BASE, self.SCENE)
        assert self.SCENE in result

    def test_output_contains_base(self):
        result = conversational_system_with_scene(self.BASE, self.SCENE)
        assert self.BASE in result

    def test_visual_question_instruction_present(self):
        result = conversational_system_with_scene(self.BASE, self.SCENE).lower()
        assert "see" in result or "scene" in result or "visual" in result

    def test_no_force_mention_instruction(self):
        """Scene should only be used when the question is about it."""
        result = conversational_system_with_scene(self.BASE, self.SCENE).lower()
        assert "unless" in result or "only" in result or "not" in result

    def test_template_uses_format_fields(self):
        assert "{base}" in SCENE_GROUNDING_TEMPLATE
        assert "{scene}" in SCENE_GROUNDING_TEMPLATE

    def test_three_grounding_prompts_independent(self):
        """Applying KB, face, and scene grounding produces three distinct outputs."""
        kb   = conversational_system_with_kb("Base", "ctx")
        face = conversational_system_with_faces("Base", "Alice")
        scene= conversational_system_with_scene("Base", "a lobby")
        assert kb != face and face != scene and kb != scene


class TestKeywordNLURegexes:
    """Voice_cmd_node: _GOTO_RE and _APPROACH_RE offline keyword NLU (Modul 3.1)."""

    # --- _GOTO_RE (navigation) -------------------------------------------

    @pytest.mark.parametrize("text,expected_room", [
        ("go to the lobby",          "lobby"),
        ("go to lobby",              "lobby"),
        ("navigate to the kitchen",  "kitchen"),
        ("head to reception",        "reception"),
        ("take me to the garden",    "garden"),
    ])
    def test_goto_re_english(self, text, expected_room):
        m = _GOTO_RE.search(text)
        assert m is not None, f"_GOTO_RE did not match {text!r}"
        assert m.group("room").lower().startswith(expected_room.lower())

    @pytest.mark.parametrize("text,expected_room", [
        ("ke lobi",           "lobi"),
        ("pergi ke dapur",    "dapur"),
        ("menuju pintu masuk","pintu masuk"),
        ("antarkan ke ruang a","ruang a"),
    ])
    def test_goto_re_indonesian(self, text, expected_room):
        m = _GOTO_RE.search(text)
        assert m is not None, f"_GOTO_RE did not match {text!r}"
        assert m.group("room").lower().startswith(expected_room.split()[0].lower())

    def test_goto_re_no_match_plain_sentence(self):
        assert _GOTO_RE.search("what time is it?") is None
        assert _GOTO_RE.search("stand up") is None

    # --- _APPROACH_RE (object approach) -----------------------------------

    @pytest.mark.parametrize("text,expected_obj", [
        ("approach the chair",        "chair"),
        ("get close to the ball",     "ball"),
        ("go near the table",         "table"),
        ("walk to the bottle",        "bottle"),
        ("move toward the person",    "person"),
    ])
    def test_approach_re_english(self, text, expected_obj):
        m = _APPROACH_RE.search(text)
        assert m is not None, f"_APPROACH_RE did not match {text!r}"
        # Captured group may include "the" (e.g. "the chair") — check containment
        assert expected_obj.lower() in m.group("obj").lower()

    @pytest.mark.parametrize("text,expected_obj", [
        ("dekati bola",          "bola"),
        ("mendekati kursi",      "kursi"),
        ("cari orang",           "orang"),
        ("temukan anjing",       "anjing"),
    ])
    def test_approach_re_indonesian(self, text, expected_obj):
        m = _APPROACH_RE.search(text)
        assert m is not None, f"_APPROACH_RE did not match {text!r}"
        assert m.group("obj").lower().startswith(expected_obj.lower())

    def test_approach_re_no_match(self):
        assert _APPROACH_RE.search("go to lobby") is None
        assert _APPROACH_RE.search("sit down") is None

    # --- _OBJECT_CLASS_MAP ------------------------------------------------

    def test_indonesian_objects_map_to_yolo_classes(self):
        assert _OBJECT_CLASS_MAP["bola"] == "sports ball"
        assert _OBJECT_CLASS_MAP["kursi"] == "chair"
        assert _OBJECT_CLASS_MAP["orang"] == "person"
        assert _OBJECT_CLASS_MAP["anjing"] == "dog"
        assert _OBJECT_CLASS_MAP["kucing"] == "cat"

    def test_english_objects_also_in_map(self):
        assert _OBJECT_CLASS_MAP["chair"] == "chair"
        assert _OBJECT_CLASS_MAP["person"] == "person"
        assert _OBJECT_CLASS_MAP["dog"] == "dog"

    # --- _COMPILED_TABLE (EN keyword NLU) ---------------------------------

    @pytest.mark.parametrize("text,expected_action", [
        ("sit down",        {"api_id": 1009, "parameter": ""}),
        ("stand up",        {"api_id": 1004, "parameter": ""}),
        ("go forward",      ("move", 1.0, 0.0)),
        ("go backward",     ("move", -1.0, 0.0)),
        ("turn left",       ("move", 0.0, 1.0)),
        ("turn right",      ("move", 0.0, -1.0)),
        ("stop",            {"api_id": 1003, "parameter": ""}),
        ("trot",            {"api_id": 1011, "parameter": "1"}),
        ("slow down",       {"api_id": 1015, "parameter": "0"}),
        ("speed up",        {"api_id": 1015, "parameter": "2"}),
    ])
    def test_compiled_table_matches(self, text, expected_action):
        matched = None
        for pattern, action in _COMPILED_TABLE:
            if pattern.search(text):
                matched = action
                break
        assert matched == expected_action, (
            f"text={text!r}: got {matched!r}, expected {expected_action!r}"
        )

    def test_compiled_table_no_match_for_unknown(self):
        matched = None
        for pattern, action in _COMPILED_TABLE:
            if pattern.search("what is the weather today"):
                matched = action
                break
        assert matched is None

    def test_compiled_table_all_patterns_are_compiled(self):
        import re as _re
        for pattern, _ in _COMPILED_TABLE:
            assert hasattr(pattern, "search"), "Pattern is not a compiled regex"


# ===========================================================================
# 3.2  RAG Knowledge Base — corpus internals
# ===========================================================================

class TestChunkMarkdown:
    """_chunk_markdown — heading inheritance, list items, stub filtering."""

    def test_single_paragraph_no_heading(self):
        text = "The museum is open every day from nine to five."
        chunks = _chunk_markdown(text, "info.md")
        assert len(chunks) == 1
        assert chunks[0].source == "info.md"

    def test_heading_carried_into_source(self):
        text = "# Opening Hours\nOpen Tuesday to Sunday."
        chunks = _chunk_markdown(text, "info.md")
        assert len(chunks) == 1
        assert "Opening Hours" in chunks[0].source

    def test_multiple_headings_inherit_correctly(self):
        text = (
            "# Section A\nFirst paragraph about A.\n\n"
            "# Section B\nSecond paragraph about B."
        )
        chunks = _chunk_markdown(text, "doc.md")
        assert len(chunks) == 2
        assert "Section A" in chunks[0].source
        assert "Section B" in chunks[1].source

    def test_list_items_become_separate_chunks(self):
        text = (
            "# Rules\n"
            "- No flash photography.\n"
            "- No food in the galleries.\n"
        )
        chunks = _chunk_markdown(text, "rules.md")
        # Each list item should become its own chunk
        assert len(chunks) >= 2
        texts = [c.text for c in chunks]
        assert any("photography" in t.lower() for t in texts)
        assert any("food" in t.lower() for t in texts)

    def test_short_stubs_filtered(self):
        text = "# Title\nOK\n\nThe exhibit covers the Bronze Age history."
        chunks = _chunk_markdown(text, "stub.md")
        # "OK" is < 12 chars — filtered out
        assert all(len(c.text) >= 12 for c in chunks)

    def test_empty_text_returns_no_chunks(self):
        assert _chunk_markdown("", "empty.md") == []

    def test_only_headings_no_content_returns_no_chunks(self):
        text = "# Heading One\n## Heading Two\n"
        chunks = _chunk_markdown(text, "empty.md")
        assert chunks == []

    def test_heading_not_included_in_chunk_text(self):
        text = "# My Section\nThis is the body text of the section."
        chunks = _chunk_markdown(text, "doc.md")
        assert all("My Section" not in c.text for c in chunks)


class TestChunkJson:
    """_chunk_json — Q&A, string list, text-dict, mixed."""

    def test_faq_qa_format(self):
        data = {"faqs": [
            {"q": "Where is the cafe?", "a": "The cafe is on the second floor."},
            {"q": "What is the price?", "a": "Adults pay fifty thousand."},
        ]}
        chunks = _chunk_json(data, "faq.json")
        assert len(chunks) == 2
        assert all("Q:" in c.text and "A:" in c.text for c in chunks)

    def test_string_list_format(self):
        data = [
            "The museum has three floors.",
            "Guided tours run at 10 AM and 2 PM.",
        ]
        chunks = _chunk_json(data, "facts.json")
        assert len(chunks) == 2
        assert chunks[0].source == "facts.json"

    def test_text_dict_format(self):
        data = [
            {"text": "Audio guides are available in five languages.", "title": "Audio guides"},
        ]
        chunks = _chunk_json(data, "info.json")
        assert len(chunks) == 1
        assert "Audio guides" in chunks[0].text

    def test_short_items_filtered(self):
        # Q&A format prepends "Q: " / "A: " so even short answers become longer.
        # Use a plain string list with a stub that is genuinely < 12 chars.
        data = [
            "OK",   # 2 chars — filtered out
            "The guided tours run at ten in the morning and two in the afternoon.",
        ]
        chunks = _chunk_json(data, "facts.json")
        assert len(chunks) == 1
        assert "tours" in chunks[0].text.lower()

    def test_empty_list_returns_no_chunks(self):
        assert _chunk_json([], "empty.json") == []

    def test_empty_dict_returns_no_chunks(self):
        assert _chunk_json({}, "empty.json") == []

    def test_nested_faq_source_uses_filename(self):
        data = {"faqs": [{"q": "Where is parking?", "a": "Basement level B1."}]}
        chunks = _chunk_json(data, "venue_faq.json")
        assert all("venue_faq.json" in c.source for c in chunks)


class TestHashingBackend:
    """_HashingBackend — pure-numpy embedding backend used by unit tests."""

    @pytest.fixture
    def backend(self):
        return _HashingBackend(dim=512)

    def test_embed_documents_shape(self, backend):
        texts = ["The museum is open Tuesday to Sunday.", "Adult tickets cost fifty thousand."]
        matrix = backend.embed_documents(texts)
        assert matrix.shape == (2, 512)

    def test_embed_documents_normalized(self, backend):
        texts = ["Open Tuesday to Sunday.", "Tickets cost fifty thousand rupiah."]
        matrix = backend.embed_documents(texts)
        norms = np.linalg.norm(matrix, axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-5)

    def test_embed_query_shape(self, backend):
        vec = backend.embed_query("what time does it open?")
        assert vec.shape == (512,)

    def test_similar_texts_score_higher_than_dissimilar(self, backend):
        docs = [
            "The museum is open Tuesday to Sunday from nine to five.",
            "Adult admission costs fifty thousand rupiah.",
        ]
        matrix = backend.embed_documents(docs)
        q_open    = backend.embed_query("what are the opening hours?")
        q_tickets = backend.embed_query("how much is the ticket?")

        score_open_hours   = float(matrix[0] @ q_open)
        score_open_tickets = float(matrix[0] @ q_tickets)
        score_ticket_hours  = float(matrix[1] @ q_open)
        score_ticket_price  = float(matrix[1] @ q_tickets)

        # "opening hours" query should score higher against the hours doc than the ticket doc
        assert score_open_hours > score_ticket_hours, (
            "Hours query should rank hours doc above ticket doc"
        )
        # "ticket" query should score higher against the ticket doc
        assert score_ticket_price > score_open_tickets, (
            "Ticket query should rank ticket doc above hours doc"
        )

    def test_different_texts_produce_different_embeddings(self, backend):
        v1 = backend.embed_query("museum opening hours")
        v2 = backend.embed_query("ticket prices adult children")
        assert not np.allclose(v1, v2), "Different texts must not produce identical embeddings"

    def test_same_text_produces_identical_embeddings(self, backend):
        text = "The robot greets every visitor warmly."
        v1 = backend.embed_query(text)
        v2 = backend.embed_query(text)
        np.testing.assert_array_equal(v1, v2)

    def test_indonesian_text_embeds_non_zero(self, backend):
        vec = backend.embed_query("museum buka jam berapa?")
        assert float(np.linalg.norm(vec)) > 0.01

    def test_empty_string_embeds_to_zero(self, backend):
        vec = backend.embed_query("")
        # All-zero vector (no tokens to hash)
        assert float(np.linalg.norm(vec)) < 1e-6


class TestKBAdvanced:
    """KnowledgeBase — min_score filtering, bilingual queries, format_context."""

    @pytest.fixture
    def bilingual_kb(self, tmp_path):
        kb_dir = tmp_path / "bilingual"
        kb_dir.mkdir()
        (kb_dir / "hours.md").write_text(
            "# Jam Buka\n"
            "Museum buka Selasa sampai Minggu dari jam sembilan pagi hingga lima sore.\n\n"
            "# Opening Hours\n"
            "The museum is open Tuesday to Sunday from nine in the morning to five.\n\n"
            "# Tiket\n"
            "Tiket dewasa lima puluh ribu rupiah; anak-anak setengah harga.\n",
            encoding="utf-8",
        )
        return KnowledgeBase(
            path=str(kb_dir),
            embed_provider="hashing",
            cache_dir=str(tmp_path / "cache"),
            top_k=3,
        )

    def test_indonesian_query_returns_results(self, bilingual_kb):
        results = bilingual_kb.search("jam buka museum apa")
        assert results, "Expected results for Indonesian 'opening hours' query"

    def test_english_query_returns_results(self, bilingual_kb):
        results = bilingual_kb.search("what are the opening hours")
        assert results

    def test_min_score_filters_low_confidence(self, tmp_path):
        kb_dir = tmp_path / "small"
        kb_dir.mkdir()
        (kb_dir / "a.md").write_text(
            "# Topic\nThe robot stands in the lobby and greets visitors every morning.\n",
            encoding="utf-8",
        )
        kb = KnowledgeBase(
            path=str(kb_dir),
            embed_provider="hashing",
            cache_dir=str(tmp_path / "c"),
            min_score=0.999,   # effectively unreachable
        )
        results = kb.search("robot lobby greets")
        # Even a good match won't reach 0.999 cosine similarity
        assert results == [], "min_score=0.999 should filter everything out"

    def test_min_score_zero_returns_results(self, bilingual_kb):
        bilingual_kb.min_score = 0.0
        results = bilingual_kb.search("museum")
        assert results

    def test_format_context_multiple_chunks(self, bilingual_kb):
        results = bilingual_kb.search("museum", top_k=3)
        ctx = bilingual_kb.format_context(results)
        assert ctx.startswith("1.")
        if len(results) >= 2:
            assert "2." in ctx
        if len(results) >= 3:
            assert "3." in ctx

    def test_format_context_empty_returns_empty_string(self):
        assert KnowledgeBase.format_context([]) == ""

    def test_format_context_includes_source_tag(self, bilingual_kb):
        results = bilingual_kb.search("museum jam buka")
        ctx = bilingual_kb.format_context(results)
        # Every chunk's source should appear in square brackets
        assert "[" in ctx and "]" in ctx

    def test_cache_key_changes_when_content_changes(self, tmp_path):
        """Mutating corpus content must invalidate the disk cache."""
        kb_dir = tmp_path / "v"
        kb_dir.mkdir()
        f = kb_dir / "a.md"
        f.write_text("# T\nVersion one of the knowledge base.\n", encoding="utf-8")
        cache_dir = str(tmp_path / "cache")
        kb1 = KnowledgeBase(path=str(kb_dir), embed_provider="hashing", cache_dir=cache_dir)
        cache_file_v1 = kb1._cache_file()

        f.write_text("# T\nVersion two of the knowledge base — completely different.\n",
                     encoding="utf-8")
        kb2 = KnowledgeBase(path=str(kb_dir), embed_provider="hashing", cache_dir=cache_dir)
        cache_file_v2 = kb2._cache_file()

        assert cache_file_v1 != cache_file_v2, (
            "Cache key should differ when corpus content changes"
        )

    def test_search_empty_query_returns_empty(self, bilingual_kb):
        assert bilingual_kb.search("") == []
        assert bilingual_kb.search("   ") == []

    def test_search_top_k_respected(self, bilingual_kb):
        results = bilingual_kb.search("museum", top_k=1)
        assert len(results) == 1

    def test_retrieved_chunk_has_text_source_score(self, bilingual_kb):
        results = bilingual_kb.search("museum buka")
        assert results
        for r in results:
            assert isinstance(r.text, str) and r.text
            assert isinstance(r.source, str)
            assert isinstance(r.score, float)


# ===========================================================================
# 3.3  TTS infrastructure — AudioCache, TTSConfig, enums
# ===========================================================================

class TestAudioCache:
    """AudioCache — thread-safe LRU-like cache for TTS audio bytes (Modul 3.3)."""

    @pytest.fixture
    def cache(self, tmp_path):
        return AudioCache(cache_dir=str(tmp_path / "tts_cache"), enabled=True)

    @pytest.fixture
    def disabled_cache(self, tmp_path):
        return AudioCache(cache_dir=str(tmp_path / "tts_no_cache"), enabled=False)

    # --- deterministic key -----------------------------------------------

    def test_cache_path_deterministic(self, cache):
        p1 = cache.get_cache_path("hello", "F1", "supertonic")
        p2 = cache.get_cache_path("hello", "F1", "supertonic")
        assert p1 == p2

    def test_different_text_different_path(self, cache):
        p1 = cache.get_cache_path("hello", "F1", "supertonic")
        p2 = cache.get_cache_path("goodbye", "F1", "supertonic")
        assert p1 != p2

    def test_different_voice_different_path(self, cache):
        p1 = cache.get_cache_path("hello", "F1", "supertonic")
        p2 = cache.get_cache_path("hello", "M1", "supertonic")
        assert p1 != p2

    def test_different_provider_different_path(self, cache):
        p1 = cache.get_cache_path("hello", "F1", "supertonic")
        p2 = cache.get_cache_path("hello", "F1", "openai")
        assert p1 != p2

    def test_cache_path_ends_with_mp3(self, cache):
        p = cache.get_cache_path("hello", "F1", "supertonic")
        assert p.endswith(".mp3")

    # --- CRUD ------------------------------------------------------------

    def test_get_returns_none_when_empty(self, cache):
        assert cache.get("hello", "F1", "supertonic") is None

    def test_put_then_get_roundtrip(self, cache):
        audio = b"\xff\xfb\x90\x00" * 128  # fake MP3 header bytes
        assert cache.put("hello", "F1", "supertonic", audio)
        retrieved = cache.get("hello", "F1", "supertonic")
        assert retrieved == audio

    def test_put_empty_bytes_returns_false(self, cache):
        assert cache.put("hello", "F1", "supertonic", b"") is False

    def test_get_returns_none_for_different_key(self, cache):
        cache.put("hello", "F1", "supertonic", b"\x01\x02")
        assert cache.get("goodbye", "F1", "supertonic") is None

    def test_clear_removes_all_files(self, cache):
        cache.put("hello", "F1", "supertonic", b"\x01")
        cache.put("world", "F1", "supertonic", b"\x02")
        cache.clear()
        assert cache.get("hello", "F1", "supertonic") is None
        assert cache.get("world", "F1", "supertonic") is None

    # --- stats -----------------------------------------------------------

    def test_get_cache_stats_after_put(self, cache):
        cache.put("hi", "F1", "supertonic", b"\xaa\xbb" * 100)
        stats = cache.get_cache_stats()
        assert stats.get("enabled") is True
        assert stats.get("file_count", 0) >= 1

    def test_get_cache_stats_empty_cache(self, cache):
        stats = cache.get_cache_stats()
        assert stats.get("file_count", 0) == 0

    # --- disabled mode ---------------------------------------------------

    def test_disabled_cache_get_always_none(self, disabled_cache):
        assert disabled_cache.get("hello", "F1", "supertonic") is None

    def test_disabled_cache_put_returns_false(self, disabled_cache):
        result = disabled_cache.put("hello", "F1", "supertonic", b"\x01\x02")
        assert result is False

    def test_disabled_cache_get_after_put_is_none(self, disabled_cache):
        disabled_cache.put("hello", "F1", "supertonic", b"\x01\x02")
        assert disabled_cache.get("hello", "F1", "supertonic") is None

    def test_disabled_cache_stats_reports_disabled(self, disabled_cache):
        stats = disabled_cache.get_cache_stats()
        assert stats.get("enabled") is False


class TestTTSConfig:
    """TTSConfig dataclass defaults (Modul 3.3)."""

    def test_default_provider_is_supertonic(self):
        cfg = TTSConfig(api_key="")
        assert cfg.provider == TTSProvider.SUPERTONIC

    def test_default_language_is_english(self):
        cfg = TTSConfig(api_key="")
        assert cfg.language == "en"

    def test_default_local_playback_is_false(self):
        cfg = TTSConfig(api_key="")
        assert cfg.local_playback is False

    def test_default_use_cache_is_true(self):
        cfg = TTSConfig(api_key="")
        assert cfg.use_cache is True

    def test_custom_provider_accepted(self):
        cfg = TTSConfig(api_key="key", provider=TTSProvider.OPENAI)
        assert cfg.provider == TTSProvider.OPENAI

    def test_supertonic_steps_default(self):
        cfg = TTSConfig(api_key="")
        assert isinstance(cfg.supertonic_steps, int) and cfg.supertonic_steps > 0

    def test_api_key_stored(self):
        cfg = TTSConfig(api_key="my_secret_key")
        assert cfg.api_key == "my_secret_key"


class TestTTSProviderEnum:
    """TTSProvider — all providers required by proposal (Modul 3.3)."""

    def test_supertonic_exists(self):
        assert TTSProvider.SUPERTONIC.value == "supertonic"

    def test_openai_exists(self):
        assert TTSProvider.OPENAI.value == "openai"

    def test_elevenlabs_exists(self):
        assert TTSProvider.ELEVENLABS.value == "elevenlabs"

    def test_gemini_exists(self):
        assert TTSProvider.GEMINI.value == "gemini"

    def test_provider_enum_is_enum(self):
        from enum import Enum
        assert issubclass(TTSProvider, Enum)


class TestAudioFormatEnum:
    """AudioFormat enum — output format options (Modul 3.3)."""

    def test_mp3_exists(self):
        assert AudioFormat.MP3.value == "mp3"

    def test_wav_exists(self):
        assert AudioFormat.WAV.value == "wav"

    def test_ogg_exists(self):
        assert AudioFormat.OGG.value == "ogg"

    def test_is_enum(self):
        from enum import Enum
        assert issubclass(AudioFormat, Enum)


# ===========================================================================
# 3.4  Multi-turn conversation memory — edge cases
# ===========================================================================

class TestConversationMemoryEdgeCases:
    """Additional edge cases on top of test_conversation_memory.py (Modul 3.4)."""

    def test_explicit_clear_resets_turn_count(self):
        mem = ConversationMemory(max_turns=3)
        mem.add("hello", "Hi!", now=0.0)
        assert mem.num_turns == 1
        mem.clear()
        assert mem.num_turns == 0

    def test_explicit_clear_resets_last_activity(self):
        mem = ConversationMemory(max_turns=3, idle_timeout=60.0)
        mem.add("hello", "Hi!", now=0.0)
        mem.clear()
        # After clear, _last_activity is None, so no idle expiry can trigger
        assert mem._last_activity is None

    def test_add_after_explicit_clear_works(self):
        mem = ConversationMemory(max_turns=3)
        mem.add("first", "answer", now=0.0)
        mem.clear()
        mem.add("second", "answer2", now=1.0)
        assert mem.num_turns == 1
        hist = mem.history(now=2.0)
        assert hist == [("user", "second"), ("assistant", "answer2")]

    def test_add_after_expired_idle_starts_fresh(self):
        mem = ConversationMemory(max_turns=3, idle_timeout=10.0)
        mem.add("q1", "a1", now=0.0)
        # add() itself checks for expiry — expired window should clear before appending
        mem.add("q2", "a2", now=15.0)
        hist = mem.history(now=16.0)
        assert hist == [("user", "q2"), ("assistant", "a2")]

    def test_exactly_at_timeout_not_expired(self):
        """A conversation at exactly the timeout boundary is still valid."""
        mem = ConversationMemory(max_turns=3, idle_timeout=60.0)
        mem.add("q", "a", now=0.0)
        # exactly 60 s — _expired uses > (strict), so this should NOT be expired
        hist = mem.history(now=60.0)
        assert len(hist) == 2

    def test_just_past_timeout_is_expired(self):
        mem = ConversationMemory(max_turns=3, idle_timeout=60.0)
        mem.add("q", "a", now=0.0)
        hist = mem.history(now=60.001)
        assert hist == []

    def test_history_alternates_user_assistant_roles(self):
        mem = ConversationMemory(max_turns=5)
        mem.add("u1", "a1", now=0.0)
        mem.add("u2", "a2", now=1.0)
        mem.add("u3", "a3", now=2.0)
        hist = mem.history(now=3.0)
        roles = [r for r, _ in hist]
        assert roles == ["user", "assistant", "user", "assistant", "user", "assistant"]

    def test_history_content_order_is_chronological(self):
        mem = ConversationMemory(max_turns=5)
        for i in range(3):
            mem.add(f"q{i}", f"a{i}", now=float(i))
        hist = mem.history(now=4.0)
        contents = [c for _, c in hist]
        assert contents == ["q0", "a0", "q1", "a1", "q2", "a2"]

    def test_large_text_stored_and_returned_intact(self):
        mem = ConversationMemory(max_turns=3)
        big_q = "What is the history of the museum? " * 200
        big_a = "The museum was founded in 1905 and has grown to include over ten thousand artifacts. " * 200
        mem.add(big_q, big_a, now=0.0)
        hist = mem.history(now=1.0)
        assert hist[0] == ("user", big_q)
        assert hist[1] == ("assistant", big_a)

    def test_num_turns_tracks_through_eviction(self):
        mem = ConversationMemory(max_turns=2)
        mem.add("q1", "a1", now=0.0)
        assert mem.num_turns == 1
        mem.add("q2", "a2", now=1.0)
        assert mem.num_turns == 2
        mem.add("q3", "a3", now=2.0)
        # max_turns=2: oldest evicted
        assert mem.num_turns == 2

    def test_history_returns_list_of_2_tuples(self):
        mem = ConversationMemory(max_turns=3)
        mem.add("question", "answer", now=0.0)
        hist = mem.history(now=1.0)
        assert isinstance(hist, list)
        for item in hist:
            assert isinstance(item, tuple) and len(item) == 2
            assert item[0] in ("user", "assistant")
            assert isinstance(item[1], str)

    def test_negative_max_turns_treated_as_zero(self):
        mem = ConversationMemory(max_turns=-5)
        mem.add("q", "a", now=0.0)
        assert mem.num_turns == 0
        assert mem.history(now=1.0) == []

    def test_idle_timeout_negative_treated_as_no_reset(self):
        """Negative idle_timeout should never expire (boundary: condition is > 0)."""
        mem = ConversationMemory(max_turns=3, idle_timeout=-1.0)
        mem.add("q", "a", now=0.0)
        # A huge gap — should NOT expire because idle_timeout <= 0 means disabled
        hist = mem.history(now=999999.0)
        assert len(hist) == 2

    def test_first_history_call_on_fresh_instance_returns_empty(self):
        mem = ConversationMemory()
        assert mem.history() == []

    def test_history_usable_as_openai_messages(self):
        """history() format must be directly usable as OpenAI messages list."""
        mem = ConversationMemory(max_turns=3)
        mem.add("what time do you open?", "Nine to five, Tuesday to Sunday.", now=0.0)
        msgs = [{"role": role, "content": content} for role, content in mem.history(now=1.0)]
        assert msgs == [
            {"role": "user",      "content": "what time do you open?"},
            {"role": "assistant", "content": "Nine to five, Tuesday to Sunday."},
        ]
