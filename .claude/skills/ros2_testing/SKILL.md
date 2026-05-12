---
name: ROS2 Testing
description: ROS2 test strategies and patterns with Clean Architecture (Python & C++)
---

# ROS2 Testing Skill

## Test Pyramid

```
        /\
       /  \   E2E — Launch Tests
      /----\
     /      \  Integration — Node/Component Tests
    /--------\
   /          \  Unit — Domain/Application (no ROS2)
  /------------\
```

## Directory Structure

```
package_name/test/
├── unit/
│   ├── domain/
│   └── application/
├── integration/
│   └── ros2/
└── e2e/
    └── launch_tests/
```

## Unit Tests (Domain — no rclpy)

```python
# test/unit/domain/test_robot_data.py
import pytest
from go2_robot_sdk.domain.entities.robot_data import RobotData

class TestRobotData:
    def test_creation(self):
        data = RobotData(id="go2_0", position=(0.0, 0.0, 0.0), velocity=(0.0, 0.0, 0.0))
        assert data.id == "go2_0"

    def test_empty_id_rejected(self):
        with pytest.raises(ValueError):
            RobotData(id="", position=(0.0, 0.0, 0.0), velocity=(0.0, 0.0, 0.0))
```

## Integration Tests (rclpy Node)

```python
# test/integration/test_go2_driver.py
import pytest
import rclpy
from rclpy.node import Node
from go2_interfaces.msg import Go2State

@pytest.fixture(scope='module')
def ros2_context():
    rclpy.init()
    yield
    rclpy.shutdown()

@pytest.fixture
def test_node(ros2_context):
    node = Node('test_helper')
    yield node
    node.destroy_node()

def test_state_published(test_node):
    received = []
    test_node.create_subscription(Go2State, '/go2_state', received.append, 10)
    rclpy.spin_once(test_node, timeout_sec=2.0)
    # Verify structure if message arrived
    if received:
        assert hasattr(received[0], 'id')
```

## GTest Unit Tests (C++)

```cpp
// test/unit/domain/test_robot_controller.cpp
#include <gtest/gtest.h>
#include <gmock/gmock.h>
#include "domain/use_cases/robot_controller.hpp"

using ::testing::Return;

class MockRobotRepository : public domain::repositories::IRobotRepository {
public:
    MOCK_METHOD(domain::entities::RobotState, get_state, (), (override));
    MOCK_METHOD(void, set_mode, (domain::entities::RobotMode), (override));
};

TEST(RobotControllerTest, StartFromIdle) {
    auto mock_repo = std::make_shared<MockRobotRepository>();
    domain::use_cases::RobotControllerUseCase use_case(mock_repo);

    EXPECT_CALL(*mock_repo, get_state())
        .WillOnce(Return(domain::entities::RobotState{domain::entities::RobotMode::IDLE}));
    EXPECT_CALL(*mock_repo, set_mode(domain::entities::RobotMode::ACTIVE));

    auto result = use_case.start();
    EXPECT_TRUE(result.success);
}
```

## Launch Tests (E2E)

```python
# test/e2e/test_robot_launch.py
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

## Commands

```bash
colcon test                                          # All packages
colcon test --packages-select go2_robot_sdk         # Specific package
colcon test-result --all --verbose                  # Show results
pytest test/unit/ --cov=go2_robot_sdk              # Coverage
```

## Best Practices

- Unit tests: never import `rclpy` or ROS2 message types — domain is pure Python.
- Integration tests: one `rclpy.init()` / `rclpy.shutdown()` pair per test module.
- Mock `IRobotDataPublisher` and `WebRTCAdapter` to isolate application logic.
- GTest mocks (C++): use `gmock` to mock domain interfaces.
