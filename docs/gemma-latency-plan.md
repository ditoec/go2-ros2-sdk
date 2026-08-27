# Gemma latency remediation plan (Jetson Orin NX)

Status: **not yet executed** — written 2026-08-27, to be run manually.

Voice responses on the onboard Gemma 4 12B were taking 8–14 s end to end,
with utterances being dropped from the queue (`Dropped (12.1s old)`) because
inference could not keep up with speech. This plan records the measured cause
and the fix, in payoff order.

---

## Measured cause

llama.cpp's own timers (`docker logs docker-llama_cpp-1 | grep 'eval time'`):

| Phase | Time | Rate |
|---|---|---|
| Prefill (audio + prompt) | 1.3–3.7 s | 15–165 tok/s |
| **Generation (33–54 tokens)** | **6.0–9.9 s** | **~5.0 tok/s** |

So roughly **75 % of each response is generating ~40 tokens at 5 tok/s.**
This is generation-bound, not prefill-bound — a smaller/faster model helps,
a shorter prompt does not.

The same Q5_K_S model previously benchmarked at **6.6–7.0 tok/s**, so it has
degraded ~30 %. `tegrastats` and `ps` show why:

```
RAM 14276/15389MB   SWAP 1568/7694MB   <-- actively swapping
```

| Process | CPU | Note |
|---|---|---|
| `rviz2` | **95.8 %** | full core rendering a VNC window nobody is watching |
| `face_recognition_node` | **145 %** | 1.5 cores, InsightFace at 2 Hz on CPU |
| `go2_driver_node` | **109 %** | software H.264 decode (no HW accel path) |
| `Xvfb` + `xfwm4` + `xfce4-panel` | ~13 % | VNC desktop |
| `rqt_graph`, `foxglove_bridge` | ~4 % | dev tooling, also log-spamming |

`llama-server` runs `--threads 8` on an 8-core box where ~3.5 cores are
already committed. It is starved of both RAM and CPU — hence 7 → 5 tok/s.

---

## Step 1 — Switch to Gemma E4B (the actual fix)

Frees ~2.3 GB (should stop the swapping outright) **and** E4B has far fewer
active parameters. Expect roughly **2–3x faster generation**: ~9 s responses
become ~3–4 s.

Already fully supported by `docker-compose.jetson.yml` — the `llama_cpp`
entrypoint branches on `GEMMA_SIZE`, and `model_init` downloads the right
GGUF + mmproj. One-time ~5 GB download.

```bash
cd /home/unitree/go2_ros2_sdk/docker

sed -i 's/^GEMMA_SIZE=.*/GEMMA_SIZE=e4b/'          .env
sed -i 's/^GEMMA_MODEL=.*/GEMMA_MODEL=gemma-4-e4b/' .env

# model_init is pulled in automatically by llama_cpp's depends_on and will
# fetch gemma-4-E4B-it-Q5_K_M.gguf + mmproj-e4b-BF16.gguf before it starts.
docker compose -f docker-compose.yml -f docker-compose.jetson.yml \
  up -d --force-recreate llama_cpp
```

Note: E4B's mmproj (~992 MB) bundles a **separate audio encoder** alongside
vision, unlike 12B where audio projects straight into the text embedding
space. Both work for `STT_PROVIDER=gemma_local`; just different mechanisms.

The old 12B GGUF stays in the `docker_gemma_models` volume, so switching back
is only a `.env` edit — no re-download.

## Step 2 — Stop RViz (free, no functional loss)

Reclaims a full core. `ENABLE_RVIZ` is **not currently in `.env`**, so it is
falling through to the compose default of `true`.

```bash
echo 'ENABLE_RVIZ=false' >> /home/unitree/go2_ros2_sdk/docker/.env
```

Takes effect on the next `go2_ros2` recreate (Step 4). To reclaim the core
immediately without waiting:

```bash
docker exec docker-go2_ros2-1 pkill -f 'lib/rviz2/rviz2'
```

## Step 3 — Halve the face-recognition rate

145 % CPU at 2 Hz is the second-largest consumer. At 1 Hz a person standing
in front is still recognized within ~1 s.

```bash
sed -i 's/^FACE_RECOGNITION_RATE=.*/FACE_RECOGNITION_RATE=1.0/' \
  /home/unitree/go2_ros2_sdk/docker/.env
```

## Step 4 — Drop dev tooling and apply Steps 2–3

`foxglove_bridge` also spams `rosidl_typesupport` errors continuously.

```bash
cd /home/unitree/go2_ros2_sdk/docker
sed -i 's/^ENABLE_FOXGLOVE=.*/ENABLE_FOXGLOVE=false/' .env

# Recreate so the container picks up the new env (a plain restart will NOT --
# env vars are baked at create time).
docker compose -f docker-compose.yml -f docker-compose.jetson.yml \
  up -d --force-recreate go2_ros2
```

**Recreating `go2_ros2` also fixes the standing issue** that `ENABLE_FACE=true`
is in `.env` but not in the running container's environment, so the face nodes
currently have to be started by hand after every reboot.

---

## Verification

Re-run the same measurement after each step so the effect is attributable:

```bash
# 1. Generation rate (the number that matters)
docker logs docker-llama_cpp-1 2>&1 | grep 'eval time' | tail -6

# 2. Memory pressure -- SWAP should read 0MB once E4B is in
tegrastats --interval 1000 | head -1

# 3. CPU contention
docker exec docker-go2_ros2-1 ps aux --sort=-%cpu | head -8

# 4. End-to-end, using the WS probe (no physical movement):
docker exec docker-go2_ros2-1 bash -c \
  'source /opt/ros/humble/install/setup.bash && source /ros2_ws/install/setup.bash && \
   python3 /tmp/ws_probe.py "elliot what is your name?"'
```

Target: generation **> 12 tok/s**, `SWAP 0MB`, end-to-end **under 4 s**.

## Rollback

```bash
cd /home/unitree/go2_ros2_sdk/docker
sed -i 's/^GEMMA_SIZE=.*/GEMMA_SIZE=12b/'       .env
sed -i 's/^GEMMA_MODEL=.*/GEMMA_MODEL=gemma-4-12b/' .env
docker compose -f docker-compose.yml -f docker-compose.jetson.yml \
  up -d --force-recreate llama_cpp
```

---

## Optional follow-up — stop echoing the transcript on commands

Not part of the steps above; a behaviour change worth measuring separately.

Both unified tool schemas mark `transcript` as **required**, so every command
makes the model regenerate the full utterance:

```json
{"command":"stand","contains_wake_word":true,"transcript":"elliot stand"}
```

At ~5 tok/s the transcript echo is a large share of the ~40 generated tokens.
It is consumed only by:

- logging,
- `_override_wake_word()` — the wake-word string-match safety net,
- `_override_command()` — the Indonesian deterministic command fallback
  (`VOICE_LANG=id` only).

Making `transcript` optional on the **English** `execute_robot_command` path
(`build_unified_tools()` in `speech_processor/command_dispatcher.py`) should
cut command latency noticeably. Keep it required for `id`, which depends on it,
and keep it on `respond_conversationally` where it costs little.

Measure before committing — if E4B alone gets commands under ~2 s, the added
branch may not be worth the complexity.
