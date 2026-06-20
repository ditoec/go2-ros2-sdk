# GO2 EduPlus AI — Module & Feature Tracker

Status of the work proposed in *"Proposal: Jasa Konfigurasi & Pemrograman AI untuk Unitree Go2 EduPlus"* (8 May 2026) against what currently exists in this repository.

**Legend:** ✅ Done · 🟡 Partial · ⬜ Not started

---

## A. Instalasi & Konfigurasi Dasar

| # | Proposal item | Status | Where / notes |
|---|---|---|---|
| A1 | Audit konfigurasi awal + setup ROS2 workspace | ✅ | Full ROS2 (Humble/Jazzy) workspace, `colcon build`. See [CLAUDE.md](CLAUDE.md), [docs/architecture.md](docs/architecture.md) |
| A2 | Instalasi dependencies AI (CUDA, PyTorch, ROS2 packages) | ✅ | [requirements.txt](requirements.txt) + Docker images: Jetson CUDA ([docker/Dockerfile.jetson](docker/Dockerfile.jetson)), Windows GPU ([docker/Dockerfile.windows-gpu](docker/Dockerfile.windows-gpu)) |
| A3 | Konfigurasi sensor: microphone, RGB-D camera, LiDAR | ✅ | LiDAR ✅, camera ✅. Mic: **use the GO2's onboard mic** three ways — (1) onboard ALSA `/dev/snd` via [stt_node.py](speech_processor/speech_processor/stt_node.py) (Jetson compose defaults `MIC_BRIDGE=false`, [docker-compose.jetson.yml:54](docker/docker-compose.jetson.yml#L54)); (2) **robot's WebRTC mic track** captured by the driver → `/robot_audio` → stt_node, set `STT_SOURCE=robot` (works from an external PC over Wi-Fi); (3) browser bridge ([mic_bridge_node.py](speech_processor/speech_processor/mic_bridge_node.py)) for off-robot dev. Mic-array/beamforming descoped |
| A4 | Remote access + logging system untuk debugging | ✅ | **Remote access:** VNC desktop (`localhost:5901`) + **Foxglove bridge** (`ws://localhost:8765`, on by default — [robot.launch.py:87](go2_robot_sdk/launch/robot.launch.py#L87)) for remote inspection of all topics. **Logging/capture:** `ENABLE_BAG=true` records a timestamped rosbag2 session (curated topics by default, `BAG_TOPICS=-a` for everything) persisted to host `./bags` ([docker-compose.yml](docker/docker-compose.yml)) — replayable in Foxglove or `ros2 bag play` |

---

## B. Modul AI

### Modul 1 — Basic Voice Command Recognition

| # | Proposal item | Status | Where / notes |
|---|---|---|---|
| 1.1 | Wake-word detection ("Hey Dogo") | ✅ | Wake word detected from structured STT output (`wake_word` param, e.g. `doggo`/`elliot`) and gates command execution in [stt_node.py](speech_processor/speech_processor/stt_node.py). Accepted as sufficient |
| 1.2 | Mapping perintah dasar → API motion | ✅ | Basic set mapped in [command_dispatcher.py](speech_processor/speech_processor/command_dispatcher.py) (`CMD_MAP` + `COMMAND_GLOSSARY`): **duduk**→sit, **berdiri**→stand, **jalan maju**→forward, **jalan mundur**→backward, **putar kiri**→turn_left, **putar kanan**→turn_right, **berhenti**→stop. ("ikut / follow me" descoped from the basic set → tracked under Modul 4.3 person-tracking) |
| 1.3 | Dukungan bilingual: Bahasa Indonesia & English | ✅ | `VOICE_LANG=en\|id`, Indonesian glossary in [command_dispatcher.py](speech_processor/speech_processor/command_dispatcher.py) (`COMMAND_GLOSSARY`) |

### Modul 2 — Extended Contextual Commands

| # | Proposal item | Status | Where / notes |
|---|---|---|---|
| 2.1 | Perintah kompleks berbasis intent ("ambilkan bola", "ikuti saya", "patroli") | ⬜ | LLM NLU only maps speech onto the **existing** motion `CMD_MAP`. No fetch / follow / patrol behaviors |
| 2.2 | Action chaining: voice → object detection → navigation → manipulation | ⬜ | No orchestrator linking perception → navigation → action |
| 2.3 | Custom command builder untuk end user | ⬜ | Command table is hard-coded in source; no user-facing builder/config |

### Modul 3 — Conversational AI (LLM Integration)

| # | Proposal item | Status | Where / notes |
|---|---|---|---|
| 3.1 | Integrasi LLM (cloud/on-device) dengan persona yang dapat dikustomisasi | ✅ | openai / gemini / gemma_local (offline llama.cpp) in [voice_cmd_node.py](speech_processor/speech_processor/voice_cmd_node.py). Persona via system prompt (`CONVERSATIONAL_SYSTEM`) — editable in code, not yet a config knob |
| 3.2 | RAG opsional untuk Q&A berbasis knowledge base klien | ⬜ | Web search (DuckDuckGo) exists, but **no RAG over a client knowledge base** |
| 3.3 | Text-to-Speech suara natural (ID & EN) | ✅ | supertonic (offline) / openai / elevenlabs / gemini in [tts_node.py](speech_processor/speech_processor/tts_node.py); `SUPERTONIC_LANG` / `VOICE_LANG` |
| 3.4 | Percakapan multi-turn dengan context memory | ⬜ | Each utterance is processed statelessly — no conversation history kept |

### Modul 4 — Visual Perception (Object & Face Recognition)

| # | Proposal item | Status | Where / notes |
|---|---|---|---|
| 4.1 | Real-time object detection (YOLOv8/setara) | ✅ | YOLOv11 in [yolo_detector_node.py](yolo_detector/yolo_detector/yolo_detector_node.py) → `/detected_objects`. Plus VLM scene text in [gemma_vision_node.py](speech_processor/speech_processor/gemma_vision_node.py) → `/scene_description` |
| 4.2 | Face detection + recognition, database wajah yang bisa di-enroll | ⬜ | No face pipeline (dlib/InsightFace) and no enrollment DB |
| 4.3 | Person tracking saat robot bergerak ("ikuti saya") | ⬜ | No tracker driving `/cmd_vel` from person detections |
| 4.4 | Visual feedback ke conversational layer (sebut nama orang dikenali) | ⬜ | `/scene_description` exists but is **not wired** into the conversational reply path; no face names |

### Modul 5 — Autonomous Indoor Navigation

| # | Proposal item | Status | Where / notes |
|---|---|---|---|
| 5.1 | Mapping awal via SLAM | ✅ | slam_toolbox + LiDAR `/scan`. See [docs/navigation-and-slam.md](docs/navigation-and-slam.md) (LiDAR-based; visual odometry not used) |
| 5.2 | Definisi waypoint per ruangan + label semantik | ⬜ | Goals are set ad-hoc via RViz "Nav2 Goal" only — no stored named/semantic waypoints |
| 5.3 | Voice command → navigation goal ("Dogo, ke Ruang A") | ⬜ | Voice path emits **motion** commands only; no bridge to a Nav2 goal |
| 5.4 | Dynamic obstacle avoidance + recovery behavior | ✅ | Nav2 costmaps + recovery behaviors ([config/nav2_params.yaml](go2_robot_sdk/config/nav2_params.yaml)) |

---

## C. Technical Components (Solusi Teknis §3)

| Component | Status | Where / notes |
|---|---|---|
| Speech pipeline (wake → STT → intent → dispatch) | ✅ | [stt_node.py](speech_processor/speech_processor/stt_node.py) + [voice_cmd_node.py](speech_processor/speech_processor/voice_cmd_node.py) |
| LLM layer (cloud API or local inference) | ✅ | openai / gemini / gemma_local |
| Vision pipeline (YOLO + face) | 🟡 | YOLO ✅, face recognition ⬜ |
| Navigation stack (SLAM + Nav2) | ✅ | slam_toolbox + Nav2 |
| Behavior coordinator (state machine arbitrasi voice/vision/nav) | 🟡 | `twist_mux` does **velocity priority** arbitration (joy 10 > voice 7 > nav 5, [config/twist_mux.yaml](go2_robot_sdk/config/twist_mux.yaml)). No full behavior state machine |

---

## D. Validasi & Implementasi Lapangan

| # | Proposal item | Status | Notes |
|---|---|---|---|
| D1 | Unit testing per modul | 🟡 | `test/unit` + `test/integration` exist; CI builds only (tests skipped) |
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
| Modul 2 — Extended Contextual | — | — | intent cmds, action chaining, cmd builder |
| Modul 3 — Conversational AI | LLM, TTS | — | RAG, multi-turn memory |
| Modul 4 — Visual Perception | object detection | — | face recog, person tracking, visual→convo |
| Modul 5 — Navigation | SLAM, obstacle avoidance | — | semantic waypoints, voice→nav goal |

**Roughly:** foundations and the milestone-payment "delivery anchors" (voice base, LLM conversation, TTS, object detection, SLAM/Nav2) are in place. The **differentiating behaviors** that make the demos land — follow-me, go-to-room-by-voice, face recognition — are the main gaps.

---

## Next boxes to tick (recommended order)

Prioritized for **highest demo value per unit of effort**, building on code that already exists.

1. **Voice → Nav2 goal + named waypoints** (Modul 5.2 + 5.3) — *high value, medium effort.*
   The headline demo ("Dogo, ke Ruang A"). Add a small semantic-waypoint store (YAML: name → pose) and a node that turns a recognized "go to <room>" intent into a `nav2_msgs/NavigateToPose` goal. Nav2 + voice NLU already exist — this is glue, not new infrastructure.

2. **Multi-turn conversation memory** (Modul 3.4) — *high value, low effort.*
   Keep a short rolling message history per session in the conversational path of [voice_cmd_node.py](speech_processor/speech_processor/voice_cmd_node.py)/[stt_node.py](speech_processor/speech_processor/stt_node.py). Makes the "museum receptionist" persona feel real with a tiny change.

3. **Wire `/scene_description` into the conversational layer** (Modul 4.4) — *low effort.*
   `gemma_vision_node` already publishes scene text. Let the conversational reply consume the latest description so "what do you see?" works. Stepping stone toward visual feedback.

4. **Follow-me / person tracking** (Modul 4.3, incl. the descoped "ikut" command) — *high value, medium effort.*
   Use existing YOLO `person` detections to drive `/cmd_vel_voice` (centroid → angular, bbox size → linear).

5. **Face recognition + enrollment** (Modul 4.2) — *medium/high effort.*
   Add an InsightFace/`face_recognition` node with an enrollable embedding DB; publish recognized names, then feed into #3 so the robot greets people by name.

6. **Dedicated wake-word engine** (Modul 1.1) — *low/medium effort, polish.*
   Swap transcript-substring matching for openWakeWord/Porcupine for true always-on, low-latency "Hey Dogo" before committing STT.

7. **RAG over client knowledge base** (Modul 3.2, *optional in proposal*) — *medium effort.*
   Add a vector store + retrieval step ahead of the LLM call for grounded museum/venue Q&A.

8. **Behavior coordinator state machine** (Solusi Teknis) — *medium effort.*
   Formal arbitration (idle / converse / navigate / follow / patrol) above `twist_mux`, needed once #1 and #4 can compete for control.

9. **Extended contextual commands + custom command builder** (Modul 2) — *higher effort.*
   "Ambilkan bola" / "patroli" and a config-driven command table. Best tackled after the coordinator (#8) exists.
