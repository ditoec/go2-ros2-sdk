# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

"""
go2_sim.launch.py — self-contained Gazebo simulation for the Unitree GO2.

Starts Gazebo Harmonic, spawns the robot, wires up all sensors and
controllers, and publishes every topic at the SDK's standard root-level
names.  No topic relay is needed in simulation.launch.py.

Topic layout after this launch:
  /imu                        sensor_msgs/Imu          (from Gazebo IMU)
  /scan                       sensor_msgs/LaserScan    (from Gazebo LiDAR)
  /go2_camera/color/image_raw sensor_msgs/Image        (from Gazebo camera)
  /joint_states               sensor_msgs/JointState   (relayed from /go2/joint_states)
  /odom                       nav_msgs/Odometry        (from QuadrupedOdometryNode)
  /tf  + /tf_static           TF                       (robot_state_publisher + odom node)
  /clock                      rosgraph_msgs/Clock      (from Gazebo)

Control input:
  /cmd_vel_muxed → relayed → /go2/cmd_vel → cmd_vel_pub → /go2/robot_velocity
                                           → robot_controller_gazebo → joint commands
"""

import os
import xacro

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    RegisterEventHandler,
    SetEnvironmentVariable,
)
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    robot_name = 'go2'

    go2_sim_dir  = get_package_share_directory('go2_sim')
    go2_desc_dir = get_package_share_directory('go2_description')

    models_dir  = os.path.join(go2_sim_dir, 'models')
    bridge_file = os.path.join(go2_sim_dir, 'config', 'gz_bridge.yaml')
    xacro_file  = os.path.join(go2_desc_dir, 'xacro', 'robot.xacro')

    # Process xacro → URDF string (robot_name drives sensor topic namespacing)
    robot_desc = xacro.process_file(
        xacro_file, mappings={'robot_name': robot_name}
    ).toxml()

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    world        = LaunchConfiguration('world', default='cafe.world')

    # ------------------------------------------------------------------ #
    # 1. Gazebo Harmonic
    #    GZ_SIM_RESOURCE_PATH must be set before gz_sim starts so that
    #    model:// URIs in cafe.world resolve to our bundled models/.
    # ------------------------------------------------------------------ #
    set_gz_resource_path = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=models_dir,
    )

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('ros_gz_sim'),
                'launch', 'gz_sim.launch.py',
            )
        ),
        launch_arguments={
            'gz_args': [
                '-r -v3 ',
                PathJoinSubstitution([FindPackageShare('go2_sim'), 'worlds', world]),
            ],
            'on_exit_shutdown': 'true',
        }.items(),
    )

    # ------------------------------------------------------------------ #
    # 2a. Robot state publisher — global namespace
    #     Publishes /robot_description (used by spawn_entity below)
    #     and /tf + /tf_static (used by Nav2, SLAM, RViz).
    # ------------------------------------------------------------------ #
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='go2_robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_desc,
            'use_sim_time': use_sim_time,
        }],
    )

    # ------------------------------------------------------------------ #
    # 2b. Robot state publisher — /go2 namespace
    #     gz_ros2_control (embedded in Gazebo, namespace=/go2) subscribes
    #     to /go2/robot_description to initialise the hardware interface.
    #     Without this it blocks forever — the global RSP only publishes
    #     to /robot_description, not /go2/robot_description.
    # ------------------------------------------------------------------ #
    robot_state_publisher_ns = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='go2_robot_state_publisher_ns',
        namespace=robot_name,
        output='screen',
        parameters=[{
            'robot_description': robot_desc,
            'use_sim_time': use_sim_time,
        }],
    )

    # ------------------------------------------------------------------ #
    # 3. Spawn robot into Gazebo (reads URDF from global /robot_description)
    # ------------------------------------------------------------------ #
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        name='spawn_go2',
        arguments=[
            '-topic', '/robot_description',
            '-name', robot_name,
            '-z', '0.5',
        ],
        output='screen',
    )

    # ------------------------------------------------------------------ #
    # 4. ROS–Gazebo sensor bridges (see config/gz_bridge.yaml)
    #    Translates /go2/* Gazebo topics → SDK root topic names
    # ------------------------------------------------------------------ #
    ros_gz_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='go2_gz_bridge',
        arguments=['--ros-args', '-p', f'config_file:={bridge_file}'],
        output='screen',
    )

    # ------------------------------------------------------------------ #
    # 5–6. ros2_control spawners (must run after spawn_robot exits)
    # ------------------------------------------------------------------ #
    joint_state_broadcaster = Node(
        package='controller_manager',
        executable='spawner',
        namespace=robot_name,
        name='joint_state_broadcaster',
        arguments=['joint_state_broadcaster'],
        output='screen',
    )

    joint_group_controller = Node(
        package='controller_manager',
        executable='spawner',
        namespace=robot_name,
        name='joint_group_controller',
        arguments=['joint_group_controller'],
        output='screen',
    )

    # Spawn controllers only after the robot entity is created
    spawn_controllers = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=spawn_robot,
            on_exit=[joint_state_broadcaster, joint_group_controller],
        )
    )

    # ------------------------------------------------------------------ #
    # 7. cmd_vel_pub — /go2/cmd_vel (Twist) → /go2/robot_velocity (RobotVelocity)
    # ------------------------------------------------------------------ #
    cmd_vel_pub = Node(
        package='go2_sim',
        executable='cmd_vel_pub.py',
        name='cmd_vel_pub',
        namespace=robot_name,
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
    )

    # ------------------------------------------------------------------ #
    # 8. Gait controller — /go2/robot_velocity → joint position commands
    # ------------------------------------------------------------------ #
    robot_controller = Node(
        package='go2_sim',
        executable='robot_controller_gazebo.py',
        name='quadruped_controller',
        namespace=robot_name,
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
    )

    # ------------------------------------------------------------------ #
    # 9. Odometry node — global namespace → /odom + odom→base_link TF
    #
    # QuadrupedOdometryNode hardcodes relative subscription names designed
    # for a /robot1/ namespace. We run it globally (so TF goes to /tf and
    # odom goes to /odom), but need explicit remappings to reach the actual
    # /go2/* topics published by the gait controller and gz_bridge.
    #
    # Hardcoded relative → actual topic (via remapping):
    #   imu_plugin/out            → /imu          (gz_bridge output)
    #   robot_velocity            → /go2/robot_velocity   (cmd_vel_pub output)
    #   joint_group_controller/commands → /go2/joint_group_controller/commands
    #   foot_contact              → /go2/foot_contact
    # ------------------------------------------------------------------ #
    odom_node = Node(
        package='go2_sim',
        executable='QuadrupedOdometryNode.py',
        name='quadruped_odom',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'verbose': False,
            'publish_rate': 50,
            'open_loop': False,
            'has_imu_heading': True,
            'is_gazebo': True,
            'base_frame_id': 'base_link',
            'odom_frame_id': 'odom',
            'clock_topic': '/clock',
            'enable_odom_tf': True,
        }],
        remappings=[
            ('imu_plugin/out',                   '/imu'),
            ('robot_velocity',                   f'/{robot_name}/robot_velocity'),
            ('joint_group_controller/commands',  f'/{robot_name}/joint_group_controller/commands'),
            ('foot_contact',                     f'/{robot_name}/foot_contact'),
        ],
    )

    # ------------------------------------------------------------------ #
    # 10. Relay: /go2/joint_states → /joint_states
    # ------------------------------------------------------------------ #
    relay_joint_states = Node(
        package='topic_tools',
        executable='relay',
        name='relay_joint_states',
        arguments=[f'/{robot_name}/joint_states', '/joint_states'],
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen',
    )

    # ------------------------------------------------------------------ #
    # 11. Relay: /cmd_vel_muxed → /go2/cmd_vel  (SDK → sim)
    # ------------------------------------------------------------------ #
    relay_cmd_vel = Node(
        package='topic_tools',
        executable='relay',
        name='relay_cmd_vel',
        arguments=['/cmd_vel_muxed', f'/{robot_name}/cmd_vel'],
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen',
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time', default_value='true',
            description='Use Gazebo simulation clock',
        ),
        DeclareLaunchArgument(
            'world', default_value='cafe.world',
            description='World file name inside go2_sim/worlds/ (e.g. cafe.world or go2_empty.sdf)',
        ),
        set_gz_resource_path,
        gazebo,
        robot_state_publisher,
        robot_state_publisher_ns,
        spawn_robot,
        ros_gz_bridge,
        spawn_controllers,
        cmd_vel_pub,
        robot_controller,
        odom_node,
        relay_joint_states,
        relay_cmd_vel,
    ])
