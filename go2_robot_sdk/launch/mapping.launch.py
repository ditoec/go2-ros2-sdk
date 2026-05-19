# Mapping launch file - optimized for SLAM and map creation
# Usage: ros2 launch go2_robot_sdk mapping.launch.py

import os
from typing import List
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import FrontendLaunchDescriptionSource, PythonLaunchDescriptionSource


def generate_launch_description():
    """Generate launch description for Go2 mapping mode"""
    
    # Environment variables
    robot_token = os.getenv('ROBOT_TOKEN', '')
    robot_ip = os.getenv('ROBOT_IP', '')
    robot_ip_list = robot_ip.replace(" ", "").split(",") if robot_ip else []
    map_name = os.getenv('MAP_NAME', 'my_map')
    save_map = os.getenv('MAP_SAVE', 'true')
    conn_type = os.getenv('CONN_TYPE', 'webrtc')
    
    # Determine connection mode
    conn_mode = "single" if len(robot_ip_list) == 1 and conn_type != "cyclonedds" else "multi"
    
    # Package paths
    package_dir = get_package_share_directory('go2_robot_sdk')
    urdf_file = 'go2.urdf' if conn_mode == 'single' else 'multi_go2.urdf'
    rviz_config = 'single_robot_conf.rviz' if conn_mode == 'single' else 'multi_robot_conf.rviz'
    
    config_paths = {
        'joystick': os.path.join(package_dir, 'config', 'joystick.yaml'),
        'twist_mux': os.path.join(package_dir, 'config', 'twist_mux.yaml'),
        'slam': os.path.join(package_dir, 'config', 'mapper_params_online_async.yaml'),
        'rviz': os.path.join(package_dir, 'config', rviz_config),
        'urdf': os.path.join(package_dir, 'urdf', urdf_file),
    }
    
    print(f"🗺️  Go2 Mapping Mode:")
    print(f"   Robot IPs: {robot_ip_list}")
    print(f"   Connection: {conn_type} ({conn_mode})")
    print(f"   Map name: {map_name}")
    
    # Launch arguments
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    with_rviz = LaunchConfiguration('rviz', default='true')
    with_foxglove = LaunchConfiguration('foxglove', default='true')
    with_joystick = LaunchConfiguration('joystick', default='true')
    
    launch_args = [
        DeclareLaunchArgument('rviz', default_value='true', description='Launch RViz2'),
        DeclareLaunchArgument('foxglove', default_value='true', description='Launch Foxglove Bridge'),
        DeclareLaunchArgument('joystick', default_value='true', description='Launch joystick control'),
    ]
    
    # Load URDF
    with open(config_paths['urdf'], 'r') as file:
        robot_desc = file.read()
    
    # Core nodes
    core_nodes = [
        # Robot state publisher
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='go2_robot_state_publisher',
            output='screen',
            parameters=[{
                'use_sim_time': use_sim_time,
                'robot_description': robot_desc
            }],
        ),
        # Main robot driver
        Node(
            package='go2_robot_sdk',
            executable='go2_driver_node',
            name='go2_driver_node',
            output='screen',
            parameters=[{
                'robot_ip': robot_ip,
                'token': robot_token,
                'conn_type': conn_type
            }],
        ),
        # LiDAR processing node
        Node(
            package='lidar_processor_cpp',
            executable='lidar_to_pointcloud_node',
            name='lidar_to_pointcloud',
            remappings=[
                ('robot0/point_cloud2', 'point_cloud2'),
            ] if conn_mode == 'single' else [],
            parameters=[{
                'robot_ip_lst': robot_ip_list,
                'map_name': map_name,
                'map_save': save_map
            }],
        ),
        # Point cloud aggregator - maximized for full coverage
        Node(
            package='lidar_processor_cpp',
            executable='pointcloud_aggregator_node',
            name='pointcloud_aggregator',
            parameters=[{
                'max_range': 20.0,
                'min_range': 0.3,
                'height_filter_min': -1.0,
                'height_filter_max': 3.0,
                'downsample_rate': 1,
                'publish_rate': 20.0
            }],
        ),
        # PointCloud to LaserScan converter - maximum coverage
        Node(
            package='pointcloud_to_laserscan',
            executable='pointcloud_to_laserscan_node',
            name='go2_pointcloud_to_laserscan',
            remappings=[
                ('cloud_in', '/pointcloud/filtered'),
                ('scan', '/scan'),
            ],
            parameters=[{
                'target_frame': 'base_link',
                'max_height': 3.0,
                'min_height': -1.0,
                'angle_min': -3.14159,
                'angle_max': 3.14159,
                'angle_increment': 0.00872665,
                'scan_time': 0.1,
                'range_min': 0.3,
                'range_max': 20.0,
                'use_inf': True,
                'concurrency_level': 1,
            }],
            output='screen',
        ),
        # TTS Node — provider selected by TTS_PROVIDER env var (supertonic* | openai | elevenlabs | gemini)
        Node(
            package='speech_processor',
            executable='tts_node',
            name='tts_node',
            parameters=[{
                'api_key': (
                    os.getenv('ELEVENLABS_API_KEY', '') if os.getenv('TTS_PROVIDER', 'supertonic') == 'elevenlabs'
                    else os.getenv('GEMINI_API_KEY', '') if os.getenv('TTS_PROVIDER', 'supertonic') == 'gemini'
                    else os.getenv('OPENAI_API_KEY', '')
                ),
                'provider': os.getenv('TTS_PROVIDER', 'supertonic'),
                'voice_name': os.getenv('TTS_VOICE', 'F1'),
                'language': os.getenv('SUPERTONIC_LANG', 'en'),
                'supertonic_steps': int(os.getenv('SUPERTONIC_STEPS', '8')),
                'local_playback': False,
                'use_cache': True,
                'audio_quality': 'standard'
            }],
        ),
    ]

    # Teleop nodes
    teleop_nodes = [
        Node(
            package='joy',
            executable='joy_node',
            condition=IfCondition(with_joystick),
            parameters=[config_paths['joystick']]
        ),
        Node(
            package='teleop_twist_joy',
            executable='teleop_node',
            name='go2_teleop_node',
            condition=IfCondition(with_joystick),
            parameters=[config_paths['twist_mux']],
        ),
        Node(
            package='twist_mux',
            executable='twist_mux',
            output='screen',
            condition=IfCondition(with_joystick),
            parameters=[
                {'use_sim_time': use_sim_time},
                config_paths['twist_mux']
            ],
        ),
    ]
    
    # Visualization nodes
    viz_nodes = [
        Node(
            package='rviz2',
            executable='rviz2',
            condition=IfCondition(with_rviz),
            name='go2_rviz2',
            output='screen',
            arguments=['-d', config_paths['rviz']],
            parameters=[{'use_sim_time': False}]
        ),
    ]
    
    # Include launches
    foxglove_launch = os.path.join(
        get_package_share_directory('foxglove_bridge'),
        'launch', 'foxglove_bridge_launch.xml'
    )
    
    include_launches = [
        # Foxglove Bridge
        IncludeLaunchDescription(
            FrontendLaunchDescriptionSource(foxglove_launch),
            condition=IfCondition(with_foxglove),
        ),
        # SLAM Toolbox for mapping
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                os.path.join(get_package_share_directory('slam_toolbox'),
                            'launch', 'online_async_launch.py')
            ]),
            launch_arguments={
                'slam_params_file': config_paths['slam'],
                'use_sim_time': use_sim_time,
            }.items(),
        ),
    ]
    
    return LaunchDescription(
        launch_args +
        core_nodes +
        teleop_nodes +
        viz_nodes +
        include_launches
    )
