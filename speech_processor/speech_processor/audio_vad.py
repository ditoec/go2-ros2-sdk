# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

"""
Shared noise-adaptive VAD + high-pass filter for speech_processor nodes.

Used identically by stt_node.py (local mic / /robot_audio) and
mic_bridge_node.py (browser mic / /robot_audio, one instance per browser
connection) so audio preprocessing can't silently diverge between the two
entry points into this SDK's STT pipeline -- exactly the kind of drift that
made the robot mic path need re-fixing here after already being fixed once
in stt_node.py.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np


# Audio-input preference, highest priority first. Each entry is a substring
# matched against PulseAudio source names:
#   bluez_source.*    -> a Bluetooth headset mic (HSP/HFP)
#   alsa_input.usb-*  -> a USB microphone plugged into the Jetson
# When neither is present the caller falls back to the robot's own mic on
# /robot_audio, which is the noisiest option and therefore last.
AUDIO_SOURCE_PRIORITY = ("bluez_source", "usb")


def find_bluetooth_sink(pactl_output: str, pattern: str = "bluez_sink") -> Optional[str]:
    """First sink name matching `pattern` in `pactl list sinks short` output.

    Shared by tts_node.py (which routes completed replies to a Bluetooth
    speaker) and mic_bridge_node.py (which streams a reply to it as the model
    speaks). Returns None when no sink matches, meaning the caller should fall
    back to the robot's own speaker.
    """
    for line in pactl_output.splitlines():
        fields = line.split("\t")
        if len(fields) >= 2 and pattern in fields[1]:
            return fields[1]
    return None


def select_pulse_source(pactl_sources_output: str, priority=AUDIO_SOURCE_PRIORITY) -> Optional[str]:
    """Highest-priority real capture source in `pactl list sources short` output.

    Shared by stt_node.py and mic_bridge_node.py so the two entry points into
    this SDK's STT pipeline cannot disagree about which microphone to use.

    Monitor sources are loopbacks of an output, not microphones, so they are
    always skipped -- otherwise a connected Bluetooth speaker's own monitor
    would be mistaken for a Bluetooth mic and the robot would hear its own
    TTS. Returns None when nothing matches, meaning the caller should fall
    back to the robot mic topic.
    """
    names = []
    for line in pactl_sources_output.splitlines():
        fields = line.split("\t")
        if len(fields) >= 2:
            names.append(fields[1])
    for fragment in priority:
        for name in names:
            if name.endswith(".monitor"):
                continue
            if fragment in name:
                return name
    return None


class BiquadHighpass:
    """2nd-order Butterworth high-pass (RBJ Audio EQ Cookbook coefficients),
    stateful across calls so it can filter a stream chunk-by-chunk.

    Motivated by robot fan/motor noise, which is concentrated at low
    frequencies and was confirmed (by ear, on hardware) to mask speech in
    captured robot-mic audio -- an amplitude-only VAD can't separate "loud
    fan" from "loud speech" when they sit at similar RMS, but a high-pass
    filter can, since speech intelligibility lives mostly above ~300 Hz
    while fan/motor noise is dominated by sub-200 Hz rumble. No scipy
    dependency -- this project doesn't otherwise depend on it, and a biquad
    is simple enough to hand-roll correctly (verified against a synthetic
    sine sweep: -3dB at the configured cutoff, ~0dB by 2x cutoff).
    """

    def __init__(self, cutoff_hz: float, sample_rate: int):
        w0 = 2 * math.pi * cutoff_hz / sample_rate
        q = 0.7071067811865476  # 1/sqrt(2) -> maximally flat (Butterworth) response
        alpha = math.sin(w0) / (2 * q)
        cosw0 = math.cos(w0)
        b0 = (1 + cosw0) / 2
        b1 = -(1 + cosw0)
        b2 = (1 + cosw0) / 2
        a0 = 1 + alpha
        a1 = -2 * cosw0
        a2 = 1 - alpha
        self._b0, self._b1, self._b2 = b0 / a0, b1 / a0, b2 / a0
        self._a1, self._a2 = a1 / a0, a2 / a0
        self._x1 = self._x2 = self._y1 = self._y2 = 0.0

    def process(self, samples: np.ndarray) -> np.ndarray:
        b0, b1, b2, a1, a2 = self._b0, self._b1, self._b2, self._a1, self._a2
        x1, x2, y1, y2 = self._x1, self._x2, self._y1, self._y2
        out = np.empty_like(samples, dtype=np.float64)
        for i in range(samples.shape[0]):
            x0 = float(samples[i])
            y0 = b0 * x0 + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
            out[i] = y0
            x2, x1 = x1, x0
            y2, y1 = y1, y0
        self._x1, self._x2, self._y1, self._y2 = x1, x2, y1, y2
        return out.astype(samples.dtype, copy=False)


class SegmentingVAD:
    """Noise-adaptive energy VAD + utterance segmentation, source-agnostic.

    Feed float32 mono PCM chunks of any size via feed(); get back raw
    int16 PCM bytes for a completed utterance once silence follows speech
    (or the optional max-utterance cap is hit), else None.

    The trigger threshold is noise_multiplier times a slow EMA of the
    ambient noise floor (clamped to absolute_floor), not a fixed value -- a
    fixed threshold tuned for one audio source (e.g. a laptop mic) can sit
    permanently above or below another source's actual speech level. The
    floor EMA only updates on frames judged non-speech, so a voiced segment
    doesn't drag its own estimate upward mid-utterance.

    Owns its own noise-floor EMA and high-pass filter state, so each audio
    source needs its own instance -- state must never be shared across
    sources (e.g. one instance per browser WebSocket connection, a separate
    one for /robot_audio, never the same instance for both).
    """

    def __init__(
        self,
        sample_rate: int,
        noise_multiplier: float = 2.5,
        absolute_floor: float = 0.003,
        noise_ema_alpha: float = 0.05,
        silence_duration_s: float = 0.4,
        highpass_cutoff_hz: float = 150.0,
        max_utterance_s: Optional[float] = None,
    ):
        self._noise_multiplier = noise_multiplier
        self._absolute_floor = absolute_floor
        self._noise_ema_alpha = noise_ema_alpha
        self._silence_samples_needed = int(silence_duration_s * sample_rate)
        self._max_utt_samples = (
            int(max_utterance_s * sample_rate) if max_utterance_s else None
        )
        self._highpass = (
            BiquadHighpass(highpass_cutoff_hz, sample_rate)
            if highpass_cutoff_hz > 0 else None
        )

        self._voiced: list[bytes] = []
        self._speaking = False
        self._silent_samples = 0
        self._voiced_samples = 0
        # Bootstraps from the first frame fed (assumed non-speech) then
        # tracks via EMA on every frame judged non-speech afterward.
        self._noise_floor: Optional[float] = None

    def feed(self, pcm: np.ndarray) -> Optional[bytes]:
        if pcm.size == 0:
            return None
        if self._highpass is not None:
            pcm = self._highpass.process(pcm)

        rms = float(np.sqrt(np.mean(pcm ** 2)))
        raw = (np.clip(pcm, -1.0, 1.0) * 32767).astype(np.int16).tobytes()

        if self._noise_floor is None:
            self._noise_floor = rms

        threshold = max(self._noise_floor * self._noise_multiplier, self._absolute_floor)

        if rms >= threshold:
            self._speaking = True
            self._silent_samples = 0
            self._voiced.append(raw)
            self._voiced_samples += pcm.shape[0]
            if self._max_utt_samples and self._voiced_samples >= self._max_utt_samples:
                return self._flush()
            return None

        self._noise_floor += self._noise_ema_alpha * (rms - self._noise_floor)
        if self._speaking:
            self._voiced.append(raw)
            self._silent_samples += pcm.shape[0]
            self._voiced_samples += pcm.shape[0]
            if self._silent_samples >= self._silence_samples_needed:
                return self._flush()
        return None

    def _flush(self) -> bytes:
        utterance = b"".join(self._voiced)
        self._voiced = []
        self._silent_samples = 0
        self._voiced_samples = 0
        self._speaking = False
        return utterance
