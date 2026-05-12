"""YOLO object detector ROS2 node using Ultralytics.

Subscribes to /camera/image_raw and publishes Detection2DArray on /detected_objects.
Also publishes an annotated image on /annotated_image (optional, enabled by default).

For simulation, remap the camera topic:
  --ros-args -r /camera/image_raw:=/go2_camera/color/image
"""

import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from vision_msgs.msg import (BoundingBox2D, Detection2D, Detection2DArray,
                              ObjectHypothesis, ObjectHypothesisWithPose)
from cv_bridge import CvBridge
from ultralytics import YOLO


class YoloDetectorNode(Node):
    """Detects objects using YOLO and publishes on ROS2.

    Subscribes to /camera/image_raw (remap for simulation).
    Publishes Detection2DArray on /detected_objects.
    Publishes annotated Image on /annotated_image (when enabled).
    """

    def __init__(self):
        super().__init__("yolo_detector_node")
        self.declare_parameter('device', 'cpu')
        self.declare_parameter('detection_threshold', 0.5)
        self.declare_parameter('publish_annotated_image', True)
        self.declare_parameter('model', 'yolo11n.pt')

        self.device = self.get_parameter('device').get_parameter_value().string_value
        self.detection_threshold = (
            self.get_parameter('detection_threshold').get_parameter_value().double_value)
        self.publish_annotated = (
            self.get_parameter('publish_annotated_image').get_parameter_value().bool_value)
        model_name = self.get_parameter('model').get_parameter_value().string_value

        self.subscription = self.create_subscription(
            Image, '/camera/image_raw', self.listener_callback, 10)
        self.detected_objects_publisher = self.create_publisher(
            Detection2DArray, 'detected_objects', 10)
        self.annotated_image_publisher = (
            self.create_publisher(Image, 'annotated_image', 10)
            if self.publish_annotated else None)

        self.bridge = CvBridge()
        self.model = YOLO(model_name)
        self.class_names = self.model.names  # {int: str}

        self.get_logger().info(
            f"YoloDetectorNode started — model: {model_name}, "
            f"device: {self.device}, threshold: {self.detection_threshold}")

    def _to_detection2d(self, box_xyxy, class_id, score, header):
        """Convert a YOLO xyxy box to a ROS2 Detection2D message."""
        x1, y1, x2, y2 = box_xyxy
        det = Detection2D()
        det.header = header
        hyp = ObjectHypothesis()
        hyp.class_id = self.class_names.get(class_id, str(class_id))
        hyp.score = score
        hyp_with_pose = ObjectHypothesisWithPose()
        hyp_with_pose.hypothesis = hyp
        det.results.append(hyp_with_pose)
        bbox = BoundingBox2D()
        bbox.center.position.x = (x1 + x2) / 2.0
        bbox.center.position.y = (y1 + y2) / 2.0
        bbox.center.theta = 0.0
        bbox.size_x = x2 - x1
        bbox.size_y = y2 - y1
        det.bbox = bbox
        return det

    def _publish_annotated_image(self, cv_image, results, header):
        """Draw bounding boxes with OpenCV and publish annotated image."""
        annotated = cv_image.copy()
        boxes_obj = results[0].boxes
        if boxes_obj is not None and len(boxes_obj) > 0:
            for box in boxes_obj:
                x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
                cls_id = int(box.cls[0])
                label = f"{self.class_names.get(cls_id, str(cls_id))} {float(box.conf[0]):.2f}"
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 255), 2)
                cv2.putText(annotated, label, (x1, y1 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        ros_msg = self.bridge.cv2_to_imgmsg(annotated, encoding='rgb8')
        ros_msg.header = header
        self.annotated_image_publisher.publish(ros_msg)

    def listener_callback(self, msg):
        """Receive image, run YOLO inference, publish detections."""
        cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='rgb8')
        results = self.model(
            cv_image, conf=self.detection_threshold, device=self.device, verbose=False)

        detection_array = Detection2DArray()
        detection_array.header = msg.header
        boxes_obj = results[0].boxes
        if boxes_obj is not None and len(boxes_obj) > 0:
            for box in boxes_obj:
                det = self._to_detection2d(
                    box.xyxy[0].tolist(), int(box.cls[0]), float(box.conf[0]), msg.header)
                detection_array.detections.append(det)
        self.detected_objects_publisher.publish(detection_array)

        if self.annotated_image_publisher is not None:
            self._publish_annotated_image(cv_image, results, msg.header)


def main():
    rclpy.init()
    node = YoloDetectorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
