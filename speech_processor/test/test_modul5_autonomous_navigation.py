"""
Tests for Modul 5 — Autonomous Indoor Navigation

Covers:
  5.2/5.3 nav_waypoint_node  — yaw→quaternion math, waypoint loading,
                               fuzzy room lookup, navigate/cancel/goal-response/result
  Technical: behavior_coordinator_node — IDLE/VOICE_MOVE/FOLLOWING/NAVIGATING/
                               APPROACHING/PATROL state machine, timer tick

Pure pytest — no ROS2 runtime, no robot, no GPU.

Run:
  export PYTHONPATH=speech_processor          # Linux/macOS
  $env:PYTHONPATH = "speech_processor"        # Windows PowerShell
  python -m pytest speech_processor/test/test_modul5_autonomous_navigation.py -v
"""

import math
import sys
import types

import pytest
import yaml

# ===========================================================================
# ROS2 stubs — force-set to override modul1's weak object stubs
# ===========================================================================


def _make_stub(name, attrs=None):
    """Create or update stub module. Always sets attrs to survive collection order."""
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
_make_stub("rclpy.action", {"ActionClient": object})


class _FakeQoSProfile:
    def __init__(self, **kwargs):
        pass


class _FakeReliabilityPolicy:
    RELIABLE = "reliable"
    BEST_EFFORT = "best_effort"


class _FakeDurabilityPolicy:
    TRANSIENT_LOCAL = "transient_local"
    VOLATILE = "volatile"


class _FakeHistoryPolicy:
    KEEP_LAST = "keep_last"


_make_stub("rclpy.qos", {
    "QoSProfile": _FakeQoSProfile,
    "ReliabilityPolicy": _FakeReliabilityPolicy,
    "DurabilityPolicy": _FakeDurabilityPolicy,
    "HistoryPolicy": _FakeHistoryPolicy,
    "qos_profile_sensor_data": None,
    "qos_profile_system_default": None,
})

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
    def __init__(self): self.frame_id = ""; self.stamp = None  # noqa: E702


class _NavPosition:
    def __init__(self): self.x = 0.0; self.y = 0.0  # noqa: E702


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

# --- sensor_msgs, vision_msgs, go2_interfaces, cv2 ---
_make_stub("sensor_msgs")
_make_stub("sensor_msgs.msg", {"Image": object, "CameraInfo": object})
_make_stub("vision_msgs")
_make_stub("vision_msgs.msg", {})
_make_stub("go2_interfaces")
_make_stub("go2_interfaces.msg", {"WebRtcReq": object, "Go2State": object})


def _cv2_imwrite(path, img, *_a, **_kw):
    """Write 4 JPEG magic bytes so file-existence checks in test_face_db pass."""
    from pathlib import Path as _P
    _P(path).write_bytes(b"\xff\xd8\xff\xe0")
    return True


_make_stub("cv2", {
    "imread": lambda *a, **kw: None,
    "imwrite": _cv2_imwrite,
    "resize": lambda img, *a, **kw: img,
    "cvtColor": lambda img, *a, **kw: img,
    "COLOR_BGR2RGB": 4,
})
_make_stub("cv_bridge", {"CvBridge": object})

# --- import production modules ---
from speech_processor.nav_waypoint_node import (              # noqa: E402
    _yaw_to_quaternion as _nav_yaw_to_q,
    NavWaypointNode,
)
from speech_processor.behavior_coordinator_node import (      # noqa: E402
    BehaviorCoordinatorNode,
)


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

            def to_msg(self_inner):
                return None
        return _T()


class _FakeGoalHandle:
    def __init__(self, accepted: bool = True):
        self.accepted = accepted
        self._cancelled = False

    def cancel_goal_async(self):
        self._cancelled = True

    def get_result_async(self):
        return _FakeFuture(None)


class _FakeFuture:
    def __init__(self, result):
        self._result = result
        self._callbacks = []

    def result(self):
        return self._result

    def add_done_callback(self, cb):
        self._callbacks.append(cb)


class _FakeNavClient:
    def __init__(self, server_ready: bool = True):
        self._server_ready = server_ready
        self.sent_goals = []

    def wait_for_server(self, timeout_sec: float = 5.0) -> bool:
        return self._server_ready

    def send_goal_async(self, goal):
        self.sent_goals.append(goal)
        return _FakeFuture(_FakeGoalHandle(accepted=True))


def _make_nav_node(waypoints=None):
    node = object.__new__(NavWaypointNode)
    node.get_logger = lambda: _FakeLogger()
    node._waypoints = waypoints or {}
    node._waypoints_file = ""
    node._goal_handle = None
    node._nav_client = _FakeNavClient(server_ready=True)
    node._nav_status_pub = _FakePub()
    node._tts_pub = _FakePub()
    node.get_clock = lambda: _FakeClock(0)
    return node


def _make_bc_node(initial_mode: str = "IDLE", vel_idle_sec: float = 0.6, clock_ns: int = 0):
    node = object.__new__(BehaviorCoordinatorNode)
    node.get_logger = lambda: _FakeLogger()
    node._mode = initial_mode
    node._vel_idle_sec = vel_idle_sec
    node._last_vel_t = 0.0
    node._mode_pub = _FakePub()
    node.get_clock = lambda: _FakeClock(clock_ns)
    return node


def _make_result_future(status: int):
    class _Res:
        def __init__(self_inner): self_inner.status = status

    class _Fut:
        def result(self_inner): return _Res()
    return _Fut()


# ===========================================================================
# NavWaypointNode — yaw → quaternion
# ===========================================================================

class TestNavYawToQuaternion:
    def test_zero_yaw_identity(self):
        q = _nav_yaw_to_q(0.0)
        assert q.z == pytest.approx(0.0)
        assert q.w == pytest.approx(1.0)

    def test_quarter_turn(self):
        q = _nav_yaw_to_q(math.pi / 2)
        assert q.z == pytest.approx(math.sin(math.pi / 4))
        assert q.w == pytest.approx(math.cos(math.pi / 4))

    def test_unit_norm_for_multiple_angles(self):
        for yaw in [0.0, 0.5, math.pi, -1.2, 3.0]:
            q = _nav_yaw_to_q(yaw)
            assert q.z ** 2 + q.w ** 2 == pytest.approx(1.0)

    def test_x_y_always_zero(self):
        q = _nav_yaw_to_q(1.5)
        assert q.x == 0.0 and q.y == 0.0


# ===========================================================================
# NavWaypointNode — waypoint loading
# ===========================================================================

class TestNavLoadWaypoints:
    def test_valid_yaml_loads_waypoints(self, tmp_path):
        f = tmp_path / "wp.yaml"
        f.write_text(yaml.dump({"waypoints": {"lobby": {"x": 1.0, "y": 2.0, "yaw": 0.0}}}))
        n = _make_nav_node()
        n._waypoints_file = str(f)
        n._load_waypoints()
        assert "lobby" in n._waypoints
        assert n._waypoints["lobby"]["x"] == 1.0

    def test_multiple_waypoints_all_loaded(self, tmp_path):
        f = tmp_path / "wp.yaml"
        f.write_text(yaml.dump({"waypoints": {"a": {}, "b": {}, "c": {}}}))
        n = _make_nav_node()
        n._waypoints_file = str(f)
        n._load_waypoints()
        assert len(n._waypoints) == 3

    def test_missing_file_leaves_waypoints_unchanged(self):
        n = _make_nav_node()
        n._waypoints_file = "/nonexistent/path.yaml"
        n._load_waypoints()
        assert n._waypoints == {}

    def test_empty_file_path_is_noop(self):
        n = _make_nav_node()
        n._waypoints_file = ""
        n._load_waypoints()
        assert n._waypoints == {}

    def test_yaml_without_waypoints_key_yields_empty(self, tmp_path):
        f = tmp_path / "other.yaml"
        f.write_text(yaml.dump({"other_key": "data"}))
        n = _make_nav_node()
        n._waypoints_file = str(f)
        n._load_waypoints()
        assert n._waypoints == {}

    def test_on_reload_triggers_load(self, tmp_path):
        f = tmp_path / "wp.yaml"
        f.write_text(yaml.dump({"waypoints": {"room1": {"x": 0.0}}}))
        n = _make_nav_node()
        n._waypoints_file = str(f)
        n._on_reload(_Empty())
        assert "room1" in n._waypoints


# ===========================================================================
# NavWaypointNode — fuzzy room lookup
# ===========================================================================

_SAMPLE_WPS = {
    "lobby": {
        "x": 1.0, "y": 1.0,
        "label_en": "main lobby",
        "label_id": "lobi utama",
    },
    "break_room": {"x": 2.0, "y": 2.0, "label_en": "break room"},
    "conference_a": {"x": 3.0, "y": 3.0, "label_id": "ruang rapat A"},
}


class TestNavLookup:
    def test_exact_key_match(self):
        n = _make_nav_node(waypoints=_SAMPLE_WPS)
        assert n._lookup("lobby") == _SAMPLE_WPS["lobby"]

    def test_space_in_room_name_normalized(self):
        n = _make_nav_node(waypoints=_SAMPLE_WPS)
        assert n._lookup("break room") == _SAMPLE_WPS["break_room"]

    def test_hyphen_in_room_name_normalized(self):
        # YAML key uses underscore; lookup input uses hyphen → normalized to underscore → matches
        wps = {"break_room": {"x": 0.0}}
        n = _make_nav_node(waypoints=wps)
        assert n._lookup("break-room") == wps["break_room"]

    def test_case_insensitive_key_match(self):
        n = _make_nav_node(waypoints=_SAMPLE_WPS)
        assert n._lookup("LOBBY") == _SAMPLE_WPS["lobby"]

    def test_mixed_case_and_spaces(self):
        n = _make_nav_node(waypoints=_SAMPLE_WPS)
        assert n._lookup("Conference A") == _SAMPLE_WPS["conference_a"]

    def test_substring_of_waypoint_key(self):
        n = _make_nav_node(waypoints=_SAMPLE_WPS)
        # "lob" is substring of key "lobby"
        assert n._lookup("lob") == _SAMPLE_WPS["lobby"]

    def test_substring_in_label_en(self):
        n = _make_nav_node(waypoints=_SAMPLE_WPS)
        # "main" is in label_en "main lobby"
        result = n._lookup("main")
        assert result is not None

    def test_substring_in_label_id(self):
        n = _make_nav_node(waypoints=_SAMPLE_WPS)
        # "lobi" is in label_id "lobi utama"
        assert n._lookup("lobi") == _SAMPLE_WPS["lobby"]

    def test_no_match_returns_none(self):
        n = _make_nav_node(waypoints=_SAMPLE_WPS)
        assert n._lookup("cafeteria") is None

    def test_empty_waypoints_returns_none(self):
        n = _make_nav_node(waypoints={})
        assert n._lookup("lobby") is None


# ===========================================================================
# NavWaypointNode — _on_navigate
# ===========================================================================

class TestNavOnNavigate:
    def test_empty_string_no_status_published(self):
        n = _make_nav_node(waypoints={"lobby": {"x": 1.0, "y": 1.0}})
        n._goal_handle = None
        n._on_navigate(_Str(data=""))
        assert n._nav_status_pub.published == []

    def test_empty_string_calls_cancel(self):
        n = _make_nav_node()
        cancelled = []
        n._cancel_current = lambda: cancelled.append(1)
        n._on_navigate(_Str(data=""))
        assert cancelled == [1]

    def test_unknown_room_publishes_unknown_status(self):
        n = _make_nav_node()
        n._on_navigate(_Str(data="cafeteria"))
        assert any("unknown:cafeteria" in m.data for m in n._nav_status_pub.published)

    def test_unknown_room_publishes_tts(self):
        n = _make_nav_node()
        n._on_navigate(_Str(data="cafeteria"))
        assert any("cafeteria" in m.data for m in n._tts_pub.published)

    def test_known_room_publishes_navigating_status(self):
        n = _make_nav_node(waypoints={"lobby": {"x": 1.0, "y": 1.0}})
        n._on_navigate(_Str(data="lobby"))
        assert any("navigating:lobby" in m.data for m in n._nav_status_pub.published)

    def test_known_room_tts_uses_label_en(self):
        n = _make_nav_node(waypoints={"lobby": {"x": 1.0, "y": 1.0, "label_en": "Main Lobby"}})
        n._on_navigate(_Str(data="lobby"))
        assert any("Main Lobby" in m.data for m in n._tts_pub.published)

    def test_nav_server_unavailable_publishes_failed(self):
        n = _make_nav_node(waypoints={"lobby": {"x": 1.0, "y": 1.0}})
        n._nav_client = _FakeNavClient(server_ready=False)
        n._on_navigate(_Str(data="lobby"))
        assert any("failed:lobby" in m.data for m in n._nav_status_pub.published)

    def test_nav_server_available_calls_send_goal(self):
        n = _make_nav_node(waypoints={"lobby": {"x": 1.0, "y": 1.0}})
        n._on_navigate(_Str(data="lobby"))
        assert len(n._nav_client.sent_goals) == 1

    def test_navigate_cancels_existing_goal_first(self):
        n = _make_nav_node(waypoints={"lobby": {"x": 1.0, "y": 1.0}})
        old_handle = _FakeGoalHandle(accepted=True)
        n._goal_handle = old_handle
        n._on_navigate(_Str(data="lobby"))
        assert old_handle._cancelled is True

    def test_goal_position_set_from_waypoint(self):
        n = _make_nav_node(waypoints={"lobby": {"x": 4.5, "y": 3.2, "yaw": 0.5}})
        n._on_navigate(_Str(data="lobby"))
        sent = n._nav_client.sent_goals
        assert len(sent) == 1
        goal = sent[0]
        assert goal.pose.pose.position.x == pytest.approx(4.5)
        assert goal.pose.pose.position.y == pytest.approx(3.2)


# ===========================================================================
# NavWaypointNode — _on_goal_response
# ===========================================================================

class TestNavGoalResponse:
    def test_rejected_publishes_failed_status(self):
        n = _make_nav_node()
        future = _FakeFuture(_FakeGoalHandle(accepted=False))
        n._on_goal_response(future, room="lobby", label="Lobby")
        assert any("failed:lobby" in m.data for m in n._nav_status_pub.published)

    def test_rejected_publishes_tts(self):
        n = _make_nav_node()
        future = _FakeFuture(_FakeGoalHandle(accepted=False))
        n._on_goal_response(future, room="lobby", label="Lobby")
        assert any("rejected" in m.data.lower() for m in n._tts_pub.published)

    def test_rejected_leaves_goal_handle_none(self):
        n = _make_nav_node()
        n._goal_handle = None
        future = _FakeFuture(_FakeGoalHandle(accepted=False))
        n._on_goal_response(future, room="lobby", label="Lobby")
        assert n._goal_handle is None

    def test_accepted_saves_goal_handle(self):
        n = _make_nav_node()
        handle = _FakeGoalHandle(accepted=True)
        future = _FakeFuture(handle)
        n._on_goal_response(future, room="lobby", label="Lobby")
        assert n._goal_handle is handle

    def test_accepted_no_failure_status_published(self):
        n = _make_nav_node()
        future = _FakeFuture(_FakeGoalHandle(accepted=True))
        n._on_goal_response(future, room="lobby", label="Lobby")
        assert not any("failed" in m.data for m in n._nav_status_pub.published)


# ===========================================================================
# NavWaypointNode — _on_result
# ===========================================================================

class TestNavOnResult:
    def test_succeeded_publishes_arrived_status(self):
        n = _make_nav_node()
        n._goal_handle = _FakeGoalHandle()
        n._on_result(_make_result_future(_GoalStatus.STATUS_SUCCEEDED), room="lobby", label="Lobby")
        assert any("arrived:lobby" in m.data for m in n._nav_status_pub.published)

    def test_succeeded_publishes_tts_with_label(self):
        n = _make_nav_node()
        n._goal_handle = _FakeGoalHandle()
        n._on_result(_make_result_future(_GoalStatus.STATUS_SUCCEEDED), room="lobby", label="Main Lobby")
        assert any("Main Lobby" in m.data for m in n._tts_pub.published)

    def test_cancelled_publishes_cancelled_status(self):
        n = _make_nav_node()
        n._goal_handle = _FakeGoalHandle()
        n._on_result(_make_result_future(_GoalStatus.STATUS_CANCELED), room="lobby", label="Lobby")
        assert any(m.data == "cancelled" for m in n._nav_status_pub.published)

    def test_cancelled_no_tts_published(self):
        n = _make_nav_node()
        n._goal_handle = _FakeGoalHandle()
        n._on_result(_make_result_future(_GoalStatus.STATUS_CANCELED), room="lobby", label="Lobby")
        assert n._tts_pub.published == []

    def test_aborted_publishes_failed_status(self):
        n = _make_nav_node()
        n._goal_handle = _FakeGoalHandle()
        n._on_result(_make_result_future(_GoalStatus.STATUS_ABORTED), room="lobby", label="Lobby")
        assert any("failed:lobby" in m.data for m in n._nav_status_pub.published)

    def test_any_result_clears_goal_handle(self):
        n = _make_nav_node()
        n._goal_handle = _FakeGoalHandle()
        n._on_result(_make_result_future(_GoalStatus.STATUS_SUCCEEDED), room="lobby", label="Lobby")
        assert n._goal_handle is None


# ===========================================================================
# NavWaypointNode — _cancel_current
# ===========================================================================

class TestNavCancelCurrent:
    def test_no_goal_handle_is_noop(self):
        n = _make_nav_node()
        n._goal_handle = None
        n._cancel_current()
        assert n._nav_status_pub.published == []

    def test_with_handle_calls_cancel_async(self):
        n = _make_nav_node()
        handle = _FakeGoalHandle()
        n._goal_handle = handle
        n._cancel_current()
        assert handle._cancelled is True

    def test_with_handle_clears_goal_handle(self):
        n = _make_nav_node()
        n._goal_handle = _FakeGoalHandle()
        n._cancel_current()
        assert n._goal_handle is None

    def test_with_handle_publishes_cancelled_status(self):
        n = _make_nav_node()
        n._goal_handle = _FakeGoalHandle()
        n._cancel_current()
        assert any(m.data == "cancelled" for m in n._nav_status_pub.published)


# ===========================================================================
# BehaviorCoordinatorNode — follow transitions
# ===========================================================================

class TestBCFollow:
    def test_true_sets_following(self):
        n = _make_bc_node("IDLE")
        n._on_follow(_Bool(data=True))
        assert n._mode == "FOLLOWING"

    def test_true_publishes_following(self):
        n = _make_bc_node("IDLE")
        n._on_follow(_Bool(data=True))
        assert any("FOLLOWING" in m.data for m in n._mode_pub.published)

    def test_false_from_following_sets_idle(self):
        n = _make_bc_node("FOLLOWING")
        n._on_follow(_Bool(data=False))
        assert n._mode == "IDLE"

    def test_false_from_idle_no_change(self):
        n = _make_bc_node("IDLE")
        n._on_follow(_Bool(data=False))
        assert n._mode == "IDLE"
        assert n._mode_pub.published == []

    def test_false_from_navigating_no_change(self):
        n = _make_bc_node("NAVIGATING")
        n._on_follow(_Bool(data=False))
        assert n._mode == "NAVIGATING"


# ===========================================================================
# BehaviorCoordinatorNode — navigation status transitions
# ===========================================================================

class TestBCNavStatus:
    def test_navigating_prefix_sets_navigating(self):
        n = _make_bc_node("IDLE")
        n._on_nav_status(_Str(data="navigating:lobby"))
        assert n._mode == "NAVIGATING"

    def test_arrived_from_navigating_sets_idle(self):
        n = _make_bc_node("NAVIGATING")
        n._on_nav_status(_Str(data="arrived:lobby"))
        assert n._mode == "IDLE"

    def test_failed_from_navigating_sets_idle(self):
        n = _make_bc_node("NAVIGATING")
        n._on_nav_status(_Str(data="failed:lobby"))
        assert n._mode == "IDLE"

    def test_cancelled_from_navigating_sets_idle(self):
        n = _make_bc_node("NAVIGATING")
        n._on_nav_status(_Str(data="cancelled"))
        assert n._mode == "IDLE"

    def test_unknown_from_navigating_sets_idle(self):
        n = _make_bc_node("NAVIGATING")
        n._on_nav_status(_Str(data="unknown:cafeteria"))
        assert n._mode == "IDLE"

    def test_arrived_from_idle_no_change(self):
        n = _make_bc_node("IDLE")
        n._on_nav_status(_Str(data="arrived:lobby"))
        assert n._mode == "IDLE"
        assert n._mode_pub.published == []

    def test_navigating_when_already_navigating_no_publish(self):
        n = _make_bc_node("NAVIGATING")
        n._on_nav_status(_Str(data="navigating:lobby"))
        assert n._mode == "NAVIGATING"
        assert n._mode_pub.published == []  # _set is noop when mode unchanged

    def test_failed_nav_status_from_approaching_no_change(self):
        n = _make_bc_node("APPROACHING")
        n._on_nav_status(_Str(data="failed:lobby"))
        assert n._mode == "APPROACHING"


# ===========================================================================
# BehaviorCoordinatorNode — velocity transitions
# ===========================================================================

class TestBCVelocity:
    def test_nonzero_linear_x_from_idle_sets_voice_move(self):
        n = _make_bc_node("IDLE", clock_ns=1_000_000_000)
        msg = _Twist()
        msg.linear.x = 0.5
        n._on_vel(msg)
        assert n._mode == "VOICE_MOVE"

    def test_nonzero_linear_y_from_idle_sets_voice_move(self):
        n = _make_bc_node("IDLE", clock_ns=1_000_000_000)
        msg = _Twist()
        msg.linear.y = 0.5
        n._on_vel(msg)
        assert n._mode == "VOICE_MOVE"

    def test_nonzero_angular_z_from_idle_sets_voice_move(self):
        n = _make_bc_node("IDLE", clock_ns=1_000_000_000)
        msg = _Twist()
        msg.angular.z = 1.0
        n._on_vel(msg)
        assert n._mode == "VOICE_MOVE"

    def test_zero_twist_from_idle_no_change(self):
        n = _make_bc_node("IDLE")
        n._on_vel(_Twist())  # all zeros
        assert n._mode == "IDLE"
        assert n._mode_pub.published == []

    def test_nonzero_from_voice_move_stays_voice_move(self):
        n = _make_bc_node("VOICE_MOVE", clock_ns=1_000_000_000)
        msg = _Twist()
        msg.linear.x = 0.3
        n._on_vel(msg)
        assert n._mode == "VOICE_MOVE"
        assert n._mode_pub.published == []  # _set is noop

    def test_nonzero_from_following_stays_following(self):
        n = _make_bc_node("FOLLOWING", clock_ns=1_000_000_000)
        msg = _Twist()
        msg.linear.x = 0.3
        n._on_vel(msg)
        assert n._mode == "FOLLOWING"

    def test_nonzero_vel_updates_last_vel_t(self):
        n = _make_bc_node("IDLE", clock_ns=2_000_000_000)
        msg = _Twist()
        msg.linear.x = 0.3
        n._on_vel(msg)
        assert n._last_vel_t == pytest.approx(2.0)


# ===========================================================================
# BehaviorCoordinatorNode — approach status transitions
# ===========================================================================

class TestBCApproach:
    def test_approaching_prefix_sets_approaching(self):
        n = _make_bc_node("IDLE")
        n._on_approach_status(_Str(data="approaching:ball"))
        assert n._mode == "APPROACHING"

    def test_reached_from_approaching_sets_idle(self):
        n = _make_bc_node("APPROACHING")
        n._on_approach_status(_Str(data="reached:ball"))
        assert n._mode == "IDLE"

    def test_lost_from_approaching_sets_idle(self):
        n = _make_bc_node("APPROACHING")
        n._on_approach_status(_Str(data="lost:ball"))
        assert n._mode == "IDLE"

    def test_cancelled_from_approaching_sets_idle(self):
        n = _make_bc_node("APPROACHING")
        n._on_approach_status(_Str(data="cancelled"))
        assert n._mode == "IDLE"

    def test_reached_from_idle_no_change(self):
        n = _make_bc_node("IDLE")
        n._on_approach_status(_Str(data="reached:ball"))
        assert n._mode == "IDLE"
        assert n._mode_pub.published == []

    def test_approaching_from_patrol_overrides_to_approaching(self):
        n = _make_bc_node("PATROL")
        n._on_approach_status(_Str(data="approaching:chair"))
        assert n._mode == "APPROACHING"


# ===========================================================================
# BehaviorCoordinatorNode — patrol status transitions
# ===========================================================================

class TestBCPatrol:
    def test_patrolling_prefix_sets_patrol(self):
        n = _make_bc_node("IDLE")
        n._on_patrol_status(_Str(data="patrolling:lobby/1/3"))
        assert n._mode == "PATROL"

    def test_patrol_done_from_patrol_sets_idle(self):
        n = _make_bc_node("PATROL")
        n._on_patrol_status(_Str(data="patrol_done"))
        assert n._mode == "IDLE"

    def test_patrol_cancelled_from_patrol_sets_idle(self):
        n = _make_bc_node("PATROL")
        n._on_patrol_status(_Str(data="patrol_cancelled"))
        assert n._mode == "IDLE"

    def test_patrol_failed_from_patrol_no_change(self):
        # patrol_failed:key is not in the terminal-condition set → stays PATROL
        n = _make_bc_node("PATROL")
        n._on_patrol_status(_Str(data="patrol_failed:lobby"))
        assert n._mode == "PATROL"
        assert n._mode_pub.published == []

    def test_patrol_done_from_idle_no_change(self):
        n = _make_bc_node("IDLE")
        n._on_patrol_status(_Str(data="patrol_done"))
        assert n._mode == "IDLE"
        assert n._mode_pub.published == []

    def test_patrolling_from_navigating_overrides_to_patrol(self):
        n = _make_bc_node("NAVIGATING")
        n._on_patrol_status(_Str(data="patrolling:room/1/2"))
        assert n._mode == "PATROL"


# ===========================================================================
# BehaviorCoordinatorNode — timer tick (voice-idle detection)
# ===========================================================================

class TestBCTick:
    def test_voice_move_elapsed_gt_timeout_sets_idle(self):
        # 0.7 s elapsed, timeout = 0.6 s → IDLE
        n = _make_bc_node("VOICE_MOVE", vel_idle_sec=0.6, clock_ns=700_000_000)
        n._last_vel_t = 0.0
        n._tick()
        assert n._mode == "IDLE"

    def test_voice_move_elapsed_below_timeout_not_idle(self):
        # 0.5 s elapsed, 0.6 s timeout → sub-threshold → stays VOICE_MOVE
        # (avoids the 600_000_000 * 1e-9 > 0.6 floating-point edge case)
        n = _make_bc_node("VOICE_MOVE", vel_idle_sec=0.6, clock_ns=1_000_000_000)
        n._last_vel_t = 0.5  # elapsed = 1.0 - 0.5 = 0.5 < 0.6
        n._tick()
        assert n._mode == "VOICE_MOVE"

    def test_voice_move_elapsed_lt_timeout_not_idle(self):
        n = _make_bc_node("VOICE_MOVE", vel_idle_sec=0.6, clock_ns=400_000_000)
        n._last_vel_t = 0.0
        n._tick()
        assert n._mode == "VOICE_MOVE"

    def test_idle_not_affected_by_tick(self):
        n = _make_bc_node("IDLE", vel_idle_sec=0.6, clock_ns=2_000_000_000)
        n._last_vel_t = 0.0
        n._tick()
        assert n._mode == "IDLE"
        assert n._mode_pub.published == []

    def test_navigating_not_affected_by_tick(self):
        n = _make_bc_node("NAVIGATING", vel_idle_sec=0.6, clock_ns=2_000_000_000)
        n._last_vel_t = 0.0
        n._tick()
        assert n._mode == "NAVIGATING"

    def test_recent_vel_keeps_voice_move(self):
        # last_vel_t = 1.5s, clock = 2.0s → elapsed = 0.5 < 0.6 → stays VOICE_MOVE
        n = _make_bc_node("VOICE_MOVE", vel_idle_sec=0.6, clock_ns=2_000_000_000)
        n._last_vel_t = 1.5
        n._tick()
        assert n._mode == "VOICE_MOVE"


# ===========================================================================
# BehaviorCoordinatorNode — _set / _publish helpers
# ===========================================================================

class TestBCSetPublish:
    def test_set_same_mode_no_publish(self):
        n = _make_bc_node("IDLE")
        n._set("IDLE")
        assert n._mode_pub.published == []

    def test_set_new_mode_publishes(self):
        n = _make_bc_node("IDLE")
        n._set("FOLLOWING")
        assert any("FOLLOWING" in m.data for m in n._mode_pub.published)

    def test_set_new_mode_updates_internal_mode(self):
        n = _make_bc_node("IDLE")
        n._set("NAVIGATING")
        assert n._mode == "NAVIGATING"

    def test_set_same_mode_twice_publishes_only_once(self):
        n = _make_bc_node("IDLE")
        n._set("PATROL")
        n._set("PATROL")  # noop
        assert len(n._mode_pub.published) == 1

    def test_publish_sends_current_mode_string(self):
        n = _make_bc_node("APPROACHING")
        n._publish()
        assert n._mode_pub.last.data == "APPROACHING"
