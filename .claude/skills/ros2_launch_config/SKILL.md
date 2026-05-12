---
name: ROS2 Launch & Configuration
description: Clean Architecture compatible ROS2 launch files and parameter management
---

# ROS2 Launch & Configuration Skill

## Launch File Structure

```
package_name/launch/
├── robot_launch.py       # Main launch file
├── sensors_launch.py     # Sensor subsystem
├── navigation_launch.py  # Navigation subsystem
└── includes/
    ├── common.py
    └── defaults.py
```

## Main Launch File Template

```python
#!/usr/bin/env python3
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node, SetParameter

def generate_launch_description():
    pkg = get_package_share_directory('go2_robot_sdk')

    declared_arguments = [
        DeclareLaunchArgument('robot_ip', default_value='192.168.12.1', description='Robot IP'),
        DeclareLaunchArgument('conn_type', default_value='webrtc', description='webrtc or cyclonedds'),
        DeclareLaunchArgument('use_sim', default_value='false', description='Simulation mode'),
        DeclareLaunchArgument('config_file',
            default_value=os.path.join(pkg, 'config', 'params.yaml'),
            description='Parameter file path'),
    ]

    env_setup = [
        SetEnvironmentVariable('RCUTILS_COLORIZED_OUTPUT', '1'),
    ]

    global_params = SetParameter(name='use_sim_time', value=LaunchConfiguration('use_sim'))

    go2_driver = Node(
        package='go2_robot_sdk',
        executable='go2_driver',
        name='go2_driver',
        parameters=[
            LaunchConfiguration('config_file'),
            {'robot_ip': LaunchConfiguration('robot_ip'),
             'conn_type': LaunchConfiguration('conn_type')},
        ],
        output='screen'
    )

    return LaunchDescription(declared_arguments + env_setup + [global_params, go2_driver])
```

## Parameter File (YAML)

```yaml
/**:
  ros__parameters:
    use_sim_time: false
    log_level: "info"

go2_driver:
  ros__parameters:
    robot_ip: "192.168.12.1"
    conn_type: "webrtc"
    update_rate: 50.0
    lidar:
      frame_id: "lidar_link"
      max_range: 30.0
```

## Loading Parameters in Python Nodes

```python
self.declare_parameter('robot_ip', '192.168.12.1')
self.declare_parameter('conn_type', 'webrtc')
self.declare_parameter('update_rate', 50.0)

self._robot_ip = self.get_parameter('robot_ip').value
self._conn_type = self.get_parameter('conn_type').value
self._update_rate = self.get_parameter('update_rate').value
```

## Including Sub-Launch Files

```python
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

nav_launch = IncludeLaunchDescription(
    PythonLaunchDescriptionSource(
        os.path.join(pkg, 'launch', 'navigation_launch.py')
    ),
    launch_arguments={'use_sim': LaunchConfiguration('use_sim')}.items()
)
```

## Lifecycle Node in Launch

```python
from launch_ros.actions import LifecycleNode
from launch_ros.events.lifecycle import ChangeState
from lifecycle_msgs.msg import Transition
from launch.actions import EmitEvent, RegisterEventHandler
from launch.event_handlers import OnProcessStart

driver_node = LifecycleNode(
    package='go2_robot_sdk', executable='lidar_driver',
    name='lidar', namespace='', output='screen'
)

configure_event = RegisterEventHandler(
    OnProcessStart(
        target_action=driver_node,
        on_start=[
            EmitEvent(event=ChangeState(
                lifecycle_node_matcher=lambda n: n == driver_node,
                transition_id=Transition.TRANSITION_CONFIGURE,
            )),
        ]
    )
)
```
