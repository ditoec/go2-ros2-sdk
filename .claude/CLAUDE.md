# ROS2 Clean Architecture Project — GO2 Robot SDK

This project uses a comprehensive set of **Claude Skills** for ROS2 development following **Clean Architecture** principles, applied to the Unitree GO2 quadruped robot SDK.

## Rules (auto-loaded)

@.claude/rules/clean_architecture.md
@.claude/rules/ros2_general.md
@.claude/rules/ros2_nodes.md
@.claude/rules/ros2_communication.md
@.claude/rules/robot_specific.md
@.claude/rules/testing.md

## Available Skills

| Skill | Description | Key Components |
|---|---|---|
| **ros2_node_creation** | Clean Architecture compliant Nodes | `BaseNode` template, Dependency Injection, QoS profiles |
| **ros2_launch_config** | Modular Launch files | Composition, `IncludeLaunchDescription`, Parameter management |
| **ros2_service_action** | Services and Actions | Server/Client wrappers, Domain Use Case integration |
| **ros2_messaging** | Pub/Sub Patterns | Domain-driven publishers, Generic subscribers, Thread-safe buffers |
| **ros2_testing** | Testing Strategy | Unit (Domain), Integration (Node), E2E (Launch), GTest/GMock |
| **ros2_lifecycle** | Managed Nodes | Lifecycle Node templates, State transition management |
| **ros2_transforms** | TF2 Management | TF2 Wrappers isolating domain from `geometry_msgs` |
| **ros2_diagnostics** | Health Monitoring | `diagnostic_updater` integration, Frequency monitoring |
| **ros2_bag** | Data Recording | Programmatic bag recording/replay (rosbag2) |

Use a skill by referencing its file, e.g. `.claude/skills/ros2_node_creation/SKILL.md`.

## Project Layer Map (GO2 SDK)

| Template Layer | GO2 SDK Equivalent |
|---|---|
| `src/domain/` | `go2_robot_sdk/domain/` |
| `src/application/` | `go2_robot_sdk/application/` |
| `src/infrastructure/` | `go2_robot_sdk/infrastructure/` |
| Presentation (Node) | `go2_robot_sdk/presentation/` (`Go2DriverNode`) |

## Quick Commands

See [ROS2 Commands Reference](.claude/commands/ros2.md) for `colcon`, `ros2`, `rqt` reference.

- **Build**: `colcon build --symlink-install`
- **Build package**: `colcon build --packages-select go2_robot_sdk`
- **Test**: `colcon test`
- **Source**: `source install/setup.bash`
