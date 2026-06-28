#!/usr/bin/env python3

# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

"""
face_enrollment_node — Browser-based face enrollment + threshold tuning (Modul 4.2).

Serves a small web page on http://localhost:8890 — the same host as the command
path (mic_bridge on 8888), a different page. It is the management surface for the
face pipeline and needs no ML model of its own:

  * **Enroll** — capture from the webcam or upload a photo, type a name, and the
    node writes the JPEG into ``face_db/<Name>/`` (the directory shared with
    face_recognition_node and bind-mounted to the host), then publishes
    ``/reload_faces`` so the recognizer re-embeds it. No live capture on the robot.
  * **Threshold tuning** — a slider publishes ``/face_threshold`` (std_msgs/Float32);
    face_recognition_node applies it live. The page polls the latest
    ``/recognized_faces`` so you can watch similarities and pick a value.

Publications:
  /reload_faces    (std_msgs/Empty)   — re-scan + re-embed face_db after an enroll
  /face_threshold  (std_msgs/Float32) — new cosine-similarity match floor

Subscriptions:
  /recognized_faces (vision_msgs/Detection2DArray) — for the live tuning table

Parameters:
  http_port          (int,   default 8890)
  face_db_path       (str,   default ./face_db — must match face_recognition_node)
  default_threshold  (float, default 0.35 — initial slider position)
"""

import base64
import http.server
import json
import re
import threading
from pathlib import Path

import rclpy
from rclpy.node import Node
from std_msgs.msg import Empty, Float32
from vision_msgs.msg import Detection2DArray

# Folder names come from web input — allow only a safe subset (no path traversal).
_SAFE_NAME = re.compile(r"[^A-Za-z0-9 _-]")

_HTML = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Face Enrollment — GO2 Robot</title>
<style>
*{box-sizing:border-box}
body{font-family:sans-serif;max-width:720px;margin:36px auto;padding:0 20px;color:#222}
h2{margin:0 0 4px}h3{margin:26px 0 8px}
p.sub{color:#555;margin:6px 0 18px;font-size:14px}
.card{border:1px solid #e3e3e3;border-radius:10px;padding:18px;margin:14px 0;background:#fcfcfc}
.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.btn{padding:9px 18px;font-size:14px;cursor:pointer;border-radius:6px;border:1px solid #aaa;background:#f3f3f3}
.btn:disabled{opacity:.45;cursor:not-allowed}
.btn-primary{background:#dbeafe;border-color:#60a5fa}
.btn-active{background:#dcfce7;border-color:#4ade80;font-weight:bold}
input[type=text]{padding:9px 12px;font-size:14px;border-radius:6px;border:1px solid #aaa;min-width:220px}
video,canvas,#preview{width:280px;height:210px;background:#111;border-radius:8px;object-fit:cover}
#preview{object-fit:contain;background:#f0f0f0}
#status{margin:12px 0 0;font-weight:bold;min-height:1.3em}
table{border-collapse:collapse;width:100%;font-size:14px;margin-top:8px}
th,td{text-align:left;padding:5px 8px;border-bottom:1px solid #eee}
.pill{display:inline-block;padding:1px 8px;border-radius:10px;font-size:12px;font-weight:bold}
.known{background:#dcfce7;color:#166534}.unknown{background:#f1f5f9;color:#64748b}
#thrVal{font-variant-numeric:tabular-nums;font-weight:bold}
small.note{color:#888}
</style>
</head>
<body>
<h2>Face Enrollment — GO2 Robot</h2>
<p class="sub">Add people to the recognition database and tune the match threshold.
Enrolled photos land in <code>face_db/&lt;Name&gt;/</code> and the recognizer reloads automatically.</p>

<div class="card">
  <h3>1 · Enroll a person</h3>
  <div class="row">
    <input id="name" type="text" placeholder="Person name (e.g. Dito)">
  </div>
  <div class="row" style="margin-top:12px">
    <video id="cam" autoplay playsinline muted></video>
    <img id="preview" alt="preview">
  </div>
  <div class="row" style="margin-top:10px">
    <button id="camBtn"     class="btn"         onclick="startCam()">&#128247; Start camera</button>
    <button id="capBtn"     class="btn btn-primary" onclick="capture()" disabled>&#128248; Capture</button>
    <label class="btn" style="margin:0">&#128193; Upload photo
      <input id="file" type="file" accept="image/*" style="display:none" onchange="loadFile(event)">
    </label>
    <button id="enrollBtn"  class="btn btn-active" onclick="enroll()" disabled>&#10003; Enroll</button>
  </div>
  <p id="status">Ready.</p>
  <canvas id="canvas" width="640" height="480" style="display:none"></canvas>
</div>

<div class="card">
  <h3>2 · Tune match threshold</h3>
  <p class="sub" style="margin:0 0 10px">Higher = stricter (fewer false matches); lower = more lenient.
  Stand a known person in front of the robot and adjust until they match reliably while strangers stay
  <span class="pill unknown">Unknown</span>.</p>
  <div class="row">
    <input id="thr" type="range" min="0" max="1" step="0.01" value="__DEFAULT_THRESHOLD__"
           oninput="document.getElementById('thrVal').textContent=(+this.value).toFixed(2)" style="flex:1;min-width:240px">
    <span id="thrVal">__DEFAULT_THRESHOLD__</span>
    <button class="btn btn-primary" onclick="applyThreshold()">Apply</button>
  </div>
  <table id="facesTbl"><thead><tr><th>Recognized now</th><th>Similarity</th></tr></thead>
    <tbody id="facesBody"><tr><td colspan="2"><small class="note">waiting for /recognized_faces…</small></td></tr></tbody>
  </table>
</div>

<script>
var imageData = null;   // data URL of the photo to enroll

function setStatus(m){ document.getElementById('status').textContent = m; }

function startCam(){
  navigator.mediaDevices.getUserMedia({video:{width:640,height:480}}).then(function(s){
    var v=document.getElementById('cam'); v.srcObject=s;
    document.getElementById('capBtn').disabled=false;
    setStatus('Camera on — frame the face and Capture.');
  }).catch(function(e){ setStatus('Camera error: '+e.message); });
}

function capture(){
  var v=document.getElementById('cam'), c=document.getElementById('canvas');
  c.getContext('2d').drawImage(v,0,0,c.width,c.height);
  imageData=c.toDataURL('image/jpeg',0.9);
  showPreview();
}

function loadFile(ev){
  var f=ev.target.files[0]; if(!f) return;
  var r=new FileReader();
  r.onload=function(){ imageData=r.result; showPreview(); };
  r.readAsDataURL(f);
}

function showPreview(){
  document.getElementById('preview').src=imageData;
  document.getElementById('enrollBtn').disabled=false;
  setStatus('Photo ready — type a name and Enroll.');
}

function enroll(){
  var name=document.getElementById('name').value.trim();
  if(!name){ setStatus('Please enter a name.'); return; }
  if(!imageData){ setStatus('Capture or upload a photo first.'); return; }
  setStatus('Enrolling…');
  fetch('/api/enroll',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({name:name,image:imageData})})
   .then(function(r){return r.json();})
   .then(function(j){
     if(j.ok){ setStatus('✓ Enrolled "'+j.name+'" (photo #'+j.index+'). Recognizer reloading…'); }
     else{ setStatus('❌ '+(j.error||'enroll failed')); }
   }).catch(function(e){ setStatus('❌ '+e); });
}

function applyThreshold(){
  var t=parseFloat(document.getElementById('thr').value);
  fetch('/api/threshold',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({threshold:t})})
   .then(function(r){return r.json();})
   .then(function(j){ setStatus(j.ok?('Threshold set to '+j.threshold.toFixed(2)):'❌ '+(j.error||'')); });
}

function refreshFaces(){
  fetch('/api/recognized').then(function(r){return r.json();}).then(function(j){
    var thr=parseFloat(document.getElementById('thr').value);
    var b=document.getElementById('facesBody');
    if(!j.faces||!j.faces.length){
      b.innerHTML='<tr><td colspan="2"><small class="note">no faces in view</small></td></tr>'; return;
    }
    b.innerHTML=j.faces.map(function(f){
      var known=f.name && f.name!=='Unknown';
      var cls=known?'known':'unknown';
      return '<tr><td><span class="pill '+cls+'">'+(f.name||'Unknown')+'</span></td>'
           + '<td>'+f.score.toFixed(3)+'</td></tr>';
    }).join('');
  }).catch(function(){});
}
setInterval(refreshFaces,1000);
</script>
</body>
</html>
"""


class FaceEnrollmentNode(Node):

    def __init__(self):
        super().__init__("face_enrollment_node")

        self.declare_parameter("http_port", 8890)
        self.declare_parameter("face_db_path", "./face_db")
        self.declare_parameter("default_threshold", 0.35)

        port = int(self.get_parameter("http_port").value)
        self._db_path = Path(self.get_parameter("face_db_path").value)
        threshold = float(self.get_parameter("default_threshold").value)

        self._reload_pub = self.create_publisher(Empty, "/reload_faces", 10)
        self._thresh_pub = self.create_publisher(Float32, "/face_threshold", 10)

        self._faces_lock = threading.Lock()
        self._latest_faces = []  # list[(name, score)]
        self.create_subscription(Detection2DArray, "/recognized_faces", self._on_faces, 10)

        self._html = _HTML.replace("__DEFAULT_THRESHOLD__", f"{threshold:.2f}").encode("utf-8")

        threading.Thread(target=self._run_http_server, args=(port,), daemon=True).start()
        self.get_logger().info(
            f"face_enrollment_node ready — open http://localhost:{port} in your host browser "
            f"(DB: {self._db_path})"
        )

    # ------------------------------------------------------------------
    # ROS callbacks / helpers
    # ------------------------------------------------------------------

    def _on_faces(self, msg: Detection2DArray) -> None:
        faces = []
        for det in msg.detections:
            if det.results:
                hyp = det.results[0].hypothesis
                faces.append((hyp.class_id, float(hyp.score)))
        with self._faces_lock:
            self._latest_faces = faces

    def _save_image(self, name: str, data: bytes) -> int:
        """Write a JPEG into face_db/<name>/ and return its index."""
        person = self._db_path / name
        person.mkdir(parents=True, exist_ok=True)
        idx = len(list(person.glob("*.jpg")))
        (person / f"{idx:04d}.jpg").write_bytes(data)
        return idx

    @staticmethod
    def _sanitize(name: str) -> str:
        return _SAFE_NAME.sub("", name or "").strip()

    # ------------------------------------------------------------------
    # HTTP server (enroll + threshold + live recognized faces)
    # ------------------------------------------------------------------

    def _run_http_server(self, port: int) -> None:
        node = self

        class _Handler(http.server.BaseHTTPRequestHandler):
            def _json(self, code, obj):
                body = json.dumps(obj).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.path in ("/", "/index.html"):
                    html = node._html
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(html)))
                    self.end_headers()
                    self.wfile.write(html)
                elif self.path == "/api/recognized":
                    with node._faces_lock:
                        faces = [{"name": n, "score": s} for n, s in node._latest_faces]
                    self._json(200, {"faces": faces})
                else:
                    self._json(404, {"error": "not found"})

            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0") or "0")
                raw = self.rfile.read(length) if length else b"{}"
                try:
                    payload = json.loads(raw)
                except Exception:
                    return self._json(400, {"error": "bad json"})

                if self.path == "/api/enroll":
                    name = node._sanitize(payload.get("name", ""))
                    if not name:
                        return self._json(400, {"error": "invalid name"})
                    img = payload.get("image", "")
                    try:
                        b64 = img.split(",", 1)[1] if "," in img else img
                        data = base64.b64decode(b64)
                    except Exception:
                        return self._json(400, {"error": "bad image data"})
                    if not data:
                        return self._json(400, {"error": "empty image"})
                    idx = node._save_image(name, data)
                    node._reload_pub.publish(Empty())
                    node.get_logger().info(
                        f"Enrolled photo for {name!r} (#{idx}) → triggered /reload_faces"
                    )
                    return self._json(200, {"ok": True, "name": name, "index": idx})

                if self.path == "/api/threshold":
                    try:
                        thr = max(0.0, min(1.0, float(payload.get("threshold"))))
                    except Exception:
                        return self._json(400, {"error": "bad threshold"})
                    node._thresh_pub.publish(Float32(data=thr))
                    node.get_logger().info(f"Published /face_threshold = {thr:.2f}")
                    return self._json(200, {"ok": True, "threshold": thr})

                return self._json(404, {"error": "not found"})

            def log_message(self, *_):
                pass

        server = http.server.ThreadingHTTPServer(("0.0.0.0", port), _Handler)
        self.get_logger().info(f"face_enrollment HTTP on port {port}")
        server.serve_forever()


def main(args=None):
    rclpy.init(args=args)
    node = FaceEnrollmentNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
