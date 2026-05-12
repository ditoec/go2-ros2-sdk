# Documentation

| File | Contents |
|---|---|
| [architecture.md](architecture.md) | Clean Architecture layers, inbound/outbound data flows, threading model, LiDAR pipeline |
| [packages.md](packages.md) | Every package — source layout, launch files, config files, message types; includes `go2_sim`, `go2_description`, `quadropted_msgs` |
| [topics-and-interfaces.md](topics-and-interfaces.md) | All published/subscribed topics, QoS profiles, velocity pipeline, TF tree, multi-robot namespacing |
| [webrtc-commands.md](webrtc-commands.md) | All `ROBOT_CMD` IDs, `RTC_TOPIC` strings, CLI examples, joystick shortcuts |
| [navigation-and-slam.md](navigation-and-slam.md) | SLAM mapping workflow, Nav2 usage, key parameters, 3D PLY dump |
| [simulation.md](simulation.md) | Sim/hardware switching (bare metal + Docker), Gazebo setup, topic bridges, VNC access, `USE_SIM` env var |
| [extending.md](extending.md) | Adding nodes, commands, message types, launch args, and tests |

For build and run commands see the top-level [CLAUDE.md](../CLAUDE.md).
