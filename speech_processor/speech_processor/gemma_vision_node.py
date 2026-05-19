#!/usr/bin/env python3

# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

"""
Gemma Vision Node — scene understanding via Gemma 4 E4B (llama.cpp sidecar).

Subscribes to /camera/image_raw, rate-limits frames, sends each one to a
local llama.cpp instance running Gemma 4 E4B via the OpenAI-compatible
/v1/chat/completions endpoint, and publishes a natural-language scene
description.  Replaces yolo_detector_node in the Windows GPU profile.

Unlike YOLO (bounding boxes + class IDs), this node produces human-readable
text — suitable for conversational queries such as "what do you see?" rather
than structured downstream perception pipelines.

Subscriptions:
  camera_topic  (sensor_msgs/Image)   — default /camera/image_raw

Publications:
  /scene_description     (std_msgs/String)   — plain-text scene description
  /gemma_annotated_image (sensor_msgs/Image) — frame with description overlaid

Parameters:
  llama_cpp_host (str,   default http://llama_cpp:8080)
  model          (str,   default gemma)
  vision_prompt  (str,   default — see _DEFAULT_PROMPT)
  inference_rate (float, default 0.5 Hz — one inference every 2 seconds)
  camera_topic   (str,   default /camera/image_raw)
"""

import base64
import textwrap
import time

import cv2
import numpy as np
import requests
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String


_DEFAULT_PROMPT = (
    "Describe what you see in one or two sentences. "
    "Mention any people, animals, objects, or obstacles and their approximate positions."
)


class GemmaVisionNode(Node):

    def __init__(self):
        super().__init__("gemma_vision_node")

        self.declare_parameter("llama_cpp_host", "http://llama_cpp:8080")
        self.declare_parameter("model", "gemma")
        self.declare_parameter("vision_prompt", _DEFAULT_PROMPT)
        self.declare_parameter("inference_rate", 0.5)
        self.declare_parameter("camera_topic", "/camera/image_raw")

        self._llama_cpp_host = self.get_parameter("llama_cpp_host").value
        self._model          = self.get_parameter("model").value
        self._prompt       = self.get_parameter("vision_prompt").value
        self._min_interval = 1.0 / max(0.01, float(self.get_parameter("inference_rate").value))
        camera_topic       = self.get_parameter("camera_topic").value

        self._bridge    = CvBridge()
        self._last_time = 0.0

        self._desc_pub = self.create_publisher(String, "/scene_description", 1)
        self._img_pub  = self.create_publisher(Image, "/gemma_annotated_image", 1)

        self.create_subscription(
            Image, camera_topic, self._on_image, qos_profile_sensor_data
        )

        self.get_logger().info(
            f"gemma_vision_node ready — model={self._model} via {self._llama_cpp_host}, "
            f"rate={1.0 / self._min_interval:.2f} Hz, topic={camera_topic}"
        )

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

        # Encode frame as JPEG and base64 for the llama.cpp OpenAI-compatible vision API
        _, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        img_b64 = base64.b64encode(jpg.tobytes()).decode("utf-8")

        try:
            resp = requests.post(
                f"{self._llama_cpp_host}/v1/chat/completions",
                json={
                    "model": self._model,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": self._prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{img_b64}",
                                },
                            },
                        ],
                    }],
                    "stream": False,
                },
                timeout=30,
            )
            resp.raise_for_status()
            description = resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            self.get_logger().warn(f"llama.cpp vision request failed: {exc}")
            return

        self._desc_pub.publish(String(data=description))
        self.get_logger().info(f"Scene: {description[:120]}")

        # Annotate the frame with the description and publish
        annotated = self._overlay_text(frame.copy(), description)
        try:
            ann_msg = self._bridge.cv2_to_imgmsg(annotated, encoding="bgr8")
            ann_msg.header = msg.header
            self._img_pub.publish(ann_msg)
        except Exception as exc:
            self.get_logger().warn(f"Annotated image publish failed: {exc}")

    # ------------------------------------------------------------------
    # Text overlay helper
    # ------------------------------------------------------------------

    def _overlay_text(self, frame: np.ndarray, text: str) -> np.ndarray:
        lines = textwrap.wrap(text, width=60)
        x, y0, dy = 10, 30, 22
        font  = cv2.FONT_HERSHEY_SIMPLEX
        scale = 0.55
        thick = 1
        for i, line in enumerate(lines[:6]):   # cap at 6 lines
            y = y0 + i * dy
            # Dark outline for readability on any background
            cv2.putText(frame, line, (x, y), font, scale, (0, 0, 0), thick + 2, cv2.LINE_AA)
            cv2.putText(frame, line, (x, y), font, scale, (255, 255, 255), thick, cv2.LINE_AA)
        return frame


def main(args=None):
    rclpy.init(args=args)
    node = GemmaVisionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
