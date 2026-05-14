cmake_minimum_required(VERSION 3.8)
project(go2_sim)

find_package(ament_cmake REQUIRED)

# Install launch files
install(DIRECTORY launch
  DESTINATION share/${PROJECT_NAME}
)

# Install Gazebo worlds
install(DIRECTORY worlds
  DESTINATION share/${PROJECT_NAME}
)

# Install bundled Gazebo models (cafe environment + furniture + AprilTags)
install(DIRECTORY models
  DESTINATION share/${PROJECT_NAME}
)

# Install bridge / controller config
install(DIRECTORY config
  DESTINATION share/${PROJECT_NAME}
)

# Install bundled Python scripts (gait controller + odometry) as executables
install(PROGRAMS
  scripts/robot_controller_gazebo.py
  scripts/cmd_vel_pub.py
  scripts/QuadrupedOdometryNode.py
  scripts/sim_cmd_node.py
  DESTINATION lib/${PROJECT_NAME}
)

# Install Python sub-packages (ForwardKinematics, InverseKinematics, etc.)
# They are placed alongside the executables so relative imports resolve.
install(DIRECTORY
  scripts/ForwardKinematics
  scripts/InverseKinematics
  scripts/RobotController
  scripts/RoboticsUtilities
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
