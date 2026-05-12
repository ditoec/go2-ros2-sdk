# WebRTC Commands

## Sending Commands Without Modifying Driver Code

Publish to `/webrtc_req` (`go2_interfaces/msg/WebRtcReq`):

```bash
ros2 topic pub /webrtc_req go2_interfaces/msg/WebRtcReq \
  "{api_id: <ID>, parameter: '<JSON>', topic: '<TOPIC>'}" --once
```

`parameter` is a JSON string. Leave it empty (`""`) if the command takes no payload.

## Sport Mode Commands (`ROBOT_CMD`)

All use `topic: 'rt/api/sport/request'`:

| Command | api_id |
|---|---|
| Hello (wave) | 1016 |
| StandUp | 1004 |
| StandDown | 1005 |
| Sit | 1009 |
| RiseSit | 1010 |
| BalanceStand | 1002 |
| RecoveryStand | 1006 |
| Damp | 1001 |
| StopMove | 1003 |
| Stretch | 1017 |
| Dance1 | 1022 |
| Dance2 | 1023 |
| FrontFlip | 1030 |
| FrontJump | 1031 |
| WiggleHips | 1033 |
| FingerHeart | 1036 |
| Handstand | 1301 |
| MoonWalk | 1305 |
| Move | 1008 |
| Euler | 1007 |
| BodyHeight | 1013 |
| SpeedLevel | 1015 |
| SwitchGait | 1011 |

Full list in `go2_robot_sdk/domain/constants/robot_commands.py`.

## Common Examples

```bash
# Wave hello
ros2 topic pub /webrtc_req go2_interfaces/msg/WebRtcReq \
  "{api_id: 1016, topic: 'rt/api/sport/request'}" --once

# Sit down
ros2 topic pub /webrtc_req go2_interfaces/msg/WebRtcReq \
  "{api_id: 1009, topic: 'rt/api/sport/request'}" --once

# Stand up
ros2 topic pub /webrtc_req go2_interfaces/msg/WebRtcReq \
  "{api_id: 1004, topic: 'rt/api/sport/request'}" --once

# Enable obstacle avoidance
ros2 topic pub /webrtc_req go2_interfaces/msg/WebRtcReq \
  "{api_id: 1, topic: 'rt/api/obstacles_avoid/request'}" --once
```

## WebRTC Topic Strings (`RTC_TOPIC`)

Key strings defined in `go2_robot_sdk/domain/constants/webrtc_topics.py`:

| Key | Topic string |
|---|---|
| `LOW_STATE` | `rt/lf/lowstate` |
| `LF_SPORT_MOD_STATE` | `rt/lf/sportmodestate` |
| `ROBOTODOM` | `rt/utlidar/robot_pose` |
| `ULIDAR_ARRAY` | `rt/utlidar/voxel_map_compressed` |
| `SPORT_MOD` | `rt/api/sport/request` |
| `OBSTACLES_AVOID` | `rt/api/obstacles_avoid/request` |
| `VUI` | `rt/api/vui/request` |
| `AUDIO_HUB_REQ` | `rt/api/audiohub/request` |
| `BASH_REQ` | `rt/api/bashrunner/request` |
| `WIRELESS_CONTROLLER` | `rt/wirelesscontroller` |

## Joystick Shortcuts

The `Go2DriverNode` directly handles `/joy` button presses without going through `/webrtc_req`:

| Button index | Action |
|---|---|
| 0 | Stand up |
| 1 | Stand down |

These are processed by `RobotControlService.handle_joy_command()`.

## Adding a New Command

1. Add the command ID to `ROBOT_CMD` in `go2_robot_sdk/domain/constants/robot_commands.py`.
2. Add the topic string to `RTC_TOPIC` in `webrtc_topics.py` if it uses a new topic.
3. Publish via `/webrtc_req` — no driver code changes needed.

For commands that require automatic triggering (e.g., on a timer or in response to a sensor), add a subscriber or timer in `Go2DriverNode` and call `self.robot_control_service.handle_webrtc_request()`.
