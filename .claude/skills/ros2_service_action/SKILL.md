---
name: ROS2 Service & Action
description: ROS2 Service and Action implementation with Clean Architecture (Python & C++)
---

# ROS2 Service & Action Skill

## Service Implementation

### Service Definition (.srv)

```
# srv/SetRobotMode.srv
# Request
string mode           # "idle", "active", "emergency"
bool force_change

---

# Response
bool success
string message
string previous_mode
```

### Service Server (Python)

```python
from robot_interfaces.srv import SetRobotMode

class RobotModeServiceNode(Node):
    def __init__(self, use_case):
        super().__init__('robot_mode_service')
        self._use_case = use_case
        self._srv = self.create_service(SetRobotMode, '/robot/set_mode', self._handle)

    def _handle(self, request, response):
        try:
            result = self._use_case.execute(mode=request.mode, force=request.force_change)
            response.success = result.success
            response.message = result.message
            response.previous_mode = result.previous_mode
        except Exception as e:
            response.success = False
            response.message = str(e)
        return response
```

### Service Client (Python)

```python
class RobotModeClient(Node):
    def __init__(self):
        super().__init__('robot_mode_client')
        self._client = self.create_client(SetRobotMode, '/robot/set_mode')

    def set_mode(self, mode: str, force: bool = False):
        req = SetRobotMode.Request()
        req.mode = mode
        req.force_change = force
        future = self._client.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        return future.result()
```

### Service Server (C++)

```cpp
// infrastructure/ros2/services/robot_mode_service.cpp
RobotModeServiceNode::RobotModeServiceNode(
    std::shared_ptr<domain::use_cases::SetRobotModeUseCase> use_case,
    const rclcpp::NodeOptions& options)
    : Node("robot_mode_service", options), use_case_(use_case) {

    using namespace std::placeholders;
    service_ = this->create_service<robot_interfaces::srv::SetRobotMode>(
        "/robot/set_mode",
        std::bind(&RobotModeServiceNode::handle_set_mode, this, _1, _2)
    );
}
```

## Action Implementation

### Action Definition (.action)

```
# action/NavigateToGoal.action
# Goal
geometry_msgs/PoseStamped target_pose
float32 max_velocity
bool allow_replanning

---

# Result
bool success
string message
float64 total_time
float64 total_distance

---

# Feedback
geometry_msgs/PoseStamped current_pose
float32 distance_remaining
float32 estimated_time_remaining
```

### Action Server (Python)

```python
from rclpy.action import ActionServer
from robot_interfaces.action import NavigateToGoal

class NavigationActionServer(Node):
    def __init__(self, use_case):
        super().__init__('navigation_action_server')
        self._use_case = use_case
        self._action_server = ActionServer(
            self, NavigateToGoal, 'navigate_to_goal', self._execute_callback
        )

    async def _execute_callback(self, goal_handle):
        goal = goal_handle.request
        feedback = NavigateToGoal.Feedback()

        for progress in self._use_case.execute(goal.target_pose, goal.max_velocity):
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                return NavigateToGoal.Result(success=False, message='Canceled')

            feedback.distance_remaining = progress.distance_remaining
            goal_handle.publish_feedback(feedback)

        goal_handle.succeed()
        return NavigateToGoal.Result(success=True, total_distance=progress.total_distance)
```

### Action Client (Python)

```python
from rclpy.action import ActionClient

class NavigationClient(Node):
    def __init__(self):
        super().__init__('navigation_client')
        self._client = ActionClient(self, NavigateToGoal, 'navigate_to_goal')

    def navigate_to(self, pose, feedback_cb=None):
        goal = NavigateToGoal.Goal()
        goal.target_pose = pose
        self._client.wait_for_server()
        future = self._client.send_goal_async(goal, feedback_callback=feedback_cb)
        return future
```
