# Unit Tests

Pure-pytest unit tests for the GO2 Robot SDK — no ROS2 runtime, no robot, no GPU required. ROS2 dependencies are stubbed at import time so tests run on any OS (Linux, Windows, macOS).

## Running the tests

```bash
# From the repo root
export PYTHONPATH=speech_processor        # Linux/macOS
$env:PYTHONPATH = "speech_processor"      # Windows PowerShell

python -m pytest speech_processor/test/ -v
```

**543 tests total, 0 failures** (as of last run, ~2.4 s on a typical laptop).

To run a single module's tests:

```bash
python -m pytest speech_processor/test/test_modul1_voice_commands.py -v
python -m pytest speech_processor/test/test_modul2_extended_contextual.py -v
python -m pytest speech_processor/test/test_modul3_conversational_ai.py -v
python -m pytest speech_processor/test/test_modul4_visual_perception.py -v
python -m pytest speech_processor/test/test_modul5_autonomous_navigation.py -v
```

## Test files

| File | Tests | Module |
|---|---|---|
| [test_modul1_voice_commands.py](../speech_processor/test/test_modul1_voice_commands.py) | 107 | Modul 1 — voice command recognition |
| [test_modul2_extended_contextual.py](../speech_processor/test/test_modul2_extended_contextual.py) | 92 | Modul 2 — extended contextual commands |
| [test_modul3_conversational_ai.py](../speech_processor/test/test_modul3_conversational_ai.py) | 148 | Modul 3 — conversational AI |
| [test_modul4_visual_perception.py](../speech_processor/test/test_modul4_visual_perception.py) | 86 | Modul 4 — visual perception |
| [test_modul5_autonomous_navigation.py](../speech_processor/test/test_modul5_autonomous_navigation.py) | 88 | Modul 5 — autonomous indoor navigation |
| [test_face_db.py](../speech_processor/test/test_face_db.py) | 6 | FaceDB — basic enrollment + cosine matching |
| [test_knowledge_base.py](../speech_processor/test/test_knowledge_base.py) | 9 | KnowledgeBase — RAG retrieval |
| [test_conversation_memory.py](../speech_processor/test/test_conversation_memory.py) | 8 | ConversationMemory — rolling window |

---

## Modul 1 — test_modul1_voice_commands.py (107 tests)

Tests the voice command recognition pipeline: wake-word gating, command mapping, bilingual support.

| Test class | Source | What it verifies |
|---|---|---|
| `TestWakeWordGating` (12) | `stt_node.py` | Gate enabled/disabled, partial match rejected, case-insensitive, empty utterance safe |
| `TestCmdMap` (12) | `CMD_MAP` in `command_dispatcher.py` | Every basic motion command has an `api_id` or `("move", lin, ang)` action; stop produces zero velocity |
| `TestFeedbackForAction` (11) | `feedback_for_action()` | TTS feedback string for every motion command; bilingual (EN + ID) |
| `TestLanguageName` (6) | `language_name()` | `"en"` → `"English"`, `"id"` → `"Bahasa Indonesia"`, unknown → fallback |
| `TestCommandGlossary` (10) | `COMMAND_GLOSSARY` | Every Indonesian keyword maps to a valid English command key |
| `TestCommandForTextEnglish` (11) | `command_for_text()` | English keyword matching; questions not confused with commands |
| `TestCommandForTextIndonesian` (18) | `command_for_text()` | Indonesian keyword matching; all bilingual aliases resolve |
| `TestLooksLikeQuestion` (9) | `_looks_like_question()` | Questions suppressed; commands not suppressed; boundary phrase `"why stop"` treated as question |
| `TestCoerceCommand` (5) | `coerce_command()` | None passthrough, dict passthrough, tuple validation |
| `TestCoerceStr` (5) | `coerce_str()` | Action tuple → loggable string |
| `TestFeedbackMap` (4) | `FEEDBACK_MAP` | Map completeness and string types |

---

## Modul 2 — test_modul2_extended_contextual.py (92 tests)

Tests patrol automation, one-shot object approach, and custom command YAML integration.

| Test class | Source | What it verifies |
|---|---|---|
| `TestYawToQuaternion` (6) | `patrol_node._yaw_to_quaternion()` | Zero, quarter-turn, half-turn, negative yaw; unit norm invariant; x/y always zero |
| `TestPatrolBuildRoute` (6) | `PatrolNode._build_route()` | Empty param → all waypoints in YAML order; explicit route filters + orders by param; unknown keys silently excluded; single waypoint works |
| `TestPatrolLoadWaypoints` (5) | `PatrolNode._load_waypoints()` | Valid YAML loads waypoints and triggers `_build_route`; missing file → empty; empty path is noop; YAML without `waypoints` key yields empty |
| `TestPatrolEnableLogic` (5) | `PatrolNode._on_enable()` | Already-running enable is noop; no-route enable publishes TTS but doesn't start; fresh enable sets `_running=True`, `_idx=0`, calls `_send_next_goal`; disable-when-idle is noop; disable-when-running stops patrol |
| `TestPatrolAdvanceAndContinue` (6) | `PatrolNode._advance_and_continue()` | Increments idx; wraps to zero on last; wrap publishes `patrol_done`; mid-route no `patrol_done`; noop when not running; calls `_send_next_goal` |
| `TestPatrolSkipOrAbort` (4) | `PatrolNode._skip_or_abort()` | `skip_on_failure=True` advances and keeps running; `skip_on_failure=False` stops patrol and publishes `patrol_cancelled` |
| `TestPatrolStatusStringFormat` (4) | status string convention | `patrolling:{key}/{1-based-idx}/{total}` format; `patrol_done` literal; `patrol_failed:{key}` format |
| `TestApproachTargetSetting` (5) | `ApproachObjectNode._on_target()` | New target lowercased+stripped; publishes `approaching:{cls}` status and TTS; empty string cancels active target; empty with no target is noop |
| `TestApproachCameraInfo` (4) | `ApproachObjectNode._on_camera_info()` | Valid dims update both fields; zero width keeps previous; zero height keeps previous; stored as float |
| `TestApproachControlLaw` (11) | `ApproachObjectNode._on_detections()` | No target → ignore; wrong class → ignore; below confidence → ignore; centered object → zero angular; left bias → positive angular; right bias → negative angular; angular clamped to max; **area == threshold − deadband → reached** (>= boundary); below threshold → forward; largest bbox wins among multiple detections |
| `TestApproachLostTimeout` (5) | `ApproachObjectNode._publish_tick()` | age=0 → publishes twist; **age == lost_to → NOT lost** (strict >); age just past timeout → triggers `_on_lost`; no target → tick is noop; zero timeout → any positive age triggers lost |
| `TestApproachTerminalConditions` (6) | `_on_reached()`, `_on_lost()` | Both clear `_target_class`; `reached:{cls}` / `lost:{cls}` status published; zero Twist published |
| `TestCustomCommandMatch` (10) | `CommandDispatcher.match_custom()` | Empty cmds → None; EN phrase matches; ID phrase matches on `language="id"`; EN trigger not matched on ID lang; no phrase match → None; **longer phrase beats shorter**; **`"ball"` does not match `"ballroom"`** (word-boundary); case-insensitive; comma-separated triggers; punctuation stripped |
| `TestCustomAction` (9) | `CommandDispatcher._custom_action()` | `api_id` → dict with api_id + parameter; `navigate_to_room` → `("goto_room", room)`; `patrol_start/stop` → tuples; `follow_start/stop` → tuples; `approach_object` → `("approach_object", cls)`; unknown type → None |
| `TestCustomCommandLoading` (7) | `CommandDispatcher._load_custom_commands()` | Valid YAML loads one command; empty dict loads zero; missing file → unchanged; empty path is noop; multiple commands all loaded; key field preserved; roundtrip load → match |

---

## Modul 3 — test_modul3_conversational_ai.py (148 tests)

Tests the conversational AI layer: LLM persona, RAG knowledge base, TTS infrastructure, conversation memory.

| Test class | Source | What it verifies |
|---|---|---|
| `TestConversationalSystemPersona` (5) | `CONVERSATIONAL_SYSTEM` | Non-empty, robot identity present, no raw markdown, TTS length hints, capability mentions |
| `TestRobotCmdSystemPrompt` (10) | `robot_cmd_system_prompt()` | Command categories, nav/patrol/approach documented, JSON return format specified, unknown fallback present |
| `TestKBGroundingPrompt` (7) | `conversational_system_with_kb()` | KB context injected into prompt, base prompt preserved, multi-sentence context handled |
| `TestFaceGroundingPrompt` (5) | `conversational_system_with_faces()` | Name injected, greeting concept present, base system + names both appear |
| `TestSceneGroundingPrompt` (6) | `conversational_system_with_scene()` | Description injected, conditional-use instruction present |
| `TestKeywordNLURegexes` (21) | `_GOTO_RE`, `_APPROACH_RE`, `_COMPILED_TABLE` | Navigation intent (EN + ID), object approach (EN + ID), `_OBJECT_CLASS_MAP` coverage, compiled keyword table non-empty |
| `TestChunkMarkdown` (8) | `_chunk_markdown()` | Heading-split chunking, short sections filtered (`< 12` chars), source metadata attached, empty file returns no chunks |
| `TestChunkJson` (7) | `_chunk_json()` | FAQ / string-list / text-dict formats, short items filtered, empty input |
| `TestHashingBackend` (8) | `_HashingBackend` | Embedding shape correct, L2-normalised, deterministic, similar text scores higher than dissimilar |
| `TestKBAdvanced` (10) | `KnowledgeBase` | Multi-file corpus load, `top_k` limit, `format_context()` citation format, unavailable when path missing, embedding cache roundtrip |
| `TestAudioCache` (16) | `AudioCache` | Enabled/disabled mode, miss then hit, key differs by text / voice / provider, `put()` on disabled → False |
| `TestTTSConfig` (7) | `TTSConfig` | Dataclass field defaults and types |
| `TestTTSProviderEnum` (5) | `TTSProvider` | SUPERTONIC / OPENAI / ELEVENLABS / GEMINI all present |
| `TestAudioFormatEnum` (4) | `AudioFormat` | MP3 / WAV / PCM / OGG all present |
| `TestConversationMemoryEdgeCases` (14) | `ConversationMemory` | `max_turns` exact boundary, idle-reset strict `>` (at exactly `idle_timeout` → not expired), role sequencing, `max_turns=0` → disabled, blank turns ignored |

---

## Modul 4 — test_modul4_visual_perception.py (86 tests)

Tests YOLO detection math, face database, enrollment helpers, follow-me control law, and visual feedback grounding.

| Test class | Source | What it verifies |
|---|---|---|
| `TestNormalize` (6) | `face_db._normalize()` | L2-norm = 1 after normalization, zero-vector safety (no division by zero), flattens 2-D input, high-dim vectors |
| `TestFaceDBCoverage` (12) | `FaceDB` | `known_names` and `num_faces` properties, multi-photo per person, threshold boundary is **strict `<`** (sim == threshold → `"Unknown"`), corrupt-cache fallback to empty DB, `rebuild_from_disk` skips images where `embed_fn` returns `None` |
| `TestFaceEnrollmentSanitize` (10) | `FaceEnrollmentNode._sanitize()` | Path traversal `../` blocked, `@`, `.`, `/` removed, hyphens / underscores / spaces preserved, leading/trailing whitespace stripped |
| `TestFaceEnrollmentSaveImage` (5) | `FaceEnrollmentNode._save_image()` | Creates person directory, writes raw bytes to disk, returns index 0 for first image then 1 for second, different people get separate dirs |
| `TestFollowMeControlLaw` (14) | `follow_me_node` P-controller | Centered person → zero angular; left/right bias → proportional angular (verified formula); large error → clamped to `max_angular`; far person → `linear = lin_speed`; close person → `linear = 0`; deadband boundary: `area == target - deadband` → stop (not strictly less) |
| `TestFollowMeLostTimeout` (5) | `_publish_tick` timeout logic | `age ≤ lost_to` → publish current twist; `age > lost_to` (strict) → publish zero twist; zero timeout makes any positive age lost |
| `TestYoloBBoxMath` (8) | `_to_detection2d` bbox math | `center_x = (x1+x2)/2`, `size_x = x2-x1`, float coordinates, degenerate zero-area box |
| `TestYoloClassNameLookup` (6) | `class_names.get()` | Known class ID → name string; unknown ID → `str(id)` fallback; empty dict always falls back; confidence threshold gates which detections are published |
| `TestFaceRecognitionLargestFace` (7) | `FaceRecognitionNode._largest_face()` | Empty list → `None`; single face → returned; larger bbox area wins; float bbox values; many faces selects the biggest |
| `TestFaceDrawFaceColorLogic` (5) | `FaceRecognitionNode._draw_face()` | Known name → green `(0, 255, 0)`; `"Unknown"` → orange `(0, 165, 255)`; label format is `"Name 0.80"` for known, `"Unknown"` for unknown |
| `TestVisualFeedback44` (8) | `conversational_system_with_faces/scene()` | Name injected, multi-name string, differs from base `CONVERSATIONAL_SYSTEM`, scene description injected verbatim, greeting concept present in face-grounded prompt |

---

## Modul 5 — test_modul5_autonomous_navigation.py (88 tests)

Tests waypoint navigation and the behavior coordinator state machine.

| Test class | Source | What it verifies |
|---|---|---|
| `TestNavYawToQuaternion` (4) | `nav_waypoint_node._yaw_to_quaternion()` | Zero, quarter-turn, unit norm invariant, x/y always zero |
| `TestNavLoadWaypoints` (6) | `NavWaypointNode._load_waypoints()` | Valid YAML loads waypoints; multiple waypoints all loaded; missing file → empty; empty path noop; YAML without `waypoints` key → empty; `_on_reload` triggers load |
| `TestNavLookup` (10) | `NavWaypointNode._lookup()` | Exact key; space-to-underscore normalization; hyphen-to-underscore normalization; case-insensitive; mixed case+spaces; **substring of YAML key**; substring in `label_en`; substring in `label_id`; no match → None; empty waypoints → None |
| `TestNavOnNavigate` (10) | `NavWaypointNode._on_navigate()` | Empty string triggers cancel only; unknown room → `unknown:{room}` status + TTS; known room → `navigating:{room}` status; TTS uses `label_en` not raw key; server unavailable → `failed:{room}`; server available → `send_goal_async` called; navigating cancels previous goal; goal position set from waypoint x/y |
| `TestNavGoalResponse` (5) | `NavWaypointNode._on_goal_response()` | Rejected → `failed:{room}` status; rejected → TTS with "rejected"; rejected leaves `_goal_handle` None; accepted saves handle; accepted publishes no failure status |
| `TestNavOnResult` (6) | `NavWaypointNode._on_result()` | STATUS_SUCCEEDED → `arrived:{room}` + TTS with label; STATUS_CANCELED → `cancelled` status, no TTS; STATUS_ABORTED → `failed:{room}`; any result clears `_goal_handle` |
| `TestNavCancelCurrent` (4) | `NavWaypointNode._cancel_current()` | No handle → noop; with handle → `cancel_goal_async` called; handle cleared; `cancelled` status published |
| `TestBCFollow` (5) | `BehaviorCoordinatorNode._on_follow()` | True → FOLLOWING + publishes; False + was FOLLOWING → IDLE; False + was IDLE → no change; False + was NAVIGATING → no change |
| `TestBCNavStatus` (8) | `BehaviorCoordinatorNode._on_nav_status()` | `navigating:*` → NAVIGATING; `arrived:*` + NAVIGATING → IDLE; `failed:*` + NAVIGATING → IDLE; `cancelled` + NAVIGATING → IDLE; `unknown:*` + NAVIGATING → IDLE; terminal from IDLE → no change; `navigating:*` already NAVIGATING → no re-publish; `failed:*` from APPROACHING → no change |
| `TestBCVelocity` (7) | `BehaviorCoordinatorNode._on_vel()` | Nonzero `linear.x/y` / `angular.z` + IDLE → VOICE_MOVE; zero Twist + IDLE → no change; nonzero + VOICE_MOVE → no re-publish; nonzero + FOLLOWING → no change; nonzero vel updates `_last_vel_t` |
| `TestBCApproach` (6) | `BehaviorCoordinatorNode._on_approach_status()` | `approaching:*` → APPROACHING from any state; `reached:*`/`lost:*`/`cancelled` + APPROACHING → IDLE; terminal from IDLE → no change |
| `TestBCPatrol` (6) | `BehaviorCoordinatorNode._on_patrol_status()` | `patrolling:*` → PATROL; `patrol_done` + PATROL → IDLE; `patrol_cancelled` + PATROL → IDLE; **`patrol_failed:*` + PATROL → no change** (not in terminal set); terminal from IDLE → no change; `patrolling:*` from NAVIGATING → overrides to PATROL |
| `TestBCTick` (6) | `BehaviorCoordinatorNode._tick()` | Elapsed > `vel_idle_sec` + VOICE_MOVE → IDLE; elapsed < timeout → stays VOICE_MOVE; IDLE not affected; NAVIGATING not affected; recent `_last_vel_t` keeps VOICE_MOVE alive |
| `TestBCSetPublish` (5) | `BehaviorCoordinatorNode._set()` / `_publish()` | Same mode → no publish; new mode → publishes; internal mode updated; two identical `_set` calls → one publish; `_publish()` always sends current mode string |

---

## How ROS2 stubs work

Each `test_modul*.py` file inserts minimal `types.ModuleType` stubs into `sys.modules` **before** importing any production module. Stubs are generally idempotent (add attrs only if missing). `test_modul2_extended_contextual.py` and `test_modul5_autonomous_navigation.py` always force-set stubs to ensure real Python classes survive collection order (Modul 1 stubs some types as plain `object`). Every file that sets `cv2.imwrite` writes 4 JPEG magic bytes to disk so file-existence assertions in `test_face_db.py` pass regardless of which stub runs last.

Key stubs:
- `rclpy`, `rclpy.node`, `rclpy.qos` — empty modules; `Node = object`
- `geometry_msgs.msg.Twist` — real Python class so control-law tests can set `.linear.x` / `.angular.z`
- `vision_msgs.msg.*` — real Python classes (`Detection2D`, `BoundingBox2D`, etc.) so message-building tests work
- `cv2.imwrite` — writes 4 JPEG magic bytes to disk so file-existence assertions pass without OpenCV installed

Production modules that are **pure Python** (no ROS2 at module level) are imported directly: `face_db.py`, `knowledge_base.py`, `conversation_memory.py`.
