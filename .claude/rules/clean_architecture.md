---
description: Clean Architecture Principles for ROS2 Projects
---

# Clean Architecture Rules

## Layer Dependency Rules

```
┌─────────────────────────────────────────────────────────┐
│                  PRESENTATION LAYER                      │
│          (Go2DriverNode — ROS2 entry point)             │
└─────────────────────────┬───────────────────────────────┘
                          │ depends on
┌─────────────────────────▼───────────────────────────────┐
│                  APPLICATION LAYER                       │
│      (RobotDataService, RobotControlService)             │
└─────────────────────────┬───────────────────────────────┘
                          │ depends on
┌─────────────────────────▼───────────────────────────────┐
│                    DOMAIN LAYER                          │
│     (RobotConfig, RobotData, interfaces, math)           │
└─────────────────────────▲───────────────────────────────┘
                          │ implements
┌─────────────────────────┴───────────────────────────────┐
│                 INFRASTRUCTURE LAYER                     │
│   (WebRTCAdapter, ROS2Publisher, LiDAR decoder)          │
└─────────────────────────────────────────────────────────┘
```

**CRITICAL RULES:**

1. The Domain layer must NOT depend on any outer layer.
2. The Application layer can only depend on the Domain layer.
3. The Infrastructure layer implements Domain interfaces.
4. The Presentation layer can only depend on the Application layer.

## Domain Layer

### Entities (Python)

```python
# CORRECT: Pure Python, no external dependencies
from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass
class RobotData:
    """Robot domain entity — no ROS2 imports."""
    id: str
    position: tuple
    velocity: tuple
```

### Domain Interfaces (Ports)

```python
# CORRECT: Abstract interface in domain layer
from abc import ABC, abstractmethod

class IRobotDataPublisher(ABC):
    @abstractmethod
    def publish_state(self, data: RobotData) -> None:
        pass
```

## Application Layer

```python
# CORRECT: Orchestrates domain logic, no ROS2 dependency
class RobotDataService:
    def __init__(self, publisher: IRobotDataPublisher):
        self._publisher = publisher

    def process_webrtc_message(self, topic: str, payload: dict) -> None:
        data = RobotData(...)
        self._publisher.publish_state(data)
```

## Infrastructure Layer

```python
# CORRECT: Implements domain interface, owns ROS2 imports
import rclpy
from rclpy.node import Node
from go2_interfaces.msg import Go2State

class ROS2Publisher(IRobotDataPublisher):
    def publish_state(self, data: RobotData) -> None:
        msg = Go2State()
        # map domain entity → ROS2 message
        self._pub.publish(msg)
```

## Anti-Patterns to Avoid

```python
# WRONG: Domain importing ROS2
from rclpy.node import Node  # Never in domain/

# WRONG: Business logic in infrastructure
class ROS2Publisher:
    def publish_state(self, data):
        if data.battery < 20:   # Business rule belongs in domain/application
            return
```
