# Architecture

## Clean Architecture Layers

The `go2_robot_sdk` package is organized into four strict layers. Dependencies only flow inward — outer layers depend on inner ones, never the reverse.

```
presentation/   Go2DriverNode         — ROS2 node, wires all layers together
application/    RobotDataService       — processes incoming WebRTC messages
                RobotControlService    — translates ROS2 commands to robot actions
infrastructure/ WebRTCAdapter          — manages Go2Connection(s), sends data to application
                ROS2Publisher          — converts domain entities to ROS2 messages
                LidarDecoder           — decodes compressed voxel frames
domain/         RobotConfig, RobotData — pure Python dataclasses, no external deps
                RTC_TOPIC, ROBOT_CMD   — all topic strings and command IDs
                IRobotDataPublisher    — interface implemented by ROS2Publisher
                IRobotController       — interface implemented by WebRTCAdapter
```

**Critical rule**: `domain/` must never import `rclpy` or any ROS2 type. Business logic in `application/` is testable without ROS2.

## Connection Mode Selection

`CONN_TYPE` selects the transport at startup. The rest of the stack (Nav2, SLAM, speech, YOLO) is identical in both modes.

| `CONN_TYPE` | Adapter | Command routing |
|---|---|---|
| `webrtc` (default) | `WebRTCAdapter` | JSON over WebRTC data channel → robot |
| `cyclonedds` | `CycloneDDSAdapter` | `/api/sport/request` (DDS) → robot |

---

## Inbound Data Flow (robot → ROS2)

```
Robot hardware
  │  WebRTC data channel (binary/JSON frames)
  ▼
Go2Connection          infrastructure/webrtc/go2_connection.py
  │  decodes binary frames, calls on_message callback
  ▼
WebRTCAdapter          infrastructure/webrtc/webrtc_adapter.py
  │  _on_data_channel_message → RobotDataService.process_webrtc_message()
  ▼
RobotDataService       application/services/robot_data_service.py
  │  matches msg["topic"] against RTC_TOPIC constants
  │  builds typed RobotData entity (OdometryData, IMUData, LidarData, …)
  │  calls IRobotDataPublisher method
  ▼
ROS2Publisher          infrastructure/ros2/ros2_publisher.py
  │  maps entity fields → ROS2 message types, stamps headers, broadcasts TF
  ▼
ROS2 topics            /odom, /imu, /joint_states, /point_cloud2, …
```

### Audio track (robot mic, `STT_SOURCE=robot`)

Audio is a separate WebRTC media track, not a data-channel frame. When `enable_audio` is set:

```
Robot onboard mic
  │  WebRTC audio track
  ▼
Go2Connection.on_track          (track.kind == "audio")
  ▼
Go2DriverNode._on_audio_frame   resamples each frame → mono s16 @ 16 kHz (av.AudioResampler)
  │  builds AudioData entity → ROS2Publisher.publish_audio_data()
  ▼
/robot_audio  (std_msgs/UInt8MultiArray, raw PCM)
  ▼
stt_node  (audio_source:=topic)  feeds the same VAD + STT backends as a local mic
```

This lets the GO2's own microphone drive STT even when the SDK runs on an external PC. `AudioData` is a pure-Python domain entity and `publish_audio_data()` is an `IRobotDataPublisher` method, so the audio path follows the same Clean-Architecture chain as video/LiDAR.

## Inbound Data Flow (CycloneDDS path)

When `CONN_TYPE=cyclonedds`, the robot publishes DDS topics directly and the SDK subscribes:

```
/sportmodestate (~50 Hz)   → _on_cyclonedds_sport_state() → publish_robot_state() → /go2_states, /imu
/lowstate (~500 Hz)        → _on_cyclonedds_low_state()   → publish_joint_state() → /joint_states, /imu
/utlidar/robot_pose        → _on_cyclonedds_pose()        → publish_odometry()    → /odom, TF
/utlidar/cloud             → _on_cyclonedds_lidar()       → /point_cloud2
/wirelesscontroller        → _on_cyclonedds_wireless()    → debug log
```

`WebRTCAdapter` and `Go2Connection` are not used in this path.

---

## Outbound Data Flow (ROS2 → robot)

```
/cmd_vel_out  (Twist)          → Go2DriverNode._on_cmd_vel()
/webrtc_req   (WebRtcReq)      → Go2DriverNode._on_webrtc_req()
/joy          (Joy)            → Go2DriverNode._on_joy()
  │
  ▼
RobotControlService    application/services/robot_control_service.py
  │  handle_cmd_vel / handle_webrtc_request / handle_joy_command
  ▼
WebRTCAdapter.send_movement_command / send_webrtc_request
  ▼
Go2Connection.data_channel.send()
  ▼
Robot hardware
```

## Threading Model

`main.py` creates a single asyncio event loop via `asyncio.run(main_async())`.

- **ROS2 spin** runs inside a `threading.Thread` using `SingleThreadedExecutor`.
- **WebRTC coroutines** run on the asyncio event loop in the main thread.
- `Go2DriverNode` receives the event loop reference at construction and uses `event_loop.call_soon_threadsafe()` to schedule WebRTC sends from ROS2 callbacks safely.

Never call `asyncio.run()` or `rclpy.spin()` directly from an already-running loop — the existing design routes all cross-thread calls through `call_soon_threadsafe`.

## Multi-Robot Mode

`ROBOT_IP="ip1,ip2"` triggers multi mode: `RobotConfig.conn_mode = "multi"`.

- `WebRTCAdapter` creates one `Go2Connection` per IP, keyed by `robot_id` string (`"0"`, `"1"`, …).
- `Go2DriverNode._setup_publishers()` creates a separate publisher list per robot and prefixes topics: `/robot0/joint_states`, `/robot1/odom`, etc.
- The URDF is automatically switched to `multi_go2.urdf`.
- TF child frames become `robot0/base_link`, `robot1/base_link`.

## WebRTC Connection Internals

`Go2Connection` (infrastructure/webrtc/go2_connection.py):

1. Performs HTTP signaling with the robot at `http://<ip>:9991`.
2. Uses AES-GCM encryption (`crypto/encryption.py`) for the validation handshake.
3. Creates an `RTCPeerConnection` via `aiortc`, opens a data channel (`id=0`), and optionally adds video and (when `enable_audio` / `STT_SOURCE=robot`) audio transceivers (`recvonly`).
4. LiDAR frames arrive as binary messages; `WebRTCDataDecoder` delegates to `LidarDecoder` when `decode_lidar=True`.
5. When `enable_audio` is set, `on_track` also receives the robot's **audio** track (the onboard mic) — see *Audio track* below.

## LiDAR Pipeline

```
WebRTC binary frame
  ▼
WebRTCDataDecoder      infrastructure/webrtc/data_decoder.py
  │  detects binary vs JSON, delegates binary to LidarDecoder
  ▼
LidarDecoder           infrastructure/sensors/lidar_decoder.py
  │  decompresses voxel map, returns point positions + metadata
  ▼
RobotDataService       application — wraps as LidarData entity
  ▼
ROS2Publisher          publishes sensor_msgs/PointCloud2 on /point_cloud2 (~7 Hz)
  ▼
pointcloud_to_laserscan_node → /scan (used by SLAM + Nav2 costmaps)
```

Additionally, `lidar_processor/lidar_to_pointcloud_node.py` subscribes to the raw PointCloud2, applies voxel downsampling, and optionally saves `.ply` snapshots every 10 s when `MAP_SAVE=True`.

## Speech Pipeline

The speech system lives in the `speech_processor` package. All nodes are opt-in. Three pipeline paths are available depending on `STT_PROVIDER`:

### Path A — `faster_whisper` (default, transcription only)

Three nodes run in sequence. `voice_cmd_node` is started automatically.

> **Audio source:** by default `stt_node`/`mic_bridge_node` capture a local mic. Set `STT_SOURCE=robot` (driver `enable_audio`, requires `CONN_TYPE=webrtc` + `MIC_BRIDGE=false`) to instead feed the GO2's onboard mic from `/robot_audio` into `stt_node` — see *Audio track (robot mic)* above. Everything downstream of the VAD is unchanged.

```
[Host microphone  OR  /robot_audio (STT_SOURCE=robot)]
  │
  ├─── stt_node          (sounddevice local mic, or /robot_audio when audio_source:=topic)
  └─── mic_bridge_node   (WebSocket — browser mic, Windows 11 + Docker)
         │  serves HTML UI at http://localhost:8888 (8889 for PCM WebSocket)
         │  energy-threshold VAD buffers voiced frames, flushes on silence
         │
         ▼
       _FasterWhisperBackend   (~50 ms GPU / ~300 ms CPU, offline)
         │  wake-word string check (WAKE_WORD env var, default "elliot")
         │  utterances without the wake word → discarded, echoed [ignored] to browser
         ▼
       /speech_text  (std_msgs/String)
         ▼
       voice_cmd_node   keyword / openai / gemini NLU → command dispatch
         ├─── /cmd_vel_voice  (Twist)      movement → twist_mux priority 7
         └─── /webrtc_req or /sim_cmd      posture / gait / gesture
                ▼
              /tts  (String)  → tts_node → /tts_audio → browser / robot speaker
```

### Path B — `gemma_local` (unified, 1 REST call)

`mic_bridge_node` handles the entire pipeline. `voice_cmd_node` is **not started**.

Uses Gemma 4's **native tool calling** (llama-server is launched with `--jinja`).
The model picks between two tools, and that discrete choice — not an `"unknown"`
sentinel in a forced field — is the high-confidence gate, so ambiguous speech is
no longer force-fit onto the nearest command. `command` is grammar-constrained to
the exact `CMD_MAP` keys, so hallucinated command names are impossible. If the
server returns no `tool_calls` (e.g. `--jinja` disabled), the backend falls back
to parsing a JSON content body.

**Language (`VOICE_LANG`)**: the instruction context is English regardless of
`VOICE_LANG` (an all-Bahasa context destabilised Gemma's audio transcription into
repetition loops). For `id`, Gemma reliably *transcribes* Indonesian but tends to
under-fire the command tool, so a deterministic `id`-scoped safety net maps the
transcript to a `CMD_MAP` key via `command_for_text()` (Indonesian glossary +
question guard). A wake-word string-match override likewise corrects a missed
`contains_wake_word`. The emitted command is always an English `CMD_MAP` key.

> Audio note: the first audio request applies a `<|channel>thought` stop sequence
> to fail a cold-start reasoning loop fast; the single retry runs **without** the
> stop so a short reasoning preamble + the forced tool call can complete (some
> inputs always reason first).

```
[Host microphone]
  │
  └─── mic_bridge_node / stt_node
         │  VAD buffers utterance (same as Path A)
         ▼
       _GemmaUnifiedBackend   (1 POST to llama.cpp /v1/chat/completions, tool_choice=required)
         │  audio in → tool_call:
         │     execute_robot_command{transcript, contains_wake_word, command}
         │     respond_conversationally{transcript, contains_wake_word, spoken_reply}
         │
         ├─ respond_conversationally, contains_wake_word == false → [ignored] echo
         │
         ├─ respond_conversationally, contains_wake_word == true
         │      └─── spoken_reply → /tts → tts_node → /tts_audio → browser
         │
         └─ execute_robot_command (wake word present)
              ├─── command dispatch (via CommandDispatcher)
              │      /cmd_vel_voice  or  /webrtc_req / /sim_cmd
              └─── canned FEEDBACK_MAP string → /tts → tts_node → /tts_audio → browser
```

### Path C — `openai_realtime` / `gemini_live` (unified, persistent WebSocket)

`mic_bridge_node` only (persistent WebSocket sessions are incompatible with `stt_node`'s synchronous sounddevice loop). `voice_cmd_node` is **not started**.

```
[Host browser mic]
  │
  └─── mic_bridge_node
         │  VAD buffers utterance
         ▼
       _OpenAIRealtimeBackend  (gpt-realtime-2 WebSocket, persistent session)
       _GeminiLiveBackend      (Gemini 2.5 Flash Live WebSocket, persistent session)
         │
         │  audio in
         │  ← function_call: {contains_wake_word, command, parameters}
         │  ← audio_response: PCM chunks (model-generated TTS, re-encoded to MP3)
         │
         ├─ contains_wake_word == false → [ignored] echo, discard audio
         │
         └─ contains_wake_word == true
              ├─── command dispatch (via CommandDispatcher)
              │      /cmd_vel_voice  or  /webrtc_req
              └─── audio_response → /tts_audio (UInt8MultiArray) → browser
                     (bypasses tts_node entirely — model speaks the response)
```

### Shared: `command_dispatcher.py`

`speech_processor/command_dispatcher.py` holds the canonical `CMD_MAP` (30+ robot commands), `FEEDBACK_MAP`, and `CommandDispatcher` class (10 Hz velocity sustain timer + timed-stop logic). Both `voice_cmd_node` (Path A) and `mic_bridge_node` / `stt_node` (Paths B/C) import from it so the command vocabulary and movement behaviour are identical across all providers.

### TTS path (`/tts` → robot speaker / host speaker)

Used by Paths A and B. Path C bypasses this entirely (audio comes directly from the model).

```
/tts  (std_msgs/String)
  ▼
tts_node  speech_processor/tts_node.py
  │  supertonic   offline neural TTS, flow-matching, no API key  ← default
  │  openai       tts-1 / tts-1-hd via OpenAI API
  │  elevenlabs   ElevenLabs API
  │  gemini       gemini-2.5-flash-tts-preview
  │
  ├─── /tts_audio (UInt8MultiArray, MP3) → mic_bridge_node → browser speaker
  └─── /webrtc_req (api_ids 4001–4003)  → Go2Connection → robot speaker
```

### Voice command path (Path A only)

```
/speech_text  (std_msgs/String)
  ▼
voice_cmd_node  (started only for pure-STT providers: faster_whisper, openai, gemini)
  │  keyword      regex ~30 phrases, offline  ← default
  │  openai       GPT-4o-mini structured JSON
  │  gemini       gemini-2.5-flash JSON
  │  gemma_local  Gemma 4 E4B via llama.cpp (NLU-only, same sidecar as Path B)
  │
  ├─── /cmd_vel_voice   (Twist)   movement → twist_mux priority 7
  └─── /webrtc_req or /sim_cmd   posture / gait / gesture
         hardware-only gestures silently skipped in simulation
```

## Vision Pipeline

Two object-detection nodes are available. They are standalone packages that subscribe to the camera topic and publish results — no driver changes are needed.

### YOLO detector (default)

```
/camera/image_raw  (sensor_msgs/Image)   hardware
/go2_camera/color/image  (simulation)    ← remap required: -r /camera/image_raw:=...
  ▼
yolo_detector_node   yolo_detector package
  │  Ultralytics YOLOv11; weights downloaded to ~/.cache/ultralytics/ on first run
  │  parameters: model (yolo11n.pt), device (cpu/cuda), detection_threshold (0.5)
  │
  ├─── /detected_objects  (vision_msgs/Detection2DArray)
  └─── /annotated_image   (sensor_msgs/Image)   bounding boxes overlaid on frame
```

### Gemma Vision node (Windows GPU profile, `ENABLE_GEMMA_VISION=true`)

```
/camera/image_raw  (sensor_msgs/Image, configurable via camera_topic parameter)
  ▼
gemma_vision_node   speech_processor package
  │  rate-limited to inference_rate Hz (default 0.5 Hz — one frame every 2 s)
  │  encodes frame as JPEG base64, sends to llama.cpp sidecar running Gemma 4 E4B
  │  via OpenAI-compatible /v1/chat/completions endpoint
  │
  ├─── /scene_description      (std_msgs/String)   natural-language description
  └─── /gemma_annotated_image  (sensor_msgs/Image) frame with text overlaid
```

This node produces human-readable text ("a person is standing near a chair on the left") rather than structured bounding boxes, making it suited for conversational queries ("what do you see?") rather than downstream perception pipelines. Use `yolo_detector` when structured `Detection2DArray` output is needed.
