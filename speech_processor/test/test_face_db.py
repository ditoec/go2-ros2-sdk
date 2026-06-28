#!/usr/bin/env python3

# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

"""
Unit tests for the enrollable face database (Modul 4.2).

Pure pytest — no ``rclpy`` and no recognition model (per .claude/rules/testing.md).
Embeddings are hand-built unit vectors so cosine matching, the threshold, and the
``.embeddings.pkl`` persistence are tested deterministically without InsightFace.
"""

import numpy as np
import pytest

from speech_processor.face_db import FaceDB


def _unit(*vals) -> np.ndarray:
    """A small L2-normalised embedding for deterministic cosine tests."""
    v = np.asarray(vals, dtype=np.float32)
    return v / np.linalg.norm(v)


def test_empty_db_returns_unknown(tmp_path):
    db = FaceDB(str(tmp_path), threshold=0.35)
    db.load()
    name, sim = db.identify(_unit(1, 0, 0))
    assert name == "Unknown"
    assert sim == 0.0


def test_identify_matches_enrolled_face(tmp_path):
    db = FaceDB(str(tmp_path), threshold=0.35)
    db.load()
    crop = np.zeros((64, 64, 3), dtype=np.uint8)
    db.add_face("Alice", crop, _unit(1, 0, 0))

    # Near-identical embedding → recognized as Alice.
    name, sim = db.identify(_unit(0.99, 0.01, 0))
    assert name == "Alice"
    assert sim > 0.9


def test_below_threshold_is_unknown(tmp_path):
    db = FaceDB(str(tmp_path), threshold=0.5)
    db.load()
    db.add_face("Alice", np.zeros((64, 64, 3), dtype=np.uint8), _unit(1, 0, 0))

    # Orthogonal embedding → similarity 0 < threshold → Unknown.
    name, sim = db.identify(_unit(0, 1, 0))
    assert name == "Unknown"


def test_picks_best_of_multiple_people(tmp_path):
    db = FaceDB(str(tmp_path), threshold=0.35)
    db.load()
    db.add_face("Alice", np.zeros((8, 8, 3), dtype=np.uint8), _unit(1, 0, 0))
    db.add_face("Bob", np.zeros((8, 8, 3), dtype=np.uint8), _unit(0, 1, 0))

    name, _ = db.identify(_unit(0.1, 1.0, 0))
    assert name == "Bob"


def test_enrollment_persists_to_cache(tmp_path):
    crop = np.zeros((8, 8, 3), dtype=np.uint8)
    db = FaceDB(str(tmp_path), threshold=0.35)
    db.load()
    db.add_face("Alice", crop, _unit(1, 0, 0))
    assert "Alice" in db.known_names
    assert (tmp_path / ".embeddings.pkl").exists()
    assert (tmp_path / "Alice" / "0000.jpg").exists()

    # A fresh instance reads the cache without re-embedding.
    db2 = FaceDB(str(tmp_path), threshold=0.35)
    db2.load()
    assert db2.known_names == ["Alice"]
    assert db2.num_faces == 1
    name, _ = db2.identify(_unit(1, 0, 0))
    assert name == "Alice"


def test_add_face_appends_incrementing_filenames(tmp_path):
    db = FaceDB(str(tmp_path), threshold=0.35)
    db.load()
    crop = np.zeros((8, 8, 3), dtype=np.uint8)
    db.add_face("Alice", crop, _unit(1, 0, 0))
    db.add_face("Alice", crop, _unit(0.9, 0.1, 0))
    assert (tmp_path / "Alice" / "0000.jpg").exists()
    assert (tmp_path / "Alice" / "0001.jpg").exists()
    assert db.num_faces == 2
