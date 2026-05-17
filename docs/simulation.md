# Simulation and Hardware Switching

## Overview

Simulation is fully self-contained — no external packages need to be cloned. The `go2_sim` package (included in this repo) provides a complete Gazebo Harmonic simulation. `simulation.launch.py` delegates the entire Gazebo layer to `go2_sim` and then starts the same Nav2/SLAM/RViz/joystick stack as the hardware launch.

All downstream nodes receive topics at SDK root-level names (`/imu`, `/scan`, `/odom`, `/joint_states`, etc.) — identical to hardware mode. No namespace translation or topic bridges are needed in `simulation.launch.py`.

## Switching at a Glance

| | Hardware (real robot) | Simulation (Gazebo) |
|---|---|---|
| **Bare metal** | `export ROBOT_IP="..."` → `ros2 launch go2_robot_sdk robot.launch.py` | `ros2 launch go2_robot_sdk simulation.launch.py` |
| **Windows 11** | `ROBOT_IP=<IP> docker-compose up` | `USE_SIM=true docker-compose up` |
| **Jetson NX 16 GB** | `ROBOT_IP=<IP> docker-compose -f docker/docker-compose.yml -f docker/docker-compose.jetson.yml up` | `USE_SIM=true docker-compose -f docker/docker-compose.yml -f docker/docker-compose.jetson.yml up` |

No code changes required — only the launch file (or `USE_SIM` env var in Docker) selects the mode. See [Choosing a Dockerfile](#choosing-a-dockerfile) for the full per-platform commands.

---

## Running (Bare Metal)

```bash
# Build once — includes go2_sim, go2_description, quadropted_msgs
colcon build && source install/setup.bash

# Launch with default world (cafe.world)
ros2 launch go2_robot_sdk simulation.launch.py

# Choose a different Gazebo world
ros2 launch go2_robot_sdk simulation.launch.py world:=go2_empty.sdf

# Disable optional components
ros2 launch go2_robot_sdk simulation.launch.py slam:=false nav2:=false foxglove:=false
```

No external `git clone` or `sudo apt install` step needed beyond the normal `colcon build`.

---

## Docker — Sim/Hardware Switching

Both host targets (Windows 11 and Jetson NX 16 GB) support hardware and simulation modes. `entrypoint.sh` selects the launch file based on `USE_SIM`.

```bash
# Windows 11 — hardware mode
ROBOT_IP=192.168.x.x CONN_TYPE=webrtc docker-compose up

# Windows 11 — simulation mode
USE_SIM=true docker-compose up

# Jetson NX 16 GB — hardware mode
ROBOT_IP=192.168.x.x \
  docker-compose -f docker/docker-compose.yml -f docker/docker-compose.jetson.yml up

# Jetson NX 16 GB — simulation mode
USE_SIM=true \
  docker-compose -f docker/docker-compose.yml -f docker/docker-compose.jetson.yml up
```

Both images include Gazebo Harmonic (`ros-jazzy-ros-gz-*`) and the `go2_sim` package — no runtime downloads.

**VNC access** (RViz / Gazebo GUI) — same on both targets:
```
Host:     localhost:5901
Password: ros2vnc   (override: VNC_PASSWORD=<pass> docker-compose up)
```

**GPU acceleration for Gazebo on Jetson NX** — enabled automatically via the `deploy.resources` block in `docker-compose.jetson.yml` (requires `nvidia-container-toolkit` on the Jetson host).

---

## Choosing a Dockerfile

Two host targets are supported. The correct combination is chosen by which `docker-compose` command you run — Compose does **not** pick automatically.

### Compose file reference

| File | Purpose |
|---|---|
| `docker/docker-compose.yml` | Base — always required |
| `docker/docker-compose.windows.yml` | Windows 11 — adds WSLg PulseAudio socket + `PULSE_SERVER` (microphone) |
| `docker/docker-compose.jetson.yml` | Jetson NX 16 GB — switches to `Dockerfile.jetson` + enables GPU |

| Dockerfile | Base image | Architecture | Used by |
|---|---|---|---|
| `docker/Dockerfile` | `ros:jazzy-ros-base` | x86_64 | Windows 11 + Docker Desktop + WSL2 |
| `docker/Dockerfile.jetson` | `dustynv/ros:jazzy-ros-base-l4t-r36.4.0` | ARM64 + CUDA 12 | Jetson NX 16 GB (JetPack 6) |

### Windows 11 — Docker Desktop + WSL2

```bash
# Without microphone (hardware or sim)
docker-compose up

# With microphone (enables stt_node)
docker-compose \
  -f docker/docker-compose.yml \
  -f docker/docker-compose.windows.yml \
  up
```

`docker-compose.windows.yml` mounts the WSLg PulseAudio socket so `stt_node` can reach the Windows microphone. See the **Microphone in Docker** section below for prerequisites.

### Jetson NX 16 GB

```bash
docker-compose \
  -f docker/docker-compose.yml \
  -f docker/docker-compose.jetson.yml \
  up --build
```

`docker-compose.jetson.yml` changes two things from the base:

| Key | `docker-compose.yml` | `docker-compose.jetson.yml` |
|---|---|---|
| `build.dockerfile` | `docker/Dockerfile` | `docker/Dockerfile.jetson` |
| `deploy.resources` | commented out | NVIDIA GPU reservation (count: 1) |

Everything else — env vars, ports, devices, entrypoint — is inherited unchanged from `docker-compose.yml`. The Jetson image includes Gazebo Harmonic and VNC, so `USE_SIM=true` works identically to the Windows 11 image. PyTorch with CUDA is pre-installed in the L4T base image so `STT_DEVICE=cuda` works out of the box.

### Decision flowchart

```
What hardware are you running on?

  Jetson NX 16 GB →
    Hardware: docker-compose -f docker/docker-compose.yml -f docker/docker-compose.jetson.yml up
    Sim:      USE_SIM=true docker-compose -f docker/docker-compose.yml -f docker/docker-compose.jetson.yml up
    └─ Microphone works via /dev/snd (already mapped in base)
    └─ VNC: localhost:5901

  Windows 11 + Docker Desktop + WSL2 →
    Hardware (no mic): docker-compose up
    Sim (no mic):      USE_SIM=true docker-compose up
    With microphone:   docker-compose -f docker/docker-compose.yml \
                                      -f docker/docker-compose.windows.yml up
    └─ VNC: localhost:5901
```

---

## Microphone in Docker

`stt_node` captures audio via `sounddevice` (PortAudio). The mechanism differs between the two supported host targets.

### Jetson NX 16 GB — works out of the box

`docker-compose.yml` maps the host ALSA devices into the container (`/dev/snd:/dev/snd`). The `docker-compose.jetson.yml` override does not touch the `devices` block, so the mapping is inherited. Plug in a USB mic and run:

```bash
ENABLE_STT=true \
  docker-compose -f docker/docker-compose.yml \
                 -f docker/docker-compose.jetson.yml up
```

### Windows 11 — Docker Desktop + WSL2

WSL2 does **not** expose `/dev/snd` to containers. Two audio routes are available; the container supports both simultaneously.

#### Route 1 — WSLg PulseAudio

`docker-compose.windows.yml` mounts the WSLg PulseAudio socket and auth cookie so `stt_node` can capture from the Windows mic. In practice this often fails due to a UID mismatch: WSLg's PA server runs as uid 1000 but Docker containers run as root (uid 0), causing `pa_context_connect() failed: Access denied`. The container detects this and falls back automatically.

```bash
# Simulation with WSLg mic attempt
USE_SIM=true \
  docker-compose -f docker/docker-compose.yml \
                 -f docker/docker-compose.windows.yml up
```

#### Route 2 — Browser mic bridge (always works)

`mic_bridge_node` starts automatically with `ENABLE_STT=true` (the default). It exposes a page at `http://localhost:8888` that uses the browser's `getUserMedia()` to capture the host mic and stream it into the container over WebSocket.

```bash
# Simulation — browser mic bridge (no extra override needed)
USE_SIM=true docker-compose up
# Then open http://localhost:8888 in your browser and click "Start Microphone"
```

#### Automatic fallback (entrypoint.sh)

At startup `entrypoint.sh` tries WSLg PulseAudio. If auth fails it starts a local PulseAudio daemon with a null source so `stt_node` opens without error. The browser route (Route 2) then provides the actual audio. No manual configuration is required.

### Verify microphone inside the container

```bash
docker exec -it <container_name> python3 -c \
  "import sounddevice as sd; print(sd.query_devices())"
# Should always show at least "NullMicrophone" (local PA) or a real device
```

### Platform summary

| Host | Audio mechanism | Requires |
|---|---|---|
| Jetson NX 16 GB | ALSA `/dev/snd` (mapped in base compose file) | Plug in USB mic before starting |
| Windows 11 + Docker Desktop + WSL2 (Route 1) | WSLg PulseAudio (socket + cookie) | `docker-compose.windows.yml` override; subject to UID auth failure |
| Windows 11 + Docker Desktop + WSL2 (Route 2) | Browser mic bridge — `http://localhost:8888` | Open in host browser; works with any `docker-compose up` command |

---

## How `go2_sim` Works

`go2_sim` is a self-contained simulation package. When `simulation.launch.py` includes `go2_sim.launch.py` it starts 11 nodes/actions in sequence:

| Step | What it does |
|---|---|
| 1 | Sets `GZ_SIM_RESOURCE_PATH` → bundled `models/` dir so `model://` URIs resolve |
| 2 | Starts **Gazebo Harmonic** with the selected world file |
| 3 | Runs `robot_state_publisher` with URDF from `go2_description` xacro |
| 4 | Spawns the GO2 robot entity into Gazebo |
| 5 | Runs `ros_gz_bridge` — clock bridge (YAML) + sensor positional bridge for IMU/scan/camera |
| 6–7 | Spawns `joint_state_broadcaster` + `joint_group_controller` via `ros2_control` (after robot spawns) |
| 8 | `cmd_vel_pub.py` — subscribes directly to `/cmd_vel_out` (twist_mux output), converts Twist → `/go2/robot_velocity` (RobotVelocity) |
| 9 | `robot_controller_gazebo.py` — 60 Hz gait controller (trot/crawl/stand/rest) → joint position commands |
| 10 | `QuadrupedOdometryNode.py` — publishes `/odom` + `odom→base_link` TF at 50 Hz |
| 11 | Five relay nodes: `/go2/imu_plugin/out`→`/imu`; `/go2/scan`→`/scan`; `/go2/color/image_raw`→`/go2_camera/color/image_raw`; `/go2/color/camera_info`→`/go2_camera/color/camera_info`; `/go2/joint_states`→`/joint_states` |
| 12 | `sim_cmd_node.py` — subscribes to `/sim_cmd` and routes to the gait controller; mirrors `/webrtc_req` |

## Topics Provided by `go2_sim`

These match hardware mode exactly — `simulation.launch.py` needs no bridging.

| Topic | Type | Source |
|---|---|---|
| `/imu` | `sensor_msgs/Imu` | Gazebo IMU via `ros_gz_bridge` |
| `/scan` | `sensor_msgs/LaserScan` | Gazebo LiDAR via `ros_gz_bridge` |
| `/go2_camera/color/image_raw` | `sensor_msgs/Image` | Gazebo camera via `ros_gz_bridge` |
| `/joint_states` | `sensor_msgs/JointState` | Relayed from `/go2/joint_states` |
| `/odom` | `nav_msgs/Odometry` | `QuadrupedOdometryNode` |
| `/tf` + `/tf_static` | TF | `robot_state_publisher` + odometry node |
| `/clock` | `rosgraph_msgs/Clock` | Gazebo |

**Note on camera topic**: in simulation the camera lands on `/go2_camera/color/image_raw`; in hardware mode the driver publishes on `/camera/image_raw`. Remap `yolo_detector_node` when running alongside simulation:
```bash
ros2 run yolo_detector yolo_detector_node \
    --ros-args -r /camera/image_raw:=/go2_camera/color/image_raw
```

## Nav2 Config Difference

Simulation uses `config/nav2_params_sim.yaml` — identical to `nav2_params.yaml` but with `use_sim_time: True` set for every node. Do not add `use_sim_time` to `nav2_params.yaml` — keep the two files in sync manually.

## Troubleshooting

### Robot frozen in Gazebo — `/go2/quadruped_controller` missing from node list

**Symptom:** `ros2 node list` does not show `/go2/quadruped_controller` (the gait controller node), yet `/go2/robot_behavior_command` appears in `ros2 service list`. Publishing to `/sim_cmd` produces no movement.

**Cause:** `robot_controller_gazebo.py` crashed during startup — typically a numpy shape error on first `run()` or `change_controller()` call before joint state feedback stabilises. The node exits, leaving only the DDS ghost endpoint for the service that `sim_cmd_node` discovered before the crash. Because `sim_cmd_node` checks `service_is_ready()` against the cached endpoint it may report the service as available yet all calls hang or time out.

**How to confirm:**
```bash
# Should show robot_controller_gazebo in the node list
ros2 node list | grep quadruped

# If only the ghost service endpoint shows:
ros2 service list | grep behavior
ros2 service call /go2/robot_behavior_command go2_interfaces/srv/RobotBehaviorCommand \
    "{command: 'stand', parameter: ''}"
# ↑ This will hang or return error if the node has crashed
```

**Fix — restart the controller node:**
```bash
# Inside the Docker container / same ROS2 environment:
ros2 run go2_sim robot_controller_gazebo --ros-args -p verbose:=false
```

Or restart the full simulation launch — the gait controller now wraps all control-loop exceptions and logs them at 1 Hz instead of crashing, so a second launch should remain stable even if the first iteration throws.

**Persistent crash on every launch:** check `ros2 log` for the error text, which is throttled to one line per second:
```bash
ros2 run go2_sim robot_controller_gazebo --ros-args -p verbose:=true
# Look for "Control loop error: ..." in the output
```

Common root causes:
- Joint state topic not yet publishing when the first control tick fires (transient — resolves on second launch)
- `tf_transformations` package not installed (`pip install transforms3d` or ensure rosdep ran)
- Gazebo paused — confirm `/clock` is publishing: `ros2 topic hz /clock`

### `/sim_cmd` published but robot does not move (service not responding)

`sim_cmd_node` waits up to 5 seconds for the behavior service before giving up:
```
[sim_cmd_node] Behavior service not immediately ready for 'sit' — waiting up to 5 s
[sim_cmd_node] /go2/robot_behavior_command unavailable after 5 s — is robot_controller_gazebo running?
```

If you see the second line, the gait controller is not running — follow the steps above to restart it.
