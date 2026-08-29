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

from __future__ import annotations

import asyncio
import base64
import http.server
import io
import json
import queue
import struct
import subprocess
import threading
import time

import numpy as np
import requests
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from std_msgs.msg import String, UInt8MultiArray, Bool
from geometry_msgs.msg import Twist
from go2_interfaces.msg import WebRtcReq

from .command_dispatcher import (
    CMD_MAP, LLAMA_SAMPLING, CommandDispatcher, build_unified_tools, coerce_command,
    coerce_str, command_for_text, feedback_for_action, language_name,
    personalize_feedback, system_prompt, system_prompt_text,
)
from sensor_msgs.msg import Image
from vision_msgs.msg import Detection2DArray

try:
    import cv2
    from cv_bridge import CvBridge
    _CV_AVAILABLE = True
except Exception:      # vision extras absent -> look_around degrades, node still runs
    _CV_AVAILABLE = False

from .visual_router import (
    DEFAULT_PATH_PRIORITY,
    choose_visual_path,
    match_coco_classes,
    summarize_detections,
)
from .audio_vad import (
    AUDIO_SOURCE_PRIORITY,
    SegmentingVAD,
    find_bluetooth_sink,
    select_pulse_source,
)


class _LocalMicClient:
    """Stand-in client handle for audio captured from a local device.

    Every audio pipeline in this node is keyed on a browser WebSocket, and
    protocol messages are sent back to that handle. A microphone plugged
    into the machine has no browser attached, so this absorbs those sends
    while leaving the capture -> VAD -> backend path byte-for-byte identical
    to the browser and robot-mic paths.
    """

    remote_address = "local-mic"

    async def send(self, _data):  # noqa: D401 - no browser to deliver to
        return

    def __repr__(self):
        return "<local-mic>"
from .tls_cert import get_server_context


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
Step 2: Pick an audio source, then toggle <em>Start Talking</em>.<br>
Transcriptions publish to <code>/speech_text</code>.</p>

<div class="row">
  <button id="connectBtn" class="btn btn-primary" onclick="doConnect()">&#128268; Connect</button>
  <button id="talkBtn"    class="btn" onclick="toggleTalk()" style="display:none">&#127908; Start Talking</button>
  <button id="discBtn"    class="btn btn-danger" onclick="doDisconnect()" style="display:none">&#10006; Disconnect</button>
</div>

<div id="sourceRow" class="row" style="display:none;margin-top:10px">
  <span style="font-size:13px;color:#555">Audio source:</span>
  <label style="font-size:13px;cursor:pointer">
    <input type="radio" name="audioSource" value="browser" checked onchange="setAudioSource('browser')"> Browser mic
  </label>
  <label style="font-size:13px;cursor:pointer">
    <input type="radio" name="audioSource" value="robot" onchange="setAudioSource('robot')"> Robot mic
  </label>
</div>

<div id="textRow" class="row" style="display:none;margin-top:10px">
  <input id="textInput" type="text" placeholder="Type a command or question&#8230;"
         style="flex:1;padding:9px 12px;font-size:14px;border-radius:6px;border:1px solid #aaa;min-width:0"
         onkeydown="if(event.key==='Enter')sendText()">
  <button id="ttsPipeBtn" class="btn" onclick="toggleTtsPipe()"
          title="Synthesize text to audio (TTS) then feed through the full STT+NLU audio pipeline">&#128266;&#8594;&#127908;</button>
  <button class="btn btn-primary" onclick="sendText()">&#9658; Send</button>
</div>

<p id="status"><span id="indicator"></span>Not connected.</p>
<div id="log"></div>

<script>
var ws, audioCtx, source, proc;
var streaming = false;
var ttsPipeMode = false;
var audioSource = 'browser';
var isTtsSpeaking = false;
var _ttsUnmuteTimer = null;

function setAudioSource(src) {{
  audioSource = src;
  if (ws && ws.readyState === 1) {{
    ws.send(JSON.stringify({{type: 'set_audio_source', source: src}}));
  }}
  log('Audio source: ' + (src === 'robot' ? 'robot mic' : 'browser mic'));
}}

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

  ws = new WebSocket('{ws_scheme}://' + location.hostname + ':{ws_port}');
  ws.binaryType = 'arraybuffer';

  ws.onopen = function() {{
    // No getUserMedia here -- Robot mic mode needs no browser mic access at
    // all, and forcing a permission prompt on every connect blocked that
    // path entirely (worse: on plain-HTTP non-localhost origins, browsers
    // refuse to even show the prompt -- navigator.mediaDevices is undefined
    // there, so the old code threw before its .catch() could run, hanging
    // on "requesting permission" forever). Browser mic is now initialized
    // lazily, only when actually selected and Start Talking is pressed.
    hide('connectBtn');
    show('talkBtn');
    show('discBtn');
    show('textRow');
    show('sourceRow');
    setStatus('Connected — pick an audio source, then click “Start Talking”.');
    log('Connected');
  }};

  ws.onmessage = function(e) {{
    if (typeof e.data === 'string') {{
      var p = null;
      try {{ p = JSON.parse(e.data); }} catch(_) {{}}
      if (p) {{ renderResult(p); }}
      else {{ setStatus('\U0001f4ac ' + e.data); log('\U0001f4ac ' + e.data); }}
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
    isTtsSpeaking = true;
    if (_ttsUnmuteTimer) clearTimeout(_ttsUnmuteTimer);
    src.onended = function() {{
      // 600 ms cooldown after TTS ends before mic re-opens — lets reverb die out
      _ttsUnmuteTimer = setTimeout(function() {{ isTtsSpeaking = false; }}, 600);
    }};
    src.start(0);
    log('\U0001f50a TTS playing (' + decoded.duration.toFixed(1) + 's)');
  }}, function(err) {{
    log('Audio decode error: ' + err);
  }});
}}

function esc(s) {{
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}}

function renderResult(r) {{
  if (r.type === 'tts_pipe_queued') {{ log('\U0001f50a→\U0001f3a4 Synthesizing… “' + (r.text || '') + '”'); return; }}
  if (r.type === 'tts_pipe_error') {{ log('❌ TTS synthesis failed: ' + (r.text || '')); return; }}

  var ok = !!r.contains_wake_word;
  var dropped = r.type === 'dropped';
  var tool = r.tool_name || ((r.command && r.command !== 'unknown') ? 'execute_robot_command' : 'respond_conversationally');
  var isCmdTool = (tool === 'execute_robot_command');
  var toolIcon = isCmdTool ? '\U0001f527' : '\U0001f4ac';
  var color = dropped ? '#ef4444' : ok ? '#16a34a' : '#64748b';
  var cmdLabel = (r.command && r.command !== 'unknown') ? ' → [' + r.command + ']' : '';
  var summary = dropped
    ? '⚠ Dropped (' + r.age_s.toFixed(1) + 's old)'
    : toolIcon + ' ' + (ok ? '✓ ' : '∅ ') + esc(r.transcript || '') + cmdLabel;
  setStatus('<span style=”color:' + color + '”>' + summary + '</span>');

  var timing = '';
  if (r.timing) {{
    var pts = [];
    if (r.timing.infer_ms != null) pts.push(r.timing.infer_ms + ' ms infer');
    if (r.timing.total_ms != null) pts.push(r.timing.total_ms + ' ms total');
    if (pts.length) timing = ' <small style=”color:#999”>(' + pts.join(' / ') + ')</small>';
  }}

  /* ── tool call parameters table ──────────────────────────── */
  var rows = '';
  var addRow = function(k, v) {{
    var vHtml = typeof v === 'boolean'
      ? (v ? '<span style=”color:#16a34a”>true</span>' : '<span style=”color:#dc2626”>false</span>')
      : '<span style=”color:#1e40af”>' + esc(String(v)) + '</span>';
    rows += '<tr><td style=”color:#6b7280;padding:1px 10px 1px 0;white-space:nowrap;vertical-align:top”>' + esc(k) + '</td>'
           + '<td style=”word-break:break-all”>' + vHtml + '</td></tr>';
  }};
  addRow('transcript', r.transcript || '');
  addRow('contains_wake_word', !!r.contains_wake_word);
  if (isCmdTool) {{
    addRow('command', r.command || '(none)');
    if (r.text_response) addRow('feedback', r.text_response);
  }} else {{
    if (r.text_response) addRow('spoken_reply', r.text_response);
  }}
  var inputBadge = r.input
    ? ' <span style=”font-size:10px;background:#e5e7eb;border-radius:3px;padding:0 5px;margin-left:4px”>' + esc(r.input) + '</span>'
    : '';
  var toolBlock = '<div style=”font-size:11px;margin:3px 0 2px”>'
    + '<strong style=”font-size:12px”>' + toolIcon + ' ' + esc(tool) + '</strong>' + inputBadge
    + '<table style=”margin-top:4px;border-collapse:collapse;line-height:1.5”>' + rows + '</table>'
    + '</div>';

  /* ── raw JSON toggle ────────────────────────────────────── */
  var safe = JSON.stringify(r, null, 2).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  var rawToggle = '<details style=”margin-top:5px”>'
    + '<summary style=”font-size:10px;color:#9ca3af;cursor:pointer;list-style:none”>raw JSON ▾</summary>'
    + '<pre style=”margin:2px 0 0;font-size:10px;background:#f1f5f9;padding:5px 7px;'
    + 'border-radius:3px;overflow-x:auto;white-space:pre-wrap;word-break:break-all”>' + safe + '</pre>'
    + '</details>';

  var d = document.getElementById('log');
  d.innerHTML = '<details style=”margin:0 0 2px”>'
    + '<summary style=”cursor:pointer;list-style:none;padding:2px 0;color:' + color + '”>'
    + new Date().toLocaleTimeString() + ' — ' + summary + timing + '</summary>'
    + '<div style=”margin:2px 0 4px 4px;padding:4px 8px;border-left:3px solid ' + color + ';background:#fafafa;border-radius:0 4px 4px 0”>'
    + toolBlock + rawToggle
    + '</div></details>' + d.innerHTML;
}}

  ws.onclose = function() {{
    streaming = false;
    audioSource = 'browser';
    var browserRadio = document.querySelector('input[name="audioSource"][value="browser"]');
    if (browserRadio) browserRadio.checked = true;
    setStatus('Disconnected.');
    log('Connection closed');
    show('connectBtn');
    enable('connectBtn');
    hide('talkBtn');
    hide('discBtn');
    hide('textRow');
    hide('sourceRow');
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

// Sets up getUserMedia + the audio graph. Only called once, lazily, the
// first time Start Talking is pressed while Browser mic is selected.
// cb(true) on success, cb(false) on failure (status/log already set).
// Top-level (not nested in doConnect()) -- toggleTalk() calls this directly
// and has no access to doConnect()'s local scope.
function initBrowserMic(cb) {{
  if (audioCtx) {{ cb(true); return; }}
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {{
    setStatus('Microphone access needs HTTPS or localhost — this page is ' + location.protocol + '//' + location.hostname + '. Use “Robot mic” instead, or open this page via an SSH tunnel to localhost.');
    log('getUserMedia unavailable — insecure origin');
    cb(false);
    return;
  }}
  setStatus('Requesting microphone permission…');
  navigator.mediaDevices.getUserMedia({{
    audio: {{channelCount: 1, echoCancellation: true, noiseSuppression: true}}
  }}).then(function(stream) {{
    audioCtx = new (window.AudioContext || window.webkitAudioContext)({{sampleRate: 16000}});
    source = audioCtx.createMediaStreamSource(stream);
    // 2048-sample buffer = 128 ms at 16 kHz — tighter VAD granularity
    proc = audioCtx.createScriptProcessor(2048, 1, 1);
    proc.onaudioprocess = function(e) {{
      if (!streaming || ws.readyState !== 1 || isTtsSpeaking || audioSource !== 'browser') return;
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
    log('Microphone ready');
    cb(true);
  }}).catch(function(err) {{
    setStatus('Microphone error: ' + err.message);
    log('getUserMedia error: ' + err);
    cb(false);
  }});
}}

function setListening(active) {{
  if (ws && ws.readyState === 1) {{
    ws.send(JSON.stringify({{type: 'set_listening', active: active}}));
  }}
}}

function startedListening() {{
  var btn = document.getElementById('talkBtn');
  btn.textContent = '\U0001f534 Stop Talking';
  btn.className = 'btn btn-active';
  var srcLabel = audioSource === 'robot' ? 'robot mic' : 'microphone';
  setStatus('<span id="indicator" class="on"></span>Streaming ' + srcLabel + ' to robot…');
  log('Started streaming (' + audioSource + ')');
  setListening(true);
}}

function toggleTalk() {{
  var btn = document.getElementById('talkBtn');
  if (!streaming) {{
    if (audioSource === 'browser') {{
      disable('talkBtn');
      initBrowserMic(function(ok) {{
        enable('talkBtn');
        if (!ok) return;
        streaming = true;
        startedListening();
      }});
    }} else {{
      streaming = true;
      startedListening();
    }}
  }} else {{
    streaming = false;
    btn.textContent = '\U0001f3a4 Start Talking';
    btn.className = 'btn';
    setStatus('Paused — click “Start Talking” to resume.');
    log('Stopped streaming');
    setListening(false);
  }}
}}

function doDisconnect() {{
  if (ws) ws.close();
}}

function toggleTtsPipe() {{
  ttsPipeMode = !ttsPipeMode;
  var btn = document.getElementById('ttsPipeBtn');
  btn.className = ttsPipeMode ? 'btn btn-active' : 'btn';
  btn.title = ttsPipeMode
    ? 'TTS→STT active — text is synthesized to audio then run through the full audio pipeline'
    : 'Synthesize text to audio (TTS) then feed through the full STT+NLU audio pipeline';
}}

function sendText() {{
  var inp = document.getElementById('textInput');
  var t = inp.value.trim();
  if (!t || !ws || ws.readyState !== 1) return;
  if (ttsPipeMode) {{
    ws.send(JSON.stringify({{type: 'tts_pipe', text: t}}));
    log('\U0001f50a→\U0001f3a4 ' + t);
  }} else {{
    ws.send(t);
    log('✏ ' + t);
  }}
  inp.value = '';
  inp.focus();
}}
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# STT backends (duplicated from stt_node to avoid circular imports)
# ---------------------------------------------------------------------------

class _FasterWhisperBackend:
    def __init__(self, model_size: str, device: str, compute_type: str, language: str, wake_word: str = ""):
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._language = language
        self._wake_word = wake_word.lower()
        self._model = None
        self._load_lock = threading.Lock()

    def _load(self):
        with self._load_lock:
            if self._model is None:
                from faster_whisper import WhisperModel
                self._model = WhisperModel(
                    self._model_size, device=self._device, compute_type=self._compute_type
                )

    def warmup(self) -> None:
        """Pre-load the model in a background thread so first real utterance isn't delayed."""
        threading.Thread(target=self._load, daemon=True, name="whisper_warmup").start()

    def transcribe(self, audio_bytes: bytes, sample_rate: int) -> tuple[str, bool]:
        self._load()
        audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        segs, _ = self._model.transcribe(audio, language=self._language, beam_size=1)
        text = " ".join(s.text for s in segs).strip()
        return text, (self._wake_word in text.lower()) if self._wake_word else True


class _OpenAIBackend:
    def __init__(self, api_key: str, language: str, wake_word: str = ""):
        import openai
        self._client = openai.OpenAI(api_key=api_key)
        self._language = language
        self._wake_word = wake_word.lower()

    def transcribe(self, audio_bytes: bytes, sample_rate: int) -> tuple[str, bool]:
        import openai
        buf = io.BytesIO(audio_bytes)
        buf.name = "audio.wav"
        try:
            text = self._client.audio.transcriptions.create(
                model="whisper-1", file=buf, language=self._language,
            ).text.strip()
        except openai.OpenAIError:
            return "", False
        return text, (self._wake_word in text.lower()) if self._wake_word else True


class _GeminiBackend:
    def __init__(self, api_key: str, language: str, wake_word: str = ""):
        from google import genai
        self._client = genai.Client(api_key=api_key)
        self._language = language
        self._wake_word = wake_word

    def transcribe(self, audio_bytes: bytes, sample_rate: int) -> tuple[str, bool]:
        import os
        import tempfile
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_bytes)
                path = f.name
            try:
                from google.genai import types
                up = self._client.files.upload(path=path, config={"mime_type": "audio/wav"})
                prompt = (
                    f"Transcribe this audio. Language: {self._language}. "
                    f'Detect if the wake word "{self._wake_word}" appears anywhere '
                    "(case-insensitive). "
                    'Return ONLY a JSON object with keys "transcript" (string) and '
                    '"contains_wake_word" (boolean). No other text.'
                )
                r = self._client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[up, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                    ),
                )
                parsed = json.loads(r.text.strip())
                transcript = parsed.get("transcript", "").strip()
                found = bool(parsed.get("contains_wake_word", False))
                return transcript, found
            finally:
                os.unlink(path)
        except Exception:
            return "", False


class _GemmaLocalBackend:
    """Gemma 4 audio transcription via a local llama.cpp sidecar.

    Works with either GEMMA_SIZE (12B or E4B) -- audio projects directly into
    the text embedding space, not through mmproj, so it isn't tied to the
    vision-only mmproj file's model-size variant.

    Uses the OpenAI-compatible /v1/chat/completions endpoint.  Audio is sent
    via the input_audio content part (llama.cpp ≥ b8766, PR #21421).
    Returns (transcript, contains_wake_word) so the caller never needs to
    do a hardcoded string match.
    """

    def __init__(self, llama_cpp_host: str, model: str, language: str, wake_word: str = ""):
        self._host = llama_cpp_host.rstrip("/")
        self._model = model
        self._language = language
        self._wake_word = wake_word

    def transcribe(self, audio_bytes: bytes, sample_rate: int) -> tuple[str, bool]:
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
                                f"The speaker is speaking {language_name(self._language)}. "
                                "Transcribe the audio exactly as spoken in that language. "
                                "Never translate to any other language. "
                                f'Also detect whether the wake word "{self._wake_word}" '
                                "appears anywhere in the transcript (case-insensitive). "
                                'Respond ONLY with a JSON object: '
                                '{"transcript": "<exact transcription>", '
                                '"contains_wake_word": true/false}'
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
                    "response_format": {"type": "json_object"},
                    "stream": False,
                    **LLAMA_SAMPLING,
                },
                timeout=120,
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"].strip()
            parsed = json.loads(raw)
            transcript = parsed.get("transcript", "").strip()
            found = bool(parsed.get("contains_wake_word", False))
            return transcript, found
        except Exception:
            return "", False


# ---------------------------------------------------------------------------
# Unified result type — returned by unified backends (gemma_local in unified
# mode, openai_realtime, gemini_live).  Pure-STT backends keep returning
# (str, bool) so _process_loop can branch on type.
# ---------------------------------------------------------------------------

from dataclasses import dataclass, field as dc_field

@dataclass
class _UnifiedResult:
    contains_wake_word: bool
    command: str | None             # key into CMD_MAP, or None / "unknown"
    parameters: dict = dc_field(default_factory=dict)
    text_response: str | None = None   # gemma_local — forward to /tts
    audio_response: bytes | None = None  # openai_realtime/gemini_live — forward to /tts_audio
    # True when the reply was streamed straight to a local speaker as the
    # model produced it. The caller must then publish nothing: the audio has
    # already been heard, and re-sending it would speak the reply twice.
    audio_streamed: bool = False
    transcript: str | None = None      # raw transcript of what was spoken (for echo feedback)


# ---------------------------------------------------------------------------
# _GemmaUnifiedBackend — single llama.cpp call: audio → wake word + command + text
# ---------------------------------------------------------------------------

class _GemmaUnifiedBackend:
    """One llama.cpp /v1/chat/completions call: audio in → structured tool call out.

    Uses Gemma 4's NATIVE tool calling (requires llama-server --jinja). The model
    chooses between two tools, and that choice IS the high-confidence gate:

      execute_robot_command   → the speech clearly maps to a known robot command
      respond_conversationally → anything else (chit-chat, unclear, no wake word)

    Because "don't issue a command" is a distinct tool rather than an "unknown"
    sentinel in a forced field, the model stops force-fitting ambiguous speech
    onto the nearest command. The `command` argument is grammar-constrained to
    the exact CMD_MAP keys, so hallucinated command names are impossible.

    Returns _UnifiedResult with text_response set (TTS handled by tts_node via
    the /tts topic); audio_response is always None. Falls back to parsing a JSON
    content body if the server returns no tool_calls (e.g. --jinja not enabled).
    """

    # Prompts and tool schema are built by command_dispatcher so both languages
    # (and both nodes) share one source. The Indonesian path is rendered entirely
    # in Bahasa Indonesia — see command_dispatcher.system_prompt / build_unified_tools.
    def __init__(self, llama_cpp_host: str, model: str, language: str,
                 wake_word: str = "", logger=None):
        self._host = llama_cpp_host.rstrip("/")
        self._model = model
        self._language = language
        self._wake_word = wake_word
        self._system = system_prompt(language, wake_word)
        self._system_text = system_prompt_text(language, wake_word)
        self._log = logger
        self._tools = build_unified_tools(language)

    def _info(self, msg: str) -> None:
        if self._log:
            self._log.info(msg)

    def _error(self, msg: str) -> None:
        if self._log:
            self._log.error(msg)

    def _system_for(self, face_names: str, text_path: bool = False) -> str:
        """System prompt for this call, optionally naming who is in front of the robot.

        Rebuilt per call rather than cached at __init__ because the recognized
        people change as visitors come and go. Falls back to the prebuilt static
        prompt when nobody is recognized, so the no-face path is unchanged.
        """
        if not face_names:
            return self._system_text if text_path else self._system
        builder = system_prompt_text if text_path else system_prompt
        return builder(self._language, self._wake_word, face_names)

    def _override_wake_word(self, result: "_UnifiedResult") -> "_UnifiedResult":
        """String-match safety net: if transcript has wake word but model set False, correct it."""
        if (not result.contains_wake_word and result.transcript
                and self._wake_word.lower() in result.transcript.lower()):
            result.contains_wake_word = True
            self._info("Wake-word string-match override → contains_wake_word=True")
        return result

    def _override_command(self, result: "_UnifiedResult") -> "_UnifiedResult":
        """Deterministic command fallback when the LLM under-fires.

        Gemma reliably transcribes Indonesian but tends to pick the conversational
        tool even on a clear command ("elliot duduk" → respond_conversationally).
        The command vocabulary is finite, so if the model went conversational while
        the wake word is present and the transcript literally names a known command,
        execute that command instead. Scoped to `id` so the working English path
        (which keeps its over-fire protection from the two-tool design) is untouched.
        """
        if (self._language or "en").lower() != "id":
            return result
        if result.command and result.command != "unknown":
            return result   # model already issued a command
        if not result.contains_wake_word or not result.transcript:
            return result
        key = command_for_text(result.transcript, self._language)
        if key:
            action = CMD_MAP.get(key)
            result.command = key
            if action is not None:
                result.text_response = feedback_for_action(action)
            self._info(f"Command string-match override → {key}")
        return result

    def _parse_message(self, message: dict, fallback_transcript) -> "_UnifiedResult":
        """Turn a chat-completion message into a _UnifiedResult.

        Prefers native tool_calls; falls back to a JSON content body so the node
        still works against a server without --jinja.
        """
        tool_calls = message.get("tool_calls") or []
        if tool_calls:
            fn = tool_calls[0].get("function", {})
            name = fn.get("name")
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except Exception:
                args = {}
            if not isinstance(args, dict):
                args = {}
            transcript = coerce_str(args.get("transcript")) or coerce_str(fallback_transcript)
            wake = bool(args.get("contains_wake_word", False))
            # execute_robot_command (two-tool) and process_speech (single-tool) both
            # carry a `command`. coerce_command maps "none"/garbage → "unknown".
            if name in ("execute_robot_command", "process_speech"):
                cmd = coerce_command(args.get("command"))
                if cmd == "unknown":
                    # No command → conversational; use spoken_reply if present.
                    return _UnifiedResult(
                        contains_wake_word=wake, command="unknown", parameters={},
                        text_response=coerce_str(args.get("spoken_reply")),
                        transcript=transcript,
                    )
                # Spoken feedback comes from the canned FEEDBACK_MAP, not the model.
                action = CMD_MAP.get(cmd)
                text = feedback_for_action(action) if action is not None else None
                return _UnifiedResult(
                    contains_wake_word=wake, command=cmd, parameters={},
                    text_response=text, transcript=transcript,
                )
            # respond_conversationally (or any unexpected tool)
            return _UnifiedResult(
                contains_wake_word=wake, command="unknown", parameters={},
                text_response=coerce_str(args.get("spoken_reply")),
                transcript=transcript,
            )

        # No tool call — fall back to a JSON content body (legacy / no --jinja).
        raw = (message.get("content") or "").strip()
        self._info(f"Gemma no tool_call, raw content: {raw}")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = None
        if not isinstance(parsed, dict):
            return _UnifiedResult(
                contains_wake_word=False, command="unknown",
                text_response=raw or None, transcript=coerce_str(fallback_transcript),
            )
        return _UnifiedResult(
            contains_wake_word=bool(parsed.get("contains_wake_word", False)),
            command=coerce_command(parsed.get("command")),
            parameters=parsed.get("parameters") if isinstance(parsed.get("parameters"), dict) else {},
            text_response=coerce_str(parsed.get("text_response")),
            transcript=coerce_str(parsed.get("transcript")) or coerce_str(fallback_transcript),
        )

    def transcribe(self, audio_bytes: bytes, sample_rate: int,
                   face_names: str = "") -> "_UnifiedResult":
        # Two attempts with DIFFERENT stop handling:
        #   attempt 0 — stop at "<|channel>thought" so a genuine cold-start reasoning
        #               loop fails fast (<1s) instead of running to n-predict.
        #   attempt 1 — NO stop. Some inputs (e.g. "duduk") always emit a short
        #               reasoning preamble before the forced tool call; stopping the
        #               retry too would cut the tool call and yield nothing. Without
        #               the stop the model finishes reasoning AND emits the tool call.
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        system = self._system_for(face_names)
        for attempt in range(2):
            try:
                body = {
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": system},
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
                    "tools": self._tools,
                    "tool_choice": "required",
                    "stream": False,
                    **LLAMA_SAMPLING,
                }
                if attempt == 0:
                    body["stop"] = ["<|channel>thought"]
                resp = requests.post(
                    f"{self._host}/v1/chat/completions", json=body, timeout=120
                )
                resp.raise_for_status()
                message = resp.json()["choices"][0]["message"]
                if message.get("tool_calls"):
                    self._info(f"Gemma message: {json.dumps(message)[:400]}")
                    return self._override_command(self._override_wake_word(self._parse_message(message, fallback_transcript=None)))
                # No tool call + empty content = the stop cut a reasoning preamble.
                # Retry WITHOUT the stop so reasoning + tool call can complete.
                content = (message.get("content") or "").strip()
                if not content and attempt == 0:
                    self._info("Gemma audio: reasoning preamble cut, retrying without stop…")
                    continue
                self._info(f"Gemma message: {json.dumps(message)[:400]}")
                return self._override_command(self._override_wake_word(self._parse_message(message, fallback_transcript=None)))
            except Exception as exc:
                self._error(f"Gemma transcription failed: {exc}")
                return _UnifiedResult(contains_wake_word=False, command=None)
        return _UnifiedResult(contains_wake_word=False, command=None)

    def transcribe_text(self, text: str, face_names: str = "") -> "_UnifiedResult":
        try:
            resp = requests.post(
                f"{self._host}/v1/chat/completions",
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system",
                         "content": self._system_for(face_names, text_path=True)},
                        {"role": "user", "content": text},
                    ],
                    "tools": self._tools,
                    "tool_choice": "required",
                    "stream": False,
                    **LLAMA_SAMPLING,
                },
                timeout=60,
            )
            resp.raise_for_status()
            message = resp.json()["choices"][0]["message"]
            self._info(f"Gemma text message: {json.dumps(message)[:400]}")
            return self._override_command(
                self._override_wake_word(self._parse_message(message, fallback_transcript=text))
            )
        except Exception as exc:
            self._error(f"Gemma text input failed: {exc}")
            return _UnifiedResult(contains_wake_word=False, command=None, transcript=text)


# ---------------------------------------------------------------------------
# _OpenAIRealtimeBackend — persistent WebSocket: audio → function call + PCM audio
# ---------------------------------------------------------------------------

class _OpenAIRealtimeBackend:
    """OpenAI gpt-realtime-2.1 via the GA Realtime WebSocket API (client.realtime, not
    the retired client.beta.realtime).

    Maintains a persistent session.  Each utterance is sent as a PCM audio
    buffer; the model calls parse_speech_command() for structured output and
    generates a PCM audio response (acknowledgement / conversational reply).

    Returns _UnifiedResult with audio_response set; text_response is None.
    """

    _TOOL = {
        "type": "function",
        "name": "parse_speech_command",
        "description": "Extract the robot command, wake-word status, and transcript from the speech.",
        "parameters": {
            "type": "object",
            "properties": {
                "transcript": {
                    "type": "string",
                    "description": "Verbatim transcription of what was spoken.",
                },
                "contains_wake_word": {
                    "type": "boolean",
                    "description": "True if the configured wake word appears in the utterance.",
                },
                "command": {
                    "type": "string",
                    "description": (
                        "One of the available robot commands, or 'unknown' if none matches: "
                        "sit, stand, balance, stretch, recover, stop, raise_body, lower_body, "
                        "trot, crawl, stand_gait, rest_gait, slow_speed, normal_speed, "
                        "fast_speed, forward, backward, turn_left, turn_right, stop_move, "
                        "keep_forward, keep_backward, keep_turn_left, keep_turn_right, "
                        "hello, dance1, dance2, front_flip, wiggle_hips, finger_heart, "
                        "handstand, moon_walk, continuous_gait, auto_rest"
                    ),
                },
                "parameters": {
                    "type": "object",
                    "description": "Extra parameters (empty for most commands).",
                },
                "needs_look": {
                    "type": "boolean",
                    "description": (
                        "True if answering requires actually seeing through the "
                        "camera -- the speaker asks what you can see, tells you to "
                        "look at something, or asks you to find or count an object. "
                        "Set it every time such a question is asked, even if you "
                        "looked a moment ago: the robot moves and the view is never "
                        "the same twice."
                    ),
                },
                "look_query": {
                    "type": "string",
                    "description": (
                        "What to look for, in the speaker's own words (e.g. 'a person', "
                        "'the sports ball', 'what is in front of you'). Empty unless "
                        "needs_look is true."
                    ),
                },
            },
            "required": ["transcript", "contains_wake_word", "command"],
        },
    }

    def __init__(self, api_key: str, model: str, wake_word: str = "", language: str = "en", logger=None):
        self._api_key = api_key
        self._model = model or "gpt-realtime-2.1"
        # When set, each PCM delta is handed to this callback as it arrives
        # instead of being buffered until response.done. Lets a local speaker
        # start talking ~300ms in rather than after the whole reply, and skips
        # MP3 encoding entirely (the API already sends PCM).
        self.on_audio_delta = None
        # Set by the node: query -> (observation_text, image_data_url|None).
        # Routing between YOLO / on-board Gemma / attaching the frame to this
        # session lives in the node, which owns the camera and detection topics.
        self.on_look = None
        self._wake_word = wake_word
        self._language = language
        self._logger = logger
        self._session: object | None = None   # openai.AsyncRealtimeConnection
        self._conn_ctx = None                  # async context manager holding the session open
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ready = threading.Event()
        self._reconnecting = False

    def _log_error(self, msg: str) -> None:
        if self._logger is not None:
            self._logger.error(msg)

    @staticmethod
    def _describe_event_error(event) -> str:
        err = getattr(event, "error", None)
        if err is not None:
            code = getattr(err, "code", None)
            message = getattr(err, "message", None)
            if message:
                return f"{code}: {message}" if code else message
        return str(event)

    @staticmethod
    def _raise_if_response_failed(event) -> None:
        """response.done can carry status='failed'/'cancelled'/'incomplete' instead
        of an 'error' event — without this check that just silently produces an
        empty result instead of surfacing what went wrong."""
        resp = getattr(event, "response", None)
        status = getattr(resp, "status", None) if resp is not None else None
        if status not in (None, "completed"):
            details = getattr(resp, "status_details", None)
            raise RuntimeError(f"Realtime response ended with status={status!r}: {details}")

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        """Called once from MicBridgeNode.__init__ to start the persistent session."""
        self._loop = loop
        asyncio.run_coroutine_threadsafe(self._connect(), loop)

    async def _connect(self) -> None:
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=self._api_key)
            # GA Realtime API — client.realtime (client.beta.realtime is retired).
            # Session shape changed with the GA move: "type": "realtime" is required,
            # "modalities"/"input_audio_format"/"output_audio_format" were replaced by
            # "output_modalities" + a nested "audio.input"/"audio.output" block.
            # Entered manually (not via `async with`) so the connection survives past
            # this coroutine — it's reused across many transcribe() calls and torn
            # down explicitly in _reconnect() when the session dies mid-run.
            conn_ctx = client.realtime.connect(model=self._model)
            conn = await conn_ctx.__aenter__()
            await conn.session.update(session={
                "type": "realtime",
                "model": self._model,
                "output_modalities": ["audio"],
                # Session default. Tool-calling (command extraction) runs at this level;
                # the spoken reply itself is further dropped to "minimal" per-response
                # below, since neither the templated ack nor casual chat need deliberation.
                "reasoning": {"effort": "low"},
                "instructions": (
                    "# Role and Objective\n"
                    "You are GO2, a Unitree quadruped robot voice assistant. Recognize spoken "
                    "commands (movement, posture, tricks) and extract them via "
                    "parse_speech_command(); hold brief natural conversation otherwise.\n\n"
                    "# Personality and Tone\n"
                    "Warm, concise, capable — a helpful field robot, not a chatty assistant. "
                    "Keep every spoken reply short.\n\n"
                    "# Language\n"
                    f"The speaker is speaking {language_name(self._language)}. Match their "
                    "language in conversation; command acknowledgements stay in the fixed "
                    "English format below regardless of input language.\n\n"
                    "# Reasoning\n"
                    "Use low reasoning only while identifying the command itself (matching "
                    "the utterance against the known command list via the tool call). Use no "
                    "reasoning — respond immediately — for the spoken reply that follows, "
                    "whether that's the fixed acknowledgement or casual conversation.\n\n"
                    "# Tools\n"
                    "When the speaker asks what you can see, tells you to look at "
                    "something, or asks you to find or count an object, set "
                    "needs_look=true and put what to look for in look_query. A camera "
                    "observation is then added to the conversation and you must answer "
                    "only from it. Set needs_look EVERY time such a question is asked, "
                    "even if you looked a moment ago: the robot moves and the view is "
                    "never the same twice. Never describe the surroundings from memory "
                    "or from an image earlier in this conversation, and never guess.\n"
                    f"Always call parse_speech_command() first. The wake word is "
                    f"'{self._wake_word}' — only treat an utterance as a command if the wake "
                    "word is present.\n\n"
                    "# Unclear Audio\n"
                    "Only act on clear audio. If the speech is muffled, cut off, or "
                    "unintelligible, don't guess — set command to 'unknown' and ask a short "
                    "clarifying question instead, e.g. \"Sorry, could you repeat that?\"\n\n"
                    "# Confirmation\n"
                    "If the wake word is present but the requested action is vague, or could "
                    "plausibly match more than one known command, or matches none clearly: do "
                    "NOT guess and do NOT execute. Set command to 'unknown' and ask a short "
                    "one-sentence question confirming what they meant, naming your best guess "
                    "if you have one, e.g. \"Did you want me to sit or stand?\". Only report a "
                    "command once it's unambiguous.\n\n"
                    "# Response Format\n"
                    "If a recognized robot command was found (command is not 'unknown'), your "
                    "spoken reply must be EXACTLY: \"Ok, <Action> now\" — where <Action> is the "
                    "present-participle (-ing) form of that command in plain English, e.g. "
                    "sit -> \"Ok, Sitting now\", stand -> \"Ok, Standing now\", turn_left -> "
                    "\"Ok, Turning left now\", front_flip -> \"Ok, Flipping now\". Say it once — "
                    "nothing else, no extra words, no filler, no repeating yourself, no "
                    "punctuation beyond the period. "
                    "If no command was recognized (command is 'unknown') because this is just "
                    "conversation, respond naturally instead with a short spoken reply (1–2 "
                    "sentences). If it's 'unknown' because you're asking for clarification per "
                    "the sections above, speak that clarifying question instead. "
                    "No markdown."
                ),
                "tools": [self._TOOL],
                "tool_choice": "required",
                "audio": {
                    "input": {
                        "format": {"type": "audio/pcm", "rate": 24000},
                        "turn_detection": None,  # manual VAD — we send complete utterances
                    },
                    "output": {
                        "format": {"type": "audio/pcm", "rate": 24000},
                        "voice": "cedar",  # male voice
                    },
                },
            })
            self._conn_ctx = conn_ctx
            self._session = conn
            self._ready.set()
        except Exception as exc:
            self._log_error(f"OpenAI Realtime connect failed: {type(exc).__name__}: {exc}")
            self._ready.clear()

    async def _reconnect(self) -> None:
        """Tear down the dead session (if any) and reconnect. Only one attempt
        runs at a time; a turn that fails while this is in flight just returns
        the empty fallback — the *next* turn picks up the fresh session."""
        if self._reconnecting:
            return
        self._reconnecting = True
        try:
            self._ready.clear()
            old_ctx, self._conn_ctx = self._conn_ctx, None
            self._session = None
            if old_ctx is not None:
                try:
                    await old_ctx.__aexit__(None, None, None)
                except Exception:
                    pass
            await self._connect()
            if self._ready.is_set() and self._logger is not None:
                self._logger.info("OpenAI Realtime session reconnected")
        finally:
            self._reconnecting = False

    def _schedule_reconnect(self) -> None:
        if self._loop is not None:
            asyncio.run_coroutine_threadsafe(self._reconnect(), self._loop)

    def transcribe(self, audio_bytes: bytes, sample_rate: int,
                   face_names: str = "") -> "_UnifiedResult":
        if self._loop is None or not self._ready.is_set():
            return _UnifiedResult(contains_wake_word=False, command=None)
        fut = asyncio.run_coroutine_threadsafe(
            self._turn(audio_bytes, face_names), self._loop
        )
        try:
            return fut.result(timeout=30)
        except Exception as exc:
            self._log_error(f"OpenAI Realtime turn failed, reconnecting: {type(exc).__name__}: {exc}")
            self._schedule_reconnect()
            return _UnifiedResult(contains_wake_word=False, command=None)

    async def _add_face_context(self, conn, face_names: str) -> None:
        """Tell the model who it is looking at, for this turn only.

        The session is long-lived and its instructions are fixed at connect
        time, so who is standing in front of the robot has to arrive per turn.
        Sent as a conversation item rather than a session update because it is
        scoped to this exchange: a stale name is worse than none, since being
        addressed as someone who has left the room reads as hallucination.
        """
        if not face_names:
            return
        await conn.conversation.item.create(item={
            "type": "message", "role": "user",
            "content": [{
                "type": "input_text",
                "text": (
                    "The robot currently recognizes these people in view: "
                    + face_names + ". Address them by name where it reads "
                    "naturally, including in short command acknowledgements, "
                    "but do not repeat the name in every sentence."
                ),
            }],
        })

    async def _turn(self, audio_bytes: bytes, face_names: str = "") -> "_UnifiedResult":
        import base64 as _b64
        conn = self._session
        if conn is None:
            return _UnifiedResult(contains_wake_word=False, command=None)
        await self._add_face_context(conn, face_names)

        # Send PCM audio as base64
        audio_b64 = _b64.b64encode(audio_bytes).decode()
        await conn.input_audio_buffer.append(audio=audio_b64)
        await conn.input_audio_buffer.commit()
        # First response: tool call only. Text-only modality so the model can't
        # also speak filler alongside the tool call — the spoken reply comes
        # entirely from the second response below, once the command is known.
        await conn.response.create(response={
            "output_modalities": ["text"],
            # Classification only, never spoken — the same minimal effort the
            # spoken response below already asks for. This is pure latency on
            # the critical path: nothing can be heard until it completes.
            "reasoning": {"effort": "minimal"},
        })

        cmd_args: dict = {}
        tool_call_id: str | None = None

        async for event in conn:
            etype = getattr(event, "type", "")
            if etype == "response.function_call_arguments.done":
                try:
                    args = json.loads(event.arguments)
                except Exception:
                    args = {}
                fname = getattr(event, "name", "") or ""
                call_id = getattr(event, "call_id", None)
                if fname:
                    cmd_args, tool_call_id = args, call_id
            elif etype == "error":
                raise RuntimeError(f"Realtime API error: {self._describe_event_error(event)}")
            elif etype == "response.done":
                self._raise_if_response_failed(event)
                break

        # Second response: the actual spoken acknowledgement ("Ok, <Action> now").
        # Look before speaking, so the reply describes what the robot can actually
        # see. The request arrives as a field on parse_speech_command rather than a
        # second tool: tool_choice is "required", which the model satisfies with one
        # call, so a separate look tool was never invoked (observed: look_around=0
        # even when asked point blank to look around).
        if cmd_args.get("needs_look") and self.on_look is not None:
            try:
                observation, image_url = self.on_look(
                    cmd_args.get("look_query") or cmd_args.get("transcript", "")
                )
            except Exception as e:
                observation, image_url = f"the camera is unavailable ({e})", None
            await conn.conversation.item.create(item={
                "type": "message", "role": "user",
                "content": [{
                    "type": "input_text",
                    "text": "Camera observation: " + (observation or "no view available"),
                }],
            })
            # The richest path attaches the frame itself and lets the model look.
            if image_url:
                await conn.conversation.item.create(item={
                    "type": "message", "role": "user",
                    "content": [{"type": "input_image", "image_url": image_url}],
                })

        # Gated on the wake word, not just on there being a tool call: the reply
        # is streamed to the speaker as it is produced, so generating it for an
        # utterance we were not addressed with would make the robot answer
        # overheard conversation. _handle_unified's wake-word check runs only
        # after the audio would already have been heard. Skipping it also saves
        # a whole API round trip on every stray utterance.
        audio_chunks: list[bytes] = []
        text_chunks: list[str] = []
        if tool_call_id and cmd_args.get("contains_wake_word"):
            await conn.conversation.item.create(item={
                "type": "function_call_output",
                "call_id": tool_call_id,
                "output": json.dumps({"status": "ok"}),
            })
            # Spoken reply: no reasoning — neither the fixed ack nor casual chat needs it.
            response2 = await conn.response.create(response={
                "reasoning": {"effort": "minimal"},
                "tool_choice": "none",  # must not call the tool again — just speak the reply
            })
            async for event in conn:
                etype = getattr(event, "type", "")
                if etype == "response.output_audio.delta":
                    chunk = getattr(event, "delta", b"")
                    if isinstance(chunk, str):
                        import base64 as _b64i
                        chunk = _b64i.b64decode(chunk)
                    if self.on_audio_delta is not None:
                        self.on_audio_delta(chunk)
                    else:
                        audio_chunks.append(chunk)
                elif etype == "response.output_audio_transcript.delta":
                    text_chunks.append(getattr(event, "delta", ""))
                elif etype == "error":
                    raise RuntimeError(f"Realtime API error: {self._describe_event_error(event)}")
                elif etype == "response.done":
                    self._raise_if_response_failed(event)
                    break

        audio_mp3 = self._pcm_to_mp3(b"".join(audio_chunks), sample_rate=24000) if audio_chunks else None
        text_response = "".join(text_chunks).strip() or None

        return _UnifiedResult(
            contains_wake_word=bool(cmd_args.get("contains_wake_word", False)),
            command=cmd_args.get("command") or "unknown",
            parameters=cmd_args.get("parameters") or {},
            audio_response=audio_mp3,
            audio_streamed=self.on_audio_delta is not None,
            text_response=text_response,
            transcript=cmd_args.get("transcript") or None,
        )

    def transcribe_text(self, text: str, face_names: str = "") -> "_UnifiedResult":
        if self._loop is None or not self._ready.is_set():
            return _UnifiedResult(contains_wake_word=False, command=None, transcript=text)
        fut = asyncio.run_coroutine_threadsafe(
            self._turn_text(text, face_names), self._loop
        )
        try:
            return fut.result(timeout=30)
        except Exception as exc:
            self._log_error(f"OpenAI Realtime text turn failed, reconnecting: {type(exc).__name__}: {exc}")
            self._schedule_reconnect()
            return _UnifiedResult(contains_wake_word=False, command=None, transcript=text)

    async def _turn_text(self, text: str, face_names: str = "") -> "_UnifiedResult":
        conn = self._session
        if conn is None:
            return _UnifiedResult(contains_wake_word=False, command=None, transcript=text)
        await self._add_face_context(conn, face_names)

        await conn.conversation.item.create(item={
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": text}],
        })
        # First response: tool call only, no spoken filler — see _turn().
        await conn.response.create(response={
            "output_modalities": ["text"],
            # Classification only, never spoken — the same minimal effort the
            # spoken response below already asks for. This is pure latency on
            # the critical path: nothing can be heard until it completes.
            "reasoning": {"effort": "minimal"},
        })

        cmd_args: dict = {}
        tool_call_id: str | None = None

        async for event in conn:
            etype = getattr(event, "type", "")
            if etype == "response.function_call_arguments.done":
                try:
                    args = json.loads(event.arguments)
                except Exception:
                    args = {}
                fname = getattr(event, "name", "") or ""
                call_id = getattr(event, "call_id", None)
                if fname:
                    cmd_args, tool_call_id = args, call_id
            elif etype == "error":
                raise RuntimeError(f"Realtime API error: {self._describe_event_error(event)}")
            elif etype == "response.done":
                self._raise_if_response_failed(event)
                break

        # Second response: the actual spoken acknowledgement ("Ok, <Action> now").
        # Look before speaking, so the reply describes what the robot can actually
        # see. The request arrives as a field on parse_speech_command rather than a
        # second tool: tool_choice is "required", which the model satisfies with one
        # call, so a separate look tool was never invoked (observed: look_around=0
        # even when asked point blank to look around).
        if cmd_args.get("needs_look") and self.on_look is not None:
            try:
                observation, image_url = self.on_look(
                    cmd_args.get("look_query") or cmd_args.get("transcript", "")
                )
            except Exception as e:
                observation, image_url = f"the camera is unavailable ({e})", None
            await conn.conversation.item.create(item={
                "type": "message", "role": "user",
                "content": [{
                    "type": "input_text",
                    "text": "Camera observation: " + (observation or "no view available"),
                }],
            })
            # The richest path attaches the frame itself and lets the model look.
            if image_url:
                await conn.conversation.item.create(item={
                    "type": "message", "role": "user",
                    "content": [{"type": "input_image", "image_url": image_url}],
                })

        # Gated on the wake word, not just on there being a tool call: the reply
        # is streamed to the speaker as it is produced, so generating it for an
        # utterance we were not addressed with would make the robot answer
        # overheard conversation. _handle_unified's wake-word check runs only
        # after the audio would already have been heard. Skipping it also saves
        # a whole API round trip on every stray utterance.
        audio_chunks: list[bytes] = []
        text_chunks: list[str] = []
        if tool_call_id and cmd_args.get("contains_wake_word"):
            await conn.conversation.item.create(item={
                "type": "function_call_output",
                "call_id": tool_call_id,
                "output": json.dumps({"status": "ok"}),
            })
            # Spoken reply: no reasoning — neither the fixed ack nor casual chat needs it.
            await conn.response.create(response={
                "reasoning": {"effort": "minimal"},
                "tool_choice": "none",  # must not call the tool again — just speak the reply
            })
            async for event in conn:
                etype = getattr(event, "type", "")
                if etype == "response.output_audio.delta":
                    chunk = getattr(event, "delta", b"")
                    if isinstance(chunk, str):
                        import base64 as _b64i
                        chunk = _b64i.b64decode(chunk)
                    if self.on_audio_delta is not None:
                        self.on_audio_delta(chunk)
                    else:
                        audio_chunks.append(chunk)
                elif etype == "response.output_audio_transcript.delta":
                    text_chunks.append(getattr(event, "delta", ""))
                elif etype == "error":
                    raise RuntimeError(f"Realtime API error: {self._describe_event_error(event)}")
                elif etype == "response.done":
                    self._raise_if_response_failed(event)
                    break

        audio_mp3 = self._pcm_to_mp3(b"".join(audio_chunks), sample_rate=24000) if audio_chunks else None
        return _UnifiedResult(
            contains_wake_word=bool(cmd_args.get("contains_wake_word", False)),
            command=cmd_args.get("command") or "unknown",
            parameters=cmd_args.get("parameters") or {},
            audio_response=audio_mp3,
            audio_streamed=self.on_audio_delta is not None,
            text_response="".join(text_chunks).strip() or None,
            transcript=text,
        )

    @staticmethod
    def _pcm_to_mp3(pcm: bytes, sample_rate: int = 24000) -> bytes | None:
        try:
            from pydub import AudioSegment
            seg = AudioSegment(data=pcm, sample_width=2, frame_rate=sample_rate, channels=1)
            buf = io.BytesIO()
            seg.export(buf, format="mp3")
            return buf.getvalue()
        except Exception:
            return None


# ---------------------------------------------------------------------------
# _GeminiLiveBackend — persistent WebSocket: audio → function call + PCM audio
# ---------------------------------------------------------------------------

class _GeminiLiveBackend:
    """Gemini 3.1 Flash Live via google.genai async client.

    Maintains a persistent session.  Each utterance is sent as PCM audio;
    the model calls parse_speech_command() and generates an audio response.

    Returns _UnifiedResult with audio_response set; text_response is None.
    """

    _TOOL_DECL = None   # built lazily after google.genai import

    def __init__(self, api_key: str, model: str, wake_word: str = "", language: str = "en"):
        self._api_key = api_key
        self._model = model or "gemini-3.1-flash-live-preview"
        self._wake_word = wake_word
        self._language = language
        self._session = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ready = threading.Event()

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        asyncio.run_coroutine_threadsafe(self._connect(), loop)

    async def _connect(self) -> None:
        try:
            from google import genai
            from google.genai import types as gt
            client = genai.Client(api_key=self._api_key)

            tool = gt.Tool(function_declarations=[
                gt.FunctionDeclaration(
                    name="parse_speech_command",
                    description="Extract robot command and wake-word status from speech.",
                    parameters=gt.Schema(
                        type=gt.Type.OBJECT,
                        properties={
                            "transcript": gt.Schema(
                                type=gt.Type.STRING,
                                description="Verbatim transcription of what was spoken.",
                            ),
                            "contains_wake_word": gt.Schema(type=gt.Type.BOOLEAN),
                            "command": gt.Schema(
                                type=gt.Type.STRING,
                                description=(
                                    "Robot command name or 'unknown'. Valid values: "
                                    "sit, stand, balance, stretch, recover, stop, "
                                    "raise_body, lower_body, trot, crawl, stand_gait, "
                                    "rest_gait, slow_speed, normal_speed, fast_speed, "
                                    "forward, backward, turn_left, turn_right, stop_move, "
                                    "keep_forward, keep_backward, keep_turn_left, "
                                    "keep_turn_right, hello, dance1, dance2, front_flip, "
                                    "wiggle_hips, finger_heart, handstand, moon_walk, "
                                    "continuous_gait, auto_rest"
                                ),
                            ),
                        },
                        required=["transcript", "contains_wake_word", "command"],
                    ),
                )
            ])

            config = gt.LiveConnectConfig(
                response_modalities=["AUDIO"],
                output_audio_transcription=gt.AudioTranscriptionConfig(),
                tools=[tool],
                system_instruction=(
                    f"You are GO2, a quadruped robot. Wake word: '{self._wake_word}'. "
                    f"The speaker is speaking {language_name(self._language)}. "
                    "Always call parse_speech_command() first. "
                    "Then respond with a short spoken acknowledgement or reply (1–2 sentences). "
                    "No markdown."
                ),
            )

            async with client.aio.live.connect(model=self._model, config=config) as session:
                self._session = session
                self._ready.set()
                await asyncio.Future()
        except Exception:
            pass

    def transcribe(self, audio_bytes: bytes, sample_rate: int) -> "_UnifiedResult":
        if self._loop is None or not self._ready.is_set():
            return _UnifiedResult(contains_wake_word=False, command=None)
        fut = asyncio.run_coroutine_threadsafe(
            self._turn(audio_bytes, sample_rate), self._loop
        )
        try:
            return fut.result(timeout=30)
        except Exception:
            return _UnifiedResult(contains_wake_word=False, command=None)

    async def _turn(self, audio_bytes: bytes, sample_rate: int = 16000) -> "_UnifiedResult":
        session = self._session
        if session is None:
            return _UnifiedResult(contains_wake_word=False, command=None)

        # Send PCM audio. The rate must be declared in the mime_type — Live API
        # assumes 16 kHz otherwise, so an actual rate mismatch plays back pitch-
        # shifted / at the wrong speed on the model's side.
        await session.send_client_content(
            turns=[{"role": "user", "parts": [
                {"inline_data": {
                    "mime_type": f"audio/pcm;rate={sample_rate}",
                    "data": base64.b64encode(audio_bytes).decode(),
                }}
            ]}],
            turn_complete=True,
        )

        cmd_args: dict = {}
        audio_chunks: list[bytes] = []
        text_chunks: list[str] = []

        async for response in session.receive():
            sc = getattr(response, "server_content", None)
            if sc is None:
                continue
            # Function call — extract command args and send tool response
            if sc.tool_calls:
                for tc in sc.tool_calls:
                    if tc.name == "parse_speech_command":
                        cmd_args = dict(tc.args) if tc.args else {}
                        await session.send_tool_response(function_responses=[{
                            "name": "parse_speech_command",
                            "id": tc.id,
                            "response": {"output": {"status": "ok"}},
                        }])
            # Audio chunks
            if sc.model_turn:
                for part in sc.model_turn.parts:
                    if hasattr(part, "inline_data") and part.inline_data:
                        audio_chunks.append(part.inline_data.data)
            # Text transcript of the audio response (output_audio_transcription)
            if getattr(sc, "output_transcription", None):
                t = getattr(sc.output_transcription, "text", None)
                if t:
                    text_chunks.append(t)
            if sc.turn_complete:
                break

        audio_mp3 = self._pcm_to_mp3(b"".join(audio_chunks), sample_rate=24000) if audio_chunks else None
        text_response = "".join(text_chunks).strip() or None

        return _UnifiedResult(
            contains_wake_word=bool(cmd_args.get("contains_wake_word", False)),
            command=cmd_args.get("command") or "unknown",
            audio_response=audio_mp3,
            text_response=text_response,
            transcript=cmd_args.get("transcript") or None,
        )

    def transcribe_text(self, text: str) -> "_UnifiedResult":
        if self._loop is None or not self._ready.is_set():
            return _UnifiedResult(contains_wake_word=False, command=None, transcript=text)
        fut = asyncio.run_coroutine_threadsafe(self._turn_text(text), self._loop)
        try:
            return fut.result(timeout=30)
        except Exception:
            return _UnifiedResult(contains_wake_word=False, command=None, transcript=text)

    async def _turn_text(self, text: str) -> "_UnifiedResult":
        session = self._session
        if session is None:
            return _UnifiedResult(contains_wake_word=False, command=None, transcript=text)

        await session.send_client_content(
            turns=[{"role": "user", "parts": [{"text": text}]}],
            turn_complete=True,
        )

        cmd_args: dict = {}
        audio_chunks: list[bytes] = []
        text_chunks: list[str] = []

        async for response in session.receive():
            sc = getattr(response, "server_content", None)
            if sc is None:
                continue
            if sc.tool_calls:
                for tc in sc.tool_calls:
                    if tc.name == "parse_speech_command":
                        cmd_args = dict(tc.args) if tc.args else {}
                        await session.send_tool_response(function_responses=[{
                            "name": "parse_speech_command",
                            "id": tc.id,
                            "response": {"output": {"status": "ok"}},
                        }])
            if sc.model_turn:
                for part in sc.model_turn.parts:
                    if hasattr(part, "inline_data") and part.inline_data:
                        audio_chunks.append(part.inline_data.data)
            if getattr(sc, "output_transcription", None):
                t = getattr(sc.output_transcription, "text", None)
                if t:
                    text_chunks.append(t)
            if sc.turn_complete:
                break

        audio_mp3 = self._pcm_to_mp3(b"".join(audio_chunks), sample_rate=24000) if audio_chunks else None
        return _UnifiedResult(
            contains_wake_word=bool(cmd_args.get("contains_wake_word", False)),
            command=cmd_args.get("command") or "unknown",
            audio_response=audio_mp3,
            text_response="".join(text_chunks).strip() or None,
            transcript=text,
        )

    @staticmethod
    def _pcm_to_mp3(pcm: bytes, sample_rate: int = 24000) -> bytes | None:
        try:
            from pydub import AudioSegment
            seg = AudioSegment(data=pcm, sample_width=2, frame_rate=sample_rate, channels=1)
            buf = io.BytesIO()
            seg.export(buf, format="mp3")
            return buf.getvalue()
        except Exception:
            return None


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
        # Separate from gemma_model on purpose. GEMMA_MODEL names the llama.cpp
        # model for gemma_local; reusing it for the hosted realtime providers
        # meant a box configured with GEMMA_MODEL=gemma-4-12b would hand that
        # string to OpenAI as a model name and fail every turn. Empty means
        # "use the provider's default".
        self.declare_parameter("realtime_model", "")
        self.declare_parameter("wake_word", "doggo")
        # Noise-adaptive VAD + high-pass filter (speech_processor.audio_vad,
        # shared with stt_node.py). vad_threshold is kept as a legacy no-op
        # declared parameter so existing launch configs overriding it don't
        # error on an unknown parameter; it's no longer read.
        self.declare_parameter("vad_threshold", 0.04)
        # Measured on a USB mic (MUSIC-BOOST MB-306): ambient frame RMS median
        # 0.0103 / max 0.0145, so a 1.5x multiplier put the trigger at 0.0155 --
        # only 6% above the loudest ambient frame. The VAD fired constantly on
        # room noise and shipped empty utterances to the STT backend (billable, on
        # cloud providers). 2.5x gives ~1.8x headroom here and still sits far
        # below speech, which runs several times the noise floor. Prefer tuning
        # this over absolute_floor: the multiplier scales with whatever mic is
        # attached, a fixed floor does not.
        self.declare_parameter("vad_noise_multiplier", 2.5)
        self.declare_parameter("vad_absolute_floor", 0.003)
        self.declare_parameter("vad_noise_ema_alpha", 0.05)
        self.declare_parameter("highpass_cutoff_hz", 150.0)
        self.declare_parameter("silence_duration", 0.640)  # 5 × 128 ms chunks
        self.declare_parameter("max_utterance_duration", 20.0)
        self.declare_parameter("sample_rate", 16000)
        # Robot mic input option (in addition to the default browser mic) --
        # lets Path C (openai_realtime/gemini_live, which only runs through
        # this node, never stt_node) use the robot's onboard mic instead of
        # requiring the operator's own browser mic.
        self.declare_parameter("robot_audio_topic", "/robot_audio")
        # Capture a microphone attached to this machine (Bluetooth headset first,
        # then USB) through the host's PulseAudio, re-checked every
        # source_probe_interval seconds so plugging one in takes effect live.
        self.declare_parameter("local_mic", False)
        # look_around: which visual path to prefer, cheapest-capable first.
        self.declare_parameter("look_path_priority", ",".join(DEFAULT_PATH_PRIORITY))
        self.declare_parameter("camera_topic", "/camera/image_raw")
        self.declare_parameter("vision_ttl", 5.0)
        # Stream the spoken reply to a local speaker as the model produces it,
        # instead of waiting for the whole answer. Only applies when such a sink
        # exists; otherwise the reply goes to the robot speaker as before.
        self.declare_parameter("stream_audio", True)
        self.declare_parameter("stream_sink_pattern", "bluez_sink")
        self.declare_parameter("pulse_source_priority", ",".join(AUDIO_SOURCE_PRIORITY))
        self.declare_parameter("source_probe_interval", 10.0)
        # Command dispatch params (used by unified backends)
        self.declare_parameter("cmd_topic", "/webrtc_req")
        self.declare_parameter("move_duration", 2.0)
        self.declare_parameter("linear_speed", 0.3)
        self.declare_parameter("angular_speed", 0.5)
        self.declare_parameter("greet_cooldown_sec", 60.0)
        self.declare_parameter("face_context_ttl", 30.0)

        http_port    = int(self.get_parameter("http_port").value)
        ws_port      = int(self.get_parameter("ws_port").value)
        provider     = self.get_parameter("stt_provider").value
        model_size   = self.get_parameter("whisper_model").value
        device       = self.get_parameter("device").value
        compute_type = self.get_parameter("compute_type").value
        language     = self.get_parameter("language").value
        self._language = language        # used by the TTS-pipe synthesizer (_tts_to_pcm)
        api_key      = self.get_parameter("api_key").value
        llama_cpp_host = self.get_parameter("llama_cpp_host").value
        gemma_model    = self.get_parameter("gemma_model").value
        self._wake_word = self.get_parameter("wake_word").value
        cmd_topic    = self.get_parameter("cmd_topic").value
        move_dur     = float(self.get_parameter("move_duration").value)
        lin_speed    = float(self.get_parameter("linear_speed").value)
        ang_speed    = float(self.get_parameter("angular_speed").value)

        self._silence   = float(self.get_parameter("silence_duration").value)
        self._max_utt   = float(self.get_parameter("max_utterance_duration").value)
        self._rate      = int(self.get_parameter("sample_rate").value)
        self._is_sim    = (cmd_topic == "/sim_cmd")
        self._vad_noise_multiplier = float(self.get_parameter("vad_noise_multiplier").value)
        self._vad_absolute_floor = float(self.get_parameter("vad_absolute_floor").value)
        self._vad_noise_ema_alpha = float(self.get_parameter("vad_noise_ema_alpha").value)
        self._highpass_cutoff_hz = float(self.get_parameter("highpass_cutoff_hz").value)
        robot_audio_topic = self.get_parameter("robot_audio_topic").value

        # Per-connection state for robot-vs-browser mic selection. Keyed by
        # websocket object; each entry is {"source": "browser"|"robot",
        # "vad": SegmentingVAD} -- one VAD instance per connection so two
        # simultaneously-open browser tabs never share noise-floor/filter
        # state. Populated in _handler() on connect, discarded on disconnect.
        self._conn_audio: dict = {}

        def _new_vad() -> SegmentingVAD:
            return SegmentingVAD(
                sample_rate=self._rate,
                noise_multiplier=self._vad_noise_multiplier,
                absolute_floor=self._vad_absolute_floor,
                noise_ema_alpha=self._vad_noise_ema_alpha,
                silence_duration_s=self._silence,
                highpass_cutoff_hz=self._highpass_cutoff_hz,
                max_utterance_s=self._max_utt,
            )
        self._new_vad = _new_vad

        self.create_subscription(
            UInt8MultiArray, robot_audio_topic, self._on_robot_audio, qos_profile_sensor_data
        )
        # Robot-mic mode has no client-side equivalent of the browser JS's
        # isTtsSpeaking mute -- the robot's own mic hears its own speaker
        # (strong direct acoustic coupling, same chassis), so without this
        # the robot reacts to its own spoken replies and cascades into
        # unrequested actions. tts_node.py publishes this bracketing actual
        # playback (see its _play_and_signal()); _on_robot_audio() checks
        # it before feeding any connection's VAD.
        self._tts_playing = False
        self._tts_mute_until = 0.0  # monotonic time; short cooldown after playback ends
        self.create_subscription(Bool, "/tts_playing", self._on_tts_playing, 10)

        # Local microphone (Bluetooth headset > USB mic), captured through the
        # host's PulseAudio. This is what lets the unified backends -- which
        # only run in this node -- use a real microphone instead of being
        # limited to the browser bridge or the robot's own noisy mic.
        self._local_mic_client = None
        if self.get_parameter("local_mic").value:
            self._pulse_priority = tuple(
                frag.strip()
                for frag in self.get_parameter("pulse_source_priority").value.split(",")
                if frag.strip()
            )
            self._source_probe_interval = float(
                self.get_parameter("source_probe_interval").value
            )
            self._local_mic_client = _LocalMicClient()
            self._conn_audio[self._local_mic_client] = {
                "source": "local", "listening": True, "vad": self._new_vad(),
            }
            threading.Thread(target=self._local_mic_loop, daemon=True).start()
            self.get_logger().info(
                "Local mic enabled — "
                f"{' > '.join(self._pulse_priority)} > robot mic ({robot_audio_topic})"
            )

        # Pure-STT path: publishes /speech_text → voice_cmd_node
        self._pub = self.create_publisher(String, "/speech_text", 10)
        # Unified path: publishes commands + TTS directly
        self._webrtc_pub = self.create_publisher(WebRtcReq, cmd_topic, 10)
        self._cmdvel_pub = self.create_publisher(Twist, "/cmd_vel_voice", 10)
        self._tts_pub    = self.create_publisher(String, "/tts", 10)
        # Proactive greeting (Modul 4.4): unified-provider setups (this node's own
        # CommandDispatcher) bypass voice_cmd_node entirely, so voice_cmd_node's own
        # /recognized_face_names greeting never fires here -- needs the same hook on
        # this node. Fires the moment a known face is (re-)seen after the cooldown,
        # independent of the person speaking first.
        self._greet_cooldown_sec = float(self.get_parameter("greet_cooldown_sec").value)
        self._greeted_names: dict = {}  # name -> monotonic time of last proactive greeting
        # Monotonic time of the last wake-word-confirmed exchange. Feeds the same
        # cooldown as _greeted_names so conversing suppresses greetings. Only
        # wake-word-confirmed speech counts -- in robot-mic mode the VAD fires on
        # ambient room chatter, which would otherwise mute greetings permanently.
        self._last_interaction_ts = 0.0
        # Latest sighting, also used to address the speaker by name in replies and
        # command feedback. Treated as gone once older than face_context_ttl, so a
        # departed visitor is never named at someone else.
        self._latest_faces = ""
        self._faces_ts = 0.0
        self._face_context_ttl = float(self.get_parameter("face_context_ttl").value)
        self.create_subscription(String, "/recognized_face_names", self._on_faces, 10)
        # Path C (openai_realtime/gemini_live) speaks via pre-synthesized
        # audio_response bytes, bypassing tts_node.py's /tts text pipeline
        # entirely -- so it needs its own way to reach the robot speaker.
        # tts_node.py subscribes to this and plays the bytes as-is (no
        # re-synthesis), same as /tts_audio but robot-only (browser already
        # gets this audio directly via _on_tts_audio below).
        self._robot_speaker_pub = self.create_publisher(UInt8MultiArray, "/robot_speaker_audio", 10)
        # Streamed playback bypasses tts_node, so nothing else would bracket it
        # with /tts_playing -- without this the robot hears its own reply through
        # the local mic and reacts to it.
        self._tts_playing_pub = self.create_publisher(Bool, "/tts_playing", 10)

        # ---- look_around inputs ------------------------------------------
        # Each path is used only if its data is fresh: a detection or scene
        # description from a minute ago describes a room the robot has since
        # walked out of, and answering from it would be worse than admitting
        # it cannot see.
        self._bridge = CvBridge() if _CV_AVAILABLE else None
        self._last_frame = None
        self._last_frame_ts = 0.0
        self._last_dets: list = []
        self._last_dets_ts = 0.0
        self._last_scene = ""
        self._last_scene_ts = 0.0
        self._look_priority = tuple(
            p.strip()
            for p in self.get_parameter("look_path_priority").value.split(",")
            if p.strip()
        ) or DEFAULT_PATH_PRIORITY
        self._vision_ttl = float(self.get_parameter("vision_ttl").value)
        self.create_subscription(
            Image, self.get_parameter("camera_topic").value,
            self._on_camera, qos_profile_sensor_data,
        )
        self.create_subscription(
            Detection2DArray, "/detected_objects", self._on_detections,
            qos_profile_sensor_data,
        )
        self.create_subscription(
            String, "/scene_description", self._on_scene, 10
        )

        self._audio_queue: queue.Queue = queue.Queue()
        self._audio_generation: int = 0   # incremented on each audio enqueue; used for latest-wins
        self._ws_loop: asyncio.AbstractEventLoop | None = None
        self._ws_clients: set = set()

        # TTS pipe state — Supertonic model is pre-loaded at startup
        self._tts_pipe_lock = threading.Lock()
        self._tts_pipe_synth = None
        self._tts_pipe_style = None
        self._warmup_tts_pipe()   # background load; ready before first button press

        self.create_subscription(UInt8MultiArray, "/tts_audio", self._on_tts_audio, 10)

        self._backend = self._build_backend(
            provider, api_key, model_size, device, compute_type, language,
            llama_cpp_host, gemma_model, self._wake_word,
            realtime_model=self.get_parameter("realtime_model").value,
        )
        # Pre-load model in background so the first real utterance isn't delayed
        if hasattr(self._backend, "warmup"):
            self._backend.warmup()
        # Routing for look_around lives in the node, which owns the camera and
        # detection topics; the backend just calls back into it.
        if hasattr(self._backend, "on_look"):
            self._backend.on_look = self._perform_look

        # HTTPS/WSS so getUserMedia() (mic access) works from a LAN client,
        # not just localhost -- see tls_cert.py. Falls back to plain HTTP/WS
        # (old behaviour, localhost-only mic access) if cert generation fails.
        self._tls_ctx = get_server_context()
        ws_scheme = "wss" if self._tls_ctx else "ws"
        if self._tls_ctx is None:
            self.get_logger().warn(
                "MicBridge: TLS cert generation failed -- falling back to plain "
                "HTTP/WS. Browser mic access will only work from localhost."
            )
        self._html = _HTML_TEMPLATE.format(ws_port=ws_port, ws_scheme=ws_scheme).encode("utf-8")

        # CommandDispatcher is created for unified providers so they can execute commands
        self._dispatcher: CommandDispatcher | None = None
        if isinstance(self._backend, (_GemmaUnifiedBackend, _OpenAIRealtimeBackend, _GeminiLiveBackend)):
            self._dispatcher = CommandDispatcher(
                cmd_pub=self._webrtc_pub, vel_pub=self._cmdvel_pub,
                lin_speed=lin_speed, ang_speed=ang_speed,
                move_dur=move_dur, is_sim=self._is_sim, node=self,
            )

        threading.Thread(target=self._process_loop, daemon=True).start()
        threading.Thread(target=self._run_http_server, args=(http_port,), daemon=True).start()
        threading.Thread(target=self._run_ws_server, args=(ws_port,), daemon=True).start()

        if self._tls_ctx:
            self.get_logger().info(
                f"mic_bridge_node ready — open https://localhost:{http_port} in your host "
                "browser (self-signed cert: click through the one-time browser warning)"
            )
        else:
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
        wake_word: str = "doggo", realtime_model: str = "",
    ):
        if provider == "openai_realtime":
            self.get_logger().info(
                f"MicBridge: OpenAI Realtime ({realtime_model or 'gpt-realtime-2.1'}) — unified pipeline"
            )
            backend = _OpenAIRealtimeBackend(
                api_key, realtime_model or "gpt-realtime-2.1", wake_word, language,
                logger=self.get_logger(),
            )
            return backend   # .start() called after ws_loop is ready
        elif provider == "gemini_live":
            self.get_logger().info(
                f"MicBridge: Gemini Live ({realtime_model or 'gemini-3.1-flash-live-preview'}) — unified pipeline"
            )
            backend = _GeminiLiveBackend(
                api_key, realtime_model, wake_word, language
            )
            return backend   # .start() called after ws_loop is ready
        elif provider == "gemma_local":
            self.get_logger().info(
                f"MicBridge: Gemma unified ({gemma_model} via {llama_cpp_host}) — unified pipeline"
            )
            return _GemmaUnifiedBackend(llama_cpp_host, gemma_model, language, wake_word,
                                        logger=self.get_logger())
        elif provider == "openai":
            self.get_logger().info("MicBridge STT: OpenAI Whisper API")
            return _OpenAIBackend(api_key, language, wake_word)
        elif provider == "gemini":
            self.get_logger().info("MicBridge STT: Gemini (structured wake-word output)")
            return _GeminiBackend(api_key, language, wake_word)
        else:
            self.get_logger().info(
                f"MicBridge STT: faster-whisper ({model_size}, {device}, {compute_type})"
            )
            return _FasterWhisperBackend(model_size, device, compute_type, language, wake_word)

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
        if self._tls_ctx:
            server.socket = self._tls_ctx.wrap_socket(server.socket, server_side=True)
            self.get_logger().info(f"MicBridge HTTPS on port {port}")
        else:
            self.get_logger().info(f"MicBridge HTTP on port {port}")
        server.serve_forever()

    # ------------------------------------------------------------------
    # WebSocket server — receives Int16 PCM from the browser
    # ------------------------------------------------------------------

    def _run_ws_server(self, port: int) -> None:
        loop = asyncio.new_event_loop()
        self._ws_loop = loop
        asyncio.set_event_loop(loop)
        # Start persistent sessions for realtime backends now that the loop exists
        if isinstance(self._backend, (_OpenAIRealtimeBackend, _GeminiLiveBackend)):
            self._backend.start(loop)
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
            node._conn_audio[websocket] = {
                "source": "browser", "listening": False, "vad": node._new_vad()
            }

            try:
                async for message in websocket:
                    # Text input or protocol message from the browser
                    if isinstance(message, str):
                        text = message.strip()
                        if text:
                            if text.startswith('{'):
                                try:
                                    msg_obj = json.loads(text)
                                    if msg_obj.get("type") == "tts_pipe":
                                        pipe_text = (msg_obj.get("text") or "").strip()
                                        if pipe_text:
                                            node._enqueue_tts_pipe(pipe_text, websocket)
                                        continue
                                    if msg_obj.get("type") == "set_audio_source":
                                        node._set_audio_source(websocket, msg_obj.get("source"))
                                        continue
                                    if msg_obj.get("type") == "set_listening":
                                        node._set_listening(websocket, msg_obj.get("active"))
                                        continue
                                except Exception:
                                    pass
                            node._audio_queue.put(("text", text, websocket, time.monotonic()))
                        continue
                    if not message:
                        continue

                    # Robot-mic mode: /robot_audio feeds this connection's VAD
                    # via _on_robot_audio() instead. Ignore stray browser
                    # frames server-side too, in case the browser doesn't
                    # perfectly stop sending on mode switch. Also ignore
                    # frames while not "listening" (Start Talking not
                    # pressed) -- the client already gates its own sends on
                    # `streaming`, this is defense-in-depth.
                    conn = node._conn_audio.get(websocket)
                    if conn is None or conn["source"] != "browser" or not conn["listening"]:
                        continue

                    pcm = np.frombuffer(message, dtype=np.int16).astype(np.float32) / 32768.0
                    utterance = conn["vad"].feed(pcm)
                    if utterance:
                        node._audio_generation += 1
                        node._audio_queue.put(("audio", utterance, websocket, time.monotonic()))

            except Exception:
                pass
            finally:
                node._ws_clients.discard(websocket)
                node._conn_audio.pop(websocket, None)

            node.get_logger().info("Browser mic disconnected")

        async with websockets.serve(_handler, "0.0.0.0", port, ssl=self._tls_ctx):
            scheme = "WSS" if self._tls_ctx else "WebSocket"
            self.get_logger().info(f"MicBridge {scheme} on port {port}")
            await asyncio.Future()

    # ------------------------------------------------------------------
    # Robot mic → per-connection VAD (source toggle: browser vs robot)
    # ------------------------------------------------------------------

    # Longer than tts_node.py's own 0.6s _play_and_signal() cooldown -- that
    # value was borrowed from the browser path's laptop-speaker-to-laptop-mic
    # reverb tail, which is a shorter/different acoustic path than the
    # robot's own chassis-mounted speaker-to-mic coupling. Extra margin here
    # is cheap; a cascade of unrequested commands is not.
    _TTS_MUTE_COOLDOWN_S = 1.2

    def _on_tts_playing(self, msg: Bool) -> None:
        was_playing = self._tts_playing
        self._tts_playing = bool(msg.data)
        if was_playing and not self._tts_playing:
            self._tts_mute_until = time.monotonic() + self._TTS_MUTE_COOLDOWN_S
            # Fresh VAD for every connection currently listening on the robot
            # mic -- not just the mute-until timestamp. Without this, a
            # connection's noise floor stays whatever it was calibrated to
            # *before* the robot spoke, which may no longer match the
            # post-playback acoustic environment (room resonance, a mic
            # gain/filter interaction, etc.). SegmentingVAD's noise floor
            # only updates on frames judged non-speech -- if the stale floor
            # makes the threshold too permissive right as listening resumes,
            # the VAD can latch into "speaking" and stay there until a long
            # enough genuine silence gap happens to occur, silently
            # buffering everything in between (ambient noise, room chatter,
            # anything) into one utterance that then gets sent to OpenAI as
            # if the user had said it -- matching the observed symptom
            # exactly: unrequested commands appearing 9-15s after the
            # previous reply, not immediately after it.
            for conn in self._conn_audio.values():
                if conn["source"] in ("robot", "local"):
                    conn["vad"] = self._new_vad()

    def _on_faces(self, msg: String) -> None:
        """Proactively greet newly-seen known faces (Modul 4.4).

        face_recognition_node publishes comma-joined known names (Unknown
        already excluded). Cooldown-gated per name so a lingering visitor
        isn't re-greeted on every ~0.5s inference tick.
        """
        now = time.monotonic()
        # Always refresh the sighting: name-addressing depends on it even when
        # the greeting itself is suppressed below.
        self._latest_faces = msg.data.strip()
        self._faces_ts = now

        # Never greet mid-exchange. The robot is either speaking right now, or
        # the person is in an active back-and-forth with it -- a "Hello, Dito!"
        # dropped into either is an interruption, not a welcome.
        if self._tts_playing:
            return

        for name in (n.strip() for n in msg.data.split(",")):
            if not name:
                continue
            # The cooldown runs from the last greeting OR the last exchange,
            # whichever is more recent, so a long conversation keeps pushing the
            # next greeting out instead of firing one every cooldown period.
            reference = max(self._greeted_names.get(name, 0.0), self._last_interaction_ts)
            if reference and (now - reference) < self._greet_cooldown_sec:
                continue
            self._greeted_names[name] = now
            greeting = f"Hello, {name}!"
            self.get_logger().info(f"Proactive greeting: {greeting!r}")
            self._tts_pub.publish(String(data=greeting))

    def _current_face_names(self) -> str:
        """Names still considered in-sight, or "" once the sighting goes stale.

        Everything downstream (prompt grounding, feedback personalization)
        degrades to the pre-face behaviour on "", so this is safe to call
        whether or not face_recognition_node is running.
        """
        if not self._latest_faces:
            return ""
        if (time.monotonic() - self._faces_ts) > self._face_context_ttl:
            return ""
        return self._latest_faces

    def _face_kwargs(self) -> dict:
        """`face_names=` kwarg for backends that accept it, else an empty dict.

        Keeps the STT-only backends (faster_whisper / openai / gemini) callable
        with their unchanged signature instead of forcing the parameter on every
        backend class.
        """
        names = self._current_face_names()
        if names and isinstance(
            self._backend, (_GemmaUnifiedBackend, _OpenAIRealtimeBackend)
        ):
            return {"face_names": names}
        return {}

    def _on_robot_audio(self, msg: UInt8MultiArray) -> None:
        """Feed /robot_audio into every connection currently in robot-mic mode.

        Runs on the ROS callback thread. _audio_queue is a plain
        thread-safe queue.Queue (already written to from the WS thread
        elsewhere), so no asyncio bridging is needed to enqueue here --
        only sending back to a browser needs run_coroutine_threadsafe.
        """
        if not self._conn_audio:
            return
        # Mute while the robot's own speaker is active (+ short cooldown for
        # reverb) -- otherwise the robot hears itself and reacts to its own
        # spoken replies. See _tts_playing_pub's creation comment in
        # tts_node.py for why this exists.
        if self._tts_playing or time.monotonic() < self._tts_mute_until:
            return
        pcm_i16 = np.frombuffer(bytes(msg.data), dtype=np.int16)
        if pcm_i16.size == 0:
            return
        pcm = pcm_i16.astype(np.float32) / 32768.0
        for websocket, conn in list(self._conn_audio.items()):
            if conn["source"] != "robot" or not conn["listening"]:
                continue
            utterance = conn["vad"].feed(pcm)
            if utterance:
                self._audio_generation += 1
                self._audio_queue.put(("audio", utterance, websocket, time.monotonic()))

    def _best_pulse_source(self) -> str | None:
        """Best available local capture source, or None to use the robot mic."""
        try:
            result = subprocess.run(
                ["pactl", "list", "sources", "short"],
                capture_output=True, text=True, timeout=3.0,
            )
            if result.returncode == 0:
                return select_pulse_source(result.stdout, self._pulse_priority)
        except Exception as e:
            self.get_logger().debug(f"Audio source probe failed: {e}")
        return None

    def _start_parec(self, source: str):
        """Capture `source` via parec, feeding the local connection's VAD."""
        frame_bytes = int(self._rate * 0.03) * 2  # 30ms of s16le mono
        proc = subprocess.Popen(
            [
                "parec", f"--device={source}", "--format=s16le",
                f"--rate={self._rate}", "--channels=1", "--raw",
            ],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )

        def reader():
            conn = self._conn_audio.get(self._local_mic_client)
            while proc.poll() is None and conn is not None:
                data = proc.stdout.read(frame_bytes)
                if not data:
                    break
                # Same self-hearing guard the robot mic needs: a mic on this
                # machine picks up the robot's own speaker, and without this
                # the robot reacts to its own spoken replies.
                if self._tts_playing or time.monotonic() < self._tts_mute_until:
                    continue
                pcm = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                utterance = conn["vad"].feed(pcm)
                if utterance:
                    self._audio_generation += 1
                    self._audio_queue.put(
                        ("audio", utterance, self._local_mic_client, time.monotonic())
                    )

        threading.Thread(target=reader, daemon=True).start()
        return proc

    # ------------------------------------------------------------------
    # look_around: YOLO / on-board Gemma / attach the frame to the session
    # ------------------------------------------------------------------

    def _on_camera(self, msg: Image) -> None:
        """Keep only the newest frame; it is encoded on demand, not per frame."""
        self._last_frame = msg
        self._last_frame_ts = time.monotonic()

    def _on_detections(self, msg: Detection2DArray) -> None:
        out = []
        for d in msg.detections:
            if not d.results:
                continue
            hyp = d.results[0].hypothesis
            out.append(
                (hyp.class_id, float(hyp.score), float(d.bbox.center.position.x))
            )
        self._last_dets = out
        self._last_dets_ts = time.monotonic()

    def _on_scene(self, msg: String) -> None:
        self._last_scene = msg.data.strip()
        self._last_scene_ts = time.monotonic()

    def _frame_data_url(self, max_width: int = 640):
        """Newest frame as a JPEG data URL, downscaled to keep image tokens sane."""
        if not _CV_AVAILABLE or self._last_frame is None:
            return None
        try:
            img = self._bridge.imgmsg_to_cv2(self._last_frame, desired_encoding="bgr8")
            h, w = img.shape[:2]
            if w > max_width:
                img = cv2.resize(img, (max_width, int(h * max_width / w)))
            ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if not ok:
                return None
            return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()
        except Exception as e:
            self.get_logger().warn(f"Frame encode failed: {e}")
            return None

    def _perform_look(self, query: str):
        """Answer a look_around call from the cheapest path holding fresh data.

        Returns (observation_text, image_data_url|None). The OpenAI path returns
        an image rather than text -- the model reads the frame itself, which is
        the whole reason it beats a canned object list.
        """
        now = time.monotonic()

        def fresh(ts):
            return bool(ts) and (now - ts) < self._vision_ttl

        path = choose_visual_path(
            query,
            yolo_ok=fresh(self._last_dets_ts),
            openai_ok=fresh(self._last_frame_ts) and _CV_AVAILABLE,
            gemma_ok=fresh(self._last_scene_ts),
            priority=self._look_priority,
        )
        if path == "yolo":
            width = float(getattr(self._last_frame, "width", 0) or 640)
            dets = [(n, sc, cx / width) for n, sc, cx in self._last_dets]
            text = summarize_detections(dets, match_coco_classes(query) or None)
            self.get_logger().info(f"👁 look (yolo): {text}")
            return text, None
        if path == "gemma":
            self.get_logger().info(f"👁 look (gemma): {self._last_scene[:70]}")
            return self._last_scene, None
        if path == "openai":
            url = self._frame_data_url()
            if url:
                self.get_logger().info("👁 look (openai): frame attached")
                # Must not be empty: the tool output falls back to
                # "no view available" on a falsy string, which would tell the
                # model it is blind in the same breath as handing it the frame.
                return (
                    "The current camera frame is attached as an image in this "
                    "conversation. Describe what is actually visible in it.",
                    url,
                )
        self.get_logger().warn(f"👁 look: no visual source for {query!r}")
        return "the camera is not producing any images right now", None

    def _best_local_sink(self) -> str | None:
        """Local speaker to stream into, or None to use the robot speaker."""
        if not self.get_parameter("stream_audio").value:
            return None
        if not isinstance(self._backend, _OpenAIRealtimeBackend):
            return None
        try:
            result = subprocess.run(
                ["pactl", "list", "sinks", "short"],
                capture_output=True, text=True, timeout=3.0,
            )
            if result.returncode == 0:
                return find_bluetooth_sink(
                    result.stdout, self.get_parameter("stream_sink_pattern").value
                )
        except Exception as e:
            self.get_logger().debug(f"Sink probe failed: {e}")
        return None

    def _make_delta_sink(self):
        """(on_delta, finish) streaming PCM to a local speaker, or (None, None).

        paplay is spawned lazily on the first delta so a turn that produces no
        audio never opens the device. finish() reports whether anything played,
        so the caller can fall back to the robot speaker if nothing did.
        """
        sink = self._best_local_sink()
        if not sink:
            return None, None
        state = {}

        def on_delta(pcm: bytes) -> None:
            proc = state.get("proc")
            if proc is None:
                proc = subprocess.Popen(
                    [
                        "paplay", f"--device={sink}", "--raw",
                        "--format=s16le", "--rate=24000", "--channels=1",
                    ],
                    stdin=subprocess.PIPE, stderr=subprocess.DEVNULL,
                )
                state["proc"] = proc
                self._set_tts_playing(True)
                # Timestamp of the FIRST audio byte — the number that matters
                # for perceived latency, as opposed to the whole-reply time.
                self.get_logger().info(f"🔊 Streaming reply → {sink}")
            try:
                proc.stdin.write(pcm)
                proc.stdin.flush()
            except Exception:
                pass  # speaker vanished mid-reply; finish() reports the failure

        def finish() -> bool:
            proc = state.get("proc")
            if proc is None:
                return False
            try:
                proc.stdin.close()
                proc.wait(timeout=60)
            except Exception:
                proc.kill()
            finally:
                self._set_tts_playing(False)
            return True

        return on_delta, finish

    def _set_tts_playing(self, playing: bool) -> None:
        """Bracket streamed playback so the mic mutes, as tts_node does."""
        self._tts_playing_pub.publish(Bool(data=playing))
        self._tts_playing = playing
        if not playing:
            self._tts_mute_until = time.monotonic() + self._TTS_MUTE_COOLDOWN_S

    def _local_mic_loop(self) -> None:
        """Keep the highest-priority local microphone attached.

        Re-probes periodically so connecting a headset or plugging in a USB mic
        switches input live, and so a capture process dying (device unplugged
        mid-sentence) is recovered from instead of going silently deaf.
        """
        # Sentinel rather than None: on the first pass the best source may
        # legitimately be None, and `None != None` would skip the branch that
        # reports having fallen back to the robot mic.
        unset = object()
        current = unset
        proc = None
        while rclpy.ok():
            if proc is not None and proc.poll() is not None:
                self.get_logger().warn(f"Local mic capture from {current} ended")
                proc, current = None, unset

            best = self._best_pulse_source()
            if best != current:
                if proc is not None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=2)
                    except Exception:
                        proc.kill()
                    proc = None
                conn = self._conn_audio.get(self._local_mic_client)
                if conn is not None:
                    # Fresh VAD on switch — never carry a noise floor tuned for
                    # one microphone over to a different one.
                    conn["vad"] = self._new_vad()
                    conn["source"] = "local" if best else "robot"
                if best:
                    proc = self._start_parec(best)
                    self.get_logger().info(f"🎙 Audio input: {best}")
                else:
                    self.get_logger().info(
                        "🎙 Audio input: robot mic — no Bluetooth or USB mic"
                    )
                current = best
            time.sleep(self._source_probe_interval)

    def _set_listening(self, websocket, active) -> None:
        """Start Talking / Stop Talking, from either audio source.

        Robot-mic audio arrives via a ROS subscription, not a client push,
        so unlike the browser path (which the client already gates by
        simply not sending), there's no other way to stop /robot_audio from
        being fed into this connection's VAD when the operator isn't
        actively listening.
        """
        conn = self._conn_audio.get(websocket)
        if conn is None:
            return
        active = bool(active)
        if conn["listening"] != active:
            conn["listening"] = active
            if active:
                # Fresh VAD each time listening starts -- don't carry a
                # noise floor estimated during an arbitrarily long idle gap.
                conn["vad"] = self._new_vad()

    def _set_audio_source(self, websocket, source) -> None:
        if source not in ("browser", "robot"):
            return
        conn = self._conn_audio.get(websocket)
        if conn is None:
            return
        if conn["source"] != source:
            # Fresh VAD on switch -- don't carry noise-floor/filter state
            # tuned for one source over to a different one.
            conn["source"] = source
            conn["vad"] = self._new_vad()
            self.get_logger().info(f"Audio source switched to {source!r}")
            self._ws_send_json(websocket, {"type": "audio_source_ack", "source": source})

    # ------------------------------------------------------------------
    # TTS audio → browser
    # ------------------------------------------------------------------

    def _on_tts_audio(self, msg: UInt8MultiArray) -> None:
        self._broadcast_audio_to_browser(bytes(msg.data))

    def _broadcast_audio_to_browser(self, audio_bytes: bytes) -> None:
        """Send MP3 bytes to every connected browser client (played via playMp3())."""
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
    # Helpers
    # ------------------------------------------------------------------

    def _ws_send_json(self, websocket, data: dict) -> None:
        if self._ws_loop is None:
            return
        asyncio.run_coroutine_threadsafe(
            websocket.send(json.dumps(data)), self._ws_loop
        )

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

    _MAX_QUEUE_AGE = 5.0  # drop utterances older than this (seconds) — they're stale

    def _process_loop(self) -> None:
        while True:
            item = self._audio_queue.get()
            if item is None:
                break

            # Audio: drain the queue so only the most recent utterance is processed.
            # This prevents a backlog of stale commands building up while the LLM
            # is busy. Text items are saved and re-queued so they are not lost.
            if item[0] == "audio":
                saved_text: list = []
                skipped = 0
                while True:
                    try:
                        nxt = self._audio_queue.get_nowait()
                    except queue.Empty:
                        break
                    if nxt is None:
                        for t in saved_text:
                            self._audio_queue.put(t)
                        self._audio_queue.put(None)
                        return
                    if nxt[0] == "audio":
                        item = nxt
                        skipped += 1
                    else:
                        saved_text.append(nxt)
                for t in saved_text:
                    self._audio_queue.put(t)
                if skipped:
                    self.get_logger().info(
                        f"Audio: skipped {skipped} queued utterance(s), processing latest"
                    )
                gen_at_dequeue = self._audio_generation

            kind, payload, websocket, t_queued = item

            age = time.monotonic() - t_queued
            if age > self._MAX_QUEUE_AGE:
                self.get_logger().warn(
                    f"Dropped stale utterance ({age:.0f}s old) — queue backlog"
                )
                self._ws_send_json(websocket, {"type": "dropped", "age_s": round(age, 1)})
                continue

            if kind == "text":
                self._process_text_item(payload, websocket, t_queued)
                continue

            # Audio path (kind == "audio" from VAD, or "tts_audio" from TTS pipe)
            wav_bytes = self._wav_header(payload)
            t_request = time.monotonic()
            try:
                # Only _GemmaUnifiedBackend takes face context; the STT-only
                # backends keep their original two-arg signature.
                on_delta, finish = self._make_delta_sink()
                if on_delta is not None:
                    self._backend.on_audio_delta = on_delta
                streamed = False
                try:
                    result = self._backend.transcribe(
                        wav_bytes, self._rate, **self._face_kwargs()
                    )
                finally:
                    if on_delta is not None:
                        self._backend.on_audio_delta = None
                        streamed = finish()
                # finish() is False when the model produced no audio at all, so
                # nothing was heard and the normal publish path must still run.
                if not streamed:
                    result.audio_streamed = False
            except Exception as exc:
                self.get_logger().error(f"MicBridge transcription error: {exc}")
                continue

            t_stt = time.monotonic()

            # Discard if newer mic audio arrived while LLM was busy (latest-wins).
            # TTS-pipe audio bypasses this check — it was intentionally synthesized.
            if kind == "audio" and self._audio_generation != gen_at_dequeue:
                self.get_logger().info(
                    "Audio: newer command arrived during inference — discarding stale result"
                )
                continue

            queue_ms = (t_request - t_queued) * 1000
            infer_ms = (t_stt - t_request) * 1000
            input_type = "tts_pipe" if kind == "tts_audio" else "audio"

            if isinstance(result, _UnifiedResult):
                self._handle_unified(result, websocket, t_queued, t_request, t_stt, input_type=input_type)
            else:
                # Pure-STT path: (transcript, wake_word_found)
                text, wake_word_found = result
                if not text:
                    continue
                self.get_logger().info(
                    f"MicBridge transcribed (queue {queue_ms:.0f} ms + infer {infer_ms:.0f} ms): {text!r}"
                )
                result_dict = {
                    "type": "transcript",
                    "input": input_type,
                    "transcript": text,
                    "contains_wake_word": wake_word_found,
                    "timing": {
                        "queue_ms": round(queue_ms),
                        "infer_ms": round(infer_ms),
                        "total_ms": round(queue_ms + infer_ms),
                    },
                }
                if not wake_word_found:
                    self.get_logger().info(
                        f"Ignored — no wake word '{self._wake_word}': {text!r}"
                    )
                    self._ws_send_json(websocket, result_dict)
                    continue
                self._pub.publish(String(data=text))
                self._ws_send_json(websocket, result_dict)

    def _process_text_item(self, text: str, websocket, t_queued: float) -> None:
        t_request = time.monotonic()

        # Unified backends: call transcribe_text → same _handle_unified path as audio
        if hasattr(self._backend, "transcribe_text"):
            try:
                result = self._backend.transcribe_text(text, **self._face_kwargs())
            except Exception as exc:
                self.get_logger().error(f"MicBridge text input error: {exc}")
                return
            t_stt = time.monotonic()
            self._handle_unified(result, websocket, t_queued, t_request, t_stt, input_type="text")
            return

        # Pure-STT backends: wake word check only (transcription not needed for typed text)
        wake_word_found = self._wake_word.lower() in text.lower() if self._wake_word else True
        result_dict = {
            "type": "transcript",
            "input": "text",
            "transcript": text,
            "contains_wake_word": wake_word_found,
        }
        if not wake_word_found:
            self.get_logger().info(f"Text input — no wake word: {text!r}")
            self._ws_send_json(websocket, result_dict)
            return
        self.get_logger().info(f"Text input — publishing to /speech_text: {text!r}")
        self._pub.publish(String(data=text))
        self._ws_send_json(websocket, result_dict)

    def _handle_unified(
        self, result: "_UnifiedResult", websocket,
        t_vad: float, t_request: float, t_stt: float,
        input_type: str = "audio",
    ) -> None:
        transcript = result.transcript or ""
        queue_ms = (t_request - t_vad) * 1000
        infer_ms = (t_stt - t_request) * 1000
        total_ms = (t_stt - t_vad) * 1000
        timing_log = f"queue {queue_ms:.0f} ms + infer {infer_ms:.0f} ms"

        _is_cmd = bool(result.command and result.command not in (None, "unknown"))
        out: dict = {
            "type": "result",
            "input": input_type,
            "tool_name": "execute_robot_command" if _is_cmd else "respond_conversationally",
            "transcript": transcript,
            "contains_wake_word": result.contains_wake_word,
            "command": result.command,
            "parameters": result.parameters,
            "text_response": result.text_response,
            "timing": {
                "queue_ms": round(queue_ms),
                "infer_ms": round(infer_ms),
                "total_ms": round(total_ms),
            },
        }

        if not result.contains_wake_word:
            self.get_logger().info(
                f"Unified ({timing_log}) — no wake word: {transcript!r}"
            )
            self._ws_send_json(websocket, out)
            return

        # Wake word confirmed — this is an exchange with the robot, so hold off
        # any proactive greeting from here (see _on_faces). Stamped again after
        # the reply goes out, since inference can take >10s on the Jetson and the
        # cooldown should run from the END of the exchange, not the start.
        self._last_interaction_ts = time.monotonic()

        # Dispatch command
        cmd = result.command
        if cmd and cmd != "unknown" and self._dispatcher is not None:
            action = CMD_MAP.get(cmd)
            if action is not None:
                t_cmd = time.monotonic()
                total_ms = (t_cmd - t_vad) * 1000
                out["timing"]["total_ms"] = round(total_ms)
                self.get_logger().info(
                    f"Unified ({timing_log} = {total_ms:.0f} ms total) "
                    f"— executing '{cmd}': {transcript!r}"
                )
                self._dispatcher.execute(action)
            else:
                self.get_logger().warn(f"Unified: unknown command key '{cmd}'")
        else:
            self.get_logger().info(
                f"Unified ({timing_log}) — no command: {transcript!r}"
            )

        # Forward TTS response (only if wake word was present)
        if result.audio_streamed:
            # Already spoken through the local speaker while it was generated.
            pass
        elif result.audio_response:
            audio_msg = UInt8MultiArray(data=list(result.audio_response))
            self._on_tts_audio(audio_msg)          # browser speaker
            self._robot_speaker_pub.publish(audio_msg)  # robot speaker
        elif result.text_response:
            spoken = result.text_response
            if _is_cmd:
                # Command feedback is a canned FEEDBACK_MAP string the model never
                # sees, so the recognized name has to be attached here. Conversational
                # replies are left alone -- the model already had the name in its
                # system prompt and worked it into the sentence itself.
                spoken = personalize_feedback(spoken, self._current_face_names())
            self.get_logger().info(f"Unified TTS: {spoken!r}")
            self._tts_pub.publish(String(data=spoken))
            out["text_response"] = spoken

        self._last_interaction_ts = time.monotonic()
        self._ws_send_json(websocket, out)

    # ------------------------------------------------------------------
    # TTS pipe — text → synthesized audio → audio pipeline
    # ------------------------------------------------------------------

    def _warmup_tts_pipe(self) -> None:
        """Pre-load the Supertonic model in a background thread at node startup."""
        def _load():
            try:
                with self._tts_pipe_lock:
                    if self._tts_pipe_synth is None:
                        from supertonic import TTS as _SupertonicTTS
                        self._tts_pipe_synth = _SupertonicTTS(auto_download=True)
                        self._tts_pipe_style = self._tts_pipe_synth.get_voice_style(voice_name="F1")
                self.get_logger().info("TTS pipe: Supertonic model loaded and ready")
            except Exception as exc:
                self.get_logger().error(f"TTS pipe warmup failed: {exc}")

        threading.Thread(target=_load, daemon=True, name="tts_pipe_warmup").start()

    def _enqueue_tts_pipe(self, text: str, websocket) -> None:
        """Synthesize `text` to PCM audio and queue it through the full audio pipeline.

        The result goes through `backend.transcribe()` exactly like real microphone
        audio — VAD framing is skipped since we have a complete utterance.
        Useful for end-to-end audio pipeline testing without a physical microphone.
        """
        self._ws_send_json(websocket, {"type": "tts_pipe_queued", "text": text})

        def _synth():
            pcm = self._tts_to_pcm(text)
            if pcm:
                self.get_logger().info(
                    f"TTS pipe: synthesized {len(pcm)//2} samples for: {text!r}"
                )
                # Play the synthesized audio in the browser NOW, in parallel with the
                # NLU pipeline: broadcast MP3 first (non-blocking), then queue the same
                # PCM for transcription/NLU. The browser hears the TTS while Gemma runs.
                try:
                    from pydub import AudioSegment
                    seg = AudioSegment(
                        data=pcm, sample_width=2, frame_rate=self._rate, channels=1
                    )
                    mp3_buf = io.BytesIO()
                    seg.export(mp3_buf, format="mp3")
                    self._broadcast_audio_to_browser(mp3_buf.getvalue())
                except Exception as exc:
                    self.get_logger().warn(f"TTS pipe browser playback failed: {exc}")
                self._audio_queue.put(("tts_audio", pcm, websocket, time.monotonic()))
            else:
                self.get_logger().error(f"TTS pipe synthesis failed for: {text!r}")
                self._ws_send_json(websocket, {"type": "tts_pipe_error", "text": text})

        threading.Thread(target=_synth, daemon=True, name="tts_pipe_synth").start()

    def _tts_to_pcm(self, text: str) -> bytes | None:
        """Synthesize `text` via Supertonic and return self._rate Hz mono Int16 raw PCM.

        The Supertonic model is lazy-loaded on first call and reused for subsequent
        calls — model load takes ~2s the first time, then is instant.
        Supertonic outputs float32 at 44.1kHz; pydub resamples to self._rate so the
        sample rate matches what backend.transcribe() expects.
        _process_loop adds the WAV header before calling transcribe().
        """
        import wave
        import numpy as np
        try:
            # Lazy-load Supertonic model under lock (called from background thread)
            with self._tts_pipe_lock:
                if self._tts_pipe_synth is None:
                    from supertonic import TTS as _SupertonicTTS
                    self._tts_pipe_synth = _SupertonicTTS(auto_download=True)
                    self._tts_pipe_style = self._tts_pipe_synth.get_voice_style(voice_name="F1")
            synth = self._tts_pipe_synth
            style = self._tts_pipe_style

            # Synthesize in the node's single configured language (VOICE_LANG → self._language,
            # e.g. "en" or "id"). A committed single language gives Supertonic a clean prior;
            # the old "na" auto-detect misread Indonesian command words as German.
            wav, _ = synth.synthesize(
                text=text,
                voice_style=style,
                lang=self._language,
                total_steps=16,   # higher than the 8 used for robot TTS: this is the
                                  # no-mic test path, so favour clearest audio for STT
                speed=1.0,        # natural rate — Gemma transcribes natural-rate speech
                                  # best; slowing this (e.g. 0.9) stretched the synthetic
                                  # Indonesian and made Gemma drop words / loop.
            )
            # wav is float32 at 44100Hz; convert to Int16 WAV then resample to self._rate
            pcm = (np.clip(wav, -1.0, 1.0) * 32767).astype(np.int16)
            wav_buf = io.BytesIO()
            with wave.open(wav_buf, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(44100)
                wf.writeframes(pcm.tobytes())
            wav_buf.seek(0)
            from pydub import AudioSegment
            seg = (
                AudioSegment.from_wav(wav_buf)
                .set_frame_rate(self._rate)
                .set_channels(1)
                .set_sample_width(2)
            )
            return seg.raw_data   # raw Int16 PCM — _process_loop adds the WAV header
        except Exception as exc:
            self.get_logger().error(f"_tts_to_pcm: {exc}")
            return None


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
