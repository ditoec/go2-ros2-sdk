---
name: ROS2 Node Creation
description: Guide for creating ROS2 nodes following Clean Architecture principles (Python & C++)
---

# ROS2 Node Creation Skill

## Directory Structure

```
src/
├── domain/
│   ├── entities/
│   ├── repositories/
│   └── use_cases/
├── application/
│   ├── services/
│   └── interfaces/
└── infrastructure/
    └── ros2/
        ├── nodes/
        ├── publishers/
        ├── subscribers/
        └── services/
```

## Python — Base Node Template

```python
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from abc import ABC, abstractmethod

class BaseNode(Node, ABC):
    def __init__(self, node_name: str):
        super().__init__(node_name)
        self._setup_parameters()
        self._setup_publishers()
        self._setup_subscribers()
        self._setup_services()
        self._setup_timers()
        self.get_logger().info(f'{node_name} initialized')

    @abstractmethod
    def _setup_parameters(self) -> None: pass

    @abstractmethod
    def _setup_publishers(self) -> None: pass

    @abstractmethod
    def _setup_subscribers(self) -> None: pass

    def _setup_services(self) -> None: pass
    def _setup_timers(self) -> None: pass

    def get_default_qos(self) -> QoSProfile:
        return QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )
```

## Python — Concrete Node

```python
from std_msgs.msg import Float64
from sensor_msgs.msg import Temperature

class SensorNode(BaseNode):
    def __init__(self, sensor_service):
        self._sensor_service = sensor_service
        super().__init__('sensor_node')

    def _setup_parameters(self):
        self.declare_parameter('update_rate', 10.0)
        self._update_rate = self.get_parameter('update_rate').value

    def _setup_publishers(self):
        self._temp_pub = self.create_publisher(Temperature, 'temperature', self.get_default_qos())

    def _setup_subscribers(self):
        self._raw_sub = self.create_subscription(Float64, 'raw_sensor', self._raw_callback, 10)

    def _setup_timers(self):
        period = 1.0 / self._update_rate
        self._timer = self.create_timer(period, self._timer_callback)

    def _raw_callback(self, msg: Float64):
        entity = self._sensor_service.process(msg.data)
        out = Temperature()
        out.temperature = entity.value
        self._temp_pub.publish(out)

    def _timer_callback(self):
        pass
```

## C++ — Base Node Header

```cpp
// infrastructure/ros2/nodes/base_node.hpp
#pragma once
#include <rclcpp/rclcpp.hpp>

namespace infrastructure::ros2::nodes {

class BaseNode : public rclcpp::Node {
public:
    explicit BaseNode(const std::string& node_name,
                      const rclcpp::NodeOptions& options = rclcpp::NodeOptions());
    virtual ~BaseNode() = default;

protected:
    virtual void setup_parameters() = 0;
    virtual void setup_publishers() = 0;
    virtual void setup_subscribers() = 0;
    virtual void setup_services() {}
    virtual void setup_timers() {}

    rclcpp::QoS get_default_qos() const;
};

} // namespace
```

## C++ — QoS Profiles

```cpp
// infrastructure/ros2/qos_profiles.hpp
#pragma once
#include <rclcpp/qos.hpp>

namespace infrastructure::ros2 {

class QoSProfiles {
public:
    static rclcpp::QoS sensor_data() {
        return rclcpp::QoS(1).best_effort().durability_volatile();
    }
    static rclcpp::QoS command() {
        return rclcpp::QoS(10).reliable().transient_local();
    }
};

} // namespace
```

## Dependency Injection

```python
# application/services/sensor_service.py
from abc import ABC, abstractmethod
from domain.entities.sensor_data import SensorData

class ISensorService(ABC):
    @abstractmethod
    def process(self, raw_data: float) -> SensorData:
        pass

# Wired at startup (main.py or launch)
service = ConcreteSensorService(calibration_params)
node = SensorNode(sensor_service=service)
```
