# Docker Compose Guide

The SDK ships three Compose files that layer on top of each other. The base file
(`docker-compose.yml`) is always required. Override files are stacked with `-f` to
add platform-specific behaviour.

| File | Purpose |
|---|---|
| `docker/docker-compose.yml` | Base — always required |
| `docker/docker-compose.windows.yml` | Windows 11: WSLg PulseAudio socket for microphone access |
| `docker/docker-compose.jetson.yml` | Jetson NX 16 GB: ARM64+CUDA image, GPU reservation, `PIPER_USE_CUDA=true` |

---

## Quick Start

```bash
# Build once (applies to all platforms and modes)
docker-compose build

# Windows 11 — hardware mode (no microphone)
ROBOT_IP=192.168.x.x docker-compose up

# Windows 11 — hardware mode (with microphone for STT + voice commands)
ROBOT_IP=192.168.x.x \
  docker-compose -f docker/docker-compose.yml \
                 -f docker/docker-compose.windows.yml up

# Windows 11 — simulation, no microphone
USE_SIM=true docker-compose up

# Windows 11 — simulation WITH microphone (voice commands work in sim too)
USE_SIM=true \
  docker-compose -f docker/docker-compose.yml \
                 -f docker/docker-compose.windows.yml up

# Jetson NX 16 GB — hardware mode
ROBOT_IP=192.168.x.x \
  docker-compose -f docker/docker-compose.yml \
                 -f docker/docker-compose.jetson.yml up

# Jetson NX 16 GB — simulation
USE_SIM=true \
  docker-compose -f docker/docker-compose.yml \
                 -f docker/docker-compose.jetson.yml up
```

VNC access (RViz / Gazebo GUI) is always available at `localhost:5901`, password `ros2vnc`.

---

## Platform Decision Flowchart

```
What hardware are you running on?

  Windows 11 + Docker Desktop + WSL2
    Hardware, no mic:   ROBOT_IP=x.x.x.x docker-compose up
    Hardware, with mic: ROBOT_IP=x.x.x.x docker-compose \
                          -f docker/docker-compose.yml \
                          -f docker/docker-compose.windows.yml up
    Sim, no mic:        USE_SIM=true docker-compose up
    Sim, with mic:      USE_SIM=true docker-compose \
                          -f docker/docker-compose.yml \
                          -f docker/docker-compose.windows.yml up

  Jetson NX 16 GB (JetPack 6)
    Hardware: ROBOT_IP=x.x.x.x docker-compose \
                -f docker/docker-compose.yml \
                -f docker/docker-compose.jetson.yml up
    Sim:      USE_SIM=true docker-compose \
                -f docker/docker-compose.yml \
                -f docker/docker-compose.jetson.yml up
    └─ Microphone works via /dev/snd — no extra override needed
```

---

## Dockerfiles

| Dockerfile | Base image | Architecture | Used by |
|---|---|---|---|
| `docker/Dockerfile` | `ros:jazzy-ros-base` | x86_64 | Windows 11 (Docker Desktop + WSL2) |
| `docker/Dockerfile.jetson` | `dustynv/ros:jazzy-ros-base-l4t-r36.4.0` | ARM64 + CUDA 12 | Jetson NX 16 GB (JetPack 6) |

Both images include Gazebo Harmonic, VNC, Piper TTS (with `en_US-lessac-medium` voice pre-baked), and all ROS2 packages — no runtime downloads on first start.

---

## Environment Variable Reference

### Mode

| Variable | Default | Values | Description |
|---|---|---|---|
| `USE_SIM` | `false` | `false` / `true` | `false` → hardware driver (needs `ROBOT_IP`). `true` → Gazebo Harmonic simulation, no robot required. |

### Hardware Connection

Ignored when `USE_SIM=true`.

| Variable | Default | Values | Description |
|---|---|---|---|
| `ROBOT_IP` | _(empty)_ | IP or comma-separated list | Robot IP address, e.g. `192.168.12.1`. Comma-separate for multi-robot: `192.168.12.1,192.168.12.2`. |
| `CONN_TYPE` | `webrtc` | `webrtc` / `cyclonedds` | `webrtc` → Wi-Fi via aiortc (close the Unitree app first). `cyclonedds` → Ethernet / onboard Jetson (stub only, not fully implemented). |
| `WEBRTC_SERVER_PORT` | `9991` | port number | WebRTC signalling port. |
| `ROBOT_TOKEN` | _(empty)_ | token string | API token required by some firmware versions. |

### Map / LiDAR

| Variable | Default | Values | Description |
|---|---|---|---|
| `MAP_SAVE` | `false` | `false` / `true` | Save `.ply` point cloud to disk every 10 s. |
| `MAP_NAME` | `3d_map` | filename prefix | Prefix for saved `.ply` files. |

### TTS — Text-to-Speech

TTS starts automatically with every launch. No `ENABLE_TTS` flag exists.

| Variable | Default | Values | Description |
|---|---|---|---|
| `TTS_PROVIDER` | `piper` | `piper` / `espeak` / `openai` / `elevenlabs` / `gemini` | Synthesis backend. `piper` and `espeak` are offline; cloud providers need an API key. |
| `TTS_VOICE` | `en_US-lessac-medium` | see below | Voice identifier. Meaning depends on provider. |
| `PIPER_VOICE_DIR` | `/root/.local/share/piper/voices` | directory path | Where Piper `.onnx` model files are stored. Pre-baked in the Docker image. |
| `PIPER_USE_CUDA` | `false` (`true` on Jetson) | `false` / `true` | GPU-accelerated Piper inference via ONNX Runtime. Set automatically by `docker-compose.jetson.yml`. |
| `OPENAI_API_KEY` | _(empty)_ | `sk-…` | Required when `TTS_PROVIDER=openai`. Also used by STT and NLU. |
| `ELEVENLABS_API_KEY` | _(empty)_ | API key | Required when `TTS_PROVIDER=elevenlabs`. |
| `GEMINI_API_KEY` | _(empty)_ | API key | Required when `TTS_PROVIDER=gemini`. Also used by STT and NLU. |
| `ANTHROPIC_API_KEY` | _(empty)_ | `sk-ant-…` | Required when `NLU_PROVIDER=claude`. Not used by TTS or STT. |

**`TTS_VOICE` by provider:**

| Provider | Voice format | Example | Notes |
|---|---|---|---|
| `piper` | `lang_COUNTRY-speaker-quality` | `en_US-lessac-medium` | Full list: [rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices) |
| `espeak` | espeak-ng voice string | `en`, `en-gb`, `de` | Run `espeak-ng --voices` for all options |
| `openai` | voice name | `nova` | `alloy` / `echo` / `fable` / `onyx` / `nova` / `shimmer` |
| `elevenlabs` | voice ID | `XrExE9yKIg1WjnnlVkGX` | Get IDs from ElevenLabs dashboard |
| `gemini` | voice name | `Kore` | `Kore` / `Zephyr` / `Puck` / `Charon` / `Fenrir` / `Leda` / `Orus` / `Aoede` / `Callirrhoe` |

### STT — Speech-to-Text

| Variable | Default | Values | Description |
|---|---|---|---|
| `ENABLE_STT` | `true` | `true` / `false` | Start `stt_node`. Requires a microphone (see [Microphone](#microphone)). |
| `STT_PROVIDER` | `faster_whisper` | `faster_whisper` / `openai` / `vosk` / `gemini` | `faster_whisper` → local CTranslate2 (~30 ms GPU / ~300 ms CPU). `openai` / `gemini` → cloud API (~1–2 s). |
| `STT_DEVICE` | `cpu` | `cpu` / `cuda` | `cuda` requires `nvidia-container-toolkit` and GPU reservation. |
| `WHISPER_MODEL` | `base` | `tiny` / `base` / `small` / `medium` | Model size for `faster_whisper`. Larger = better accuracy, more RAM. |
| `STT_LANGUAGE` | `en` | Whisper language code | Target language for transcription. |

### Voice Commands

| Variable | Default | Values | Description |
|---|---|---|---|
| `ENABLE_VOICE_CMD` | `true` | `true` / `false` | Start `voice_cmd_node`. Routes `/speech_text` → robot commands and `/cmd_vel_voice`. |
| `NLU_PROVIDER` | `keyword` | `keyword` / `openai` / `gemini` / `claude` | `keyword` → regex matching, instant, fully offline. Others → LLM-based free-form parsing, needs API key. |
| `VOICE_MOVE_DURATION` | `2.0` | seconds | How long movement commands run before auto-stopping. |
| `VOICE_LINEAR_SPEED` | `0.3` | m/s | Forward / backward speed for voice movement commands. |
| `VOICE_ANGULAR_SPEED` | `0.5` | rad/s | Turn speed for voice rotation commands. |

### VNC

| Variable | Default | Description |
|---|---|---|
| `VNC_RESOLUTION` | `1920x1080` | Screen resolution of the virtual display. |
| `VNC_PASSWORD` | `ros2vnc` | VNC login password. Set at runtime: `VNC_PASSWORD=mypass docker-compose up`. |

---

## Ports

| Port | Protocol | Service |
|---|---|---|
| `5901` | TCP | VNC — connect with any VNC client to `localhost:5901` |
| `8765` | TCP | Foxglove WebSocket — open Foxglove Studio → WebSocket → `ws://localhost:8765` |
| `8888` | TCP | `mic_bridge_node` HTML page — open in the host browser to stream mic audio |
| `8889` | TCP | `mic_bridge_node` WebSocket — browser PCM audio stream (used internally by the page) |
| `9991` | TCP | WebRTC signalling server |

---

## Microphone

`stt_node` records audio via `sounddevice` (PortAudio). How the microphone reaches the container differs by platform.

### Jetson NX 16 GB

`docker-compose.yml` maps `/dev/snd:/dev/snd`. Plug in a USB mic and it is available automatically — no extra override file needed.

### Windows 11 — Docker Desktop + WSL2

WSL2 does not expose `/dev/snd`. Two routes are available; the container supports both simultaneously.

#### Route 1 — WSLg PulseAudio (native Windows mic)

`docker-compose.windows.yml` mounts the WSLg PulseAudio socket so `stt_node` can access the Windows microphone directly.

Two things must reach the container — the socket alone is not enough:

| What | Host path | Container path |
|---|---|---|
| Unix socket | `/mnt/wslg/runtime-dir/pulse/native` | `/tmp/pulse/native` |
| Auth cookie | `/mnt/wslg/.config/pulse/cookie` | `/root/.config/pulse/cookie` |

**Known limitation:** Docker containers run as root (uid 0). WSLg's PulseAudio server runs as uid 1000 and uses `auth-unix-uid`. Even with the correct cookie, the UID mismatch causes the server to return `pa_context_connect() failed: Access denied`. The container detects this at startup and falls back to Route 2 automatically.

**One-time check — confirm both WSLg files exist:**

```powershell
wsl ls /mnt/wslg/runtime-dir/pulse/native
wsl ls /mnt/wslg/.config/pulse/cookie
# Both lines should print the path back.
# If either is missing: run  wsl --update  then restart Docker Desktop.
```

**Run with microphone — hardware mode:**

```bash
ROBOT_IP=192.168.x.x \
  docker-compose -f docker/docker-compose.yml \
                 -f docker/docker-compose.windows.yml up
```

**Run with microphone — simulation mode:**

```bash
USE_SIM=true \
  docker-compose -f docker/docker-compose.yml \
                 -f docker/docker-compose.windows.yml up
```

#### Route 2 — Browser mic bridge (always available)

`mic_bridge_node` is started automatically whenever `ENABLE_STT=true`. It serves a small HTML page at `http://localhost:8888`. Opening this page in the host browser and clicking **Start Microphone** grants the browser direct OS-level mic access (via `getUserMedia()`), which it streams to the container as raw PCM over WebSocket on port 8889. The same VAD + STT pipeline used by `stt_node` processes the audio and publishes to `/speech_text`.

This route works regardless of Docker audio configuration — no `docker-compose.windows.yml` required.

```
┌─────────────────────┐   getUserMedia()    ┌──────────────────────────┐
│  Host Browser       │ ─────────────────►  │  mic_bridge_node         │
│  localhost:8888     │  WS localhost:8889  │  VAD + STT → /speech_text│
└─────────────────────┘                     └──────────────────────────┘
```

**How to use it:**

1. Start the container with `ENABLE_STT=true` (the Docker Compose default)
2. Open `http://localhost:8888` in your Windows browser
3. Click **Start Microphone** and grant microphone permission
4. Speak — transcriptions appear in the browser tab and publish to `/speech_text`

#### Automatic audio fallback (entrypoint.sh)

`entrypoint.sh` runs the following logic at startup:

| Condition | Action |
|---|---|
| `/proc/asound/card0` present (Jetson, native Linux) | Leave audio untouched — ALSA hardware available |
| WSLg socket at `/tmp/pulse/native` and auth succeeds | Use WSLg PulseAudio — Windows mic available to `stt_node` |
| WSLg socket present but auth fails (UID mismatch) | Start local PulseAudio daemon with null source so `stt_node` doesn't crash; use browser route for real audio |
| No socket, no ALSA | Start local PulseAudio daemon with null source; use browser route |

The local PulseAudio daemon provides a dummy input device so `stt_node` opens successfully. Without real audio reaching it via Route 1, `stt_node` will simply produce no transcriptions; `mic_bridge_node` (Route 2) handles the actual input.

### Verify inside the container

```bash
docker exec -it <container_name> python3 -c \
  "import sounddevice as sd; print(sd.query_devices())"
# Should always show at least "NullMicrophone" (local PA) or a real device (WSLg / ALSA)
```

---

## GPU / CUDA

### Jetson NX 16 GB

`docker-compose.jetson.yml` includes the NVIDIA GPU reservation block and sets `PIPER_USE_CUDA=true`. The L4T base image ships CUDA 12, cuDNN, and PyTorch with CUDA support — no extra setup.

Prerequisite on the Jetson host:

```bash
sudo apt install nvidia-container-toolkit
```

### Windows 11 with NVIDIA GPU

GPU support for the x86_64 image is opt-in. Uncomment the `deploy.resources` block in `docker-compose.yml` and follow NVIDIA's WSL2 guide to install the container toolkit on the Windows host.

Enables: `STT_DEVICE=cuda` (faster-whisper GPU inference), GPU-accelerated Gazebo rendering.

---

## Build Arguments

Pass with `--build-arg` to customise the image at build time.

| Argument | Default | Description |
|---|---|---|
| `PIPER_VOICE` | `en_US-lessac-medium` | Piper voice model to pre-bake into the image. Use a different model to avoid the first-run download for that voice. |

```bash
# Bake a higher-quality voice into the image
docker-compose build --build-arg PIPER_VOICE=en_US-ryan-high

# Bake a non-English voice
docker-compose build --build-arg PIPER_VOICE=de_DE-thorsten-medium
```

If a user sets `TTS_VOICE` to a voice that is **not** pre-baked, Piper downloads it at first use from Hugging Face (~65–120 MB). Subsequent starts use the cached file.

---

## Common Recipes

```bash
# Fully offline — no internet, no API keys, local STT + Piper TTS + keyword NLU
ROBOT_IP=192.168.x.x \
  STT_PROVIDER=faster_whisper STT_DEVICE=cpu \
  NLU_PROVIDER=keyword \
  docker-compose up

# All cloud — OpenAI for everything
ROBOT_IP=192.168.x.x OPENAI_API_KEY=sk-... \
  TTS_PROVIDER=openai TTS_VOICE=nova \
  STT_PROVIDER=openai NLU_PROVIDER=openai \
  docker-compose up

# Gemini for everything (single key)
ROBOT_IP=192.168.x.x GEMINI_API_KEY=... \
  TTS_PROVIDER=gemini TTS_VOICE=Kore \
  STT_PROVIDER=gemini NLU_PROVIDER=gemini \
  docker-compose up

# OpenAI STT + Claude NLU (best command understanding)
ROBOT_IP=192.168.x.x \
  OPENAI_API_KEY=sk-... ANTHROPIC_API_KEY=sk-ant-... \
  STT_PROVIDER=openai NLU_PROVIDER=claude \
  docker-compose up

# STT-only (transcription, no command routing)
ROBOT_IP=192.168.x.x ENABLE_VOICE_CMD=false \
  docker-compose up

# Disable STT entirely
ROBOT_IP=192.168.x.x ENABLE_STT=false ENABLE_VOICE_CMD=false \
  docker-compose up

# Jetson — CUDA STT, offline Piper TTS, keyword NLU
ROBOT_IP=192.168.x.x \
  STT_PROVIDER=faster_whisper STT_DEVICE=cuda WHISPER_MODEL=small \
  docker-compose -f docker/docker-compose.yml \
                 -f docker/docker-compose.jetson.yml up
```

---

## Troubleshooting

### Container exits immediately / won't start

Check logs: `docker-compose logs go2_ros2`

Common causes:
- `ROBOT_IP` not set and `USE_SIM=false` — set `ROBOT_IP` or `USE_SIM=true`
- Port already in use (5901, 8765, 9991) — stop another container or change the port mapping

### VNC shows black screen

Xvfb or xfce4 failed to start. Re-run and watch for `Xvfb` errors in the logs. Usually resolves on a second `docker-compose up`.

### `sounddevice.PortAudioError: Error querying device -1`

`stt_node` found no audio input device. Since the container now starts a local PulseAudio daemon as a fallback, this error should no longer occur. If it does:

- **Windows (Docker)**: the local PA daemon may have failed to start — check container startup logs for `pulseaudio` errors. Use the browser mic bridge at `http://localhost:8888` instead.
- **Jetson NX**: ensure the USB mic is plugged in _before_ starting the container.

Even when this error appears, `mic_bridge_node` is unaffected — the browser route at `http://localhost:8888` provides audio independently of PortAudio.

### Piper voice not found / download fails

If `PIPER_VOICE_DIR` is correct but the model file is missing at runtime, Piper attempts to download from Hugging Face. If the container has no internet access:

```bash
# Pre-download on the host, then mount the directory
mkdir -p ~/.local/share/piper/voices
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx \
     -O ~/.local/share/piper/voices/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json \
     -O ~/.local/share/piper/voices/en_US-lessac-medium.onnx.json
# Then add to docker-compose.yml under volumes:
#   - ~/.local/share/piper/voices:/root/.local/share/piper/voices:ro
```

Alternatively fall back to espeak: `TTS_PROVIDER=espeak docker-compose up`

### WebRTC connection refused / robot not responding

- Close the Unitree mobile app — only one WebRTC client is allowed at a time
- Confirm the robot and the host are on the same Wi-Fi network
- Check `ROBOT_IP` and `WEBRTC_SERVER_PORT` are correct

### `/go2/quadruped_controller` missing (simulation frozen)

The gait controller crashed during startup. See [simulation.md — Troubleshooting](simulation.md#troubleshooting) for diagnosis steps and how to restart it.
