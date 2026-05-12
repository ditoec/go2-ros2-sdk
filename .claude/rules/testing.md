---
description: ROS2 Testing Standards
---

# ROS2 Testing Standards

## Test Structure

```
package_name/test/
├── unit/           # Pure Python tests (domain/application logic)
├── integration/    # ROS2 node tests
└── e2e/            # Full system/Launch tests
```

## Unit Tests (pytest, no ROS2)

```python
import pytest
from go2_robot_sdk.domain.entities.robot_data import RobotData

class TestRobotData:
    def test_creation(self):
        data = RobotData(id="go2_0", position=(0, 0, 0), velocity=(0, 0, 0))
        assert data.id == "go2_0"

    def test_invalid_id(self):
        with pytest.raises(ValueError):
            RobotData(id="", position=(0, 0, 0), velocity=(0, 0, 0))
```

## Integration Tests (rclpy)

```python
import pytest
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

@pytest.fixture(scope='module')
def ros2_context():
    rclpy.init()
    yield
    rclpy.shutdown()

@pytest.fixture
def test_node(ros2_context):
    node = Node('test_node')
    yield node
    node.destroy_node()

def test_publisher(test_node):
    received = []
    sub = test_node.create_subscription(String, 'test', lambda m: received.append(m), 10)
    pub = test_node.create_publisher(String, 'test', 10)
    msg = String(data='Hello')
    pub.publish(msg)
    rclpy.spin_once(test_node, timeout_sec=1.0)
    assert len(received) >= 1
```

## Launch Tests (E2E)

```python
import launch_testing
from launch import LaunchDescription
from launch_ros.actions import Node

@launch_testing.markers.keep_alive
def generate_test_description():
    return LaunchDescription([
        Node(package='go2_robot_sdk', executable='go2_driver'),
        launch_testing.actions.ReadyToTest()
    ])
```

## Test Commands

```bash
# All tests
colcon test

# Specific package
colcon test --packages-select go2_robot_sdk

# View results
colcon test-result --all --verbose

# Python coverage
pytest --cov=go2_robot_sdk --cov-report=html
```

## Best Practices

- Unit tests must NOT import `rclpy` or any ROS2 message types — domain is pure Python.
- Integration tests call `rclpy.init()` / `rclpy.shutdown()` exactly once per module.
- Mock infrastructure adapters (WebRTC, publishers) to isolate application logic.
- Use `colcon test` rather than `pytest` directly to ensure ROS2 environment is sourced.
