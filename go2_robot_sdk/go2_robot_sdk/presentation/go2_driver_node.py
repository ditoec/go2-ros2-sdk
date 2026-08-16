# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

import asyncio
import logging
import os
from typing import Dict, Any

import numpy as np
from aiortc import MediaStreamTrack
from cv_bridge import CvBridge

from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSHistoryPolicy, QoSReliabilityPolicy
from rclpy.qos_overriding_options import QoSOverridingOptions
from rcl_interfaces.msg import SetParametersResult
from tf2_ros import TransformBroadcaster

from geometry_msgs.msg import Twist, PoseStamped
from go2_interfaces.msg import Go2State, IMU
from go2_interfaces.msg import VoxelMapCompressed, WebRtcReq
# CycloneDDS ingest only: subscribe using Unitree's own unitree_go message
# package, not this repo's go2_interfaces clones of the same fields. ROS2's
# rosidl toolchain bakes the package name into each message's DDS wire-level
# type identifier (<package>::msg::dds_::<Type>_), so a go2_interfaces-typed
# subscriber can never receive data from the robot firmware's native
# unitree_go-typed publisher on the same topic name, even with identical
# fields -- confirmed live: `ros2 topic echo` refuses with "contains more
# than one type", and every downstream topic derived from these three
# (/imu, /joint_states, /go2_states) stayed silent while topics using
# standard sensor_msgs/geometry_msgs types (/utlidar/cloud,
# /utlidar/robot_pose) received live data normally.
from unitree_go.msg import LowState, SportModeState, WirelessController
from sensor_msgs.msg import PointCloud2, JointState, Joy, Image, CameraInfo
from std_msgs.msg import UInt8MultiArray
from nav_msgs.msg import Odometry

from ..domain.entities import RobotConfig, RobotData, CameraData, AudioData
from ..domain.entities.robot_data import IMUData, JointData, OdometryData, RobotState
from ..application.services import RobotDataService, RobotControlService
from ..infrastructure.ros2 import ROS2Publisher
from ..infrastructure.webrtc import WebRTCAdapter
from ..infrastructure.cyclonedds import CycloneDDSAdapter

logging.basicConfig(level=logging.WARN)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Go2DriverNode(Node):
    """Main Go2 driver node - entry point to the application"""

    def __init__(self, event_loop=None):
        super().__init__('go2_driver_node')  # Clean architecture main driver
        self.event_loop = event_loop
        
        # Configuration initialization
        self.config = self._setup_configuration()
        
        # Infrastructure initialization
        self.publishers_dict = self._setup_publishers()
        self.broadcaster = TransformBroadcaster(self, qos=QoSProfile(depth=10))
        self.bridge = CvBridge()
        
        # Architecture layers initialization
        self.ros2_publisher = ROS2Publisher(
            node=self,
            config=self.config,
            publishers=self.publishers_dict,
            broadcaster=self.broadcaster
        )
        
        self.robot_data_service = RobotDataService(self.ros2_publisher)
        
        self.webrtc_adapter = WebRTCAdapter(
            config=self.config,
            on_validated_callback=self._on_robot_validated,
            on_video_frame_callback=self._on_video_frame if self.config.enable_video else None,
            on_audio_frame_callback=self._on_audio_frame if self.config.enable_audio else None,
            event_loop=self.event_loop
        )
        
        # CycloneDDS command adapter (replaces WebRTCAdapter for command routing)
        if self.config.conn_type == 'cyclonedds':
            self.cyclonedds_adapter = CycloneDDSAdapter(self, self.config)
            self.robot_control_service = RobotControlService(self.cyclonedds_adapter)
        else:
            self.cyclonedds_adapter = None
            self.robot_control_service = RobotControlService(self.webrtc_adapter)

        # Set callback for data
        self.webrtc_adapter.set_data_callback(self._on_robot_data_received)
        
        # Subscribers initialization
        self._setup_subscribers()
        
        # State
        self.joy_state = Joy()

    def _setup_configuration(self) -> RobotConfig:
        """Configuration setup"""
        robot_ip = os.getenv('ROBOT_IP', os.getenv('GO2_IP', ''))
        token = os.getenv('ROBOT_TOKEN', os.getenv('GO2_TOKEN', ''))
        conn_type = os.getenv('CONN_TYPE', '')
        enable_webrtc_camera = os.getenv('ENABLE_WEBRTC_CAMERA', 'false').lower() == 'true'

        # Declare parameters
        self.declare_parameters(
            namespace='',
            parameters=[
                ('robot_ip', robot_ip),
                ('token', token),
                ('conn_type', conn_type),
                ('enable_video', True),
                ('enable_audio', False),
                ('decode_lidar', True),
                ('publish_raw_voxel', False),
                ('obstacle_avoidance', False),
                ('enable_webrtc_camera', enable_webrtc_camera),
            ]
        )

        self.add_on_set_parameters_callback(self._on_set_parameters)

        # Get parameter values
        config = RobotConfig.from_params(
            robot_ip=self.get_parameter('robot_ip').get_parameter_value().string_value,
            token=self.get_parameter('token').get_parameter_value().string_value,
            conn_type=self.get_parameter('conn_type').get_parameter_value().string_value,
            enable_video=self.get_parameter('enable_video').get_parameter_value().bool_value,
            decode_lidar=self.get_parameter('decode_lidar').get_parameter_value().bool_value,
            publish_raw_voxel=self.get_parameter('publish_raw_voxel').get_parameter_value().bool_value,
            obstacle_avoidance=self.get_parameter('obstacle_avoidance').get_parameter_value().bool_value,
            enable_audio=self.get_parameter('enable_audio').get_parameter_value().bool_value,
            enable_webrtc_camera=self.get_parameter('enable_webrtc_camera').get_parameter_value().bool_value
        )

        # Log configuration
        self.get_logger().info(f"Robot IPs: {config.robot_ip_list}")
        self.get_logger().info(f"Connection type: {config.conn_type}")
        self.get_logger().info(f"Connection mode: {config.conn_mode}")
        self.get_logger().info(f"Enable video: {config.enable_video}")
        self.get_logger().info(f"Enable audio: {config.enable_audio}")
        self.get_logger().info(f"Decode lidar: {config.decode_lidar}")
        self.get_logger().info(f"Publish raw voxel: {config.publish_raw_voxel}")
        self.get_logger().info(f"Obstacle avoidance: {config.obstacle_avoidance}")
        if config.conn_type == 'cyclonedds':
            self.get_logger().info(f"WebRTC camera (hybrid): {config.enable_webrtc_camera}")

        return config

    def _setup_publishers(self) -> Dict[str, list]:
        """ROS2 publishers setup"""
        qos_profile = QoSProfile(depth=10)
        best_effort_qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1
        )

        publishers = {
            'joint_state': [],
            'robot_state': [],
            'lidar': [],
            'odometry': [],
            'imu': [],
            'camera': [],
            'camera_info': [],
            'voxel': [],
            'audio': []
        }

        num_robots = len(self.config.robot_ip_list)
        
        for i in range(num_robots):
            # Define topics depending on connection mode
            if self.config.conn_mode == 'single':
                joint_topic = 'joint_states'
                robot_state_topic = 'go2_states'
                lidar_topic = 'point_cloud2'
                odom_topic = 'odom'
                imu_topic = 'imu'
                camera_topic = 'camera/image_raw'
                camera_info_topic = 'camera/camera_info'
                voxel_topic = '/utlidar/voxel_map_compressed'
                audio_topic = 'robot_audio'
            else:
                prefix = f'robot{i}'
                joint_topic = f'{prefix}/joint_states'
                robot_state_topic = f'{prefix}/go2_states'
                lidar_topic = f'{prefix}/point_cloud2'
                odom_topic = f'{prefix}/odom'
                imu_topic = f'{prefix}/imu'
                camera_topic = f'{prefix}/camera/image_raw'
                camera_info_topic = f'{prefix}/camera/camera_info'
                voxel_topic = f'{prefix}/utlidar/voxel_map_compressed'
                audio_topic = f'{prefix}/robot_audio'

            # Create publishers
            publishers['joint_state'].append(
                self.create_publisher(JointState, joint_topic, qos_profile))
            publishers['robot_state'].append(
                self.create_publisher(Go2State, robot_state_topic, qos_profile))
            publishers['lidar'].append(
                self.create_publisher(
                    PointCloud2, lidar_topic, best_effort_qos,
                    qos_overriding_options=QoSOverridingOptions.with_default_policies()))
            publishers['odometry'].append(
                self.create_publisher(Odometry, odom_topic, qos_profile))
            publishers['imu'].append(
                self.create_publisher(IMU, imu_topic, qos_profile))

            if self.config.enable_video:
                publishers['camera'].append(
                    self.create_publisher(
                        Image, camera_topic, best_effort_qos,
                        qos_overriding_options=QoSOverridingOptions.with_default_policies()))
                publishers['camera_info'].append(
                    self.create_publisher(
                        CameraInfo, camera_info_topic, best_effort_qos,
                        qos_overriding_options=QoSOverridingOptions.with_default_policies()))

            if self.config.publish_raw_voxel:
                publishers['voxel'].append(
                    self.create_publisher(VoxelMapCompressed, voxel_topic, best_effort_qos))

            if self.config.enable_audio:
                publishers['audio'].append(
                    self.create_publisher(UInt8MultiArray, audio_topic, best_effort_qos))

        return publishers

    def _setup_subscribers(self) -> None:
        """ROS2 subscribers setup"""
        qos_profile = QoSProfile(depth=10)

        # Command subscribers
        num_robots = len(self.config.robot_ip_list)
        
        if self.config.conn_mode == 'single':
            self.create_subscription(
                Twist, 'cmd_vel_out',
                lambda msg: self._on_cmd_vel(msg, "0"), qos_profile)
            self.create_subscription(
                WebRtcReq, 'webrtc_req',
                lambda msg: self._on_webrtc_req(msg, "0"), qos_profile)
        else:
            for i in range(num_robots):
                self.create_subscription(
                    Twist, f'robot{i}/cmd_vel_out',
                    lambda msg, robot_id=str(i): self._on_cmd_vel(msg, robot_id), qos_profile)
                self.create_subscription(
                    WebRtcReq, f'robot{i}/webrtc_req',
                    lambda msg, robot_id=str(i): self._on_webrtc_req(msg, robot_id), qos_profile)

        # Joystick subscriber
        self.create_subscription(Joy, 'joy', self._on_joy, qos_profile)

        # CycloneDDS subscriptions (data ingest from robot over Ethernet DDS)
        if self.config.conn_type == 'cyclonedds':
            best_effort = QoSProfile(
                reliability=QoSReliabilityPolicy.BEST_EFFORT,
                history=QoSHistoryPolicy.KEEP_LAST,
                depth=1,
            )
            # High-level sport-mode state (~50 Hz) — position, velocity, foot force
            self.create_subscription(
                SportModeState, 'sportmodestate',
                self._on_cyclonedds_sport_state, qos_profile)
            # Low-level joint + IMU state (~500 Hz) — motor angles, IMU
            self.create_subscription(
                LowState, 'lowstate',
                self._on_cyclonedds_low_state, best_effort)
            # Odometry from UnitreeLidar onboard estimation
            self.create_subscription(
                PoseStamped, '/utlidar/robot_pose',
                self._on_cyclonedds_pose, qos_profile)
            # Raw LiDAR point cloud from onboard processor
            self.create_subscription(
                PointCloud2, '/utlidar/cloud',
                self._on_cyclonedds_lidar, best_effort)
            # Wireless controller button/joystick state
            self.create_subscription(
                WirelessController, 'wirelesscontroller',
                self._on_cyclonedds_wireless, qos_profile)

    def _on_set_parameters(self, params) -> SetParametersResult:
        """Callback for parameter changes"""
        result = SetParametersResult(successful=True)

        try:
            for p in params:
                if p.name == 'obstacle_avoidance':
                    self.get_logger().info(f'New obstacle_avoidance value: {p.value}')
                    self.config.obstacle_avoidance = p.value
                    
                    try:
                        self.robot_control_service.set_obstacle_avoidance(p.value, "0")
                    except Exception as e:
                        self.get_logger().error(f"Failed to set obstacle avoidance: {e}")
                        result.successful = False
                        result.reason = str(e)
                        break
                    
                    result.successful = True
                    result.reason = 'Updated obstacle_avoidance'
                    break
        except Exception as e:
            self.get_logger().error(f"Error setting parameters: {e}")
            result.successful = False
            result.reason = str(e)
            
        return result

    def _on_cmd_vel(self, msg: Twist, robot_id: str) -> None:
        """Callback for movement commands"""
        self.robot_control_service.handle_cmd_vel(
            msg.linear.x, msg.linear.y, msg.angular.z, 
            robot_id, self.config.obstacle_avoidance
        )

    def _on_webrtc_req(self, msg: WebRtcReq, robot_id: str) -> None:
        """Callback for WebRTC requests"""
        self.robot_control_service.handle_webrtc_request(
            msg.api_id, msg.parameter, msg.topic, msg.id, robot_id
        )

    def _on_joy(self, msg: Joy) -> None:
        """Callback for joystick"""
        self.joy_state = msg

    def _on_robot_validated(self, robot_id: str) -> None:
        """Callback after robot validation"""
        self.get_logger().info(f"Robot {robot_id} validated and ready")

    def _on_robot_data_received(self, msg: Dict[str, Any], robot_id: str) -> None:
        """Callback for receiving data from robot"""
        # In CycloneDDS mode, WebRTC (if connected at all — see enable_webrtc_camera)
        # is only ever used for camera video, negotiated via _on_video_frame below.
        # CycloneDDSAdapter's own DDS subscriptions stay the sole source of state/
        # commands; this data channel is never processed to avoid double-publishing.
        if self.config.conn_type == 'cyclonedds':
            return
        self.robot_data_service.process_webrtc_message(msg, robot_id)

    async def _on_video_frame(self, track: MediaStreamTrack, robot_id: str) -> None:
        """Callback for processing video frames"""
        logger.info(f"Video frame received for robot {robot_id}")

        while True:
            try:
                frame = await track.recv()
                img = frame.to_ndarray(format="bgr24")

                # Create camera data
                camera_data = CameraData(
                    image=img,
                    height=img.shape[0],
                    width=img.shape[1],
                    encoding="bgr8"
                )

                robot_data = RobotData(
                    robot_id=robot_id,
                    timestamp=0.0,
                    camera_data=camera_data
                )

                # Publish via ROS2Publisher
                self.ros2_publisher.publish_camera_data(robot_data)
                await asyncio.sleep(0)

            except Exception as e:
                logger.error(f"Error processing video frame: {e}")
                break

    async def _on_audio_frame(self, track: MediaStreamTrack, robot_id: str) -> None:
        """Callback for processing the robot's onboard mic audio track.

        Resamples each WebRTC audio frame to mono signed-16-bit PCM at 16 kHz and
        republishes it on /robot_audio so the speech_processor STT pipeline
        (audio_source:=topic) can consume it just like a local microphone.
        """
        import av

        logger.info(f"Audio track received for robot {robot_id}")
        resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)

        while True:
            try:
                frame = await track.recv()
                resampled = resampler.resample(frame)
                # PyAV >=9 returns a list of frames; older returns a single frame.
                frames = resampled if isinstance(resampled, list) else [resampled]

                for rs in frames:
                    pcm = rs.to_ndarray()  # shape (1, n), int16 for mono s16
                    audio_bytes = np.ascontiguousarray(pcm).astype('<i2').tobytes()
                    robot_data = RobotData(
                        robot_id=robot_id,
                        timestamp=0.0,
                        audio_data=AudioData(
                            data=audio_bytes, sample_rate=16000, channels=1
                        ),
                    )
                    self.ros2_publisher.publish_audio_data(robot_data)

                await asyncio.sleep(0)

            except Exception as e:
                logger.error(f"Error processing audio frame: {e}")
                break

    # ------------------------------------------------------------------
    # CycloneDDS inbound callbacks
    # ------------------------------------------------------------------

    def _on_cyclonedds_sport_state(self, msg: SportModeState) -> None:
        """
        SportModeState (~50 Hz) — high-level position, velocity, gait, foot force.
        Publishes /go2_states and /imu.
        """
        imu = IMUData(
            quaternion=list(msg.imu_state.quaternion),
            accelerometer=list(msg.imu_state.accelerometer),
            gyroscope=list(msg.imu_state.gyroscope),
            rpy=list(msg.imu_state.rpy),
            temperature=float(msg.imu_state.temperature),
        )
        state = RobotState(
            mode=int(msg.mode),
            progress=float(msg.progress),
            gait_type=int(msg.gait_type),
            position=list(map(float, msg.position)),
            body_height=float(msg.body_height),
            velocity=list(map(float, msg.velocity)),
            range_obstacle=list(map(float, msg.range_obstacle)),
            foot_force=list(map(float, msg.foot_force)),
            foot_position_body=list(map(float, msg.foot_position_body)),
            foot_speed_body=list(map(float, msg.foot_speed_body)),
        )
        robot_data = RobotData(
            robot_id="0",
            timestamp=float(msg.stamp.sec) + float(msg.stamp.nanosec) * 1e-9,
            robot_state=state,
            imu_data=imu,
        )
        self.ros2_publisher.publish_robot_state(robot_data)

    def _on_cyclonedds_low_state(self, msg: LowState) -> None:
        """
        LowState (~500 Hz) — motor angles/velocities/torques + IMU.
        Publishes /joint_states and /imu (high-frequency update).
        """
        imu = IMUData(
            quaternion=list(msg.imu_state.quaternion),
            accelerometer=list(msg.imu_state.accelerometer),
            gyroscope=list(msg.imu_state.gyroscope),
            rpy=list(msg.imu_state.rpy),
            temperature=float(msg.imu_state.temperature),
        )
        # Motors 0-11 are the 12 leg joints (FR:0-2, FL:3-5, RR:6-8, RL:9-11)
        motor_state = [
            {
                'q':       float(m.q),
                'dq':      float(m.dq),
                'ddq':     float(m.ddq),
                'tau_est': float(m.tau_est),
            }
            for m in msg.motor_state[:12]
        ]
        robot_data = RobotData(
            robot_id="0",
            timestamp=float(msg.tick) * 1e-3,
            imu_data=imu,
            joint_data=JointData(motor_state=motor_state),
        )
        self.ros2_publisher.publish_joint_state(robot_data)
        # Also republish IMU at full 500 Hz rate
        robot_data_imu_only = RobotData(
            robot_id="0",
            timestamp=robot_data.timestamp,
            robot_state=RobotState(
                mode=0, progress=0.0, gait_type=0,
                position=[0.0, 0.0, 0.0], body_height=0.0,
                velocity=[0.0, 0.0, 0.0], range_obstacle=[0.0, 0.0, 0.0, 0.0],
                foot_force=[0.0, 0.0, 0.0, 0.0],
                foot_position_body=[0.0] * 12,
                foot_speed_body=[0.0] * 12,
            ),
            imu_data=imu,
        )
        self.ros2_publisher.publish_robot_state(robot_data_imu_only)

    def _on_cyclonedds_pose(self, msg: PoseStamped) -> None:
        """
        /utlidar/robot_pose — odometry estimated by the onboard LiDAR processor.
        Publishes /odom and the odom→base_link TF.
        """
        p = msg.pose.position
        q = msg.pose.orientation
        odom = OdometryData(
            position={'x': p.x, 'y': p.y, 'z': p.z},
            orientation={'x': q.x, 'y': q.y, 'z': q.z, 'w': q.w},
        )
        robot_data = RobotData(
            robot_id="0",
            timestamp=float(msg.header.stamp.sec) + float(msg.header.stamp.nanosec) * 1e-9,
            odometry_data=odom,
        )
        self.ros2_publisher.publish_odometry(robot_data)

    def _on_cyclonedds_lidar(self, msg: PointCloud2) -> None:
        """
        /utlidar/cloud — raw PointCloud2 from the onboard LiDAR processor.
        Re-stamps with node clock and republishes on /point_cloud2.
        """
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'lidar_link'
        if self.publishers_dict['lidar']:
            self.publishers_dict['lidar'][0].publish(msg)

    def _on_cyclonedds_wireless(self, msg: WirelessController) -> None:
        """
        /wirelesscontroller — physical remote button/joystick state.
        Logged at debug level; extend here to forward to /joy if needed.
        """
        self.get_logger().debug(
            f"Wireless: lx={msg.lx:.2f} ly={msg.ly:.2f} "
            f"rx={msg.rx:.2f} ry={msg.ry:.2f} keys={msg.keys:#06x}"
        )

    async def connect_robots(self) -> None:
        """Connect to robots"""
        if self.config.conn_type == 'webrtc':
            for i, robot_ip in enumerate(self.config.robot_ip_list):
                try:
                    await self.webrtc_adapter.connect(str(i))
                except Exception as e:
                    self.get_logger().error(f"Failed to connect to robot {i}: {e}")
                    raise
        elif self.config.conn_type == 'cyclonedds' and self.config.enable_webrtc_camera:
            # Hybrid mode: CycloneDDSAdapter (already constructed) owns commands/state
            # over the internal DDS domain; WebRTC is opened here purely to feed
            # /camera/image_raw via _on_video_frame -- _on_robot_data_received drops
            # everything else the data channel might deliver. A camera failure here
            # must not take down CycloneDDS's already-working state/command path.
            for i, robot_ip in enumerate(self.config.robot_ip_list):
                if not robot_ip:
                    self.get_logger().warn(
                        "enable_webrtc_camera is set but ROBOT_IP is empty -- "
                        "skipping WebRTC camera connection (needs the robot's "
                        "internal IP to reach its WebRTC signaling server)."
                    )
                    continue
                try:
                    await self.webrtc_adapter.connect(str(i))
                except Exception as e:
                    self.get_logger().error(
                        f"WebRTC camera connection failed for robot {i} (CycloneDDS "
                        f"command/state path is unaffected): {e}"
                    )

    async def run_robot_control_loop(self, robot_id: str) -> None:
        """Main robot control loop"""
        while True:
            try:
                # Process joystick commands
                if self.joy_state.buttons:
                    self.robot_control_service.handle_joy_command(
                        self.joy_state.buttons, robot_id
                    )

                # Process WebRTC commands
                self.webrtc_adapter.process_webrtc_commands(robot_id)
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.get_logger().error(f"Error in control loop for robot {robot_id}: {e}")
                raise 