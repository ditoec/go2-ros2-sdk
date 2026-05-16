# Simulation and Hardware Switching

## Overview

Simulation is fully self-contained — no external packages need to be cloned. The `go2_sim` package (included in this repo) provides a complete Gazebo Harmonic simulation. `simulation.launch.py` delegates the entire Gazebo layer to `go2_sim` and then starts the same Nav2/SLAM/RViz/joystick stack as the hardware launch.

All downstream nodes receive topics at SDK root-level names (`/imu`, `/scan`, `/odom`, `/joint_states`, etc.) — identical to hardware mode. No namespace translation or topic bridges are needed in `simulation.launch.py`.

## Switching at a Glance

| | Hardware (real robot) | Simulation (Gazebo) |
|---|---|---|
| **Bare metal** | `export ROBOT_IP="..."` → `ros2 launch go2_robot_sdk robot.launch.py` | `ros2 launch go2_robot_sdk simulation.launch.py` |
| **Docker** | `ROBOT_IP=<IP> CONN_TYPE=webrtc docker-compose up` | `USE_SIM=true docker-compose up` |

No code changes required — only the launch file (or `USE_SIM` env var in Docker) selects the mode.

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

The Docker image supports both modes via the `USE_SIM` environment variable. `entrypoint.sh` selects the launch file at container start.

```bash
cd docker

# Hardware mode
ROBOT_IP=192.168.x.x CONN_TYPE=webrtc docker-compose up

# Simulation mode (no robot required)
USE_SIM=true docker-compose up

# Build once, run either mode
docker-compose build
```

The image includes Gazebo Harmonic (`ros-jazzy-ros-gz-*`) and the `go2_sim` package — no runtime downloads.

**VNC access** (RViz / Gazebo GUI):
```
Host:     localhost:5901
Password: ros2vnc   (override: VNC_PASSWORD=<pass> docker-compose up)
```

**GPU acceleration for Gazebo** — uncomment the `deploy` section in `docker/docker-compose.yml` (requires `nvidia-container-toolkit` on the host).

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
