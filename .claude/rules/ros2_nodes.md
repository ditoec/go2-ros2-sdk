---
description: ROS2 Node Development Standards
---

# ROS2 Node Standards

## Base Node Pattern (Python)

```python
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

## Publisher Pattern

```python
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy

def create_reliable_publisher(self, msg_type, topic_name, queue_size=10):
    qos = QoSProfile(
        reliability=ReliabilityPolicy.RELIABLE,
        durability=DurabilityPolicy.TRANSIENT_LOCAL,
        depth=queue_size
    )
    return self.create_publisher(msg_type, topic_name, qos)

def create_sensor_publisher(self, msg_type, topic_name, queue_size=10):
    qos = QoSProfile(
        reliability=ReliabilityPolicy.BEST_EFFORT,
        durability=DurabilityPolicy.VOLATILE,
        depth=queue_size
    )
    return self.create_publisher(msg_type, topic_name, qos)
```

## Subscriber Pattern

```python
from rclpy.qos import qos_profile_sensor_data, qos_profile_system_default

def create_sensor_subscriber(self, msg_type, topic_name, callback):
    return self.create_subscription(msg_type, topic_name, callback, qos_profile_sensor_data)

def create_reliable_subscriber(self, msg_type, topic_name, callback):
    return self.create_subscription(msg_type, topic_name, callback, qos_profile_system_default)
```

## Service Pattern

```python
class ServiceNode(BaseNode):
    def __init__(self):
        super().__init__('service_node')
        self._srv = self.create_service(SetBool, 'enable_feature', self._enable_callback)

    def _enable_callback(self, request, response):
        try:
            self._feature_enabled = request.data
            response.success = True
            response.message = f"Feature {'enabled' if request.data else 'disabled'}"
        except Exception as e:
            response.success = False
            response.message = str(e)
        return response
```

## Lifecycle Node Pattern

```python
from rclpy.lifecycle import Node as LifecycleNode, TransitionCallbackReturn

class ManagedNode(LifecycleNode):
    def on_configure(self, state):
        self._pub = self.create_lifecycle_publisher(String, 'topic', 10)
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state):
        self._pub.on_activate()
        return TransitionCallbackReturn.SUCCESS

    def on_deactivate(self, state):
        self._pub.on_deactivate()
        return TransitionCallbackReturn.SUCCESS

    def on_cleanup(self, state):
        self.destroy_publisher(self._pub)
        return TransitionCallbackReturn.SUCCESS
```

## Thread Safety (Go2DriverNode pattern)

The Go2 SDK runs the ROS2 node in a thread while asyncio runs the WebRTC loop. Use `call_soon_threadsafe` to schedule ROS2 callbacks from asyncio:

```python
# Schedule from asyncio into ROS2 node thread
self._event_loop.call_soon_threadsafe(self._ros_node.some_callback, data)
```
