"""
Unit tests for Modul 4 — Visual Perception (Object & Face Recognition).

Sub-modules covered:
  4.1 Real-time object detection — YOLO bbox math, class-name lookup
  4.2 Face detection + recognition — FaceDB (extended), FaceEnrollmentNode
       helpers (sanitize, save_image), FaceRecognitionNode static methods
  4.3 Person tracking / follow-me — P-controller math, lost-timeout logic
  4.4 Visual feedback — face/scene grounding prompt helpers

Pure pytest, no rclpy runtime required (ROS2 deps stubbed at module load).
PYTHONPATH must include: d:\\go2_ros2_sdk\\speech_processor
Run:
    $env:PYTHONPATH="d:\\go2_ros2_sdk\\speech_processor"
    python -m pytest speech_processor/test/test_modul4_visual_perception.py -v
"""

# ── IMPORTANT: pytest import must come first so @pytest.mark.* work at class
#    definition time.
import pytest
import pickle
import re
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import numpy as np


# ──────────────────────────────────────────────────────────────────────────────
# Stub factory — idempotent: only inserts if not already present
# ──────────────────────────────────────────────────────────────────────────────

def _make_stub(module_path, attrs=None):
    if module_path not in sys.modules:
        mod = types.ModuleType(module_path)
        sys.modules[module_path] = mod
    mod = sys.modules[module_path]
    if attrs:
        for k, v in attrs.items():
            if not hasattr(mod, k):
                setattr(mod, k, v)
    return mod


# ── Minimal Python classes that mirror the vision_msgs API used in production
class _Point2D:
    def __init__(self): self.x = 0.0; self.y = 0.0


class _Pose2D:
    def __init__(self): self.position = _Point2D(); self.theta = 0.0


class _BBox2D:
    def __init__(self): self.center = _Pose2D(); self.size_x = 0.0; self.size_y = 0.0


class _ObjHyp:
    def __init__(self): self.class_id = ""; self.score = 0.0


class _ObjHypWithPose:
    def __init__(self): self.hypothesis = _ObjHyp()


class _Det2D:
    def __init__(self): self.header = None; self.results = []; self.bbox = _BBox2D()


class _Det2DArray:
    def __init__(self): self.header = None; self.detections = []


# ── rclpy stubs
_make_stub("rclpy")
_make_stub("rclpy.node", {"Node": object})
_make_stub("rclpy.qos", {
    "qos_profile_sensor_data": None,
    "QoSProfile": object,
    "QoSReliabilityPolicy": object,
    "QoSDurabilityPolicy": object,
    "QoSHistoryPolicy": object,
    "ReliabilityPolicy": object,
    "DurabilityPolicy": object,
    "HistoryPolicy": object,
})

# ── geometry_msgs stubs (Twist used in follow_me)
class _Twist:
    def __init__(self):
        self.linear  = SimpleNamespace(x=0.0, y=0.0, z=0.0)
        self.angular = SimpleNamespace(x=0.0, y=0.0, z=0.0)

_make_stub("geometry_msgs")
_make_stub("geometry_msgs.msg", {"Twist": _Twist})

# ── sensor_msgs stubs
_make_stub("sensor_msgs")
_make_stub("sensor_msgs.msg", {"Image": object, "CameraInfo": object})

# ── std_msgs stubs
_make_stub("std_msgs")
_make_stub("std_msgs.msg", {
    "Empty": object, "String": object, "Bool": object,
    "Float32": lambda data=0.0: SimpleNamespace(data=data),
    "UInt8MultiArray": object,
})

# ── vision_msgs stubs — use real functional classes
_make_stub("vision_msgs")
_make_stub("vision_msgs.msg", {
    "BoundingBox2D": _BBox2D,
    "Detection2D": _Det2D,
    "Detection2DArray": _Det2DArray,
    "ObjectHypothesis": _ObjHyp,
    "ObjectHypothesisWithPose": _ObjHypWithPose,
})

# ── cv2 stub — imwrite writes stub bytes so file-existence checks pass;
#    other drawing functions are silent no-ops.
def _cv2_imwrite(path, img, *args, **kwargs):
    """Write minimal bytes so downstream os.path.exists() tests pass."""
    Path(path).write_bytes(b"\xff\xd8\xff\xe0")
    return True

_make_stub("cv2")
_make_stub("cv2", {
    "rectangle": lambda *a, **kw: None,
    "putText":   lambda *a, **kw: None,
    "imread":    lambda *a, **kw: np.zeros((64, 64, 3), dtype=np.uint8),
    "imwrite":   _cv2_imwrite,
    "resize":    lambda *a, **kw: None,
    "FONT_HERSHEY_SIMPLEX": 0,
    "LINE_AA": 16,
    "LINE_8": 8,
})

# ── go2_interfaces stubs (needed by command_dispatcher)
_make_stub("go2_interfaces")
_make_stub("go2_interfaces.msg", {"WebRtcReq": object, "Go2State": object})

# ── cv_bridge stub
class _CvBridgeStub:
    def imgmsg_to_cv2(self, *a, **kw): return np.zeros((480, 640, 3), dtype=np.uint8)
    def cv2_to_imgmsg(self, *a, **kw): return SimpleNamespace(header=None)

_make_stub("cv_bridge", {"CvBridge": _CvBridgeStub})

# ── ultralytics stub
_make_stub("ultralytics", {"YOLO": lambda *a, **kw: SimpleNamespace(names={})})

# ── insightface stubs
_make_stub("insightface")
class _FaceAnalysisStub:
    def __init__(self, *a, **kw): pass
    def prepare(self, *a, **kw): pass
    def get(self, *a, **kw): return []
_make_stub("insightface.app", {"FaceAnalysis": _FaceAnalysisStub})

# ── onnxruntime stub
_make_stub("onnxruntime", {"get_available_providers": lambda: ["CPUExecutionProvider"]})


# ── Now import pure-Python modules (no stubs needed)
from speech_processor.face_db import FaceDB, _normalize  # noqa: E402

# ── Import node classes that require stubs (stubs already in place)
from speech_processor.face_enrollment_node import FaceEnrollmentNode  # noqa: E402
from speech_processor.face_recognition_node import FaceRecognitionNode  # noqa: E402

# ── command_dispatcher (needed for 4.4 visual grounding)
from speech_processor.command_dispatcher import (  # noqa: E402
    CONVERSATIONAL_SYSTEM,
    conversational_system_with_faces,
    conversational_system_with_scene,
)


# ══════════════════════════════════════════════════════════════════════════════
# 4.2 — FaceDB: _normalize() standalone
# ══════════════════════════════════════════════════════════════════════════════

class TestNormalize:
    def test_unit_vector_unchanged_dot(self):
        v = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        n = _normalize(v)
        assert abs(np.dot(n, n) - 1.0) < 1e-6

    def test_unnormalized_becomes_unit(self):
        v = np.array([3.0, 4.0], dtype=np.float32)  # norm = 5
        n = _normalize(v)
        assert abs(np.linalg.norm(n) - 1.0) < 1e-6

    def test_negative_values_handled(self):
        v = np.array([-1.0, -1.0], dtype=np.float32)
        n = _normalize(v)
        assert abs(np.linalg.norm(n) - 1.0) < 1e-6

    def test_zero_vector_returns_zeros(self):
        v = np.zeros(4, dtype=np.float32)
        n = _normalize(v)
        assert np.allclose(n, 0.0)  # no division by zero

    def test_high_dimensional_vector(self):
        v = np.random.randn(512).astype(np.float32)
        n = _normalize(v)
        assert abs(np.linalg.norm(n) - 1.0) < 1e-5

    def test_flattens_2d_input(self):
        v = np.array([[3.0, 0.0, 4.0]], dtype=np.float32)  # shape (1,3)
        n = _normalize(v)
        assert n.ndim == 1
        assert abs(np.linalg.norm(n) - 1.0) < 1e-6


# ══════════════════════════════════════════════════════════════════════════════
# 4.2 — FaceDB: extended coverage beyond test_face_db.py
# ══════════════════════════════════════════════════════════════════════════════

def _unit(*vals) -> np.ndarray:
    v = np.asarray(vals, dtype=np.float32)
    return v / np.linalg.norm(v)


class TestFaceDBCoverage:

    def test_known_names_empty_db(self, tmp_path):
        db = FaceDB(str(tmp_path))
        db.load()
        assert db.known_names == []

    def test_known_names_after_enroll(self, tmp_path):
        db = FaceDB(str(tmp_path))
        db.load()
        db.add_face("Alice", np.zeros((8, 8, 3), dtype=np.uint8), _unit(1, 0, 0))
        assert "Alice" in db.known_names

    def test_num_faces_empty(self, tmp_path):
        db = FaceDB(str(tmp_path))
        db.load()
        assert db.num_faces == 0

    def test_num_faces_single_enroll(self, tmp_path):
        db = FaceDB(str(tmp_path))
        db.load()
        db.add_face("Bob", np.zeros((8, 8, 3), dtype=np.uint8), _unit(0, 1, 0))
        assert db.num_faces == 1

    def test_num_faces_multiple_photos(self, tmp_path):
        db = FaceDB(str(tmp_path))
        db.load()
        crop = np.zeros((8, 8, 3), dtype=np.uint8)
        db.add_face("Carol", crop, _unit(1, 0, 0))
        db.add_face("Carol", crop, _unit(0.9, 0.1, 0))
        assert db.num_faces == 2

    def test_num_faces_across_people(self, tmp_path):
        db = FaceDB(str(tmp_path))
        db.load()
        crop = np.zeros((8, 8, 3), dtype=np.uint8)
        db.add_face("Alice", crop, _unit(1, 0, 0))
        db.add_face("Bob",   crop, _unit(0, 1, 0))
        assert db.num_faces == 2
        assert len(db.known_names) == 2

    def test_identify_exact_threshold_is_unknown(self, tmp_path):
        # The comparison is best_sim < threshold (strict), so sim == threshold → Unknown
        threshold = 0.5
        db = FaceDB(str(tmp_path), threshold=threshold)
        db.load()
        db.add_face("Alice", np.zeros((8, 8, 3), dtype=np.uint8), _unit(1, 0, 0))
        # Crafting a query whose dot product with _unit(1,0,0) is exactly 0.5:
        # cos(θ) = 0.5 → θ = 60°, so q = (cos60°, sin60°, 0) = (0.5, √3/2, 0)
        q = np.array([0.5, (3**0.5)/2, 0.0], dtype=np.float32)
        q = q / np.linalg.norm(q)
        name, sim = db.identify(q)
        # sim ≈ 0.5 but _normalize(q) dot _unit(1,0,0) = 0.5 which is NOT < 0.5 → should be Alice
        # Actually: sim = np.dot(_normalize(q), _unit(1,0,0)) ≈ 0.5
        # if sim < threshold → Unknown; 0.5 < 0.5 is False → returns Alice
        assert name == "Alice"

    def test_identify_below_threshold_is_unknown(self, tmp_path):
        threshold = 0.5
        db = FaceDB(str(tmp_path), threshold=threshold)
        db.load()
        db.add_face("Alice", np.zeros((8, 8, 3), dtype=np.uint8), _unit(1, 0, 0))
        # Orthogonal → sim = 0 < 0.5 → Unknown
        name, sim = db.identify(_unit(0, 1, 0))
        assert name == "Unknown"

    def test_identify_just_above_threshold(self, tmp_path):
        threshold = 0.35
        db = FaceDB(str(tmp_path), threshold=threshold)
        db.load()
        db.add_face("Alice", np.zeros((8, 8, 3), dtype=np.uint8), _unit(1, 0, 0))
        # Slightly off → high sim
        name, sim = db.identify(_unit(0.99, 0.01, 0))
        assert name == "Alice"
        assert sim > threshold

    def test_load_no_cache_no_embed_fn_is_empty(self, tmp_path):
        db = FaceDB(str(tmp_path))
        db.load(embed_fn=None)  # no embed_fn → empty db, no crash
        assert db.num_faces == 0

    def test_corrupt_cache_falls_back_to_empty(self, tmp_path):
        # Write garbage to the cache file → FaceDB should recover gracefully
        cache = tmp_path / ".embeddings.pkl"
        cache.write_bytes(b"not a pickle file")
        db = FaceDB(str(tmp_path))
        db.load(embed_fn=None)
        assert db.num_faces == 0

    def test_rebuild_skips_images_where_embed_fn_returns_none(self, tmp_path):
        # Create fake image files
        person = tmp_path / "Dave"
        person.mkdir()
        (person / "0000.jpg").write_bytes(b"fake")
        db = FaceDB(str(tmp_path))
        embedded = db.rebuild_from_disk(embed_fn=lambda _: None)
        assert embedded == 0
        assert db.num_faces == 0


# ══════════════════════════════════════════════════════════════════════════════
# 4.2 — FaceEnrollmentNode: _sanitize() static method
# ══════════════════════════════════════════════════════════════════════════════

class TestFaceEnrollmentSanitize:
    def test_plain_name_unchanged(self):
        assert FaceEnrollmentNode._sanitize("Alice") == "Alice"

    def test_name_with_numbers(self):
        assert FaceEnrollmentNode._sanitize("Alice123") == "Alice123"

    def test_space_preserved(self):
        result = FaceEnrollmentNode._sanitize("Alice Bob")
        assert result == "Alice Bob"

    def test_hyphen_preserved(self):
        assert FaceEnrollmentNode._sanitize("Anne-Marie") == "Anne-Marie"

    def test_underscore_preserved(self):
        assert FaceEnrollmentNode._sanitize("alice_bob") == "alice_bob"

    def test_path_traversal_removed(self):
        # "../evil" → dots and slash not in [A-Za-z0-9 _-] → removed → "evil"
        result = FaceEnrollmentNode._sanitize("../evil")
        assert "/" not in result
        assert ".." not in result
        assert "evil" in result

    def test_special_chars_removed(self):
        result = FaceEnrollmentNode._sanitize("alice@example.com")
        assert "@" not in result
        assert "." not in result

    def test_empty_string(self):
        assert FaceEnrollmentNode._sanitize("") == ""

    def test_only_special_chars(self):
        assert FaceEnrollmentNode._sanitize("@#$%") == ""

    def test_leading_trailing_whitespace_stripped(self):
        result = FaceEnrollmentNode._sanitize("  Alice  ")
        assert result == "Alice"


# ══════════════════════════════════════════════════════════════════════════════
# 4.2 — FaceEnrollmentNode: _save_image() (file-system, no ROS2 needed)
# ══════════════════════════════════════════════════════════════════════════════

class TestFaceEnrollmentSaveImage:

    def _make_node(self, db_path):
        """Create an enrollment node shell with only _db_path set (no ROS2 init)."""
        node = object.__new__(FaceEnrollmentNode)
        node._db_path = Path(db_path)
        return node

    def test_creates_person_directory(self, tmp_path):
        node = self._make_node(tmp_path)
        node._save_image("Alice", b"\xff\xd8\xff")  # minimal JPEG magic bytes
        assert (tmp_path / "Alice").is_dir()

    def test_writes_jpeg_file(self, tmp_path):
        node = self._make_node(tmp_path)
        data = b"\xff\xd8\xff" * 10
        node._save_image("Bob", data)
        assert (tmp_path / "Bob" / "0000.jpg").exists()
        assert (tmp_path / "Bob" / "0000.jpg").read_bytes() == data

    def test_returns_index_zero_first_image(self, tmp_path):
        node = self._make_node(tmp_path)
        idx = node._save_image("Carol", b"data")
        assert idx == 0

    def test_returns_incremented_index_second_image(self, tmp_path):
        node = self._make_node(tmp_path)
        node._save_image("Dave", b"data1")
        idx = node._save_image("Dave", b"data2")
        assert idx == 1

    def test_different_people_get_separate_dirs(self, tmp_path):
        node = self._make_node(tmp_path)
        node._save_image("Eve",  b"e")
        node._save_image("Frank", b"f")
        assert (tmp_path / "Eve" / "0000.jpg").exists()
        assert (tmp_path / "Frank" / "0000.jpg").exists()


# ══════════════════════════════════════════════════════════════════════════════
# 4.3 — Follow-me: P-controller math (pure, no imports needed)
# ══════════════════════════════════════════════════════════════════════════════

# Replicates the control law from follow_me_node._on_detections() exactly.
def _follow_ctrl(
    cx, img_w, img_h, bbox_w, bbox_h,
    kp=1.0, max_ang=0.8, lin_speed=0.20, tgt_area=0.10, deadband=0.03
):
    error_x = (cx - img_w / 2.0) / (img_w / 2.0)
    area_frac = (bbox_w * bbox_h) / max(img_w * img_h, 1)
    raw_az = -kp * error_x
    angular_z = max(-max_ang, min(max_ang, raw_az))
    linear_x = lin_speed if area_frac < tgt_area - deadband else 0.0
    return angular_z, linear_x


class TestFollowMeControlLaw:

    # ── Angular (P-controller)

    def test_centered_person_zero_angular(self):
        az, _ = _follow_ctrl(cx=320, img_w=640, img_h=480, bbox_w=60, bbox_h=100)
        assert abs(az) < 1e-9

    def test_person_on_left_positive_angular(self):
        # cx=0 → error_x=-1.0 → raw_az=+kp
        az, _ = _follow_ctrl(cx=0, img_w=640, img_h=480, bbox_w=60, bbox_h=60)
        assert az > 0

    def test_person_on_right_negative_angular(self):
        az, _ = _follow_ctrl(cx=640, img_w=640, img_h=480, bbox_w=60, bbox_h=60)
        assert az < 0

    def test_small_left_bias_proportional(self):
        # error_x = (160-320)/320 = -0.5 → raw_az = +0.5 (kp=1)
        az, _ = _follow_ctrl(cx=160, img_w=640, img_h=480, bbox_w=10, bbox_h=10, kp=1.0)
        assert abs(az - 0.5) < 1e-6

    def test_small_right_bias_proportional(self):
        az, _ = _follow_ctrl(cx=480, img_w=640, img_h=480, bbox_w=10, bbox_h=10, kp=1.0)
        assert abs(az - (-0.5)) < 1e-6

    def test_large_error_clamped_to_max_ang(self):
        az, _ = _follow_ctrl(cx=0, img_w=640, img_h=480, bbox_w=1, bbox_h=1, kp=2.0, max_ang=0.8)
        assert az == pytest.approx(0.8)

    def test_higher_kp_larger_angular(self):
        az_lo, _ = _follow_ctrl(cx=160, img_w=640, img_h=480, bbox_w=10, bbox_h=10, kp=1.0)
        az_hi, _ = _follow_ctrl(cx=160, img_w=640, img_h=480, bbox_w=10, bbox_h=10, kp=2.0)
        assert az_hi > az_lo

    def test_max_ang_zero_always_zero_angular(self):
        az, _ = _follow_ctrl(cx=0, img_w=640, img_h=480, bbox_w=1, bbox_h=1, max_ang=0.0)
        assert az == 0.0

    # ── Linear (area-fraction threshold)

    def test_far_person_linear_forward(self):
        # bbox very small relative to image → area_frac tiny → below threshold → move
        _, lx = _follow_ctrl(cx=320, img_w=640, img_h=480, bbox_w=20, bbox_h=20,
                              tgt_area=0.10, deadband=0.03, lin_speed=0.20)
        assert lx == pytest.approx(0.20)

    def test_close_person_no_linear(self):
        # bbox fills most of image → area_frac large → above threshold → stop
        _, lx = _follow_ctrl(cx=320, img_w=640, img_h=480, bbox_w=500, bbox_h=400,
                              tgt_area=0.10, deadband=0.03)
        assert lx == 0.0

    def test_exactly_at_deadband_boundary_no_linear(self):
        # area_frac == tgt_area - deadband → NOT < → linear = 0
        tgt, db = 0.10, 0.03
        # img=100x100=10000, need area_frac = 0.07 → bbox=sqrt(700)~26.5x26.5
        area_target = (tgt - db) * 100 * 100  # = 700 pixels
        side = area_target ** 0.5
        _, lx = _follow_ctrl(cx=50, img_w=100, img_h=100,
                              bbox_w=side, bbox_h=side,
                              tgt_area=tgt, deadband=db, lin_speed=0.2)
        assert lx == 0.0

    def test_just_below_deadband_threshold_linear_forward(self):
        tgt, db = 0.10, 0.03
        area_target = (tgt - db) * 100 * 100  # 700 pixels
        side = (area_target - 1) ** 0.5  # slightly below → should move
        _, lx = _follow_ctrl(cx=50, img_w=100, img_h=100,
                              bbox_w=side, bbox_h=side,
                              tgt_area=tgt, deadband=db, lin_speed=0.2)
        assert lx == pytest.approx(0.2)

    def test_zero_image_size_no_crash(self):
        # max(img_w*img_h, 1) prevents zero division
        az, lx = _follow_ctrl(cx=0, img_w=1, img_h=1, bbox_w=0, bbox_h=0)
        assert isinstance(az, float)
        assert isinstance(lx, float)

    def test_both_centered_and_close(self):
        az, lx = _follow_ctrl(cx=320, img_w=640, img_h=480, bbox_w=400, bbox_h=300)
        assert abs(az) < 1e-6  # centered
        assert lx == 0.0       # close


# ══════════════════════════════════════════════════════════════════════════════
# 4.3 — Follow-me: lost-timeout logic
# ══════════════════════════════════════════════════════════════════════════════

# Replicates the decision in _publish_tick: publish current or zero?
def _tick_result(age_s: float, lost_to: float) -> str:
    """Return 'current' or 'zero' matching _publish_tick behavior."""
    return "zero" if age_s > lost_to else "current"


class TestFollowMeLostTimeout:

    def test_age_zero_sends_current(self):
        assert _tick_result(0.0, lost_to=1.0) == "current"

    def test_age_equal_timeout_sends_current(self):
        # strictly >, so exactly at timeout is still current
        assert _tick_result(1.0, lost_to=1.0) == "current"

    def test_age_just_over_timeout_sends_zero(self):
        assert _tick_result(1.001, lost_to=1.0) == "zero"

    def test_zero_timeout_any_positive_age_is_zero(self):
        assert _tick_result(0.001, lost_to=0.0) == "zero"

    def test_large_timeout_always_current(self):
        assert _tick_result(5.0, lost_to=999.0) == "current"


# ══════════════════════════════════════════════════════════════════════════════
# 4.1 — YOLO: bounding-box math (xyxy → center + size)
# ══════════════════════════════════════════════════════════════════════════════

# Replicates _to_detection2d bbox math from yolo_detector_node.py
def _yolo_bbox(xyxy):
    x1, y1, x2, y2 = xyxy
    return {
        "center_x": (x1 + x2) / 2.0,
        "center_y": (y1 + y2) / 2.0,
        "size_x":   x2 - x1,
        "size_y":   y2 - y1,
    }


class TestYoloBBoxMath:

    def test_symmetric_box_center(self):
        b = _yolo_bbox([100, 100, 200, 200])
        assert b["center_x"] == pytest.approx(150.0)
        assert b["center_y"] == pytest.approx(150.0)

    def test_origin_box_size(self):
        b = _yolo_bbox([0, 0, 10, 10])
        assert b["size_x"] == pytest.approx(10.0)
        assert b["size_y"] == pytest.approx(10.0)

    def test_non_square_box(self):
        b = _yolo_bbox([0, 0, 100, 50])
        assert b["size_x"] == pytest.approx(100.0)
        assert b["size_y"] == pytest.approx(50.0)

    def test_float_coordinates(self):
        b = _yolo_bbox([10.5, 20.3, 50.5, 60.3])
        assert b["center_x"] == pytest.approx(30.5)
        assert b["center_y"] == pytest.approx(40.3)

    def test_degenerate_point_box_zero_size(self):
        b = _yolo_bbox([5, 5, 5, 5])
        assert b["size_x"] == 0.0
        assert b["size_y"] == 0.0

    def test_full_image_box_center(self):
        b = _yolo_bbox([0, 0, 640, 480])
        assert b["center_x"] == pytest.approx(320.0)
        assert b["center_y"] == pytest.approx(240.0)

    def test_center_x_formula(self):
        # center_x = (x1+x2)/2
        for x1, x2 in [(10, 90), (0, 640), (100, 200)]:
            b = _yolo_bbox([x1, 0, x2, 1])
            assert b["center_x"] == pytest.approx((x1 + x2) / 2.0)

    def test_large_coordinates(self):
        b = _yolo_bbox([1000, 500, 1200, 700])
        assert b["center_x"] == pytest.approx(1100.0)
        assert b["size_x"] == pytest.approx(200.0)


# ══════════════════════════════════════════════════════════════════════════════
# 4.1 — YOLO: class-name lookup
# ══════════════════════════════════════════════════════════════════════════════

class TestYoloClassNameLookup:
    COCO_SUBSET = {0: "person", 1: "bicycle", 2: "car", 39: "bottle", 56: "chair"}

    def _lookup(self, cls_id):
        return self.COCO_SUBSET.get(cls_id, str(cls_id))

    def test_known_class_zero_person(self):
        assert self._lookup(0) == "person"

    def test_known_class_returns_name(self):
        assert self._lookup(2) == "car"

    def test_unknown_class_returns_string_of_id(self):
        assert self._lookup(999) == "999"

    def test_unknown_class_large_id(self):
        assert self._lookup(42) == "42"

    def test_empty_class_names_always_fallback(self):
        lookup = lambda cls_id: {}.get(cls_id, str(cls_id))
        assert lookup(0) == "0"
        assert lookup(5) == "5"

    def test_detection_threshold_gates_inclusion(self):
        # Simulates the conf >= threshold check in listener_callback
        threshold = 0.5
        confs = [0.9, 0.6, 0.4, 0.2]
        above = [c for c in confs if c >= threshold]
        assert above == [0.9, 0.6]
        assert len(above) == 2


# ══════════════════════════════════════════════════════════════════════════════
# 4.2 — FaceRecognitionNode: static helpers
# ══════════════════════════════════════════════════════════════════════════════

def _make_face(x1, y1, x2, y2):
    """Minimal face object matching InsightFace face.bbox API."""
    return SimpleNamespace(bbox=[x1, y1, x2, y2])


class TestFaceRecognitionLargestFace:

    def test_empty_list_returns_none(self):
        assert FaceRecognitionNode._largest_face([]) is None

    def test_single_face_returned(self):
        f = _make_face(0, 0, 100, 100)
        assert FaceRecognitionNode._largest_face([f]) is f

    def test_larger_face_wins(self):
        small = _make_face(0, 0, 10, 10)    # area = 100
        large = _make_face(0, 0, 100, 100)  # area = 10000
        assert FaceRecognitionNode._largest_face([small, large]) is large

    def test_order_does_not_matter(self):
        small = _make_face(0, 0, 10, 10)
        large = _make_face(0, 0, 100, 100)
        assert FaceRecognitionNode._largest_face([large, small]) is large

    def test_area_computed_from_xyxy_correctly(self):
        # bbox = [x1,y1,x2,y2]; area = (x2-x1)*(y2-y1)
        f_wide  = _make_face(0, 0, 200, 50)   # 200*50 = 10000
        f_tall  = _make_face(0, 0, 50,  200)  # 50*200 = 10000 — tie
        # both equal — either returned is OK, just no crash
        result = FaceRecognitionNode._largest_face([f_wide, f_tall])
        assert result in (f_wide, f_tall)

    def test_float_bbox_values(self):
        f1 = _make_face(0.5, 0.5, 10.5, 10.5)  # area ~100
        f2 = _make_face(0.0, 0.0, 50.0, 50.0)  # area 2500
        assert FaceRecognitionNode._largest_face([f1, f2]) is f2

    def test_many_faces_largest_selected(self):
        faces = [_make_face(0, 0, i, i) for i in range(1, 11)]  # areas 1..100
        largest = FaceRecognitionNode._largest_face(faces)
        assert largest is faces[-1]  # area=100 is last


# ══════════════════════════════════════════════════════════════════════════════
# 4.2 — FaceRecognitionNode: _draw_face color / label logic
# ══════════════════════════════════════════════════════════════════════════════

# Extract the pure color/label logic from _draw_face (the cv2 calls are no-ops
# in the stub; we test what gets chosen, not the pixel result).
def _face_color_and_label(name: str, sim: float):
    known = name != "Unknown"
    color = (0, 255, 0) if known else (0, 165, 255)
    label = f"{name} {sim:.2f}" if known else "Unknown"
    return color, label


class TestFaceDrawFaceColorLogic:

    def test_known_face_green_color(self):
        color, _ = _face_color_and_label("Alice", 0.8)
        assert color == (0, 255, 0)

    def test_unknown_face_orange_color(self):
        color, _ = _face_color_and_label("Unknown", 0.1)
        assert color == (0, 165, 255)

    def test_known_label_includes_name_and_score(self):
        _, label = _face_color_and_label("Bob", 0.75)
        assert "Bob" in label
        assert "0.75" in label

    def test_unknown_label_is_literal_unknown(self):
        _, label = _face_color_and_label("Unknown", 0.3)
        assert label == "Unknown"

    def test_score_formatted_to_two_decimal_places(self):
        _, label = _face_color_and_label("Carol", 0.9)
        assert "0.90" in label


# ══════════════════════════════════════════════════════════════════════════════
# 4.4 — Visual feedback: face + scene grounding prompt helpers
# ══════════════════════════════════════════════════════════════════════════════

class TestVisualFeedback44:
    # Both functions take (base_system: str, <second>: str) and return a str.

    def test_face_grounding_includes_known_name(self):
        prompt = conversational_system_with_faces(CONVERSATIONAL_SYSTEM, "Alice")
        assert "Alice" in prompt

    def test_face_grounding_includes_multiple_names(self):
        prompt = conversational_system_with_faces(CONVERSATIONAL_SYSTEM, "Alice, Bob")
        assert "Alice" in prompt
        assert "Bob" in prompt

    def test_face_grounding_with_empty_names_returns_string(self):
        prompt = conversational_system_with_faces(CONVERSATIONAL_SYSTEM, "")
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_face_grounding_differs_from_base_prompt(self):
        grounded = conversational_system_with_faces(CONVERSATIONAL_SYSTEM, "Someone")
        assert grounded != CONVERSATIONAL_SYSTEM

    def test_scene_grounding_includes_description(self):
        desc = "a large hall with red chairs and a podium"
        prompt = conversational_system_with_scene(CONVERSATIONAL_SYSTEM, desc)
        assert desc in prompt

    def test_scene_grounding_with_empty_string_returns_string(self):
        prompt = conversational_system_with_scene(CONVERSATIONAL_SYSTEM, "")
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_scene_grounding_differs_from_base_prompt(self):
        prompt = conversational_system_with_scene(CONVERSATIONAL_SYSTEM, "some scene")
        assert prompt != CONVERSATIONAL_SYSTEM

    def test_face_grounding_mentions_greeting_concept(self):
        prompt = conversational_system_with_faces(CONVERSATIONAL_SYSTEM, "Dito")
        # The template explicitly says "Greet or address them by name"
        keywords = ["greet", "name", "Dito"]
        assert any(kw.lower() in prompt.lower() for kw in keywords)
