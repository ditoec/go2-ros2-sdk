# Floating tag — pin the digest to prevent unexpected cache busts:
#   docker pull ros:jazzy-ros-base && bash docker/pin-base-image.sh
FROM ros@sha256:eac11a5285beeb1e1884e71f7091c610e08452e823bfb3f43afaa334375325f6

# Unified image for both hardware and simulation modes.
# Upgraded from Humble to Jazzy — the SDK CI validates both; Gazebo Harmonic
# is used for simulation via the self-contained go2_sim package.
#
# Runtime mode is controlled by the USE_SIM environment variable:
#   USE_SIM=false (default)  →  ros2 launch go2_robot_sdk robot.launch.py
#   USE_SIM=true             →  ros2 launch go2_robot_sdk simulation.launch.py

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg2 \
    lsb-release \
    git \
    python3-pip \
    portaudio19-dev \
    libpulse0 \
    libasound2-plugins \
    mesa-utils \
    libgl1 \
    libgl1-mesa-dri \
    libgles2 \
    ros-jazzy-rviz2 \
    software-properties-common \
    ros-jazzy-rmw-cyclonedds-cpp \
    ffmpeg \
    xvfb \
    x11vnc \
    xfce4 \
    xfce4-terminal \
    xfce4-screenshooter \
    mousepad \
    dbus-x11 \
    x11-utils \
    x11-xserver-utils \
    # Simulation: Gazebo Harmonic + ROS2 bridge
    ros-jazzy-ros-gz-sim \
    ros-jazzy-ros-gz-bridge \
    ros-jazzy-ros-gz-image \
    ros-jazzy-gz-ros2-control \
    ros-jazzy-ros2-control \
    ros-jazzy-ros2-controllers \
    # Topic relay (joint_states + cmd_vel inside go2_sim)
    ros-jazzy-topic-tools \
    # Required by QuadrupedOdometryNode and gait controller scripts
    ros-jazzy-tf-transformations \
    # ROS2 graph visualization and image viewing
    ros-jazzy-rqt-graph \
    ros-jazzy-rqt-image-view \
    ros-jazzy-image-tools \
    # Offline TTS (default provider, no API key required)
    espeak-ng \
 && rm -rf /var/lib/apt/lists/*

# Route all ALSA audio through PulseAudio so PortAudio/sounddevice can see
# the WSLg mic even when /dev/snd is absent.  PULSE_SERVER must be set at
# runtime (docker-compose.windows.yml sets it to the WSLg socket).
RUN printf 'pcm.default pulse\nctl.default pulse\n' > /etc/asound.conf

WORKDIR /ros2_ws

# ── Layer 1: Python deps ──────────────────────────────────────────────────────
# Only re-runs when requirements.txt changes.
# torch/ultralytics (~1-3 GB) are split into a separate layer so a requirements
# change doesn't force a full torch re-download.
# For GPU/CUDA support swap the torch line for the appropriate CUDA wheel
# (e.g. torch --index-url https://download.pytorch.org/whl/cu121).
COPY requirements.txt /ros2_ws/src/requirements.txt
RUN grep -vE '^(torch|ultralytics)' /ros2_ws/src/requirements.txt | \
    pip install --break-system-packages --ignore-installed -r /dev/stdin
RUN pip install --break-system-packages --ignore-installed torch ultralytics

# STT + unified voice deps (used by speech_processor/stt_node.py and TTSProvider_OpenAI)
# faster-whisper uses CUDA automatically when STT_DEVICE=cuda and the nvidia runtime is enabled.
RUN pip install --break-system-packages faster-whisper sounddevice openai google-genai anthropic

# Piper TTS — offline neural TTS (default provider, no API key required).
# piper-phonemize uses espeak-ng for phonemisation (already installed above via apt).
RUN pip install --break-system-packages piper-tts

# Pre-bake the default Piper voice model so the first container start is instant.
# Model: en_US-lessac-medium (~65 MB .onnx + tiny .json).
# To use a different default voice, pass --build-arg PIPER_VOICE=en_US-ryan-high at build time.
ARG PIPER_VOICE=en_US-lessac-medium
ENV PIPER_VOICE_DIR=/root/.local/share/piper/voices
RUN set -e && \
    python3 -c " \
import os, sys, urllib.request; \
voice = '${PIPER_VOICE}'; \
parts = voice.split('-', 2); \
lang_country, speaker, quality = parts[0], parts[1], parts[2]; \
lang = lang_country.split('_')[0].lower(); \
d = '/root/.local/share/piper/voices'; \
os.makedirs(d, exist_ok=True); \
base = f'https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/{lang}/{lang_country}/{speaker}/{quality}'; \
[urllib.request.urlretrieve(f'{base}/{f}', os.path.join(d, f)) or print(f'Downloaded {f}') \
 for f in [f'{voice}.onnx', f'{voice}.onnx.json'] if not os.path.exists(os.path.join(d, f))]; \
print('Piper voice ready:', voice) \
"

# ── Layer 2: ROS2 package deps ───────────────────────────────────────────────
# Copy only package.xml files so rosdep only re-runs when dependencies change,
# not on every source edit.
COPY coco_detector/package.xml       /ros2_ws/src/coco_detector/package.xml
COPY go2_description/package.xml    /ros2_ws/src/go2_description/package.xml
COPY go2_interfaces/package.xml     /ros2_ws/src/go2_interfaces/package.xml
COPY go2_robot_sdk/package.xml      /ros2_ws/src/go2_robot_sdk/package.xml
COPY go2_sim/package.xml            /ros2_ws/src/go2_sim/package.xml
COPY lidar_processor/package.xml    /ros2_ws/src/lidar_processor/package.xml
COPY lidar_processor_cpp/package.xml /ros2_ws/src/lidar_processor_cpp/package.xml
COPY quadropted_msgs/package.xml    /ros2_ws/src/quadropted_msgs/package.xml
COPY speech_processor/package.xml   /ros2_ws/src/speech_processor/package.xml
COPY yolo_detector/package.xml      /ros2_ws/src/yolo_detector/package.xml
RUN apt-get update && \
    . /opt/ros/${ROS_DISTRO}/setup.sh && \
    rosdep update && \
    rosdep install --from-paths src --ignore-src -r -y && \
    rm -rf /var/lib/apt/lists/*

# ── Layer 3: Source + build ───────────────────────────────────────────────────
# Full copy comes last — only this layer re-runs on source changes.
# chmod +x is explicit: Windows build hosts may not preserve the Unix execute bit.
COPY . /ros2_ws/src
# Strip Windows CRLF line endings from all Python and shell scripts.
# Files checked out on Windows or copied via a Windows Docker build context
# arrive with \r\n, making the shebang line unresolvable on Linux.
RUN find /ros2_ws/src -type f \( -name "*.py" -o -name "*.sh" \) \
      -exec sed -i 's/\r$//' {} \; && \
    chmod +x /ros2_ws/src/docker/entrypoint.sh && \
    . /opt/ros/${ROS_DISTRO}/setup.sh && \
    colcon build

RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> /root/.bashrc && \
    echo "source /ros2_ws/install/setup.bash" >> /root/.bashrc

# Runtime environment defaults
ENV ROBOT_IP=""
ENV CONN_TYPE="webrtc"
ENV WEBRTC_SERVER_HOST="0.0.0.0"
ENV WEBRTC_SERVER_PORT="9991"
ENV USE_SIM="false"

# VNC — default password "ros2vnc", override with VNC_PASSWORD at runtime
ENV DISPLAY=:1
ENV VNC_PORT=5901
ENV VNC_RESOLUTION=1920x1080

RUN mkdir -p /root/.vnc

RUN sed --in-place --expression \
      '$isource "/ros2_ws/install/setup.bash"' \
      /ros_entrypoint.sh

# No CMD — entrypoint.sh selects the launch file based on USE_SIM
CMD []
