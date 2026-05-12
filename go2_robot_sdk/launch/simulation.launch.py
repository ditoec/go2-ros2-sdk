# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

"""
Gazebo simulation launch for the GO2 robot SDK.

Replaces the hardware driver (go2_driver_node) with a Gazebo simulation
provided by the go2_ros2_sim_py package. All downstream SDK nodes (Nav2,
SLAM, coco_detector, RViz, joystick) work unchanged.

Prerequisites:
  Clone https://github.com/abutalipovvv/go2_ros2_sim_py into your workspace
  src/ directory and rebuild before using this launch file.

Usage:
  ros2 launch go2_robot_sdk simulation.launch.py
  ros2 launch go2_robot_sdk simulation.launch.py slam:=false nav2:=false
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import (
    FrontendLaunchDescriptionSource,
    PythonLaunchDescriptionSource,
)


def _get_sim_launch():
    """Return IncludeLaunchDescription for go2_ros2_sim_py, or raise with install hint."""
    try:
        sim_pkg_dir = get_package_share_directory('go2_ros2_sim_py')
    except Exception:
        raise RuntimeError(
            "\n\ngo2_ros2_sim_py package not found.\n"
            "Clone it into your workspace and rebuild:\n"
            "  cd <ros2_ws>/src\n"
            "  git clone https://github.com/abutalipovvv/go2_ros2_sim_py\n"
            "  cd .. && colcon build --packages-select go2_ros2_sim_py\n"
        )

    # go2_ros2_sim_py bundles its own SLAM and Nav2. We disable them here
    # and use the SDK's own tuned configs instead.
    # Adjust launch file path if go2_ros2_sim_py restructures its launch dir.
    sim_launch_candidates = [
        os.path.join(sim_pkg_dir, 'launch', 'gazebo_multi_nav2_world.launch.py'),
        os.path.join(sim_pkg_dir, 'launch', 'gazebo_world.launch.py'),
        os.path.join(sim_pkg_dir, 'launch', 'simulation.launch.py'),
    ]

    sim_launch_file = next(
        (p for p in sim_launch_candidates if os.path.isfile(p)), None
    )
    if sim_launch_file is None:
        raise RuntimeError(
            f"Could not find a known launch file in {sim_pkg_dir}/launch/.\n"
            "Available files: " + str(os.listdir(os.path.join(sim_pkg_dir, 'launch')))
        )

    return IncludeLaunchDescription(
        PythonLaunchDescriptionSource(sim_launch_file),
        launch_arguments={
            'use_sim_time': 'true',
            # Disable go2_ros2_sim_py's bundled SLAM and Nav2 — we use SDK configs
            'slam': 'false',
            'nav2': 'false',
        }.items(),
    )


def generate_launch_description():
    pkg_dir = get_package_share_directory('go2_robot_sdk')

    urdf_path = os.path.join(pkg_dir, 'urdf', 'go2.urdf')
    with open(urdf_path, 'r') as f:
        robot_desc = f.read()

    slam_config = os.path.join(pkg_dir, 'config', 'mapper_params_online_async.yaml')
    nav2_config = os.path.join(pkg_dir, 'config', 'nav2_params_sim.yaml')
    joystick_config = os.path.join(pkg_dir, 'config', 'joystick.yaml')
    twist_mux_config = os.path.join(pkg_dir, 'config', 'twist_mux.yaml')
    rviz_config = os.path.join(pkg_dir, 'config', 'single_robot_conf.rviz')

    # ------------------------------------------------------------------ #
    # Launch arguments — same surface as robot.launch.py for easy switching
    # ------------------------------------------------------------------ #
    launch_args = [
        DeclareLaunchArgument('rviz2', default_value='true', description='Launch RViz2'),
        DeclareLaunchArgument('nav2', default_value='true', description='Launch Nav2'),
        DeclareLaunchArgument('slam', default_value='true', description='Launch SLAM'),
        DeclareLaunchArgument('foxglove', default_value='false', description='Launch Foxglove Bridge'),
        DeclareLaunchArgument('joystick', default_value='true', description='Launch joystick'),
        DeclareLaunchArgument('teleop', default_value='true', description='Launch teleoperation'),
    ]

    # ------------------------------------------------------------------ #
    # Gazebo simulation (go2_ros2_sim_py)
    # Publishes: /robot1/joint_states, /robot1/odom, /robot1/imu,
    #            /robot1/point_cloud2, /robot1/go2_camera/color/image
    # Subscribes: /robot1/cmd_vel
    # ------------------------------------------------------------------ #
    gazebo_launch = _get_sim_launch()

    # ------------------------------------------------------------------ #
    # Topic bridges: relay sim's /robot1/* namespace to SDK root topics.
    # Requires the topic_tools package (ros-$ROS_DISTRO-topic-tools).
    # Direction: sim → SDK (except cmd_vel which is SDK → sim).
    # ------------------------------------------------------------------ #
    topic_bridges = [
        Node(
            package='topic_tools',
            executable='relay',
            name='relay_joint_states',
            arguments=['/robot1/joint_states', '/joint_states'],
            parameters=[{'use_sim_time': True}],
            output='screen',
        ),
        Node(
            package='topic_tools',
            executable='relay',
            name='relay_odom',
            arguments=['/robot1/odom', '/odom'],
            parameters=[{'use_sim_time': True}],
            output='screen',
        ),
        Node(
            package='topic_tools',
            executable='relay',
            name='relay_imu',
            arguments=['/robot1/imu', '/imu'],
            parameters=[{'use_sim_time': True}],
            output='screen',
        ),
        Node(
            package='topic_tools',
            executable='relay',
            name='relay_point_cloud2',
            arguments=['/robot1/point_cloud2', '/point_cloud2'],
            parameters=[{'use_sim_time': True}],
            output='screen',
        ),
        Node(
            package='topic_tools',
            executable='relay',
            name='relay_camera',
            arguments=['/robot1/go2_camera/color/image', '/go2_camera/color/image'],
            parameters=[{'use_sim_time': True}],
            output='screen',
        ),
        # Reverse bridge: SDK's muxed velocity → sim's command input
        Node(
            package='topic_tools',
            executable='relay',
            name='relay_cmd_vel',
            arguments=['/cmd_vel_muxed', '/robot1/cmd_vel'],
            parameters=[{'use_sim_time': True}],
            output='screen',
        ),
    ]

    # ------------------------------------------------------------------ #
    # Robot state publisher — uses SDK URDF (same as hardware mode)
    # ------------------------------------------------------------------ #
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='go2_robot_state_publisher',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'robot_description': robot_desc,
        }],
    )

    # ------------------------------------------------------------------ #
    # PointCloud2 → LaserScan (needed by SLAM and Nav2 costmaps)
    # ------------------------------------------------------------------ #
    pointcloud_to_laserscan = Node(
        package='pointcloud_to_laserscan',
        executable='pointcloud_to_laserscan_node',
        name='go2_pointcloud_to_laserscan',
        remappings=[
            ('cloud_in', '/point_cloud2'),
            ('scan', '/scan'),
        ],
        parameters=[{
            'use_sim_time': True,
            'target_frame': 'base_link',
            'max_height': 0.5,
        }],
        output='screen',
    )

    # ------------------------------------------------------------------ #
    # Joystick + twist multiplexer (same as hardware mode)
    # ------------------------------------------------------------------ #
    teleop_nodes = [
        Node(
            package='joy',
            executable='joy_node',
            condition=IfCondition(LaunchConfiguration('joystick')),
            parameters=[joystick_config],
        ),
        Node(
            package='teleop_twist_joy',
            executable='teleop_node',
            name='go2_teleop_node',
            condition=IfCondition(LaunchConfiguration('joystick')),
            parameters=[twist_mux_config],
        ),
        Node(
            package='twist_mux',
            executable='twist_mux',
            output='screen',
            condition=IfCondition(LaunchConfiguration('teleop')),
            parameters=[
                {'use_sim_time': True},
                twist_mux_config,
            ],
        ),
    ]

    # ------------------------------------------------------------------ #
    # Visualization
    # ------------------------------------------------------------------ #
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        condition=IfCondition(LaunchConfiguration('rviz2')),
        name='go2_rviz2',
        output='screen',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': True}],
    )

    foxglove_launch = IncludeLaunchDescription(
        FrontendLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('foxglove_bridge'),
                'launch', 'foxglove_bridge_launch.xml',
            )
        ),
        condition=IfCondition(LaunchConfiguration('foxglove')),
    )

    # ------------------------------------------------------------------ #
    # SLAM — uses SDK's own config with use_sim_time passed via argument
    # ------------------------------------------------------------------ #
    slam_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(
                get_package_share_directory('slam_toolbox'),
                'launch', 'online_async_launch.py',
            )
        ]),
        condition=IfCondition(LaunchConfiguration('slam')),
        launch_arguments={
            'slam_params_file': slam_config,
            'use_sim_time': 'true',
        }.items(),
    )

    # ------------------------------------------------------------------ #
    # Nav2 — uses nav2_params_sim.yaml (use_sim_time: True throughout)
    # ------------------------------------------------------------------ #
    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(
                get_package_share_directory('nav2_bringup'),
                'launch', 'navigation_launch.py',
            )
        ]),
        condition=IfCondition(LaunchConfiguration('nav2')),
        launch_arguments={
            'params_file': nav2_config,
            'use_sim_time': 'true',
        }.items(),
    )

    return LaunchDescription(
        launch_args
        + [gazebo_launch]
        + [robot_state_publisher, pointcloud_to_laserscan]
        + topic_bridges
        + teleop_nodes
        + [rviz_node, foxglove_launch, slam_launch, nav2_launch]
    )
