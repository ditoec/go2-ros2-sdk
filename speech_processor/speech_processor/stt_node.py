#!/usr/bin/env python3

# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

"""
STT Node — speech-to-text for the GO2 robot.

Providers
---------
openai        : OpenAI Whisper API (Tier 1, internet required, same key as TTS OpenAI provider)
gemini        : Gemini 2.5 Flash (Tier 1, internet required, same key as TTS Gemini provider)
faster_whisper: CTranslate2 local inference — CUDA on Jetson NX gives ~30–60 ms per utterance
gemma_local   : Gemma 4 (12B or E4B) via llama.cpp sidecar (offline) — audio input
                projects directly into the text embedding space, no mmproj needed,
                so this works with either GEMMA_SIZE (mmproj is vision-only either way)

Audio is captured via sounddevice (ARM64 compatible, no PyAudio required).
A simple energy-threshold VAD buffers frames and fires the STT backend once
silence follows a voiced segment.

Published topic: /speech_text  (std_msgs/String)
"""

from __future__ import annotations

import base64
import io
import json
import queue
import subprocess
import threading
import time
from typing import Optional

import numpy as np
import requests
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from std_msgs.msg import String, UInt8MultiArray
from geometry_msgs.msg import Twist
from go2_interfaces.msg import WebRtcReq

from .audio_vad import AUDIO_SOURCE_PRIORITY, select_pulse_source

from .command_dispatcher import (
    CMD_MAP, LLAMA_SAMPLING, CommandDispatcher, build_unified_tools, coerce_command,
    coerce_str, command_for_text, feedback_for_action, language_name, system_prompt,
)
from .audio_vad import SegmentingVAD


# ---------------------------------------------------------------------------
# STT backend classes
# ---------------------------------------------------------------------------

class _OpenAIBackend:
    """Whisper API — same openai package used by TTSProvider_OpenAI."""

    def __init__(self, api_key: str, model: str, language: str, wake_word: str = ""):
        import openai
        self._client = openai.OpenAI(api_key=api_key)
        self._model = model      # "whisper-1"
        self._language = language
        self._wake_word = wake_word.lower()

    def transcribe(self, audio_bytes: bytes, sample_rate: int) -> tuple[str, bool]:
        import openai
        buf = io.BytesIO(audio_bytes)
        buf.name = "audio.wav"
        try:
            text = self._client.audio.transcriptions.create(
                model=self._model,
                file=buf,
                language=self._language,
            ).text.strip()
        except openai.OpenAIError:
            return "", False
        return text, (self._wake_word in text.lower()) if self._wake_word else True


class _FasterWhisperBackend:
    """Local CTranslate2 Whisper — offline, CUDA-accelerated on Jetson NX."""

    def __init__(self, model_size: str, device: str, compute_type: str, language: str, wake_word: str = ""):
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._language = language
        self._wake_word = wake_word.lower()
        self._model = None  # loaded on first transcribe() call

    def _load(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self._model_size, device=self._device, compute_type=self._compute_type
            )

    def transcribe(self, audio_bytes: bytes, sample_rate: int) -> tuple[str, bool]:
        self._load()
        audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        segments, _ = self._model.transcribe(audio_array, language=self._language, beam_size=1)
        text = " ".join(seg.text for seg in segments).strip()
        return text, (self._wake_word in text.lower()) if self._wake_word else True


class _GeminiBackend:
    """Gemini 2.5 Flash — returns structured JSON with transcript + wake-word flag."""

    def __init__(self, api_key: str, language: str, wake_word: str = ""):
        from google import genai
        from google.genai import types
        self._client = genai.Client(api_key=api_key)
        self._types = types
        self._language = language
        self._wake_word = wake_word

    def transcribe(self, audio_bytes: bytes, sample_rate: int) -> tuple[str, bool]:
        import os
        import tempfile
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            try:
                uploaded = self._client.files.upload(
                    path=tmp_path,
                    config={"mime_type": "audio/wav"},
                )
                prompt = (
                    f"Transcribe this audio. Language: {self._language}. "
                    f'Detect if the wake word "{self._wake_word}" appears anywhere '
                    "(case-insensitive). "
                    'Return ONLY a JSON object with keys "transcript" (string) and '
                    '"contains_wake_word" (boolean). No other text.'
                )
                response = self._client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[uploaded, prompt],
                    config=self._types.GenerateContentConfig(
                        response_mime_type="application/json",
                    ),
                )
                parsed = json.loads(response.text.strip())
                transcript = parsed.get("transcript", "").strip()
                found = bool(parsed.get("contains_wake_word", False))
                return transcript, found
            finally:
                os.unlink(tmp_path)
        except Exception:
            return "", False


class _GemmaLocalBackend:
    """Gemma 4 STT-only (transcription + wake-word flag) via llama.cpp.

    Works with either GEMMA_SIZE (12B or E4B) -- audio projects directly into
    the text embedding space, not through mmproj, so it isn't tied to the
    vision-only mmproj file's model-size variant.
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


class _GemmaUnifiedBackend:
    """Gemma 4 unified: audio → tool call (command) or conversational reply.

    Used by stt_node (physical mic on Jetson).  One llama.cpp REST call
    replaces the STT → NLU → TTS pipeline.  Uses Gemma 4's NATIVE tool calling
    (requires llama-server --jinja): the model picks execute_robot_command only
    when the speech clearly maps to a command, otherwise respond_conversationally.
    That discrete choice — not an "unknown" sentinel in a forced field — is the
    high-confidence gate, so it stops force-fitting ambiguous speech onto the
    nearest command.  `command` is grammar-constrained to the exact CMD_MAP keys.

    Returns a _UnifiedResult; stt_node's _process_loop dispatches the command
    and publishes /tts.  Falls back to a JSON content body if the server returns
    no tool_calls (e.g. --jinja not enabled).
    """

    # Prompt and tool schema come from command_dispatcher so both languages (and
    # both nodes) share one source. The Indonesian path is rendered entirely in
    # Bahasa Indonesia — see command_dispatcher.system_prompt / build_unified_tools.
    def __init__(self, llama_cpp_host: str, model: str, language: str, wake_word: str = ""):
        self._host = llama_cpp_host.rstrip("/")
        self._model = model
        self._language = language
        self._wake_word = wake_word
        self._system = system_prompt(language, wake_word)
        self._tools = build_unified_tools(language)

    def _override_command(self, result: "_UnifiedResult") -> "_UnifiedResult":
        """Deterministic command fallback when the LLM under-fires on a clear
        Indonesian command (it tends to pick the conversational tool even on a
        perfect transcript). Scoped to `id` so the English path is untouched."""
        if (self._language or "en").lower() != "id":
            return result
        if result.command and result.command != "unknown":
            return result
        if not result.contains_wake_word or not result.transcript:
            return result
        key = command_for_text(result.transcript, self._language)
        if key:
            action = CMD_MAP.get(key)
            result.command = key
            if action is not None:
                result.text_response = feedback_for_action(action)
        return result

    def _parse_message(self, message: dict) -> "_UnifiedResult":
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
            transcript = coerce_str(args.get("transcript"))
            wake = bool(args.get("contains_wake_word", False))
            # execute_robot_command (two-tool) and process_speech (single-tool) both
            # carry a `command`. coerce_command maps "none"/garbage → "unknown".
            if name in ("execute_robot_command", "process_speech"):
                cmd = coerce_command(args.get("command"))
                if cmd == "unknown":
                    return _UnifiedResult(
                        contains_wake_word=wake, command="unknown", parameters={},
                        text_response=coerce_str(args.get("spoken_reply")),
                        transcript=transcript,
                    )
                action = CMD_MAP.get(cmd)
                text = feedback_for_action(action) if action is not None else None
                return _UnifiedResult(
                    contains_wake_word=wake, command=cmd, parameters={},
                    text_response=text, transcript=transcript,
                )
            return _UnifiedResult(
                contains_wake_word=wake, command="unknown", parameters={},
                text_response=coerce_str(args.get("spoken_reply")),
                transcript=transcript,
            )

        # No tool call — fall back to a JSON content body (legacy / no --jinja).
        raw = (message.get("content") or "").strip()
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = None
        if not isinstance(parsed, dict):
            return _UnifiedResult(
                contains_wake_word=False, command="unknown",
                text_response=raw or None,
            )
        return _UnifiedResult(
            contains_wake_word=bool(parsed.get("contains_wake_word", False)),
            command=coerce_command(parsed.get("command")),
            parameters=parsed.get("parameters") if isinstance(parsed.get("parameters"), dict) else {},
            text_response=coerce_str(parsed.get("text_response")),
            transcript=coerce_str(parsed.get("transcript")),
        )

    def transcribe(self, audio_bytes: bytes, sample_rate: int) -> "_UnifiedResult":
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        try:
            resp = requests.post(
                f"{self._host}/v1/chat/completions",
                json={
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
                },
                timeout=120,
            )
            resp.raise_for_status()
            message = resp.json()["choices"][0]["message"]
            return self._override_command(self._parse_message(message))
        except Exception:
            return _UnifiedResult(contains_wake_word=False, command=None)


# ---------------------------------------------------------------------------
# Unified result (mirrors mic_bridge_node._UnifiedResult — kept local to avoid
# circular import; both modules define the same lightweight dataclass)
# ---------------------------------------------------------------------------

from dataclasses import dataclass, field as dc_field

@dataclass
class _UnifiedResult:
    contains_wake_word: bool
    command: str | None
    parameters: dict = dc_field(default_factory=dict)
    text_response: str | None = None
    audio_response: bytes | None = None
    transcript: str | None = None


# ---------------------------------------------------------------------------
# Main node
# ---------------------------------------------------------------------------

class STTNode(Node):

    def __init__(self):
        super().__init__("stt_node")

        self.declare_parameter("stt_provider", "openai")
        self.declare_parameter("whisper_model", "base")
        self.declare_parameter("device", "cuda")
        self.declare_parameter("compute_type", "float16")
        self.declare_parameter("language", "en")
        self.declare_parameter("api_key", "")
        self.declare_parameter("llama_cpp_host", "http://llama_cpp:8080")
        self.declare_parameter("gemma_model", "gemma")
        self.declare_parameter("wake_word", "doggo")
        # Noise-adaptive VAD: threshold tracks a slow moving average of the
        # ambient noise floor rather than a fixed value, since a threshold
        # tuned for one audio source can sit permanently above or below
        # another source's actual speech level. Concretely: the robot's
        # onboard mic over CycloneDDS measured idle-noise RMS ~0.014-0.017
        # (normalized) with speech peaking only ~0.027 -- a fixed 0.04
        # threshold (tuned for a normal-gain mic) never triggers on that
        # source at all. See docs/connection-modes.md#audio-topics-cyclonedds-mode.
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
        # High-pass filter applied before VAD/STT -- robot fan/motor noise is
        # low-frequency-dominated and was confirmed (by ear, on hardware) to
        # mask speech in captured robot-mic audio at levels the amplitude-only
        # VAD above can't tell apart from a person talking. 0 disables it.
        self.declare_parameter("highpass_cutoff_hz", 150.0)
        self.declare_parameter("silence_duration", 0.4)
        self.declare_parameter("sample_rate", 16000)
        self.declare_parameter("frame_duration_ms", 30)
        # Audio source: "mic" (local sounddevice) or "topic" (robot's WebRTC mic
        # republished on /robot_audio by the driver). The latter lets the robot's
        # onboard mic drive STT even when the SDK runs on an external PC.
        self.declare_parameter("audio_source", "mic")
        self.declare_parameter("audio_topic", "/robot_audio")
        # "auto" walks AUDIO_SOURCE_PRIORITY (Bluetooth mic, then USB mic) via
        # PulseAudio and falls back to the robot mic topic when neither exists.
        # Re-checked every source_probe_interval seconds, so plugging in a USB
        # mic or connecting a headset takes effect without a restart.
        self.declare_parameter("pulse_source_priority", ",".join(AUDIO_SOURCE_PRIORITY))
        self.declare_parameter("source_probe_interval", 10.0)

        provider      = self.get_parameter("stt_provider").value
        model_size    = self.get_parameter("whisper_model").value
        device        = self.get_parameter("device").value
        compute_type  = self.get_parameter("compute_type").value
        language      = self.get_parameter("language").value
        api_key       = self.get_parameter("api_key").value
        llama_cpp_host = self.get_parameter("llama_cpp_host").value
        gemma_model    = self.get_parameter("gemma_model").value
        self._wake_word = self.get_parameter("wake_word").value
        vad_noise_multiplier = float(self.get_parameter("vad_noise_multiplier").value)
        vad_absolute_floor = float(self.get_parameter("vad_absolute_floor").value)
        vad_noise_ema_alpha = float(self.get_parameter("vad_noise_ema_alpha").value)
        highpass_cutoff_hz = float(self.get_parameter("highpass_cutoff_hz").value)
        self._silence = float(self.get_parameter("silence_duration").value)
        self._rate    = int(self.get_parameter("sample_rate").value)
        self._frame_ms = int(self.get_parameter("frame_duration_ms").value)
        self._audio_source = self.get_parameter("audio_source").value
        audio_topic        = self.get_parameter("audio_topic").value

        # Noise-adaptive VAD + high-pass filter (speech_processor.audio_vad,
        # shared with mic_bridge_node.py so the two entry points into this
        # SDK's STT pipeline can't silently diverge in how they preprocess
        # audio). One instance for this node -- mic and topic sources are
        # mutually exclusive per node instance, never fed concurrently.
        self._vad = SegmentingVAD(
            sample_rate=self._rate,
            noise_multiplier=vad_noise_multiplier,
            absolute_floor=vad_absolute_floor,
            noise_ema_alpha=vad_noise_ema_alpha,
            silence_duration_s=self._silence,
            highpass_cutoff_hz=highpass_cutoff_hz,
        )

        self._pub = self.create_publisher(String, "/speech_text", 10)

        # Declare dispatch params (used by unified backends)
        self.declare_parameter("cmd_topic", "/webrtc_req")
        self.declare_parameter("move_duration", 2.0)
        self.declare_parameter("linear_speed", 0.3)
        self.declare_parameter("angular_speed", 0.5)
        cmd_topic = self.get_parameter("cmd_topic").value
        move_dur  = float(self.get_parameter("move_duration").value)
        lin_speed = float(self.get_parameter("linear_speed").value)
        ang_speed = float(self.get_parameter("angular_speed").value)
        self._is_sim = (cmd_topic == "/sim_cmd")

        self._webrtc_pub = self.create_publisher(WebRtcReq, cmd_topic, 10)
        self._cmdvel_pub = self.create_publisher(Twist, "/cmd_vel_voice", 10)
        self._tts_pub    = self.create_publisher(String, "/tts", 10)

        self._backend = self._build_backend(
            provider, api_key, model_size, device, compute_type, language,
            llama_cpp_host, gemma_model, self._wake_word,
        )

        self._dispatcher: CommandDispatcher | None = None
        if isinstance(self._backend, _GemmaUnifiedBackend):
            self._dispatcher = CommandDispatcher(
                cmd_pub=self._webrtc_pub, vel_pub=self._cmdvel_pub,
                lin_speed=lin_speed, ang_speed=ang_speed,
                move_dur=move_dur, is_sim=self._is_sim, node=self,
            )

        # Utterance assembly
        self._audio_queue: queue.Queue = queue.Queue()
        self._worker = threading.Thread(target=self._process_loop, daemon=True)
        self._worker.start()

        self._audio_topic = audio_topic
        self._topic_sub = None
        self._pulse_priority = tuple(
            frag.strip()
            for frag in self.get_parameter("pulse_source_priority").value.split(",")
            if frag.strip()
        )
        self._source_probe_interval = float(self.get_parameter("source_probe_interval").value)

        if self._audio_source == "auto":
            self._capture_thread = threading.Thread(target=self._auto_capture_loop, daemon=True)
            self._capture_thread.start()
            self.get_logger().info(
                "stt_node audio source: auto — "
                f"{' > '.join(self._pulse_priority)} > robot mic ({audio_topic})"
            )
        elif self._audio_source == "topic":
            self._enable_topic_source()
            self.get_logger().info(f"stt_node audio source: ROS topic {audio_topic} (robot mic)")
        else:
            self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._capture_thread.start()
            self.get_logger().info("stt_node audio source: local microphone (sounddevice)")

        self.get_logger().info(
            f"stt_node ready — provider={provider}, model={model_size}, "
            f"device={device}, rate={self._rate} Hz"
        )

    # ------------------------------------------------------------------
    # Backend factory
    # ------------------------------------------------------------------

    def _build_backend(
        self, provider: str, api_key: str,
        model_size: str, device: str, compute_type: str,
        language: str,
        llama_cpp_host: str = "http://llama_cpp:8080", gemma_model: str = "gemma",
        wake_word: str = "doggo",
    ):
        if provider == "openai":
            self.get_logger().info("STT backend: OpenAI Whisper API")
            return _OpenAIBackend(api_key, "whisper-1", language, wake_word)
        elif provider == "faster_whisper":
            self.get_logger().info(
                f"STT backend: faster-whisper ({model_size}, {device}, {compute_type})"
            )
            return _FasterWhisperBackend(model_size, device, compute_type, language, wake_word)
        elif provider == "gemini":
            self.get_logger().info(
                "STT backend: Gemini (gemini-2.5-flash, structured wake-word output)"
            )
            return _GeminiBackend(api_key, language, wake_word)
        elif provider == "gemma_local":
            self.get_logger().info(
                f"STT backend: Gemma unified ({gemma_model} via {llama_cpp_host}) — "
                "audio → wake word + command + text response"
            )
            return _GemmaUnifiedBackend(llama_cpp_host, gemma_model, language, wake_word)
        else:
            self.get_logger().error(f"Unknown stt_provider '{provider}' — falling back to faster_whisper CPU")
            return _FasterWhisperBackend(model_size, "cpu", "int8", language, wake_word)

    # ------------------------------------------------------------------
    # Audio capture (sounddevice, ARM64 compatible)
    # ------------------------------------------------------------------

    def _feed_pcm(self, pcm: np.ndarray) -> None:
        """Feed a float32 mono chunk to the shared VAD; queue completed utterances.

        Source-agnostic — fed by the local mic (sounddevice) or the robot's
        mic (/robot_audio, WebRTC or CycloneDDS). See
        speech_processor.audio_vad.SegmentingVAD for the noise-adaptive
        threshold + high-pass filter this delegates to.
        """
        utterance = self._vad.feed(pcm)
        if utterance:
            self._audio_queue.put((utterance, time.monotonic()))

    def _on_robot_audio(self, msg: UInt8MultiArray) -> None:
        """Feed the robot's WebRTC mic PCM (int16 LE @ self._rate) into the VAD."""
        pcm_i16 = np.frombuffer(bytes(msg.data), dtype=np.int16)
        if pcm_i16.size:
            self._feed_pcm(pcm_i16.astype(np.float32) / 32768.0)

    # ------------------------------------------------------------------
    # Auto source selection: Bluetooth mic > USB mic > robot mic
    # ------------------------------------------------------------------

    def _enable_topic_source(self) -> None:
        """Subscribe to the robot's own mic (last-resort input)."""
        if self._topic_sub is None:
            self._topic_sub = self.create_subscription(
                UInt8MultiArray, self._audio_topic, self._on_robot_audio,
                qos_profile_sensor_data,
            )

    def _disable_topic_source(self) -> None:
        """Drop the robot-mic subscription once a better input is available."""
        if self._topic_sub is not None:
            self.destroy_subscription(self._topic_sub)
            self._topic_sub = None

    def _best_pulse_source(self) -> Optional[str]:
        """Best available PulseAudio capture source, or None.

        In the Docker deployment PULSE_SERVER points at the host's PulseAudio,
        because the audio server (and BlueZ) live on the host while this node
        runs in the container. Any failure returns None, which degrades to the
        robot mic rather than losing audio input altogether.
        """
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
        """Capture `source` via parec, feeding PCM frames into the VAD pipeline."""
        frame_bytes = int(self._rate * self._frame_ms / 1000) * 2  # s16le mono
        proc = subprocess.Popen(
            [
                "parec", f"--device={source}", "--format=s16le",
                f"--rate={self._rate}", "--channels=1", "--raw",
            ],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )

        def reader():
            while proc.poll() is None:
                data = proc.stdout.read(frame_bytes)
                if not data:
                    break
                pcm = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                self._feed_pcm(pcm)

        threading.Thread(target=reader, daemon=True).start()
        return proc

    def _auto_capture_loop(self):
        """Keep the highest-priority available input attached.

        Re-probes periodically so connecting a headset or plugging in a USB mic
        switches input live, and so the death of a capture process (speaker
        powered off mid-sentence) falls back instead of going deaf.
        """
        # Sentinel, not None: on the first pass the best source may legitimately
        # be None (no Bluetooth/USB mic), and `None != None` would skip the
        # branch that subscribes to the robot mic, leaving the node deaf.
        unset = object()
        current = unset
        proc = None
        while rclpy.ok():
            if proc is not None and proc.poll() is not None:
                self.get_logger().warn(
                    f"Audio capture from {current} ended — re-selecting input"
                )
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
                if best:
                    self._disable_topic_source()
                    proc = self._start_parec(best)
                    self.get_logger().info(f"🎙 Audio input: {best}")
                else:
                    self._enable_topic_source()
                    self.get_logger().info(
                        f"🎙 Audio input: robot mic ({self._audio_topic}) — no Bluetooth or USB mic"
                    )
                current = best
            time.sleep(self._source_probe_interval)

    def _capture_loop(self):
        try:
            import sounddevice as sd
        except ImportError:
            self.get_logger().error("sounddevice not installed — run: pip install sounddevice")
            return

        frame_samples = int(self._rate * self._frame_ms / 1000)

        def callback(indata, frames, time_info, status):
            self._feed_pcm(indata[:, 0])  # mono

        try:
            stream = sd.InputStream(
                samplerate=self._rate,
                channels=1,
                dtype="float32",
                blocksize=frame_samples,
                callback=callback,
            )
        except Exception as e:
            self.get_logger().error(
                f"No audio input device available — STT disabled: {e}. "
                "On Windows/Docker use the browser mic bridge (MIC_BRIDGE=true, open http://localhost:8888); "
                "on Jetson plug in a USB mic; or set ENABLE_STT=false."
            )
            return

        with stream:
            self.get_logger().info("Microphone open — listening…")
            while rclpy.ok():
                import time
                time.sleep(0.1)

    # ------------------------------------------------------------------
    # STT inference worker
    # ------------------------------------------------------------------

    def _wav_header(self, pcm_bytes: bytes) -> bytes:
        import struct
        num_samples = len(pcm_bytes) // 2
        data_size = num_samples * 2
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", 36 + data_size, b"WAVE",
            b"fmt ", 16, 1, 1,
            self._rate, self._rate * 2, 2, 16,
            b"data", data_size,
        )
        return header + pcm_bytes

    def _process_loop(self):
        while True:
            item = self._audio_queue.get()
            if item is None:
                break
            pcm_bytes, t_vad = item
            wav_bytes = self._wav_header(pcm_bytes)
            try:
                result = self._backend.transcribe(wav_bytes, self._rate)
            except Exception as exc:
                self.get_logger().error(f"STT transcription error: {exc}")
                continue

            t_stt = time.monotonic()

            if isinstance(result, _UnifiedResult):
                self._handle_unified(result, t_vad, t_stt)
            else:
                text, wake_word_found = result
                if not text:
                    continue
                stt_ms = (t_stt - t_vad) * 1000
                self.get_logger().info(f"Transcribed ({stt_ms:.0f} ms): {text!r}")
                if not wake_word_found:
                    self.get_logger().debug(f"Ignored (no wake word '{self._wake_word}'): {text!r}")
                    continue
                self._pub.publish(String(data=text))

    def _handle_unified(self, result: "_UnifiedResult", t_vad: float, t_stt: float) -> None:
        transcript = result.transcript or ""
        stt_ms = (t_stt - t_vad) * 1000

        if not result.contains_wake_word:
            self.get_logger().info(
                f"Unified ({stt_ms:.0f} ms) — no wake word: {transcript!r}"
            )
            return

        cmd = result.command
        if cmd and cmd != "unknown" and self._dispatcher is not None:
            action = CMD_MAP.get(cmd)
            if action is not None:
                t_cmd = time.monotonic()
                total_ms = (t_cmd - t_vad) * 1000
                self.get_logger().info(
                    f"Unified ({total_ms:.0f} ms total | {stt_ms:.0f} ms STT) "
                    f"— executing '{cmd}': {transcript!r}"
                )
                self._dispatcher.execute(action)
            else:
                self.get_logger().warn(f"Unified: unknown command key '{cmd}'")
        else:
            self.get_logger().info(
                f"Unified ({stt_ms:.0f} ms) — no command: {transcript!r}"
            )

        if result.text_response:
            self.get_logger().info(f"Unified TTS: {result.text_response!r}")
            self._tts_pub.publish(String(data=result.text_response))


def main(args=None):
    rclpy.init(args=args)
    node = STTNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
