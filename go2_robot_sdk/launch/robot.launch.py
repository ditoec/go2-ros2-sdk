# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

import datetime
import os
import shlex
from typing import List
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch.actions import ExecuteProcess, IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import FrontendLaunchDescriptionSource, PythonLaunchDescriptionSource
from launch.substitutions import PythonExpression, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


# Topics captured by default when bag recording is enabled (ENABLE_BAG=true).
# Curated for debugging: robot state, commands, navigation and voice/perception
# *outputs* — deliberately excludes the heavy raw streams (/camera/image_raw,
# /point_cloud2, annotated images) so field bags stay small. Set BAG_TOPICS=-a
# to capture absolutely everything instead.
DEFAULT_BAG_TOPICS = [
    '/tf', '/tf_static',
    '/odom', '/go2_state', '/imu', '/joint_states',
    '/scan', '/map', '/plan',
    '/cmd_vel_out', '/cmd_vel_joy', '/cmd_vel_voice', '/cmd_vel_foxglove',
    '/webrtc_req',
    '/detected_objects',
    '/speech_text', '/tts', '/scene_description',
    '/diagnostics',
]


class Go2LaunchConfig:
    """Configuration container for Go2 robot launch parameters"""
    
    def __init__(self):
        # Environment variables
        self.robot_token = os.getenv('ROBOT_TOKEN', '')
        self.robot_ip = os.getenv('ROBOT_IP', '')
        self.robot_ip_list = self._parse_ip_list(self.robot_ip)
        self.map_name = os.getenv('MAP_NAME', '3d_map')
        self.save_map = os.getenv('MAP_SAVE', 'true')
        self.conn_type = os.getenv('CONN_TYPE', 'webrtc')
        
        # Derived configurations
        self.conn_mode = self._determine_connection_mode()
        self.rviz_config = self._get_rviz_config()
        self.urdf_file = self._get_urdf_file()
        
        # Package paths
        self.package_dir = get_package_share_directory('go2_robot_sdk')
        self.config_paths = self._get_config_paths()
        
        print(f"� Go2 Launch Configuration:")
        print(f"   Robot IPs: {self.robot_ip_list}")
        print(f"   Connection: {self.conn_type} ({self.conn_mode})")
        print(f"   URDF: {self.urdf_file}")
    
    def _parse_ip_list(self, robot_ip: str) -> List[str]:
        """Parse robot IP addresses from environment variable"""
        return robot_ip.replace(" ", "").split(",") if robot_ip else []
    
    def _determine_connection_mode(self) -> str:
        """Determine connection mode based on IP list and connection type"""
        # CycloneDDS's own native subscriptions are never robot-prefixed regardless --
        # this only controls the driver's own published/converted topic naming. <= 1
        # (not == 1) since ROBOT_IP unset parses to [] here, not [''] (see
        # _parse_ip_list) -- the common single-robot-onboard case must still resolve
        # to 'single', not fall through to 'multi' on an empty list.
        return "single" if len(self.robot_ip_list) <= 1 else "multi"
    
    def _get_rviz_config(self) -> str:
        """Get appropriate RViz configuration file"""
        if self.conn_type == 'cyclonedds':
            return "cyclonedx_config.rviz"
        elif self.conn_mode == 'single':
            return "single_robot_conf.rviz"
        else:
            return "multi_robot_conf.rviz"
    
    def _get_urdf_file(self) -> str:
        """Get appropriate URDF file"""
        return 'go2.urdf' if self.conn_mode == 'single' else 'multi_go2.urdf'
    
    def _get_config_paths(self) -> dict:
        """Get all configuration file paths"""
        return {
            'joystick': os.path.join(self.package_dir, 'config', 'joystick.yaml'),
            'twist_mux': os.path.join(self.package_dir, 'config', 'twist_mux.yaml'),
            'slam': os.path.join(self.package_dir, 'config', 'mapper_params_online_async.yaml'),
            'nav2': os.path.join(self.package_dir, 'config', 'nav2_params.yaml'),
            'rviz': os.path.join(self.package_dir, 'config', self.rviz_config),
            'urdf': os.path.join(self.package_dir, 'urdf', self.urdf_file),
        }


class Go2NodeFactory:
    """Factory for creating Go2 robot nodes"""
    
    def __init__(self, config: Go2LaunchConfig):
        self.config = config
    
    def create_launch_arguments(self) -> List[DeclareLaunchArgument]:
        """Create all launch arguments"""
        return [
            DeclareLaunchArgument(
                'rviz2', default_value=os.getenv('ENABLE_RVIZ', 'true'),
                description='Launch RViz2. RViz2 is a GUI visualization tool with no effect on '
                            'robot behavior -- on a resource-constrained Jetson it can consume a '
                            'large share of CPU (observed ~83% on an Orin NX) for a window nobody '
                            'is watching, starving latency-sensitive work like a persistent '
                            'openai_realtime WebSocket session. Set ENABLE_RVIZ=false when running '
                            'headless / onboard without an active VNC viewer.',
            ),
            DeclareLaunchArgument(
                'nav2', default_value=os.getenv('ENABLE_NAV2', 'false'),
                description='Launch Nav2. The full Nav2 stack (planner/controller/smoother/'
                            'bt_navigator/lifecycle_manager) is CPU/RAM-heavy -- on a '
                            'resource-constrained Jetson running other demanding workloads '
                            '(e.g. a local LLM) concurrently, it can starve them of both. Set '
                            'ENABLE_NAV2=true to enable (needed for nav_waypoint_node/patrol_node).',
            ),
            DeclareLaunchArgument(
                'slam', default_value=os.getenv('ENABLE_SLAM', 'false'),
                description='Launch SLAM Toolbox. Same resource-contention rationale as nav2 '
                            '-- set ENABLE_SLAM=true to enable (needed to build a map before '
                            'Nav2 waypoint navigation is usable).',
            ),
            DeclareLaunchArgument(
                'foxglove', default_value=os.getenv('ENABLE_FOXGLOVE', 'true'),
                description='Launch Foxglove Bridge'
            ),
            DeclareLaunchArgument('joystick', default_value='true', description='Launch joystick'),
            DeclareLaunchArgument('teleop', default_value='true', description='Launch teleoperation'),
            DeclareLaunchArgument(
                'enable_stt',
                default_value=os.getenv('ENABLE_STT', 'false'),
                description='Launch STT node (set STT_PROVIDER, STT_DEVICE, WHISPER_MODEL env vars to configure)',
            ),
            DeclareLaunchArgument(
                'enable_voice_cmd',
                # Unified providers (gemma_local, openai_realtime, gemini_live) handle NLU+TTS
                # internally — voice_cmd_node is not needed and defaults to disabled for them.
                default_value=str(
                    os.getenv('ENABLE_VOICE_CMD', os.getenv('ENABLE_STT', 'false')).lower() == 'true'
                    and os.getenv('STT_PROVIDER', 'faster_whisper')
                        not in ('gemma_local', 'openai_realtime', 'gemini_live')
                ).lower(),
                description='Launch voice command node. Auto-disabled for unified STT providers.',
            ),
            DeclareLaunchArgument(
                'mic_bridge',
                default_value=os.getenv('MIC_BRIDGE', 'true'),
                description='true (default) → mic_bridge_node (browser mic, no system audio needed). '
                            'false → stt_node (requires local /dev/snd or working PulseAudio).',
            ),
            DeclareLaunchArgument(
                'cam_bridge',
                default_value=os.getenv('CAM_BRIDGE', 'false'),
                description='true → cam_bridge_node: stream the host browser webcam to /camera/image_raw '
                            '(http://localhost:8891). Useful on Windows when no robot camera is connected. '
                            'face_recognition_node + yolo_detector subscribe to /camera/image_raw unchanged.',
            ),
            DeclareLaunchArgument(
                'enable_mic_diagnostic',
                default_value=os.getenv('ENABLE_MIC_DIAGNOSTIC', 'false'),
                description='true → mic_diagnostic_node: Record/Stop web UI (http://localhost:8893) to '
                            'capture /robot_audio and play it back in-browser, for judging robot-mic '
                            'audio quality without SSH. Needs STT_SOURCE=robot to have anything to record.',
            ),
            DeclareLaunchArgument(
                'enable_gemma_vision',
                default_value=os.getenv('ENABLE_GEMMA_VISION', 'false'),
                description='Launch gemma_vision_node (Gemma 4 E4B scene description via Ollama). '
                            'Replaces yolo_detector in the Windows GPU profile.',
            ),
            DeclareLaunchArgument(
                'enable_face_recognition',
                default_value=os.getenv('ENABLE_FACE', 'false'),
                description='Launch face_recognition_node (InsightFace SCRFD + ArcFace, Modul 4.2). '
                            'Publishes /recognized_faces + /recognized_face_names; voice_cmd_node '
                            'greets recognized people by name (Modul 4.4).',
            ),
            DeclareLaunchArgument(
                'enable_yolo',
                default_value=os.getenv(
                    'ENABLE_YOLO',
                    'true' if os.getenv('ENABLE_FOLLOW', 'false').lower() == 'true' else 'false',
                ),
                description='Launch yolo_detector_node (/detected_objects). '
                            'Auto-enabled when ENABLE_FOLLOW=true.',
            ),
            DeclareLaunchArgument(
                'enable_follow',
                default_value=os.getenv('ENABLE_FOLLOW', 'false'),
                description='Launch follow_me_node (Modul 4.3) — tracks the nearest person '
                            'detected by YOLO and publishes /cmd_vel_follow (twist_mux priority 6). '
                            'Voice and joystick always override. Requires ENABLE_YOLO=true '
                            '(auto-enabled). Toggle at runtime via /follow_enable (Bool).',
            ),
            DeclareLaunchArgument(
                'enable_nav_waypoint',
                default_value=os.getenv('ENABLE_NAV_WAYPOINT', 'false'),
                description='Launch nav_waypoint_node (Modul 5.2/5.3) — listens on /navigate_to_room '
                            '(String) and sends NavigateToPose goals to Nav2. '
                            'Requires Nav2 running (enable_nav2=true) and a saved SLAM map. '
                            'Waypoints defined in WAYPOINTS_FILE (default config/waypoints.yaml).',
            ),
            DeclareLaunchArgument(
                'enable_behavior_coordinator',
                default_value=os.getenv('ENABLE_BEHAVIOR_COORDINATOR', 'false'),
                description='Launch behavior_coordinator_node — observes /follow_enable, '
                            '/navigation_status, /cmd_vel_voice, /approach_status, /patrol_status '
                            'and publishes /behavior_mode '
                            '(IDLE/VOICE_MOVE/FOLLOWING/NAVIGATING/APPROACHING/PATROL) '
                            'with TRANSIENT_LOCAL QoS.',
            ),
            DeclareLaunchArgument(
                'enable_patrol',
                default_value=os.getenv('ENABLE_PATROL', 'false'),
                description='Launch patrol_node (Modul 2.1) — cycles through named waypoints '
                            'indefinitely on /patrol_enable=true. Shares WAYPOINTS_FILE with '
                            'nav_waypoint_node. PATROL_ROUTE: comma-separated subset of keys '
                            '(empty=all). Requires Nav2 running (enable_nav2=true).',
            ),
            DeclareLaunchArgument(
                'enable_approach_object',
                default_value=os.getenv('ENABLE_APPROACH_OBJECT', 'false'),
                description='Launch approach_object_node (Modul 2.1/2.2) — one-shot visual servo '
                            'to a YOLO-detected object via /approach_target (String class name). '
                            'Requires ENABLE_YOLO=true. Publishes /cmd_vel_follow '
                            '(priority 6, same as follow_me_node).',
            ),
            DeclareLaunchArgument(
                'bag_record',
                default_value=os.getenv('ENABLE_BAG', 'false'),
                description='Record a timestamped rosbag2 session to BAG_DIR for debugging/replay. '
                            'BAG_TOPICS=-a captures camera+LiDAR too; default is a curated '
                            'lightweight set. BAG_STORAGE overrides the storage backend '
                            '(default: rosbag2 default, sqlite3 on Humble).',
            ),
            DeclareLaunchArgument(
                'enable_webrtc_camera',
                default_value=os.getenv('ENABLE_WEBRTC_CAMERA', 'false'),
                description='CONN_TYPE=cyclonedds only: also open a WebRTC session (needs '
                            'ROBOT_IP set to the robot\'s internal IP) purely for camera video '
                            '(/camera/image_raw) -- commands/state stay CycloneDDS-owned. '
                            'Requires closing the Unitree mobile app first (one WebRTC client '
                            'at a time, robot-side limit).',
            ),
        ]
    
    def create_robot_state_nodes(self) -> List[Node]:
        """Create robot state publisher nodes"""
        nodes = []
        use_sim_time = LaunchConfiguration('use_sim_time', default='false')
        
        if self.config.conn_mode == 'single':
            # Single robot configuration
            robot_desc = self._load_urdf_content(self.config.config_paths['urdf'])
            
            nodes.extend([
                Node(
                    package='robot_state_publisher',
                    executable='robot_state_publisher',
                    name='go2_robot_state_publisher',
                    output='screen',
                    parameters=[{
                        'use_sim_time': use_sim_time,
                        'robot_description': robot_desc
                    }],
                    arguments=[self.config.config_paths['urdf']]
                ),
                self._create_pointcloud_to_laserscan_node()
            ])
        else:
            # Multi-robot configuration
            base_urdf = self._load_urdf_content(self.config.config_paths['urdf'])
            
            for i, _ in enumerate(self.config.robot_ip_list):
                robot_desc = base_urdf.format(robot_num=f"robot{i}")
                
                nodes.extend([
                    Node(
                        package='robot_state_publisher',
                        executable='robot_state_publisher',
                        name='go2_robot_state_publisher',
                        output='screen',
                        namespace=f"robot{i}",
                        parameters=[{
                            'use_sim_time': use_sim_time,
                            'robot_description': robot_desc
                        }],
                        arguments=[self.config.config_paths['urdf']]
                    ),
                    self._create_pointcloud_to_laserscan_node(f"robot{i}")
                ])
        
        return nodes
    
    def _load_urdf_content(self, urdf_path: str) -> str:
        """Load URDF file content"""
        with open(urdf_path, 'r') as file:
            return file.read()
    
    def _create_pointcloud_to_laserscan_node(self, namespace: str = None) -> Node:
        """Create pointcloud to laserscan conversion node"""
        if namespace:
            # Multi-robot setup
            return Node(
                package='pointcloud_to_laserscan',
                executable='pointcloud_to_laserscan_node',
                name=f'{namespace}_pointcloud_to_laserscan',
                remappings=[
                    ('cloud_in', f'{namespace}/point_cloud2'),
                    ('scan', f'{namespace}/scan'),
                ],
                parameters=[{
                    'target_frame': f'{namespace}/base_link',
                    'max_height': 0.1
                }],
                output='screen',
            )
        else:
            # Single robot setup
            return Node(
                package='pointcloud_to_laserscan',
                executable='pointcloud_to_laserscan_node',
                name='go2_pointcloud_to_laserscan',
                remappings=[
                    ('cloud_in', 'point_cloud2'),
                    ('scan', 'scan'),
                ],
                parameters=[{
                    'target_frame': 'base_link',
                    'max_height': 0.5
                }],
                output='screen',
            )
    
    def create_core_nodes(self) -> List[Node]:
        """Create core Go2 robot nodes"""
        _stt_on     = LaunchConfiguration('enable_stt')
        _use_bridge = LaunchConfiguration('mic_bridge')
        _cond_bridge = IfCondition(PythonExpression(
            ["'", _stt_on, "' == 'true' and '", _use_bridge, "' == 'true'"]
        ))
        _cond_local  = IfCondition(PythonExpression(
            ["'", _stt_on, "' == 'true' and '", _use_bridge, "' != 'true'"]
        ))
        # Single master language knob (en | id) — drives STT, NLU and TTS.
        # Command output always stays English (CMD_MAP keys).
        _voice_lang = os.getenv('VOICE_LANG', 'en')
        # Audio source for STT: "mic" (local sounddevice) or "robot" (the GO2's
        # onboard mic, captured from the WebRTC audio track and republished on
        # /robot_audio by the driver). "robot" requires CONN_TYPE=webrtc and
        # MIC_BRIDGE=false (so stt_node — not the browser bridge — runs).
        # auto* -> prefer a Bluetooth headset mic, then a USB mic on the Jetson,
        # falling back to the robot's own (noisy) mic when neither is connected.
        # mic   -> always the local sounddevice input.
        # robot -> always /robot_audio.
        _stt_source = os.getenv('STT_SOURCE', 'auto')
        _robot_audio = (_stt_source == 'robot')
        # Knowledge-base RAG (Modul 3.2) — ground conversational answers on the
        # client's venue knowledge. KB_PATH overrides the default, which points at
        # the bundled sample venue (KB_VENUE, default museum_demo) under the
        # installed speech_processor share dir. Replace that folder with the real
        # venue's facts for production. Needs an LLM NLU_PROVIDER.
        _kb_enabled = os.getenv('ENABLE_KB', 'false').lower() == 'true'
        _kb_path = os.getenv('KB_PATH', '')
        if _kb_enabled and not _kb_path:
            try:
                _kb_path = os.path.join(
                    get_package_share_directory('speech_processor'),
                    'knowledge', os.getenv('KB_VENUE', 'museum_demo'),
                )
            except Exception:
                _kb_path = ''
        _stt_params = {
            'stt_provider':  os.getenv('STT_PROVIDER', 'faster_whisper'),
            'api_key': (
                os.getenv('GEMINI_API_KEY', '') if os.getenv('STT_PROVIDER', '') == 'gemini'
                else os.getenv('OPENAI_API_KEY', '')
            ),
            'whisper_model': os.getenv('WHISPER_MODEL', 'base'),
            'device':        os.getenv('STT_DEVICE', 'cpu'),
            'compute_type':  'float16' if os.getenv('STT_DEVICE', 'cpu') == 'cuda' else 'int8',
            'language':      _voice_lang,
            'llama_cpp_host':    os.getenv('LLAMA_CPP_HOST', 'http://llama_cpp:8080'),
            'gemma_model':       os.getenv('GEMMA_MODEL', 'gemma'),
            'wake_word':         os.getenv('WAKE_WORD', 'doggo'),
            'vad_noise_multiplier': float(os.getenv('VAD_NOISE_MULTIPLIER', '2.5')),
            'vad_absolute_floor':   float(os.getenv('VAD_ABSOLUTE_FLOOR', '0.003')),
            'vad_noise_ema_alpha':  float(os.getenv('VAD_NOISE_EMA_ALPHA', '0.05')),
            'highpass_cutoff_hz':   float(os.getenv('STT_HIGHPASS_CUTOFF_HZ', '150.0')),
            'silence_duration':  float(os.getenv('VAD_SILENCE_DURATION', '0.4')),
            # Unified dispatch params (used when STT_PROVIDER is a unified provider)
            'cmd_topic':         '/webrtc_req',
            'move_duration':     float(os.getenv('VOICE_MOVE_DURATION', '2.0')),
            'linear_speed':      float(os.getenv('VOICE_LINEAR_SPEED', '0.3')),
            'angular_speed':     float(os.getenv('VOICE_ANGULAR_SPEED', '0.5')),
        }
        return [
            # Main robot driver (clean architecture)
            Node(
                package='go2_robot_sdk',
                executable='go2_driver_node',
                name='go2_driver_node',
                output='screen',
                parameters=[{
                    'robot_ip': self.config.robot_ip,
                    'token': self.config.robot_token,
                    'conn_type': self.config.conn_type,
                    'enable_audio': _robot_audio,
                    'enable_webrtc_camera': LaunchConfiguration('enable_webrtc_camera'),
                }],
            ),
            # LiDAR processing node (new separate package)
            Node(
                package='lidar_processor',
                executable='lidar_to_pointcloud',
                name='lidar_to_pointcloud',
                parameters=[{
                    'robot_ip_lst': self.config.robot_ip_list or [''],
                    'map_name': self.config.map_name,
                    'map_save': self.config.save_map
                }],
            ),
            # Advanced point cloud aggregator
            Node(
                package='lidar_processor',
                executable='pointcloud_aggregator',
                name='pointcloud_aggregator',
                parameters=[{
                    'max_range': 20.0,
                    'min_range': 0.1,
                    'height_filter_min': -2.0,
                    'height_filter_max': 3.0,
                    'downsample_rate': 5,
                    'publish_rate': 10.0
                }],
            ),
            # TTS Node — provider selected by TTS_PROVIDER env var (supertonic* | piper | openai | elevenlabs | gemini)
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
                    'language': os.getenv('SUPERTONIC_LANG') or _voice_lang,
                    'supertonic_steps': int(os.getenv('SUPERTONIC_STEPS', '8')),
                    'local_playback': False,
                    # Speak through a connected Bluetooth speaker when one is
                    # present, otherwise fall back to the robot's own speaker.
                    'bluetooth_playback': os.getenv('TTS_BLUETOOTH', 'true').lower() == 'true',
                    'bluetooth_sink_pattern': os.getenv('TTS_BLUETOOTH_SINK', 'bluez_sink'),
                    'bluetooth_probe_interval': float(os.getenv('TTS_BLUETOOTH_PROBE_SEC', '5.0')),
                    'use_cache': True,
                    'audio_quality': 'standard',
                    'chunk_size': int(os.getenv('TTS_CHUNK_SIZE', '32768')),
                }],
            ),
            # Mic bridge — browser-based mic relay; default when ENABLE_STT=true.
            # Open http://localhost:8888 in the host browser to stream the mic.
            # Switch to stt_node with MIC_BRIDGE=false (or mic_bridge:=false at launch).
            Node(
                package='speech_processor',
                executable='mic_bridge_node',
                name='mic_bridge_node',
                condition=_cond_bridge,
                parameters=[{
                    'http_port': 8888, 'ws_port': 8889,
                    'greet_cooldown_sec': float(os.getenv('GREET_COOLDOWN_SEC', '60')),
                    'face_context_ttl':   float(os.getenv('FACE_CONTEXT_TTL', '30')),
                    # Capture a Bluetooth/USB mic attached to this machine. The
                    # unified backends (openai_realtime / gemini_live / gemma_local)
                    # only run in this node, so without this they are limited to the
                    # browser bridge or the robot's own noisy mic.
                    'local_mic': _stt_source in ('auto', 'mic'),
                    'pulse_source_priority': os.getenv('STT_SOURCE_PRIORITY', 'bluez_source,usb'),
                    'source_probe_interval': float(os.getenv('STT_SOURCE_PROBE_SEC', '10.0')),
                    # Speak the reply through a local speaker as the model
                    # generates it (openai_realtime only) instead of waiting for
                    # the whole answer. Falls back to the robot speaker when no
                    # matching sink is connected.
                    'stream_audio': os.getenv('STREAM_AUDIO', 'true').lower() == 'true',
                    'stream_sink_pattern': os.getenv('STREAM_SINK_PATTERN', 'bluez_sink'),
                    **_stt_params,
                }],
                output='screen',
            ),
            # STT Node — only when MIC_BRIDGE=false; requires /dev/snd or working PulseAudio.
            Node(
                package='speech_processor',
                executable='stt_node',
                name='stt_node',
                condition=_cond_local,
                parameters=[{
                    **_stt_params,
                    'audio_source': (
                        'topic' if _robot_audio
                        else 'mic' if _stt_source == 'mic'
                        else 'auto'
                    ),
                    'audio_topic': '/robot_audio',
                    'pulse_source_priority': os.getenv('STT_SOURCE_PRIORITY', 'bluez_source,usb'),
                    'source_probe_interval': float(os.getenv('STT_SOURCE_PROBE_SEC', '10.0')),
                }],
                output='screen',
            ),
            # Voice Command Node — translates /speech_text → /webrtc_req + /cmd_vel_voice
            # Requires stt_node running (enable_stt=true).
            # NLU_PROVIDER=keyword (offline) | openai | gemini | claude | gemma_local
            Node(
                package='speech_processor',
                executable='voice_cmd_node',
                name='voice_cmd_node',
                condition=IfCondition(LaunchConfiguration('enable_voice_cmd')),
                parameters=[{
                    'cmd_topic':      '/webrtc_req',
                    'nlu_provider':   os.getenv('NLU_PROVIDER', 'keyword'),
                    'api_key': (
                        os.getenv('GEMINI_API_KEY', '') if os.getenv('NLU_PROVIDER', 'keyword') == 'gemini'
                        else os.getenv('ANTHROPIC_API_KEY', '') if os.getenv('NLU_PROVIDER', 'keyword') == 'claude'
                        else os.getenv('OPENAI_API_KEY', '')
                    ),
                    'llama_cpp_host':    os.getenv('LLAMA_CPP_HOST', 'http://llama_cpp:8080'),
                    'gemma_model':       os.getenv('GEMMA_MODEL', 'gemma'),
                    'language':          _voice_lang,
                    'move_duration':     float(os.getenv('VOICE_MOVE_DURATION', '2.0')),
                    'linear_speed':      float(os.getenv('VOICE_LINEAR_SPEED', '0.3')),
                    'angular_speed':     float(os.getenv('VOICE_ANGULAR_SPEED', '0.5')),
                    'enable_web_search': os.getenv('ENABLE_WEB_SEARCH', 'true').lower() == 'true',
                    # Knowledge-base RAG (Modul 3.2)
                    'enable_kb':         _kb_enabled,
                    'kb_path':           _kb_path,
                    'kb_embed_provider': os.getenv('KB_EMBED_PROVIDER', 'local'),
                    'kb_model':          os.getenv('KB_MODEL', 'intfloat/multilingual-e5-small'),
                    'kb_top_k':          int(os.getenv('KB_TOP_K', '3')),
                    'kb_min_score':      float(os.getenv('KB_MIN_SCORE', '0.0')),
                    # Multi-turn conversation memory (Modul 3.4)
                    'enable_conv_memory':    os.getenv('ENABLE_CONV_MEMORY', 'true').lower() == 'true',
                    'conv_history_turns':    int(os.getenv('CONV_HISTORY_TURNS', '3')),
                    'conv_history_idle_sec': float(os.getenv('CONV_HISTORY_IDLE_SEC', '60')),
                    # Visual feedback (Modul 4.4): face greeting + scene description grounding
                    'face_context_ttl':      float(os.getenv('FACE_CONTEXT_TTL', '30')),
                    'scene_context_ttl':     float(os.getenv('SCENE_CONTEXT_TTL', '10')),
                    'greet_cooldown_sec':    float(os.getenv('GREET_COOLDOWN_SEC', '60')),
                }],
                output='screen',
            ),
            # Gemma Vision Node — Gemma 4 E4B scene description via llama.cpp sidecar.
            # Replaces yolo_detector_node in the Windows GPU profile.
            # Enabled with ENABLE_GEMMA_VISION=true; publishes /scene_description and
            # /gemma_annotated_image instead of /detected_objects and /annotated_image.
            Node(
                package='speech_processor',
                executable='gemma_vision_node',
                name='gemma_vision_node',
                condition=IfCondition(LaunchConfiguration('enable_gemma_vision')),
                parameters=[{
                    'llama_cpp_host': os.getenv('LLAMA_CPP_HOST', 'http://llama_cpp:8080'),
                    'model':          os.getenv('GEMMA_MODEL', 'gemma'),
                    'inference_rate': float(os.getenv('GEMMA_VISION_RATE', '0.5')),
                }],
                output='screen',
            ),
            # Face Recognition Node — InsightFace SCRFD + ArcFace (Modul 4.2 / 4.4).
            # Enabled with ENABLE_FACE=true; publishes /recognized_faces,
            # /recognized_face_names (consumed by voice_cmd_node for greetings), and
            # /face_annotated_image. Recognition only — the DB is populated out-of-band
            # (web enroller writes face_db/<Name>/*.jpg); ping /reload_faces to re-scan.
            Node(
                package='speech_processor',
                executable='face_recognition_node',
                name='face_recognition_node',
                condition=IfCondition(LaunchConfiguration('enable_face_recognition')),
                parameters=[{
                    'face_device':       os.getenv('FACE_DEVICE', 'cpu'),
                    'face_model_pack':   os.getenv('FACE_MODEL_PACK', 'buffalo_sc'),
                    'face_db_path':      os.getenv('FACE_DB_PATH', './face_db'),
                    'face_threshold':    float(os.getenv('FACE_THRESHOLD', '0.35')),
                    'inference_rate':    float(os.getenv('FACE_RECOGNITION_RATE', '2.0')),
                    'camera_topic':      os.getenv('CAMERA_TOPIC', '/camera/image_raw'),
                    'rebuild_on_start':  os.getenv('FACE_REBUILD_ON_START', 'true').lower() == 'true',
                }],
                output='screen',
            ),
            # Face Enrollment UI — browser-based enrollment + threshold tuning (Modul 4.2).
            # http://localhost:8890 — same host as mic_bridge (8888), different page.
            # Writes face_db/<Name>/<idx>.jpg, publishes /reload_faces + /face_threshold.
            Node(
                package='speech_processor',
                executable='face_enrollment_node',
                name='face_enrollment_node',
                condition=IfCondition(LaunchConfiguration('enable_face_recognition')),
                parameters=[{
                    'http_port':          int(os.getenv('FACE_ENROLL_PORT', '8890')),
                    'face_db_path':       os.getenv('FACE_DB_PATH', './face_db'),
                    'default_threshold':  float(os.getenv('FACE_THRESHOLD', '0.35')),
                }],
                output='screen',
            ),
            # Camera Bridge — streams host browser webcam → /camera/image_raw (Windows).
            # Does for video what mic_bridge_node does for audio: on Windows (Docker Desktop +
            # WSL2), the host webcam is inaccessible from inside the container; cam_bridge_node
            # serves http://localhost:8891 — open it, click Connect, click Start Streaming.
            # face_recognition_node + yolo_detector subscribe to /camera/image_raw unchanged.
            # CAM_BRIDGE=true activates this; on Windows GPU compose it is true by default.
            Node(
                package='speech_processor',
                executable='cam_bridge_node',
                name='cam_bridge_node',
                condition=IfCondition(LaunchConfiguration('cam_bridge')),
                parameters=[{
                    'http_port':   int(os.getenv('CAM_BRIDGE_HTTP_PORT', '8891')),
                    'ws_port':     int(os.getenv('CAM_BRIDGE_WS_PORT', '8892')),
                    'image_topic': os.getenv('CAM_BRIDGE_TOPIC', '/camera/image_raw'),
                    'frame_id':    os.getenv('CAM_BRIDGE_FRAME_ID', 'camera_link'),
                }],
                output='screen',
            ),
            # Mic Diagnostic — Record/Stop web UI to capture /robot_audio and play it
            # back in-browser (http://localhost:8893). Purely observational: only
            # buffers audio while a capture is active, publishes nothing, can't
            # interfere with the STT pipeline. Needs STT_SOURCE=robot to have
            # anything to record from.
            Node(
                package='speech_processor',
                executable='mic_diagnostic_node',
                name='mic_diagnostic_node',
                condition=IfCondition(LaunchConfiguration('enable_mic_diagnostic')),
                parameters=[{
                    'http_port':     int(os.getenv('MIC_DIAGNOSTIC_HTTP_PORT', '8893')),
                    'ws_port':       int(os.getenv('MIC_DIAGNOSTIC_WS_PORT', '8894')),
                    'audio_topic':   os.getenv('MIC_DIAGNOSTIC_TOPIC', '/robot_audio'),
                    'sample_rate':   int(os.getenv('MIC_DIAGNOSTIC_SAMPLE_RATE', '16000')),
                    'max_capture_s': float(os.getenv('MIC_DIAGNOSTIC_MAX_CAPTURE_S', '60.0')),
                }],
                output='screen',
            ),
            Node(
                package='yolo_detector',
                executable='yolo_detector_node',
                name='yolo_detector_node',
                condition=IfCondition(LaunchConfiguration('enable_yolo')),
                parameters=[{
                    'model':               os.getenv('YOLO_MODEL', 'yolo11n.pt'),
                    'device':              os.getenv('YOLO_DEVICE', 'cpu'),
                    'detection_threshold': float(os.getenv('YOLO_THRESHOLD', '0.5')),
                }],
                output='screen',
            ),
            Node(
                package='speech_processor',
                executable='follow_me_node',
                name='follow_me_node',
                condition=IfCondition(LaunchConfiguration('enable_follow')),
                parameters=[{
                    'linear_speed':      float(os.getenv('FOLLOW_LINEAR_SPEED', '0.2')),
                    'angular_kp':        float(os.getenv('FOLLOW_ANGULAR_KP', '1.0')),
                    'max_angular_speed': float(os.getenv('FOLLOW_MAX_ANGULAR', '0.8')),
                    'target_area':       float(os.getenv('FOLLOW_TARGET_AREA', '0.10')),
                    'area_deadband':     float(os.getenv('FOLLOW_AREA_DEADBAND', '0.03')),
                    'min_confidence':    float(os.getenv('FOLLOW_MIN_CONFIDENCE', '0.5')),
                    'lost_timeout':      float(os.getenv('FOLLOW_LOST_TIMEOUT', '1.0')),
                    'publish_rate':      float(os.getenv('FOLLOW_PUBLISH_RATE', '10.0')),
                }],
                output='screen',
            ),
            Node(
                package='speech_processor',
                executable='nav_waypoint_node',
                name='nav_waypoint_node',
                condition=IfCondition(LaunchConfiguration('enable_nav_waypoint')),
                parameters=[{
                    'waypoints_file': os.getenv(
                        'WAYPOINTS_FILE',
                        os.path.join(
                            get_package_share_directory('go2_robot_sdk'),
                            'config', 'waypoints.yaml',
                        ),
                    ),
                    'nav_timeout': float(os.getenv('NAV_TIMEOUT', '120.0')),
                }],
                output='screen',
            ),
            Node(
                package='speech_processor',
                executable='behavior_coordinator_node',
                name='behavior_coordinator',
                condition=IfCondition(LaunchConfiguration('enable_behavior_coordinator')),
                parameters=[{
                    'vel_idle_timeout': float(os.getenv('BEHAVIOR_VEL_IDLE', '0.6')),
                }],
                output='screen',
            ),
            Node(
                package='speech_processor',
                executable='patrol_node',
                name='patrol_node',
                condition=IfCondition(LaunchConfiguration('enable_patrol')),
                parameters=[{
                    'waypoints_file': os.getenv(
                        'WAYPOINTS_FILE',
                        os.path.join(
                            get_package_share_directory('go2_robot_sdk'),
                            'config', 'waypoints.yaml',
                        ),
                    ),
                    'patrol_route': os.getenv('PATROL_ROUTE', ''),
                    'nav_timeout': float(os.getenv('NAV_TIMEOUT', '120.0')),
                    'skip_on_failure': os.getenv('PATROL_SKIP_ON_FAILURE', 'true').lower() == 'true',
                }],
                output='screen',
            ),
            Node(
                package='speech_processor',
                executable='approach_object_node',
                name='approach_object_node',
                condition=IfCondition(LaunchConfiguration('enable_approach_object')),
                parameters=[{
                    'linear_speed': float(os.getenv('APPROACH_LINEAR_SPEED', '0.25')),
                    'angular_kp': float(os.getenv('APPROACH_ANGULAR_KP', '1.0')),
                    'max_angular_speed': float(os.getenv('APPROACH_MAX_ANGULAR', '0.8')),
                    'target_area': float(os.getenv('APPROACH_TARGET_AREA', '0.12')),
                    'lost_timeout': float(os.getenv('APPROACH_LOST_TIMEOUT', '2.0')),
                }],
                output='screen',
            ),
        ]

    def create_teleop_nodes(self) -> List[Node]:
        """Create teleoperation and joystick nodes"""
        use_sim_time = LaunchConfiguration('use_sim_time', default='false')
        with_joystick = LaunchConfiguration('joystick', default='true')
        with_teleop = LaunchConfiguration('teleop', default='true')
        
        return [
            # Joystick node
            Node(
                package='joy',
                executable='joy_node',
                condition=IfCondition(with_joystick),
                parameters=[self.config.config_paths['joystick']]
            ),
            # Teleop twist joy node
            Node(
                package='teleop_twist_joy',
                executable='teleop_node',
                name='go2_teleop_node',
                condition=IfCondition(with_joystick),
                parameters=[self.config.config_paths['twist_mux']],
                remappings=[('cmd_vel', 'cmd_vel_joy')],
            ),
            # Twist multiplexer
            Node(
                package='twist_mux',
                executable='twist_mux',
                output='screen',
                condition=IfCondition(with_teleop),
                parameters=[
                    {'use_sim_time': use_sim_time},
                    self.config.config_paths['twist_mux']
                ],
            ),
        ]
    
    def create_visualization_nodes(self) -> List[Node]:
        """Create visualization nodes (RViz, Foxglove, rqt_graph)"""
        with_rviz2 = LaunchConfiguration('rviz2', default='true')

        return [
            # RViz2
            Node(
                package='rviz2',
                executable='rviz2',
                condition=IfCondition(with_rviz2),
                name='go2_rviz2',
                output='screen',
                arguments=['-d', self.config.config_paths['rviz']],
                parameters=[{'use_sim_time': False}]
            ),
            # rqt_graph — live node/topic graph; shares the rviz2 condition
            Node(
                package='rqt_graph',
                executable='rqt_graph',
                name='rqt_graph',
                condition=IfCondition(with_rviz2),
                output='screen',
            ),
        ]
    
    def create_include_launches(self) -> List[IncludeLaunchDescription]:
        """Create included launch descriptions"""
        use_sim_time = LaunchConfiguration('use_sim_time', default='false')
        with_foxglove = LaunchConfiguration('foxglove', default='true')
        with_slam = LaunchConfiguration('slam', default='true')
        with_nav2 = LaunchConfiguration('nav2', default='true')

        # FindPackageShare is a launch-time substitution, resolved only when the
        # IncludeLaunchDescription actually runs -- unlike the previous eager
        # get_package_share_directory() calls (which ran at Python construction
        # time regardless of the IfCondition below), this means a disabled
        # feature never triggers a PackageNotFoundError even if the package
        # backing it isn't installed.
        return [
            # Foxglove Bridge
            IncludeLaunchDescription(
                FrontendLaunchDescriptionSource(
                    PathJoinSubstitution([
                        FindPackageShare('foxglove_bridge'),
                        'launch', 'foxglove_bridge_launch.xml'
                    ])
                ),
                condition=IfCondition(with_foxglove),
            ),
            # SLAM Toolbox
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution([
                        FindPackageShare('slam_toolbox'),
                        'launch', 'online_async_launch.py'
                    ])
                ),
                condition=IfCondition(with_slam),
                launch_arguments={
                    'slam_params_file': self.config.config_paths['slam'],
                    'use_sim_time': use_sim_time,
                }.items(),
            ),
            # Nav2
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution([
                        FindPackageShare('nav2_bringup'),
                        'launch', 'navigation_launch.py'
                    ])
                ),
                condition=IfCondition(with_nav2),
                launch_arguments={
                    'params_file': self.config.config_paths['nav2'],
                    'use_sim_time': use_sim_time,
                }.items(),
            ),
        ]

    def create_bag_recorder(self) -> List[ExecuteProcess]:
        """Create the rosbag2 session recorder (A4 — debugging log capture).

        Enabled with ENABLE_BAG=true (or bag_record:=true). Writes a timestamped
        bag under BAG_DIR so each run is a self-contained, replayable session —
        open it in Foxglove or `ros2 bag play`. In Docker, BAG_DIR is mounted to
        the host so sessions survive container restarts.

        Topic selection (BAG_TOPICS):
          unset      → curated debugging set (DEFAULT_BAG_TOPICS)
          "-a"       → record everything (incl. camera + point cloud)
          "/a /b"    → record exactly those topics

        Storage follows the rosbag2 default (sqlite3 on Humble); override with
        BAG_STORAGE=mcap for the newer plugin if it's installed. `mkdir -p` runs
        inside the recording command so nothing is created when recording is off.
        """
        bag_dir = os.getenv('BAG_DIR', os.path.join(os.getcwd(), 'bags'))
        session = os.path.join(
            bag_dir, f"session_{datetime.datetime.now():%Y%m%d_%H%M%S}"
        )

        topics_env = os.getenv('BAG_TOPICS', '').strip()
        if topics_env in ('-a', 'all', '*'):
            topic_args = ['-a']
        elif topics_env:
            topic_args = topics_env.split()
        else:
            topic_args = DEFAULT_BAG_TOPICS

        storage = os.getenv('BAG_STORAGE', '').strip()
        storage_args = ['-s', storage] if storage else []

        record_args = ['-o', session] + storage_args + topic_args
        record_sh = (
            'mkdir -p ' + shlex.quote(bag_dir)
            + ' && exec ros2 bag record '
            + ' '.join(shlex.quote(a) for a in record_args)
        )

        return [
            ExecuteProcess(
                cmd=['bash', '-c', record_sh],
                output='screen',
                condition=IfCondition(LaunchConfiguration('bag_record')),
            )
        ]


def generate_launch_description():
    """Generate the launch description for Go2 robot system"""
    
    # Initialize configuration and factory
    config = Go2LaunchConfig()
    factory = Go2NodeFactory(config)
    
    # Create all components
    launch_args = factory.create_launch_arguments()
    robot_state_nodes = factory.create_robot_state_nodes()
    core_nodes = factory.create_core_nodes()
    teleop_nodes = factory.create_teleop_nodes()
    visualization_nodes = factory.create_visualization_nodes()
    include_launches = factory.create_include_launches()
    bag_recorder = factory.create_bag_recorder()

    # Combine all elements
    launch_entities = (
        launch_args +
        robot_state_nodes +
        core_nodes +
        teleop_nodes +
        visualization_nodes +
        include_launches +
        bag_recorder
    )
    
    return LaunchDescription(launch_entities)