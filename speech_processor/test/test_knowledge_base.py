#!/usr/bin/env python3

# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

"""
Unit tests for the knowledge-base retriever (Modul 3.2).

Pure pytest — no ``rclpy``, no ROS2 messages (per .claude/rules/testing.md). Uses
the dependency-free ``hashing`` embedding backend so the tests are hermetic and
deterministic regardless of whether sentence-transformers is installed.
"""

import json

import pytest

from speech_processor.knowledge_base import KnowledgeBase


@pytest.fixture
def venue_kb(tmp_path):
    """A small bilingual KB built with the deterministic hashing backend."""
    kb_dir = tmp_path / "venue"
    kb_dir.mkdir()
    (kb_dir / "info.md").write_text(
        "# Opening hours\n"
        "The museum is open Tuesday to Sunday from nine in the morning to five.\n\n"
        "# Tickets\n"
        "Adult admission costs fifty thousand rupiah; children pay half price.\n\n"
        "# Facilities\n"
        "Toilets are on the ground floor next to the main staircase.\n",
        encoding="utf-8",
    )
    (kb_dir / "faq.json").write_text(
        json.dumps({"faqs": [
            {"q": "Where is the cafe?", "a": "The cafe is on the second floor."},
        ]}),
        encoding="utf-8",
    )
    return KnowledgeBase(
        path=str(kb_dir),
        embed_provider="hashing",
        cache_dir=str(tmp_path / "cache"),
    )


def test_kb_loads_and_chunks(venue_kb):
    assert venue_kb.available
    # 3 markdown paragraphs + 1 FAQ entry.
    assert venue_kb.num_chunks == 4


def test_retrieves_relevant_chunk(venue_kb):
    results = venue_kb.search("what are the opening hours?")
    assert results
    assert "open" in results[0].text.lower()
    assert results[0].source.endswith("Opening hours")


def test_retrieves_from_json_faq(venue_kb):
    results = venue_kb.search("where can I find the cafe?")
    assert results
    assert "cafe" in results[0].text.lower()


def test_top_k_limit(venue_kb):
    assert len(venue_kb.search("toilet", top_k=2)) <= 2


def test_format_context_is_citable(venue_kb):
    ctx = venue_kb.format_context(venue_kb.search("tickets price"))
    assert ctx and ctx.strip()[0] == "1"  # numbered, citable block


def test_empty_directory_is_unavailable(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    kb = KnowledgeBase(path=str(empty), embed_provider="hashing",
                       cache_dir=str(tmp_path / "c"))
    assert not kb.available
    assert kb.search("anything") == []


def test_missing_path_is_unavailable(tmp_path):
    kb = KnowledgeBase(path=str(tmp_path / "does_not_exist"),
                       embed_provider="hashing", cache_dir=str(tmp_path / "c"))
    assert not kb.available


def test_embedding_cache_roundtrip(tmp_path):
    """A second KB over the same corpus loads embeddings from the disk cache."""
    kb_dir = tmp_path / "v"
    kb_dir.mkdir()
    (kb_dir / "a.md").write_text("# T\nThe robot greets every visitor warmly.\n",
                                 encoding="utf-8")
    cache = str(tmp_path / "cache")
    first = KnowledgeBase(path=str(kb_dir), embed_provider="hashing", cache_dir=cache)
    second = KnowledgeBase(path=str(kb_dir), embed_provider="hashing", cache_dir=cache)
    assert first.available and second.available
    r1 = first.search("greet visitor")
    r2 = second.search("greet visitor")
    assert r1 and r2
    assert r1[0].text == r2[0].text
