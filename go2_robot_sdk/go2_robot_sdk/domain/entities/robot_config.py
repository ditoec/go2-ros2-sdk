# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

from dataclasses import dataclass
from typing import List


@dataclass
class RobotConfig:
    """Robot configuration parameters"""
    robot_ip_list: List[str]
    token: str
    conn_type: str
    enable_video: bool
    decode_lidar: bool
    publish_raw_voxel: bool
    obstacle_avoidance: bool
    conn_mode: str  # 'single' or 'multi'
    enable_audio: bool = False  # capture the robot's WebRTC mic track → /robot_audio
    enable_webrtc_camera: bool = False  # conn_type=='cyclonedds' only: also open a WebRTC
    # session for camera video while CycloneDDS stays authoritative for commands/state

    @classmethod
    def from_params(cls, robot_ip: str, token: str, conn_type: str,
                   enable_video: bool, decode_lidar: bool,
                   publish_raw_voxel: bool, obstacle_avoidance: bool,
                   enable_audio: bool = False, enable_webrtc_camera: bool = False):
        """Create configuration from parameters"""
        robot_ip_list = robot_ip.replace(" ", "").split(",")
        # CycloneDDS's own native subscriptions (sportmodestate, lowstate, etc.) are
        # never robot-prefixed regardless -- the DDS domain just listens to whatever's
        # on the LAN, no per-robot differentiation at that layer. So conn_mode here only
        # controls this driver's own published/converted topic naming (/odom vs
        # /robot0/odom); a single onboard robot (the common case, ROBOT_IP typically
        # unset -- robot_ip_list == ['']) gets unprefixed topics like every other
        # single-robot deployment, matching the primary documented onboard-Jetson setup.
        conn_mode = "single" if len(robot_ip_list) == 1 else "multi"

        return cls(
            robot_ip_list=robot_ip_list,
            token=token,
            conn_type=conn_type,
            enable_video=enable_video,
            decode_lidar=decode_lidar,
            publish_raw_voxel=publish_raw_voxel,
            obstacle_avoidance=obstacle_avoidance,
            conn_mode=conn_mode,
            enable_audio=enable_audio,
            enable_webrtc_camera=enable_webrtc_camera
        )