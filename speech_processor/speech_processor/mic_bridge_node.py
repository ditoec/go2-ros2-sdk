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
import json
import queue
import struct
import threading
import time

import numpy as np
import requests
import rclpy
from rclpy.node import Node
from std_msgs.msg import String, UInt8MultiArray
from geometry_msgs.msg import Twist
from go2_interfaces.msg import WebRtcReq

from .command_dispatcher import (
    CMD_MAP, LLAMA_SAMPLING, CommandDispatcher, build_unified_tools, coerce_command,
    coerce_str, command_for_text, feedback_for_action, language_name,
    system_prompt, system_prompt_text,
)


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
      // 2048-sample buffer = 128 ms at 16 kHz — tighter VAD granularity
      proc = audioCtx.createScriptProcessor(2048, 1, 1);
      proc.onaudioprocess = function(e) {{
        if (!streaming || ws.readyState !== 1 || isTtsSpeaking) return;
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
      show('textRow');
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
      var p = null;
      try {{ p = JSON.parse(e.data); }} catch(_) {{}}
      if (p) {{ renderResult(p); }}
      else {{ setStatus('\U0001f4ac ' + e.data); log('\U0001f4ac ' + e.data); }}
    }} else if (e.data instanceof ArrayBuffer && e.data.byteLength > 0) {{
      playMp3(e.data);
    }}
  }};

var isTtsSpeaking = false;
var _ttsUnmuteTimer = null;
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
    setStatus('Disconnected.');
    log('Connection closed');
    show('connectBtn');
    enable('connectBtn');
    hide('talkBtn');
    hide('discBtn');
    hide('textRow');
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
    """Gemma 4 E4B audio transcription via a local llama.cpp sidecar.

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

    def transcribe(self, audio_bytes: bytes, sample_rate: int) -> "_UnifiedResult":
        # Two attempts with DIFFERENT stop handling:
        #   attempt 0 — stop at "<|channel>thought" so a genuine cold-start reasoning
        #               loop fails fast (<1s) instead of running to n-predict.
        #   attempt 1 — NO stop. Some inputs (e.g. "duduk") always emit a short
        #               reasoning preamble before the forced tool call; stopping the
        #               retry too would cut the tool call and yield nothing. Without
        #               the stop the model finishes reasoning AND emits the tool call.
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        for attempt in range(2):
            try:
                body = {
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": self._system},
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

    def transcribe_text(self, text: str) -> "_UnifiedResult":
        try:
            resp = requests.post(
                f"{self._host}/v1/chat/completions",
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": self._system_text},
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
            },
            "required": ["transcript", "contains_wake_word", "command"],
        },
    }

    def __init__(self, api_key: str, model: str, wake_word: str = "", language: str = "en", logger=None):
        self._api_key = api_key
        self._model = model or "gpt-realtime-2.1"
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

    def transcribe(self, audio_bytes: bytes, sample_rate: int) -> "_UnifiedResult":
        if self._loop is None or not self._ready.is_set():
            return _UnifiedResult(contains_wake_word=False, command=None)
        fut = asyncio.run_coroutine_threadsafe(
            self._turn(audio_bytes), self._loop
        )
        try:
            return fut.result(timeout=30)
        except Exception as exc:
            self._log_error(f"OpenAI Realtime turn failed, reconnecting: {type(exc).__name__}: {exc}")
            self._schedule_reconnect()
            return _UnifiedResult(contains_wake_word=False, command=None)

    async def _turn(self, audio_bytes: bytes) -> "_UnifiedResult":
        import base64 as _b64
        conn = self._session
        if conn is None:
            return _UnifiedResult(contains_wake_word=False, command=None)

        # Send PCM audio as base64
        audio_b64 = _b64.b64encode(audio_bytes).decode()
        await conn.input_audio_buffer.append(audio=audio_b64)
        await conn.input_audio_buffer.commit()
        # First response: tool call only. Text-only modality so the model can't
        # also speak filler alongside the tool call — the spoken reply comes
        # entirely from the second response below, once the command is known.
        await conn.response.create(response={"output_modalities": ["text"]})

        cmd_args: dict = {}
        tool_call_id: str | None = None

        async for event in conn:
            etype = getattr(event, "type", "")
            if etype == "response.function_call_arguments.done":
                try:
                    cmd_args = json.loads(event.arguments)
                    tool_call_id = getattr(event, "call_id", None)
                except Exception:
                    pass
            elif etype == "error":
                raise RuntimeError(f"Realtime API error: {self._describe_event_error(event)}")
            elif etype == "response.done":
                self._raise_if_response_failed(event)
                break

        # Second response: the actual spoken acknowledgement ("Ok, <Action> now").
        audio_chunks: list[bytes] = []
        text_chunks: list[str] = []
        if tool_call_id:
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
            text_response=text_response,
            transcript=cmd_args.get("transcript") or None,
        )

    def transcribe_text(self, text: str) -> "_UnifiedResult":
        if self._loop is None or not self._ready.is_set():
            return _UnifiedResult(contains_wake_word=False, command=None, transcript=text)
        fut = asyncio.run_coroutine_threadsafe(self._turn_text(text), self._loop)
        try:
            return fut.result(timeout=30)
        except Exception as exc:
            self._log_error(f"OpenAI Realtime text turn failed, reconnecting: {type(exc).__name__}: {exc}")
            self._schedule_reconnect()
            return _UnifiedResult(contains_wake_word=False, command=None, transcript=text)

    async def _turn_text(self, text: str) -> "_UnifiedResult":
        conn = self._session
        if conn is None:
            return _UnifiedResult(contains_wake_word=False, command=None, transcript=text)

        await conn.conversation.item.create(item={
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": text}],
        })
        # First response: tool call only, no spoken filler — see _turn().
        await conn.response.create(response={"output_modalities": ["text"]})

        cmd_args: dict = {}
        tool_call_id: str | None = None

        async for event in conn:
            etype = getattr(event, "type", "")
            if etype == "response.function_call_arguments.done":
                try:
                    cmd_args = json.loads(event.arguments)
                    tool_call_id = getattr(event, "call_id", None)
                except Exception:
                    pass
            elif etype == "error":
                raise RuntimeError(f"Realtime API error: {self._describe_event_error(event)}")
            elif etype == "response.done":
                self._raise_if_response_failed(event)
                break

        # Second response: the actual spoken acknowledgement ("Ok, <Action> now").
        audio_chunks: list[bytes] = []
        text_chunks: list[str] = []
        if tool_call_id:
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
        self.declare_parameter("wake_word", "doggo")
        self.declare_parameter("vad_threshold", 0.04)
        self.declare_parameter("silence_duration", 0.640)  # 5 × 128 ms chunks
        self.declare_parameter("max_utterance_duration", 20.0)
        self.declare_parameter("sample_rate", 16000)
        # Command dispatch params (used by unified backends)
        self.declare_parameter("cmd_topic", "/webrtc_req")
        self.declare_parameter("move_duration", 2.0)
        self.declare_parameter("linear_speed", 0.3)
        self.declare_parameter("angular_speed", 0.5)

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

        self._vad_thr   = float(self.get_parameter("vad_threshold").value)
        self._silence   = float(self.get_parameter("silence_duration").value)
        self._max_utt   = float(self.get_parameter("max_utterance_duration").value)
        self._rate      = int(self.get_parameter("sample_rate").value)
        self._is_sim    = (cmd_topic == "/sim_cmd")

        # Pure-STT path: publishes /speech_text → voice_cmd_node
        self._pub = self.create_publisher(String, "/speech_text", 10)
        # Unified path: publishes commands + TTS directly
        self._webrtc_pub = self.create_publisher(WebRtcReq, cmd_topic, 10)
        self._cmdvel_pub = self.create_publisher(Twist, "/cmd_vel_voice", 10)
        self._tts_pub    = self.create_publisher(String, "/tts", 10)

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
        )
        # Pre-load model in background so the first real utterance isn't delayed
        if hasattr(self._backend, "warmup"):
            self._backend.warmup()
        self._html = _HTML_TEMPLATE.format(ws_port=ws_port).encode("utf-8")

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
        wake_word: str = "doggo",
    ):
        if provider == "openai_realtime":
            self.get_logger().info(
                f"MicBridge: OpenAI Realtime ({gemma_model or 'gpt-realtime-2.1'}) — unified pipeline"
            )
            backend = _OpenAIRealtimeBackend(
                api_key, gemma_model or "gpt-realtime-2.1", wake_word, language,
                logger=self.get_logger(),
            )
            return backend   # .start() called after ws_loop is ready
        elif provider == "gemini_live":
            self.get_logger().info(
                f"MicBridge: Gemini Live ({gemma_model or 'gemini-3.1-flash-live-preview'}) — unified pipeline"
            )
            backend = _GeminiLiveBackend(api_key, gemma_model, wake_word, language)
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

            voiced_frames: list[bytes] = []
            silent_frames = 0
            speaking = False
            # Thresholds are derived from the first frame's actual size so they
            # are correct regardless of the browser's ScriptProcessor buffer size.
            silence_needed: int = 3     # recalculated on first message
            max_voiced: int = 120       # recalculated on first message

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
                                except Exception:
                                    pass
                            node._audio_queue.put(("text", text, websocket, time.monotonic()))
                        continue
                    if not message:
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
                            node._audio_generation += 1
                            node._audio_queue.put(("audio", b"".join(voiced_frames), websocket, time.monotonic()))
                            voiced_frames = []
                            silent_frames = 0
                            speaking = False
                    elif speaking:
                        voiced_frames.append(raw)
                        silent_frames += 1
                        if silent_frames >= silence_needed:
                            node._audio_generation += 1
                            node._audio_queue.put(("audio", b"".join(voiced_frames), websocket, time.monotonic()))
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
                result = self._backend.transcribe(wav_bytes, self._rate)
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
                result = self._backend.transcribe_text(text)
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

        # Wake word confirmed — dispatch command
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
        if result.audio_response:
            audio_msg = UInt8MultiArray(data=list(result.audio_response))
            self._on_tts_audio(audio_msg)
        elif result.text_response:
            self.get_logger().info(f"Unified TTS: {result.text_response!r}")
            self._tts_pub.publish(String(data=result.text_response))

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
