# Documentation

| File | Contents |
|---|---|
| [testing-capabilities.md](testing-capabilities.md) | Per-capability verification (IMU, LiDAR, camera, teleop, SLAM, Nav2, YOLO, TTS) — hardware vs simulation differences |
| [connection-modes.md](connection-modes.md) | WebRTC vs CycloneDDS, GO2 variant differences, GO2 EDU onboard Jetson deployment, known bugs |
| [architecture.md](architecture.md) | Clean Architecture layers, inbound/outbound data flows, threading model, LiDAR pipeline |
| [packages.md](packages.md) | Every package — source layout, launch files, config files, message types; includes `go2_sim`, `go2_description`, `quadropted_msgs` |
| [topics-and-interfaces.md](topics-and-interfaces.md) | All published/subscribed topics, QoS profiles, velocity pipeline, TF tree, multi-robot namespacing |
| [webrtc-commands.md](webrtc-commands.md) | All `ROBOT_CMD` IDs, `RTC_TOPIC` strings, CLI examples, joystick shortcuts |
| [navigation-and-slam.md](navigation-and-slam.md) | SLAM mapping workflow, Nav2 usage, key parameters, 3D PLY dump |
| [simulation.md](simulation.md) | Sim/hardware switching (bare metal + Docker), host targets (Windows 11 Docker Desktop + WSL2 / Jetson NX 16 GB), microphone setup, Gazebo setup, topic bridges, VNC access |
| [extending.md](extending.md) | Adding nodes, commands, message types, launch args, and tests |

For build and run commands see the top-level [CLAUDE.md](../CLAUDE.md).
