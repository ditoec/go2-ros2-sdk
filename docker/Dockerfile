# Floating tag — pin the digest to prevent unexpected cache busts:
#   docker pull ros:humble-ros-base && bash docker/pin-base-image.sh
FROM ros@sha256:7bea3d9aa2483d3ca34c8e30d921b79273b0913bd7dc64bebf51d082b5d107e4

# Unified image for both hardware and simulation modes.
# Gazebo Fortress is used for simulation via the self-contained go2_sim package.
#
# Runtime mode is controlled by the USE_SIM environment variable:
#   USE_SIM=false (default)  →  ros2 launch go2_robot_sdk robot.launch.py
#   USE_SIM=true             →  ros2 launch go2_robot_sdk simulation.launch.py

# Gazebo Fortress (~900 MB) in its own layer — rarely changes.
# Keeping it first means adding/removing other apt packages never re-downloads Gazebo.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-humble-ros-gz-sim \
    ros-humble-ros-gz-bridge \
    ros-humble-ros-gz-image \
    ros-humble-gz-ros2-control \
    ros-humble-ros2-control \
    ros-humble-ros2-controllers \
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
    ros-humble-rviz2 \
    software-properties-common \
    ros-humble-rmw-cyclonedds-cpp \
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
    ros-humble-topic-tools \
    ros-humble-tf-transformations \
    ros-humble-rqt-graph \
    ros-humble-rqt-image-view \
    ros-humble-image-tools \
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
    pip install --ignore-installed -r /dev/stdin
RUN pip install --ignore-installed torch ultralytics

# Heavy STT dep: faster-whisper pulls ctranslate2 (~250 MB native C++).
# Isolated so updating API SDKs below never re-downloads ctranslate2.
# faster-whisper uses CUDA automatically when STT_DEVICE=cuda and the nvidia runtime is enabled.
RUN pip install faster-whisper sounddevice

# Face recognition (Modul 4.2 — face_recognition_node, gated by ENABLE_FACE).
# CPU onnxruntime + the small buffalo_sc pack, pre-baked so the first start is
# instant. buffalo_* weights carry a non-commercial-research license.
RUN pip install insightface onnxruntime
RUN python3 -c "from insightface.app import FaceAnalysis; FaceAnalysis(name='buffalo_sc').prepare(ctx_id=-1); print('Face model (buffalo_sc) ready')"

# Light API clients (~5 MB pure Python) — updated more often than ctranslate2.
RUN pip install openai google-genai anthropic websockets duckduckgo-search

# Supertonic TTS — on-device neural TTS (default provider, no API key required).
RUN pip install supertonic

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

# unitree_go: Unitree's official ROS2 interfaces package (SportModeState,
# LowState, WirelessController, etc.), vendored from source since it's not an
# official ros-humble-* apt package. go2_driver_node's CycloneDDS ingest path
# subscribes to these types directly (not this repo's own go2_interfaces
# clones of the same fields) because ROS2's rosidl toolchain bakes the
# package name into each message's DDS wire-level type identifier
# (<package>::msg::dds_::<Type>_) -- a same-named go2_interfaces clone
# produces a different DDS type ID than the robot firmware's native
# unitree_go publisher, so a go2_interfaces-typed subscriber can never
# receive the robot's data even though the fields are identical (confirmed
# live on hardware: `ros2 topic echo` refuses with "contains more than one
# type"). Needed even on this WebRTC-default image because go2_driver_node
# imports unitree_go.msg unconditionally at module load time, regardless of
# CONN_TYPE.
# unitree_api: Unitree's official request/response envelope package
# (Request/Response, with nested header.identity.{id,api_id},
# header.lease.id, header.policy.{priority,noreply}), vendored alongside
# unitree_go for the same reason. cyclonedds_adapter.py publishes robot
# commands to /api/sport/request using THIS package's Request type, not
# unitree_go's simpler Req (uuid+body) -- confirmed live that the robot's
# actual command receiver on that topic, and all 9 native robot-side
# publishers sharing it, are typed unitree_api/msg/Request. unitree_go/Req
# is a DDS-type-valid but apparently-unused legacy schema: fixing the DDS
# type-name collision by switching to it (an earlier version of this
# Dockerfile/cyclonedds_adapter.py) was necessary but not sufficient --
# commands still went unreceived because it's the wrong schema, not just
# the wrong package name.
#
# rosidl_generate_dds_interfaces (Connext-specific IDL export, RTI's
# proprietary DDS vendor tooling) is stripped out of both packages'
# CMakeLists.txt: it needs rosidl_generator_dds_idl, an undeclared,
# non-portable dependency not available here and not needed for plain
# ROS2/CycloneDDS typed pub-sub, which only needs the standard
# rosidl_generate_interfaces() call above it.
RUN git clone --depth 1 https://github.com/unitreerobotics/unitree_ros2.git /tmp/unitree_ros2 && \
    cp -r /tmp/unitree_ros2/cyclonedds_ws/src/unitree/unitree_go /ros2_ws/src/unitree_go && \
    cp -r /tmp/unitree_ros2/cyclonedds_ws/src/unitree/unitree_api /ros2_ws/src/unitree_api && \
    rm -rf /tmp/unitree_ros2 && \
    sed -i \
      -e '/find_package(rosidl_generator_dds_idl REQUIRED)/d' \
      -e '/^rosidl_generate_dds_interfaces(/,/^)$/d' \
      -e '/^add_dependencies(/,/^)$/d' \
      /ros2_ws/src/unitree_go/CMakeLists.txt \
      /ros2_ws/src/unitree_api/CMakeLists.txt

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
