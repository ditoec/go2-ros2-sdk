# Connection Modes

## Overview

The SDK supports two connection modes, selected via `CONN_TYPE`:

| Mode | Transport | Typical deployment | Robot variant |
|---|---|---|---|
| `webrtc` (default) | Wi-Fi via aiortc | External PC on the same Wi-Fi as the robot | AIR, PRO, EDU |
| `cyclonedds` | Ethernet, native ROS2 DDS | Onboard Jetson (EDU) or wired PC | EDU (Ethernet port); some PRO |

---

## WebRTC Mode (`CONN_TYPE=webrtc`)

**Default mode.** The SDK opens a WebRTC peer connection to the robot over Wi-Fi.

```bash
export ROBOT_IP="192.168.x.x"   # from mobile app: Device → Data → STA Network wlan0
export CONN_TYPE="webrtc"
ros2 launch go2_robot_sdk robot.launch.py
```

**Requirements:**
- Robot and PC on the same Wi-Fi network.
- **Close the Unitree mobile app** before connecting — the robot only allows one WebRTC client at a time.
- `ROBOT_TOKEN` env var is optional; leave unset unless the robot firmware requires it.

**What the SDK does internally:**
1. `Go2Connection` performs HTTP signaling to `http://<ROBOT_IP>:9991`.
2. Uses AES-GCM encryption (`infrastructure/webrtc/crypto/`) for the validation handshake.
3. Opens a WebRTC data channel (`id=0`) for JSON/binary telemetry and a video transceiver for the camera.
4. `WebRTCAdapter` dispatches all incoming messages to `RobotDataService`.

**Multi-robot WebRTC:**
```bash
export ROBOT_IP="192.168.1.100,192.168.1.101"
export CONN_TYPE="webrtc"
ros2 launch go2_robot_sdk robot.launch.py
```
One `Go2Connection` is created per IP. Topics become `/robot0/...`, `/robot1/...`.

---

## CycloneDDS Mode (`CONN_TYPE=cyclonedds`)

**Ethernet / onboard deployment.** When the GO2 EDU is connected via Ethernet (or the SDK runs onboard the built-in Jetson), the robot exposes its sensor data as native ROS2 DDS topics. The SDK subscribes to those topics directly and routes commands back via the sport-mode API — no WebRTC connection is made.

### Topics subscribed by the SDK

| Topic | Type | Frequency | Published to |
|---|---|---|---|
| `/sportmodestate` | `unitree_go/SportModeState` | ~50 Hz | `/go2_states`, `/imu` |
| `/lowstate` | `unitree_go/LowState` | ~500 Hz | `/joint_states`, `/imu` |
| `/utlidar/robot_pose` | `geometry_msgs/PoseStamped` | ~10 Hz | `/odom`, TF `odom→base_link` |
| `/utlidar/cloud` | `sensor_msgs/PointCloud2` | ~10 Hz | `/point_cloud2` |
| `/wirelesscontroller` | `unitree_go/WirelessController` | on press | debug log |

These three use `unitree_go` (Unitree's own official ROS2 interfaces package, vendored from source — see `docker/Dockerfile`), not this repo's `go2_interfaces` package, even though `go2_interfaces` defines identically-shaped messages of the same name. ROS2's rosidl toolchain bakes the package name into each message's DDS wire-level type identifier (`<package>::msg::dds_::<Type>_`), so a `go2_interfaces`-typed subscriber gets a different DDS type than the robot firmware's native `unitree_go`-typed publisher and silently never receives its data, regardless of matching field layout — confirmed live on hardware (`ros2 topic echo` refuses with "contains more than one type" once both endpoints are visible on the same DDS domain).

### Command routing

In CycloneDDS mode, commands from `/cmd_vel_out` and `/webrtc_req` are forwarded to the robot via:

```
/api/sport/request  (unitree_api/Request)   ← velocity, posture, gait, gesture commands
/api/sport/response (unitree_api/Response)  → response codes (logged)
```

These use `unitree_api`, a *third* vendored package — not `unitree_go`, despite `unitree_go` also shipping a simpler `Req`/`Res` pair (`uuid` + `body` string) that seemed like the obvious fit and is DDS-type-valid. Confirmed live: `/api/sport/request` has 10 publishers and exactly 1 subscriber, and every one of them — including the actual command receiver — is typed `unitree_api/msg/Request` (nested `header.identity.{id,api_id}`, `header.lease.id`, `header.policy.{priority,noreply}`, `parameter`). `unitree_go/Req` matches no subscriber on that topic at all.

**BalanceStand precondition for movement:** `StandUp` (api_id 1004) alone leaves the robot in `mode=0`/`gait_type=0` — a static standing lock (Unitree's own docs: "the motor joint remains locked"), not the active balance-control loop `MoveCmd` (api_id 1008) needs ("unlock the joint motor... switch to balanced standing mode"). Confirmed live: velocity commands got `Response.header.status.code=0` (request accepted/routed) on every tick, but the robot never physically moved, and `/sportmodestate.error_code` read `1002` the whole time. `CycloneDDSAdapter.send_stand_up_command()` now sends `BalanceStand` (api_id 1002 — already declared as `_API_BALANCE` in the class but previously unused) immediately after `StandUp`, mirroring `webrtc_adapter.py`'s `send_stand_up_command()`, which has always sent this exact pair — both adapters implement the same `IRobotController` interface and should behave identically regardless of which is active.

`ROBOT_IP` is not used in CycloneDDS mode.

### Audio topics (CycloneDDS mode)

Six audio-related names show up once STT/TTS are in the picture; they split
into three unrelated families that are easy to conflate because of the
similar naming.

**1. TTS out — robot speaker, request/response command channel:**

```
/api/audiohub/request  (unitree_api/Request)   ← TTS audio chunks (tts_node.py)
/api/audiohub/response (unitree_api/Response)  → ack / status code (logged)
```

`tts_node.py`'s `_play_on_robot()` doesn't stream raw audio to a DDS topic —
it converts synthesized speech to WAV, base64-encodes it, splits it into
chunks, and sends `START_AUDIO` (api_id 4001) → repeated `SEND_AUDIO_BLOCK`
(4003, one chunk per JSON `parameter`) → `STOP_AUDIO` (4002), all as
`unitree_api/Request` messages on `/api/audiohub/request`. This is a
*separate* native DDS topic from `/api/sport/request`, not a sub-channel of
it (confirmed live: 3 native publishers / 1 native subscriber, distinct from
sport/request's 10/1) — `CycloneDDSAdapter` routes to it by matching the
WebRTC-style `rt/api/audiohub/request` topic string embedded in the request
against `_TOPIC_ROUTES` (see `cyclonedds_adapter.py`). In WebRTC mode the
same `WebRtcReq` sequence goes out over the WebRTC data channel directly —
same command shape, different transport, same `tts_node.py` code path either
way.

`_play_on_robot()` waits for playback to finish before sending `STOP_AUDIO` —
see the next topic for how, and note this wait runs on `tts_node.py`'s own
background worker thread, not the ROS2 executor, so it never blocks the node
from processing the next `/tts` request while one is still playing.

**2. TTS completion signal — wired for WebRTC, pending hardware verification for CycloneDDS:**

```
/audiohub/player/state   (RTC name: rt/audiohub/player/state)
  → SDK topic: /audiohub_player_state (std_msgs/String, passthrough)
```

The robot broadcasts its own playback state on this topic. WebRTC mode now
consumes it: `RobotDataService.process_webrtc_message()` has an `elif`
branch for `RTC_TOPIC["AUDIO_HUB_PLAY_STATE"]`
(`domain/constants/webrtc_topics.py`) that republishes the raw `data` body
(schema not confirmed against hardware, so passed through as-is rather than
parsed into fields) to the SDK-level `/audiohub_player_state` topic.
`tts_node.py` subscribes to that topic and does a best-effort keyword match
(`idle`/`stop`/`finish`/`complete`/`done`) to release `_play_on_robot()`'s
wait early instead of always running the full `duration + 1.0`s timer.

**CycloneDDS mode does not populate `/audiohub_player_state` yet** —
`CycloneDDSAdapter` never subscribes to the real `/audiohub/player/state` DDS
topic, because its message type hasn't been confirmed against hardware
(`ros2 topic info -v /audiohub/player/state` once the robot is reachable
would confirm it, the same way `/api/sport/request`'s type mismatch was
caught earlier). Guessing the type here risks the exact unitree_go-vs-
unitree_api class of bug already fixed once. Until that subscription is
added, `tts_node.py`'s duration-based timeout is what actually governs
`_play_on_robot()`'s wait in CycloneDDS mode — functionally unchanged from
before, just non-blocking now rather than a blind `time.sleep()`.

**3. STT in — robot mic, raw audio streaming (not request/response):**

```
/audiosender    (unitree_go/AudioData: {time_frame, data})  — robot mic, Opus-encoded
/audioreceiver  (same type, presumed)                        — unused by this SDK
```

`/audiosender` is the CycloneDDS-mode source for `/robot_audio`:
`Go2DriverNode._on_cyclonedds_audio()` subscribes, decodes Opus with a
persistent `av.CodecContext`, resamples to mono s16 @ 16kHz, applies a
software gain stage (`ROBOT_MIC_GAIN` env var, default `3.0` — the raw mic
level measured very low on hardware, verified before any of this code
touches it), and republishes through the exact same
`RobotData(audio_data=AudioData(...))` → `publish_audio_data()` call
`_on_audio_frame()` (WebRTC mode) uses. This topic has **no WebRTC-mode
equivalent name** — WebRTC mode gets mic audio from its own
`MediaStreamTrack` (RTP media, not a named DDS/data-channel topic), decoded
by `_on_audio_frame()` with no gain stage applied. Both converge on
`/robot_audio` so `stt_node` consumes identically either way, but the gain
asymmetry itself is unverified — CycloneDDS was measured and tuned this
session, WebRTC's mic level never has been.

`/audioreceiver` is presumed to be the raw-audio mirror of `/audiosender`
(client → robot speaker) by naming symmetry, but it's never referenced
anywhere in this codebase and hasn't been confirmed against hardware. This
SDK's TTS pipeline uses the audiohub request/response command channel
(family 1 above) instead, not a raw streaming topic — worth knowing
`/audioreceiver` exists so it isn't mistaken for something already wired up.

**Not part of the robot's native audio layer at all:** `/tts_audio`
(`std_msgs/UInt8MultiArray`, MP3 bytes) is this SDK's *own* ROS2 topic —
`tts_node.py` publishes synthesized speech there unconditionally, and
`mic_bridge_node.py` relays it to a browser speaker over its own WebSocket.
It exists purely for the browser-playback dev path (no physical robot
required) and has no relationship to any `/api/audiohub/*`, `/audiosender`,
`/audioreceiver`, or `/audiohub/player/state` topic beyond the coincidental
"audio" naming.

### Docker (recommended)

`CYCLONEDDS_IFACE` is the only variable you need to set — the inline XML URI is constructed automatically:

```bash
# Hardware mode
CONN_TYPE=cyclonedds CYCLONEDDS_IFACE=eth0 ROBOT_IP="" docker-compose up

# With Jetson override
CONN_TYPE=cyclonedds CYCLONEDDS_IFACE=eth0 \
  docker-compose -f docker/docker-compose.yml \
                 -f docker/docker-compose.jetson.yml up
```

Common interface names: `eth0` (most Linux / Jetson), `enp2s0` (PCIe desktop), `eno1` (Dell/HP onboard).

For loopback testing with no robot:
```bash
CONN_TYPE=cyclonedds CYCLONEDDS_IFACE=lo docker-compose up
```

### Bare metal

```bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file://$(pwd)/config/cyclonedds.xml
export CYCLONEDDS_IFACE=eth0        # change to your interface
export CONN_TYPE=cyclonedds
ros2 launch go2_robot_sdk robot.launch.py
```

`config/cyclonedds.xml` reads `$CYCLONEDDS_IFACE` at startup — edit the file directly if you prefer a static interface name.

### How it works internally

```
Robot hardware (DDS domain)
  │
  ├─ /sportmodestate (~50 Hz)  ──► _on_cyclonedds_sport_state()
  │                                  → ROS2Publisher.publish_robot_state()
  │                                    → /go2_states, /imu
  │
  ├─ /lowstate (~500 Hz)       ──► _on_cyclonedds_low_state()
  │                                  → ROS2Publisher.publish_joint_state()
  │                                    → /joint_states
  │                                  → ROS2Publisher.publish_robot_state() (IMU only)
  │                                    → /imu
  │
  ├─ /utlidar/robot_pose       ──► _on_cyclonedds_pose()
  │                                  → ROS2Publisher.publish_odometry()
  │                                    → /odom, TF odom→base_link
  │
  ├─ /utlidar/cloud            ──► _on_cyclonedds_lidar()
  │                                  → /point_cloud2 (re-stamped)
  │
  └─ /wirelesscontroller       ──► _on_cyclonedds_wireless()
                                     → debug log

/cmd_vel_out, /webrtc_req
  │
  └─► CycloneDDSAdapter.send_movement_command() / send_webrtc_request()
        → /api/sport/request (unitree_api/Request, nested header/parameter)
```

---

## GO2 Variants

| Variant | Ethernet port | Onboard compute | CycloneDDS viable | Foot force sensors |
|---|---|---|---|---|
| **AIR** | No | No | No | No |
| **PRO** | Some models | No | If Ethernet available | Some models |
| **EDU** | Yes | Jetson Orin NX | Yes — primary intended use | Yes |

---

## GO2 EDU — Onboard Jetson Deployment

The GO2 EDU includes a secondary **Jetson Orin NX** development board on the robot's internal network. Running the SDK onboard avoids Wi-Fi latency and WebRTC overhead entirely.

**Recommended: use CycloneDDS** — the Jetson shares the same internal DDS domain as the robot's main compute unit, so all sensor topics are available natively with zero configuration.

```bash
# On the Jetson, inside the container:
CONN_TYPE=cyclonedds CYCLONEDDS_IFACE=eth0 \
  docker-compose -f docker/docker-compose.yml \
                 -f docker/docker-compose.jetson.yml up
```

**WebRTC is still an option onboard** if you prefer it — the Jetson can reach the robot's WebRTC server at its internal IP:

```bash
ROBOT_IP=<robot_internal_ip> CONN_TYPE=webrtc docker-compose up
```

**Build only what you need** (skip Gazebo etc.):
```bash
colcon build --packages-select go2_interfaces go2_robot_sdk lidar_processor
```
