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
        conn_mode = "single" if (
            len(robot_ip_list) == 1 and conn_type != "cyclonedds") else "multi"

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