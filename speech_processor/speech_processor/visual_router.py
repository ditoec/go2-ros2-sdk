# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

"""Routing for the robot's `look_around` tool.

The robot has three ways to answer a question about what it can see, with very
different cost and capability profiles:

  yolo    -- /detected_objects, already produced at camera rate. Instant, free,
             and precise about *which* known objects are present and where, but
             limited to the COCO class list and says nothing about context.
  openai  -- the camera frame attached to the live Realtime session. Best
             reasoning by far (reads text, judges context, answers open
             questions) and needs no extra service, but costs image tokens per
             look and requires network.
  gemma   -- /scene_description from the on-board vision model. Offline and
             free, but slow on a Jetson and coarse.

Choosing between them is pure logic, kept here so it is testable without ROS,
a camera, or an API key.
"""

from __future__ import annotations

from typing import Iterable, Optional, Sequence

# Ultralytics COCO class names -- what yolo_detector can actually report.
COCO_CLASSES = (
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck",
    "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench",
    "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra",
    "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
    "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove",
    "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup",
    "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
    "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
    "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear",
    "hair drier", "toothbrush",
)

# Everyday words the speaker is likely to use for a COCO class.
_SYNONYMS = {
    "person": ("person", "people", "someone", "anybody", "anyone", "human", "orang"),
    "sports ball": ("ball", "bola"),
    "cell phone": ("phone", "mobile", "handphone", "hp"),
    "tv": ("tv", "television", "monitor", "screen"),
    "couch": ("couch", "sofa"),
    "potted plant": ("plant", "pot plant"),
    "dining table": ("table", "meja"),
    "chair": ("chair", "kursi"),
    "bottle": ("bottle", "botol"),
    "cup": ("cup", "mug", "gelas"),
    "laptop": ("laptop", "notebook"),
    "dog": ("dog", "anjing"),
    "cat": ("cat", "kucing"),
    "book": ("book", "buku"),
    "backpack": ("backpack", "bag", "tas"),
}

DEFAULT_PATH_PRIORITY = ("yolo", "openai", "gemma")


def match_coco_classes(query: str) -> list[str]:
    """COCO classes the query plausibly asks about, most specific first.

    Multi-word names are matched before single words so "sports ball" wins over
    a bare "ball", and "cell phone" is not shadowed by an unrelated "phone".
    """
    q = " " + (query or "").lower().strip() + " "
    hits: list[str] = []

    def _add(name: str) -> None:
        if name not in hits:
            hits.append(name)

    # Explicit synonyms first -- they carry the multi-word and non-English cases.
    for cls, words in _SYNONYMS.items():
        for w in words:
            if " " + w + " " in q:
                _add(cls)
                break
    # Then the raw class names, longest first so compound names win.
    for cls in sorted(COCO_CLASSES, key=len, reverse=True):
        if " " + cls + " " in q:
            _add(cls)
    return hits


def choose_visual_path(
    query: str,
    *,
    yolo_ok: bool = False,
    openai_ok: bool = False,
    gemma_ok: bool = False,
    priority: Sequence[str] = DEFAULT_PATH_PRIORITY,
) -> Optional[str]:
    """Cheapest available path that can actually answer `query`.

    yolo is only offered when the question names an object it knows -- asking it
    "what is happening here" would otherwise return a bare object list and pass
    it off as scene understanding. Returns None when nothing can answer.
    """
    available = {"yolo": yolo_ok, "openai": openai_ok, "gemma": gemma_ok}
    for path in priority:
        if not available.get(path):
            continue
        if path == "yolo" and not match_coco_classes(query):
            continue
        return path
    return None


def describe_position(cx: float) -> str:
    """Horizontal position of a detection, as a person would say it."""
    if cx < 0.34:
        return "on the left"
    if cx > 0.66:
        return "on the right"
    return "straight ahead"


def summarize_detections(
    detections: Iterable[tuple], wanted: Optional[Sequence[str]] = None
) -> str:
    """Turn detections into one sentence for the model to speak from.

    `detections` is (class_name, score, cx) with cx normalised 0..1. When
    `wanted` is given, anything else is dropped -- the answer to "do you see a
    chair" should not list every object in the room.
    """
    dets = [d for d in detections if not wanted or d[0] in wanted]
    if not dets:
        if wanted:
            return "I cannot see " + " or ".join(wanted) + " right now."
        return "I cannot see anything I recognise right now."

    grouped: dict[str, list[float]] = {}
    for name, _score, cx in dets:
        grouped.setdefault(name, []).append(cx)

    parts = []
    for name, xs in grouped.items():
        if len(xs) == 1:
            parts.append(f"a {name} {describe_position(xs[0])}")
        else:
            parts.append(f"{len(xs)} {name}s")
    return "I can see " + ", ".join(parts) + "."
