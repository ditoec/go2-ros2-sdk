cmake_minimum_required(VERSION 3.8)
project(go2_interfaces)

# Fix for CMake policy CMP0148 warning
if(POLICY CMP0148)
  cmake_policy(SET CMP0148 OLD)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(rosidl_default_generators REQUIRED)
# uncomment the following section in order to fill in
# further dependencies manually.


rosidl_generate_interfaces(${PROJECT_NAME}
  # Original go2_interfaces messages
  "msg/Go2Cmd.msg"
  "msg/Go2State.msg"
  "msg/Go2Move.msg"
  "msg/Go2RpyCmd.msg"
  "msg/IMU.msg"

  # Merged from unitree_go
  # NOTE: SportModeState/LowState/WirelessController/Req/Res were removed
  # from this list (2026-08) -- they duplicated unitree_go's own messages
  # under a different package name, which ROS2's rosidl toolchain resolves
  # to a different DDS wire-level type identifier than the robot firmware's
  # native unitree_go publisher. That made them permanently unable to
  # receive/send real robot data over CycloneDDS despite identical fields
  # (confirmed live on hardware: `ros2 topic echo` refused with "contains
  # more than one type"). go2_driver_node.py and cyclonedds_adapter.py now
  # import the real unitree_go package instead (vendored from source in
  # docker/Dockerfile*) -- see docs/connection-modes.md for the full
  # explanation. Do not re-add these five here.
  "msg/AudioData.msg"
  "msg/BmsCmd.msg"
  "msg/BmsState.msg"
  "msg/Error.msg"
  "msg/Go2FrontVideoData.msg"
  "msg/HeightMap.msg"
  "msg/InterfaceConfig.msg"
  "msg/LidarState.msg"
  "msg/LowCmd.msg"
  "msg/MotorCmd.msg"
  "msg/MotorCmds.msg"
  "msg/MotorState.msg"
  "msg/MotorStates.msg"
  "msg/PathPoint.msg"
  "msg/SportModeCmd.msg"
  "msg/TimeSpec.msg"
  "msg/UwbState.msg"
  "msg/UwbSwitch.msg"
  "msg/VoxelMapCompressed.msg"
  "msg/VoxelHeightMapState.msg"
  "msg/WebRtcReq.msg"

  DEPENDENCIES geometry_msgs # Add packages that above messages depend on
)


ament_package()
