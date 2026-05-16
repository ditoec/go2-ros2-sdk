# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

"""
Gazebo simulation launch for the GO2 robot SDK.

The heavy lifting is done by go2_sim (a self-contained package in this SDK):
  - Starts Gazebo Harmonic with an empty world
  - Spawns the GO2 robot (from go2_description xacro)
  - Bridges all sensor topics to SDK root-level names
  - Runs the quadruped gait controller and odometry node

All downstream nodes below (Nav2, SLAM, RViz, joystick) receive the same
topic names as in hardware mode — no bridging or namespace translation needed.

Topic layout provided by go2_sim:
  /imu                        sensor_msgs/Imu
  /scan                       sensor_msgs/LaserScan
  /go2_camera/color/image_raw sensor_msgs/Image
  /joint_states               sensor_msgs/JointState
  /odom                       nav_msgs/Odometry
  /tf + /tf_static            TF (odom→base_link, static sensor frames)
  /clock                      rosgraph_msgs/Clock

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



def generate_launch_description():
    pkg_dir = get_package_share_directory('go2_robot_sdk')

    slam_config  = os.path.join(pkg_dir, 'config', 'mapper_params_online_async_sim.yaml')
    nav2_config  = os.path.join(pkg_dir, 'config', 'nav2_params_sim.yaml')
    joystick_config  = os.path.join(pkg_dir, 'config', 'joystick.yaml')
    twist_mux_config = os.path.join(pkg_dir, 'config', 'twist_mux.yaml')
    rviz_config  = os.path.join(pkg_dir, 'config', 'single_robot_conf_sim.rviz')

    # ------------------------------------------------------------------ #
    # Launch arguments — same surface as robot.launch.py for easy switching
    # ------------------------------------------------------------------ #
    launch_args = [
        DeclareLaunchArgument('rviz2',    default_value='true',  description='Launch RViz2'),
        DeclareLaunchArgument('nav2',     default_value='true',  description='Launch Nav2'),
        DeclareLaunchArgument('slam',     default_value='true',  description='Launch SLAM'),
        DeclareLaunchArgument('foxglove', default_value='false', description='Launch Foxglove Bridge'),
        DeclareLaunchArgument('joystick', default_value='true',  description='Launch joystick'),
        DeclareLaunchArgument('teleop',   default_value='true',  description='Launch teleoperation'),
        DeclareLaunchArgument('world',    default_value='cafe.world',
                              description='Gazebo world file name (go2_sim/worlds/)'),
        DeclareLaunchArgument(
            'enable_stt',
            default_value=os.getenv('ENABLE_STT', 'false'),
            description='Launch STT node',
        ),
        DeclareLaunchArgument(
            'enable_voice_cmd',
            default_value=os.getenv('ENABLE_VOICE_CMD', os.getenv('ENABLE_STT', 'false')),
            description='Launch voice command node — defaults to enable_stt value; set ENABLE_VOICE_CMD=false to run STT-only',
        ),
    ]

    # ------------------------------------------------------------------ #
    # Gazebo simulation — self-contained, no topic bridges needed here
    # ------------------------------------------------------------------ #
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('go2_sim'),
                'launch', 'go2_sim.launch.py',
            )
        ),
        launch_arguments={'world': LaunchConfiguration('world')}.items(),
    )

    # ------------------------------------------------------------------ #
    # Joystick + twist multiplexer
    # ------------------------------------------------------------------ #
    teleop_nodes = [
        Node(
            package='joy', executable='joy_node',
            condition=IfCondition(LaunchConfiguration('joystick')),
            parameters=[joystick_config],
        ),
        Node(
            package='teleop_twist_joy', executable='teleop_node',
            name='go2_teleop_node',
            condition=IfCondition(LaunchConfiguration('joystick')),
            parameters=[twist_mux_config],
            remappings=[('cmd_vel', 'cmd_vel_joy')],
        ),
        Node(
            package='twist_mux', executable='twist_mux',
            output='screen',
            condition=IfCondition(LaunchConfiguration('teleop')),
            parameters=[{'use_sim_time': True}, twist_mux_config],
        ),
    ]

    # ------------------------------------------------------------------ #
    # Visualization
    # ------------------------------------------------------------------ #
    rviz_node = Node(
        package='rviz2', executable='rviz2',
        condition=IfCondition(LaunchConfiguration('rviz2')),
        name='go2_rviz2', output='screen',
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
    # SLAM — reads /scan (provided by go2_sim at SDK root level)
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
    # Nav2 — reads /odom, /scan, /tf (all at SDK root level from go2_sim)
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

    # ------------------------------------------------------------------ #
    # Voice pipeline — STT + voice command router (simulation mode)
    # cmd_topic=/sim_cmd so commands reach go2_sim's sim_cmd_node, not hardware
    # ------------------------------------------------------------------ #
    voice_nodes = [
        Node(
            package='speech_processor',
            executable='stt_node',
            name='stt_node',
            condition=IfCondition(LaunchConfiguration('enable_stt')),
            parameters=[{
                'stt_provider':  os.getenv('STT_PROVIDER', 'openai'),
                'api_key': (
                    os.getenv('GEMINI_API_KEY', '') if os.getenv('STT_PROVIDER', 'openai') == 'gemini'
                    else os.getenv('OPENAI_API_KEY', '')
                ),
                'whisper_model': os.getenv('WHISPER_MODEL', 'base'),
                'device':        os.getenv('STT_DEVICE', 'cpu'),
                'compute_type':  'float16' if os.getenv('STT_DEVICE', 'cpu') == 'cuda' else 'int8',
                'language':      os.getenv('STT_LANGUAGE', 'en'),
                'use_sim_time':  True,
            }],
            output='screen',
        ),
        Node(
            package='speech_processor',
            executable='voice_cmd_node',
            name='voice_cmd_node',
            condition=IfCondition(LaunchConfiguration('enable_voice_cmd')),
            parameters=[{
                'cmd_topic':     '/sim_cmd',       # → go2_sim sim_cmd_node (not /webrtc_req)
                'nlu_provider':  os.getenv('NLU_PROVIDER', 'keyword'),
                'api_key': (
                    os.getenv('GEMINI_API_KEY', '') if os.getenv('NLU_PROVIDER', 'keyword') == 'gemini'
                    else os.getenv('ANTHROPIC_API_KEY', '') if os.getenv('NLU_PROVIDER', 'keyword') == 'claude'
                    else os.getenv('OPENAI_API_KEY', '')
                ),
                'move_duration': float(os.getenv('VOICE_MOVE_DURATION', '2.0')),
                'linear_speed':  float(os.getenv('VOICE_LINEAR_SPEED', '0.3')),
                'angular_speed': float(os.getenv('VOICE_ANGULAR_SPEED', '0.5')),
                'use_sim_time':  True,
            }],
            output='screen',
        ),
    ]

    return LaunchDescription(
        launch_args
        + [gazebo_launch]
        + teleop_nodes
        + [rviz_node, foxglove_launch, slam_launch, nav2_launch]
        + voice_nodes
    )
