#!/bin/bash
set -e

# Source ROS2 environment
source /opt/ros/${ROS_DISTRO}/setup.bash
source /ros2_ws/install/setup.bash

# Allow overriding VNC password at runtime
if [ -n "$VNC_PASSWORD" ]; then
    python3 -c "
import sys
pw = sys.argv[1]
data = bytes(int('{:08b}'.format(b)[::-1], 2) for b in (pw.encode() + b'\x00'*8)[:8])
open('/root/.vnc/passwd', 'wb').write(data)
" "$VNC_PASSWORD"
    chmod 600 /root/.vnc/passwd
fi

# Start VNC server on display :1 (port 5901)
# -localhost no allows connections from outside the container (Windows host)
vncserver :1 \
    -geometry "${VNC_RESOLUTION:-1920x1080}" \
    -depth 24 \
    -SecurityTypes VncAuth \
    -localhost no 2>/dev/null || true

echo "VNC server started — connect to localhost:${VNC_PORT:-5901} with password '${VNC_PASSWORD:-ros2vnc}'"

# If an explicit command was passed (e.g. docker run ... bash), run it directly.
# Otherwise select the launch file based on USE_SIM.
if [ "$#" -gt 0 ]; then
    exec "$@"
elif [ "${USE_SIM:-false}" = "true" ]; then
    echo "Mode: SIMULATION (USE_SIM=true)"
    exec ros2 launch go2_robot_sdk simulation.launch.py
else
    echo "Mode: HARDWARE (USE_SIM=false) — robot IP: ${ROBOT_IP}"
    exec ros2 launch go2_robot_sdk robot.launch.py
fi
