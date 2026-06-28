# GO2 EduPlus AI — Module & Feature Tracker

Status of the work proposed in *"Proposal: Jasa Konfigurasi & Pemrograman AI untuk Unitree Go2 EduPlus"* (8 May 2026) against what currently exists in this repository.

**Legend:** ✅ Done · 🟡 Partial · ⬜ Not started

---

## A. Instalasi & Konfigurasi Dasar

| # | Proposal item | Status | Where / notes |
|---|---|---|---|
| A1 | Audit konfigurasi awal + setup ROS2 workspace | ✅ | Full ROS2 (Humble/Jazzy) workspace, `colcon build`. See [CLAUDE.md](CLAUDE.md), [docs/architecture.md](docs/architecture.md) |
| A2 | Instalasi dependencies AI (CUDA, PyTorch, ROS2 packages) | ✅ | [requirements.txt](requirements.txt) + Docker images: Jetson CUDA ([docker/Dockerfile.jetson](docker/Dockerfile.jetson)), Windows GPU ([docker/Dockerfile.windows-gpu](docker/Dockerfile.windows-gpu)) |
| A3 | Konfigurasi sensor: microphone, RGB-D camera, LiDAR | ✅ | LiDAR ✅, camera ✅, mic ✅. **Camera:** hardware WebRTC (robot camera → `/camera/image_raw`); **Windows Docker** — [cam_bridge_node.py](speech_processor/speech_processor/cam_bridge_node.py) streams host browser webcam to `/camera/image_raw` (`CAM_BRIDGE=true`, default on `docker-compose.windows-gpu.yml`, open `http://localhost:8891`). **Mic:** (1) onboard ALSA `/dev/snd` via [stt_node.py](speech_processor/speech_processor/stt_node.py) (Jetson); (2) robot's WebRTC mic track → `/robot_audio` → stt_node, set `STT_SOURCE=robot`; (3) browser bridge ([mic_bridge_node.py](speech_processor/speech_processor/mic_bridge_node.py)) for off-robot dev. Mic-array/beamforming descoped |
| A4 | Remote access + logging system untuk debugging | ✅ | **Remote access:** VNC desktop (`localhost:5901`) + **Foxglove bridge** (`ws://localhost:8765`, on by default — [robot.launch.py:87](go2_robot_sdk/launch/robot.launch.py#L87)) for remote inspection of all topics. **Logging/capture:** `ENABLE_BAG=true` records a timestamped rosbag2 session (curated topics by default, `BAG_TOPICS=-a` for everything) persisted to host `./bags` ([docker-compose.yml](docker/docker-compose.yml)) — replayable in Foxglove or `ros2 bag play` |

---

## B. Modul AI

### Modul 1 — Basic Voice Command Recognition

| # | Proposal item | Status | Where / notes |
|---|---|---|---|
| 1.1 | Wake-word detection ("Hey Dogo") | ✅ | Wake word detected from structured STT output (`wake_word` param, e.g. `doggo`/`elliot`) and gates command execution in [stt_node.py](speech_processor/speech_processor/stt_node.py). Accepted as sufficient. *Optional future hardening (not required): a dedicated always-on engine (openWakeWord/Porcupine) for lower-latency, lower-power wake detection without continuous STT.* |
| 1.2 | Mapping perintah dasar → API motion | ✅ | Basic set mapped in [command_dispatcher.py](speech_processor/speech_processor/command_dispatcher.py) (`CMD_MAP` + `COMMAND_GLOSSARY`): **duduk**→sit, **berdiri**→stand, **jalan maju**→forward, **jalan mundur**→backward, **putar kiri**→turn_left, **putar kanan**→turn_right, **berhenti**→stop. ("ikut / follow me" descoped from the basic set → tracked under Modul 4.3 person-tracking) |
| 1.3 | Dukungan bilingual: Bahasa Indonesia & English | ✅ | `VOICE_LANG=en\|id`, Indonesian glossary in [command_dispatcher.py](speech_processor/speech_processor/command_dispatcher.py) (`COMMAND_GLOSSARY`) |

### Modul 2 — Extended Contextual Commands

| # | Proposal item | Status | Where / notes |
|---|---|---|---|
| 2.1 | Perintah kompleks berbasis intent ("dekati bola", "ikuti saya", "patroli") — robot tidak memiliki manipulator sehingga tidak bisa mengambil objek; aksi yang bisa dilakukan adalah **mendekati** objek yang terdeteksi | ✅ | **patrol_node** (`ENABLE_PATROL=true`): loops Nav2 waypoints indefinitely, voice "patroli". **approach_object_node** (`ENABLE_APPROACH_OBJECT=true`): one-shot visual servo toward any YOLO class, voice "dekati <obj>"; bbox area fraction as proximity proxy (no depth camera needed). **follow_me_node** (4.3) handles "ikuti saya". CommandDispatcher enforces mutual exclusion between all three. |
| 2.2 | Action chaining: voice → object detection → navigation (approach) | ✅ | `approach_object_node` chains: voice → CommandDispatcher → `/approach_target` → visual servo (YOLO `/detected_objects` + PD control) → `/cmd_vel_follow`. One-shot: stops automatically when `target_area` fraction of image is filled. Publishes `/approach_status` for coordinator. |
| 2.3 | Custom command builder untuk end user | ✅ | `speech_processor/config/custom_commands.yaml` — operator-editable YAML: trigger phrases (EN+ID), action_type, parameters. Loaded at startup; hot-reload via `ros2 topic pub /reload_custom_commands std_msgs/Empty "{}" --once`. Supports `api_id`, `navigate_to_room`, `patrol_start/stop`, `follow_start/stop`, `approach_object`. No code changes needed. |

### Modul 3 — Conversational AI (LLM Integration)

| # | Proposal item | Status | Where / notes |
|---|---|---|---|
| 3.1 | Integrasi LLM (cloud/on-device) dengan persona yang dapat dikustomisasi | ✅ | openai / gemini / gemma_local (offline llama.cpp) in [voice_cmd_node.py](speech_processor/speech_processor/voice_cmd_node.py). Persona via system prompt (`CONVERSATIONAL_SYSTEM`) — editable in code, not yet a config knob |
| 3.2 | RAG opsional untuk Q&A berbasis knowledge base klien | ✅ | Lightweight embedding RAG: multilingual-e5 embeddings + file-based index in [knowledge_base.py](speech_processor/speech_processor/knowledge_base.py), retrieved snippets grounded into the conversational prompt across openai/gemini/gemma_local. Bilingual venue KB under [speech_processor/knowledge/](speech_processor/knowledge/museum_demo/exhibits.md). Enable with `ENABLE_KB=true` (needs an LLM `NLU_PROVIDER`). CPU-only, ~tens of ms. See [docs/knowledge-base.md](docs/knowledge-base.md). Multi-turn memory still pending (→ 3.4) |
| 3.3 | Text-to-Speech suara natural (ID & EN) | ✅ | supertonic (offline) / openai / elevenlabs / gemini in [tts_node.py](speech_processor/speech_processor/tts_node.py); `SUPERTONIC_LANG` / `VOICE_LANG` |
| 3.4 | Percakapan multi-turn dengan context memory | ✅ | Rolling conversation window in [conversation_memory.py](speech_processor/speech_processor/conversation_memory.py) (default 3 exchanges + 60s idle reset), injected into openai/gemini/gemma_local calls in [voice_cmd_node.py](speech_processor/speech_processor/voice_cmd_node.py). Idle reset keeps a new visitor from inheriting the previous one's context. `CONV_HISTORY_TURNS` / `CONV_HISTORY_IDLE_SEC`. See [docs/conversation-memory.md](docs/conversation-memory.md) |

### Modul 4 — Visual Perception (Object & Face Recognition)

| # | Proposal item | Status | Where / notes |
|---|---|---|---|
| 4.1 | Real-time object detection (YOLOv8/setara) | ✅ | YOLOv11 in [yolo_detector_node.py](yolo_detector/yolo_detector/yolo_detector_node.py) → `/detected_objects`. Plus VLM scene text in [gemma_vision_node.py](speech_processor/speech_processor/gemma_vision_node.py) → `/scene_description` |
| 4.2 | Face detection + recognition, database wajah yang bisa di-enroll | ✅ | InsightFace SCRFD+ArcFace (`buffalo_sc`) in [face_recognition_node.py](speech_processor/speech_processor/face_recognition_node.py) → `/recognized_faces` + `/recognized_face_names`. **Enrollment UI** at `http://localhost:8890` ([face_enrollment_node.py](speech_processor/speech_processor/face_enrollment_node.py)): webcam/photo upload, type a name, click Enroll → writes `face_db/<Name>/`, triggers `/reload_faces`. Threshold slider publishes `/face_threshold` live to the recognizer. **Windows camera source:** [cam_bridge_node.py](speech_processor/speech_processor/cam_bridge_node.py) streams host browser webcam → `/camera/image_raw` (open `http://localhost:8891`; `CAM_BRIDGE=true` default on windows-gpu). Enable with `ENABLE_FACE=true`. ⚠️ buffalo_* weights non-commercial — see [docs/proposal-face-recognition.md](docs/proposal-face-recognition.md) |
| 4.3 | Person tracking saat robot bergerak ("ikuti saya") | ✅ | [follow_me_node.py](speech_processor/speech_processor/follow_me_node.py) subscribes to `/detected_objects` (YOLO), selects the largest `person` detection, runs a P-controller (centroid → angular error, bbox area → linear stop), and publishes `geometry_msgs/Twist` to `/cmd_vel_follow` (twist_mux priority 6 — below voice=7, above nav=5). Toggle at runtime via `/follow_enable` (Bool). Voice: "ikuti saya" / "follow me" → enable; "berhenti" → disable. Enable with `ENABLE_FOLLOW=true` (also auto-enables YOLO). |
| 4.4 | Visual feedback ke conversational layer (sebut nama orang dikenali) | ✅ | Two visual sources wired into `_ask_conversational()` in [voice_cmd_node.py](speech_processor/speech_processor/voice_cmd_node.py): **(a)** `/recognized_face_names` → `conversational_system_with_faces()` (30s TTL, `FACE_CONTEXT_TTL`) — robot greets known visitors by name; **(b)** `/scene_description` → `conversational_system_with_scene()` (10s TTL, `SCENE_CONTEXT_TTL`) — robot answers "what do you see?" from the live gemma_vision_node description. Both helpers in [command_dispatcher.py](speech_processor/speech_processor/command_dispatcher.py). Stale sightings are silently dropped so replies stay accurate. |

### Modul 5 — Autonomous Indoor Navigation

| # | Proposal item | Status | Where / notes |
|---|---|---|---|
| 5.1 | Mapping awal via SLAM | ✅ | slam_toolbox + LiDAR `/scan`. See [docs/navigation-and-slam.md](docs/navigation-and-slam.md) (LiDAR-based; visual odometry not used) |
| 5.2 | Definisi waypoint per ruangan + label semantik | ✅ | YAML waypoint store in [go2_robot_sdk/config/waypoints.yaml](go2_robot_sdk/config/waypoints.yaml): each entry has `x`, `y`, `yaw` (map frame) + `label_en`/`label_id` for fuzzy name matching. Edit after first SLAM mapping session. Reload live without restart: `ros2 topic pub /reload_waypoints std_msgs/Empty "{}" --once`. |
| 5.3 | Voice command → navigation goal ("Dogo, ke Ruang A") | ✅ | [nav_waypoint_node.py](speech_processor/speech_processor/nav_waypoint_node.py) (`ENABLE_NAV_WAYPOINT=true`) subscribes to `/navigate_to_room` (String), fuzzy-matches the room name against `waypoints.yaml`, and sends a `nav2_msgs/action/NavigateToPose` goal to Nav2. Voice bridge: **keyword NLU** — `_GOTO_RE` regex catches "go to / ke / pergi ke `<room>`" and dispatches `("goto_room", room)` → `CommandDispatcher._nav_pub` → `/navigate_to_room`; **LLM NLU** — `ROBOT_CMD_SYSTEM_PROMPT` extended with `go_to_room:<room_name>`, all three parsers (openai/gemini/gemma_local) detect the `go_to_room:` prefix and return the room action tuple. TTS announces "Navigating to lobby" / "Arrived at lobby". Empty `/navigate_to_room` or voice "berhenti" cancels the in-flight Nav2 goal. |
| 5.4 | Dynamic obstacle avoidance + recovery behavior | ✅ | Nav2 costmaps + recovery behaviors ([config/nav2_params.yaml](go2_robot_sdk/config/nav2_params.yaml)) |

---

## C. Technical Components (Solusi Teknis §3)

| Component | Status | Where / notes |
|---|---|---|
| Speech pipeline (wake → STT → intent → dispatch) | ✅ | [stt_node.py](speech_processor/speech_processor/stt_node.py) + [voice_cmd_node.py](speech_processor/speech_processor/voice_cmd_node.py) |
| LLM layer (cloud API or local inference) | ✅ | openai / gemini / gemma_local |
| Vision pipeline (YOLO + face) | ✅ | YOLO ✅; face recognition ✅ — InsightFace SCRFD+ArcFace ([face_recognition_node.py](speech_processor/speech_processor/face_recognition_node.py)) + browser enrollment UI ([face_enrollment_node.py](speech_processor/speech_processor/face_enrollment_node.py), port 8890) + live threshold tuning |
| Navigation stack (SLAM + Nav2) | ✅ | slam_toolbox + Nav2 |
| Behavior coordinator (state machine arbitrasi voice/vision/nav) | ✅ | `twist_mux` handles velocity priority. [behavior_coordinator_node.py](speech_processor/speech_processor/behavior_coordinator_node.py) adds intent-level state machine (IDLE/VOICE_MOVE/FOLLOWING/NAVIGATING/APPROACHING/PATROL) — observes `/follow_enable`, `/navigation_status`, `/cmd_vel_voice`, `/approach_status`, `/patrol_status`; publishes `/behavior_mode` (TRANSIENT_LOCAL). Mutual exclusion enforced in `CommandDispatcher`: every activating action (follow, nav, approach, patrol) cancels all others before activating. |

---

## D. Validasi & Implementasi Lapangan

| # | Proposal item | Status | Notes |
|---|---|---|---|
| D1 | Unit testing per modul | ✅ | 543 pure-pytest unit tests across Modul 1, 2, 3, 4, 5 — see [docs/unit-tests.md](unit-tests.md) for the full test map. CI builds only (tests skipped in CI); run locally with `PYTHONPATH=speech_processor python -m pytest speech_processor/test/` |
| D2 | Integration testing end-to-end | 🟡 | Per-capability checklist in [docs/testing-capabilities.md](docs/testing-capabilities.md); not automated |
| D3 | Mapping & commissioning di lokasi klien (1 site) | ⬜ | Field activity — pending |
| D4 | Pelatihan operator (1 sesi ≤3 jam) | ⬜ | Pending |
| D5 | Dokumentasi teknis & user manual | 🟡 | Extensive `docs/` exists; dedicated operator **user manual** not yet written |
| D6 | Masa pemeliharaan 3 bulan | ⬜ | Post-delivery |

---

## Summary by module

| Module | Done | Partial | Not started |
|---|---|---|---|
| Modul 1 — Basic Voice | wake word, basic commands (ID), bilingual | — | — |
| Modul 2 — Extended Contextual | patrol (2.1), object approach (2.1/2.2), action chaining (2.2), custom command builder (2.3) | — | — |
| Modul 3 — Conversational AI | LLM, TTS, RAG, multi-turn memory | — | — |
| Modul 4 — Visual Perception | object detection (4.1), face recognition + enrollment (4.2), person tracking (4.3), visual conversational feedback — face greeting + scene description (4.4) | — | — |
| Modul 5 — Navigation | SLAM, semantic waypoints + voice→nav goal (5.2/5.3), obstacle avoidance | — | — |

**Roughly:** foundations and the milestone-payment "delivery anchors" (voice base, LLM conversation, TTS, object detection, SLAM/Nav2) are in place. Modul 2 (extended contextual commands — patrol, object approach, custom command builder) is now complete. Modul 4 (visual perception) is fully complete: face recognition + enrollment (4.2), greeting by name (4.4), and person tracking / follow-me (4.3). Modul 5.2 + 5.3 (go-to-room-by-voice) are complete. Behavior coordinator state machine (next box #7) is complete with IDLE/VOICE_MOVE/FOLLOWING/NAVIGATING/APPROACHING/PATROL states. The main remaining items are Modul 3 (conversational AI / RAG) and Modul 5 advanced (SLAM tuning, obstacle avoidance).

---

## Next boxes to tick (recommended order)

Prioritized for **highest demo value per unit of effort**, building on code that already exists.

1. ~~**Voice → Nav2 goal + named waypoints** (Modul 5.2 + 5.3)~~ — ✅ **done.**
   [nav_waypoint_node.py](speech_processor/speech_processor/nav_waypoint_node.py) + [waypoints.yaml](go2_robot_sdk/config/waypoints.yaml).
   Keyword NLU: `_GOTO_RE` regex → `("goto_room", room)` → `CommandDispatcher._nav_pub` → `/navigate_to_room` → Nav2 `NavigateToPose`.
   LLM NLU: `ROBOT_CMD_SYSTEM_PROMPT` extended with `go_to_room:<room>` format; all three parsers (openai/gemini/gemma_local) detect prefix.
   TTS announces navigation start and arrival. "Berhenti" cancels in-flight goal.

2. ~~**Multi-turn conversation memory** (Modul 3.4)~~ — ✅ **done.**
   Rolling 3-exchange window + 60s idle reset in the conversational path of [voice_cmd_node.py](speech_processor/speech_processor/voice_cmd_node.py). See [docs/conversation-memory.md](docs/conversation-memory.md).

3. ~~**Wire `/scene_description` into the conversational layer** (Modul 4.4)~~ — ✅ **done.**
   `/scene_description` (from `gemma_vision_node`) subscribed in `voice_cmd_node`, stored with a 10s TTL,
   and injected via `conversational_system_with_scene()` in `_ask_conversational()`. "What do you see?" now works.

4. ~~**Follow-me / person tracking** (Modul 4.3, incl. the descoped "ikut" command)~~ — ✅ **done.**
   [follow_me_node.py](speech_processor/speech_processor/follow_me_node.py) subscribes to `/detected_objects`,
   selects the largest `person` detection, and publishes `/cmd_vel_follow` (priority 6 in twist_mux). Voice wiring:
   "ikuti saya" → enable, "berhenti" → disable via `/follow_enable`. `ENABLE_FOLLOW=true` auto-enables YOLO.

5. ~~**Face recognition + enrollment** (Modul 4.2)~~ — ✅ **done.**
   InsightFace SCRFD+ArcFace [face_recognition_node.py](speech_processor/speech_processor/face_recognition_node.py)
   + browser enrollment UI [face_enrollment_node.py](speech_processor/speech_processor/face_enrollment_node.py) (port 8890:
   webcam/photo upload, name, Enroll → writes `face_db/<Name>/`, auto-reloads the recognizer) + live threshold
   tuning slider → `/face_threshold` live to the recognizer. Recognized names wired into the conversational greeting
   (Modul 4.4). See [docs/proposal-face-recognition.md](docs/proposal-face-recognition.md).
   Open item: commercial-license decision on the buffalo_* weights (may swap to YuNet+SFace via `FACE_MODEL_PACK`).

6. ~~**RAG over client knowledge base** (Modul 3.2)~~ — ✅ **done.**
   Lightweight embedding RAG (multilingual-e5 + file-based index) grounds the
   conversational reply on a venue KB. See [docs/knowledge-base.md](docs/knowledge-base.md).

7. ~~**Behavior coordinator state machine**~~ — ✅ **done.**
   [behavior_coordinator_node.py](speech_processor/speech_processor/behavior_coordinator_node.py) (`ENABLE_BEHAVIOR_COORDINATOR=true`).
   States: IDLE / VOICE_MOVE / FOLLOWING / NAVIGATING. Driven by existing status topics, no new control flow.
   Mutual exclusion fix in `CommandDispatcher`: `follow_start` cancels active Nav2 goal; `goto_room` disables follow-me.
   `/behavior_mode` published with TRANSIENT_LOCAL QoS — future patrol/converse nodes can subscribe and immediately see current state.

8. ✅ **Extended contextual commands + custom command builder** (Modul 2) — *complete.*
   - **2.1 — Patrol** (`patrol_node`, `ENABLE_PATROL=true`): cycles all `waypoints.yaml` entries via Nav2 `NavigateToPose` indefinitely. Voice: "patroli" / "mulai patroli" → start; "hentikan patroli" → stop. `PATROL_ROUTE` for a subset of waypoints.
   - **2.1 / 2.2 — Object approach** (`approach_object_node`, `ENABLE_APPROACH_OBJECT=true`): subscribes `/detected_objects` from YOLO, PD-controls `/cmd_vel_follow` toward the target class, stops when bbox fills `APPROACH_TARGET_AREA` fraction of image. No depth camera or Nav2 needed. Voice: "dekati bola" → `sports ball`; map in `_OBJECT_CLASS_MAP` in `voice_cmd_node.py`.
   - **2.3 — Custom command builder** (`config/custom_commands.yaml`): YAML-configurable trigger phrases (EN + ID per command), action_type covers `api_id`, `navigate_to_room`, `patrol_start/stop`, `follow_start/stop`, `approach_object`. Hot-reload via `/reload_custom_commands`. No code changes needed to add new operator commands.
   - CommandDispatcher enforces full mutual exclusion: every activating action cancels all others first.
   - `behavior_coordinator_node` extended with APPROACHING + PATROL states.

> A dedicated wake-word engine for Modul 1.1 (openWakeWord/Porcupine) was previously listed here but **dropped from the actionable backlog** — 1.1 is accepted as sufficient. It remains noted as optional hardening on the Modul 1.1 row above.

See [docs/unit-tests.md](unit-tests.md) for the full test map — per-file counts, per-class breakdown, ROS2 stub explanation, and run commands.
