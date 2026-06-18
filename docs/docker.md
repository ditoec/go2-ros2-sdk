# Docker Compose Guide

The SDK ships three Compose files that layer on top of each other. The base file
(`docker-compose.yml`) is always required. Override files are stacked with `-f` to
add platform-specific behaviour.

| File | Purpose |
|---|---|
| `docker/docker-compose.yml` | Base — always required |
| `docker/docker-compose.jetson.yml` | Jetson NX 16 GB: ARM64+CUDA image, GPU reservation, `MIC_BRIDGE=false`. Gemma model selected with `GEMMA_SIZE=12b` (default, Q5_K_M ~9.5 GB) or `GEMMA_SIZE=e4b` (Q5_K_M ~5.5 GB, faster). |
| `docker/docker-compose.windows-gpu.yml` | Windows 11 + 8 GB GPU: lighter image (no `torch`/`ultralytics`), GPU passthrough. Supports two modes selected by `COMPOSE_PROFILES`: **no profile** = Path A (faster_whisper + keyword, no sidecar); **`gemma`** = Path B (llama.cpp sidecar, Gemma unified pipeline). Model size selected with `GEMMA_SIZE=12b` (default) or `GEMMA_SIZE=e4b`. |

---

## Quick Start

```bash
# Build once (applies to all platforms and modes)
docker-compose build

# Windows 11 — hardware mode
ROBOT_IP=192.168.x.x docker-compose up

# Windows 11 — simulation
USE_SIM=true docker-compose up

# Windows 11 + 8 GB GPU — Path A (faster_whisper GPU + keyword NLU, no llama.cpp)
ROBOT_IP=192.168.x.x ENABLE_STT=true \
  docker-compose -f docker/docker-compose.yml \
                 -f docker/docker-compose.windows-gpu.yml up

# Windows 11 + 8 GB GPU — Path B (Gemma unified pipeline, llama.cpp sidecar)
# GEMMA_SIZE=12b (default): gemma-4-12b-it-Q4_0 + 175 MB mmproj, ~7 GB first-run download
# GEMMA_SIZE=e4b:           gemma-4-E4B-it-Q4_K_M + 992 MB mmproj, ~6 GB first-run download
ROBOT_IP=192.168.x.x ENABLE_STT=true COMPOSE_PROFILES=gemma \
  docker-compose -f docker/docker-compose.yml \
                 -f docker/docker-compose.windows-gpu.yml up
# E4B variant (faster, more VRAM headroom):
ROBOT_IP=192.168.x.x ENABLE_STT=true GEMMA_SIZE=e4b COMPOSE_PROFILES=gemma \
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

  Windows 11 + Docker Desktop + WSL2 + 8 GB NVIDIA GPU
    Path A — faster_whisper GPU + keyword NLU (no llama.cpp, instant start):
      Hardware:  ROBOT_IP=x.x.x.x ENABLE_STT=true \
                   docker-compose -f docker/docker-compose.yml \
                                  -f docker/docker-compose.windows-gpu.yml up
      Sim:       USE_SIM=true ENABLE_STT=true \
                   docker-compose -f docker/docker-compose.yml \
                                  -f docker/docker-compose.windows-gpu.yml up

    Path B — Gemma unified pipeline (llama.cpp sidecar):
      GEMMA_SIZE=12b (default, ~7 GB first-run): higher quality, ~12-15 t/s
      GEMMA_SIZE=e4b            (~6 GB first-run): faster (~30+ t/s), more VRAM headroom
      Hardware:  ROBOT_IP=x.x.x.x ENABLE_STT=true [GEMMA_SIZE=e4b] COMPOSE_PROFILES=gemma \
                   docker-compose -f docker/docker-compose.yml \
                                  -f docker/docker-compose.windows-gpu.yml up
      Sim:       USE_SIM=true ENABLE_STT=true [GEMMA_SIZE=e4b] COMPOSE_PROFILES=gemma \
                   docker-compose -f docker/docker-compose.yml \
                                  -f docker/docker-compose.windows-gpu.yml up

    └─ Microphone: open http://localhost:8888 in your browser
    └─ Prerequisites: NVIDIA driver ≥ 570 + nvidia-container-toolkit for WSL2 (see GPU section below)

  Jetson NX 16 GB (JetPack 6)
    Path A — faster_whisper CUDA + keyword NLU (no llama.cpp):
      Hardware: ROBOT_IP=x.x.x.x docker-compose \
                  -f docker/docker-compose.yml \
                  -f docker/docker-compose.jetson.yml up
      Sim:      USE_SIM=true docker-compose \
                  -f docker/docker-compose.yml \
                  -f docker/docker-compose.jetson.yml up

    Path B — Gemma unified pipeline (llama.cpp sidecar):
      GEMMA_SIZE=12b (default): Q5_K_M ~9.5 GB, ~8-10 t/s, ~12.6 GB system total
      GEMMA_SIZE=e4b:           Q5_K_M ~5.5 GB, ~15-20 t/s, ~9.0 GB system total
      Hardware: ROBOT_IP=x.x.x.x [GEMMA_SIZE=e4b] COMPOSE_PROFILES=gemma docker-compose \
                  -f docker/docker-compose.yml \
                  -f docker/docker-compose.jetson.yml up

    └─ Microphone: physical USB mic via /dev/snd (stt_node, default)
    └─ Path C: add MIC_BRIDGE=true and STT_PROVIDER=openai_realtime/gemini_live
```

---

## Dockerfiles

| Dockerfile | Base image | Architecture | Used by |
|---|---|---|---|
| `docker/Dockerfile` | `ros:jazzy-ros-base` | x86_64 | Windows 11 (Docker Desktop + WSL2) |
| `docker/Dockerfile.jetson` | `dustynv/ros:jazzy-ros-base-l4t-r36.4.0` | ARM64 + CUDA 12 | Jetson NX 16 GB (JetPack 6) |
| `docker/Dockerfile.windows-gpu` | `ros:jazzy-ros-base` | x86_64 | Windows 11 + 8 GB GPU (Gemma unified pipeline) — `docker-compose.windows-gpu.yml` |
| `docker/Dockerfile.llama-cpp-jetson` | `nvidia/cuda:12.2.2-cudnn8-devel-ubuntu22.04` | ARM64 + CUDA | llama.cpp sidecar built from source for Jetson (SM 87) |

All images include Gazebo Harmonic, VNC, Supertonic TTS (model pre-baked ~305 MB), and all ROS2 packages — no runtime downloads on first start. `Dockerfile.windows-gpu` omits `torch` and `ultralytics` (saves ~3 GB); GPU inference runs in the llama.cpp sidecar container instead.

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
| `ROBOT_IP` | _(empty)_ | IP or comma-separated list | Robot IP for WebRTC mode. Not used in CycloneDDS mode. |
| `CONN_TYPE` | `webrtc` | `webrtc` / `cyclonedds` | `webrtc` → Wi-Fi via aiortc (close the Unitree app first). `cyclonedds` → Ethernet / onboard Jetson (fully implemented). |
| `WEBRTC_SERVER_PORT` | `9991` | port number | WebRTC signalling port (WebRTC mode only). |
| `ROBOT_TOKEN` | _(empty)_ | token string | API token required by some firmware versions (WebRTC mode only). |

### CycloneDDS

Only active when `CONN_TYPE=cyclonedds`. The inline XML URI is built automatically from `CYCLONEDDS_IFACE` — no file editing needed.

| Variable | Default | Description |
|---|---|---|
| `CYCLONEDDS_IFACE` | `eth0` | Ethernet interface connected to the robot. Common values: `eth0`, `enp2s0`, `eno1`. Use `lo` for loopback testing. |
| `RMW_IMPLEMENTATION` | `rmw_cyclonedds_cpp` | ROS2 middleware. Override only if you need a different RMW. |
| `CYCLONEDDS_URI` | _(inline XML built from `CYCLONEDDS_IFACE`)_ | Full CycloneDDS config. Override only if you need advanced DDS settings (RTPS ports, discovery peers, etc.). |

**Usage:**
```bash
# Default interface (eth0)
CONN_TYPE=cyclonedds docker-compose up

# Specify interface
CONN_TYPE=cyclonedds CYCLONEDDS_IFACE=enp2s0 docker-compose up

# Loopback test (no physical robot)
CONN_TYPE=cyclonedds CYCLONEDDS_IFACE=lo docker-compose up
```

See [docs/connection-modes.md](connection-modes.md) for the full topic list, data-flow diagram, and Jetson onboard deployment guide.

### Map / LiDAR

| Variable | Default | Values | Description |
|---|---|---|---|
| `MAP_SAVE` | `false` | `false` / `true` | Save `.ply` point cloud to disk every 10 s. |
| `MAP_NAME` | `3d_map` | filename prefix | Prefix for saved `.ply` files. |

### Language

| Variable | Default | Values | Description |
|---|---|---|---|
| `VOICE_LANG` | `en` | `en` / `id` | **Master language knob.** Focuses STT, NLU, and TTS on a single language (a strong single-language prior is what keeps transcription accurate). The robot command output always stays English (the movement API only understands English `CMD_MAP` keys). |

The pipeline runs in **one** language at a time. Pick it once with `VOICE_LANG`; every stage
(speech-to-text, command parsing, and the spoken reply) follows it. Example:

```bash
VOICE_LANG=id ROBOT_IP=<IP> ENABLE_STT=true docker-compose up   # Indonesian
docker-compose up                                               # English (default)
```

### TTS — Text-to-Speech

TTS starts automatically with every launch. No `ENABLE_TTS` flag exists.

| Variable | Default | Values | Description |
|---|---|---|---|
| `TTS_PROVIDER` | `supertonic` | `supertonic` / `openai` / `elevenlabs` / `gemini` | Synthesis backend. `supertonic` is offline; cloud providers need an API key. |
| `TTS_VOICE` | `F1` | see below | Voice identifier. Meaning depends on provider. |
| `SUPERTONIC_LANG` | _(follows `VOICE_LANG`)_ | ISO 639-1 code | TTS-only override of the synthesis language. Leave unset to follow `VOICE_LANG`; set to any of Supertonic's 31 codes (e.g. `de`, `ja`) for TTS in a different language than STT/NLU. |
| `SUPERTONIC_STEPS` | `8` | `5`–`12` | Flow-matching quality steps. Higher = better quality, slower synthesis. |
| `OPENAI_API_KEY` | _(empty)_ | `sk-…` | Required when `TTS_PROVIDER=openai`. Also used by STT and NLU. |
| `ELEVENLABS_API_KEY` | _(empty)_ | API key | Required when `TTS_PROVIDER=elevenlabs`. |
| `GEMINI_API_KEY` | _(empty)_ | API key | Required when `TTS_PROVIDER=gemini`. Also used by STT and NLU. |

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
| `ENABLE_STT` | `true` | `true` / `false` | Start the STT node (`mic_bridge_node` by default, or `stt_node` if `MIC_BRIDGE=false`). |
| `STT_PROVIDER` | `faster_whisper` | see below | STT / unified pipeline backend. |
| `STT_DEVICE` | `cpu` | `cpu` / `cuda` | Device for `faster_whisper`. Base default is `cpu` (no GPU required). `docker-compose.windows-gpu.yml` overrides this to `cuda`. |
| `WHISPER_MODEL` | `base` | `tiny` / `base` / `small` / `medium` | Model size for `faster_whisper`. Larger = better accuracy, more RAM. |
| _STT language_ | — | — | Transcription language follows `VOICE_LANG` (see the Language section). The old `STT_LANGUAGE` variable has been removed. |
| `WAKE_WORD` | `elliot` | any word | Utterances not containing the wake word are discarded before publishing or executing. |
| `VAD_SILENCE_DURATION` | `0.4` | seconds | Silence duration after speech that triggers utterance segmentation. |

**`STT_PROVIDER` values:**

| Value | Pipeline | Speed | Notes |
|---|---|---|---|
| `faster_whisper` | STT only → `voice_cmd_node` | ~50–300 ms | Default. Offline, CTranslate2. |
| `gemma_local` | **Unified**: audio → wake word + command + text (1 llama.cpp call) | ~2–5 s | Requires llama.cpp sidecar (`docker-compose.windows-gpu.yml` or `.jetson.yml`). `voice_cmd_node` not started. |
| `openai_realtime` | **Unified**: audio → wake word + command + audio (gpt-realtime-2 WS) | ~1–2 s | Internet + `OPENAI_API_KEY`. `voice_cmd_node` not started. Audio response bypasses `tts_node`. |
| `gemini_live` | **Unified**: audio → wake word + command + audio (Gemini 2.5 Flash Live WS) | ~1–2 s | Internet + `GEMINI_API_KEY`. `voice_cmd_node` not started. Audio response bypasses `tts_node`. |
| `openai` | STT only (Whisper API) → `voice_cmd_node` | ~1–2 s | Legacy. Internet + `OPENAI_API_KEY`. |
| `gemini` | STT only (Gemini REST) → `voice_cmd_node` | ~1–2 s | Legacy. Internet + `GEMINI_API_KEY`. |
| `vosk` | STT only (local Kaldi) → `voice_cmd_node` | ~50 ms | Offline, lowest RAM, lower accuracy. |

### Voice Commands

| Variable | Default | Values | Description |
|---|---|---|---|
| `ENABLE_VOICE_CMD` | auto | `true` / `false` | Start `voice_cmd_node`. **Auto-disabled** when `STT_PROVIDER` is `gemma_local`, `openai_realtime`, or `gemini_live` (those providers handle NLU+TTS internally). Set to `true` to force-enable. |
| `NLU_PROVIDER` | `keyword` | `keyword` / `openai` / `gemini` / `gemma_local` | Used only when `voice_cmd_node` is running (i.e. `STT_PROVIDER=faster_whisper`). `keyword` → regex, offline. Others → LLM free-form parsing. |
| `VOICE_MOVE_DURATION` | `2.0` | seconds | How long timed movement commands run before auto-stopping. |
| `VOICE_LINEAR_SPEED` | `0.3` | m/s | Forward / backward speed for voice movement commands. |
| `VOICE_ANGULAR_SPEED` | `0.5` | rad/s | Turn speed for voice rotation commands. |

### Gemma / llama.cpp

These variables are used by the `gemma_local` unified provider and Gemma vision node. They are no-ops unless the llama.cpp sidecar is running (`docker-compose.windows-gpu.yml` or `docker-compose.jetson.yml`).

| Variable | Default | Description |
|---|---|---|
| `LLAMA_CPP_HOST` | `http://llama_cpp:8080` | llama.cpp sidecar address (OpenAI-compatible API). |
| `GEMMA_SIZE` | `12b` | Model selection for the llama.cpp sidecar (`gemma` profile only). `12b` → `gemma-4-12b-it-Q4_0.gguf` (higher quality, ~7.7 GB VRAM on 8 GB card). `e4b` → `gemma-4-E4B-it-Q4_K_M.gguf` (faster, ~6.2 GB VRAM). See VRAM table in Path B section above. |
| `GEMMA_MODEL` | `gemma` | Model label sent in the `model` field of `/v1/chat/completions` requests. The sidecar ignores this field — use `GEMMA_SIZE` to select the actual model file. |
| `ENABLE_GEMMA_VISION` | `false` | Start `gemma_vision_node`. Publishes `/scene_description` at `GEMMA_VISION_RATE` Hz. Set `ENABLE_GEMMA_VISION=true` alongside `COMPOSE_PROFILES=gemma` to enable. |
| `GEMMA_VISION_RATE` | `0.5` | Vision inference frequency in Hz (0.5 = one description every 2 s). |

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

### Windows 11 + 8 GB GPU (`docker-compose.windows-gpu.yml`)

This override uses a lighter image (no `torch`/`ultralytics`, ~3 GB lighter) with GPU passthrough. It supports two speech paths selected via `COMPOSE_PROFILES`:

| Component | Path A — no profile (default) | Path B — `COMPOSE_PROFILES=gemma` |
|---|---|---|
| STT | `faster_whisper` GPU (~50 ms) | `gemma_local` unified (1 llama.cpp call) |
| NLU | `keyword` via `voice_cmd_node` | built into unified Gemma pass |
| TTS | `tts_node` (Supertonic) | `tts_node` (Supertonic) |
| Vision | not started | `gemma_vision_node` → `/scene_description` |
| llama.cpp sidecar | **not started** | started, GPU-accelerated |
| `voice_cmd_node` | started | **not started** (auto-disabled) |
| First-run download | none | `12b`: ~7 GB (6.7 GB model + 175 MB mmproj) · `e4b`: ~6 GB (5 GB model + 992 MB mmproj) |

**Prerequisites (one-time):**

```powershell
# NVIDIA driver ≥ 570 on Windows (required for llama.cpp:server-cuda)
# Then verify GPU is visible inside WSL2:
wsl -- nvidia-smi
```

Full setup guide: [docs.nvidia.com/cuda/wsl-user-guide](https://docs.nvidia.com/cuda/wsl-user-guide/index.html)

**Path A — faster_whisper + keyword NLU (instant start, no sidecar):**

```bash
cd docker

# Hardware
ROBOT_IP=192.168.x.x ENABLE_STT=true \
  docker-compose -f docker-compose.yml -f docker-compose.windows-gpu.yml up

# Simulation
USE_SIM=true ENABLE_STT=true \
  docker-compose -f docker-compose.yml -f docker-compose.windows-gpu.yml up
```

**Path B — Gemma unified pipeline (`COMPOSE_PROFILES=gemma`):**

Select the model with `GEMMA_SIZE` (default `12b`). Files are cached in the `gemma_models` named volume — subsequent runs skip the download.

| `GEMMA_SIZE` | Model file | Model VRAM | mmproj | mmproj notes | KV cache (4096 ctx) | Total VRAM |
|---|---|---|---|---|---|---|
| `12b` (default) | `gemma-4-12b-it-Q4_0.gguf` | ~6.7 GB | ~175 MB | vision projector only | ~750 MB (q8_0) | **~7.7 GB** — tight on 8 GB |
| `e4b` | `gemma-4-E4B-it-Q4_K_M.gguf` | ~5.0 GB | ~992 MB | vision **+** audio encoders | ~170 MB (q8_0) | **~6.2 GB** — 1.8 GB headroom |

> **Note on E4B mmproj size:** Gemma 4 E4B bundles a full vision encoder (16L/768H) and audio encoder (12L/1024H) inside the mmproj file, which is why it is nearly 1 GB. The 12B model uses a compact 175 MB projector. Both are required for audio STT — llama.cpp loads the mmproj to process `input_audio` content.

```bash
cd docker

# Hardware — 12B (default)
ROBOT_IP=192.168.x.x ENABLE_STT=true COMPOSE_PROFILES=gemma \
  docker-compose -f docker-compose.yml -f docker-compose.windows-gpu.yml up

# Hardware — E4B (faster, more headroom)
ROBOT_IP=192.168.x.x ENABLE_STT=true GEMMA_SIZE=e4b COMPOSE_PROFILES=gemma \
  docker-compose -f docker-compose.yml -f docker-compose.windows-gpu.yml up

# Simulation — 12B
USE_SIM=true ENABLE_STT=true COMPOSE_PROFILES=gemma \
  docker-compose -f docker-compose.yml -f docker-compose.windows-gpu.yml up

# Simulation — E4B
USE_SIM=true ENABLE_STT=true GEMMA_SIZE=e4b COMPOSE_PROFILES=gemma \
  docker-compose -f docker-compose.yml -f docker-compose.windows-gpu.yml up
```

**Mix and match:** all variables are overridable regardless of profile:

```bash
# faster_whisper STT + Gemma vision (start sidecar, override STT)
ENABLE_STT=true STT_PROVIDER=faster_whisper ENABLE_GEMMA_VISION=true COMPOSE_PROFILES=gemma \
  docker-compose -f docker-compose.yml -f docker-compose.windows-gpu.yml up
```

**Verify llama.cpp (Path B only):**

```bash
curl http://localhost:8080/health
# {"status":"ok"}
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
# Windows 11 + 8 GB GPU — Path A (faster_whisper GPU + keyword NLU, instant start)
ROBOT_IP=192.168.x.x ENABLE_STT=true \
  docker-compose -f docker-compose.yml -f docker-compose.windows-gpu.yml up

# Windows 11 + 8 GB GPU — Path B, 12B (default, higher quality, ~7 GB first-run download)
ROBOT_IP=192.168.x.x ENABLE_STT=true COMPOSE_PROFILES=gemma \
  docker-compose -f docker-compose.yml -f docker-compose.windows-gpu.yml up

# Windows 11 + 8 GB GPU — Path B, E4B (faster ~30+ t/s, more VRAM headroom, ~6 GB first-run)
ROBOT_IP=192.168.x.x ENABLE_STT=true GEMMA_SIZE=e4b COMPOSE_PROFILES=gemma \
  docker-compose -f docker-compose.yml -f docker-compose.windows-gpu.yml up

# Same but simulation (either path)
USE_SIM=true ENABLE_STT=true \
  docker-compose -f docker-compose.yml -f docker-compose.windows-gpu.yml up
USE_SIM=true ENABLE_STT=true COMPOSE_PROFILES=gemma \
  docker-compose -f docker-compose.yml -f docker-compose.windows-gpu.yml up

# OpenAI Realtime unified (audio → wake word + command + spoken reply, single WS session)
# voice_cmd_node and tts_node are bypassed — gpt-realtime-2 speaks the response directly
ROBOT_IP=192.168.x.x OPENAI_API_KEY=sk-... ENABLE_STT=true \
  STT_PROVIDER=openai_realtime \
  docker-compose up

# Gemini Live unified (same one-pass pattern with Gemini 2.5 Flash Live)
ROBOT_IP=192.168.x.x GEMINI_API_KEY=... ENABLE_STT=true \
  STT_PROVIDER=gemini_live TTS_PROVIDER=gemini TTS_VOICE=Kore \
  docker-compose up

# Fully offline — faster_whisper STT + Supertonic TTS + keyword NLU
ROBOT_IP=192.168.x.x \
  STT_PROVIDER=faster_whisper STT_DEVICE=cpu \
  NLU_PROVIDER=keyword \
  docker-compose up

# STT-only (transcription, no command routing)
ROBOT_IP=192.168.x.x ENABLE_VOICE_CMD=false \
  docker-compose up

# Disable STT entirely
ROBOT_IP=192.168.x.x ENABLE_STT=false ENABLE_VOICE_CMD=false \
  docker-compose up

# Jetson — Gemma unified pipeline, 12B (default, ~8-10 t/s, ~12.6 GB system)
ROBOT_IP=192.168.x.x COMPOSE_PROFILES=gemma \
  docker-compose -f docker/docker-compose.yml \
                 -f docker/docker-compose.jetson.yml up

# Jetson — Gemma E4B (faster ~15-20 t/s, ~9.0 GB system, more headroom)
ROBOT_IP=192.168.x.x GEMMA_SIZE=e4b COMPOSE_PROFILES=gemma \
  docker-compose -f docker/docker-compose.yml \
                 -f docker/docker-compose.jetson.yml up
# Note: Jetson uses MIC_BRIDGE=false by default (stt_node with /dev/snd mic).
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
