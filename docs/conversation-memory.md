# Multi-turn Conversation Memory

Gives the robot a short memory of the current conversation so follow-up questions
and anaphora resolve naturally — *"What time do you open?"* → *"And on weekends?"*
→ *"How much is a ticket then?"*. Fulfils **Modul 3.4** of the proposal.

## Design

A **rolling window** of the last few user↔robot exchanges, with an **idle reset**
so a new visitor stepping up starts fresh instead of inheriting the previous
person's context. Both bounds are tuned for a public venue (museum / park / event)
where strangers take turns talking to the robot.

- Implemented in [`conversation_memory.py`](../speech_processor/speech_processor/conversation_memory.py)
  (pure Python, no ROS2 imports — unit-tested in
  [`test/test_conversation_memory.py`](../speech_processor/test/test_conversation_memory.py)).
- Wired into [`voice_cmd_node`](../speech_processor/speech_processor/voice_cmd_node.py):
  after each conversational reply the exchange is recorded; on the next utterance
  the window (idle-reset applied) is injected into the LLM call. **Provider-agnostic**
  — openai (`messages`), gemini (`contents`, assistant→`model` role), and
  gemma_local (`messages`) all receive the prior turns.
- Only **conversational Q&A turns** are remembered — motion-command feedback
  ("Sitting down.") is not, so the context stays about the visitor's questions.

> **Requires an LLM NLU provider** (`openai` / `gemini` / `gemma_local`). The
> offline `keyword` provider has no conversational path, so memory is skipped.

## Default window: 3 turns + 60 s idle reset

`CONV_HISTORY_TURNS=3` keeps the last 3 exchanges (≈6 messages). Rationale for this
application:

- **Venue follow-ups are shallow** — references point at the last 1–2 exchanges;
  3 covers a typical chain with margin.
- **Multi-visitor contamination** is the real risk in a public setting. A short
  window plus the 60 s idle reset bounds how far one visitor's topic can carry into
  the next person's answer. The idle reset matters more than the raw count.
- **Local model budget** — every kept turn is re-sent on each call. With RAG also
  injecting venue snippets, 3 turns (~150–200 tokens of history) keeps Gemma E4B
  fast and inside its context; 8–10 turns would start to hurt the local path.

Raise `CONV_HISTORY_TURNS` to ~5 for cloud providers if a venue wants chattier
context; lower `CONV_HISTORY_IDLE_SEC` for high-traffic venues with rapid turnover.

## Configuration

| Env var | Default | Meaning |
|---|---|---|
| `ENABLE_CONV_MEMORY` | `true` | Turn multi-turn memory on/off (LLM NLU only) |
| `CONV_HISTORY_TURNS` | `3` | Exchanges (user+robot pairs) kept as context |
| `CONV_HISTORY_IDLE_SEC` | `60` | Clear memory after this many seconds of silence |

## Example

```bash
ENABLE_STT=true NLU_PROVIDER=openai OPENAI_API_KEY=... \
  ENABLE_KB=true CONV_HISTORY_TURNS=3 ROBOT_IP=<IP> docker-compose up
```

```
Visitor: "What time does the museum open?"
GO2:     "We're open Tuesday to Sunday, nine to five."
Visitor: "And on weekends?"                ← resolved via memory
GO2:     "Same hours on Saturday and Sunday — nine to five."
   …60 s of silence; a new visitor approaches…
Visitor: "How much is that?"               ← memory cleared; GO2 asks for clarification
```

## Testing

```bash
colcon test --packages-select speech_processor
# or isolated (no ROS2 needed):
pytest speech_processor/test/test_conversation_memory.py -q
```
