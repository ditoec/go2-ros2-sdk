# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

"""
LiDAR to PointCloud Node

Enhanced LiDAR data processing node with better architecture and performance.
"""

from typing import List, Set, Tuple
from dataclasses import dataclass
from threading import Lock

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2


def _voxel_downsample(points: np.ndarray, voxel_size: float) -> np.ndarray:
    """Grid-based voxel downsampling — one representative point per voxel cell."""
    if voxel_size <= 0 or len(points) == 0:
        return points
    voxel_coords = np.floor(points / voxel_size).astype(np.int64)
    _, unique_idx = np.unique(voxel_coords, axis=0, return_index=True)
    return points[np.sort(unique_idx)]


def _save_ply(filename: str, points: np.ndarray) -> bool:
    """Write an Nx3 float32 array as a binary-little-endian PLY file."""
    try:
        header = (
            "ply\n"
            "format binary_little_endian 1.0\n"
            f"element vertex {len(points)}\n"
            "property float x\n"
            "property float y\n"
            "property float z\n"
            "end_header\n"
        ).encode('ascii')
        with open(filename, 'wb') as f:
            f.write(header)
            f.write(points.astype(np.float32).tobytes())
        return True
    except Exception:
        return False


@dataclass
class LidarConfig:
    """Configuration for LiDAR processing"""
    robot_ip_list: List[str]
    map_name: str
    save_map: bool
    save_interval: float = 10.0  # seconds
    max_points: int = 1000000    # Maximum points to keep in memory
    voxel_size: float = 0.01     # Voxel downsampling size


class PointCloudAggregator:
    """Thread-safe point cloud aggregation with memory management"""
    
    def __init__(self, config: LidarConfig):
        self.config = config
        self.points: Set[Tuple[float, float, float]] = set()
        self._lock = Lock()
        self._points_changed = False
        
    def add_points(self, new_points: List[Tuple[float, float, float]]) -> None:
        """Add new points to the aggregated cloud"""
        with self._lock:
            for point in new_points:
                # Round points to reduce memory usage
                rounded_point = (
                    round(point[0], 3),
                    round(point[1], 3), 
                    round(point[2], 3)
                )
                self.points.add(rounded_point)
            
            # Memory management - remove oldest points if exceeding limit
            if len(self.points) > self.config.max_points:
                # Convert to list, sort by distance from origin, keep closest points
                points_list = list(self.points)
                points_list.sort(key=lambda p: p[0]**2 + p[1]**2 + p[2]**2)
                self.points = set(points_list[:self.config.max_points])
            
            self._points_changed = True
    
    def get_points_copy(self) -> List[Tuple[float, float, float]]:
        """Get a thread-safe copy of current points"""
        with self._lock:
            return list(self.points)
    
    def has_changes(self) -> bool:
        """Check if points have changed since last check"""
        with self._lock:
            return self._points_changed
    
    def mark_saved(self) -> None:
        """Mark current state as saved"""
        with self._lock:
            self._points_changed = False
    
    def get_point_count(self) -> int:
        """Get current point count"""
        with self._lock:
            return len(self.points)


class LidarToPointCloudNode(Node):
    """Enhanced LiDAR to PointCloud processing node"""
    
    def __init__(self):
        super().__init__('lidar_to_pointcloud')
        
        # Declare and get parameters
        self._declare_parameters()
        self.config = self._load_configuration()
        
        # Initialize components
        self.aggregator = PointCloudAggregator(self.config)
        
        # Setup QoS profile for high-frequency data
        self.qos_profile = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1
        )
        
        # Setup subscriptions and publishers
        self._setup_subscriptions()
        self._setup_publishers()
        
        # Setup timers
        if self.config.save_map:
            self.save_timer = self.create_timer(
                self.config.save_interval, 
                self._save_map_callback
            )
        
        # Log configuration
        self._log_configuration()
    
    def _declare_parameters(self) -> None:
        """Declare all node parameters"""
        self.declare_parameter('robot_ip_lst', [''])
        self.declare_parameter('map_name', '3d_map')
        self.declare_parameter('map_save', 'true')
        self.declare_parameter('save_interval', 10.0)
        self.declare_parameter('max_points', 1000000)
        self.declare_parameter('voxel_size', 0.01)
    
    def _load_configuration(self) -> LidarConfig:
        """Load configuration from parameters"""
        robot_ip_lst = [ip for ip in self.get_parameter('robot_ip_lst').get_parameter_value().string_array_value if ip]
        map_name = self.get_parameter('map_name').get_parameter_value().string_value
        save_map_str = self.get_parameter('map_save').get_parameter_value().string_value
        save_interval = self.get_parameter('save_interval').get_parameter_value().double_value
        max_points = self.get_parameter('max_points').get_parameter_value().integer_value
        voxel_size = self.get_parameter('voxel_size').get_parameter_value().double_value
        
        return LidarConfig(
            robot_ip_list=robot_ip_lst,
            map_name=map_name,
            save_map=save_map_str.lower() == 'true',
            save_interval=save_interval,
            max_points=max_points,
            voxel_size=voxel_size
        )
    
    def _setup_subscriptions(self) -> None:
        """Setup LiDAR data subscriptions"""
        self.subscriptions = []
        
        if len(self.config.robot_ip_list) == 1:
            # Single robot mode
            subscription = self.create_subscription(
                PointCloud2,
                '/robot0/point_cloud2',
                self._lidar_callback,
                self.qos_profile
            )
            self.subscriptions.append(subscription)
        else:
            # Multi-robot mode
            for i, _ in enumerate(self.config.robot_ip_list):
                subscription = self.create_subscription(
                    PointCloud2,
                    f'/robot{i}/point_cloud2',
                    self._lidar_callback,
                    self.qos_profile
                )
                self.subscriptions.append(subscription)
    
    def _setup_publishers(self) -> None:
        """Setup publishers for processed data"""
        self.pointcloud_pub = self.create_publisher(
            PointCloud2, 
            '/pointcloud/aggregated', 
            self.qos_profile
        )
    
    def _lidar_callback(self, msg: PointCloud2) -> None:
        """Process incoming LiDAR data"""
        try:
            # Extract points from message
            points = []
            for point in point_cloud2.read_points(
                msg, 
                field_names=("x", "y", "z"), 
                skip_nans=True
            ):
                points.append(tuple(point))
            
            # Add to aggregator
            self.aggregator.add_points(points)
            
            # Publish aggregated point cloud
            self._publish_aggregated_pointcloud(msg.header)
            
        except Exception as e:
            self.get_logger().error(f"Error processing LiDAR data: {e}")
    
    def _publish_aggregated_pointcloud(self, header) -> None:
        """Publish aggregated point cloud"""
        try:
            points = self.aggregator.get_points_copy()
            if points:
                pointcloud_msg = point_cloud2.create_cloud_xyz32(header, points)
                self.pointcloud_pub.publish(pointcloud_msg)
        except Exception as e:
            self.get_logger().error(f"Error publishing point cloud: {e}")
    
    def _save_map_callback(self) -> None:
        """Periodic map saving callback"""
        try:
            if not self.aggregator.has_changes():
                return
            
            points = self.aggregator.get_points_copy()
            if not points:
                return
            
            pts = np.array(points, dtype=np.float32)
            if self.config.voxel_size > 0:
                pts = _voxel_downsample(pts, self.config.voxel_size)

            map_filename = f"{self.config.map_name}.ply"
            if _save_ply(map_filename, pts):
                self.aggregator.mark_saved()
                self.get_logger().info(
                    f"Saved map: {map_filename} "
                    f"({len(pts)} downsampled / {self.aggregator.get_point_count()} total points)"
                )
            else:
                self.get_logger().error(f"Failed to save map: {map_filename}")
                
        except Exception as e:
            self.get_logger().error(f"Error saving map: {e}")
    
    def _log_configuration(self) -> None:
        """Log current configuration"""
        self.get_logger().info("🗺️  LiDAR Processor Configuration:")
        self.get_logger().info(f"   Robot IPs: {self.config.robot_ip_list}")
        self.get_logger().info(f"   Map name: {self.config.map_name}")
        self.get_logger().info(f"   Save map: {self.config.save_map}")
        if self.config.save_map:
            self.get_logger().info(f"   Save interval: {self.config.save_interval}s")
            self.get_logger().info(f"   Max points: {self.config.max_points:,}")
            self.get_logger().info(f"   Voxel size: {self.config.voxel_size}m")


def main(args=None):
    """Main entry point"""
    rclpy.init(args=args)
    
    try:
        node = LidarToPointCloudNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error running lidar processor: {e}")
    finally:
        rclpy.shutdown()


if __name__ == '__main__':
    main() 