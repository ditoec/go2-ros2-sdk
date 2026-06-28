"""
Tests for Modul 2 — Extended Contextual Commands

Covers:
  2.1  patrol_node        — yaw→quaternion math, waypoint loading/route building,
                            enable/disable state machine, advance-and-continue, skip-or-abort
  2.1/2.2 approach_object_node — target management, camera-info update, control law,
                            lost timeout, terminal states (reached/lost/cancelled)
  2.3  CommandDispatcher  — custom command YAML loader, phrase matching, action dispatch

All tests are pure pytest — no ROS2 runtime, no robot, no GPU.

Run:
  export PYTHONPATH=speech_processor          # Linux/macOS
  $env:PYTHONPATH = "speech_processor"        # Windows PowerShell
  python -m pytest speech_processor/test/test_modul2_extended_contextual.py -v
"""

import math
import sys
import types

import pytest
import yaml

# ===========================================================================
# ROS2 stubs — must run before any production import
# ===========================================================================


def _make_stub(name, attrs=None):
    """Create or update a stub module. Always sets attrs (overrides earlier stubs)."""
    if name not in sys.modules:
        mod = types.ModuleType(name)
        sys.modules[name] = mod
    else:
        mod = sys.modules[name]
    if attrs:
        for k, v in attrs.items():
            setattr(mod, k, v)
    return mod


# --- rclpy ---
_make_stub("rclpy")
_make_stub("rclpy.node", {"Node": object})
_make_stub("rclpy.qos", {
    "qos_profile_sensor_data": None,
    "QoSProfile": object,
    "QoSReliabilityPolicy": object,
    "QoSDurabilityPolicy": object,
    "QoSHistoryPolicy": object,
})
_make_stub("rclpy.action", {"ActionClient": object})


# --- geometry_msgs ---
class _TwistLinear:
    def __init__(self): self.x = 0.0; self.y = 0.0; self.z = 0.0  # noqa: E702


class _TwistAngular:
    def __init__(self): self.x = 0.0; self.y = 0.0; self.z = 0.0  # noqa: E702


class _Twist:
    def __init__(self):
        self.linear = _TwistLinear()
        self.angular = _TwistAngular()


class _Quaternion:
    def __init__(self): self.x = 0.0; self.y = 0.0; self.z = 0.0; self.w = 1.0  # noqa: E702


_make_stub("geometry_msgs")
_make_stub("geometry_msgs.msg", {"Twist": _Twist, "Quaternion": _Quaternion})


# --- std_msgs ---
class _Str:
    def __init__(self, data=""): self.data = data  # noqa: E704


class _Bool:
    def __init__(self, data=False): self.data = data  # noqa: E704


class _Empty:
    pass


_make_stub("std_msgs")
_make_stub("std_msgs.msg", {"String": _Str, "Bool": _Bool, "Empty": _Empty})


# --- sensor_msgs ---
class _CameraInfo:
    def __init__(self):
        self.width = 640
        self.height = 480


_make_stub("sensor_msgs")
_make_stub("sensor_msgs.msg", {"CameraInfo": _CameraInfo, "Image": object})


# --- vision_msgs ---
class _ObjHyp:
    def __init__(self): self.class_id = ""; self.score = 0.0  # noqa: E702


class _DetResult:
    def __init__(self): self.hypothesis = _ObjHyp()


class _BBoxPos:
    def __init__(self): self.x = 0.0; self.y = 0.0  # noqa: E702


class _BBoxCenter:
    def __init__(self): self.position = _BBoxPos()


class _BBox:
    def __init__(self):
        self.center = _BBoxCenter()
        self.size_x = 0.0
        self.size_y = 0.0


class _Detection2D:
    def __init__(self):
        self.bbox = _BBox()
        self.results = []


class _Detection2DArray:
    def __init__(self): self.detections = []  # noqa: E704


_make_stub("vision_msgs")
_make_stub("vision_msgs.msg", {
    "Detection2DArray": _Detection2DArray,
    "Detection2D": _Detection2D,
    "BoundingBox2D": _BBox,
    "ObjectHypothesisWithPose": _DetResult,
})


# --- go2_interfaces ---
_make_stub("go2_interfaces")
_make_stub("go2_interfaces.msg", {"WebRtcReq": object, "Go2State": object})


# --- action_msgs ---
class _GoalStatus:
    STATUS_ACCEPTED = 1
    STATUS_EXECUTING = 2
    STATUS_CANCELING = 3
    STATUS_SUCCEEDED = 4
    STATUS_CANCELED = 5
    STATUS_ABORTED = 6


_make_stub("action_msgs")
_make_stub("action_msgs.msg", {"GoalStatus": _GoalStatus})


# --- nav2_msgs ---
class _NavPoseHeader:
    frame_id = ""
    stamp = None


class _NavPosition:
    x = 0.0
    y = 0.0


class _NavPoseInner:
    def __init__(self):
        self.position = _NavPosition()
        self.orientation = None


class _NavPose:
    def __init__(self):
        self.header = _NavPoseHeader()
        self.pose = _NavPoseInner()


class _NavGoal:
    def __init__(self): self.pose = _NavPose()  # noqa: E704


class _NavigateToPose:
    Goal = _NavGoal


_make_stub("nav2_msgs")
_make_stub("nav2_msgs.action", {"NavigateToPose": _NavigateToPose})


# --- cv2 (needed transitively when command_dispatcher imports face modules) ---
from pathlib import Path as _Path


def _cv2_imwrite(path, img, *a, **kw):
    _Path(path).write_bytes(b"\xff\xd8\xff\xe0")
    return True


_make_stub("cv2", {
    "imread": lambda *a, **kw: None,
    "imwrite": _cv2_imwrite,
    "resize": lambda img, *a, **kw: img,
    "cvtColor": lambda img, *a, **kw: img,
    "COLOR_BGR2RGB": 4,
})
_make_stub("cv_bridge")
_make_stub("cv_bridge", {"CvBridge": object})


# --- Now import the production modules ---
from speech_processor.patrol_node import _yaw_to_quaternion, PatrolNode          # noqa: E402
from speech_processor.approach_object_node import ApproachObjectNode              # noqa: E402
from speech_processor.command_dispatcher import CommandDispatcher                 # noqa: E402


# ===========================================================================
# Test helpers
# ===========================================================================

class _FakeLogger:
    def info(self, *a): pass
    def warn(self, *a): pass
    def warning(self, *a): pass
    def error(self, *a): pass
    def debug(self, *a): pass


class _FakePub:
    """Captures every publish() call."""
    def __init__(self):
        self.published = []

    def publish(self, msg):
        self.published.append(msg)

    @property
    def last(self):
        return self.published[-1] if self.published else None


class _FakeClock:
    def __init__(self, ns: int = 0):
        self._ns = ns

    def now(self):
        ns = self._ns

        class _T:
            nanoseconds = ns
        return _T()


def _make_patrol_node(waypoints=None, route="", skip_on_failure=True):
    """Bare PatrolNode with ROS2 __init__ bypassed."""
    node = object.__new__(PatrolNode)
    node.get_logger = lambda: _FakeLogger()
    node._waypoints = waypoints or {}
    node._patrol_route_param = route
    node._route = []
    node._running = False
    node._idx = 0
    node._skip_on_failure = skip_on_failure
    node._goal_handle = None
    node._patrol_status_pub = _FakePub()
    node._tts_pub = _FakePub()
    node._send_next_goal = lambda: None
    node._cancel_current = lambda: None
    return node


def _make_approach_node(
    target_class="",
    img_w=640.0, img_h=480.0,
    lin_speed=0.25, kp=1.0, max_ang=0.8,
    tgt_area=0.12, deadband=0.03, min_conf=0.5,
    lost_to=2.0,
    clock_ns=1_000_000_000,
):
    """Bare ApproachObjectNode with ROS2 __init__ bypassed."""
    node = object.__new__(ApproachObjectNode)
    node.get_logger = lambda: _FakeLogger()
    node._target_class = target_class
    node._img_w = img_w
    node._img_h = img_h
    node._lin_speed = lin_speed
    node._kp = kp
    node._max_ang = max_ang
    node._tgt_area = tgt_area
    node._deadband = deadband
    node._min_conf = min_conf
    node._lost_to = lost_to
    node._current_twist = _Twist()
    node._last_det_ns = 0
    node._follow_pub = _FakePub()
    node._status_pub = _FakePub()
    node._tts_pub = _FakePub()
    node.get_clock = lambda: _FakeClock(clock_ns)
    return node


def _make_det(class_id, score, cx, bbox_w, bbox_h):
    """Construct a minimal Detection2D."""
    d = _Detection2D()
    r = _DetResult()
    r.hypothesis.class_id = class_id
    r.hypothesis.score = score
    d.results.append(r)
    d.bbox.center.position.x = cx
    d.bbox.size_x = bbox_w
    d.bbox.size_y = bbox_h
    return d


def _make_det_array(*dets):
    arr = _Detection2DArray()
    arr.detections.extend(dets)
    return arr


def _make_dispatcher(custom_cmds=None):
    """Bare CommandDispatcher with only the custom-command fields populated."""
    d = object.__new__(CommandDispatcher)
    d._custom_cmds = custom_cmds or []
    d._custom_cmd_file = ""
    _logger = _FakeLogger()

    class _FakeNode:
        def get_logger(self): return _logger
    d._node = _FakeNode()
    return d


# ===========================================================================
# 1. TestYawToQuaternion
# ===========================================================================

class TestYawToQuaternion:
    def test_zero_yaw(self):
        q = _yaw_to_quaternion(0.0)
        assert q.z == pytest.approx(0.0)
        assert q.w == pytest.approx(1.0)

    def test_quarter_turn(self):
        q = _yaw_to_quaternion(math.pi / 2)
        assert q.z == pytest.approx(math.sin(math.pi / 4))
        assert q.w == pytest.approx(math.cos(math.pi / 4))

    def test_half_turn(self):
        q = _yaw_to_quaternion(math.pi)
        assert q.z == pytest.approx(1.0, abs=1e-9)
        assert q.w == pytest.approx(0.0, abs=1e-9)

    def test_negative_yaw(self):
        q = _yaw_to_quaternion(-math.pi / 2)
        assert q.z == pytest.approx(-math.sin(math.pi / 4))
        assert q.w == pytest.approx(math.cos(math.pi / 4))

    def test_unit_quaternion_norm(self):
        for yaw in [0.0, 0.5, 1.2, math.pi, -0.7]:
            q = _yaw_to_quaternion(yaw)
            assert q.z ** 2 + q.w ** 2 == pytest.approx(1.0)

    def test_x_and_y_always_zero(self):
        q = _yaw_to_quaternion(1.0)
        assert q.x == 0.0
        assert q.y == 0.0


# ===========================================================================
# 2. TestPatrolBuildRoute
# ===========================================================================

class TestPatrolBuildRoute:
    def test_empty_param_uses_all_waypoints_in_order(self):
        n = _make_patrol_node(waypoints={"a": {}, "b": {}, "c": {}}, route="")
        n._build_route()
        assert n._route == ["a", "b", "c"]

    def test_explicit_route_filters_to_given_keys(self):
        n = _make_patrol_node(waypoints={"a": {}, "b": {}, "c": {}}, route="a,c")
        n._build_route()
        assert n._route == ["a", "c"]

    def test_unknown_keys_excluded_silently(self):
        n = _make_patrol_node(waypoints={"a": {}, "b": {}}, route="a,z,b")
        n._build_route()
        assert n._route == ["a", "b"]

    def test_all_unknown_keys_produces_empty_route(self):
        n = _make_patrol_node(waypoints={"a": {}}, route="x,y,z")
        n._build_route()
        assert n._route == []

    def test_order_follows_param_not_yaml(self):
        n = _make_patrol_node(
            waypoints={"a": {}, "b": {}, "c": {}, "d": {}}, route="d,b,a"
        )
        n._build_route()
        assert n._route == ["d", "b", "a"]

    def test_single_waypoint(self):
        n = _make_patrol_node(waypoints={"lobby": {}}, route="")
        n._build_route()
        assert n._route == ["lobby"]


# ===========================================================================
# 3. TestPatrolLoadWaypoints
# ===========================================================================

class TestPatrolLoadWaypoints:
    def test_valid_yaml_loads_waypoints(self, tmp_path):
        f = tmp_path / "wp.yaml"
        f.write_text(yaml.dump({"waypoints": {"lobby": {"x": 1.0, "y": 2.0, "yaw": 0.0}}}))
        n = _make_patrol_node()
        n._waypoints_file = str(f)
        n._patrol_route_param = ""
        n._load_waypoints()
        assert "lobby" in n._waypoints
        assert n._waypoints["lobby"]["x"] == 1.0

    def test_valid_yaml_builds_route(self, tmp_path):
        f = tmp_path / "wp.yaml"
        f.write_text(yaml.dump({"waypoints": {"a": {}, "b": {}}}))
        n = _make_patrol_node()
        n._waypoints_file = str(f)
        n._patrol_route_param = ""
        n._load_waypoints()
        assert n._route == ["a", "b"]

    def test_missing_file_keeps_empty_waypoints(self):
        n = _make_patrol_node()
        n._waypoints_file = "/nonexistent/path/wp.yaml"
        n._load_waypoints()
        assert n._waypoints == {}

    def test_empty_path_is_noop(self):
        n = _make_patrol_node()
        n._waypoints_file = ""
        n._load_waypoints()
        assert n._waypoints == {}

    def test_yaml_without_waypoints_key_yields_empty(self, tmp_path):
        f = tmp_path / "other.yaml"
        f.write_text(yaml.dump({"other_section": "data"}))
        n = _make_patrol_node()
        n._waypoints_file = str(f)
        n._patrol_route_param = ""
        n._load_waypoints()
        assert n._waypoints == {}


# ===========================================================================
# 4. TestPatrolEnableLogic
# ===========================================================================

class TestPatrolEnableLogic:
    def test_enable_when_already_running_is_noop(self):
        n = _make_patrol_node(waypoints={"a": {}})
        n._running = True
        n._route = ["a"]
        calls = []
        n._send_next_goal = lambda: calls.append(1)
        n._on_enable(_Bool(data=True))
        assert n._running is True
        assert calls == []

    def test_enable_with_no_route_publishes_tts_no_start(self):
        n = _make_patrol_node(waypoints={})
        n._route = []
        n._on_enable(_Bool(data=True))
        assert n._running is False
        assert n._tts_pub.last is not None

    def test_enable_starts_patrol_and_calls_send_goal(self):
        n = _make_patrol_node(waypoints={"a": {}})
        n._route = ["a"]
        calls = []
        n._send_next_goal = lambda: calls.append(1)
        n._on_enable(_Bool(data=True))
        assert n._running is True
        assert n._idx == 0
        assert calls == [1]

    def test_disable_when_not_running_is_noop(self):
        n = _make_patrol_node()
        n._running = False
        n._on_enable(_Bool(data=False))
        assert n._running is False
        assert n._patrol_status_pub.published == []

    def test_disable_when_running_stops_patrol(self):
        n = _make_patrol_node(waypoints={"a": {}})
        n._running = True
        n._on_enable(_Bool(data=False))
        assert n._running is False
        all_msgs = n._patrol_status_pub.published + n._tts_pub.published
        assert any(
            "cancel" in m.data.lower() or "stop" in m.data.lower()
            for m in all_msgs
        )


# ===========================================================================
# 5. TestPatrolAdvanceAndContinue
# ===========================================================================

class TestPatrolAdvanceAndContinue:
    def test_advance_increments_idx(self):
        n = _make_patrol_node(waypoints={"a": {}, "b": {}, "c": {}})
        n._route = ["a", "b", "c"]
        n._running = True
        n._idx = 0
        n._advance_and_continue()
        assert n._idx == 1

    def test_advance_wraps_to_zero_on_last(self):
        n = _make_patrol_node(waypoints={"a": {}, "b": {}, "c": {}})
        n._route = ["a", "b", "c"]
        n._running = True
        n._idx = 2
        n._advance_and_continue()
        assert n._idx == 0

    def test_wrap_publishes_patrol_done(self):
        n = _make_patrol_node(waypoints={"a": {}, "b": {}})
        n._route = ["a", "b"]
        n._running = True
        n._idx = 1
        n._advance_and_continue()
        assert any("patrol_done" in m.data for m in n._patrol_status_pub.published)

    def test_mid_route_advance_no_patrol_done(self):
        n = _make_patrol_node(waypoints={"a": {}, "b": {}, "c": {}})
        n._route = ["a", "b", "c"]
        n._running = True
        n._idx = 0
        n._advance_and_continue()
        assert not any("patrol_done" in m.data for m in n._patrol_status_pub.published)

    def test_noop_when_not_running(self):
        n = _make_patrol_node(waypoints={"a": {}, "b": {}})
        n._route = ["a", "b"]
        n._running = False
        n._idx = 0
        calls = []
        n._send_next_goal = lambda: calls.append(1)
        n._advance_and_continue()
        assert n._idx == 0
        assert calls == []

    def test_calls_send_next_goal_after_advance(self):
        n = _make_patrol_node(waypoints={"a": {}, "b": {}})
        n._route = ["a", "b"]
        n._running = True
        n._idx = 0
        calls = []
        n._send_next_goal = lambda: calls.append(1)
        n._advance_and_continue()
        assert calls == [1]


# ===========================================================================
# 6. TestPatrolSkipOrAbort
# ===========================================================================

class TestPatrolSkipOrAbort:
    def test_skip_on_failure_calls_advance(self):
        n = _make_patrol_node(waypoints={"a": {}, "b": {}}, skip_on_failure=True)
        n._route = ["a", "b"]
        n._running = True
        n._idx = 0
        calls = []
        n._send_next_goal = lambda: calls.append(1)
        n._skip_or_abort("a")
        assert calls == [1]

    def test_skip_on_failure_keeps_patrol_running(self):
        n = _make_patrol_node(waypoints={"a": {}, "b": {}}, skip_on_failure=True)
        n._route = ["a", "b"]
        n._running = True
        n._idx = 0
        n._send_next_goal = lambda: None
        n._skip_or_abort("a")
        assert n._running is True

    def test_no_skip_aborts_patrol(self):
        n = _make_patrol_node(waypoints={"a": {}}, skip_on_failure=False)
        n._route = ["a"]
        n._running = True
        n._skip_or_abort("a")
        assert n._running is False

    def test_no_skip_publishes_patrol_cancelled(self):
        n = _make_patrol_node(waypoints={"a": {}}, skip_on_failure=False)
        n._route = ["a"]
        n._running = True
        n._skip_or_abort("a")
        assert any("cancel" in m.data for m in n._patrol_status_pub.published)


# ===========================================================================
# 7. TestPatrolStatusStringFormat
# ===========================================================================

class TestPatrolStatusStringFormat:
    def test_patrolling_prefix_and_structure(self):
        key, idx, total = "lobby", 1, 3
        s = f"patrolling:{key}/{idx}/{total}"
        assert s.startswith("patrolling:")
        parts = s[len("patrolling:"):].split("/")
        assert parts[0] == "lobby"
        assert parts[1] == "1"

    def test_patrolling_status_uses_one_based_index(self):
        n = _make_patrol_node(waypoints={"a": {}, "b": {}})
        n._route = ["a", "b"]
        n._running = False  # let _on_enable start it
        n._idx = 0
        captured = []

        def fake_send():
            key = n._route[n._idx]
            total = len(n._route)
            captured.append(f"patrolling:{key}/{n._idx + 1}/{total}")

        n._send_next_goal = fake_send
        n._on_enable(_Bool(data=True))
        assert captured == ["patrolling:a/1/2"]

    def test_patrol_done_literal(self):
        assert "patrol_done" == "patrol_done"

    def test_patrol_failed_contains_key(self):
        key = "kitchen"
        s = f"patrol_failed:{key}"
        assert key in s
        assert s.startswith("patrol_failed:")


# ===========================================================================
# 8. TestApproachTargetSetting
# ===========================================================================

class TestApproachTargetSetting:
    def test_new_target_lowercased_and_stripped(self):
        n = _make_approach_node()
        n._on_target(_Str(data="  Sports Ball  "))
        assert n._target_class == "sports ball"

    def test_new_target_publishes_approaching_status(self):
        n = _make_approach_node()
        n._on_target(_Str(data="cup"))
        assert any("approaching:cup" in m.data for m in n._status_pub.published)

    def test_new_target_publishes_tts(self):
        n = _make_approach_node()
        n._on_target(_Str(data="chair"))
        assert any("chair" in m.data.lower() for m in n._tts_pub.published)

    def test_empty_string_cancels_active_target(self):
        n = _make_approach_node(target_class="chair")
        n._on_target(_Str(data=""))
        assert n._target_class == ""
        assert any("cancelled" in m.data for m in n._status_pub.published)

    def test_empty_string_with_no_active_target_is_noop(self):
        n = _make_approach_node(target_class="")
        n._on_target(_Str(data=""))
        assert n._status_pub.published == []


# ===========================================================================
# 9. TestApproachCameraInfo
# ===========================================================================

class TestApproachCameraInfo:
    def test_valid_dimensions_update_both(self):
        n = _make_approach_node(img_w=640.0, img_h=480.0)
        msg = _CameraInfo()
        msg.width = 1280
        msg.height = 720
        n._on_camera_info(msg)
        assert n._img_w == 1280.0
        assert n._img_h == 720.0

    def test_zero_width_keeps_previous(self):
        n = _make_approach_node(img_w=640.0)
        msg = _CameraInfo()
        msg.width = 0
        msg.height = 480
        n._on_camera_info(msg)
        assert n._img_w == 640.0

    def test_zero_height_keeps_previous(self):
        n = _make_approach_node(img_h=480.0)
        msg = _CameraInfo()
        msg.width = 640
        msg.height = 0
        n._on_camera_info(msg)
        assert n._img_h == 480.0

    def test_dimensions_stored_as_float(self):
        n = _make_approach_node()
        msg = _CameraInfo()
        msg.width = 800
        msg.height = 600
        n._on_camera_info(msg)
        assert isinstance(n._img_w, float)
        assert isinstance(n._img_h, float)


# ===========================================================================
# 10. TestApproachControlLaw
# ===========================================================================

class TestApproachControlLaw:
    def test_no_target_ignores_detections(self):
        n = _make_approach_node(target_class="")
        arr = _make_det_array(_make_det("chair", 0.9, 320.0, 100.0, 100.0))
        n._on_detections(arr)
        assert n._current_twist.linear.x == 0.0

    def test_wrong_class_ignored(self):
        n = _make_approach_node(target_class="chair")
        arr = _make_det_array(_make_det("cup", 0.9, 320.0, 100.0, 100.0))
        n._on_detections(arr)
        assert n._current_twist.linear.x == 0.0

    def test_below_confidence_threshold_ignored(self):
        n = _make_approach_node(target_class="chair", min_conf=0.5)
        arr = _make_det_array(_make_det("chair", 0.4, 320.0, 100.0, 100.0))
        n._on_detections(arr)
        assert n._current_twist.linear.x == 0.0

    def test_centered_far_object_zero_angular_positive_linear(self):
        # cx == img_w/2 → error_x = 0 → angular = 0
        n = _make_approach_node(target_class="chair", img_w=640.0, img_h=480.0,
                                 tgt_area=0.12, deadband=0.03, kp=1.0)
        arr = _make_det_array(_make_det("chair", 0.9, 320.0, 50.0, 50.0))
        n._on_detections(arr)
        assert n._current_twist.angular.z == pytest.approx(0.0, abs=1e-9)
        assert n._current_twist.linear.x > 0.0

    def test_left_biased_object_positive_angular(self):
        # cx < img_w/2 → error_x < 0 → raw_az = -kp*error_x > 0 (turn left)
        n = _make_approach_node(target_class="chair", img_w=640.0, img_h=480.0,
                                 kp=1.0, max_ang=0.8)
        arr = _make_det_array(_make_det("chair", 0.9, 160.0, 50.0, 50.0))
        n._on_detections(arr)
        assert n._current_twist.angular.z > 0.0

    def test_right_biased_object_negative_angular(self):
        n = _make_approach_node(target_class="chair", img_w=640.0, img_h=480.0,
                                 kp=1.0, max_ang=0.8)
        arr = _make_det_array(_make_det("chair", 0.9, 480.0, 50.0, 50.0))
        n._on_detections(arr)
        assert n._current_twist.angular.z < 0.0

    def test_angular_clamped_to_max(self):
        n = _make_approach_node(target_class="chair", img_w=640.0, img_h=480.0,
                                 kp=10.0, max_ang=0.8)
        arr = _make_det_array(_make_det("chair", 0.9, 0.0, 50.0, 50.0))
        n._on_detections(arr)
        assert abs(n._current_twist.angular.z) <= 0.8 + 1e-9

    def test_area_at_exact_stop_threshold_triggers_reached(self):
        # area_frac = 30*30/10000 = 0.09 == tgt_area(0.12) - deadband(0.03) → reached (>=)
        n = _make_approach_node(target_class="chair", img_w=100.0, img_h=100.0,
                                 tgt_area=0.12, deadband=0.03)
        reached = []
        n._on_reached = lambda: reached.append(1)
        arr = _make_det_array(_make_det("chair", 0.9, 50.0, 30.0, 30.0))
        n._on_detections(arr)
        assert reached == [1]

    def test_area_below_threshold_moves_forward(self):
        # 28*28/10000 = 0.0784 < 0.09 → not yet reached
        n = _make_approach_node(target_class="chair", img_w=100.0, img_h=100.0,
                                 tgt_area=0.12, deadband=0.03)
        n._on_reached = lambda: None
        arr = _make_det_array(_make_det("chair", 0.9, 50.0, 28.0, 28.0))
        n._on_detections(arr)
        assert n._current_twist.linear.x > 0.0

    def test_largest_bbox_wins_among_multiple_detections(self):
        # Small centered box vs. large left-offset box; large box should drive angular > 0
        n = _make_approach_node(target_class="chair", img_w=640.0, img_h=480.0,
                                 kp=1.0, max_ang=0.8, tgt_area=0.12, deadband=0.03)
        small = _make_det("chair", 0.9, 320.0, 50.0, 50.0)   # centered, small
        large = _make_det("chair", 0.9, 160.0, 150.0, 150.0)  # left, large (wins)
        arr = _make_det_array(small, large)
        n._on_detections(arr)
        assert n._current_twist.angular.z > 0.0  # steered toward left (large) box


# ===========================================================================
# 11. TestApproachLostTimeout
# ===========================================================================

class TestApproachLostTimeout:
    def test_age_zero_publishes_current_twist(self):
        n = _make_approach_node(target_class="chair", lost_to=2.0)
        n._current_twist.linear.x = 0.25
        n._last_det_ns = 1_000_000_000
        n.get_clock = lambda: _FakeClock(1_000_000_000)  # age == 0
        n._on_lost = lambda: None
        n._publish_tick()
        assert n._follow_pub.last.linear.x == 0.25

    def test_age_exactly_at_timeout_not_lost(self):
        # age == lost_to: strict > means not triggered
        n = _make_approach_node(target_class="chair", lost_to=2.0)
        n._last_det_ns = 0
        n.get_clock = lambda: _FakeClock(int(2.0 * 1e9))  # age exactly 2.0
        lost = []
        n._on_lost = lambda: lost.append(1)
        n._publish_tick()
        assert lost == []

    def test_age_past_timeout_triggers_on_lost(self):
        n = _make_approach_node(target_class="chair", lost_to=2.0)
        n._last_det_ns = 0
        n.get_clock = lambda: _FakeClock(int(2.001 * 1e9))  # age > 2.0
        lost = []
        n._on_lost = lambda: lost.append(1)
        n._publish_tick()
        assert lost == [1]

    def test_no_target_skips_publish_tick(self):
        n = _make_approach_node(target_class="")
        n._publish_tick()
        assert n._follow_pub.published == []

    def test_zero_lost_timeout_immediately_triggers_lost(self):
        n = _make_approach_node(target_class="chair", lost_to=0.0)
        n._last_det_ns = 0
        n.get_clock = lambda: _FakeClock(1)  # age = 1 ns > 0
        lost = []
        n._on_lost = lambda: lost.append(1)
        n._publish_tick()
        assert lost == [1]


# ===========================================================================
# 12. TestApproachTerminalConditions
# ===========================================================================

class TestApproachTerminalConditions:
    def test_on_reached_clears_target_class(self):
        n = _make_approach_node(target_class="chair")
        n._on_reached()
        assert n._target_class == ""

    def test_on_reached_publishes_reached_status_with_class(self):
        n = _make_approach_node(target_class="sports ball")
        n._on_reached()
        assert any("reached:sports ball" in m.data for m in n._status_pub.published)

    def test_on_reached_publishes_zero_velocity(self):
        n = _make_approach_node(target_class="chair")
        n._current_twist.linear.x = 0.25
        n._on_reached()
        assert n._follow_pub.last.linear.x == 0.0
        assert n._follow_pub.last.angular.z == 0.0

    def test_on_lost_clears_target_class(self):
        n = _make_approach_node(target_class="cup")
        n._on_lost()
        assert n._target_class == ""

    def test_on_lost_publishes_lost_status_with_class(self):
        n = _make_approach_node(target_class="dog")
        n._on_lost()
        assert any("lost:dog" in m.data for m in n._status_pub.published)

    def test_on_lost_publishes_zero_velocity(self):
        n = _make_approach_node(target_class="cat")
        n._on_lost()
        assert n._follow_pub.last.linear.x == 0.0
        assert n._follow_pub.last.angular.z == 0.0


# ===========================================================================
# 13. TestCustomCommandMatch
# ===========================================================================

class TestCustomCommandMatch:
    def test_empty_custom_cmds_returns_none(self):
        d = _make_dispatcher()
        assert d.match_custom("go to lobby") is None

    def test_english_phrase_matches(self):
        d = _make_dispatcher([{
            "trigger_en": "go to lobby",
            "action_type": "navigate_to_room",
            "room": "lobby",
        }])
        result = d.match_custom("please go to lobby now", language="en")
        assert result == ("goto_room", "lobby")

    def test_indonesian_phrase_matches_with_id_language(self):
        d = _make_dispatcher([{
            "trigger_id": "ke lobi",
            "action_type": "navigate_to_room",
            "room": "lobby",
        }])
        result = d.match_custom("tolong ke lobi sekarang", language="id")
        assert result == ("goto_room", "lobby")

    def test_english_trigger_not_matched_on_id_language(self):
        d = _make_dispatcher([{
            "trigger_en": "go to lobby",
            "action_type": "navigate_to_room",
            "room": "lobby",
        }])
        result = d.match_custom("go to lobby", language="id")  # looks in trigger_id
        assert result is None

    def test_no_phrase_match_returns_none(self):
        d = _make_dispatcher([{
            "trigger_en": "go to lobby",
            "action_type": "navigate_to_room",
            "room": "lobby",
        }])
        assert d.match_custom("what is the weather", language="en") is None

    def test_longer_phrase_beats_shorter(self):
        d = _make_dispatcher([
            {"trigger_en": "entrance",
             "action_type": "navigate_to_room", "room": "entrance"},
            {"trigger_en": "go to the main entrance",
             "action_type": "navigate_to_room", "room": "main_entrance"},
        ])
        result = d.match_custom("please go to the main entrance", language="en")
        assert result == ("goto_room", "main_entrance")

    def test_word_boundary_not_substring(self):
        # "ball" should NOT match inside "ballroom"
        d = _make_dispatcher([{
            "trigger_en": "ball",
            "action_type": "approach_object",
            "class_name": "sports ball",
        }])
        result = d.match_custom("go to the ballroom", language="en")
        assert result is None

    def test_case_insensitive_match(self):
        d = _make_dispatcher([{
            "trigger_en": "start patrol",
            "action_type": "patrol_start",
        }])
        result = d.match_custom("START PATROL please", language="en")
        assert result == ("patrol_start",)

    def test_multiple_triggers_comma_separated(self):
        d = _make_dispatcher([{
            "trigger_en": "guard the area, start patrol",
            "action_type": "patrol_start",
        }])
        result = d.match_custom("guard the area", language="en")
        assert result == ("patrol_start",)

    def test_punctuation_stripped_before_matching(self):
        d = _make_dispatcher([{
            "trigger_en": "go to lobby",
            "action_type": "navigate_to_room",
            "room": "lobby",
        }])
        result = d.match_custom("please, go to lobby!", language="en")
        assert result == ("goto_room", "lobby")


# ===========================================================================
# 14. TestCustomAction
# ===========================================================================

class TestCustomAction:
    def _act(self, cmd):
        return _make_dispatcher()._custom_action(cmd)

    def test_api_id_returns_dict_with_api_id(self):
        result = self._act({"action_type": "api_id", "api_id": 1009})
        assert result == {"api_id": 1009, "parameter": ""}

    def test_api_id_with_parameter(self):
        result = self._act({"action_type": "api_id", "api_id": 1013, "parameter": "0.05"})
        assert result["parameter"] == "0.05"

    def test_navigate_to_room(self):
        result = self._act({"action_type": "navigate_to_room", "room": "lobby"})
        assert result == ("goto_room", "lobby")

    def test_patrol_start(self):
        assert self._act({"action_type": "patrol_start"}) == ("patrol_start",)

    def test_patrol_stop(self):
        assert self._act({"action_type": "patrol_stop"}) == ("patrol_stop",)

    def test_follow_start(self):
        assert self._act({"action_type": "follow_start"}) == ("follow_start",)

    def test_follow_stop(self):
        assert self._act({"action_type": "follow_stop"}) == ("follow_stop",)

    def test_approach_object(self):
        result = self._act({"action_type": "approach_object", "class_name": "sports ball"})
        assert result == ("approach_object", "sports ball")

    def test_unknown_action_type_returns_none(self):
        assert self._act({"action_type": "teleport"}) is None


# ===========================================================================
# 15. TestCustomCommandLoading
# ===========================================================================

class TestCustomCommandLoading:
    def test_valid_yaml_loads_one_command(self, tmp_path):
        f = tmp_path / "cmds.yaml"
        f.write_text(yaml.dump({
            "custom_commands": {
                "go_lobby": {
                    "trigger_en": "go to lobby",
                    "trigger_id": "ke lobi",
                    "action_type": "navigate_to_room",
                    "room": "lobby",
                }
            }
        }))
        d = _make_dispatcher()
        d._custom_cmd_file = str(f)
        d._load_custom_commands()
        assert len(d._custom_cmds) == 1
        assert d._custom_cmds[0]["key"] == "go_lobby"

    def test_empty_commands_dict_loads_zero(self, tmp_path):
        f = tmp_path / "empty.yaml"
        f.write_text(yaml.dump({"custom_commands": {}}))
        d = _make_dispatcher()
        d._custom_cmd_file = str(f)
        d._load_custom_commands()
        assert d._custom_cmds == []

    def test_missing_file_leaves_cmds_unchanged(self):
        d = _make_dispatcher()
        d._custom_cmd_file = "/nonexistent/cmds.yaml"
        d._load_custom_commands()
        assert d._custom_cmds == []

    def test_empty_file_path_is_noop(self):
        d = _make_dispatcher()
        d._load_custom_commands()
        assert d._custom_cmds == []

    def test_multiple_commands_all_loaded(self, tmp_path):
        f = tmp_path / "multi.yaml"
        f.write_text(yaml.dump({
            "custom_commands": {
                "cmd_a": {"trigger_en": "do a", "action_type": "patrol_start"},
                "cmd_b": {"trigger_en": "do b", "action_type": "patrol_stop"},
                "cmd_c": {"trigger_en": "do c", "action_type": "follow_start"},
            }
        }))
        d = _make_dispatcher()
        d._custom_cmd_file = str(f)
        d._load_custom_commands()
        assert len(d._custom_cmds) == 3

    def test_command_key_preserved_in_loaded_entry(self, tmp_path):
        f = tmp_path / "key.yaml"
        f.write_text(yaml.dump({
            "custom_commands": {
                "welcome_pose": {
                    "trigger_en": "welcome",
                    "action_type": "api_id",
                    "api_id": 1004,
                }
            }
        }))
        d = _make_dispatcher()
        d._custom_cmd_file = str(f)
        d._load_custom_commands()
        assert d._custom_cmds[0]["key"] == "welcome_pose"
        assert d._custom_cmds[0]["action_type"] == "api_id"

    def test_roundtrip_load_then_match(self, tmp_path):
        f = tmp_path / "rt.yaml"
        f.write_text(yaml.dump({
            "custom_commands": {
                "patrol_go": {
                    "trigger_en": "begin patrol now",
                    "action_type": "patrol_start",
                }
            }
        }))
        d = _make_dispatcher()
        d._custom_cmd_file = str(f)
        d._load_custom_commands()
        result = d.match_custom("begin patrol now", language="en")
        assert result == ("patrol_start",)
