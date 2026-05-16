# Connection Modes

## Overview

The SDK supports two connection modes, selected via `CONN_TYPE`:

| Mode | Transport | Typical deployment | Robot variant |
|---|---|---|---|
| `webrtc` | Wi-Fi (WebRTC / aiortc) | External PC on the same Wi-Fi as the robot | AIR, PRO, EDU |
| `cyclonedds` | Ethernet (native ROS2 DDS) | Onboard Jetson (EDU) or wired PC | EDU (Ethernet port); some PRO |

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
4. The `WebRTCAdapter` dispatches all incoming messages to `RobotDataService`.

**Multi-robot WebRTC:**
```bash
export ROBOT_IP="192.168.1.100,192.168.1.101"
export CONN_TYPE="webrtc"
ros2 launch go2_robot_sdk robot.launch.py
```
One `Go2Connection` is created per IP. Topics become `/robot0/...`, `/robot1/...`.

---

## CycloneDDS Mode (`CONN_TYPE=cyclonedds`)

**Ethernet / onboard deployment.** When the GO2 EDU is connected via Ethernet (or the SDK runs onboard the built-in Jetson), the robot exposes its sensor data as native ROS2 topics over DDS. The SDK subscribes to those topics directly — no WebRTC connection is made.

```bash
export CONN_TYPE="cyclonedds"
# ROBOT_IP is not used in CycloneDDS mode
ros2 launch go2_robot_sdk robot.launch.py
```

**Topics the SDK subscribes to in CycloneDDS mode:**

| Topic | Type | Notes |
|---|---|---|
| `/lowstate` | `go2_interfaces/LowState` | Joint states, IMU, foot forces |
| `/utlidar/robot_pose` | `geometry_msgs/PoseStamped` | Robot odometry |
| `/utlidar/cloud` | `sensor_msgs/PointCloud2` | LiDAR point cloud |

**Implementation status:** The subscriptions are wired up in `Go2DriverNode._setup_subscribers()`, but all three callbacks (`_on_cyclonedds_low_state`, `_on_cyclonedds_pose`, `_on_cyclonedds_lidar`) are currently **empty stubs**. CycloneDDS mode connects the topics but does not yet publish anything to the SDK's output topics. It is a work-in-progress.

The `cyclonedx_config.rviz` layout is loaded automatically when `CONN_TYPE=cyclonedds`. No manual override is needed.

---

## GO2 Variants and Relevant Differences

| Variant | Ethernet port | Onboard compute | CycloneDDS viable | Foot force sensors |
|---|---|---|---|---|
| **AIR** | No | No | No | No |
| **PRO** | Some models | No | If Ethernet available | Some models |
| **EDU** | Yes | Jetson Orin NX (secondary board) | Yes — primary intended use | Yes |

---

## GO2 EDU — Onboard Jetson Deployment

The GO2 EDU includes a secondary **Jetson Orin NX** development board connected to the robot's internal network. Running the SDK onboard (rather than on an external PC) avoids Wi-Fi latency and the WebRTC overhead entirely.

**Intended approach (CycloneDDS):**

Because the Jetson shares the same internal DDS domain as the robot's main compute unit, `CONN_TYPE=cyclonedds` is the natural choice — the SDK subscribes to topics the robot already publishes natively.

**Practical state today:** Since the CycloneDDS callbacks are stubs, running onboard the Jetson with `CONN_TYPE=cyclonedds` won't produce any output topics. Two workarounds:

1. **Use WebRTC onboard over the internal network** — if the Jetson can reach the robot's WebRTC server (`port 9991`), `CONN_TYPE=webrtc` with the robot's internal IP works today.
2. **Implement the CycloneDDS callbacks** — see [extending.md](extending.md) for the four-file pattern. The subscriptions are already declared; only the three callbacks in `go2_driver_node.py` and the corresponding `RobotDataService` routing need implementing.

**Build considerations for Jetson:**
- The Jetson Orin NX runs Ubuntu 22.04 (JetPack 6.x) which supports ROS2 Humble or Jazzy — same as the SDK's CI targets.
- `open3d` is not in `requirements.txt` anymore; remaining deps (`torch`, `ultralytics`) have Jetson-native wheels. Use `pip install torch torchvision --index-url <jetson-wheel-url>` if the default PyPI wheels don't match the ARM architecture.
- The `go2_sim` / Gazebo packages are not needed on the Jetson — build only the packages you need:
  ```bash
  colcon build --packages-select go2_interfaces go2_robot_sdk lidar_processor
  ```
