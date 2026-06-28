#!/usr/bin/env python3

# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

"""
Face database — file-system enrollment store + cosine matcher (Modul 4.2).

Pure logic, no rclpy and no ROS2 message imports, so it is unit-testable
without a ROS2 environment (see test/unit/test_face_db.py). The recognition
*model* lives in the node; this module only stores and compares the 512-d
ArcFace embeddings the node feeds it.

Ported from the proven recognizer in the separate ``face-captioner`` project
(``recognizer/wrapper.py``): the same on-disk layout, ``.embeddings.pkl`` cache,
and cosine-similarity matching, adapted to consume embeddings supplied by
InsightFace's ``FaceAnalysis`` app instead of owning a recognition model.

On-disk layout::

    <db_path>/
    ├── Alice/
    │   ├── 0000.jpg
    │   └── 0001.jpg
    ├── Bob/
    │   └── 0000.jpg
    └── .embeddings.pkl        # dict[str, list[np.ndarray]] cache

Delete ``.embeddings.pkl`` to force a rebuild from the stored images.
"""

import pickle
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

_DB_CACHE_FILE = ".embeddings.pkl"
_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}

# Callable that turns a BGR image into a single L2-normalised embedding,
# or None when no face is found. Supplied by the node (wraps FaceAnalysis).
EmbedFn = Callable[[np.ndarray], Optional[np.ndarray]]


def _normalize(vec: np.ndarray) -> np.ndarray:
    """Return the L2-normalised vector (cosine similarity == dot product)."""
    vec = np.asarray(vec, dtype=np.float32).flatten()
    norm = float(np.linalg.norm(vec))
    return vec / norm if norm > 0.0 else vec


class FaceDB:
    """Enrollable face database with cosine matching against ArcFace embeddings.

    Parameters
    ----------
    db_path:    Directory holding ``<Name>/*.jpg`` folders and the embedding cache.
    threshold:  Minimum cosine similarity to accept a match; below it the face is
                reported as ``"Unknown"``. Default 0.35 (the face-captioner value).
    """

    def __init__(self, db_path: str, threshold: float = 0.35):
        self.db_path = Path(db_path)
        self.threshold = float(threshold)
        self._db: Dict[str, List[np.ndarray]] = {}

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _cache_path(self) -> Path:
        return self.db_path / _DB_CACHE_FILE

    def load(self, embed_fn: Optional[EmbedFn] = None) -> None:
        """Load the cache, or rebuild from images if no cache exists.

        With no cache and no ``embed_fn`` the database starts empty (faces can
        still be enrolled live via :meth:`add_face`).
        """
        self.db_path.mkdir(parents=True, exist_ok=True)
        cache = self._cache_path()
        if cache.exists():
            try:
                with open(cache, "rb") as fh:
                    self._db = pickle.load(fh)
                return
            except Exception:
                # Corrupt cache — fall through to a rebuild.
                self._db = {}
        if embed_fn is not None:
            self.rebuild_from_disk(embed_fn)

    def rebuild_from_disk(self, embed_fn: EmbedFn) -> int:
        """Re-scan ``<db_path>/<Name>/*`` and recompute every embedding.

        Returns the number of face images successfully embedded. Images in
        which no face is detected are skipped.
        """
        import cv2  # local import — keeps this module importable without cv2

        self.db_path.mkdir(parents=True, exist_ok=True)
        self._db = {}
        embedded = 0
        for person_dir in sorted(p for p in self.db_path.iterdir() if p.is_dir()):
            embeddings: List[np.ndarray] = []
            for img_path in sorted(person_dir.iterdir()):
                if img_path.suffix.lower() not in _IMAGE_SUFFIXES:
                    continue
                img = cv2.imread(str(img_path))
                if img is None:
                    continue
                emb = embed_fn(img)
                if emb is None:
                    continue
                embeddings.append(_normalize(emb))
                embedded += 1
            if embeddings:
                self._db[person_dir.name] = embeddings
        self._save_cache()
        return embedded

    def _save_cache(self) -> None:
        self.db_path.mkdir(parents=True, exist_ok=True)
        with open(self._cache_path(), "wb") as fh:
            pickle.dump(self._db, fh)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def identify(self, embedding: np.ndarray) -> Tuple[str, float]:
        """Return ``(name, similarity)`` for the best DB match.

        ``name`` is ``"Unknown"`` when the best similarity is below
        ``threshold`` or the database is empty.
        """
        query = _normalize(embedding)
        best_name, best_sim = "Unknown", 0.0
        for name, known in self._db.items():
            for ref in known:
                sim = float(np.dot(query, ref))
                if sim > best_sim:
                    best_sim, best_name = sim, name
        if best_sim < self.threshold:
            return "Unknown", best_sim
        return best_name, best_sim

    def add_face(self, name: str, crop_bgr: np.ndarray, embedding: np.ndarray) -> None:
        """Enroll a face: persist the crop and append its embedding to the cache.

        The image is written so a later :meth:`rebuild_from_disk` can recover the
        embedding by re-detection; the node should pass a crop with some margin
        around the face.
        """
        import cv2  # local import — see rebuild_from_disk

        person_dir = self.db_path / name
        person_dir.mkdir(parents=True, exist_ok=True)
        idx = len(list(person_dir.glob("*.jpg")))
        cv2.imwrite(str(person_dir / f"{idx:04d}.jpg"), crop_bgr)

        self._db.setdefault(name, []).append(_normalize(embedding))
        self._save_cache()

    @property
    def known_names(self) -> List[str]:
        return list(self._db.keys())

    @property
    def num_faces(self) -> int:
        return sum(len(v) for v in self._db.values())
