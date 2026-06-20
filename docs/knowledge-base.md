# Knowledge Base (RAG) — Venue Q&A

Grounds the robot's conversational replies on a **client knowledge base** so it can
answer questions about the place it operates in — a museum's hours and exhibits, an
amusement park's attractions, a brand launch event's schedule. Fulfils **Modul 3.2**
of the proposal.

This is the lightweight embedding-RAG design chosen in
[knowledge-base-options.md](knowledge-base-options.md) (Option 2): a small
multilingual embedding model + a file-based index, with retrieval folded into the
conversational prompt. No vector database, no extra service. Retrieval is
CPU-only and adds tens of milliseconds.

## How it works

```
visitor speech ─► stt_node ─► /speech_text ─► voice_cmd_node
                                                  │
                          no motion command matched, LLM NLU provider
                                                  ▼
                                   KnowledgeBase.search(question)        ← multilingual-e5 embeddings,
                                                  │                        brute-force cosine over the venue corpus
                                          top-k venue snippets
                                                  ▼
                          system prompt + VENUE KNOWLEDGE  ─►  LLM (openai/gemini/gemma_local)
                                                  ▼
                                       grounded reply ─► /tts
```

- The knowledge base is built **once at startup** in
  [`voice_cmd_node`](../speech_processor/speech_processor/voice_cmd_node.py): every
  document is chunked and embedded, then cached to disk (keyed by content hash) so
  restarts are instant.
- On each non-command utterance, the top snippets are retrieved and injected into
  the conversational system prompt via `conversational_system_with_kb()` in
  [`command_dispatcher.py`](../speech_processor/speech_processor/command_dispatcher.py).
  This is **provider-agnostic** — `openai`, `gemini`, and `gemma_local` all get the
  grounding with no per-model tool wiring. The existing `search_web` tool stays
  available, so the LLM uses venue facts when relevant and the web otherwise.
- Retrieval logic lives in
  [`knowledge_base.py`](../speech_processor/speech_processor/knowledge_base.py),
  which has **no ROS2 imports** and is unit-tested in isolation
  ([`test/test_knowledge_base.py`](../speech_processor/test/test_knowledge_base.py)).

> **Requires an LLM NLU provider.** RAG needs a model to phrase the answer, so it
> is skipped under `NLU_PROVIDER=keyword` (which has no conversational path). Use
> `openai`, `gemini`, or `gemma_local`.

## Quick start (Docker)

```bash
# Uses the bundled sample venue (speech_processor/knowledge/museum_demo)
ENABLE_STT=true ENABLE_KB=true NLU_PROVIDER=openai OPENAI_API_KEY=... ROBOT_IP=<IP> \
  docker-compose up

# Fully offline (Windows 8 GB GPU): Gemma NLU + local multilingual embeddings
ENABLE_STT=true ENABLE_KB=true NLU_PROVIDER=gemma_local COMPOSE_PROFILES=gemma \
  docker-compose -f docker/docker-compose.yml -f docker/docker-compose.windows-gpu.yml up
```

Then ask (EN or ID): *"What time do you open?"* · *"Jam berapa buka?"* ·
*"Where are the toilets?"* · *"Berapa harga tiketnya?"*

## Quick start (bare metal)

```bash
export ENABLE_STT=true ENABLE_KB=true
export NLU_PROVIDER=openai OPENAI_API_KEY=...
export VOICE_LANG=id            # optional — Indonesian focus
ros2 launch go2_robot_sdk robot.launch.py
```

## Authoring the knowledge base

Drop plain files into a venue folder. Keep **one fact per paragraph or bullet** so
retrieval stays crisp. Bilingual (EN + ID) entries both work because the default
model is multilingual.

```
speech_processor/knowledge/<venue>/
├── exhibits.md     # headings become snippet labels ("exhibits.md › Opening hours")
├── facilities.md
└── faq.json        # ["fact", ...] | [{"text","source"}] | {"faqs":[{"q","a"}]}
```

Supported files: `.md` / `.markdown` / `.txt` (split by paragraph; the nearest
heading is kept as the source label) and `.json`. See the bundled
[`museum_demo`](../speech_processor/knowledge/museum_demo/exhibits.md) for a
template.

**Point at your own KB** with `KB_PATH` (absolute path), or drop a folder next to
the sample and select it with `KB_VENUE`. In Docker, mount real venue facts:

```yaml
# docker-compose override
services:
  go2: { volumes: ["/host/venue_kb:/venue_kb:ro"] }
# then: KB_PATH=/venue_kb ENABLE_KB=true ... docker-compose up
```

## Configuration

| Env var | Default | Meaning |
|---|---|---|
| `ENABLE_KB` | `false` | Turn on KB grounding (needs an LLM `NLU_PROVIDER`) |
| `KB_VENUE` | `museum_demo` | Bundled venue folder under `speech_processor/knowledge/` |
| `KB_PATH` | *(empty)* | Absolute KB directory; overrides `KB_VENUE` |
| `KB_EMBED_PROVIDER` | `local` | `local` (multilingual-e5, CPU) · `openai` (text-embedding-3-small) · `hashing` (no-dep fallback) |
| `KB_MODEL` | `intfloat/multilingual-e5-small` | sentence-transformers model when `local` |
| `KB_TOP_K` | `3` | Snippets injected per question |
| `KB_MIN_SCORE` | `0.0` | Cosine floor; raise to suppress weak matches |

### Embedding backends

- **`local`** (recommended) — `intfloat/multilingual-e5-small` via
  `sentence-transformers`, ~118 M params, runs on **CPU**, handles Indonesian +
  English in one index. ~10–40 ms/query. First run downloads the model
  (~470 MB) to the HuggingFace cache.
- **`openai`** — `text-embedding-3-small`; no local model, reuses `OPENAI_API_KEY`,
  adds ~100–300 ms network per query.
- **`hashing`** — pure-numpy character-n-gram fallback. Zero dependencies, lexical
  (not semantic) quality. Used automatically if neither of the above is available,
  and by the unit tests. Fine for a demo; install `sentence-transformers` for real
  use.

## Cost & footprint

At venue scale (tens–hundreds of facts) this is negligible: vectors are a few
hundred KB on disk, retrieval is sub-millisecond after the query embed, and there
is **no GPU contention** (embeddings run on CPU). The embedding cache lives in
`~/.cache/go2_robot_sdk/kb/`.

## Testing

```bash
colcon test --packages-select speech_processor
# or, isolated (no ROS2 needed — knowledge_base.py is pure Python):
pytest speech_processor/test/test_knowledge_base.py -q
```

## Limitations / next steps

- Replies are still **stateless** — no multi-turn memory yet (Modul 3.4). A
  follow-up like *"and on weekends?"* loses context. Pairs naturally with the
  rolling-history work tracked there.
- For long, messy source documents (full catalogues, sponsor decks), curate them
  into clean Markdown first — optionally with the offline OpenKB authoring pipeline
  described in [knowledge-base-options.md §5](knowledge-base-options.md).
