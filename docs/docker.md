# Docker Compose Guide

The SDK ships three Compose files that layer on top of each other. The base file
(`docker-compose.yml`) is always required. Override files are stacked with `-f` to
add platform-specific behaviour.

| File | Purpose |
|---|---|
| `docker/docker-compose.yml` | Base — always required |
| `docker/docker-compose.jetson.yml` | Jetson NX 16 GB: ARM64+CUDA image, GPU reservation, `MIC_BRIDGE=false` |
| `docker/docker-compose.windows-gpu.yml` | Windows 11 + 8 GB GPU: adds Ollama sidecar (Gemma 4 E4B), routes STT/NLU/vision through Gemma, removes heavy ML deps (~4 GB lighter image) |

---

## Quick Start

```bash
# Build once (applies to all platforms and modes)
docker-compose build

# Windows 11 — hardware mode (no microphone)
ROBOT_IP=192.168.x.x docker-compose up

# Windows 11 — hardware mode with microphone (mic_bridge_node, open http://localhost:8888)
ROBOT_IP=192.168.x.x docker-compose up

# Windows 11 — simulation with microphone (same — browser bridge always works)
USE_SIM=true docker-compose up

# Windows 11 + 8 GB GPU — Gemma 4 E4B pipeline (STT + NLU + vision via Ollama)
ROBOT_IP=192.168.x.x ENABLE_STT=true \
  docker-compose -f docker/docker-compose.yml \
                 -f docker/docker-compose.windows-gpu.yml up

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
    Hardware:           ROBOT_IP=x.x.x.x docker-compose up
    Simulation:         USE_SIM=true docker-compose up
    └─ Microphone: open http://localhost:8888 in your browser (mic_bridge_node)

  Windows 11 + Docker Desktop + WSL2 + 8 GB NVIDIA GPU (Gemma pipeline)
    Hardware:  ROBOT_IP=x.x.x.x ENABLE_STT=true \
                 docker-compose -f docker/docker-compose.yml \
                                -f docker/docker-compose.windows-gpu.yml up
    Sim:       USE_SIM=true ENABLE_STT=true \
                 docker-compose -f docker/docker-compose.yml \
                                -f docker/docker-compose.windows-gpu.yml up
    └─ Microphone: open http://localhost:8888 in your browser (mic_bridge_node)
    └─ First run: Ollama pulls gemma4:e4b (~2.5 GB) into a named volume — subsequent runs skip download
    └─ Prerequisites: nvidia-container-toolkit + WSL2 NVIDIA driver (see GPU section below)

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
| `docker/Dockerfile.windows-gpu` | `ros:jazzy-ros-base` | x86_64 | Windows 11 + 8 GB GPU (Gemma pipeline) — `docker-compose.windows-gpu.yml` |

All images include Gazebo Harmonic, VNC, Supertonic TTS (model pre-baked ~305 MB), and all ROS2 packages — no runtime downloads on first start. `Dockerfile.windows-gpu` omits `torch` and `ultralytics` (saves ~3 GB) since Gemma 4 E4B via Ollama replaces YOLO and STT.

---

## Building and Deploying the Jetson Image

`Dockerfile.jetson` targets ARM64. You cannot run it natively on Windows (x86_64). Two paths are supported:

| Path | Build time | When to use |
|---|---|---|
| **Build on Jetson directly** | ~30–60 min | Simple, native ARM64, recommended for first-time setup |
| **Cross-build on Windows → transfer** | ~3–5 h (QEMU) | CI/CD, or when SSH to Jetson isn't available during build |

### Path A — Build directly on the Jetson (recommended)

The Jetson compiles natively at full speed. The only requirement is that the Jetson has internet access (for apt packages and the Supertonic model download during build).

**Step 1 — Prerequisites on the Jetson (one-time)**

```bash
# JetPack 6 must already be installed (CUDA 12, cuDNN)
sudo apt install -y docker.io nvidia-container-toolkit
sudo systemctl restart docker
# Verify GPU is accessible inside containers:
docker run --rm --runtime=nvidia nvcr.io/nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi
```

**Step 2 — Get the source on the Jetson**

```bash
# Option A: clone directly
git clone https://github.com/<your-repo>/go2_ros2_sdk.git
cd go2_ros2_sdk

# Option B: copy from Windows (if repo is not on GitHub yet)
# In Windows PowerShell:
scp -r D:\go2_ros2_sdk jetson_user@<jetson_ip>:~/go2_ros2_sdk
# Then on Jetson:
cd ~/go2_ros2_sdk
```

**Step 3 — Build the image on the Jetson**

```bash
docker-compose \
  -f docker/docker-compose.yml \
  -f docker/docker-compose.jetson.yml \
  build
```

This step takes 30–60 minutes depending on Jetson NX clock speed. The longest sub-steps are:

| Sub-step | ~Time | Notes |
|---|---|---|
| `apt-get install` Gazebo + VNC | ~8–12 min | Downloads ~900 MB |
| `pip install faster-whisper` | ~3–5 min | Pulls `ctranslate2` C++ wheel (~250 MB) |
| `pip install supertonic` | ~1–2 min | Installs flow-matching TTS library |
| Supertonic model download | ~2–4 min | ~305 MB from Hugging Face (pre-baked) |
| `colcon build` | ~10–20 min | Compiles C++ packages natively |

**Step 4 — Run**

```bash
# Hardware mode
ROBOT_IP=192.168.x.x \
  docker-compose -f docker/docker-compose.yml \
                 -f docker/docker-compose.jetson.yml up

# Simulation mode
USE_SIM=true \
  docker-compose -f docker/docker-compose.yml \
                 -f docker/docker-compose.jetson.yml up
```

---

### Path B — Cross-build on Windows, transfer to Jetson

This uses Docker `buildx` with QEMU ARM64 emulation to build the image on Windows and then ship the result to the Jetson. Useful when you want to avoid SSH access during build, or for CI pipelines.

> **Warning**: `colcon build` runs C++ compilation under QEMU emulation, which is ~10–20× slower than native. Expect 3–5 hours total.

**Step 1 — Enable ARM64 emulation on Windows (one-time)**

Open **Docker Desktop** → Settings → Features in development → enable "Use Rosetta for x86/amd64 emulation" (macOS only) or install QEMU via WSL:

```powershell
# In PowerShell (as administrator)
wsl --install          # if WSL2 is not yet installed
docker run --privileged --rm tonistiigi/binfmt --install arm64
```

Verify:

```powershell
docker buildx ls
# Should show: linux/arm64 as a supported platform
```

**Step 2 — Create a buildx builder**

```powershell
docker buildx create --name jetson-builder --driver docker-container --use
docker buildx inspect --bootstrap
# Output should include: linux/arm64/v8
```

**Step 3 — Cross-build the image**

Run from the repo root (`D:\go2_ros2_sdk`):

```powershell
docker buildx build `
  --platform linux/arm64 `
  -f docker/Dockerfile.jetson `
  -t go2-ros2-sdk:jetson `
  --load `
  .
```

`--load` imports the finished image into your local Docker daemon. The build will take 3–5 hours.

**Step 4 — Export the image to a file**

```powershell
docker save go2-ros2-sdk:jetson -o go2-jetson.tar
```

The `.tar` file is typically 6–10 GB.

**Step 5 — Transfer to the Jetson**

```powershell
# SCP (replace jetson_user and jetson_ip)
scp go2-jetson.tar jetson_user@<jetson_ip>:~/
```

Or copy via USB drive / local network share.

**Step 6 — Load and run on the Jetson**

```bash
# On the Jetson
docker load -i ~/go2-jetson.tar

# Copy the compose files (or clone the repo if not already there)
# Then run:
ROBOT_IP=192.168.x.x \
  docker-compose -f docker/docker-compose.yml \
                 -f docker/docker-compose.jetson.yml up
```

---

### Re-deploying after code changes

When source files change but dependencies haven't:

```bash
# Fastest: rebuild only the source layer (Layer 3 in the Dockerfile)
docker-compose \
  -f docker/docker-compose.yml \
  -f docker/docker-compose.jetson.yml \
  build --no-cache go2_ros2

# Then re-deploy via Path A (rebuild on Jetson) or Path B (save → scp → load)
```

Only `colcon build` re-runs (not apt or pip), so this takes ~10–20 minutes.

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
| `TTS_PROVIDER` | `supertonic` | `supertonic` / `openai` / `elevenlabs` / `gemini` | Synthesis backend. `supertonic` is offline; cloud providers need an API key. |
| `TTS_VOICE` | `F1` | see below | Voice identifier. Meaning depends on provider. |
| `SUPERTONIC_LANG` | `en` | ISO 639-1 code | Language for Supertonic synthesis. Supports 31 languages; use `na` for auto-detect. |
| `SUPERTONIC_STEPS` | `8` | `5`–`12` | Flow-matching quality steps. Higher = better quality, slower synthesis. |
| `OPENAI_API_KEY` | _(empty)_ | `sk-…` | Required when `TTS_PROVIDER=openai`. Also used by STT and NLU. |
| `ELEVENLABS_API_KEY` | _(empty)_ | API key | Required when `TTS_PROVIDER=elevenlabs`. |
| `GEMINI_API_KEY` | _(empty)_ | API key | Required when `TTS_PROVIDER=gemini`. Also used by STT and NLU. |
| `ANTHROPIC_API_KEY` | _(empty)_ | `sk-ant-…` | Required when `NLU_PROVIDER=claude`. Not used by TTS or STT. |

**`TTS_VOICE` by provider:**

| Provider | Voice format | Options | Notes |
|---|---|---|---|
| `supertonic` | voice code | `M1`–`M5` (male), `F1`–`F5` (female) | Expression tags: `<laugh>` `<breath>` `<sigh>` inline in text |
| `openai` | voice name | `alloy` / `echo` / `fable` / `onyx` / `nova` / `shimmer` | Cloud API, needs `OPENAI_API_KEY` |
| `elevenlabs` | voice ID | `XrExE9yKIg1WjnnlVkGX` (example) | Get IDs from ElevenLabs dashboard |
| `gemini` | voice name | `Kore` / `Zephyr` / `Puck` / `Charon` / `Fenrir` / `Leda` / `Orus` / `Aoede` / `Callirrhoe` | Cloud API, needs `GEMINI_API_KEY` |

### STT — Speech-to-Text

| Variable | Default | Values | Description |
|---|---|---|---|
| `ENABLE_STT` | `true` | `true` / `false` | Start `stt_node`. Requires a microphone (see [Microphone](#microphone)). |
| `STT_PROVIDER` | `faster_whisper` | `faster_whisper` / `openai` / `vosk` / `gemini` / `gemma_local` | `faster_whisper` → local CTranslate2 (~30 ms GPU / ~300 ms CPU). `openai` / `gemini` → cloud API (~1–2 s). `gemma_local` → Gemma 4 E4B via Ollama sidecar (set by `docker-compose.windows-gpu.yml`). |
| `STT_DEVICE` | `cpu` | `cpu` / `cuda` | `cuda` requires `nvidia-container-toolkit` and GPU reservation. |
| `WHISPER_MODEL` | `base` | `tiny` / `base` / `small` / `medium` | Model size for `faster_whisper`. Larger = better accuracy, more RAM. |
| `STT_LANGUAGE` | `en` | Whisper language code | Target language for transcription. |

### Voice Commands

| Variable | Default | Values | Description |
|---|---|---|---|
| `ENABLE_VOICE_CMD` | `true` | `true` / `false` | Start `voice_cmd_node`. Routes `/speech_text` → robot commands and `/cmd_vel_voice`. |
| `NLU_PROVIDER` | `keyword` | `keyword` / `openai` / `gemini` / `claude` / `gemma_local` | `keyword` → regex matching, instant, fully offline. Others → LLM-based free-form parsing, needs API key or Ollama. `gemma_local` → Gemma 4 E4B via Ollama sidecar, fully offline. |
| `VOICE_MOVE_DURATION` | `2.0` | seconds | How long movement commands run before auto-stopping. |
| `VOICE_LINEAR_SPEED` | `0.3` | m/s | Forward / backward speed for voice movement commands. |
| `VOICE_ANGULAR_SPEED` | `0.5` | rad/s | Turn speed for voice rotation commands. |

### Gemma / Ollama (Windows GPU profile)

These variables have safe defaults and are no-ops unless `docker-compose.windows-gpu.yml` is active.

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_HOST` | `http://ollama:11434` | Ollama sidecar address used by `gemma_local` STT, NLU, and vision providers. |
| `GEMMA_MODEL` | `gemma4:e4b` | Ollama model tag. Override to use a different quantization (e.g. `gemma4:e4b-q8`). |
| `ENABLE_GEMMA_VISION` | `false` | Start `gemma_vision_node`, which publishes scene descriptions to `/scene_description` at `GEMMA_VISION_RATE` Hz. Set automatically to `true` by `docker-compose.windows-gpu.yml`. |
| `GEMMA_VISION_RATE` | `0.5` | Vision inference frequency in Hz. Lower values reduce GPU load; higher values increase scene-description freshness. |

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

Microphone input in Docker is handled by `mic_bridge_node` (started automatically when `ENABLE_STT=true`, the default). No PulseAudio, no `/dev/snd` passthrough, and no override file are required.

```
┌──────────────────────┐  getUserMedia()   ┌──────────────────────────┐
│  Host browser        │ ────────────────► │  mic_bridge_node         │
│  http://localhost:8888│  WS port 8889    │  VAD + STT → /speech_text│
└──────────────────────┘                   └──────────────────────────┘
```

**How to use it:**
1. Start the container with `ENABLE_STT=true` (the default in `docker-compose.yml`)
2. Open `http://localhost:8888` in your Windows browser
3. Click **Connect**, then **Start Talking** and grant microphone permission
4. Speak — transcriptions appear in the browser tab and publish to `/speech_text`

This works on any platform (Windows 11, WSL2, native Linux) because the browser captures the microphone directly at the OS level.

### Jetson NX 16 GB — local mic (stt_node)

On Jetson, `docker-compose.yml` maps `/dev/snd:/dev/snd`. To use a USB mic directly with `stt_node` instead of the browser bridge:

```bash
ENABLE_STT=true MIC_BRIDGE=false \
  docker-compose -f docker/docker-compose.yml \
                 -f docker/docker-compose.jetson.yml up
```

### Verify mic_bridge_node is running

```bash
ros2 node list | grep mic_bridge
# Expected: /mic_bridge_node
```

---

## GPU / CUDA

### Jetson NX 16 GB

`docker-compose.jetson.yml` includes the NVIDIA GPU reservation block. The L4T base image ships CUDA 12, cuDNN, and PyTorch with CUDA support — no extra setup.

Prerequisite on the Jetson host:

```bash
sudo apt install nvidia-container-toolkit
```

### Windows 11 with NVIDIA GPU (standard profile)

GPU support for the standard x86_64 image is opt-in. Uncomment the `deploy.resources` block in `docker-compose.yml` and follow NVIDIA's WSL2 guide to install the container toolkit on the Windows host.

Enables: `STT_DEVICE=cuda` (faster-whisper GPU inference), GPU-accelerated Gazebo rendering.

### Windows 11 + 8 GB GPU — Gemma pipeline (`docker-compose.windows-gpu.yml`)

This override adds a dedicated Ollama sidecar and replaces the standard ML stack with Gemma 4 E4B (4-bit quantized, ~5 GB VRAM):

| Component | Standard profile | Windows GPU profile |
|---|---|---|
| STT | `faster-whisper` (local) or cloud | `gemma_local` → Ollama |
| NLU | `keyword` / cloud | `gemma_local` → Ollama |
| Vision | YOLO (not started) | `gemma_vision_node` → `/scene_description` |
| TTS | Supertonic (unchanged) | Supertonic (unchanged) |
| Image size | ~8 GB | ~5 GB (`torch`/`ultralytics` removed) |

**Prerequisites on the Windows host (one-time):**

```powershell
# 1. Install the NVIDIA container toolkit for WSL2
# Follow: https://docs.nvidia.com/cuda/wsl-user-guide/index.html
# Minimum: NVIDIA driver 555+ on the Windows side; no CUDA toolkit needed in Windows.

# 2. Verify GPU is visible inside WSL2
wsl -- nvidia-smi
# Should print your GPU, CUDA version, and driver version.
```

**First run — model pull:**

On first `docker-compose up`, the `ollama_init` service pulls `gemma4:e4b` (~2.5 GB) into the `ollama_models` named volume. The `go2_ros2` container waits until the pull completes before starting. Subsequent runs skip the download entirely.

**VRAM budget:** Gemma 4 E4B Q4 ≈ 5 GB + Ollama overhead ≈ 1 GB = ~6 GB, leaving ~2 GB free on an 8 GB card.

**Usage:**

```bash
cd docker

# Hardware mode
ROBOT_IP=192.168.x.x ENABLE_STT=true \
  docker-compose -f docker-compose.yml -f docker-compose.windows-gpu.yml up

# Simulation mode
USE_SIM=true ENABLE_STT=true \
  docker-compose -f docker-compose.yml -f docker-compose.windows-gpu.yml up
```

**Verify Ollama is serving the model:**

```bash
curl http://localhost:11434/api/tags
# Should list gemma4:e4b in the "models" array
```

---

## Build Arguments

The current Dockerfile has no build-time arguments. The Supertonic TTS model (~305 MB) is always pre-baked during the image build using the same model for all voices — no build arg is needed. Voice selection (M1–M5, F1–F5) is a runtime parameter via `TTS_VOICE`.

```bash
# Standard build — Supertonic model is pre-baked automatically
docker-compose build
```

---

## Common Recipes

```bash
# Windows 11 + 8 GB GPU — Gemma 4 E4B for everything (offline, no API keys)
# First run downloads gemma4:e4b (~2.5 GB) into the ollama_models Docker volume.
ROBOT_IP=192.168.x.x ENABLE_STT=true \
  docker-compose -f docker-compose.yml -f docker-compose.windows-gpu.yml up

# Windows 11 + 8 GB GPU — simulation mode with Gemma pipeline
USE_SIM=true ENABLE_STT=true \
  docker-compose -f docker-compose.yml -f docker-compose.windows-gpu.yml up

# Fully offline — no internet, no API keys, local STT + Supertonic TTS + keyword NLU
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

# Jetson — CUDA STT, offline Supertonic TTS, keyword NLU
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

### Supertonic model not found / first-run download

The Supertonic model (~305 MB) is pre-baked into the image during `docker-compose build`. If the pre-bake failed (e.g. no internet during build), the model downloads automatically on first container start. To force a clean rebuild with the model:

```bash
docker-compose build --no-cache go2_ros2
```

If the container has no internet access and the model is missing, switch to a cloud provider at runtime: `TTS_PROVIDER=openai OPENAI_API_KEY=sk-... docker-compose up`

### WebRTC connection refused / robot not responding

- Close the Unitree mobile app — only one WebRTC client is allowed at a time
- Confirm the robot and the host are on the same Wi-Fi network
- Check `ROBOT_IP` and `WEBRTC_SERVER_PORT` are correct

### `/go2/quadruped_controller` missing (simulation frozen)

The gait controller crashed during startup. See [simulation.md — Troubleshooting](simulation.md#troubleshooting) for diagnosis steps and how to restart it.
