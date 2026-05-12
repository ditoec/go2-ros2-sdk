---
name: ROS2 Diagnostics
description: ROS2 Diagnostics and Health Monitoring with Clean Architecture (Python & C++)
---

# ROS2 Diagnostics Skill

## Domain Layer

```python
# domain/entities/health.py
from enum import Enum
from dataclasses import dataclass, field

class HealthLevel(Enum):
    OK = 0
    WARN = 1
    ERROR = 2
    STALE = 3

@dataclass
class ComponentHealth:
    name: str
    level: HealthLevel
    message: str
    values: dict = field(default_factory=dict)
```

## Infrastructure Layer (Python)

```python
# infrastructure/ros2/diagnostics/diagnostics_manager.py
import diagnostic_updater
from diagnostic_msgs.msg import DiagnosticStatus
from domain.entities.health import HealthLevel

class DiagnosticsManager:
    def __init__(self, node, hardware_id: str):
        self._updater = diagnostic_updater.Updater(node)
        self._updater.setHardwareID(hardware_id)

    def register(self, name: str, callback):
        self._updater.add(name, callback)

    def make_callback(self, get_health_fn):
        def cb(stat):
            health = get_health_fn()
            level_map = {
                HealthLevel.OK: DiagnosticStatus.OK,
                HealthLevel.WARN: DiagnosticStatus.WARN,
                HealthLevel.ERROR: DiagnosticStatus.ERROR,
                HealthLevel.STALE: DiagnosticStatus.STALE,
            }
            stat.summary(level_map[health.level], health.message)
            for k, v in health.values.items():
                stat.add(k, str(v))
        return cb
```

## Infrastructure Layer (C++)

```cpp
// infrastructure/ros2/diagnostics/diagnostics_manager.hpp
#include <rclcpp/rclcpp.hpp>
#include <diagnostic_updater/diagnostic_updater.hpp>

class DiagnosticsManager {
public:
    explicit DiagnosticsManager(rclcpp::Node::SharedPtr node)
        : node_(node), updater_(node) {
        updater_.setHardwareID(node->get_name());
    }

    void register_monitor(const std::string& name,
        std::function<void(diagnostic_updater::DiagnosticStatusWrapper&)> callback) {
        updater_.add(name, callback);
    }

private:
    rclcpp::Node::SharedPtr node_;
    diagnostic_updater::Updater updater_;
};
```

## Frequency Monitor (C++)

```cpp
#include <diagnostic_updater/publisher.hpp>

class FrequencyMonitor {
public:
    FrequencyMonitor(diagnostic_updater::Updater& updater,
                     const std::string& topic_name,
                     double min_freq, double max_freq) {
        diagnostic_updater::FrequencyStatusParam freq_param(&min_freq, &max_freq, 0.1, 10);
        monitor_ = std::make_unique<diagnostic_updater::HeaderlessTopicDiagnostic>(
            topic_name, updater, freq_param);
    }

    void tick() { monitor_->tick(); }

private:
    std::unique_ptr<diagnostic_updater::HeaderlessTopicDiagnostic> monitor_;
};
```

## Usage in GO2 SDK

Monitor key topics like `/point_cloud2` (~7 Hz) and `/joint_states` (~1 Hz):

```python
# In Go2DriverNode setup
diag_mgr = DiagnosticsManager(self, hardware_id='go2_robot')

diag_mgr.register('LiDAR frequency', diag_mgr.make_callback(self._get_lidar_health))
diag_mgr.register('WebRTC connection', diag_mgr.make_callback(self._get_connection_health))
```

## Best Practices

1. Set a unique `hardware_id` per robot (useful for multi-robot setups).
2. Use frequency monitors for sensor topics to detect dropped messages.
3. Keep diagnostic callbacks lightweight — they run on a timer.
4. Use OK/WARN/ERROR/STALE semantics consistently.
