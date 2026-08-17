# Jetson Hot-Patch Status (Pending Docker Image Rebuild)

**Purpose of this file:** track which fixes are only living in the running
container's writable layer (via `docker cp` hot-patch) versus what's actually
baked into the `go2-ros2-sdk:latest` image on the Jetson. No image rebuild has
happened yet this development cycle — per the agreed workflow, Python-only
changes are hot-patched into the running container instead of rebuilding, and
a single image rebuild happens once everything is fixed and confirmed on
hardware.

**Risk:** hot-patches live in the container's writable layer. A plain
`docker restart <container>` preserves them. `docker compose up
--force-recreate` (or any flow that removes/recreates the container) does
**not** — it reverts to whatever is baked into the image, silently discarding
every patch below. This matters most after a power cycle: if Docker/compose
recreates the container on Jetson boot instead of just restarting it, all
patches are lost until reapplied.

**Current status: the container is now running `STT_PROVIDER=openai_realtime`
+ `MIC_BRIDGE=true`** (switched from `faster_whisper` + `stt_node`, per the
user's request to test Path C). This means **`stt_node` is not currently
running** — `mic_bridge_node` is, along with `tts_node`/`go2_driver_node` as
before. Sections 1-4 plus the new section 6 (robot-mic toggle in
`mic_bridge_node`) are deployed and confirmed present after the switch —
see `C:\...\scratchpad\jetson_full_redeploy.py`, which deploys all of
go2_robot_sdk + speech_processor's pending files (including the new
`audio_vad.py` shared module and `mic_diagnostic_node.py`) in one pass, run
after any `--force-recreate`. To go back to `stt_node`/`faster_whisper`,
recreate again with `STT_PROVIDER=faster_whisper MIC_BRIDGE=false` and
redeploy the same way.
**Deployed ≠ fully behavior-verified** — see the checklist at the bottom for
what's still open per section (STT-via-robot-mic transcription, TTS
playback on this hardware, Path C's actual robot-speaker echo).

Section 5 (`mic_diagnostic_node`, new) is running but **only as a manual
background process**, not through the supervised launch tree — it will NOT
survive a container restart. See section 5 for how to make it permanent.

Container name used throughout: `docker-go2_ros2-1`.

---

## 1. Robot mic gain fix — hot-patched previously, still uncommitted

`go2_robot_sdk/go2_robot_sdk/presentation/go2_driver_node.py` — CycloneDDS
audio bridge (`/audiosender` → Opus decode → resample → `ROBOT_MIC_GAIN`
(default `3.0`) → `/robot_audio`). Idle room-noise floor measured ~470–560
RMS (raw int16, after 3x gain) vs. `stt_node`'s VAD threshold ~1311 raw;
confirmed real speech only reached ~854 RMS with this gain — narrow margin,
**STT-via-robot-mic not yet confirmed end-to-end**. Gain much beyond 3x
risks false-triggering the VAD on room noise.

This file also now carries section 2's changes (new publisher registration,
extra import, extended docstring) — see below. Confirm with `git status`
that it's still showing modified; if clean, it's been committed and this
note is stale.

---

## 2. `/audiohub_player_state` — TTS completion signal + non-blocking TTS (deployed, hardware behavior not yet confirmed)

Implements a real completion signal for `tts_node.py`'s robot-speaker
playback (replacing a blind `time.sleep(duration + 1.0)`) and makes TTS
non-blocking end-to-end, so announcing a robot action and actually
performing it run in parallel rather than the announcement gating anything.
Full design writeup: `docs/connection-modes.md#audio-topics-cyclonedds-mode`
and `docs/architecture.md` (TTS path section).

**Files touched, all uncommitted:**
- `go2_robot_sdk/go2_robot_sdk/domain/entities/robot_data.py` — new `AudioPlayerState` entity
- `go2_robot_sdk/go2_robot_sdk/domain/entities/__init__.py` — export it
- `go2_robot_sdk/go2_robot_sdk/domain/interfaces/robot_data_publisher.py` — new abstract `publish_audio_player_state()`
- `go2_robot_sdk/go2_robot_sdk/infrastructure/ros2/ros2_publisher.py` — implements it, publishes `std_msgs/String` to `audiohub_player_state`
- `go2_robot_sdk/go2_robot_sdk/presentation/go2_driver_node.py` — registers the new publisher (unconditional, not gated by `enable_audio`)
- `go2_robot_sdk/go2_robot_sdk/application/services/robot_data_service.py` — new `elif` branch routing `RTC_TOPIC["AUDIO_HUB_PLAY_STATE"]` (WebRTC data-channel messages only) to the new publisher, passthrough (unparsed) JSON body
- `go2_robot_sdk/go2_robot_sdk/infrastructure/cyclonedds/cyclonedds_adapter.py` — comment-only update (no behavior change) documenting the CycloneDDS-side gap below
- `speech_processor/speech_processor/tts_node.py` — background worker thread + queue (`tts_callback` only enqueues now), subscribes to `/audiohub_player_state`, `_play_on_robot()` waits on a `threading.Event` (real signal, or the same `duration + 1.0`s ceiling as before on timeout) instead of a blind sleep

**Known gap, by design, not a bug:** CycloneDDS mode does **not** populate
`/audiohub_player_state` yet. `CycloneDDSAdapter` never subscribes to the
real `/audiohub/player/state` DDS topic because its message type hasn't
been confirmed against hardware — guessing wrong would repeat the exact
unitree_go-vs-unitree_api type-mismatch bug already fixed once this
project for `/api/sport/request`. **This robot runs CycloneDDS**, so on
this hardware `_play_on_robot()` will keep using the duration-based
timeout fallback (same wait ceiling as before, just non-blocking now) until
someone runs `ros2 topic info -v /audiohub/player/state` on the Jetson to
confirm the type and a matching subscription gets added to
`cyclonedds_adapter.py`. WebRTC mode (not what this robot uses) is fully
wired already.

**What IS verified now:** deployed and loaded cleanly (container restarted
without errors, all marker strings present via `grep`). **Not yet verified:**
an actual TTS request has not been observed playing correctly through this
non-blocking path on this hardware — the worker thread, queue, and event-wait
logic haven't been exercised by a real `/tts` message since deployment.

**Reapply after container recreation** (once first deployed and confirmed —
run from a machine with SSH access to the Jetson):
```bash
for f in \
  go2_robot_sdk/go2_robot_sdk/domain/entities/robot_data.py \
  go2_robot_sdk/go2_robot_sdk/domain/entities/__init__.py \
  go2_robot_sdk/go2_robot_sdk/domain/interfaces/robot_data_publisher.py \
  go2_robot_sdk/go2_robot_sdk/infrastructure/ros2/ros2_publisher.py \
  go2_robot_sdk/go2_robot_sdk/presentation/go2_driver_node.py \
  go2_robot_sdk/go2_robot_sdk/application/services/robot_data_service.py \
  go2_robot_sdk/go2_robot_sdk/infrastructure/cyclonedds/cyclonedds_adapter.py \
; do
  scp "$f" <jetson-host>:/tmp/"$(basename "$f")"
done
scp speech_processor/speech_processor/tts_node.py <jetson-host>:/tmp/tts_node.py

ssh <jetson-host> '
GO2=/ros2_ws/install/go2_robot_sdk/lib/python3.8/site-packages/go2_robot_sdk
SPEECH=/ros2_ws/install/speech_processor/lib/python3.8/site-packages/speech_processor
docker cp /tmp/robot_data.py            docker-go2_ros2-1:$GO2/domain/entities/robot_data.py
docker cp /tmp/__init__.py              docker-go2_ros2-1:$GO2/domain/entities/__init__.py
docker cp /tmp/robot_data_publisher.py  docker-go2_ros2-1:$GO2/domain/interfaces/robot_data_publisher.py
docker cp /tmp/ros2_publisher.py        docker-go2_ros2-1:$GO2/infrastructure/ros2/ros2_publisher.py
docker cp /tmp/go2_driver_node.py       docker-go2_ros2-1:$GO2/presentation/go2_driver_node.py
docker cp /tmp/robot_data_service.py    docker-go2_ros2-1:$GO2/application/services/robot_data_service.py
docker cp /tmp/cyclonedds_adapter.py    docker-go2_ros2-1:$GO2/infrastructure/cyclonedds/cyclonedds_adapter.py
docker cp /tmp/tts_node.py              docker-go2_ros2-1:$SPEECH/tts_node.py
docker restart docker-go2_ros2-1
'
```

(The `speech_processor` install path above follows the same
`/ros2_ws/install/<package>/lib/python3.8/site-packages/<package>/...`
pattern as `go2_robot_sdk` — confirmed correct on this Jetson via the full
deploy script.)

---

## 3. Noise-adaptive VAD + high-pass filter (deployed; user confirmed audible speech, fan noise masking it)

`speech_processor/speech_processor/stt_node.py` — replaces the fixed
`vad_threshold=0.04` energy VAD with a threshold that tracks
`vad_noise_multiplier` (default `1.5`) times a slow EMA of the ambient
noise floor, clamped to `vad_absolute_floor` (default `0.003`). Motivated
directly by section 1's finding: the robot mic's idle noise floor and
speech level are both far below `0.04`, so the old fixed threshold could
never trigger on this source regardless of gain tuning. Also touches
`go2_robot_sdk/launch/robot.launch.py` and `.../launch/simulation.launch.py`
(new `VAD_NOISE_MULTIPLIER` / `VAD_ABSOLUTE_FLOOR` / `VAD_NOISE_EMA_ALPHA`
env vars wired to the new params) — those two are launch-time only, nothing
to hot-patch for them specifically, but they matter if the launch is
re-invoked with different values.

**Update — user confirmed via `mic_diagnostic_node` (section 5):** could
hear themselves in the capture, so the pipeline genuinely works; the
problem is the mic is "a little insensitive" and robot fan noise "masks
what people are saying." That's a spectral separation problem an
amplitude-only VAD structurally can't solve (loud fan and loud speech look
identical to RMS). Added `_BiquadHighpass` — a 2nd-order Butterworth
high-pass, `highpass_cutoff_hz` param (default `150.0`, env
`STT_HIGHPASS_CUTOFF_HZ`), applied in `_feed_pcm` before VAD/STT on both
mic sources. Verified correct with a synthetic sine-sweep test before
deploying (-3dB at 150Hz exactly, near-zero attenuation ≥300Hz — textbook
Butterworth response). **Deployed and confirmed loading without errors**;
subjective effectiveness (does it actually cut through the fan by ear) is
still the user's call to make — see the before/after comparison built from
the existing capture (same clip, filtered vs not) for a first read, but a
fresh capture through `mic_diagnostic_node` reflects the raw signal only
(the filter lives in `stt_node.py`'s internal processing, not on
`/robot_audio` itself) — reasonable outcomes if this isn't enough: retune
`highpass_cutoff_hz`, or accept this may need hardware (external mic on the
Jetson — the fix a couple of other public GO2 deployments landed on for
this exact "fan noise masks speech" complaint, per the web research earlier
this session).

**Not yet reconciled with section 1's gain fix:** section 1's `ROBOT_MIC_GAIN=3.0`
and this section's adaptive VAD were designed from the same measurements
but haven't been tested *together* on hardware. It's possible the gain fix
alone already provides enough headroom for the default multiplier here, or
that they need joint retuning once real captured audio is available (see
the capture script below).

**Tested together once, inconclusive:** a post-deploy capture (15s window,
9.24s of actual audio due to gaps in `/robot_audio`'s publish rate — see
section 5, this is worth re-checking with the diagnostic UI) produced 0
`/speech_text` messages. Peak reached 12.2% of full scale, but the RMS
profile stayed flat (847-979) across the whole capture with no rise/fall
shape — more consistent with sustained ambient/mechanical noise than an
isolated utterance, so this isn't strong evidence the VAD is miscalibrated;
it may just not have seen unambiguous speech yet. Use
`mic_diagnostic_node`'s web UI (section 5) for a tighter-synchronized retest
— it removes the SSH round-trip lag that made timing hard to judge earlier.

**Reapply:**
```bash
scp speech_processor/speech_processor/stt_node.py <jetson-host>:/tmp/stt_node.py
scp go2_robot_sdk/launch/robot.launch.py <jetson-host>:/tmp/robot.launch.py
ssh <jetson-host> '
docker cp /tmp/stt_node.py docker-go2_ros2-1:/ros2_ws/install/speech_processor/lib/python3.8/site-packages/speech_processor/stt_node.py
docker restart docker-go2_ros2-1
'
```
(`robot.launch.py` changes only take effect on the next `ros2 launch` /
container recreate that re-reads the launch file, not a plain restart — not
usually needed for a hot-patch cycle since the container already has the
env-derived params baked into its running launch invocation until recreated.)

**Verification script ready to run:** `jetson_deploy_and_capture.py` in the
scratchpad (see top of this file) deploys this file, restarts the
container, then captures `/robot_audio` to a WAV file and pulls it back —
covers both re-deploying this section and the audio-capture request below
in one pass. It now also deploys section 4 below in the same pass.

---

## 4. Path C robot-speaker echo fix (deployed, hardware behavior not yet confirmed)

**Bug found:** `mic_bridge_node.py`'s Path C (`openai_realtime`/`gemini_live`
— the persistent-WebSocket unified providers) speaks via a model-generated
`audio_response` (already MP3-encoded) that bypassed `tts_node.py` and the
`/tts` text pipeline entirely, going straight to the browser only
(`_on_tts_audio` → `_broadcast_audio_to_browser`). It never reached the
robot speaker — unlike every other TTS path in this SDK (Path A/B via
`/tts` → `tts_node` → `_play_on_robot()`), which all do reach the robot.
Not relevant to `stt_node.py`'s unified path (`gemma_local`), which only
ever produces `text_response`, not `audio_response` — see
`docs/architecture.md`'s Path C diagram (updated) for the distinction.

**Fix:** new `/robot_speaker_audio` topic (`std_msgs/UInt8MultiArray`).
`mic_bridge_node.py` publishes `audio_response` there in addition to its
existing direct browser forward. `tts_node.py` subscribes and plays the
bytes via the same `_play_on_robot()`/`_play_locally()` split as normal
`/tts` requests — through the same worker queue (section 2's non-blocking
design), so a `/tts` announcement and a `/robot_speaker_audio` clip
arriving close together still play in strict order rather than
interleaving. No re-synthesis, no re-broadcast to `/tts_audio` (the browser
already has this exact audio via `mic_bridge_node`'s direct forward — that
would just double it).

**Files touched (uncommitted):**
- `speech_processor/speech_processor/mic_bridge_node.py` — new `_robot_speaker_pub` publisher, one line added to the `audio_response` branch
- `speech_processor/speech_processor/tts_node.py` — new `/robot_speaker_audio` subscription (`_on_robot_speaker_audio`), queue generalized from plain text items to `(kind, payload)` tuples, new `_process_pregenerated_audio()`

**Reapply:**
```bash
scp speech_processor/speech_processor/tts_node.py <jetson-host>:/tmp/tts_node.py
scp speech_processor/speech_processor/mic_bridge_node.py <jetson-host>:/tmp/mic_bridge_node.py
ssh <jetson-host> '
SPEECH=/ros2_ws/install/speech_processor/lib/python3.8/site-packages/speech_processor
docker cp /tmp/tts_node.py         docker-go2_ros2-1:$SPEECH/tts_node.py
docker cp /tmp/mic_bridge_node.py  docker-go2_ros2-1:$SPEECH/mic_bridge_node.py
docker restart docker-go2_ros2-1
'
```

**To actually test this:** requires `STT_PROVIDER=openai_realtime` or
`gemini_live` (Path C only starts via `mic_bridge_node`, not `stt_node`),
speaking a wake-worded command or question at the browser mic UI
(`http://localhost:8888`), and confirming audio plays from BOTH the
browser and the physical robot speaker, not just the browser.

---

## 5. `mic_diagnostic_node` — NEW node, running but NOT persistent yet

Record/Stop web UI (`http://<jetson-ip>:8893`) to capture `/robot_audio`
and play it back in-browser without SSH — see
`docs/docker.md#mic-diagnostic-enable_mic_diagnostictrue`. Confirmed
end-to-end from the laptop: connected over WebSocket (`:8894`), started a
capture, received live level updates, stopped, received `capture_done` +
binary WAV, saved and played back successfully.

**This is a brand-new node, not a file hot-patch** — `ros2 run`/launch
resolve executables via a wrapper script in
`install/speech_processor/lib/speech_processor/`, which `colcon build`
normally generates from `setup.py`'s `entry_points`. Since there was no
rebuild, that wrapper doesn't exist for this node by default. What's
actually running right now:
1. `mic_diagnostic_node.py` copied to
   `.../site-packages/speech_processor/mic_diagnostic_node.py` (normal hot-patch)
2. A **hand-written** wrapper at
   `.../lib/speech_processor/mic_diagnostic_node` (not setuptools-generated —
   a plain `from speech_processor.mic_diagnostic_node import main; main()`,
   simpler than replicating the real wrapper's `importlib.metadata` lookup,
   which would've required also hand-editing the package's installed
   entry_points metadata)
3. Launched **standalone** via `ros2 run speech_processor mic_diagnostic_node
   --ros-args -p http_port:=8893 ...` in the background
   (`docker exec -d ...`), NOT through the container's supervised launch
   tree.

**Consequence: this does not survive a container restart.** `docker restart`
undoes nothing about steps 1-2 (they're in the writable layer like any
other hot-patch), but step 3's background process is gone — the container's
main process is the `ros2 launch` invocation from when it started, and this
node was never part of that tree.

**To make it permanent:** add `ENABLE_MIC_DIAGNOSTIC=true` to the actual
launch env vars next time the container/launch restarts (already wired into
`robot.launch.py` + `docker-compose.yml` this session). Until then, if the
container restarts, relaunch it standalone the same way:
```bash
ssh <jetson-host> "docker exec -d docker-go2_ros2-1 bash -c '. /opt/ros/humble/install/setup.bash && . /ros2_ws/install/setup.bash && nohup ros2 run speech_processor mic_diagnostic_node --ros-args -p http_port:=8893 -p ws_port:=8894 -p audio_topic:=/robot_audio -p sample_rate:=16000 -p max_capture_s:=60.0 > /tmp/mic_diagnostic.log 2>&1 & disown'"
```
(Files themselves need re-copying too if the container was recreated, not
just restarted — see section 1's file-loss risk explanation up top.)

**Reapply files if lost:**
```bash
scp speech_processor/speech_processor/mic_diagnostic_node.py <jetson-host>:/tmp/mic_diagnostic_node.py
ssh <jetson-host> "docker cp /tmp/mic_diagnostic_node.py docker-go2_ros2-1:/ros2_ws/install/speech_processor/lib/python3.8/site-packages/speech_processor/mic_diagnostic_node.py"
```
(The hand-written wrapper at `lib/speech_processor/mic_diagnostic_node`
survives a plain restart same as any other file — only regenerate it if the
container was recreated. Its content is just the 4-line snippet in step 2
above.)

**Once a full image rebuild happens** (deferred all session, see the
checklist below), this becomes a normal `colcon build`-generated executable
and the hand-written wrapper can be deleted.

---

## 6. Shared `audio_vad.py` + robot-mic toggle in `mic_bridge_node` (NEW, deployed, connection confirmed)

**Motivation:** testing Path C (`openai_realtime`) was the point of this
switch, but `mic_bridge_node.py` had its own separate, simpler
fixed-threshold VAD — feeding `/robot_audio` into it unchanged would hit
the exact same "never triggers on the quiet/noisy robot mic" problem
section 3 already fixed once in `stt_node.py`. Rather than duplicate that
fix, extracted `BiquadHighpass` + a new `SegmentingVAD` class into
`speech_processor/speech_processor/audio_vad.py` (NEW file), imported by
both `stt_node.py` (refactored to delegate to it, same behavior as before)
and `mic_bridge_node.py` (one `SegmentingVAD` instance per browser
connection — never shared across connections or sources).

**Feature added:** `mic_bridge_node`'s web UI now has a "Browser mic /
Robot mic" radio toggle, sent to the server as
`{"type":"set_audio_source","source":"browser"|"robot"}`. Server-side:
`_on_robot_audio()` subscribes to `/robot_audio` (note: had to explicitly
use `qos_profile_sensor_data` — the publisher is BEST_EFFORT, and the
default `create_subscription(..., 10)` QoS is RELIABLE, which is
incompatible and would have silently received nothing) and feeds any
connection currently set to `"robot"` through that connection's own VAD
instance. This is the only way to give Path C the robot's mic, since
`openai_realtime`/`gemini_live` only ever run through `mic_bridge_node`,
never `stt_node`.

**Files touched (uncommitted):**
- `speech_processor/speech_processor/audio_vad.py` — NEW, `BiquadHighpass` + `SegmentingVAD`
- `speech_processor/speech_processor/stt_node.py` — refactored to use it (no behavior change)
- `speech_processor/speech_processor/mic_bridge_node.py` — new params, `_on_robot_audio`, `_set_audio_source`, per-connection `_conn_audio` dict, HTML/JS toggle

**Provider-switch gotchas hit and fixed while deploying this (worth knowing for next time):**
1. **`docker compose -f docker/docker-compose.yml -f docker/docker-compose.jetson.yml`
   resolves its project directory to `docker/`** (the first `-f` file's
   directory), not the repo root — so a `.env` file at the repo root
   (`/home/unitree/go2_ros2_sdk/.env`) is silently ignored; `docker compose
   ... config | grep OPENAI_API_KEY` showed `""` even with a correct
   repo-root `.env`. Fixed by explicitly `source`-ing `.env` into the shell
   (`set -a; source .env; set +a`) before invoking `docker compose`, which
   sidesteps the project-directory question entirely — more robust than
   moving/duplicating `.env` into `docker/`.
2. **`GEMMA_MODEL` is overloaded as the realtime model-name override** for
   `openai_realtime`/`gemini_live` (see `_build_backend()` in
   `mic_bridge_node.py`) — leaving it at its `gemma_local`-oriented default
   (`"gemma"`) makes OpenAI reject the session with
   `invalid_request_error.invalid_model`, since `gemma_model or
   "gpt-realtime-2.1"` only falls back when the value is empty/falsy, not
   when it's just wrong. Fixed by explicitly exporting
   `GEMMA_MODEL=gpt-realtime-2.1` when switching to `openai_realtime`.
3. Unrelated, pre-existing, not blocking: `mic_bridge_node`'s TTS-pipe
   warmup (`_warmup_tts_pipe`, the "TTS→STT pipe" test button) always tries
   to download a Supertonic model from HuggingFace regardless of
   `TTS_PROVIDER`, and fails on this Jetson (no general internet access,
   robot-network-only). Logged as an `[ERROR]` on every `mic_bridge_node`
   startup but doesn't affect the core `openai_realtime` voice loop.

**Confirmed:** after the fixes above, `mic_bridge_node` log shows `OpenAI
Realtime (gpt-realtime-2.1) — unified pipeline` with no connection-error
lines (compare to the two earlier failed attempts logged with
`invalid_request_error` for auth and then for the model name). Web UI
reachable from the laptop at `http://192.168.123.18:8888`, radio toggle and
`setAudioSource` JS confirmed present in the served page.

**Follow-up fix (same file, redeployed):** the user hit `getUserMedia`
hanging on "requesting microphone permission" forever with no browser
prompt ever appearing. Root cause: `getUserMedia` requires a secure context
(HTTPS or `localhost`), and the page is accessed as
`http://192.168.123.18:8888` -- a plain-HTTP LAN IP, which browsers treat
as insecure. `navigator.mediaDevices` is `undefined` there, so the old code
threw synchronously before its `.catch()` could run. Also a design bug on
top: `doConnect()` unconditionally called `getUserMedia` even for
Robot-mic-only users who never needed browser mic access at all. Fixed by
decoupling connect from mic permission entirely -- `getUserMedia` is now
called lazily, only when Browser mic is selected AND Start Talking is
pressed, with an explicit `navigator.mediaDevices` guard that shows an
actionable message ("use Robot mic instead, or an SSH tunnel to localhost")
instead of hanging. Also added a `listening` per-connection flag
(`set_listening` control message, tied to Start/Stop Talking) so
`/robot_audio` isn't fed into a connection's VAD before the operator has
actually pressed Start Talking. Verified: JS syntax-checked with `node
--check` on the extracted `<script>` block, Python `.format()` call
round-tripped cleanly, redeployed and confirmed `mic_bridge_node` restarts
without errors, served page contains `initBrowserMic`/`setListening`.
**Second follow-up fix (self-hearing / command cascade bug):** user tried
Robot mic end-to-end and hit a real bug -- asking for one action (e.g.
"stand up") triggered a cascade of unrelated follow-up actions (turn_left,
front_flip, moon_walk, ...) a few seconds apart, matching the log's
`TTS playing` → new unprompted command pattern exactly. Root cause: the
robot's own mic hears its own speaker (tight acoustic coupling, same
chassis, made more sensitive by this session's gain + high-pass work) and
feeds that back into the same live OpenAI Realtime session as if it were a
new user utterance. The browser-mic path always had a guard for this
(`isTtsSpeaking` in the JS, mutes the browser mic while the browser's own
speaker plays) but the robot-mic path never got an equivalent when it was
built.

**Fix:** `tts_node.py` now publishes `/tts_playing` (`std_msgs/Bool`)
bracketing the *actual playback call* (`_play_and_signal()`), not just
synthesis -- True right before `_play_locally()`/`_play_on_robot()`, False
~0.6s after it returns (cooldown for acoustic reverb, matching the
browser's existing 600ms `_ttsUnmuteTimer`). Note this window is
measurably longer than the raw audio duration shown in the UI's
`TTS playing (Xs)` log line, since that log is the *browser's* playback
duration -- the robot-speaker path chunks audio with inter-chunk delays
plus a completion wait, so `/tts_playing` covers the real, longer window.
`mic_bridge_node.py` subscribes and gates `_on_robot_audio()` on
`self._tts_playing or time.monotonic() < self._tts_mute_until` before
feeding any connection's VAD. Browser-mic mode is unaffected (it has its
own separate, already-working guard).

**Files touched (uncommitted):**
- `speech_processor/speech_processor/tts_node.py` — new `/tts_playing` publisher, `_play_and_signal()` wraps both playback call sites
- `speech_processor/speech_processor/mic_bridge_node.py` — new `/tts_playing` subscription (`_on_tts_playing`), mute gate in `_on_robot_audio()`

**Deployed, not yet behavior-confirmed** — syntax-checked, container
restarted cleanly, `/tts_playing` topic confirmed advertised, all markers
present via `grep`. **Not yet confirmed:** that this actually stops the
cascade on hardware — that's the user's next thing to try. If the cascade
still happens (e.g. cooldown too short for this specific chassis's acoustic
coupling), the next lever is `_TTS_MUTE_COOLDOWN_S` in `mic_bridge_node.py`
(currently `0.6`, matching the browser path's constant, not independently
tuned for the robot's tighter coupling).

**Reapply after container recreation:** section 4's files plus `audio_vad.py`,
covering both follow-up fixes above:
```bash
scp speech_processor/speech_processor/audio_vad.py <jetson-host>:/tmp/audio_vad.py
scp speech_processor/speech_processor/stt_node.py <jetson-host>:/tmp/stt_node.py
scp speech_processor/speech_processor/tts_node.py <jetson-host>:/tmp/tts_node.py
scp speech_processor/speech_processor/mic_bridge_node.py <jetson-host>:/tmp/mic_bridge_node.py
ssh <jetson-host> '
SPEECH=/ros2_ws/install/speech_processor/lib/python3.8/site-packages/speech_processor
docker cp /tmp/audio_vad.py       docker-go2_ros2-1:$SPEECH/audio_vad.py
docker cp /tmp/stt_node.py        docker-go2_ros2-1:$SPEECH/stt_node.py
docker cp /tmp/tts_node.py        docker-go2_ros2-1:$SPEECH/tts_node.py
docker cp /tmp/mic_bridge_node.py docker-go2_ros2-1:$SPEECH/mic_bridge_node.py
docker restart docker-go2_ros2-1
'
```

---

## 7. TTS robot-speaker latency (deployed, confirmed on hardware)

User observed the robot-speaker TTS path lagged noticeably behind the
browser path. Root cause: `_play_on_robot()` throttles
`SEND_AUDIO_BLOCK` sends with `time.sleep(0.15)` between each chunk
(`# Prevent flooding`) -- fine per-chunk, but for a base64-encoded WAV at
the old `chunk_size=16384` (16KB), a ~2-4s reply needed 6-11 chunks, i.e.
~1.0-1.75s of pure throttle delay before the robot even finished
*receiving* its audio, on top of whatever it needs to actually start
playing. The browser path just decodes and plays an MP3 directly with no
equivalent throttle, hence the perceptible gap.

**Fix:** doubled `chunk_size` default to `32768` (32KB) in both
`TTSConfig`'s dataclass default and the declared ROS parameter, plus a new
`TTS_CHUNK_SIZE` env var wired into both launch files. Deliberately did
**not** touch the `0.15`s inter-chunk sleep itself -- that changes the send
*rate*, which is the actual "flooding" concern the throttle exists for;
increasing chunk size only reduces how many sends are needed for the same
audio, at the same rate, which is a lower-risk lever.

**Confirmed on hardware:** published a test `/tts` message after
deploying. Log showed `Sending audio to robot: 6 chunks, 3.1s duration` --
computed old-vs-new chunk counts for this clip size are ~9 (old 16KB) vs
~5-6 (new 32KB), matching. Playback completed normally (`Robot playback
completed`, no non-zero response-code warnings), so the larger chunks
didn't cause any observable failure. **Not independently confirmed by
ear** that audio quality is unaffected -- reasonable proxy (clean
completion, no error/retry logging) but not the same as actually listening;
worth a quick sanity check next time you're testing.

**If more speed is wanted:** `chunk_size` can be pushed further (e.g.
65536) via `TTS_CHUNK_SIZE` -- untested at that size, same reasoning should
apply, but confirm playback still completes cleanly before trusting it.

**Files touched (uncommitted):**
- `speech_processor/speech_processor/tts_node.py` — `chunk_size` default 16384 → 32768 (two places: dataclass + declared param)
- `go2_robot_sdk/launch/robot.launch.py` + `.../launch/simulation.launch.py` — new `TTS_CHUNK_SIZE` env var wired to `chunk_size`

**Reapply after container recreation:**
```bash
scp speech_processor/speech_processor/tts_node.py <jetson-host>:/tmp/tts_node.py
scp go2_robot_sdk/launch/robot.launch.py <jetson-host>:/tmp/robot.launch.py
ssh <jetson-host> '
docker cp /tmp/tts_node.py docker-go2_ros2-1:/ros2_ws/install/speech_processor/lib/python3.8/site-packages/speech_processor/tts_node.py
docker cp /tmp/robot.launch.py docker-go2_ros2-1:/ros2_ws/install/go2_robot_sdk/share/go2_robot_sdk/launch/robot.launch.py
docker restart docker-go2_ros2-1
'
```
(The launch-file copy only matters if the container gets a fresh `ros2
launch` invocation -- i.e. after a full recreate. A plain restart re-runs
the launch file too, so it's included above for correctness either way.)

---

## 8. `rviz2` was starving the OpenAI Realtime connection + VAD post-TTS cascade bug (deployed, confirmed on hardware)

**Discovery 1 -- system overload broke STT entirely.** After a robot power
cycle + hot-patch redeploy, `mic_bridge_node` showed `infer 0 ms` on every
single attempt -- `_OpenAIRealtimeBackend.transcribe()`'s early-return guard
(`if not self._ready.is_set(): return ...`) firing instantly, meaning the
persistent WebSocket to OpenAI was never becoming ready. Root cause: system
load average was **9.60** (`uptime`) -- `rviz2` alone was 82.8% CPU (a GUI
visualization tool with zero effect on robot behavior, running to an
unwatched virtual display), on top of the full Nav2 stack and a
`pointcloud_to_laserscan_node` so backed up it was logging "queue full,
discarding message" hundreds of times/sec. Under that load,
`mic_bridge_node`'s asyncio loop couldn't get scheduled promptly enough to
service the WebSocket.

**Fix 1:** `rviz2` launch argument (`go2_robot_sdk/launch/robot.launch.py`
+ `.../launch/simulation.launch.py`) now reads `ENABLE_RVIZ` (default
`true`, unchanged) instead of being hardcoded. **This only takes effect on
a full container recreate** (env vars are fixed at container creation, a
plain restart can't introduce a new one) -- on this running container,
`rviz2` was just killed directly (`pkill -f rviz2`) rather than paying for
a full recreate cycle to test an env var that would've respawned `rviz2`
in the interim anyway. Add `ENABLE_RVIZ=false` to the env-export block next
time this container gets `--force-recreate`d (see section 6's recreate
command as a template) so it doesn't come back. Confirmed: load dropped
9.60 → ~3.8-7.3 after the kill (continued settling over several minutes).

**Discovery 2 -- even after STT started working, one command triggered a
cascade of unrequested ones 9-15s later, repeatedly.** This looked like a
recurrence of section 6's self-hearing bug, but the timing didn't fit: the
`/tts_playing` mute window (playback + 0.6s cooldown) only covers a few
seconds, while the unrequested commands appeared 9-15s after the *previous*
reply finished -- too long for simple acoustic reverb. Actual mechanism:
`SegmentingVAD`'s noise floor only updates on frames judged non-speech
(`speech_processor/speech_processor/audio_vad.py`). If the floor is stale
right when listening resumes after TTS (calibrated to the *pre-TTS*
acoustic environment, which may not match post-TTS room resonance), the
adaptive threshold can end up too permissive, latching the VAD into
`speaking=True` and keeping it there -- silently buffering everything
(ambient noise, room chatter, anything) until a long-enough genuine silence
gap finally occurs, at which point the whole accumulated buffer gets sent
to OpenAI as if the user had said it. This matches the observed pattern
exactly: gaps measured in seconds, not immediate post-reply.

**Fix 2:** `mic_bridge_node.py`'s `_on_tts_playing()` now resets every
robot-mic connection's `SegmentingVAD` instance (fresh noise-floor
bootstrap) on the True→False transition, not just the mute-until
timestamp. Also raised `_TTS_MUTE_COOLDOWN_S` `0.6` → `1.2` -- the original
0.6s was borrowed from the browser path's laptop-speaker-to-laptop-mic
reverb tail, likely too short for the robot's own chassis-mounted
speaker-to-mic coupling.

**Deployed via the same surgical single-node restart as section 6's fix**
(kill + `ros2 run speech_processor mic_bridge_node --ros-args --params-file
<existing file>`, not a full container restart -- avoids respawning
`rviz2` and avoids re-triggering the whole hot-patch-everything dance for
a one-file change). Confirmed: clean OpenAI Realtime reconnect, no errors,
both fix markers (`_TTS_MUTE_COOLDOWN_S = 1.2`, the VAD-reset comment)
present via `grep`.

**Not yet confirmed:** that the cascade is actually gone on a live retest
-- that's the next thing to verify. If it recurs, the next lever is
`speech_processor/audio_vad.py`'s `SegmentingVAD` itself: `_flush()`
doesn't reset `_noise_floor`, so an extended "stuck speaking" state that
hits the `max_utterance_s` force-flush (20s default) would immediately be
able to recur, since the underlying stale-threshold mismatch that caused
it isn't corrected by a flush alone -- a deeper fix there would need the
floor to keep adapting (much more slowly) even during an extended
`speaking=True` run, not just when `speaking=False`.

**Files touched (uncommitted):**
- `go2_robot_sdk/launch/robot.launch.py` + `.../launch/simulation.launch.py` — `rviz2` arg reads `ENABLE_RVIZ`
- `docker/docker-compose.yml` — new `ENABLE_RVIZ` env var
- `docs/docker.md` — documented `ENABLE_RVIZ`
- `speech_processor/speech_processor/mic_bridge_node.py` — VAD reset on TTS-end, cooldown `0.6`→`1.2`

**Reapply after container recreation:**
```bash
scp speech_processor/speech_processor/mic_bridge_node.py <jetson-host>:/tmp/mic_bridge_node.py
scp go2_robot_sdk/launch/robot.launch.py <jetson-host>:/tmp/robot.launch.py
ssh <jetson-host> '
docker cp /tmp/mic_bridge_node.py docker-go2_ros2-1:/ros2_ws/install/speech_processor/lib/python3.8/site-packages/speech_processor/mic_bridge_node.py
docker cp /tmp/robot.launch.py docker-go2_ros2-1:/ros2_ws/install/go2_robot_sdk/share/go2_robot_sdk/launch/robot.launch.py
docker restart docker-go2_ros2-1
'
```
(Remember to add `ENABLE_RVIZ=false` to the env-export block if doing a
`--force-recreate` rather than a plain restart, per Fix 1 above.)

---

## 9. Voice command safety guard (deployed, confirmed on hardware)

Following the section 8 incident (unrequested `front_flip`/`handstand`
etc.), added a default-on restriction: `dance1`, `dance2`, `front_flip`,
`handstand`, `moon_walk` are refused when dispatched via voice, from any
provider (keyword NLU, Gemma unified, `openai_realtime`, `gemini_live`) --
`CommandDispatcher._send_robot_cmd()` checks the action's `api_id` against
`RESTRICTED_API_IDS` (derived from `CMD_MAP`'s new `restricted: True`
flags) before publishing, and `feedback_for()` replies "Sorry, that move is
restricted for safety." instead of the normal confirmation. Checked by
`api_id`, not by command key, so it also covers custom commands from
`config/custom_commands.yaml` that happen to reference the same `api_id`.
Opt-out: `VOICE_ALLOW_DANGEROUS_MOVES=true`. Still reachable directly via
`/webrtc_req`/`/sim_cmd` regardless -- this only gates the voice path.

This set (5 commands) is what was assessed as clearly high fall/damage
risk on a first pass; the user asked for the *rest* of `CMD_MAP` to be
listed so they can decide on any others (e.g. `fast_speed`,
`keep_forward`/`keep_backward`/`keep_turn_left`/`keep_turn_right` --
continuous movement with no built-in timeout, a collision risk rather than
a fall risk, and notably a category `RESTRICTED_API_IDS` doesn't cover at
all since those are tuple actions, not `{"api_id": ...}` dicts). See the
chat transcript for the full command-by-command list presented.

**Files touched (uncommitted):**
- `speech_processor/speech_processor/command_dispatcher.py` — `restricted` flags, `RESTRICTED_API_IDS`, `_is_restricted()`, guard in `_send_robot_cmd()` and `feedback_for()`
- `docker/docker-compose.yml` + `docs/docker.md` — documented `VOICE_ALLOW_DANGEROUS_MOVES`

**Verified:** 107/107 existing unit tests still pass
(`speech_processor/test/test_modul1_voice_commands.py`, run from
`speech_processor/` with `python -m pytest test/ -q`). Deployed via the
same surgical `mic_bridge_node` restart as sections 6 and 8 (shared module,
no other file changes needed for the currently-running provider). Confirmed
on hardware: `RESTRICTED_API_IDS` correctly resolves to `[1022, 1023, 1030,
1301, 1305]` after import inside the container.

**Reapply after container recreation:**
```bash
scp speech_processor/speech_processor/command_dispatcher.py <jetson-host>:/tmp/command_dispatcher.py
ssh <jetson-host> '
docker cp /tmp/command_dispatcher.py docker-go2_ros2-1:/ros2_ws/install/speech_processor/lib/python3.8/site-packages/speech_processor/command_dispatcher.py
docker restart docker-go2_ros2-1
'
```

### 9.1 Follow-up: continuous locomotion (`keep_*`) also restricted

Per the user's decision on the command-by-command list from 9's first pass:
`keep_forward`/`keep_backward`/`keep_turn_left`/`keep_turn_right` are now
also refused by default. These are `("keep", lin, ang)` tuple actions, not
`{"api_id": ...}` dicts, so `RESTRICTED_API_IDS` couldn't cover them --
instead the restriction check was moved to the top of `execute()`, and
`_is_restricted()` now returns `True` for any `("keep", ...)` tuple (in
addition to the existing dict/`api_id` check), gated by the same
`VOICE_ALLOW_DANGEROUS_MOVES` opt-out. `_send_robot_cmd()`'s own
now-redundant check was removed since `execute()` gates it before dispatch;
confirmed `_send_robot_cmd(`/`_send_keep_move(` each still have exactly one
call site (inside `execute()`) so this consolidation doesn't skip either
path. Basic timed locomotion (`forward`/`backward`/`turn_left`/`turn_right`,
`("move", lin, ang)` tuples -- auto-stop after `move_duration`, default 2s)
and `stop_move`/`stop` are untouched.

**Files touched (uncommitted):**
- `speech_processor/speech_processor/command_dispatcher.py` — restriction check centralized at top of `execute()`; `_is_restricted()` also covers `("keep", ...)` tuples; redundant check removed from `_send_robot_cmd()`

**Verified:** 107/107 existing unit tests still pass. Deployed via the same
surgical `mic_bridge_node` restart. Confirmed on hardware via a logic-level
check (constructing a fake dispatcher and calling `_is_restricted()`
directly): `front_flip` dict → restricted, `sit` dict → not restricted,
`("keep", 0.3, 0.0)` → restricted, `("move", 0.3, 0.0)` → not restricted,
`("stop_move",)` → not restricted, `("keep", ...)` with
`VOICE_ALLOW_DANGEROUS_MOVES=true` → not restricted.

**Reapply after container recreation:** same command as 9's reapply block
above (single file, `command_dispatcher.py`).

---

## After power-on: check whether patches survived

```bash
# Compare container Created time to StartedAt -- if Created predates the
# reboot, the container was restarted (patches survive); if Created is
# fresh, it was recreated (patches are gone, reapply everything above).
docker inspect docker-go2_ros2-1 --format '{{.Created}} / started {{.State.StartedAt}}'

# Direct content checks -- all should print a nonzero count if present:
GO2=/ros2_ws/install/go2_robot_sdk/lib/python3.8/site-packages/go2_robot_sdk
SPEECH=/ros2_ws/install/speech_processor/lib/python3.8/site-packages/speech_processor
docker exec docker-go2_ros2-1 grep -c ROBOT_MIC_GAIN      $GO2/presentation/go2_driver_node.py
docker exec docker-go2_ros2-1 grep -c audio_player_state  $GO2/presentation/go2_driver_node.py
docker exec docker-go2_ros2-1 grep -c AudioPlayerState    $GO2/domain/entities/robot_data.py
docker exec docker-go2_ros2-1 grep -c _tts_worker_loop    $SPEECH/tts_node.py
docker exec docker-go2_ros2-1 grep -c vad_noise_multiplier $SPEECH/stt_node.py
docker exec docker-go2_ros2-1 grep -c robot_speaker_audio  $SPEECH/tts_node.py
docker exec docker-go2_ros2-1 grep -c _robot_speaker_pub   $SPEECH/mic_bridge_node.py
docker exec docker-go2_ros2-1 test -f $SPEECH/mic_diagnostic_node.py && echo "mic_diagnostic_node.py present"
docker exec docker-go2_ros2-1 ros2 node list 2>&1 | grep mic_diagnostic || echo "mic_diagnostic_node NOT running (expected after any restart -- see section 5)"
```

## Still open

1. STT-via-robot-mic transcription still unconfirmed end-to-end — use
   `mic_diagnostic_node`'s web UI (section 5) for a tighter-synchronized
   capture/listen loop than the SSH-script approach, then check
   `/speech_text` and `stt_node`'s log during a deliberate, unambiguous
   utterance.
2. TTS non-blocking worker (section 2) hasn't played an actual `/tts`
   request on this hardware since deployment — trigger one (e.g. a voice
   command's canned feedback, or `ros2 topic pub /tts std_msgs/String
   "{data: 'test'}" --once`) and confirm robot-speaker audio still works.
3. Path C robot-speaker echo (section 4) needs an actual
   `openai_realtime`/`gemini_live` session to confirm audio reaches the
   robot speaker, not just the browser.
4. Optionally: run `ros2 topic info -v /audiohub/player/state` on the
   Jetson, add the matching `CycloneDDSAdapter` subscription once the type
   is known, so this robot gets the real TTS completion signal instead of
   the timing fallback.
5. Make `mic_diagnostic_node` permanent — add `ENABLE_MIC_DIAGNOSTIC=true`
   to the launch env vars next restart (section 5).

## Once everything above is confirmed

6. Commit everything (follow this session's pattern of committing only
   after hardware confirmation).
7. Do the full `docker compose build` / image rebuild that's been deferred
   all session, so hot-patches (and the hand-written `mic_diagnostic_node`
   wrapper) stop being necessary.
8. Delete this file — it only describes a transitional state.
