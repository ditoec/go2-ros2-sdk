#!/bin/bash
set -e

# Source ROS2 environment
source /opt/ros/${ROS_DISTRO}/setup.bash
source /ros2_ws/install/setup.bash

# Remove stale X11 lock files left by a previous container run (Docker restart reuses
# the overlay filesystem, so /tmp/.X1-lock survives between restarts and blocks Xvfb).
rm -f /tmp/.X1-lock /tmp/.X11-unix/X1 2>/dev/null || true

# Start virtual X display
Xvfb :1 -screen 0 "${VNC_RESOLUTION:-1920x1080}x24" &
export DISPLAY=:1

# Wait until Xvfb is actually accepting connections (up to 10 s) instead of a fixed sleep.
for _i in $(seq 1 20); do
    xdpyinfo >/dev/null 2>&1 && break
    sleep 0.5
done

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
