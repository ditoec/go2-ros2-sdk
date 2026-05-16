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
vosk          : Streaming Kaldi/LSTM model, lowest RAM, lower accuracy

Audio is captured via sounddevice (ARM64 compatible, no PyAudio required).
A simple energy-threshold VAD buffers frames and fires the STT backend once
silence follows a voiced segment.

Published topic: /speech_text  (std_msgs/String)
"""

import io
import threading
import queue
from typing import Optional

import numpy as np
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


# ---------------------------------------------------------------------------
# STT backend classes
# ---------------------------------------------------------------------------

class _OpenAIBackend:
    """Whisper API — same openai package used by TTSProvider_OpenAI."""

    def __init__(self, api_key: str, model: str, language: str):
        import openai
        self._client = openai.OpenAI(api_key=api_key)
        self._model = model      # "whisper-1"
        self._language = language

    def transcribe(self, audio_bytes: bytes, sample_rate: int) -> str:
        import openai
        buf = io.BytesIO(audio_bytes)
        buf.name = "audio.wav"
        try:
            result = self._client.audio.transcriptions.create(
                model=self._model,
                file=buf,
                language=self._language,
            )
            return result.text.strip()
        except openai.OpenAIError:
            return ""


class _FasterWhisperBackend:
    """Local CTranslate2 Whisper — offline, CUDA-accelerated on Jetson NX."""

    def __init__(self, model_size: str, device: str, compute_type: str, language: str):
        from faster_whisper import WhisperModel
        self._model = WhisperModel(model_size, device=device, compute_type=compute_type)
        self._language = language

    def transcribe(self, audio_bytes: bytes, sample_rate: int) -> str:
        audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        segments, _ = self._model.transcribe(audio_array, language=self._language, beam_size=1)
        return " ".join(seg.text for seg in segments).strip()


class _VoskBackend:
    """Streaming Kaldi/LSTM — lightest RAM, no GPU required."""

    def __init__(self, model_path: str, sample_rate: int):
        from vosk import Model, KaldiRecognizer
        import json
        self._recognizer = KaldiRecognizer(Model(model_path), sample_rate)
        self._json = json

    def transcribe(self, audio_bytes: bytes, sample_rate: int) -> str:
        self._recognizer.AcceptWaveform(audio_bytes)
        result = self._json.loads(self._recognizer.FinalResult())
        return result.get("text", "").strip()


class _GeminiBackend:
    """Gemini Whisper — gemini-2.5-flash via google-genai, internet required."""

    def __init__(self, api_key: str, language: str):
        from google import genai
        from google.genai import types
        self._client = genai.Client(api_key=api_key)
        self._types = types
        self._language = language

    def transcribe(self, audio_bytes: bytes, sample_rate: int) -> str:
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
                response = self._client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        uploaded,
                        f"Transcribe this audio to text. Language: {self._language}. "
                        "Return only the transcript, no extra text.",
                    ],
                )
                return response.text.strip() if response.text else ""
            finally:
                os.unlink(tmp_path)
        except Exception:
            return ""


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
        self.declare_parameter("vosk_model_path", "")
        self.declare_parameter("vad_threshold", 0.02)
        self.declare_parameter("silence_duration", 0.8)
        self.declare_parameter("sample_rate", 16000)
        self.declare_parameter("frame_duration_ms", 30)

        provider      = self.get_parameter("stt_provider").value
        model_size    = self.get_parameter("whisper_model").value
        device        = self.get_parameter("device").value
        compute_type  = self.get_parameter("compute_type").value
        language      = self.get_parameter("language").value
        api_key       = self.get_parameter("api_key").value
        vosk_path     = self.get_parameter("vosk_model_path").value
        self._vad_thr = float(self.get_parameter("vad_threshold").value)
        self._silence = float(self.get_parameter("silence_duration").value)
        self._rate    = int(self.get_parameter("sample_rate").value)
        self._frame_ms = int(self.get_parameter("frame_duration_ms").value)

        self._pub = self.create_publisher(String, "/speech_text", 10)

        self._backend = self._build_backend(
            provider, api_key, model_size, device, compute_type, language, vosk_path
        )

        # Utterance assembly
        self._audio_queue: queue.Queue = queue.Queue()
        self._worker = threading.Thread(target=self._process_loop, daemon=True)
        self._worker.start()

        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._capture_thread.start()

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
        language: str, vosk_path: str,
    ):
        if provider == "openai":
            self.get_logger().info("STT backend: OpenAI Whisper API")
            return _OpenAIBackend(api_key, "whisper-1", language)
        elif provider == "faster_whisper":
            self.get_logger().info(
                f"STT backend: faster-whisper ({model_size}, {device}, {compute_type})"
            )
            return _FasterWhisperBackend(model_size, device, compute_type, language)
        elif provider == "vosk":
            self.get_logger().info(f"STT backend: Vosk — model path: {vosk_path}")
            return _VoskBackend(vosk_path, self._rate)
        elif provider == "gemini":
            self.get_logger().info("STT backend: Gemini (gemini-2.5-flash)")
            return _GeminiBackend(api_key, language)
        else:
            self.get_logger().error(f"Unknown stt_provider '{provider}' — falling back to faster_whisper CPU")
            return _FasterWhisperBackend(model_size, "cpu", "int8", language)

    # ------------------------------------------------------------------
    # Audio capture (sounddevice, ARM64 compatible)
    # ------------------------------------------------------------------

    def _capture_loop(self):
        try:
            import sounddevice as sd
        except ImportError:
            self.get_logger().error("sounddevice not installed — run: pip install sounddevice")
            return

        frame_samples = int(self._rate * self._frame_ms / 1000)
        voiced_frames: list[bytes] = []
        silent_frames = 0
        speaking = False

        silence_frames_needed = int(self._silence * 1000 / self._frame_ms)

        def callback(indata, frames, time_info, status):
            nonlocal voiced_frames, silent_frames, speaking
            pcm = indata[:, 0]  # mono
            rms = float(np.sqrt(np.mean(pcm ** 2)))

            raw = (pcm * 32767).astype(np.int16).tobytes()

            if rms >= self._vad_thr:
                speaking = True
                silent_frames = 0
                voiced_frames.append(raw)
            elif speaking:
                voiced_frames.append(raw)
                silent_frames += 1
                if silent_frames >= silence_frames_needed:
                    utterance = b"".join(voiced_frames)
                    self._audio_queue.put(utterance)
                    voiced_frames = []
                    silent_frames = 0
                    speaking = False

        with sd.InputStream(
            samplerate=self._rate,
            channels=1,
            dtype="float32",
            blocksize=frame_samples,
            callback=callback,
        ):
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
            pcm_bytes = self._audio_queue.get()
            if pcm_bytes is None:
                break
            wav_bytes = self._wav_header(pcm_bytes)
            try:
                text = self._backend.transcribe(wav_bytes, self._rate)
            except Exception as exc:
                self.get_logger().error(f"STT transcription error: {exc}")
                text = ""
            if text:
                self.get_logger().info(f"Transcribed: {text!r}")
                msg = String()
                msg.data = text
                self._pub.publish(msg)


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
