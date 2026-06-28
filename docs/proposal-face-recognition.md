# Proposal: Face Detection & Recognition for GO2 EduPlus (Modul 4.2 / 4.4)

Decision record + design for the face pipeline that closes Modul 4.2 (face detection +
recognition with an enrollable DB) and Modul 4.4 (greet recognized people by name). Tracks
against [proposal-module-tracker.md](proposal-module-tracker.md).

**Status:** ✅ complete — `face_recognition_node` + `face_enrollment_node` (browser UI on
port 8890) + conversational greeting wiring. The web UI handles enrollment (webcam capture or
photo upload), live threshold tuning, and shows the recognized-faces table. See *As-built* below.

---

## 1. Constraints

The choice had to satisfy the project's actual deployment targets:

| Constraint | Source |
|---|---|
| Runs on **Windows 11 + 8 GB GPU** (Docker Desktop / WSL2) | [docker-compose.windows-gpu.yml](../docker/docker-compose.windows-gpu.yml) |
| Runs on **Jetson Orin NX 16 GB** (ARM64 + CUDA, JetPack 6) | [docker-compose.jetson.yml](../docker/docker-compose.jetson.yml) |
| **Offline-capable** — project default is no API keys (supertonic TTS, gemma_local) | [CLAUDE.md](../CLAUDE.md) |
| **Enrollable** DB — add a person without retraining | Proposal Modul 4.2 |
| Recognized **names feed the conversational layer** | Proposal Modul 4.4 |
| Slots into a **standalone ROS2 node** like [yolo_detector_node.py](../yolo_detector/yolo_detector/yolo_detector_node.py) — no `go2_robot_sdk` core changes | repo architecture |

This is a **paid client engagement** ("Jasa Konfigurasi"), so model **licensing** is a
first-class criterion (see §6).

---

## 2. Options considered

### A. InsightFace — SCRFD detector + ArcFace recognition (ONNX Runtime) ⭐ chosen
Industry-standard pipeline and the one already proven in the team's separate `face-captioner`
project (SCRFD detection + ArcFace embeddings + a file-system face DB). Highest accuracy
(~99.8% LFW), one library does detect+align+embed, and it runs through ONNX Runtime so the
same Python code gets CUDA on both Windows and Jetson — only the runtime wheel differs.

### B. DeepFace — wrapper over RetinaFace + ArcFace
Same underlying models behind a higher-level wrapper. Easier backend-swapping, but a heavier
dependency tree (TensorFlow by default) and fiddlier ARM64/Jetson installs. Good for
prototyping, weaker as an embedded product.

### C. face_recognition (dlib)
Simplest API, but dlib must **compile from source on Jetson ARM64** (slow), the HOG detector
is weak on angled/partial faces, and GPU use is awkward. Worst fit for the two-platform target.

### D. OpenCV YuNet detector + SFace recognition — commercial-license fallback
Both ship in OpenCV Zoo, run as small ONNX models, cross-platform, and carry **permissive
licenses usable commercially**. Accuracy a notch below ArcFace-R50 but ample for greeting a
known visitor. Held in reserve via the `FACE_MODEL_PACK` knob if the InsightFace weight
license becomes a blocker (§6).

### Comparison

| | **A. InsightFace** ⭐ | **B. DeepFace** | **C. face_recognition (dlib)** | **D. YuNet + SFace** |
|---|---|---|---|---|
| Detect / Recognize | SCRFD / ArcFace | RetinaFace / ArcFace | HOG\|CNN / dlib-ResNet | YuNet / SFace |
| LFW accuracy | ~99.8% | ~99.8% | ~99.4% | ~99.4% |
| Windows 8 GB GPU | ✅ `pip install insightface onnxruntime` | 🟡 TF dep heavy | ✅ GPU awkward | ✅ trivial |
| Jetson Orin NX ARM64 | ✅ ORT wheel + auto-download | 🟡 hard | ⬜ compile dlib | ✅ trivial |
| GPU path | CUDA EP / TensorRT FP16 | CUDA | CUDA (rebuild) | CUDA EP |
| Offline | ✅ | ✅ | ✅ | ✅ |
| Footprint | ~16 MB (buffalo_sc) | large | ~100 MB | ~5 MB |
| Enrollment | file-system DB + pickle cache (reused) | manual | folder of images | folder of images |
| Code license | MIT | MIT | MIT | Apache/MIT |
| **Model license** | ⚠️ **non-commercial research** | same models | mixed | ✅ **commercial OK** |
| Reuse from face-captioner | **high** | medium | none | none |

---

## 3. Recommendation

**Option A (InsightFace), reusing the `face-captioner` recognizer logic**, with **Option D
(YuNet + SFace) held in reserve** behind `FACE_MODEL_PACK` for a commercial-license swap.

Key refinement made during implementation: **do not port the `face-captioner` detector** —
it is a custom Torch RetinaFace with a domain-specific (Sukarno) `.pth` weights file. Instead
use InsightFace's unified `insightface.app.FaceAnalysis`, which bundles SCRFD detection +
5-point landmark alignment + ArcFace embeddings in **one `app.get(frame)` call, no Torch**,
and reuse only the *DB/matching/enrollment* logic (file-system `face_db/<Name>/*.jpg`,
`.embeddings.pkl` cache, cosine match at 0.35, `add_face`).

Use the small **`buffalo_sc`** pack (SCRFD-500MF + a small ArcFace) — real-time on CPU and
~16 MB; no need for `buffalo_l` to greet visitors.

---

## 4. As-built integration

| Piece | Location |
|---|---|
| Pure DB + cosine matcher (no rclpy) | [face_db.py](../speech_processor/speech_processor/face_db.py) |
| ROS2 recognition node (FaceAnalysis → publish) | [face_recognition_node.py](../speech_processor/speech_processor/face_recognition_node.py) |
| Browser enrollment UI + threshold tuning (port 8890) | [face_enrollment_node.py](../speech_processor/speech_processor/face_enrollment_node.py) |
| **Browser webcam bridge → `/camera/image_raw` (Windows, port 8891/8892)** | [cam_bridge_node.py](../speech_processor/speech_processor/cam_bridge_node.py) |
| Conversational greeting helper | `conversational_system_with_faces()` in [command_dispatcher.py](../speech_processor/speech_processor/command_dispatcher.py) |
| Name injection into the reply path (4.4) | `_ask_conversational()` in [voice_cmd_node.py](../speech_processor/speech_processor/voice_cmd_node.py) |
| Launch gating (`ENABLE_FACE`, `CAM_BRIDGE`) | [robot.launch.py](../go2_robot_sdk/launch/robot.launch.py) |
| Deps + model pre-bake + `face_db` volume | `docker/` Dockerfiles + compose files |
| Unit tests | [test_face_db.py](../speech_processor/test/test_face_db.py) |

**Topics**

| Topic | Type | Direction |
|---|---|---|
| `/recognized_faces` | `vision_msgs/Detection2DArray` | published (`class_id`=name, `score`=similarity) |
| `/recognized_face_names` | `std_msgs/String` | published (comma-joined known names) → consumed by voice_cmd_node |
| `/face_annotated_image` | `sensor_msgs/Image` | published (boxes + name labels) |
| `/reload_faces` | `std_msgs/Empty` | consumed by face_recognition_node — re-scan + re-embed (auto-triggered by enrollment UI) |
| `/face_threshold` | `std_msgs/Float32` | published by face_enrollment_node (slider) → consumed by face_recognition_node live |

**Enrollment UI (`face_enrollment_node`, http://localhost:8890):**
1. Open the page in a host browser (`ENABLE_FACE=true` launches the node alongside the recognizer).
2. Section 1 — **Enroll a person**: start the webcam, capture a frame (or upload a JPEG), type a name, click *Enroll*. The node writes the photo into `face_db/<Name>/` and publishes `/reload_faces` — the recognizer reloads within seconds, no restart needed.
3. Section 2 — **Tune threshold**: drag the slider and click *Apply* — publishes `/face_threshold` (Float32) to the recognizer live. The table below the slider polls `/recognized_faces` every second so you can watch real similarity scores and find the right cutoff.

`face_db/` bind-mounts to `./face_db` on the host, so enrollments survive container restarts.

---

## 5. Platform / deployment notes

- **CPU vs GPU.** `FACE_DEVICE` selects the ONNX Runtime providers. Default `cpu`
  (`buffalo_sc` runs real-time on CPU). Jetson compose defaults `FACE_DEVICE=cuda`; the
  Windows-GPU container stays `cpu` because that image has **no CUDA toolkit** (its GPU is the
  llama.cpp sidecar). The node logs `onnxruntime.get_available_providers()` at startup and
  warns + falls back to CPU if a requested CUDA EP is missing.
- **Jetson onnxruntime-gpu.** `onnxruntime-gpu` for aarch64 is **not on PyPI**; the L4T base
  image ships a CUDA-enabled build, so the Jetson Dockerfile installs **insightface only** (a
  CPU `onnxruntime` wheel would shadow the GPU one). If `CUDAExecutionProvider` is absent at
  build time, install a JetPack-matched wheel from the `jp6/cu126` index / Jetson Zoo /
  Ultralytics-hosted wheel / a community build. A common TensorRT pitfall is the ONNX
  **INT64 → TensorRT** cast — sanitize the model before building an `.engine` if you go that route.
- **numpy.** insightface needs `numpy<2`; the repo already pins `numpy==1.26.4`, so they agree.
- **Model caching.** `buffalo_sc` is pre-baked into all three images (`FaceAnalysis(...).prepare(ctx_id=-1)`
  at build), so the first container start is instant and works offline.

---

## 6. ⚠️ Licensing — decide before commercial delivery

InsightFace's **code is MIT, but the pretrained `buffalo_*` / `antelopev2` weight packs are
licensed "for non-commercial research purposes only"** — including the auto-downloaded
weights. For a paid client deployment this is a genuine risk. Options, in order of effort:

1. **Confirm scope with the client** — the robot is an *EduPlus* research/education unit, which
   may qualify. Get it in writing.
2. **Swap to YuNet + SFace** via `FACE_MODEL_PACK` — commercially-licensed weights, same node,
   slightly lower accuracy. *(Requires a small adapter: YuNet+SFace are not a FaceAnalysis pack,
   so the node's `_build_app` would branch to OpenCV Zoo models — a contained change.)*
3. **Email `recognition-oss-pack@insightface.ai`** for a commercial license.
4. **Train/fine-tune** an ArcFace head on a license-clean dataset (highest effort).

The scaffold ships `buffalo_sc` (fastest path, max reuse) with the license flagged in
[CLAUDE.md](../CLAUDE.md) and the model kept behind `FACE_MODEL_PACK` so the decision does not
block the build.

---

## 7. Verification

```bash
colcon build --packages-select speech_processor go2_robot_sdk && source install/setup.bash
```

### Hardware (robot camera over WebRTC)

```bash
ENABLE_FACE=true ros2 launch go2_robot_sdk robot.launch.py
# → face_recognition_node on /camera/image_raw (robot camera)
# → face_enrollment_node on http://localhost:8890
```

### Windows (Docker) — webcam via cam_bridge

On Windows the robot camera is not accessible inside the Docker container. `cam_bridge_node` fills this role. It is the **recommended path** for development and demos on Windows.

```bash
# Windows GPU (cam_bridge=true is the default)
ENABLE_FACE=true docker-compose \
  -f docker/docker-compose.yml \
  -f docker/docker-compose.windows-gpu.yml up

# → Open http://localhost:8891 — Connect → Start Streaming (webcam → /camera/image_raw)
# → face_recognition_node picks up /camera/image_raw automatically
# → Open http://localhost:8890 for enrollment and threshold tuning
```

### Enrollment via UI

```
Open http://localhost:8890 → start webcam (or upload a photo) → type "Dito" → Enroll
→ writes face_db/Dito/0000.jpg  →  auto-publishes /reload_faces
Container log: "Face DB: 1 people, 1 embeddings at /ros2_ws/face_db"
```

### Verify recognition

```bash
ros2 topic echo /recognized_face_names      # → "Dito" when recognized, "" otherwise
ros2 topic echo /recognized_faces           # Detection2DArray, class_id: Dito, score: 0.6–0.9
ros2 run image_tools showimage --ros-args -r /image:=/face_annotated_image
```

### Standalone recognition node (simulation camera remap)

```bash
ros2 run speech_processor face_recognition_node --ros-args \
  -p face_db_path:=/tmp/face_db -p face_device:=cpu \
  -r /camera/image_raw:=/go2_camera/color/image_raw
```

### Threshold tuning

Drag the slider on `http://localhost:8890` and watch the live score table to find the right cutoff. Manual override:

```bash
ros2 topic pub /face_threshold std_msgs/Float32 "{data: 0.40}" --once
```

### Manual reload (photos added outside the UI)

```bash
ros2 topic pub /reload_faces std_msgs/Empty "{}" --once
```

### End-to-end greeting (Modul 4.4)

```bash
ENABLE_FACE=true ENABLE_STT=true ENABLE_CONV_MEMORY=true NLU_PROVIDER=gemma_local \
  docker-compose -f docker/docker-compose.yml -f docker/docker-compose.windows-gpu.yml up
# With a known face in view, say "elliot, hello, who am I?" → robot replies with the name
```

### Unit tests

```bash
colcon test --packages-select speech_processor && colcon test-result --all --verbose
```

---

## 8. Sources

- [InsightFace (deepinsight/insightface)](https://github.com/deepinsight/insightface) · [Windows install](https://github.com/cobanov/insightface_windows) · [deployment/TensorRT guides](https://www.insightface.ai/guides)
- [InsightFace-REST (SCRFD+ArcFace, TensorRT/Docker)](https://github.com/SthPhoenix/InsightFace-REST)
- [onnxruntime-gpu for Jetson (community aarch64 wheels)](https://github.com/guyin24/onnxruntime-gpu-for-jetson) · [ONNX Runtime install docs](https://onnxruntime.ai/docs/install/)
- [LearnOpenCV — Face Detection model comparison 2025](https://learnopencv.com/what-is-face-detection-the-ultimate-guide/)
- [Top face recognition libraries comparison](https://nulldog.com/top-face-recognition-libraries-for-accurate-identification)
- [Eden AI — free face-compare tools/models](https://www.edenai.co/post/top-free-face-compare-tools-apis-and-open-source-models)
