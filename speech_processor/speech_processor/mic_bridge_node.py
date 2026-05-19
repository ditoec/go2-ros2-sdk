#!/usr/bin/env python3

# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

"""
mic_bridge_node — Browser-based microphone input for the GO2 robot.

Serves an HTML page on http://localhost:8888.  The page has two phases:
  1. Connect — opens the WebSocket and requests microphone permission.
  2. Start/Stop Talking — toggle to control when audio is relayed.

Raw Int16 PCM at 16 kHz mono is streamed to the container only while the user
is actively talking.  VAD silence threshold is derived dynamically from the
actual WebSocket frame size, not a fixed millisecond parameter.

Same STT pipeline as stt_node; publishes transcriptions to /speech_text and
echoes them back to the browser tab.

Enabled by default when ENABLE_STT=true.  Replaces stt_node (which requires
system audio that is often unavailable in Docker on Windows 11).
"""

import asyncio
import base64
import http.server
import io
import queue
import struct
import threading

import numpy as np
import requests
import rclpy
from rclpy.node import Node
from std_msgs.msg import String, UInt8MultiArray


# ---------------------------------------------------------------------------
# HTML page — served to the host browser on http_port
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Mic Bridge — GO2 Robot</title>
<style>
*{{box-sizing:border-box}}
body{{font-family:sans-serif;max-width:640px;margin:48px auto;padding:0 20px;color:#222}}
h2{{margin-bottom:4px}}
p.sub{{color:#555;margin:6px 0 24px;font-size:14px}}
.row{{display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
.btn{{padding:10px 22px;font-size:14px;cursor:pointer;border-radius:6px;
      border:1px solid #aaa;background:#f3f3f3;white-space:nowrap}}
.btn:disabled{{opacity:.45;cursor:not-allowed}}
.btn-primary{{background:#dbeafe;border-color:#60a5fa}}
.btn-active{{background:#dcfce7;border-color:#4ade80;font-weight:bold}}
.btn-danger{{background:#fee2e2;border-color:#f87171}}
#status{{margin:18px 0 6px;font-weight:bold;min-height:1.4em}}
#indicator{{display:inline-block;width:10px;height:10px;border-radius:50%;
            background:#ccc;margin-right:6px;vertical-align:middle}}
#indicator.on{{background:#22c55e;box-shadow:0 0 6px #22c55e}}
#log{{font-family:monospace;font-size:12px;background:#f8f8f8;border-radius:6px;
      padding:10px;height:180px;overflow-y:auto;border:1px solid #e0e0e0}}
</style>
</head>
<body>
<h2>Mic Bridge — GO2 Robot</h2>
<p class="sub">Step 1: Connect to the container.<br>
Step 2: Toggle <em>Start Talking</em> to relay your microphone to the robot.<br>
Transcriptions publish to <code>/speech_text</code>.</p>

<div class="row">
  <button id="connectBtn" class="btn btn-primary" onclick="doConnect()">&#128268; Connect</button>
  <button id="talkBtn"    class="btn" onclick="toggleTalk()" style="display:none">&#127908; Start Talking</button>
  <button id="discBtn"    class="btn btn-danger" onclick="doDisconnect()" style="display:none">&#10006; Disconnect</button>
</div>

<p id="status"><span id="indicator"></span>Not connected.</p>
<div id="log"></div>

<script>
var ws, audioCtx, source, proc;
var streaming = false;

function log(m) {{
  var d = document.getElementById('log');
  d.innerHTML = new Date().toLocaleTimeString() + ' — ' + m + '<br>' + d.innerHTML;
}}
function setStatus(m) {{
  document.getElementById('status').innerHTML =
    '<span id="indicator"' + (streaming ? ' class="on"' : '') + '></span>' + m;
}}
function show(id) {{ document.getElementById(id).style.display = ''; }}
function hide(id) {{ document.getElementById(id).style.display = 'none'; }}
function enable(id) {{ document.getElementById(id).disabled = false; }}
function disable(id) {{ document.getElementById(id).disabled = true; }}

function doConnect() {{
  disable('connectBtn');
  setStatus('Connecting…');

  ws = new WebSocket('ws://' + location.hostname + ':{ws_port}');
  ws.binaryType = 'arraybuffer';

  ws.onopen = function() {{
    setStatus('Connected — requesting microphone permission…');
    navigator.mediaDevices.getUserMedia({{
      audio: {{channelCount: 1, echoCancellation: true, noiseSuppression: true}}
    }}).then(function(stream) {{
      audioCtx = new (window.AudioContext || window.webkitAudioContext)({{sampleRate: 16000}});
      source = audioCtx.createMediaStreamSource(stream);
      // 4096-sample buffer = 256 ms at 16 kHz — matches dynamic VAD on the server side
      proc = audioCtx.createScriptProcessor(4096, 1, 1);
      proc.onaudioprocess = function(e) {{
        if (!streaming || ws.readyState !== 1) return;
        var f = e.inputBuffer.getChannelData(0);
        var i16 = new Int16Array(f.length);
        for (var i = 0; i < f.length; i++) {{
          var s = f[i] < -1 ? -1 : f[i] > 1 ? 1 : f[i];
          i16[i] = s < 0 ? s * 32768 : s * 32767;
        }}
        ws.send(i16.buffer);
      }};
      // Connect to destination to keep the audio graph alive (required for ScriptProcessorNode)
      source.connect(proc);
      proc.connect(audioCtx.destination);

      hide('connectBtn');
      show('talkBtn');
      show('discBtn');
      setStatus('Ready — click “Start Talking” to begin.');
      log('Connected and microphone ready');
    }}).catch(function(err) {{
      setStatus('Microphone error: ' + err.message);
      log('getUserMedia error: ' + err);
      enable('connectBtn');
    }});
  }};

  ws.onmessage = function(e) {{
    if (typeof e.data === 'string') {{
      setStatus('\U0001f4ac ' + e.data);
      log('\U0001f4ac ' + e.data);
    }} else if (e.data instanceof ArrayBuffer && e.data.byteLength > 0) {{
      playMp3(e.data);
    }}
  }};

function playMp3(buffer) {{
  var ctx = new (window.AudioContext || window.webkitAudioContext)();
  ctx.decodeAudioData(buffer.slice(0), function(decoded) {{
    var src = ctx.createBufferSource();
    src.buffer = decoded;
    src.connect(ctx.destination);
    src.start(0);
    log('\U0001f50a TTS playing (' + decoded.duration.toFixed(1) + 's)');
  }}, function(err) {{
    log('Audio decode error: ' + err);
  }});
}}

  ws.onclose = function() {{
    streaming = false;
    setStatus('Disconnected.');
    log('Connection closed');
    show('connectBtn');
    enable('connectBtn');
    hide('talkBtn');
    hide('discBtn');
    var tb = document.getElementById('talkBtn');
    tb.textContent = ' \U0001f3a4 Start Talking';
    tb.className = 'btn';
    if (audioCtx) {{ audioCtx.close(); audioCtx = null; }}
  }};

  ws.onerror = function() {{
    setStatus('WebSocket error — is port {ws_port} reachable?');
    log('WebSocket error');
    enable('connectBtn');
  }};
}}

function toggleTalk() {{
  streaming = !streaming;
  var btn = document.getElementById('talkBtn');
  if (streaming) {{
    btn.textContent = '\U0001f534 Stop Talking';
    btn.className = 'btn btn-active';
    setStatus('<span id="indicator" class="on"></span>Streaming microphone to robot…');
    log('Started streaming');
  }} else {{
    btn.textContent = '\U0001f3a4 Start Talking';
    btn.className = 'btn';
    setStatus('Paused — click “Start Talking” to resume.');
    log('Stopped streaming');
  }}
}}

function doDisconnect() {{
  if (ws) ws.close();
}}
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# STT backends (duplicated from stt_node to avoid circular imports)
# ---------------------------------------------------------------------------

class _FasterWhisperBackend:
    def __init__(self, model_size: str, device: str, compute_type: str, language: str):
        from faster_whisper import WhisperModel
        self._model = WhisperModel(model_size, device=device, compute_type=compute_type)
        self._language = language

    def transcribe(self, audio_bytes: bytes, sample_rate: int) -> str:
        audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        segs, _ = self._model.transcribe(audio, language=self._language, beam_size=1)
        return " ".join(s.text for s in segs).strip()


class _OpenAIBackend:
    def __init__(self, api_key: str, language: str):
        import openai
        self._client = openai.OpenAI(api_key=api_key)
        self._language = language

    def transcribe(self, audio_bytes: bytes, sample_rate: int) -> str:
        import openai
        buf = io.BytesIO(audio_bytes)
        buf.name = "audio.wav"
        try:
            return self._client.audio.transcriptions.create(
                model="whisper-1", file=buf, language=self._language,
            ).text.strip()
        except openai.OpenAIError:
            return ""


class _GeminiBackend:
    def __init__(self, api_key: str, language: str):
        from google import genai
        self._client = genai.Client(api_key=api_key)
        self._language = language

    def transcribe(self, audio_bytes: bytes, sample_rate: int) -> str:
        import os
        import tempfile
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_bytes)
                path = f.name
            try:
                up = self._client.files.upload(path=path, config={"mime_type": "audio/wav"})
                r = self._client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[up, f"Transcribe. Language: {self._language}. Return transcript only."],
                )
                return r.text.strip() if r.text else ""
            finally:
                os.unlink(path)
        except Exception:
            return ""


class _GemmaLocalBackend:
    """Gemma 4 E4B audio transcription via a local llama.cpp sidecar.

    Uses the OpenAI-compatible /v1/chat/completions endpoint.  Audio is sent
    via the input_audio content part (llama.cpp ≥ b8766, PR #21421).
    """

    def __init__(self, llama_cpp_host: str, model: str, language: str):
        self._host = llama_cpp_host.rstrip("/")
        self._model = model
        self._language = language

    def transcribe(self, audio_bytes: bytes, sample_rate: int) -> str:
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        try:
            resp = requests.post(
                f"{self._host}/v1/chat/completions",
                json={
                    "model": self._model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a speech transcription assistant. "
                                "Transcribe the audio exactly as spoken. "
                                "The speaker uses either English or Bahasa Indonesia — "
                                "output the transcript in the exact same language as spoken. "
                                "Never translate to any other language. "
                                "Output only the raw transcript with no commentary, "
                                "explanation, or formatting."
                            ),
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "input_audio",
                                    "input_audio": {"data": audio_b64, "format": "wav"},
                                },
                            ],
                        },
                    ],
                    "stream": False,
                },
                timeout=120,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            return ""


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class MicBridgeNode(Node):

    def __init__(self):
        super().__init__("mic_bridge_node")

        self.declare_parameter("http_port", 8888)
        self.declare_parameter("ws_port", 8889)
        self.declare_parameter("stt_provider", "faster_whisper")
        self.declare_parameter("whisper_model", "base")
        self.declare_parameter("device", "cpu")
        self.declare_parameter("compute_type", "int8")
        self.declare_parameter("language", "en")
        self.declare_parameter("api_key", "")
        self.declare_parameter("llama_cpp_host", "http://llama_cpp:8080")
        self.declare_parameter("gemma_model", "gemma")
        self.declare_parameter("vad_threshold", 0.04)
        self.declare_parameter("silence_duration", 0.5)          # seconds of silence to end utterance
        self.declare_parameter("max_utterance_duration", 20.0)   # force-flush after this many seconds
        self.declare_parameter("sample_rate", 16000)

        http_port    = int(self.get_parameter("http_port").value)
        ws_port      = int(self.get_parameter("ws_port").value)
        provider     = self.get_parameter("stt_provider").value
        model_size   = self.get_parameter("whisper_model").value
        device       = self.get_parameter("device").value
        compute_type = self.get_parameter("compute_type").value
        language     = self.get_parameter("language").value
        api_key      = self.get_parameter("api_key").value
        llama_cpp_host = self.get_parameter("llama_cpp_host").value
        gemma_model    = self.get_parameter("gemma_model").value

        self._vad_thr   = float(self.get_parameter("vad_threshold").value)
        self._silence   = float(self.get_parameter("silence_duration").value)
        self._max_utt   = float(self.get_parameter("max_utterance_duration").value)
        self._rate      = int(self.get_parameter("sample_rate").value)

        self._pub = self.create_publisher(String, "/speech_text", 10)
        self._audio_queue: queue.Queue = queue.Queue()
        self._ws_loop: asyncio.AbstractEventLoop | None = None
        self._ws_clients: set = set()

        self.create_subscription(UInt8MultiArray, "/tts_audio", self._on_tts_audio, 10)

        self._backend = self._build_backend(
            provider, api_key, model_size, device, compute_type, language,
            llama_cpp_host, gemma_model,
        )
        self._html = _HTML_TEMPLATE.format(ws_port=ws_port).encode("utf-8")

        threading.Thread(target=self._process_loop, daemon=True).start()
        threading.Thread(target=self._run_http_server, args=(http_port,), daemon=True).start()
        threading.Thread(target=self._run_ws_server, args=(ws_port,), daemon=True).start()

        self.get_logger().info(
            f"mic_bridge_node ready — open http://localhost:{http_port} in your host browser"
        )

    # ------------------------------------------------------------------
    # Backend factory
    # ------------------------------------------------------------------

    def _build_backend(
        self, provider: str, api_key: str,
        model_size: str, device: str, compute_type: str, language: str,
        llama_cpp_host: str = "http://llama_cpp:8080", gemma_model: str = "gemma",
    ):
        if provider == "openai":
            self.get_logger().info("MicBridge STT: OpenAI Whisper API")
            return _OpenAIBackend(api_key, language)
        elif provider == "gemini":
            self.get_logger().info("MicBridge STT: Gemini")
            return _GeminiBackend(api_key, language)
        elif provider == "gemma_local":
            self.get_logger().info(
                f"MicBridge STT: Gemma local ({gemma_model} via {llama_cpp_host})"
            )
            return _GemmaLocalBackend(llama_cpp_host, gemma_model, language)
        else:
            self.get_logger().info(
                f"MicBridge STT: faster-whisper ({model_size}, {device}, {compute_type})"
            )
            return _FasterWhisperBackend(model_size, device, compute_type, language)

    # ------------------------------------------------------------------
    # HTTP server — serves the HTML page
    # ------------------------------------------------------------------

    def _run_http_server(self, port: int) -> None:
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
        self.get_logger().info(f"MicBridge HTTP on port {port}")
        server.serve_forever()

    # ------------------------------------------------------------------
    # WebSocket server — receives Int16 PCM from the browser
    # ------------------------------------------------------------------

    def _run_ws_server(self, port: int) -> None:
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
            addr = getattr(websocket, "remote_address", "?")
            node.get_logger().info(f"Browser mic connected from {addr}")
            node._ws_clients.add(websocket)

            voiced_frames: list[bytes] = []
            silent_frames = 0
            speaking = False
            # Thresholds are derived from the first frame's actual size so they
            # are correct regardless of the browser's ScriptProcessor buffer size.
            silence_needed: int = 3     # recalculated on first message
            max_voiced: int = 120       # recalculated on first message

            try:
                async for message in websocket:
                    if not isinstance(message, bytes) or not message:
                        continue

                    pcm = np.frombuffer(message, dtype=np.int16).astype(np.float32) / 32768.0
                    chunk_samples = len(pcm)

                    # Recalculate thresholds from actual chunk duration.
                    # Browser sends 4096-sample chunks → 256 ms at 16 kHz.
                    # silence_duration=0.8 s → 3 chunks; max_utterance=30 s → 117 chunks.
                    chunk_dur = chunk_samples / node._rate
                    silence_needed = max(1, round(node._silence / chunk_dur))
                    max_voiced     = max(1, round(node._max_utt / chunk_dur))

                    rms = float(np.sqrt(np.mean(pcm ** 2)))
                    raw = (pcm * 32767).astype(np.int16).tobytes()

                    if rms >= node._vad_thr:
                        speaking = True
                        silent_frames = 0
                        voiced_frames.append(raw)
                        # Force-flush if the utterance exceeds max duration.
                        if len(voiced_frames) >= max_voiced:
                            node._audio_queue.put((b"".join(voiced_frames), websocket))
                            voiced_frames = []
                            silent_frames = 0
                            speaking = False
                    elif speaking:
                        voiced_frames.append(raw)
                        silent_frames += 1
                        if silent_frames >= silence_needed:
                            node._audio_queue.put((b"".join(voiced_frames), websocket))
                            voiced_frames = []
                            silent_frames = 0
                            speaking = False

            except Exception:
                pass
            finally:
                node._ws_clients.discard(websocket)

            node.get_logger().info("Browser mic disconnected")

        async with websockets.serve(_handler, "0.0.0.0", port):
            self.get_logger().info(f"MicBridge WebSocket on port {port}")
            await asyncio.Future()

    # ------------------------------------------------------------------
    # TTS audio → browser
    # ------------------------------------------------------------------

    def _on_tts_audio(self, msg: UInt8MultiArray) -> None:
        audio_bytes = bytes(msg.data)
        if not audio_bytes or not self._ws_clients or self._ws_loop is None:
            return

        async def _broadcast():
            for ws in list(self._ws_clients):
                try:
                    await ws.send(audio_bytes)
                except Exception:
                    pass

        asyncio.run_coroutine_threadsafe(_broadcast(), self._ws_loop)

    # ------------------------------------------------------------------
    # STT worker
    # ------------------------------------------------------------------

    def _wav_header(self, pcm_bytes: bytes) -> bytes:
        data_size = len(pcm_bytes)
        return struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", 36 + data_size, b"WAVE",
            b"fmt ", 16, 1, 1,
            self._rate, self._rate * 2, 2, 16,
            b"data", data_size,
        ) + pcm_bytes

    def _process_loop(self) -> None:
        while True:
            item = self._audio_queue.get()
            if item is None:
                break
            pcm_bytes, websocket = item
            wav_bytes = self._wav_header(pcm_bytes)
            try:
                text = self._backend.transcribe(wav_bytes, self._rate)
            except Exception as exc:
                self.get_logger().error(f"MicBridge transcription error: {exc}")
                text = ""
            if text:
                self.get_logger().info(f"MicBridge transcribed: {text!r}")
                if "doggo" not in text.lower():
                    self.get_logger().debug("Ignored (no wake word 'Doggo')")
                    if self._ws_loop is not None:
                        asyncio.run_coroutine_threadsafe(websocket.send(f"[ignored] {text}"), self._ws_loop)
                    continue
                msg = String()
                msg.data = text
                self._pub.publish(msg)
                if self._ws_loop is not None:
                    asyncio.run_coroutine_threadsafe(websocket.send(text), self._ws_loop)


def main(args=None):
    rclpy.init(args=args)
    node = MicBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
