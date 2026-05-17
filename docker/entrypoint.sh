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

# ── Audio setup ────────────────────────────────────────────────────────────
# Priority:
#   1. Real ALSA hardware (Jetson, native Linux) — leave audio untouched.
#   2. WSLg PulseAudio socket — works only when uid matches (native WSL shell).
#      Docker containers run as root (uid 0); WSLg PA runs as uid 1000, so
#      auth-unix-uid rejects us even with the correct cookie.
#   3. Local PulseAudio daemon with a null source so PortAudio/sounddevice
#      always finds a device.  Use http://localhost:8888 (mic_bridge_node)
#      in the host browser to relay real microphone audio over WebSocket.

_start_local_pa() {
    mkdir -p /run/pulse
    cat > /tmp/pulse-docker.pa << 'PAEOF'
load-module module-native-protocol-unix auth-anonymous=1 socket=/run/pulse/native
load-module module-null-source source_name=null_source source_properties=device.description="NullMicrophone"
load-module module-null-sink   sink_name=null_sink   sink_properties=device.description="NullOutput"
PAEOF
    pulseaudio --daemonize=yes --exit-idle-time=-1 --disable-shm=true \
        --file=/tmp/pulse-docker.pa --no-config 2>/dev/null || true
    sleep 1
    export PULSE_SERVER=unix:/run/pulse/native
    unset PULSE_COOKIE
}

if [ -d /proc/asound/card0 ]; then
    echo "Audio: ALSA hardware detected — using directly"
elif [ -S "/tmp/pulse/native" ]; then
    if PULSE_SERVER=unix:/tmp/pulse/native pactl info >/dev/null 2>&1; then
        echo "Audio: WSLg PulseAudio connected — Windows microphone available"
    else
        echo "Audio: WSLg PA auth failed (UID mismatch) — starting local PulseAudio (null source)"
        echo "       Open http://localhost:8888 in your browser to use your Windows microphone"
        _start_local_pa
    fi
else
    echo "Audio: No ALSA or WSLg socket — starting local PulseAudio (null source)"
    echo "       Open http://localhost:8888 in your browser to use your Windows microphone"
    _start_local_pa
fi

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
