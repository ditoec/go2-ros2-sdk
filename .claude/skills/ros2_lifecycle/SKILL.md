---
name: ROS2 Lifecycle Nodes
description: ROS2 Managed (Lifecycle) Node implementation with Clean Architecture (Python & C++)
---

# ROS2 Lifecycle Nodes Skill

## State Machine

```
UNCONFIGURED → (configure) → INACTIVE → (activate) → ACTIVE
ACTIVE → (deactivate) → INACTIVE → (cleanup) → UNCONFIGURED
Any state → (shutdown) → FINALIZED
```

## Python Implementation

```python
from rclpy.lifecycle import Node as LifecycleNode, TransitionCallbackReturn, State
from std_msgs.msg import String

class ManagedDriverNode(LifecycleNode):
    def __init__(self):
        super().__init__('managed_driver')

    def on_configure(self, state: State) -> TransitionCallbackReturn:
        self.get_logger().info('Configuring...')
        self._pub = self.create_lifecycle_publisher(String, 'output', 10)
        # Initialize connections, load params
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state: State) -> TransitionCallbackReturn:
        self.get_logger().info('Activating...')
        self._pub.on_activate()
        # Start timers, open hardware connections
        return TransitionCallbackReturn.SUCCESS

    def on_deactivate(self, state: State) -> TransitionCallbackReturn:
        self.get_logger().info('Deactivating...')
        self._pub.on_deactivate()
        return TransitionCallbackReturn.SUCCESS

    def on_cleanup(self, state: State) -> TransitionCallbackReturn:
        self.get_logger().info('Cleaning up...')
        self.destroy_lifecycle_publisher(self._pub)
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state: State) -> TransitionCallbackReturn:
        self.get_logger().info('Shutting down...')
        return TransitionCallbackReturn.SUCCESS
```

## C++ Implementation

```cpp
// infrastructure/ros2/nodes/managed_node.hpp
#pragma once
#include <rclcpp_lifecycle/lifecycle_node.hpp>
#include <std_msgs/msg/string.hpp>

using CallbackReturn = rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn;

class ManagedNode : public rclcpp_lifecycle::LifecycleNode {
public:
    explicit ManagedNode(const std::string& node_name)
        : rclcpp_lifecycle::LifecycleNode(node_name) {}

    CallbackReturn on_configure(const rclcpp_lifecycle::State&) override {
        pub_ = this->create_publisher<std_msgs::msg::String>("topic", 10);
        return CallbackReturn::SUCCESS;
    }

    CallbackReturn on_activate(const rclcpp_lifecycle::State&) override {
        pub_->on_activate();
        return CallbackReturn::SUCCESS;
    }

    CallbackReturn on_deactivate(const rclcpp_lifecycle::State&) override {
        pub_->on_deactivate();
        return CallbackReturn::SUCCESS;
    }

    CallbackReturn on_cleanup(const rclcpp_lifecycle::State&) override {
        pub_.reset();
        return CallbackReturn::SUCCESS;
    }

    CallbackReturn on_shutdown(const rclcpp_lifecycle::State&) override {
        return CallbackReturn::SUCCESS;
    }

private:
    rclcpp_lifecycle::LifecyclePublisher<std_msgs::msg::String>::SharedPtr pub_;
};
```

## Lifecycle Client (Python)

```python
import lifecycle_msgs.srv as lc_srv
from lifecycle_msgs.msg import Transition

class LifecycleClient(Node):
    def __init__(self, target_node: str):
        super().__init__('lifecycle_client')
        self._change_state = self.create_client(
            lc_srv.ChangeState, f'{target_node}/change_state'
        )

    def configure(self):
        return self._call_transition(Transition.TRANSITION_CONFIGURE)

    def activate(self):
        return self._call_transition(Transition.TRANSITION_ACTIVATE)

    def _call_transition(self, transition_id: int):
        req = lc_srv.ChangeState.Request()
        req.transition.id = transition_id
        future = self._change_state.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        return future.result().success
```

## Best Practices

- Allocate resources (publishers, connections) in `on_configure`; release in `on_cleanup`.
- Only publish data or run main logic in the **ACTIVE** state.
- Use `on_error` to handle transition failures gracefully.
- Use `LifecycleNode` in launch files with auto-configure/activate events.
