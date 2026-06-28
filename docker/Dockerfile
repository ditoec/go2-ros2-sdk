# Floating tag — pin the digest to prevent unexpected cache busts:
#   docker pull ros:jazzy-ros-base && bash docker/pin-base-image.sh
FROM ros@sha256:eac11a5285beeb1e1884e71f7091c610e08452e823bfb3f43afaa334375325f6

# Unified image for both hardware and simulation modes.
# Gazebo Harmonic is used for simulation via the self-contained go2_sim package.
#
# Runtime mode is controlled by the USE_SIM environment variable:
#   USE_SIM=false (default)  →  ros2 launch go2_robot_sdk robot.launch.py
#   USE_SIM=true             →  ros2 launch go2_robot_sdk simulation.launch.py

# Gazebo Harmonic (~900 MB) in its own layer — rarely changes.
# Keeping it first means adding/removing other apt packages never re-downloads Gazebo.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-jazzy-ros-gz-sim \
    ros-jazzy-ros-gz-bridge \
    ros-jazzy-ros-gz-image \
    ros-jazzy-gz-ros2-control \
    ros-jazzy-ros2-control \
    ros-jazzy-ros2-controllers \
 && rm -rf /var/lib/apt/lists/*

# System utilities + ROS2 tools — changes when adding/removing packages.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg2 \
    lsb-release \
    git \
    python3-pip \
    portaudio19-dev \
    libpulse0 \
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
    ros-jazzy-topic-tools \
    ros-jazzy-tf-transformations \
    ros-jazzy-rqt-graph \
    ros-jazzy-rqt-image-view \
    ros-jazzy-image-tools \
 && rm -rf /var/lib/apt/lists/*

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

# Heavy STT dep: faster-whisper pulls ctranslate2 (~250 MB native C++).
# Isolated so updating API SDKs below never re-downloads ctranslate2.
# faster-whisper uses CUDA automatically when STT_DEVICE=cuda and the nvidia runtime is enabled.
RUN pip install --break-system-packages faster-whisper sounddevice

# Face recognition (Modul 4.2 — face_recognition_node, gated by ENABLE_FACE).
# CPU onnxruntime + the small buffalo_sc pack, pre-baked so the first start is
# instant. buffalo_* weights carry a non-commercial-research license.
RUN pip install --break-system-packages insightface onnxruntime
RUN python3 -c "from insightface.app import FaceAnalysis; FaceAnalysis(name='buffalo_sc').prepare(ctx_id=-1); print('Face model (buffalo_sc) ready')"

# Light API clients (~5 MB pure Python) — updated more often than ctranslate2.
RUN pip install --break-system-packages openai google-genai anthropic websockets duckduckgo-search

# Supertonic TTS — on-device neural TTS (default provider, no API key required).
RUN pip install --break-system-packages supertonic

# Pre-bake the Supertonic model (~305 MB) so the first container start is instant.
RUN python3 -c "from supertonic import TTS; TTS(auto_download=True); print('Supertonic model ready')"

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
