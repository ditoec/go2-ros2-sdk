---
name: ROS2 Messaging Patterns
description: ROS2 messaging patterns and best practices with Clean Architecture (Python & C++)
---

# ROS2 Messaging Patterns Skill

## Domain-Driven Publisher (Python)

```python
# infrastructure/ros2/publishers/state_publisher.py
from go2_interfaces.msg import Go2State
from domain.entities.robot_data import RobotData
from domain.interfaces.robot_data_publisher import IRobotDataPublisher

class ROS2StatePublisher(IRobotDataPublisher):
    def __init__(self, node, topic: str, qos):
        self._pub = node.create_publisher(Go2State, topic, qos)

    def publish_state(self, data: RobotData) -> None:
        msg = Go2State()
        msg.id = data.id
        # ... map domain entity fields to ROS2 message
        self._pub.publish(msg)
```

## Domain-Driven Publisher (C++)

```cpp
// infrastructure/ros2/publishers/state_publisher.hpp
#include <rclcpp/rclcpp.hpp>
#include "domain/entities/robot_state.hpp"
#include "robot_interfaces/msg/robot_state.hpp"

class RobotStatePublisher {
public:
    RobotStatePublisher(rclcpp::Node::SharedPtr node, const std::string& topic, const rclcpp::QoS& qos)
        : node_(node) {
        publisher_ = node_->create_publisher<robot_interfaces::msg::RobotState>(topic, qos);
    }

    void publish(const domain::entities::RobotState& state) {
        robot_interfaces::msg::RobotState msg;
        msg.mode = static_cast<int>(state.mode);
        publisher_->publish(msg);
    }

private:
    rclcpp::Node::SharedPtr node_;
    rclcpp::Publisher<robot_interfaces::msg::RobotState>::SharedPtr publisher_;
};
```

## Generic Subscriber Handler (C++)

```cpp
// infrastructure/ros2/subscribers/base_subscriber.hpp
template<typename MsgT, typename EntityT>
class BaseSubscriber {
public:
    BaseSubscriber(rclcpp::Node::SharedPtr node,
                   const std::string& topic,
                   const rclcpp::QoS& qos,
                   std::function<void(const EntityT&)> callback)
        : callback_(callback) {

        subscription_ = node->create_subscription<MsgT>(
            topic, qos,
            [this](const typename MsgT::SharedPtr msg) {
                auto entity = convert_to_entity(msg);
                callback_(entity);
            }
        );
    }

protected:
    virtual EntityT convert_to_entity(const typename MsgT::SharedPtr msg) = 0;

private:
    rclcpp::Subscription<MsgT>::SharedPtr subscription_;
    std::function<void(const EntityT&)> callback_;
};
```

## Message Synchronization (C++)

```cpp
// Sync camera image + info using approximate time
#include <message_filters/subscriber.h>
#include <message_filters/sync_policies/approximate_time.h>
#include <message_filters/synchronizer.h>

class CameraSync {
public:
    CameraSync(rclcpp::Node::SharedPtr node) {
        image_sub_.subscribe(node, "go2_camera/color/image");
        info_sub_.subscribe(node, "camera_info");
        sync_ = std::make_shared<Sync>(MySyncPolicy(10), image_sub_, info_sub_);
        sync_->registerCallback(&CameraSync::callback, this);
    }

private:
    void callback(const sensor_msgs::msg::Image::ConstSharedPtr& image,
                  const sensor_msgs::msg::CameraInfo::ConstSharedPtr& info) {}

    message_filters::Subscriber<sensor_msgs::msg::Image> image_sub_;
    message_filters::Subscriber<sensor_msgs::msg::CameraInfo> info_sub_;
    typedef message_filters::sync_policies::ApproximateTime<
        sensor_msgs::msg::Image, sensor_msgs::msg::CameraInfo> MySyncPolicy;
    typedef message_filters::Synchronizer<MySyncPolicy> Sync;
    std::shared_ptr<Sync> sync_;
};
```

## Thread-Safe Buffer (Go2 SDK pattern)

The Go2 SDK dispatches WebRTC messages from asyncio into the ROS2 thread using `call_soon_threadsafe`. When sharing data between threads, protect with a lock:

```python
import threading

class ThreadSafeBuffer:
    def __init__(self):
        self._lock = threading.Lock()
        self._data = None

    def set(self, data):
        with self._lock:
            self._data = data

    def get(self):
        with self._lock:
            return self._data
```

## Best Practices

- **Isolation**: Keep domain entities independent of ROS2 message types.
- **Conversion**: Perform message ↔ entity conversion only in infrastructure.
- **Thread Safety**: Use `threading.Lock` (Python) or `std::mutex` (C++) for shared state.
- **QoS**: Use BEST_EFFORT for sensors, RELIABLE for commands and state.
