#!/usr/bin/env python3

# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

"""
Knowledge base retrieval (RAG) for venue Q&A — pure Python, no ROS2 imports.

Implements the lightweight embedding-RAG approach from
``docs/knowledge-base-options.md`` (Option 2): a small embedding model turns each
KB chunk and the incoming question into a vector, and the best-matching snippets
are returned for the conversational LLM to ground its answer on. Designed for the
small, simple corpora a robot meets in the field (a museum's exhibits, an
amusement park's attractions, a brand launch event) — tens to a few hundred short
facts per venue — so brute-force cosine search over an in-memory matrix is exact
and sub-millisecond. No vector database, no server.

This module deliberately contains **no ``rclpy`` or ROS2 message imports** so it
stays unit-testable without a ROS2 environment (see ``test/test_knowledge_base.py``).
``voice_cmd_node`` owns the ROS2 wiring and injects the retrieved context into the
conversational prompt.

Embedding backends (selected by ``embed_provider``)
---------------------------------------------------
``local``  : sentence-transformers, default ``intfloat/multilingual-e5-small`` —
             handles Indonesian + English in one index (matches ``VOICE_LANG=id``).
``openai`` : OpenAI ``text-embedding-3-small`` — no local model, reuses the
             ``OPENAI_API_KEY`` already in the stack (~100-300 ms network/query).
``hashing``: pure-numpy character-n-gram fallback — zero extra dependencies, used
             automatically when neither of the above is available, and by the unit
             tests for determinism. Lower quality, but keeps the feature working.

Corpus files (any mix, loaded recursively from the KB directory)
----------------------------------------------------------------
``.md`` / ``.markdown`` / ``.txt`` : split into paragraphs; the nearest preceding
                                     Markdown heading is kept as the chunk's source
                                     label so retrieved snippets carry context.
``.json``                          : a list of strings, a list of ``{"text", ...}``
                                     objects, or ``{"faqs": [{"q", "a"}, ...]}``.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

import numpy as np

logger = logging.getLogger(__name__)

_TEXT_EXTS = (".md", ".markdown", ".txt")
_DEFAULT_LOCAL_MODEL = "intfloat/multilingual-e5-small"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Chunk:
    """A single retrievable unit of knowledge."""
    text: str
    source: str = ""           # e.g. "exhibits.md › Opening hours"


@dataclass
class RetrievedChunk:
    """A chunk paired with its similarity score for a query."""
    text: str
    source: str
    score: float


@dataclass
class _Corpus:
    chunks: List[Chunk] = field(default_factory=list)
    fingerprint: str = ""      # hash of file contents — invalidates the cache


# ---------------------------------------------------------------------------
# Embedding backends
# ---------------------------------------------------------------------------

class _EmbeddingBackend:
    """Strategy interface. ``name`` participates in the cache key."""

    name: str = "base"

    def embed_documents(self, texts: Sequence[str]) -> np.ndarray:
        raise NotImplementedError

    def embed_query(self, text: str) -> np.ndarray:
        return self.embed_documents([text])[0]


class _SentenceTransformerBackend(_EmbeddingBackend):
    """Local CPU embeddings via sentence-transformers (recommended path)."""

    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer  # lazy, optional dep

        self._model = SentenceTransformer(model_name)
        self._is_e5 = "e5" in model_name.lower()  # e5 wants query:/passage: prefixes
        self.name = f"st:{model_name}"

    def _encode(self, texts: Sequence[str], prefix: str) -> np.ndarray:
        if self._is_e5:
            texts = [f"{prefix}{t}" for t in texts]
        vecs = self._model.encode(
            list(texts), normalize_embeddings=True, show_progress_bar=False
        )
        return np.asarray(vecs, dtype=np.float32)

    def embed_documents(self, texts: Sequence[str]) -> np.ndarray:
        return self._encode(texts, "passage: ")

    def embed_query(self, text: str) -> np.ndarray:
        return self._encode([text], "query: ")[0]


class _OpenAIEmbeddingBackend(_EmbeddingBackend):
    """Cloud embeddings — no local model, reuses the OpenAI key."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        import openai  # lazy, optional dep

        self._client = openai.OpenAI(api_key=api_key)
        self._model = model
        self.name = f"openai:{model}"

    def embed_documents(self, texts: Sequence[str]) -> np.ndarray:
        resp = self._client.embeddings.create(model=self._model, input=list(texts))
        vecs = np.asarray([d.embedding for d in resp.data], dtype=np.float32)
        # Normalise so a plain dot product is cosine similarity.
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        return vecs / np.clip(norms, 1e-8, None)


class _HashingBackend(_EmbeddingBackend):
    """Pure-numpy bag-of-words + character-n-gram fallback — deterministic, deps-free.

    Not as good as a real embedding model (it is lexical, not semantic), but
    language-agnostic at the character level (so Indonesian and English both hash),
    and it keeps the KB working — and the unit tests hermetic — when no model is
    installed. Stopwords are dropped so common function words ("the", "yang") don't
    dominate the similarity, and exact word matches are weighted above fuzzy
    character-trigram overlap.
    """

    # Small English + Indonesian function-word list — enough to stop the most
    # common words from drowning out content terms in lexical matching.
    _STOPWORDS = frozenset((
        "a an and are as at be by for from how in is it of on or that the this to "
        "was what when where which who will with you your do does "
        "yang di ke dari dan atau apa kapan dimana adalah ini itu untuk pada "
        "dengan ada saya kamu apakah bisa"
    ).split())

    def __init__(self, dim: int = 1024):
        self._dim = dim
        self.name = f"hash:{dim}"

    @classmethod
    def _tokens(cls, text: str) -> List[tuple]:
        """Return (token, weight) pairs: weighted word tokens + char trigrams."""
        words = [w for w in re.findall(r"\w+", text.lower(), re.UNICODE)
                 if len(w) > 1 and w not in cls._STOPWORDS]
        out: List[tuple] = []
        for w in words:
            out.append((f"w:{w}", 2.0))  # exact word match dominates
            padded = f"#{w}#"
            out.extend((padded[i:i + 3], 1.0) for i in range(len(padded) - 2))
        return out

    def _embed_one(self, text: str) -> np.ndarray:
        vec = np.zeros(self._dim, dtype=np.float32)
        for tok, weight in self._tokens(text):
            h = hashlib.md5(tok.encode("utf-8")).digest()
            idx = int.from_bytes(h[:8], "little") % self._dim
            sign = 1.0 if h[8] & 1 else -1.0
            vec[idx] += sign * weight
        norm = float(np.linalg.norm(vec))
        return vec / norm if norm > 1e-8 else vec

    def embed_documents(self, texts: Sequence[str]) -> np.ndarray:
        return np.vstack([self._embed_one(t) for t in texts]).astype(np.float32)


def _build_backend(embed_provider: str, model_name: str, api_key: str) -> _EmbeddingBackend:
    """Build the requested backend, degrading gracefully if deps/keys are missing."""
    provider = (embed_provider or "local").lower()

    if provider == "local":
        try:
            return _SentenceTransformerBackend(model_name or _DEFAULT_LOCAL_MODEL)
        except Exception as exc:  # ImportError or model download failure
            logger.warning(
                "KB: sentence-transformers unavailable (%s); trying OpenAI/hashing", exc
            )
            provider = "openai" if api_key else "hashing"

    if provider == "openai":
        try:
            return _OpenAIEmbeddingBackend(api_key)
        except Exception as exc:
            logger.warning("KB: OpenAI embeddings unavailable (%s); using hashing", exc)
            provider = "hashing"

    return _HashingBackend()


# ---------------------------------------------------------------------------
# Corpus loading / chunking
# ---------------------------------------------------------------------------

def _chunk_markdown(text: str, filename: str) -> List[Chunk]:
    """Split text/markdown into paragraph chunks, tagging each with its heading."""
    chunks: List[Chunk] = []
    heading = ""
    buf: List[str] = []

    def flush() -> None:
        para = " ".join(buf).strip()
        buf.clear()
        if len(para) < 12:  # skip stubs / lone punctuation
            return
        source = f"{filename} › {heading}" if heading else filename
        chunks.append(Chunk(text=para, source=source))

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            flush()
            continue
        if line.startswith("#"):
            flush()
            heading = line.lstrip("#").strip()
            continue
        # Treat Markdown list items as their own chunks for crisp retrieval.
        if line[:2] in ("- ", "* ") or (line[:2].isdigit() and ". " in line[:4]):
            flush()
            buf.append(line.lstrip("-*0123456789. ").strip())
            flush()
            continue
        buf.append(line)
    flush()
    return chunks


def _chunk_json(data, filename: str) -> List[Chunk]:
    chunks: List[Chunk] = []
    items = data.get("faqs", data) if isinstance(data, dict) else data
    if not isinstance(items, list):
        return chunks
    for item in items:
        if isinstance(item, str):
            text, source = item, filename
        elif isinstance(item, dict):
            if "q" in item and "a" in item:
                text = f"Q: {item['q']}\nA: {item['a']}"
            else:
                text = str(item.get("text", "")).strip()
            source = str(item.get("source", item.get("title", filename)))
        else:
            continue
        if len(text.strip()) >= 12:
            chunks.append(Chunk(text=text.strip(), source=source))
    return chunks


def _load_corpus(path: str) -> _Corpus:
    """Load and chunk every supported file under ``path`` (recursively)."""
    corpus = _Corpus()
    hasher = hashlib.md5()
    if not path or not os.path.isdir(path):
        return corpus

    for root, _dirs, files in os.walk(path):
        for name in sorted(files):
            ext = os.path.splitext(name)[1].lower()
            full = os.path.join(root, name)
            rel = os.path.relpath(full, path)
            try:
                with open(full, "r", encoding="utf-8") as fh:
                    content = fh.read()
            except (OSError, UnicodeDecodeError) as exc:
                logger.warning("KB: skipping %s (%s)", rel, exc)
                continue

            if ext in _TEXT_EXTS:
                corpus.chunks.extend(_chunk_markdown(content, rel))
            elif ext == ".json":
                try:
                    corpus.chunks.extend(_chunk_json(json.loads(content), rel))
                except json.JSONDecodeError as exc:
                    logger.warning("KB: bad JSON in %s (%s)", rel, exc)
                    continue
            else:
                continue
            hasher.update(rel.encode("utf-8"))
            hasher.update(content.encode("utf-8"))

    corpus.fingerprint = hasher.hexdigest()
    return corpus


# ---------------------------------------------------------------------------
# Knowledge base
# ---------------------------------------------------------------------------

class KnowledgeBase:
    """In-memory semantic index over a venue's knowledge directory.

    Embeds every chunk once at construction (cached to disk keyed by the corpus
    fingerprint + backend, so restarts are instant), then answers ``search`` with
    brute-force cosine similarity.
    """

    def __init__(
        self,
        path: str,
        embed_provider: str = "local",
        model_name: str = _DEFAULT_LOCAL_MODEL,
        api_key: str = "",
        top_k: int = 3,
        min_score: float = 0.0,
        cache_dir: Optional[str] = None,
    ):
        self.path = path
        self.top_k = max(1, int(top_k))
        self.min_score = float(min_score)
        self._cache_dir = cache_dir or os.path.join(
            os.path.expanduser("~"), ".cache", "go2_robot_sdk", "kb"
        )

        self._corpus = _load_corpus(path)
        self._matrix: Optional[np.ndarray] = None
        self._backend: Optional[_EmbeddingBackend] = None

        if not self._corpus.chunks:
            logger.warning("KB: no usable documents found under %r", path)
            return

        self._backend = _build_backend(embed_provider, model_name, api_key)
        self._matrix = self._embed_corpus()
        logger.info(
            "KB ready — %d chunks from %r, backend=%s",
            len(self._corpus.chunks), path, self._backend.name,
        )

    # -- public API --------------------------------------------------------

    @property
    def available(self) -> bool:
        """True when the index is populated and queryable."""
        return self._matrix is not None and len(self._corpus.chunks) > 0

    @property
    def num_chunks(self) -> int:
        return len(self._corpus.chunks)

    def search(self, query: str, top_k: Optional[int] = None) -> List[RetrievedChunk]:
        """Return the best-matching chunks for ``query``, highest score first."""
        if not self.available or not query.strip():
            return []
        k = max(1, int(top_k)) if top_k else self.top_k

        q_vec = self._backend.embed_query(query)
        scores = self._matrix @ q_vec  # cosine: rows are normalised
        order = np.argsort(-scores)[:k]
        out: List[RetrievedChunk] = []
        for idx in order:
            score = float(scores[idx])
            if score < self.min_score:
                continue
            chunk = self._corpus.chunks[idx]
            out.append(RetrievedChunk(text=chunk.text, source=chunk.source, score=score))
        return out

    @staticmethod
    def format_context(results: Sequence[RetrievedChunk]) -> str:
        """Render retrieved chunks as a compact, citable context block."""
        lines = []
        for i, r in enumerate(results, 1):
            tag = f" [{r.source}]" if r.source else ""
            lines.append(f"{i}.{tag} {r.text}")
        return "\n".join(lines)

    # -- internals ---------------------------------------------------------

    def _embed_corpus(self) -> np.ndarray:
        cached = self._load_cache()
        if cached is not None:
            return cached
        texts = [c.text for c in self._corpus.chunks]
        matrix = self._backend.embed_documents(texts).astype(np.float32)
        self._save_cache(matrix)
        return matrix

    def _cache_file(self) -> str:
        key = hashlib.md5(
            f"{self._corpus.fingerprint}|{self._backend.name}".encode("utf-8")
        ).hexdigest()
        return os.path.join(self._cache_dir, f"{key}.npz")

    def _load_cache(self) -> Optional[np.ndarray]:
        cache_file = self._cache_file()
        if not os.path.isfile(cache_file):
            return None
        try:
            with np.load(cache_file) as data:
                matrix = data["matrix"]
            if matrix.shape[0] == len(self._corpus.chunks):
                logger.info("KB: loaded embedding cache %s", cache_file)
                return matrix.astype(np.float32)
        except Exception as exc:
            logger.warning("KB: ignoring unreadable cache %s (%s)", cache_file, exc)
        return None

    def _save_cache(self, matrix: np.ndarray) -> None:
        try:
            os.makedirs(self._cache_dir, exist_ok=True)
            np.savez(self._cache_file(), matrix=matrix)
        except OSError as exc:
            logger.warning("KB: could not write embedding cache (%s)", exc)
