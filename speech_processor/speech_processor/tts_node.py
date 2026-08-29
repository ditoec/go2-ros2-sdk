#!/usr/bin/env python3

# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

"""
Enhanced TTS Node

Improved Text-to-Speech functionality with better architecture,
caching, and multiple provider support.
"""

import base64
import io
import json
import os
import subprocess
import time
import hashlib
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import threading
from queue import Queue, Empty

from pydub import AudioSegment
from pydub.playback import play
import rclpy
from rclpy.node import Node
import requests
from std_msgs.msg import String, UInt8MultiArray, Bool
from go2_interfaces.msg import WebRtcReq


from .audio_vad import find_bluetooth_sink  # noqa: F401  (re-exported)


class AudioFormat(Enum):
    """Supported audio formats"""
    MP3 = "mp3"
    WAV = "wav"
    OGG = "ogg"


class TTSProvider(Enum):
    """Supported TTS providers"""
    SUPERTONIC = "supertonic"  # offline neural TTS — flow-matching, 31 langs, expression tags
    PIPER = "piper"             # offline TTS — subprocess binary, en/id, no Python-version coupling
    ELEVENLABS = "elevenlabs"
    GOOGLE = "google"
    AMAZON = "amazon"
    OPENAI = "openai"
    GEMINI = "gemini"


@dataclass
class TTSConfig:
    """Configuration for TTS functionality"""
    api_key: str
    provider: TTSProvider = TTSProvider.SUPERTONIC
    voice_name: str = "F1"      # Supertonic: M1–M5, F1–F5
    local_playback: bool = False
    # Bluetooth speaker preference. When a PulseAudio bluez sink is present
    # the reply is spoken through it; otherwise playback falls back to the
    # robot's own speaker (or local_playback). Detection is re-checked every
    # bluetooth_probe_interval seconds so unplugging/reconnecting a speaker
    # is picked up at runtime without restarting the node.
    bluetooth_playback: bool = True
    bluetooth_sink_pattern: str = "bluez_sink"
    bluetooth_probe_interval: float = 5.0
    use_cache: bool = True
    cache_dir: str = "tts_cache"
    chunk_size: int = 32 * 1024
    audio_quality: str = "standard"
    language: str = "en"

    # Supertonic-specific settings
    supertonic_steps: int = 8    # quality: 5 (fast) → 12 (best)
    supertonic_speed: float = 1.0

    # ElevenLabs specific settings
    stability: float = 0.5
    similarity_boost: float = 0.5
    model_id: str = "eleven_turbo_v2_5"


class AudioCache:
    """Thread-safe audio cache management"""
    
    def __init__(self, cache_dir: str, enabled: bool = True):
        self.cache_dir = cache_dir
        self.enabled = enabled
        self._lock = threading.Lock()
        
        if self.enabled:
            os.makedirs(self.cache_dir, exist_ok=True)
    
    def get_cache_path(self, text: str, voice_name: str, provider: str) -> str:
        """Generate cache file path"""
        cache_key = f"{text}_{voice_name}_{provider}"
        text_hash = hashlib.md5(cache_key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{text_hash}.mp3")
    
    def get(self, text: str, voice_name: str, provider: str) -> Optional[bytes]:
        """Get cached audio data"""
        if not self.enabled:
            return None
            
        with self._lock:
            cache_path = self.get_cache_path(text, voice_name, provider)
            if os.path.exists(cache_path):
                with open(cache_path, "rb") as f:
                    return f.read()
        return None
    
    def put(self, text: str, voice_name: str, provider: str, audio_data: bytes) -> bool:
        """Cache audio data"""
        if not self.enabled or not audio_data:
            return False
            
        with self._lock:
            try:
                cache_path = self.get_cache_path(text, voice_name, provider)
                with open(cache_path, "wb") as f:
                    f.write(audio_data)
                return True
            except Exception:
                return False
    
    def clear(self) -> bool:
        """Clear all cached files"""
        if not self.enabled:
            return True
            
        with self._lock:
            try:
                for filename in os.listdir(self.cache_dir):
                    file_path = os.path.join(self.cache_dir, filename)
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                return True
            except Exception:
                return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.enabled:
            return {"enabled": False}
            
        with self._lock:
            try:
                files = os.listdir(self.cache_dir)
                total_size = sum(
                    os.path.getsize(os.path.join(self.cache_dir, f)) 
                    for f in files if os.path.isfile(os.path.join(self.cache_dir, f))
                )
                return {
                    "enabled": True,
                    "file_count": len(files),
                    "total_size_mb": round(total_size / (1024 * 1024), 2),
                    "cache_dir": self.cache_dir
                }
            except Exception:
                return {"enabled": True, "error": "Unable to read cache stats"}


class TTSProvider_ElevenLabs:
    """ElevenLabs TTS provider implementation"""
    
    def __init__(self, config: TTSConfig):
        self.config = config
        self.base_url = "https://api.elevenlabs.io/v1"
    
    def synthesize(self, text: str) -> Optional[bytes]:
        """Generate speech using ElevenLabs API"""
        url = f"{self.base_url}/text-to-speech/{self.config.voice_name}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.config.api_key,
        }
        
        data = {
            "text": text,
            "model_id": self.config.model_id,
            "voice_settings": {
                "stability": self.config.stability,
                "similarity_boost": self.config.similarity_boost
            },
        }
        
        try:
            response = requests.post(url, json=data, headers=headers, timeout=30)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException:
            return None
    
    def get_voices(self) -> List[Dict[str, Any]]:
        """Get available voices"""
        url = f"{self.base_url}/voices"
        headers = {"xi-api-key": self.config.api_key}
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json().get("voices", [])
        except requests.exceptions.RequestException:
            return []


class TTSProvider_OpenAI:
    """OpenAI TTS provider — tts-1-hd model, same openai package as STT node."""

    def __init__(self, config: TTSConfig):
        import openai
        self.client = openai.OpenAI(api_key=config.api_key)
        # voice_name should be one of: alloy, echo, fable, onyx, nova, shimmer
        self.voice = config.voice_name if config.voice_name in (
            "alloy", "echo", "fable", "onyx", "nova", "shimmer"
        ) else "nova"
        self.model = "tts-1-hd" if config.audio_quality == "high" else "tts-1"

    def synthesize(self, text: str) -> Optional[bytes]:
        """Generate speech using OpenAI TTS API. Returns MP3 bytes."""
        try:
            import openai
            response = self.client.audio.speech.create(
                model=self.model,
                voice=self.voice,
                input=text,
                response_format="mp3",
            )
            return response.content
        except openai.OpenAIError:
            return None


class TTSProvider_Gemini:
    """Gemini TTS provider — gemini-2.5-flash-tts-preview.

    Gemini returns raw PCM (24 kHz, 16-bit mono). This class converts it to
    MP3 bytes via pydub so the rest of the pipeline (cache, robot playback) is
    unchanged.
    """

    _VALID_VOICES = {
        "Kore", "Zephyr", "Puck", "Charon", "Fenrir",
        "Leda", "Orus", "Aoede", "Callirrhoe",
    }

    def __init__(self, config: TTSConfig):
        from google import genai
        from google.genai import types
        self._client = genai.Client(api_key=config.api_key)
        self._types = types
        self._voice = config.voice_name if config.voice_name in self._VALID_VOICES else "Kore"

    def synthesize(self, text: str) -> Optional[bytes]:
        """Generate speech and return MP3 bytes."""
        try:
            response = self._client.models.generate_content(
                model="gemini-2.5-flash-tts-preview",
                contents=text,
                config=self._types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=self._types.SpeechConfig(
                        voice_config=self._types.VoiceConfig(
                            prebuilt_voice_config=self._types.PrebuiltVoiceConfig(
                                voice_name=self._voice
                            )
                        )
                    ),
                ),
            )
            pcm_bytes = response.candidates[0].content.parts[0].inline_data.data
            # 24 kHz, 16-bit, mono PCM → MP3
            pcm_audio = AudioSegment(data=pcm_bytes, sample_width=2, frame_rate=24000, channels=1)
            mp3_buf = io.BytesIO()
            pcm_audio.export(mp3_buf, format="mp3")
            return mp3_buf.getvalue()
        except Exception:
            return None


class TTSProvider_Supertonic:
    """On-device neural TTS via Supertonic v3 — 99M flow-matching model, ONNX runtime.

    Model (~305 MB) auto-downloads from Hugging Face on first use.
    The Docker image pre-bakes the model so the first container start is instant.

    Voices:  M1–M5 (male), F1–F5 (female)
    Languages: 31 supported (en, ko, ja, de, fr, es, pt, ar, …) — 'na' for auto-detect
    Expression tags: <laugh>, <breath>, <sigh>, and 7 more inline tags
    """

    _VALID_VOICES = {"M1", "M2", "M3", "M4", "M5", "F1", "F2", "F3", "F4", "F5"}

    def __init__(self, config: TTSConfig):
        try:
            from supertonic import TTS as _TTS
        except ImportError as exc:
            raise RuntimeError(
                "supertonic not installed — run: pip install supertonic"
            ) from exc

        self._tts = _TTS(auto_download=True)
        voice = config.voice_name if config.voice_name in self._VALID_VOICES else "F1"
        self._style = self._tts.get_voice_style(voice_name=voice)
        self._lang = config.language or "en"
        self._steps = config.supertonic_steps
        self._speed = config.supertonic_speed

    def synthesize(self, text: str) -> Optional[bytes]:
        """Return MP3 bytes synthesised by Supertonic, or None on failure."""
        import wave
        import numpy as np
        try:
            wav, _ = self._tts.synthesize(
                text=text,
                voice_style=self._style,
                lang=self._lang,
                total_steps=self._steps,
                speed=self._speed,
            )
            # wav is a float32 numpy array at 44.1 kHz — convert to WAV then MP3
            pcm = (np.clip(wav, -1.0, 1.0) * 32767).astype(np.int16)
            wav_buf = io.BytesIO()
            with wave.open(wav_buf, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(44100)
                wf.writeframes(pcm.tobytes())
            wav_buf.seek(0)
            audio = AudioSegment.from_wav(wav_buf)
            mp3_buf = io.BytesIO()
            audio.export(mp3_buf, format='mp3')
            return mp3_buf.getvalue()
        except Exception:
            return None


class TTSProvider_Piper:
    """On-device TTS via Piper — a standalone C++ binary (rhasspy/piper's
    classic release, not the newer piper1-gpl Python rewrite) invoked as a
    subprocess. Unlike every other offline option this SDK evaluated
    (Supertonic, MMS-TTS via transformers), Piper has zero coupling to the
    host's Python version — it never imports as a Python package here — which
    is why it's the default provider on the Jetson image (Python 3.8.10, tied
    to ROS2 Humble's source-built rclpy bindings; see docker/Dockerfile.jetson).

    Voice models are pre-baked per-language (English + Indonesian) into the
    Jetson Docker image. voice_name may override the model file basename
    directly (e.g. "en_US-lessac-medium") to use a different/custom voice;
    otherwise the language-default voice is picked from config.language.
    """

    _DEFAULT_VOICES = {
        "en": "en_US-lessac-medium",
        "id": "id_ID-news_tts-medium",
    }
    # Other providers' voice_name defaults (Supertonic's M1-M5/F1-F5) mean
    # "use the language default" here rather than a literal Piper model name.
    _NON_PIPER_VOICE_NAMES = {"M1", "M2", "M3", "M4", "M5", "F1", "F2", "F3", "F4", "F5"}

    def __init__(self, config: TTSConfig):
        self._binary = os.environ.get("PIPER_BINARY", "/opt/piper/piper")
        if not os.path.isfile(self._binary):
            raise RuntimeError(
                f"piper binary not found at {self._binary} — set PIPER_BINARY "
                "or rebuild the Jetson image (docker/Dockerfile.jetson pre-bakes it)"
            )

        voices_dir = os.environ.get("PIPER_VOICES_DIR", "/opt/piper/voices")
        lang = (config.language or "en").split("-")[0].lower()
        voice = config.voice_name
        if not voice or voice in self._NON_PIPER_VOICE_NAMES:
            voice = self._DEFAULT_VOICES.get(lang, self._DEFAULT_VOICES["en"])

        self._model_path = os.path.join(voices_dir, f"{voice}.onnx")
        if not os.path.isfile(self._model_path):
            raise RuntimeError(
                f"piper voice model not found: {self._model_path} "
                f"(pre-baked languages: {', '.join(self._DEFAULT_VOICES)})"
            )

    def synthesize(self, text: str) -> Optional[bytes]:
        """Run piper as a subprocess and return MP3 bytes, or None on failure."""
        import subprocess
        import tempfile

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
            result = subprocess.run(
                [self._binary, "--model", self._model_path, "--output_file", tmp_path],
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=30,
            )
            if result.returncode != 0 or not os.path.exists(tmp_path):
                return None
            audio = AudioSegment.from_wav(tmp_path)
            mp3_buf = io.BytesIO()
            audio.export(mp3_buf, format="mp3")
            return mp3_buf.getvalue()
        except Exception:
            return None
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)


class AudioProcessor:
    """Audio processing utilities"""
    
    @staticmethod
    def convert_to_wav(audio_data: bytes, input_format: AudioFormat = AudioFormat.MP3) -> Optional[bytes]:
        """Convert audio data to WAV format"""
        try:
            if input_format == AudioFormat.MP3:
                audio = AudioSegment.from_mp3(io.BytesIO(audio_data))
            elif input_format == AudioFormat.OGG:
                audio = AudioSegment.from_ogg(io.BytesIO(audio_data))
            else:
                return audio_data  # Already WAV
            
            wav_io = io.BytesIO()
            audio.export(wav_io, format="wav")
            return wav_io.getvalue()
        except Exception:
            return None
    
    @staticmethod
    def get_duration(audio_data: bytes, format: AudioFormat = AudioFormat.WAV) -> float:
        """Get audio duration in seconds"""
        try:
            if format == AudioFormat.WAV:
                audio = AudioSegment.from_wav(io.BytesIO(audio_data))
            elif format == AudioFormat.MP3:
                audio = AudioSegment.from_mp3(io.BytesIO(audio_data))
            else:
                audio = AudioSegment.from_file(io.BytesIO(audio_data))
            
            return len(audio) / 1000.0  # Convert ms to seconds
        except Exception:
            return 0.0
    
    @staticmethod
    def split_into_chunks(data: bytes, chunk_size: int) -> List[bytes]:
        """Split data into chunks"""
        return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]


class EnhancedTTSNode(Node):
    """Enhanced TTS Node with improved architecture"""
    
    def __init__(self):
        super().__init__("tts_node")
        
        # Declare parameters
        self._declare_parameters()
        
        # Load configuration
        self.config = self._load_configuration()
        
        # Initialize components
        self.cache = AudioCache(self.config.cache_dir, self.config.use_cache)
        self.audio_processor = AudioProcessor()
        
        # Initialize TTS provider
        self.tts_provider = self._create_tts_provider()
        
        if not self.tts_provider:
            self.get_logger().error("Failed to initialize TTS provider!")
            return
        
        # Synthesis + robot playback both happen off the ROS2 executor
        # thread -- see tts_callback()/_tts_worker_loop() docstrings. Set up
        # before _setup_communication() so the queue/event already exist by
        # the time any subscription callback could reference them. Items are
        # ("text", str) from /tts (needs synthesis) or ("audio", bytes) from
        # /robot_speaker_audio (already synthesized, play as-is).
        self._tts_queue: "Queue[tuple[str, str | bytes]]" = Queue()
        self._playback_done_event = threading.Event()
        # Cached result of the last `pactl list sinks` probe, so a speaker
        # lookup does not fork a process on every single utterance.
        self._bt_sink: Optional[str] = None
        self._bt_probe_ts: float = 0.0

        # Setup subscriptions and publishers
        self._setup_communication()

        # RTC topic constants (matches domain/constants/webrtc_topics.py)
        self.RTC_TOPIC = {"AUDIO_HUB_REQ": "rt/api/audiohub/request"}

        self._worker_thread = threading.Thread(
            target=self._tts_worker_loop, daemon=True, name="tts_worker"
        )
        self._worker_thread.start()

        # Log initialization
        self._log_initialization()
    
    def _declare_parameters(self) -> None:
        """Declare all node parameters"""
        self.declare_parameter("api_key", "")
        self.declare_parameter("provider", "supertonic")
        self.declare_parameter("voice_name", "F1")
        self.declare_parameter("local_playback", False)
        self.declare_parameter("bluetooth_playback", True)
        self.declare_parameter("bluetooth_sink_pattern", "bluez_sink")
        self.declare_parameter("bluetooth_probe_interval", 5.0)
        self.declare_parameter("use_cache", True)
        self.declare_parameter("cache_dir", "tts_cache")
        # Larger chunks -> fewer SEND_AUDIO_BLOCK round trips for the same
        # audio, each still spaced by the same 0.15s throttle in
        # _play_on_robot() -- reduces total robot-speaker start latency
        # without changing the send rate (the flooding concern the 0.15s
        # spacing guards against). A 2s reply that needed ~6 chunks (~1.0s
        # of pure throttle delay) at 16KB needs ~3 at 32KB (~0.55s).
        self.declare_parameter("chunk_size", 32768)
        self.declare_parameter("audio_quality", "standard")
        self.declare_parameter("language", "en")
        self.declare_parameter("stability", 0.5)
        self.declare_parameter("similarity_boost", 0.5)
        self.declare_parameter("model_id", "eleven_turbo_v2_5")
        self.declare_parameter("supertonic_steps", 8)
        self.declare_parameter("supertonic_speed", 1.0)
    
    def _load_configuration(self) -> TTSConfig:
        """Load configuration from parameters"""
        provider_str = self.get_parameter("provider").get_parameter_value().string_value
        try:
            provider = TTSProvider(provider_str)
        except ValueError:
            self.get_logger().warn(
                f"Unknown TTS provider '{provider_str}' — falling back to supertonic (offline)"
            )
            provider = TTSProvider.SUPERTONIC

        return TTSConfig(
            api_key=self.get_parameter("api_key").get_parameter_value().string_value,
            provider=provider,
            voice_name=self.get_parameter("voice_name").get_parameter_value().string_value,
            local_playback=self.get_parameter("local_playback").get_parameter_value().bool_value,
            bluetooth_playback=self.get_parameter("bluetooth_playback").get_parameter_value().bool_value,
            bluetooth_sink_pattern=self.get_parameter("bluetooth_sink_pattern").get_parameter_value().string_value,
            bluetooth_probe_interval=self.get_parameter("bluetooth_probe_interval").get_parameter_value().double_value,
            use_cache=self.get_parameter("use_cache").get_parameter_value().bool_value,
            cache_dir=self.get_parameter("cache_dir").get_parameter_value().string_value,
            chunk_size=self.get_parameter("chunk_size").get_parameter_value().integer_value,
            audio_quality=self.get_parameter("audio_quality").get_parameter_value().string_value,
            language=self.get_parameter("language").get_parameter_value().string_value,
            stability=self.get_parameter("stability").get_parameter_value().double_value,
            similarity_boost=self.get_parameter("similarity_boost").get_parameter_value().double_value,
            model_id=self.get_parameter("model_id").get_parameter_value().string_value,
            supertonic_steps=self.get_parameter("supertonic_steps").get_parameter_value().integer_value,
            supertonic_speed=self.get_parameter("supertonic_speed").get_parameter_value().double_value,
        )
    
    def _create_tts_provider(self):
        """Create TTS provider based on configuration"""
        if self.config.provider == TTSProvider.SUPERTONIC:
            try:
                return TTSProvider_Supertonic(self.config)
            except RuntimeError as e:
                self.get_logger().error(str(e))
                return None
        elif self.config.provider == TTSProvider.PIPER:
            try:
                return TTSProvider_Piper(self.config)
            except RuntimeError as e:
                self.get_logger().error(str(e))
                return None
        elif self.config.provider == TTSProvider.ELEVENLABS:
            if not self.config.api_key:
                self.get_logger().error("ElevenLabs API key not provided! Set ELEVENLABS_API_KEY or use TTS_PROVIDER=supertonic.")
                return None
            return TTSProvider_ElevenLabs(self.config)
        elif self.config.provider == TTSProvider.OPENAI:
            if not self.config.api_key:
                self.get_logger().error("OpenAI API key not provided! Set OPENAI_API_KEY or use TTS_PROVIDER=supertonic.")
                return None
            return TTSProvider_OpenAI(self.config)
        elif self.config.provider == TTSProvider.GEMINI:
            if not self.config.api_key:
                self.get_logger().error("Gemini API key not provided! Set GEMINI_API_KEY or use TTS_PROVIDER=supertonic.")
                return None
            return TTSProvider_Gemini(self.config)
        else:
            self.get_logger().error(f"Unsupported TTS provider: {self.config.provider}")
            return None
    
    def _setup_communication(self) -> None:
        """Setup ROS2 communication"""
        self.subscription = self.create_subscription(
            String, "/tts", self.tts_callback, 10
        )
        self.audio_pub = self.create_publisher(WebRtcReq, "/webrtc_req", 10)
        # Raw MP3 bytes forwarded to mic_bridge_node → browser speaker
        self._audio_bridge_pub = self.create_publisher(UInt8MultiArray, "/tts_audio", 10)
        # Robot audiohub playback-state passthrough (see cyclonedds_adapter.py
        # for which connection modes actually populate this today) — lets
        # _play_on_robot() wait for a real completion signal instead of only
        # a duration-based guess.
        self._player_state_sub = self.create_subscription(
            String, "/audiohub_player_state", self._on_audio_player_state, 10
        )
        # Already-synthesized audio that should reach the robot speaker
        # without going through synthesis (see _on_robot_speaker_audio()).
        self._robot_speaker_sub = self.create_subscription(
            UInt8MultiArray, "/robot_speaker_audio", self._on_robot_speaker_audio, 10
        )
        # Published True/False bracketing actual playback (not synthesis) so
        # other nodes can mute mic input while the robot's own speaker is
        # active -- specifically mic_bridge_node's robot-mic path, which has
        # no other way to avoid the robot hearing (and re-triggering
        # commands from) its own spoken replies. See _play_and_signal().
        self._tts_playing_pub = self.create_publisher(Bool, "/tts_playing", 10)

        # Service for cache management
        # self.cache_service = self.create_service(
        #     Empty, "clear_tts_cache", self.clear_cache_callback
        # )
    
    def _on_audio_player_state(self, msg: String) -> None:
        """/audiohub_player_state -- robot playback-state passthrough.

        Payload schema is not confirmed against hardware (see
        cyclonedds_adapter.py), so this is a best-effort keyword match
        rather than a parsed enum: any state text that looks like playback
        has stopped/finished releases _play_on_robot()'s wait early. A
        false negative here just falls back to the duration-based timeout
        that was already the only mechanism before this was wired up; a
        false positive would end the wait early and send STOP_AUDIO before
        the robot is actually done -- not observed, but worth knowing if
        robot audio ever cuts off early once this is live on hardware.
        """
        state_text = (msg.data or "").lower()
        if any(kw in state_text for kw in ("idle", "stop", "finish", "complete", "done")):
            self._playback_done_event.set()

    def tts_callback(self, msg: String) -> None:
        """Handle incoming TTS requests.

        Only enqueues -- synthesis (network calls for API providers) and
        playback (multi-second robot-speaker sequence) both happen on
        _worker_thread, not here, so this callback returns immediately and
        the node's single-threaded executor (rclpy.spin) stays free to
        process the next /tts message, the player-state subscription, etc.
        Callers that publish an announcement and then separately trigger a
        robot action (nav goals, patrol, twist commands) were already
        non-blocking at the pub/sub level -- this additionally keeps
        tts_node itself responsive while a long announcement is still
        playing, e.g. for back-to-back status updates.
        """
        text = msg.data.strip()
        if not text:
            self.get_logger().warn("Received empty TTS request")
            return
        self._tts_queue.put(("text", text))

    def _on_robot_speaker_audio(self, msg: UInt8MultiArray) -> None:
        """/robot_speaker_audio -- already-synthesized audio (e.g. Path C's
        openai_realtime/gemini_live audio_response, which speaks via its own
        realtime-model TTS and bypasses the /tts text pipeline entirely, per
        mic_bridge_node.py). Plays as-is on the robot speaker, no
        synthesis/cache step -- see _process_pregenerated_audio().
        """
        audio_data = bytes(msg.data)
        if not audio_data:
            return
        self._tts_queue.put(("audio", audio_data))

    def _tts_worker_loop(self) -> None:
        """Background thread: processes queued playback jobs one at a time.

        One dedicated worker (not one thread per request) so playback stays
        strictly ordered -- START_AUDIO/SEND_AUDIO_BLOCK/STOP_AUDIO is a
        stateful sequence on the robot's single audio player, and
        interleaving two utterances' chunks would corrupt both, regardless
        of whether they came from /tts (synthesize then play) or
        /robot_speaker_audio (play only).
        """
        while rclpy.ok():
            try:
                kind, payload = self._tts_queue.get(timeout=1.0)
            except Empty:
                continue
            try:
                if kind == "text":
                    self._process_tts_request(payload)
                else:
                    self._process_pregenerated_audio(payload)
            except Exception as e:
                self.get_logger().error(f"❌ TTS processing error: {str(e)}")
            finally:
                self._tts_queue.task_done()

    def _process_pregenerated_audio(self, audio_data: bytes) -> None:
        """Play already-synthesized audio bytes on the robot speaker.

        No cache/synthesize step and no /tts_audio re-broadcast -- the
        caller (mic_bridge_node's Path C) already sent this same audio to
        the browser directly, so re-publishing it here would just double it.
        """
        self.get_logger().info(f"🔈 Pre-generated audio: {len(audio_data)} bytes")
        self._play_and_signal(audio_data)

    def _play_and_signal(self, audio_data: bytes) -> None:
        """Play audio_data (robot speaker or local) while publishing
        /tts_playing around the actual playback window (not synthesis) --
        see the publisher's creation comment for why this exists.
        """
        self._tts_playing_pub.publish(Bool(data=True))
        try:
            # A connected Bluetooth speaker wins when present; _play_bluetooth
            # returns False on any failure so a flaky link degrades to the
            # robot's own speaker rather than dropping the reply entirely.
            if not self._play_bluetooth(audio_data):
                if self.config.local_playback:
                    self._play_locally(audio_data)
                else:
                    self._play_on_robot(audio_data)
        finally:
            # Cooldown before clearing so acoustic reverb/tail dies out
            # first -- mirrors mic_bridge_node's browser-side 600ms
            # post-TTS mic cooldown (_ttsUnmuteTimer in its JS).
            time.sleep(0.6)
            self._tts_playing_pub.publish(Bool(data=False))

    def _process_tts_request(self, text: str) -> None:
        """Synthesize + play one queued TTS request. Runs on _worker_thread."""
        self.get_logger().info(f'🎤 TTS Request: "{text}" (voice: {self.config.voice_name})')

        # Check cache first
        cache_hit = False
        audio_data = self.cache.get(text, self.config.voice_name, self.config.provider.value)

        if audio_data:
            self.get_logger().info("💾 Cache hit - using cached audio")
            cache_hit = True
        else:
            # Generate new speech
            self.get_logger().info("🔊 Generating new speech...")
            audio_data = self.tts_provider.synthesize(text)

            if audio_data:
                # Cache the result
                if self.cache.put(text, self.config.voice_name, self.config.provider.value, audio_data):
                    self.get_logger().info("💾 Audio cached successfully")
            else:
                self.get_logger().error("❌ Failed to generate speech")
                return

        # Forward raw MP3 to browser (mic_bridge_node relays over WebSocket)
        bridge_msg = UInt8MultiArray()
        bridge_msg.data = list(audio_data)
        self._audio_bridge_pub.publish(bridge_msg)

        # Process and play audio
        self._play_and_signal(audio_data)

        # Log success
        status = "cached" if cache_hit else "generated"
        self.get_logger().info(f"✅ TTS completed successfully ({status})")

    def _detect_bluetooth_sink(self) -> Optional[str]:
        """Name of a connected Bluetooth (A2DP) sink, or None.

        Queries PulseAudio via pactl. In the Docker deployment PULSE_SERVER
        points at the host's PulseAudio over loopback TCP, because BlueZ and
        the audio server live on the host while this node runs in the
        container. The result is cached for bluetooth_probe_interval seconds.
        """
        now = time.monotonic()
        if now - self._bt_probe_ts < self.config.bluetooth_probe_interval:
            return self._bt_sink
        self._bt_probe_ts = now

        sink = None
        try:
            result = subprocess.run(
                ["pactl", "list", "sinks", "short"],
                capture_output=True, text=True, timeout=3.0,
            )
            if result.returncode == 0:
                sink = find_bluetooth_sink(
                    result.stdout, self.config.bluetooth_sink_pattern
                )
        except Exception as e:
            self.get_logger().debug(f"Bluetooth sink probe failed: {e}")

        # Log only on transitions, not on every probe.
        if sink != self._bt_sink:
            if sink:
                self.get_logger().info(f"🔵 Bluetooth speaker connected: {sink}")
            else:
                self.get_logger().info("🔵 Bluetooth speaker gone — using robot speaker")
        self._bt_sink = sink
        return sink

    def _play_bluetooth(self, audio_data: bytes) -> bool:
        """Speak through a connected Bluetooth speaker.

        Returns True only if playback actually succeeded, so the caller can
        fall back to the robot speaker on any failure.
        """
        if not self.config.bluetooth_playback:
            return False
        sink = self._detect_bluetooth_sink()
        if not sink:
            return False

        try:
            wav_data = self.audio_processor.convert_to_wav(audio_data, AudioFormat.MP3)
            if not wav_data:
                self.get_logger().error("❌ Failed to convert audio to WAV for Bluetooth")
                return False

            duration = self.audio_processor.get_duration(wav_data, AudioFormat.WAV)
            result = subprocess.run(
                ["paplay", f"--device={sink}"],
                input=wav_data, capture_output=True, timeout=duration + 30.0,
            )
            if result.returncode == 0:
                self.get_logger().info(f"🔊 Bluetooth playback completed ({duration:.1f}s)")
                return True

            stderr = result.stderr.decode("utf-8", "replace").strip()
            self.get_logger().warn(
                f"⚠ Bluetooth playback failed (rc={result.returncode}): {stderr} — falling back to robot speaker"
            )
        except Exception as e:
            self.get_logger().warn(f"⚠ Bluetooth playback error: {e} — falling back to robot speaker")

        # The sink is probably stale (speaker powered off mid-utterance);
        # force a fresh probe rather than waiting out the cache interval.
        self._bt_sink = None
        self._bt_probe_ts = 0.0
        return False

    def _play_locally(self, audio_data: bytes) -> None:
        """Play audio locally"""
        try:
            audio = AudioSegment.from_mp3(io.BytesIO(audio_data))
            play(audio)
            self.get_logger().info("🔊 Local playback completed")
        except Exception as e:
            self.get_logger().error(f"❌ Local playback error: {str(e)}")
    
    def _play_on_robot(self, audio_data: bytes) -> None:
        """Send audio to robot for playback"""
        try:
            # Convert to WAV
            wav_data = self.audio_processor.convert_to_wav(audio_data, AudioFormat.MP3)
            if not wav_data:
                self.get_logger().error("❌ Failed to convert audio to WAV")
                return
            
            # Get audio duration for timing
            duration = self.audio_processor.get_duration(wav_data, AudioFormat.WAV)
            
            # Encode and split into chunks
            b64_encoded = base64.b64encode(wav_data).decode("utf-8")
            chunks = self.audio_processor.split_into_chunks(b64_encoded.encode(), self.config.chunk_size)
            total_chunks = len(chunks)
            
            self.get_logger().info(f"📤 Sending audio to robot: {total_chunks} chunks, {duration:.1f}s duration")
            
            # Send start command
            self._playback_done_event.clear()  # discard any stale signal from a prior utterance
            self._send_audio_command(4001, "")
            time.sleep(0.1)

            # Send audio chunks
            for chunk_idx, chunk in enumerate(chunks, 1):
                audio_block = {
                    "current_block_index": chunk_idx,
                    "total_block_number": total_chunks,
                    "block_content": chunk.decode(),
                }
                self._send_audio_command(4003, json.dumps(audio_block))

                if chunk_idx % 10 == 0:  # Log progress every 10 chunks
                    self.get_logger().info(f"📤 Sent {chunk_idx}/{total_chunks} chunks")

                time.sleep(0.15)  # Prevent flooding

            # Wait for playback to complete: a real signal from
            # /audiohub_player_state if it's wired up for the active
            # connection mode (see cyclonedds_adapter.py), otherwise the
            # same duration-based ceiling as before. Either way this runs on
            # _worker_thread, not the ROS2 executor, so it no longer blocks
            # tts_node from processing the next /tts request or any other
            # callback while this one is "waiting".
            wait_ceiling = duration + 1.0
            self.get_logger().info(f"⏳ Waiting for playback completion (up to {wait_ceiling:.1f}s)...")
            if self._playback_done_event.wait(timeout=wait_ceiling):
                self.get_logger().info("🔈 Robot confirmed playback finished (audiohub player state)")
            else:
                self.get_logger().info(f"⏳ No player-state confirmation within {wait_ceiling:.1f}s — proceeding on timer")

            # Send end command
            self._send_audio_command(4002, "")

            self.get_logger().info("🎵 Robot playback completed")
            
        except Exception as e:
            self.get_logger().error(f"❌ Robot playback error: {str(e)}")
    
    def _send_audio_command(self, api_id: int, parameter: str) -> None:
        """Send audio command to robot"""
        req = WebRtcReq()
        req.api_id = api_id
        req.priority = 0
        req.parameter = parameter
        req.topic = self.RTC_TOPIC["AUDIO_HUB_REQ"]
        self.audio_pub.publish(req)
    
    def _log_initialization(self) -> None:
        """Log initialization details"""
        cache_stats = self.cache.get_cache_stats()
        
        self.get_logger().info("🎤 Enhanced TTS Node Initialized")
        self.get_logger().info(f"   Provider: {self.config.provider.value}")
        self.get_logger().info(f"   Voice: {self.config.voice_name}")
        if self.config.provider == TTSProvider.SUPERTONIC:
            self.get_logger().info(f"   Lang: {self.config.language}  Steps: {self.config.supertonic_steps}  Speed: {self.config.supertonic_speed}")
        fallback = 'Local' if self.config.local_playback else 'Robot'
        if self.config.bluetooth_playback:
            self.get_logger().info(f"   Playback: Bluetooth if connected, else {fallback}")
        else:
            self.get_logger().info(f"   Playback: {fallback}")
        self.get_logger().info(f"   Language: {self.config.language}")
        self.get_logger().info(f"   Quality: {self.config.audio_quality}")
        
        if cache_stats["enabled"]:
            self.get_logger().info(f"   Cache: Enabled ({cache_stats.get('file_count', 0)} files, "
                                 f"{cache_stats.get('total_size_mb', 0)}MB)")
        else:
            self.get_logger().info("   Cache: Disabled")


def main(args=None):
    """Main entry point"""
    rclpy.init(args=args)
    
    try:
        node = EnhancedTTSNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"❌ TTS Node error: {e}")
    finally:
        try:
            rclpy.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    main() 