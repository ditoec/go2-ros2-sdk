---
description: ROS2 General Conventions and Best Practices
---

# ROS2 General Conventions

## Package Naming

- Package names must be in **snake_case**, lowercase, underscores only.
- Format: `<robot>_<component>` (e.g. `go2_robot_sdk`, `go2_interfaces`).

## File Structure (Python Package)

```
package_name/
├── package.xml
├── setup.py
├── setup.cfg
├── resource/
│   └── package_name
├── package_name/
│   ├── __init__.py
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   └── presentation/
├── launch/
│   └── node_launch.py
├── config/
│   └── params.yaml
└── test/
    └── test_node.py
```

## Python Setup

```python
from setuptools import find_packages, setup

package_name = 'package_name'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/node_launch.py']),
        ('share/' + package_name + '/config', ['config/params.yaml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    entry_points={
        'console_scripts': [
            'node_name = package_name.node_file:main',
        ],
    },
)
```

## Launch Files

```python
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    use_sim_time = DeclareLaunchArgument(
        'use_sim_time', default_value='false', description='Use simulation time'
    )
    my_node = Node(
        package='package_name',
        executable='node_name',
        name='node_name',
        parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}],
        output='screen'
    )
    return LaunchDescription([use_sim_time, my_node])
```

## Parameter Files (YAML)

```yaml
/**:
  ros__parameters:
    update_rate: 10.0
    sensor:
      frame_id: "base_link"
      range_min: 0.1
```

## Logging

```python
self.get_logger().debug('Debug detail')
self.get_logger().info('Normal info')
self.get_logger().warn('Warning')
self.get_logger().error('Error')

# High-frequency: throttle
self.get_logger().info('Status', throttle_duration_sec=1.0)
```

## Workspace Layout

```
ros2_ws/
├── src/
│   ├── go2_robot_sdk/
│   ├── go2_interfaces/
│   ├── lidar_processor/
│   └── ...
├── build/
├── install/
└── log/
```
