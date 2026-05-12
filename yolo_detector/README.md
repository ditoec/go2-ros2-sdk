# yolo_detector

YOLO object detection for the GO2 ROS2 SDK using [Ultralytics](https://github.com/ultralytics/ultralytics).

Subscribes to `/camera/image_raw` and publishes a `vision_msgs/Detection2DArray` on `/detected_objects`. Optionally publishes an annotated image with bounding boxes on `/annotated_image`.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `model` | string | `yolo11n.pt` | Ultralytics model filename. Downloaded on first run (~6 MB for nano). |
| `device` | string | `cpu` | Inference device: `cpu` or `cuda`. |
| `detection_threshold` | float | `0.5` | Minimum confidence score (0.0–1.0). Raise to reduce false positives. |
| `publish_annotated_image` | bool | `true` | Publish bounding-box image on `/annotated_image`. |

## Model options

| Model | Size | Speed (GPU) | Notes |
|---|---|---|---|
| `yolo11n.pt` | ~6 MB | fastest | Default — good for CPU/edge |
| `yolo11s.pt` | ~22 MB | fast | Better accuracy |
| `yolo11m.pt` | ~52 MB | moderate | Balanced |
| `yolo11l.pt` | ~87 MB | slower | High accuracy |
| `yolo11x.pt` | ~137 MB | slowest | Best accuracy |

YOLOv8 variants (`yolov8n.pt`, `yolov8s.pt`, etc.) are also supported via the same `model` parameter.

## Running

**Hardware mode** (driver publishes on `/camera/image_raw`):
```bash
ros2 run yolo_detector yolo_detector_node
```

**Simulation mode** (remap to Gazebo camera topic):
```bash
ros2 run yolo_detector yolo_detector_node \
    --ros-args -r /camera/image_raw:=/go2_camera/color/image
```

**GPU with a larger model:**
```bash
ros2 run yolo_detector yolo_detector_node \
    --ros-args -p model:=yolo11s.pt -p device:=cuda -p detection_threshold:=0.4
```

**Disable annotated image** (saves bandwidth):
```bash
ros2 run yolo_detector yolo_detector_node \
    --ros-args -p publish_annotated_image:=False
```

**View detections and annotated image:**
```bash
ros2 topic echo /detected_objects
ros2 run image_tools showimage --ros-args -r /image:=/annotated_image
```

## Notes

- Model weights are downloaded to `~/.cache/ultralytics/` on first inference call. In Docker, mount a volume to persist the cache across container restarts.
- `class_id` in `ObjectHypothesis` contains the string label directly (e.g., `"dog"`, `"person"`), matching the original coco_detector behaviour.
- Default threshold is `0.5` (YOLO confidence differs from FasterRCNN — use `0.7`+ for stricter filtering).
