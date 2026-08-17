#!/usr/bin/env python3

# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

"""
mic_diagnostic_node — on-robot web UI to record and play back /robot_audio.

Serves a small HTML page (http://<jetson-ip>:8893) with Record/Stop buttons,
a live level meter, a waveform, and native audio playback -- so anyone on
the same network can capture what the robot's onboard mic is actually
picking up and listen to it directly, without going through SSH.

Purely observational: subscribes to /robot_audio (the same topic stt_node
consumes) and only buffers while a capture is active. Doesn't touch the VAD,
doesn't publish anything -- can't interfere with the STT pipeline.

Publications: none.
Subscriptions:
  /robot_audio (std_msgs/UInt8MultiArray) -- mono s16 PCM @ sample_rate

Parameters (env-var defaults wired in robot.launch.py):
  http_port      (int,   default 8893)
  ws_port        (int,   default 8894)
  audio_topic    (str,   default /robot_audio)
  sample_rate    (int,   default 16000)
  max_capture_s  (float, default 60.0) -- auto-stop safety cap
"""

import asyncio
import http.server
import json
import math
import struct
import threading
import time
import wave
import io

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from std_msgs.msg import UInt8MultiArray

# ---------------------------------------------------------------------------
# HTML page
# ---------------------------------------------------------------------------

_HTML = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Mic Diagnostic — GO2 Robot</title>
<style>
:root{
  --bg:#12141a; --surface:#1a1d26; --surface-2:#20242e; --border:#2c303c;
  --text:#edeff4; --text-dim:#939aad; --accent:#d9a441; --accent-strong:#f0b859;
  --signal:#6fd3c0; --danger:#e2793d;
}
*{box-sizing:border-box}
body{
  background:var(--bg); color:var(--text); margin:0; padding:40px 20px 60px;
  font-family:-apple-system,"Segoe UI",system-ui,sans-serif; font-size:15px; line-height:1.6;
}
.page{max-width:640px;margin:0 auto;display:flex;flex-direction:column;gap:24px}
.mono{font-family:ui-monospace,"SF Mono","Cascadia Code","Roboto Mono",Consolas,monospace}
.eyebrow{font-family:ui-monospace,"SF Mono","Cascadia Code",monospace;font-size:11px;letter-spacing:.09em;text-transform:uppercase;color:var(--text-dim)}
h1{font-family:ui-monospace,"SF Mono","Cascadia Code",monospace;font-size:26px;font-weight:600;margin:6px 0 0}
p.sub{color:var(--text-dim);margin:10px 0 0;font-size:14px}
section{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:22px}
.controls{display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.btn{
  padding:11px 22px;font-size:14px;font-weight:600;cursor:pointer;border-radius:8px;
  border:1px solid var(--border);background:var(--surface-2);color:var(--text);
  font-family:inherit;transition:filter .15s;
}
.btn:hover{filter:brightness(1.15)}
.btn:disabled{opacity:.4;cursor:not-allowed}
.btn-record{background:var(--accent);border-color:var(--accent);color:#1a1408}
.btn-stop{background:var(--danger);border-color:var(--danger);color:#1a1408}
#status{font-family:ui-monospace,"SF Mono","Cascadia Code",monospace;font-size:13px;color:var(--text-dim)}
#status.live{color:var(--danger)}

.meter-wrap{flex:1;min-width:140px;height:14px;background:var(--surface-2);border:1px solid var(--border);border-radius:7px;overflow:hidden}
#meter{height:100%;width:0%;background:linear-gradient(90deg,var(--signal),var(--accent-strong));transition:width .08s linear}

.waveform-wrap{background:var(--surface-2);border:1px solid var(--border);border-radius:8px;padding:12px;margin-top:18px}
canvas#wave{display:block;width:100%;height:110px}
audio{width:100%;margin-top:14px;accent-color:var(--accent)}

.stats-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:16px}
.stat{display:flex;flex-direction:column;gap:3px}
.stat-label{font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:var(--text-dim)}
.stat-value{font-family:ui-monospace,"SF Mono","Cascadia Code",monospace;font-size:22px;font-weight:600;color:var(--accent-strong);font-variant-numeric:tabular-nums}

.footer-row{display:flex;justify-content:space-between;align-items:center;margin-top:16px}
a.dl{color:var(--signal);font-size:13px;text-decoration:none;font-family:ui-monospace,"SF Mono","Cascadia Code",monospace}
a.dl:hover{text-decoration:underline}
a.dl[aria-disabled="true"]{color:var(--text-dim);pointer-events:none}
.hint{font-size:12.5px;color:var(--text-dim);margin-top:4px}
.empty{color:var(--text-dim);font-size:13.5px;padding:24px 0;text-align:center}
</style>
</head>
<body>
<div class="page">
  <div>
    <div class="eyebrow">go2_ros2_sdk &middot; speech_processor &middot; mic diagnostic</div>
    <h1>Robot Mic Capture</h1>
    <p class="sub">Records __AUDIO_TOPIC__ live from the robot's onboard mic and plays it back
    right here — no SSH needed. Max __MAX_CAPTURE__s per capture.</p>
  </div>

  <section>
    <div class="controls">
      <button id="recordBtn" class="btn btn-record" onclick="startCapture()">&#9679; Record</button>
      <button id="stopBtn" class="btn btn-stop" onclick="stopCapture()" disabled>&#9632; Stop</button>
      <div class="meter-wrap"><div id="meter"></div></div>
    </div>
    <p id="status">Not connected.</p>
  </section>

  <section id="resultSection" style="display:none">
    <div class="waveform-wrap">
      <canvas id="wave" width="1200" height="220"></canvas>
    </div>
    <audio id="player" controls preload="none"></audio>
    <div class="stats-grid">
      <div class="stat"><span class="stat-label">Duration</span><span class="stat-value" id="statDur">—</span></div>
      <div class="stat"><span class="stat-label">Peak</span><span class="stat-value" id="statPeak">—</span></div>
      <div class="stat"><span class="stat-label">Mean RMS</span><span class="stat-value" id="statRms">—</span></div>
    </div>
    <div class="footer-row">
      <a id="dlLink" class="dl" aria-disabled="true">&#8681; Download WAV</a>
      <span class="hint mono" id="topicInfo"></span>
    </div>
  </section>

  <section id="emptyState">
    <p class="empty">No capture yet — click Record, speak near the robot, click Stop.</p>
  </section>
</div>

<script>
var ws = null;
var recording = false;
var lastWavBlobUrl = null;

function setStatus(msg, live){
  var el = document.getElementById('status');
  el.textContent = msg;
  el.className = live ? 'live' : '';
}

function connect(){
  ws = new WebSocket('ws://' + location.hostname + ':__WS_PORT__');
  ws.binaryType = 'arraybuffer';
  ws.onopen = function(){ setStatus('Connected — ready to record.', false); };
  ws.onclose = function(){ setStatus('Disconnected — reload the page to reconnect.', false); recording=false; updateButtons(); };
  ws.onerror = function(){ setStatus('WebSocket error — is port __WS_PORT__ reachable?', false); };

  var pendingMeta = null;
  ws.onmessage = function(evt){
    if (typeof evt.data === 'string') {
      var msg = JSON.parse(evt.data);
      if (msg.type === 'level') {
        document.getElementById('meter').style.width = Math.min(100, msg.pct) + '%';
        setStatus('Recording… ' + msg.elapsed.toFixed(1) + 's', true);
      } else if (msg.type === 'capture_started') {
        setStatus('Recording…', true);
      } else if (msg.type === 'capture_done') {
        pendingMeta = msg;
        document.getElementById('meter').style.width = '0%';
      } else if (msg.type === 'capture_empty') {
        setStatus('No audio captured — is /robot_audio publishing? (STT_SOURCE=robot required)', false);
        recording = false;
        updateButtons();
      }
    } else {
      // Binary WAV bytes immediately following a capture_done JSON message.
      onWavReceived(new Uint8Array(evt.data), pendingMeta);
      pendingMeta = null;
      recording = false;
      updateButtons();
    }
  };
}

function updateButtons(){
  document.getElementById('recordBtn').disabled = recording;
  document.getElementById('stopBtn').disabled = !recording;
}

function startCapture(){
  if (!ws || ws.readyState !== 1) { setStatus('Not connected.', false); return; }
  recording = true;
  updateButtons();
  ws.send(JSON.stringify({cmd: 'start'}));
}

function stopCapture(){
  if (!ws || ws.readyState !== 1) return;
  ws.send(JSON.stringify({cmd: 'stop'}));
  setStatus('Finishing…', false);
}

function onWavReceived(bytes, meta){
  if (!bytes || bytes.length < 44) return;

  document.getElementById('emptyState').style.display = 'none';
  document.getElementById('resultSection').style.display = '';

  var blob = new Blob([bytes], {type: 'audio/wav'});
  if (lastWavBlobUrl) URL.revokeObjectURL(lastWavBlobUrl);
  lastWavBlobUrl = URL.createObjectURL(blob);

  var player = document.getElementById('player');
  player.src = lastWavBlobUrl;

  var dl = document.getElementById('dlLink');
  dl.href = lastWavBlobUrl;
  dl.download = 'robot_mic_capture_' + Date.now() + '.wav';
  dl.removeAttribute('aria-disabled');

  // Parse PCM samples directly from the WAV bytes (44-byte header, s16 mono).
  var dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  var n = (bytes.length - 44) / 2;
  var samples = new Int16Array(n);
  for (var i = 0; i < n; i++) samples[i] = dv.getInt16(44 + i * 2, true);

  var peak = 0, sumSq = 0;
  for (var i = 0; i < n; i++) {
    var v = Math.abs(samples[i]);
    if (v > peak) peak = v;
    sumSq += samples[i] * samples[i];
  }
  var rms = n ? Math.sqrt(sumSq / n) : 0;
  var duration = meta ? meta.duration : (n / __SAMPLE_RATE__);

  document.getElementById('statDur').textContent = duration.toFixed(1) + 's';
  document.getElementById('statPeak').textContent = (peak / 32768 * 100).toFixed(1) + '%';
  document.getElementById('statRms').textContent = rms.toFixed(0);
  document.getElementById('topicInfo').textContent = '__AUDIO_TOPIC__ · __SAMPLE_RATE__ Hz mono s16';

  drawWaveform(samples);
  setStatus('Capture complete — ' + duration.toFixed(1) + 's.', false);
}

function drawWaveform(samples){
  var canvas = document.getElementById('wave');
  var ctx = canvas.getContext('2d');
  var w = canvas.clientWidth, h = canvas.clientHeight;
  var dpr = window.devicePixelRatio || 1;
  canvas.width = w * dpr; canvas.height = h * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);

  var mid = h / 2;
  var cols = Math.min(400, samples.length || 1);
  var colSize = Math.max(1, Math.floor(samples.length / cols));
  var barW = w / cols;

  ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue('--border').trim();
  ctx.beginPath(); ctx.moveTo(0, mid); ctx.lineTo(w, mid); ctx.stroke();

  ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--signal').trim();
  for (var c = 0; c < cols; c++) {
    var lo = 32767, hi = -32768;
    var start = c * colSize;
    for (var i = start; i < start + colSize && i < samples.length; i++) {
      if (samples[i] < lo) lo = samples[i];
      if (samples[i] > hi) hi = samples[i];
    }
    var y1 = mid - (hi / 32768) * mid * 0.92;
    var y2 = mid - (lo / 32768) * mid * 0.92;
    ctx.fillRect(c * barW, y1, Math.max(1, barW - 1), Math.max(1, y2 - y1));
  }
}

connect();
</script>
</body>
</html>
"""


class MicDiagnosticNode(Node):

    def __init__(self):
        super().__init__("mic_diagnostic_node")

        self.declare_parameter("http_port", 8893)
        self.declare_parameter("ws_port", 8894)
        self.declare_parameter("audio_topic", "/robot_audio")
        self.declare_parameter("sample_rate", 16000)
        self.declare_parameter("max_capture_s", 60.0)

        http_port = int(self.get_parameter("http_port").value)
        ws_port = int(self.get_parameter("ws_port").value)
        audio_topic = self.get_parameter("audio_topic").value
        self._rate = int(self.get_parameter("sample_rate").value)
        self._max_capture_s = float(self.get_parameter("max_capture_s").value)

        self._html = (
            _HTML.replace("__WS_PORT__", str(ws_port))
            .replace("__AUDIO_TOPIC__", audio_topic)
            .replace("__SAMPLE_RATE__", str(self._rate))
            .replace("__MAX_CAPTURE__", str(int(self._max_capture_s)))
            .encode("utf-8")
        )

        self._recording = False
        self._buffer = bytearray()
        self._record_start = 0.0
        self._last_level_sent = 0.0

        self._ws_loop: asyncio.AbstractEventLoop | None = None
        self._ws_clients: set = set()

        self.create_subscription(
            UInt8MultiArray, audio_topic, self._on_robot_audio, qos_profile_sensor_data
        )

        threading.Thread(target=self._run_http, args=(http_port,), daemon=True).start()
        threading.Thread(target=self._run_ws, args=(ws_port,), daemon=True).start()

        self.get_logger().info(
            f"mic_diagnostic_node ready — open http://localhost:{http_port} in your browser\n"
            f"  records → {audio_topic} (@ {self._rate} Hz), max {self._max_capture_s:.0f}s per capture"
        )

    # ------------------------------------------------------------------
    # Audio capture (passive -- only buffers while a capture is active)
    # ------------------------------------------------------------------

    def _on_robot_audio(self, msg: UInt8MultiArray) -> None:
        if not self._recording:
            return

        data = bytes(msg.data)
        self._buffer.extend(data)

        now = time.monotonic()
        elapsed = now - self._record_start

        if elapsed >= self._max_capture_s:
            self.get_logger().info(f"Capture hit max_capture_s={self._max_capture_s:.0f}s, auto-stopping")
            self._finish_capture()
            return

        # Throttle level updates to ~8/s regardless of audio message rate.
        if now - self._last_level_sent >= 0.125 and len(data) >= 2:
            self._last_level_sent = now
            n = len(data) // 2
            samples = struct.unpack(f"<{n}h", data[: n * 2])
            peak = max(abs(s) for s in samples) if samples else 0
            pct = min(100.0, peak / 32768.0 * 100.0 * 3.0)  # visually scaled, not a calibrated meter
            self._ws_broadcast_json({"type": "level", "pct": pct, "elapsed": elapsed})

    def _start_capture(self) -> None:
        self._buffer = bytearray()
        self._record_start = time.monotonic()
        self._last_level_sent = 0.0
        self._recording = True
        self._ws_broadcast_json({"type": "capture_started"})

    def _finish_capture(self) -> None:
        self._recording = False
        pcm = bytes(self._buffer)
        self._buffer = bytearray()

        if not pcm:
            self.get_logger().warn("Capture stopped with zero audio buffered")
            self._ws_broadcast_json({"type": "capture_empty"})
            return

        duration = len(pcm) / 2 / self._rate
        wav_buf = io.BytesIO()
        with wave.open(wav_buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self._rate)
            wf.writeframes(pcm)
        wav_bytes = wav_buf.getvalue()

        n = len(pcm) // 2
        samples = struct.unpack(f"<{n}h", pcm)
        peak = max(abs(s) for s in samples) if samples else 0
        rms = math.sqrt(sum(s * s for s in samples) / n) if n else 0.0

        self.get_logger().info(
            f"Capture done: {duration:.1f}s, {len(pcm)} bytes, "
            f"peak={peak/32768*100:.1f}%, rms={rms:.0f}"
        )
        self._ws_broadcast_json({
            "type": "capture_done",
            "duration": duration,
            "peak_pct": round(peak / 32768 * 100, 2),
            "rms": round(rms, 1),
        })
        self._ws_broadcast_bytes(wav_bytes)

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

        server = http.server.ThreadingHTTPServer(("0.0.0.0", port), _Handler)
        self.get_logger().info(f"MicDiagnostic HTTP on port {port}")
        server.serve_forever()

    # ------------------------------------------------------------------
    # WebSocket server (control messages in, level/WAV data out)
    # ------------------------------------------------------------------

    def _run_ws(self, port: int) -> None:
        loop = asyncio.new_event_loop()
        self._ws_loop = loop
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
                f"Mic diagnostic client connected from {getattr(websocket, 'remote_address', '?')}"
            )
            node._ws_clients.add(websocket)
            try:
                async for message in websocket:
                    if not isinstance(message, str):
                        continue
                    try:
                        cmd = json.loads(message).get("cmd")
                    except Exception:
                        continue
                    if cmd == "start" and not node._recording:
                        node._start_capture()
                    elif cmd == "stop" and node._recording:
                        node._finish_capture()
            except Exception:
                pass
            finally:
                node._ws_clients.discard(websocket)
            node.get_logger().info("Mic diagnostic client disconnected")

        async with websockets.serve(_handler, "0.0.0.0", port):
            self.get_logger().info(f"MicDiagnostic WebSocket on port {port}")
            await asyncio.Future()

    def _ws_broadcast_json(self, data: dict) -> None:
        if not self._ws_clients or self._ws_loop is None:
            return

        async def _send():
            payload = json.dumps(data)
            for ws in list(self._ws_clients):
                try:
                    await ws.send(payload)
                except Exception:
                    pass

        asyncio.run_coroutine_threadsafe(_send(), self._ws_loop)

    def _ws_broadcast_bytes(self, data: bytes) -> None:
        if not self._ws_clients or self._ws_loop is None:
            return

        async def _send():
            for ws in list(self._ws_clients):
                try:
                    await ws.send(data)
                except Exception:
                    pass

        asyncio.run_coroutine_threadsafe(_send(), self._ws_loop)


def main(args=None):
    rclpy.init(args=args)
    node = MicDiagnosticNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
