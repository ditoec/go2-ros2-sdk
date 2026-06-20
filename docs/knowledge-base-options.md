# Custom Knowledge Base for the GO2 — Options & Comparison

How to give the robot venue-specific knowledge (museum exhibits, amusement-park
attractions, a brand's launch event) so it can answer visitor questions in its
voice loop — and how to store and query that knowledge **fast and cheaply on edge
hardware**.

> **TL;DR.** The corpus here is small and simple (tens to a few hundred short
> facts per venue), not hundred-page PDFs. At that scale a server vector DB and an
> LLM-reasoning retriever like **OpenKB are both overkill for the robot's hot
> path.** Use a **lightweight embedding RAG** — a small multilingual embedding
> model + a file-based index (sqlite-vec / FAISS-flat / numpy), exposed as a
> `search_knowledge_base` tool inside the conversational loop that already exists
> in [`voice_cmd_node.py`](../speech_processor/speech_processor/voice_cmd_node.py).
> Keep **OpenKB as an *offline authoring* tool** to turn messy brochures/PDFs into
> a clean wiki you then index. Details below.

---

## 1. What we're actually building, and the constraints that decide it

The robot already has a conversational fallback: when speech doesn't match a motion
command, [`voice_cmd_node`](../speech_processor/speech_processor/voice_cmd_node.py)
calls `_ask_conversational()`, which runs an OpenAI-style **tool-call loop** —
today the only tool is `search_web` (DuckDuckGo). This works across the
`openai`, `gemini`, and `gemma_local` (llama.cpp) NLU providers.

**This is the integration point.** A knowledge base is just one more retrieval
source. Two ways to wire it in:

- **(a) As a tool** — add a `search_knowledge_base` function alongside `search_web`;
  the LLM decides when to call it. Cleanest, model-agnostic, already supported by
  the loop.
- **(b) As injected context** — retrieve top-_k_ snippets *before* the LLM call and
  prepend them to `CONVERSATIONAL_SYSTEM`. Simpler, one fewer round-trip, but
  retrieves on every turn whether needed or not.

Four constraints set the answer:

| Constraint | Value here | Consequence |
|---|---|---|
| **Corpus size** | Tens–hundreds of short paragraphs per venue ("not very complicated") | Storage and ANN indexing are non-issues; brute-force search is sub-millisecond |
| **Latency budget** | Voice UX wants an answer in ~1–3 s, on top of STT+NLU+TTS | Retrieval must add **tens of ms, not seconds**. Rules out per-query LLM-reasoning retrieval on edge |
| **Compute** | Shared Jetson NX 16 GB / Win 8 GB GPU; GPU already busy with gemma + whisper + YOLO | Prefer **CPU-only** retrieval or a tiny model; don't add GPU contention |
| **Language** | `VOICE_LANG=id` is a first-class mode | Retriever must handle **Indonesian + English**; pushes toward a *multilingual embedding* model over pure keyword match |

The corpus-size point is the crux. PageIndex/OpenKB exist to navigate **long**
documents that don't fit a context window. A museum's facts are short — a single
exhibit is a paragraph. If a whole venue fits in ~3–8k tokens you barely need
retrieval at all (see Option 0); if it doesn't, cheap semantic search closes the
gap without putting an LLM in the retrieval path.

---

## 2. The option spectrum (simplest → heaviest)

### Option 0 — No retrieval: stuff the KB into the system prompt
Put the entire venue KB into the conversational system prompt as static context.

- **Complexity:** trivial — a text file loaded at launch.
- **Speed:** fastest possible — *zero* retrieval step.
- **Compute/storage:** none beyond the file; you pay the KB's tokens on **every**
  LLM call instead.
- **Limit:** only works while the KB fits comfortably in context (rough ceiling
  ~50–100 short facts / a few thousand tokens, and *less* for `gemma e4b` whose
  context and instruction-following are weaker). Token cost per query grows with
  the KB.
- **Verdict:** the right starting point for a **single small venue**. Ship this
  first; add retrieval only when the KB outgrows the prompt.

### Option 1 — Keyword / BM25 / SQLite FTS5 (no ML)
Tokenize the query, retrieve top-_k_ chunks by lexical overlap, inject them.
Use `rank_bm25` (pure Python) or SQLite's built-in `FTS5`.

- **Complexity:** low. No model, no embeddings, no extra service.
- **Code efficiency:** ~50 lines. SQLite FTS5 ships with Python's `sqlite3`.
- **Speed:** sub-millisecond on CPU at this scale.
- **Compute:** negligible CPU; **no GPU, no model download**.
- **Storage:** the text + a small inverted index (single-digit MB).
- **Limit:** lexical only — misses synonyms/paraphrase, and **mixes poorly with
  Indonesian↔English** ("where's the toilet" vs "di mana toilet"). Visitors phrase
  questions unpredictably, so recall suffers.
- **Verdict:** great zero-dependency fallback; weak for multilingual free-form
  questions.

### Option 2 — Lightweight embedding RAG (recommended) ⭐
A small embedding model turns each chunk and the query into a vector; retrieve by
cosine similarity from an in-process index.

- **Complexity:** low–moderate. One model + a flat index. No server.
- **Index choice at this scale:**
  - **numpy brute force** — `cos_sim` over a `(N, d)` matrix. For N < ~10k this is
    exact and <1 ms. Honestly enough.
  - **FAISS `IndexFlatL2`** — exact, slightly faster, trivial API.
  - **sqlite-vec** — vector search as a SQLite extension; one file, metadata
    filtering (e.g. `WHERE venue='museum_a'`), incremental inserts.
  - **LanceDB** — embedded columnar vector store, file-based, nice if you want
    versioning/filters without a server.
- **Embedding model (CPU-friendly, pick for language):**
  - English-only: `bge-small-en-v1.5` (33 M params, 384-dim) or
    `all-MiniLM-L6-v2` (22 M, 384-dim, ~80 MB).
  - **Multilingual (matches `VOICE_LANG=id`):** `intfloat/multilingual-e5-small`
    or `paraphrase-multilingual-MiniLM-L12-v2` (both ~118 M, 384-dim). **This is
    the one to use here** — handles Indonesian and English in one index.
  - Zero-local-compute alternative: OpenAI `text-embedding-3-small` (1536-dim,
    ~$0.02 / 1M tokens). Adds ~100–300 ms network per query and needs a key, but
    no model on the robot. Reuses the `OPENAI_API_KEY` already in the stack.
- **Speed:** query embed ~10–40 ms on CPU (MiniLM-class) + <1 ms search.
  Total retrieval well inside the latency budget.
- **Compute:** one small model in RAM (~100–500 MB); **CPU is fine**, no GPU
  contention. Index once at startup (or cache to disk).
- **Storage:** vectors are tiny — 200 chunks × 384 × 4 B ≈ **300 KB**; 10k chunks
  ≈ 15 MB.
- **Accuracy:** semantic match across paraphrase and language. The standard,
  well-understood RAG quality.
- **Verdict:** **best fit.** Fast, cheap, multilingual, edge-friendly, persistent,
  supports per-venue filtering. Slots straight into the existing tool-call loop.

### Option 3 — Embedded vector DB with management features
Same as Option 2 but with a "real" embedded DB — **Chroma**, **LanceDB**,
**Qdrant (embedded)**, **sqlite-vec**.

- Adds: metadata filtering, incremental upserts, persistence, collections per venue.
- **Complexity:** moderate (Chroma pulls a non-trivial dependency tree;
  sqlite-vec / LanceDB are lean).
- **Speed/compute/storage:** ANN indexing is unnecessary below ~100k vectors, so
  performance ≈ Option 2.
- **Verdict:** worth it only if you want **many venues with metadata filtering and
  frequent content updates** managed in one store. Prefer **sqlite-vec or LanceDB**
  over Chroma for footprint.

### Option 4 — Standalone server vector DB (Qdrant / Milvus / Weaviate)
A separate service in `docker-compose`.

- **Complexity:** high — another container, RAM (Milvus wants GBs), ops surface.
- **Justified at:** millions of vectors, multi-tenant, high QPS. **None of which
  applies here.**
- **Verdict:** **not recommended** at this scale. It buys nothing a file-based
  index doesn't already give you, and it competes for the robot's RAM.

### Option 5 — OpenKB / PageIndex (vectorless, LLM-reasoning retrieval)
[OpenKB](https://github.com/VectifyAI/OpenKB) compiles raw documents into a
**wiki of Markdown pages with `[[wikilinks]]`** (summaries, concept/entity pages,
cross-links), then answers via **PageIndex** — a *vectorless, reasoning-based*
retriever that builds a hierarchical tree of each document and has the **LLM reason
over the tree** to find relevant sections. No embeddings, no vector DB.

- **What it's genuinely good at:** long/complex source documents (hundred-page
  reports, manuals), synthesis across many sources, **knowledge that accumulates**
  (each doc enriches the wiki instead of being re-derived per query), citations,
  contradiction/gap linting, Obsidian-compatible browsing.
- **Setup complexity:** low — `pip install openkb`, drop files in `raw/`, `compile`.
  CLI-driven, multi-provider via LiteLLM.
- **Storage:** small — plain Markdown files. No DB.
- **Runtime cost (the catch):** retrieval is **one or more LLM calls per query** to
  navigate the tree, *then* another to answer. On the robot's voice hot path that
  means **seconds of latency** and **per-query token cost** — and on a local
  `gemma e4b` the tree-reasoning quality is uncertain (it's tuned for stronger
  models). It optimizes a problem this use case **doesn't have** (long-doc
  navigation) while taxing the one resource that's tight (latency + edge compute).
- **Verdict:** **wrong tool for the hot path, right tool for the workshop.** Use
  OpenKB **offline** to turn a venue's messy brochures/PDFs/site exports into a
  clean, de-duplicated, cross-linked Markdown wiki — *then index that wiki* with
  Option 2 for fast runtime retrieval. Best of both worlds (see §5).

---

## 3. Side-by-side comparison

Ratings are for **this use case** (small venue KB, voice UX, edge hardware).
"⚙ compute" = runtime cost per query.

| | **0 Prompt-stuff** | **1 BM25/FTS5** | **2 Embedding RAG** ⭐ | **3 Embedded DB** | **4 Server DB** | **5 OpenKB** |
|---|---|---|---|---|---|---|
| Setup complexity | ★ trivial | ★ low | ★★ low–mod | ★★★ mod | ★★★★ high | ★★ low (CLI) |
| Code to maintain | ~10 lines | ~50 lines | ~120 lines | ~120 lines + dep | container + client | external tool |
| Query latency | ~0 ms | <1 ms | **~10–40 ms** | ~10–40 ms | ~5–30 ms + net | **seconds (LLM)** |
| Extra compute | none | CPU negligible | small CPU model | small CPU model | separate service | **LLM per query** |
| GPU needed | no | no | no (CPU ok) | no | no | strong LLM helps |
| Storage | KB text | text + index (MB) | **vectors (≤15 MB)** | tens of MB | GBs (service) | Markdown (small) |
| Semantic match | n/a (full ctx) | ✗ lexical only | ✓ | ✓ | ✓ | ✓ (reasoning) |
| Multilingual (id+en) | ✓ (LLM does it) | ✗ weak | ✓ w/ ml-e5 model | ✓ | ✓ | ✓ |
| Per-venue filtering | swap prompt | per-index | metadata filter | metadata filter | metadata filter | per-wiki |
| Incremental updates | edit file | re-index | upsert | upsert | upsert | watch/recompile |
| Scales to long docs | ✗ | ~ | ✓ (chunked) | ✓ | ✓ | ✓✓ (its strength) |
| Token cost / query | **high** (whole KB) | low (top-k) | low (top-k) | low (top-k) | low (top-k) | high (retrieval+answer) |
| **Fit here** | single small venue | zero-dep fallback | **★ recommended** | many venues | overkill | **offline authoring** |

---

## 4. Recommendation for this repo

**Build Option 2, with Option 0 as the trivial starting case and OpenKB as an
offline content pipeline.** Concretely:

1. **Store** each venue's knowledge as human-editable Markdown/JSON under
   `config/knowledge/<venue>/` (e.g. `museum_a/exhibits.md`). Source-controlled,
   reviewable, no DB to back up. Select the active venue with an env var, e.g.
   `KB_VENUE=museum_a` (mirrors how `VOICE_LANG`, `STT_SOURCE` are handled).
2. **Index at launch** — chunk by paragraph/heading, embed with
   `intfloat/multilingual-e5-small` (multilingual for `VOICE_LANG=id`), cache the
   vectors to disk next to the source so restarts are instant. Use **numpy
   brute-force or sqlite-vec** — both file-based, no server.
3. **Query** — add a `search_knowledge_base(query)` tool to the existing tool-call
   loop in [`voice_cmd_node._ask_conversational()`](../speech_processor/speech_processor/voice_cmd_node.py),
   right next to `search_web`. Retrieve top-3, return as context; the LLM composes
   the 1–2 sentence spoken answer. Falls back to `search_web` when the KB has no
   hit — so "what time does the park close?" hits the KB, "what's the weather?"
   hits the web.
4. **Package** it cleanly: either a small `knowledge_base/` module inside
   `speech_processor`, or a standalone node (use `yolo_detector` as the template
   per the repo's "new standalone node" guidance). Keep embeddings/index in the
   infrastructure layer; the retrieval *interface* stays provider-agnostic.

This keeps retrieval **CPU-only, <40 ms, a few MB on disk**, multilingual, and
fully inside the architecture and provider abstraction the SDK already uses.

### When to escalate
- KB grows past ~100k chunks, or you need heavy metadata filtering across many
  venues → move the same vectors into **sqlite-vec/LanceDB (Option 3)**. No
  re-architecture, just a different store behind the same interface.
- You're ingesting **long, messy source PDFs** (full exhibit catalogues, sponsor
  decks) → run them through **OpenKB offline** (§5) before indexing.
- Never reach for a **standalone server DB** unless you blow past ~1M vectors or
  need multi-tenant QPS — not foreseeable for venue Q&A.

---

## 5. Hybrid: OpenKB as the authoring tool, embeddings as the runtime

OpenKB and a vector index aren't competitors here — they sit at different stages:

```
 Raw venue material                Offline (authoring)              On-robot (runtime)
 brochures, PDFs,        ──►  OpenKB compile → clean Markdown  ──►  chunk + embed (ml-e5)
 site exports, notes          wiki: summaries, entity pages,        → file index (numpy/sqlite-vec)
                              [[cross-links]], citations            → search_knowledge_base tool
                                                                     → conversational LLM answer
```

- **OpenKB's strengths** (synthesis, de-duplication, entity/place pages,
  contradiction linting, long-doc handling) are applied **once, off the robot**,
  where seconds-per-query latency and a strong cloud LLM are fine.
- **The robot** only ever queries the *distilled, short* wiki with **fast,
  CPU-only embedding search** — no LLM in the retrieval path, predictable latency.

You get OpenKB's content quality without paying its per-query reasoning cost during
a live visitor interaction.

---

## 6. Sources

- [VectifyAI/OpenKB — GitHub](https://github.com/VectifyAI/OpenKB)
- [Introducing OpenKB — PageIndex blog](https://pageindex.ai/blog/introducing-openkb)
- [VectifyAI/OpenKB — AISignal overview](https://www.aisignal.dev/repo/VectifyAI/OpenKB)
- Existing integration point in this repo: [`speech_processor/speech_processor/voice_cmd_node.py`](../speech_processor/speech_processor/voice_cmd_node.py) (`_ask_conversational`, `search_web` tool loop) and [`command_dispatcher.py`](../speech_processor/speech_processor/command_dispatcher.py) (`CONVERSATIONAL_SYSTEM_WITH_SEARCH`, `SEARCH_TOOL_OPENAI`).
