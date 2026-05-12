---
name: ROS2 Bag Utility
description: ROS2 bag recording and analysis utilities with Clean Architecture (Python & C++)
---

# ROS2 Bag Utility Skill

## Domain Layer

```python
# domain/interfaces/data_recorder.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

@dataclass
class RecordingConfig:
    bag_name: str
    topics: List[str]
    storage_id: str = 'mcap'

class IDataRecorder(ABC):
    @abstractmethod
    def start_recording(self, config: RecordingConfig) -> bool:
        pass

    @abstractmethod
    def stop_recording(self) -> None:
        pass

    @abstractmethod
    def is_recording(self) -> bool:
        pass
```

## Infrastructure Layer (Python)

```python
# infrastructure/ros2/bag/bag_recorder.py
import subprocess
from domain.interfaces.data_recorder import IDataRecorder, RecordingConfig

class BagRecorder(IDataRecorder):
    def __init__(self):
        self._process = None

    def start_recording(self, config: RecordingConfig) -> bool:
        topics_args = ' '.join(config.topics)
        cmd = f'ros2 bag record -o {config.bag_name} --storage {config.storage_id} {topics_args}'
        self._process = subprocess.Popen(cmd.split())
        return self._process is not None

    def stop_recording(self) -> None:
        if self._process:
            self._process.terminate()
            self._process = None

    def is_recording(self) -> bool:
        return self._process is not None and self._process.poll() is None
```

## Infrastructure Layer (C++)

```cpp
// infrastructure/ros2/bag/bag_recorder.hpp
#include <rclcpp/rclcpp.hpp>
#include <rosbag2_cpp/writer.hpp>
#include <rosbag2_storage/storage_options.hpp>

class BagRecorder {
public:
    explicit BagRecorder(rclcpp::Node::SharedPtr node) : node_(node) {}

    bool start_recording(const std::string& bag_name,
                         const std::vector<std::string>& topics) {
        try {
            writer_ = std::make_unique<rosbag2_cpp::Writer>();
            rosbag2_storage::StorageOptions storage_options;
            storage_options.uri = bag_name;
            storage_options.storage_id = "mcap";
            rosbag2_cpp::ConverterOptions converter_options;
            converter_options.input_serialization_format = "cdr";
            converter_options.output_serialization_format = "cdr";
            writer_->open(storage_options, converter_options);
            is_recording_ = true;
            return true;
        } catch (const std::exception& e) {
            RCLCPP_ERROR(node_->get_logger(), "Failed to open bag: %s", e.what());
            return false;
        }
    }

    void stop_recording() {
        writer_.reset();
        is_recording_ = false;
    }

private:
    rclcpp::Node::SharedPtr node_;
    std::unique_ptr<rosbag2_cpp::Writer> writer_;
    bool is_recording_ = false;
};
```

## CLI Commands

```bash
# Record all topics
ros2 bag record -a -o my_bag

# Record specific GO2 topics
ros2 bag record -o go2_session \
    /go2_state /joint_states /imu /odom /point_cloud2 /go2_camera/color/image

# Replay at normal speed
ros2 bag play my_bag

# Replay at 0.5x speed
ros2 bag play my_bag --rate 0.5

# Inspect bag info
ros2 bag info my_bag
```

## Best Practices

1. **Storage**: Prefer `mcap` over `sqlite3` for better performance and tooling support.
2. **Serialization**: Use `cdr` format for compatibility.
3. **Selective recording**: Record only needed topics — `/point_cloud2` is large (~7 Hz).
4. **Splitting**: Use `--max-bag-size` for long recordings to avoid huge files.
5. **Map saving**: Use `MAP_SAVE=True` env var in GO2 SDK to auto-save `.ply` pointclouds.
