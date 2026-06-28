#!/usr/bin/env python3

# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

"""
Face Recognition Node — detect + recognize faces, greet people by name (Modul 4.2 / 4.4).

Uses InsightFace's unified ``FaceAnalysis`` app (SCRFD detection + 5-point
landmark alignment + ArcFace embeddings in one ``app.get(frame)`` call — no
PyTorch) and matches each face against a file-system database
(:class:`~speech_processor.face_db.FaceDB`, ported from the ``face-captioner``
project). Recognized names are published for ``voice_cmd_node`` to greet
visitors by name.

**Recognition only — no on-site enrollment.** The database is populated
out-of-band (e.g. a web enrollment service) by dropping ``<Name>/*.jpg`` photos
under ``face_db_path``. The node embeds those images at startup; publish to
``/reload_faces`` to re-scan after the DB changes without restarting the node.

Subscriptions:
  camera_topic  (sensor_msgs/Image)  — default /camera/image_raw
                                        (simulation: remap to /go2_camera/color/image)
  /reload_faces (std_msgs/Empty)     — re-scan face_db_path and re-embed all photos

Publications:
  /recognized_faces       (vision_msgs/Detection2DArray) — bbox + class_id=name + score=similarity
  /recognized_face_names  (std_msgs/String)              — comma-joined known names (excludes Unknown)
  /face_annotated_image   (sensor_msgs/Image)            — frame with boxes + name labels

Parameters (env-var defaults wired in robot.launch.py):
  face_device        (str,   cpu | cuda — default cpu; the Windows GPU container
                             has no CUDA toolkit, the Jetson image does)
  face_model_pack    (str,   InsightFace pack — default buffalo_sc. NOTE: buffalo_*
                             weights are licensed for non-commercial research only)
  face_db_path       (str,   directory holding <Name>/*.jpg photos — default ./face_db)
  face_threshold     (float, cosine-similarity match floor — default 0.35)
  inference_rate     (float, Hz — default 2.0)
  det_size           (int,   SCRFD detection square — default 640)
  camera_topic       (str,   default /camera/image_raw)
  publish_annotated  (bool,  default True)
  rebuild_on_start   (bool,  re-embed photos from disk at startup — default True;
                             picks up faces added by the web enroller since last run)
"""

import time

import cv2
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import Empty, Float32, String
from vision_msgs.msg import (BoundingBox2D, Detection2D, Detection2DArray,
                             ObjectHypothesis, ObjectHypothesisWithPose)

from speech_processor.face_db import FaceDB


class FaceRecognitionNode(Node):

    def __init__(self):
        super().__init__("face_recognition_node")

        self.declare_parameter("face_device", "cpu")
        self.declare_parameter("face_model_pack", "buffalo_sc")
        self.declare_parameter("face_db_path", "./face_db")
        self.declare_parameter("face_threshold", 0.35)
        self.declare_parameter("inference_rate", 2.0)
        self.declare_parameter("det_size", 640)
        self.declare_parameter("camera_topic", "/camera/image_raw")
        self.declare_parameter("publish_annotated", True)
        self.declare_parameter("rebuild_on_start", True)

        device = str(self.get_parameter("face_device").value).lower()
        model_pack = self.get_parameter("face_model_pack").value
        db_path = self.get_parameter("face_db_path").value
        threshold = float(self.get_parameter("face_threshold").value)
        self._min_interval = 1.0 / max(0.01, float(self.get_parameter("inference_rate").value))
        det = int(self.get_parameter("det_size").value)
        camera_topic = self.get_parameter("camera_topic").value
        self._publish_annotated = bool(self.get_parameter("publish_annotated").value)
        rebuild_on_start = bool(self.get_parameter("rebuild_on_start").value)

        self._bridge = CvBridge()
        self._last_time = 0.0

        # --- InsightFace app (detection + alignment + embedding in one call) ---
        self._app = self._build_app(model_pack, device, det)

        # --- Face DB (cosine matcher over ArcFace embeddings) ---
        # Populated out-of-band (web enrollment) as face_db_path/<Name>/*.jpg;
        # we embed those photos here. rebuild_on_start re-scans every launch so
        # newly enrolled people are picked up; otherwise the cache is trusted.
        self._db = FaceDB(db_path, threshold=threshold)
        self._load_db(rebuild=rebuild_on_start)

        # --- Publishers ---
        self._faces_pub = self.create_publisher(Detection2DArray, "/recognized_faces", 10)
        self._names_pub = self.create_publisher(String, "/recognized_face_names", 10)
        self._img_pub = (
            self.create_publisher(Image, "/face_annotated_image", 1)
            if self._publish_annotated else None
        )

        # --- Subscriptions ---
        self.create_subscription(Image, camera_topic, self._on_image, qos_profile_sensor_data)
        self.create_subscription(Empty, "/reload_faces", self._on_reload, 10)
        # Live threshold tuning from the enrollment web UI (face_enrollment_node).
        self.create_subscription(Float32, "/face_threshold", self._on_threshold, 10)

        self.get_logger().info(
            f"face_recognition_node ready — pack={model_pack}, device={device}, "
            f"threshold={threshold}, rate={1.0 / self._min_interval:.2f} Hz, topic={camera_topic}"
        )

    def _load_db(self, rebuild: bool) -> None:
        """(Re)load the database from disk and log how many faces were embedded."""
        if rebuild:
            self._db.rebuild_from_disk(self._embed_largest)
        else:
            self._db.load(embed_fn=self._embed_largest)
        self.get_logger().info(
            f"Face DB: {len(self._db.known_names)} people, "
            f"{self._db.num_faces} embeddings at {self._db.db_path}"
        )

    # ------------------------------------------------------------------
    # InsightFace setup
    # ------------------------------------------------------------------

    def _build_app(self, model_pack: str, device: str, det: int):
        """Construct and prepare a FaceAnalysis app, logging the active providers."""
        import onnxruntime as ort
        from insightface.app import FaceAnalysis

        if device == "cuda":
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
            ctx_id = 0
        else:
            providers = ["CPUExecutionProvider"]
            ctx_id = -1

        app = FaceAnalysis(name=model_pack, providers=providers)
        app.prepare(ctx_id=ctx_id, det_size=(det, det))

        active = ort.get_available_providers()
        if device == "cuda" and "CUDAExecutionProvider" not in active:
            self.get_logger().warn(
                "face_device=cuda requested but CUDAExecutionProvider is unavailable — "
                "running on CPU. Install a JetPack-matched onnxruntime-gpu wheel for GPU."
            )
        else:
            self.get_logger().info(f"onnxruntime providers: {active}")
        return app

    def _embed_largest(self, frame_bgr):
        """Return the normed embedding of the largest face in a frame, or None."""
        face = self._largest_face(self._app.get(frame_bgr))
        return None if face is None else face.normed_embedding

    @staticmethod
    def _largest_face(faces):
        """Pick the face with the biggest bounding-box area."""
        if not faces:
            return None
        return max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))

    # ------------------------------------------------------------------
    # Image callback
    # ------------------------------------------------------------------

    def _on_image(self, msg: Image) -> None:
        now = time.monotonic()
        if now - self._last_time < self._min_interval:
            return
        self._last_time = now

        try:
            frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as exc:
            self.get_logger().error(f"CvBridge conversion error: {exc}")
            return

        faces = self._app.get(frame)

        det_array = Detection2DArray()
        det_array.header = msg.header
        names = []
        annotated = frame.copy() if self._img_pub is not None else None

        for face in faces:
            name, sim = self._db.identify(face.normed_embedding)
            det_array.detections.append(self._to_detection2d(face.bbox, name, sim, msg.header))
            if name != "Unknown":
                names.append(name)
            if annotated is not None:
                self._draw_face(annotated, face.bbox, name, sim)

        self._faces_pub.publish(det_array)
        # Deduplicate while preserving order so the conversational layer gets a clean list.
        unique = list(dict.fromkeys(names))
        self._names_pub.publish(String(data=", ".join(unique)))

        if annotated is not None:
            try:
                out = self._bridge.cv2_to_imgmsg(annotated, encoding="bgr8")
                out.header = msg.header
                self._img_pub.publish(out)
            except Exception as exc:
                self.get_logger().warn(f"Annotated image publish failed: {exc}")

    def _to_detection2d(self, bbox, name, score, header) -> Detection2D:
        """Convert an InsightFace bbox + identity into a ROS2 Detection2D."""
        x1, y1, x2, y2 = [float(v) for v in bbox]
        det = Detection2D()
        det.header = header
        hyp = ObjectHypothesis()
        hyp.class_id = name
        hyp.score = float(score)
        hyp_pose = ObjectHypothesisWithPose()
        hyp_pose.hypothesis = hyp
        det.results.append(hyp_pose)
        box = BoundingBox2D()
        box.center.position.x = (x1 + x2) / 2.0
        box.center.position.y = (y1 + y2) / 2.0
        box.center.theta = 0.0
        box.size_x = x2 - x1
        box.size_y = y2 - y1
        det.bbox = box
        return det

    @staticmethod
    def _draw_face(frame, bbox, name, sim) -> None:
        x1, y1, x2, y2 = [int(v) for v in bbox]
        known = name != "Unknown"
        color = (0, 255, 0) if known else (0, 165, 255)  # green known, orange unknown
        label = f"{name} {sim:.2f}" if known else "Unknown"
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, label, (x1, max(0, y1 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)

    # ------------------------------------------------------------------
    # Reload callback (DB populated out-of-band by the web enroller)
    # ------------------------------------------------------------------

    def _on_reload(self, _msg: Empty) -> None:
        """Re-scan face_db_path and re-embed every photo (no restart needed)."""
        self.get_logger().info("Reloading face DB from disk…")
        self._load_db(rebuild=True)

    def _on_threshold(self, msg: Float32) -> None:
        """Apply a new cosine-similarity match floor live (from the enrollment UI)."""
        self._db.threshold = max(0.0, min(1.0, float(msg.data)))
        self.get_logger().info(f"Face match threshold set to {self._db.threshold:.2f}")


def main(args=None):
    rclpy.init(args=args)
    node = FaceRecognitionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
