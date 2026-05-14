#!/bin/bash
set -e

# Source ROS2 environment
source /opt/ros/${ROS_DISTRO}/setup.bash
source /ros2_ws/install/setup.bash

# Start virtual X display
Xvfb :1 -screen 0 "${VNC_RESOLUTION:-1920x1080}x24" &
sleep 1
export DISPLAY=:1

# Start XFCE4 desktop
startxfce4 &

# Start x11vnc — handles VNC password format correctly
x11vnc -display :1 \
    -rfbport 5901 \
    -passwd "${VNC_PASSWORD:-ros2vnc}" \
    -forever \
    -shared \
    -noxdamage \
    -quiet &

echo "VNC server started — connect to localhost:5901 with password '${VNC_PASSWORD:-ros2vnc}'"

# If an explicit command was passed (e.g. docker run ... bash), run it directly.
# Otherwise select the launch file based on USE_SIM.
if [ "$#" -gt 0 ]; then
    exec "$@"
elif [ "${USE_SIM:-false}" = "true" ]; then
    echo "Mode: SIMULATION (USE_SIM=true)"
    exec ros2 launch go2_robot_sdk simulation.launch.py foxglove:=true
else
    echo "Mode: HARDWARE (USE_SIM=false) — robot IP: ${ROBOT_IP}"
    exec ros2 launch go2_robot_sdk robot.launch.py
fi
