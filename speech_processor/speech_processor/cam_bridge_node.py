#!/usr/bin/env python3

# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

"""
cam_bridge_node — Browser-based camera source for the GO2 vision pipeline (Windows).

On Windows (Docker Desktop + WSL2) the robot's hardware camera arrives over WebRTC
and is fine when the robot is connected, but during development or demo prep you often
want to point a laptop webcam at a subject without having the robot present. This node
does for video what mic_bridge_node does for audio: it serves a small HTML page on
http://localhost:8891; the browser captures the webcam via getUserMedia, encodes each
frame as a JPEG, and sends it over WebSocket to the container. The node decodes the
frames and publishes them as standard ROS2 image messages so the rest of the pipeline
(face_recognition_node, yolo_detector_node, gemma_vision_node) works unchanged.

Publications:
  /camera/image_raw    (sensor_msgs/Image)      — BGR8, frame-rate controlled by the browser
  /camera/camera_info  (sensor_msgs/CameraInfo) — identity calibration (no distortion);
                                                   adequate for detection/recognition — not for 3-D reconstruction

Parameters (env-var defaults wired in robot.launch.py):
  http_port   (int,   default 8891)
  ws_port     (int,   default 8892)
  image_topic (str,   default /camera/image_raw — remap for sim: /go2_camera/color/image)
  frame_id    (str,   default camera_link)
"""

import asyncio
import http.server
import threading

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image

# ---------------------------------------------------------------------------
# HTML page
# ---------------------------------------------------------------------------

_HTML = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Camera Bridge — GO2 Robot</title>
<style>
*{box-sizing:border-box}
body{font-family:sans-serif;max-width:720px;margin:48px auto;padding:0 20px;color:#222}
h2{margin-bottom:4px}
p.sub{color:#555;margin:6px 0 24px;font-size:14px}
.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:10px}
.btn{padding:10px 22px;font-size:14px;cursor:pointer;border-radius:6px;border:1px solid #aaa;background:#f3f3f3}
.btn:disabled{opacity:.45;cursor:not-allowed}
.btn-primary{background:#dbeafe;border-color:#60a5fa}
.btn-active{background:#dcfce7;border-color:#4ade80;font-weight:bold}
.btn-danger{background:#fee2e2;border-color:#f87171}
video{width:100%;max-width:640px;border-radius:8px;background:#111;display:block;margin:12px 0}
canvas{display:none}
#status{font-weight:bold;min-height:1.4em;margin:8px 0}
#indicator{display:inline-block;width:10px;height:10px;border-radius:50%;background:#ccc;margin-right:6px;vertical-align:middle}
#indicator.on{background:#22c55e;box-shadow:0 0 6px #22c55e}
.meta{font-size:12px;color:#666;margin-top:4px}
label{font-size:13px}
input[type=range]{vertical-align:middle;margin:0 6px}
</style>
</head>
<body>
<h2>Camera Bridge — GO2 Robot</h2>
<p class="sub">Streams your browser webcam to the robot container as
<code>/camera/image_raw</code>. The face recognition and object detection pipelines
use this topic automatically — no remapping needed.</p>

<div class="row">
  <button id="connectBtn" class="btn btn-primary" onclick="doConnect()">&#128247; Connect</button>
  <button id="startBtn"   class="btn" onclick="toggleStream()" style="display:none">&#9654; Start Streaming</button>
  <button id="discBtn"    class="btn btn-danger" onclick="doDisconnect()" style="display:none">&#10006; Disconnect</button>
</div>

<p id="status"><span id="indicator"></span>Not connected.</p>
<video id="cam" autoplay playsinline muted></video>
<canvas id="canvas"></canvas>

<div class="row" style="margin-top:4px">
  <label>FPS: <input id="fps" type="range" min="1" max="30" value="10"
    oninput="document.getElementById('fpsVal').textContent=this.value;setRate(+this.value)">
  <span id="fpsVal">10</span></label>
  <label style="margin-left:16px">Quality: <input id="qual" type="range" min="20" max="95" value="75"
    oninput="document.getElementById('qualVal').textContent=this.value">
  <span id="qualVal">75</span></label>
</div>
<p class="meta" id="info">Topic: /camera/image_raw &nbsp;|&nbsp; Port: __WS_PORT__</p>

<script>
var ws = null;
var streaming = false;
var camStream = null;
var intervalId = null;
var sentFrames = 0;

function log(m){console.log(m);}
function setStatus(m, streaming){
  document.getElementById('status').innerHTML =
    '<span id="indicator"'+(streaming?' class="on"':'')+' ></span>'+m;
}
function show(id){document.getElementById(id).style.display='';}
function hide(id){document.getElementById(id).style.display='none';}
function enable(id){document.getElementById(id).disabled=false;}
function disable(id){document.getElementById(id).disabled=true;}

function doConnect(){
  disable('connectBtn');
  setStatus('Connecting…', false);

  navigator.mediaDevices.getUserMedia({video:{width:{ideal:640},height:{ideal:480}}})
  .then(function(stream){
    camStream = stream;
    var v = document.getElementById('cam');
    v.srcObject = stream;
    var track = stream.getVideoTracks()[0];
    var settings = track.getSettings();
    document.getElementById('info').textContent =
      'Topic: /camera/image_raw  |  Port: __WS_PORT__  |  Camera: '
      + (settings.width||'?') + 'x' + (settings.height||'?');
    return new Promise(function(ok){ v.onloadedmetadata = ok; });
  })
  .then(function(){
    ws = new WebSocket('ws://'+location.hostname+':__WS_PORT__');
    ws.binaryType = 'arraybuffer';
    ws.onopen = function(){
      setStatus('Connected — click Start Streaming.', false);
      hide('connectBtn');
      show('startBtn');
      show('discBtn');
    };
    ws.onclose = function(){
      stopStream();
      setStatus('Disconnected.', false);
      show('connectBtn');
      enable('connectBtn');
      hide('startBtn');
      hide('discBtn');
    };
    ws.onerror = function(){ setStatus('WebSocket error — is port __WS_PORT__ reachable?', false); enable('connectBtn'); };
  })
  .catch(function(e){
    setStatus('Camera error: '+e.message, false);
    enable('connectBtn');
  });
}

function setRate(fps){
  if(intervalId){ clearInterval(intervalId); intervalId = null; }
  if(streaming){ intervalId = setInterval(sendFrame, 1000/fps); }
}

function sendFrame(){
  if(!ws || ws.readyState !== 1 || !camStream) return;
  var v = document.getElementById('cam');
  var c = document.getElementById('canvas');
  if(!v.videoWidth) return;
  c.width = v.videoWidth; c.height = v.videoHeight;
  c.getContext('2d').drawImage(v, 0, 0);
  var qual = parseFloat(document.getElementById('qual').value)/100;
  c.toBlob(function(blob){
    if(!blob) return;
    blob.arrayBuffer().then(function(buf){
      if(ws && ws.readyState === 1) ws.send(buf);
      sentFrames++;
    });
  }, 'image/jpeg', qual);
}

function toggleStream(){
  streaming = !streaming;
  var btn = document.getElementById('startBtn');
  if(streaming){
    btn.textContent = '⏸ Stop Streaming';
    btn.className = 'btn btn-active';
    setStatus('Streaming to /camera/image_raw…', true);
    var fps = +document.getElementById('fps').value;
    intervalId = setInterval(sendFrame, 1000/fps);
  } else {
    stopStream();
    setStatus('Paused — click Start Streaming to resume.', false);
  }
}

function stopStream(){
  streaming = false;
  if(intervalId){ clearInterval(intervalId); intervalId = null; }
  var btn = document.getElementById('startBtn');
  if(btn){ btn.textContent = '▶ Start Streaming'; btn.className = 'btn'; }
}

function doDisconnect(){
  stopStream();
  if(camStream){ camStream.getTracks().forEach(function(t){t.stop();}); camStream=null; }
  if(ws){ ws.close(); ws=null; }
}
</script>
</body>
</html>
"""


class CamBridgeNode(Node):

    def __init__(self):
        super().__init__("cam_bridge_node")

        self.declare_parameter("http_port", 8891)
        self.declare_parameter("ws_port", 8892)
        self.declare_parameter("image_topic", "/camera/image_raw")
        self.declare_parameter("frame_id", "camera_link")

        http_port   = int(self.get_parameter("http_port").value)
        ws_port     = int(self.get_parameter("ws_port").value)
        image_topic = self.get_parameter("image_topic").value
        self._frame_id = self.get_parameter("frame_id").value

        self._bridge = CvBridge()
        self._img_pub  = self.create_publisher(Image, image_topic, qos_profile_sensor_data)
        self._info_pub = self.create_publisher(CameraInfo, "/camera/camera_info", qos_profile_sensor_data)

        self._width = 0
        self._height = 0

        self._html = _HTML.replace("__WS_PORT__", str(ws_port)).encode("utf-8")

        threading.Thread(target=self._run_http, args=(http_port,), daemon=True).start()
        threading.Thread(target=self._run_ws, args=(ws_port,), daemon=True).start()

        self.get_logger().info(
            f"cam_bridge_node ready — open http://localhost:{http_port} in your host browser\n"
            f"  publishes → {image_topic} + /camera/camera_info"
        )

    # ------------------------------------------------------------------
    # Frame processing
    # ------------------------------------------------------------------

    def _on_frame(self, data: bytes) -> None:
        """Decode one JPEG frame from the browser and publish it."""
        arr = np.frombuffer(data, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            return

        h, w = frame.shape[:2]
        now = self.get_clock().now().to_msg()

        img_msg = self._bridge.cv2_to_imgmsg(frame, encoding="bgr8")
        img_msg.header.stamp = now
        img_msg.header.frame_id = self._frame_id
        self._img_pub.publish(img_msg)

        # Rebuild camera_info only when resolution changes (or first frame).
        if w != self._width or h != self._height:
            self._width, self._height = w, h
            self._camera_info = self._make_camera_info(w, h)

        self._camera_info.header.stamp = now
        self._info_pub.publish(self._camera_info)

    def _make_camera_info(self, w: int, h: int) -> CameraInfo:
        """Identity calibration — adequate for detection/recognition, not for 3-D work."""
        msg = CameraInfo()
        msg.header.frame_id = self._frame_id
        msg.width = w
        msg.height = h
        msg.distortion_model = "plumb_bob"
        msg.d = [0.0, 0.0, 0.0, 0.0, 0.0]
        # Focal length guess: typical webcam FOV ≈ 70° → f ≈ w / (2 * tan(35°)) ≈ 0.71 * w
        f = 0.71 * w
        cx, cy = w / 2.0, h / 2.0
        msg.k = [f, 0.0, cx,
                 0.0, f,  cy,
                 0.0, 0.0, 1.0]
        msg.r = [1.0, 0.0, 0.0,
                 0.0, 1.0, 0.0,
                 0.0, 0.0, 1.0]
        msg.p = [f,   0.0, cx, 0.0,
                 0.0, f,   cy, 0.0,
                 0.0, 0.0, 1.0, 0.0]
        return msg

    # ------------------------------------------------------------------
    # HTTP server (serves the HTML page)
    # ------------------------------------------------------------------

    def _run_http(self, port: int) -> None:
        html = self._html

        class _Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html)))
                self.end_headers()
                self.wfile.write(html)

            def log_message(self, *_):
                pass

        http.server.ThreadingHTTPServer(("0.0.0.0", port), _Handler).serve_forever()

    # ------------------------------------------------------------------
    # WebSocket server (receives binary JPEG frames from the browser)
    # ------------------------------------------------------------------

    def _run_ws(self, port: int) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._ws_serve(port))

    async def _ws_serve(self, port: int) -> None:
        try:
            import websockets
        except ImportError:
            self.get_logger().error("websockets not installed — run: pip install websockets")
            return

        node = self

        async def _handler(websocket):
            node.get_logger().info(
                f"Browser camera connected from {getattr(websocket, 'remote_address', '?')}"
            )
            try:
                async for message in websocket:
                    if isinstance(message, (bytes, bytearray)) and message:
                        node._on_frame(bytes(message))
            except Exception:
                pass
            node.get_logger().info("Browser camera disconnected")

        async with websockets.serve(_handler, "0.0.0.0", port):
            self.get_logger().info(f"CamBridge WebSocket on port {port}")
            await asyncio.Future()


def main(args=None):
    rclpy.init(args=args)
    node = CamBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
