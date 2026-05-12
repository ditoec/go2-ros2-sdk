# Simulation and Hardware Switching

## Overview

`simulation.launch.py` replaces the hardware driver (`go2_driver_node`) with the Gazebo simulator from the `go2_ros2_sim_py` package. All downstream SDK nodes — Nav2, SLAM, RViz, joystick, yolo_detector — work unchanged because topic bridges relay the simulator's namespaced topics to the SDK's root topics.

## Switching at a Glance

| | Hardware (real robot) | Simulation (Gazebo) |
|---|---|---|
| **Bare metal** | `export ROBOT_IP="..."` → `ros2 launch go2_robot_sdk robot.launch.py` | `ros2 launch go2_robot_sdk simulation.launch.py` |
| **Docker** | `ROBOT_IP=<IP> CONN_TYPE=webrtc docker-compose up` | `USE_SIM=true docker-compose up` |

No code changes are required — only the launch file (or `USE_SIM` env var in Docker) selects the mode. Nav2, SLAM, and all other SDK features behave identically.

---

## Bare Metal Setup (simulation)

Clone the Gazebo sim package alongside this SDK before first use:

```bash
cd <ros2_ws>/src
git clone https://github.com/abutalipovvv/go2_ros2_sim_py
sudo apt install ros-$ROS_DISTRO-topic-tools
cd .. && colcon build
source install/setup.bash
```

Then launch:

```bash
ros2 launch go2_robot_sdk simulation.launch.py
```

Optional arguments (same surface as `robot.launch.py`):

```bash
ros2 launch go2_robot_sdk simulation.launch.py slam:=false nav2:=false rviz2:=true foxglove:=false
```

---

## Docker — Sim/Hardware Switching

The Docker image (`docker/Dockerfile`) is built once and supports both modes via the `USE_SIM` environment variable. The `entrypoint.sh` selects the launch file at container start.

```bash
cd docker

# --- Hardware mode ---
ROBOT_IP=192.168.x.x CONN_TYPE=webrtc docker-compose up

# --- Simulation mode (no robot required) ---
USE_SIM=true docker-compose up

# --- Build once, run either mode ---
docker-compose build
ROBOT_IP=192.168.x.x docker-compose up
# or
USE_SIM=true docker-compose up
```

The image includes:
- **ROS Jazzy** base
- **Gazebo Harmonic** + `ros_gz_*` bridge packages — pre-installed and ready for `USE_SIM=true`
- **VNC server** (TigerVNC + XFCE4) on port `5901` — connect from any VNC client to see RViz/Gazebo

**VNC access:**
```
Host:     localhost:5901
Password: ros2vnc   (override with VNC_PASSWORD=<pass> docker-compose up)
```

**GPU acceleration for Gazebo** — uncomment the `deploy` section in `docker/docker-compose.yml` (requires `nvidia-container-toolkit` on the host).

---

## How `simulation.launch.py` Works

1. **Starts Gazebo** via `go2_ros2_sim_py`. That package's own SLAM and Nav2 are disabled; the SDK's tuned configs are used instead.

2. **Bridges topics** — six `topic_tools/relay` nodes translate between the sim's `/robot1/*` namespace and SDK root topics:

   | Sim topic | SDK topic | Direction |
   |---|---|---|
   | `/robot1/joint_states` | `/joint_states` | sim → SDK |
   | `/robot1/odom` | `/odom` | sim → SDK |
   | `/robot1/imu` | `/imu` | sim → SDK |
   | `/robot1/point_cloud2` | `/point_cloud2` | sim → SDK |
   | `/robot1/go2_camera/color/image` | `/go2_camera/color/image` | sim → SDK |
   | `/cmd_vel_muxed` | `/robot1/cmd_vel` | SDK → sim |

3. **Starts the SDK stack** — `robot_state_publisher`, `pointcloud_to_laserscan`, joystick, RViz, SLAM, Nav2. All nodes use `use_sim_time: True`.

## Nav2 Config Difference

Simulation uses `config/nav2_params_sim.yaml` — identical to `nav2_params.yaml` but with `use_sim_time: True` set for every node. Do not add `use_sim_time` to `nav2_params.yaml` — keep the two files in sync manually.

## Object Detection in Simulation

`yolo_detector_node` subscribes to `/camera/image_raw` but the simulation publishes on `/go2_camera/color/image`. Remap when running standalone:

```bash
ros2 run yolo_detector yolo_detector_node \
    --ros-args -r /camera/image_raw:=/go2_camera/color/image
```
