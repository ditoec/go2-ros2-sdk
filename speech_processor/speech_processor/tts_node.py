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
import time
import hashlib
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import threading

from pydub import AudioSegment
from pydub.playback import play
import rclpy
from rclpy.node import Node
import requests
from std_msgs.msg import String
from go2_interfaces.msg import WebRtcReq


class AudioFormat(Enum):
    """Supported audio formats"""
    MP3 = "mp3"
    WAV = "wav"
    OGG = "ogg"


class TTSProvider(Enum):
    """Supported TTS providers"""
    PIPER = "piper"          # offline neural TTS — best quality, no key required
    ESPEAK = "espeak"        # offline legacy TTS — no key, no model download required
    ELEVENLABS = "elevenlabs"
    GOOGLE = "google"
    AMAZON = "amazon"
    OPENAI = "openai"
    GEMINI = "gemini"


@dataclass
class TTSConfig:
    """Configuration for TTS functionality"""
    api_key: str
    provider: TTSProvider = TTSProvider.PIPER
    voice_name: str = "en_US-lessac-medium"
    local_playback: bool = False
    use_cache: bool = True
    cache_dir: str = "tts_cache"
    chunk_size: int = 16 * 1024
    audio_quality: str = "standard"  # standard, high
    language: str = "en"

    # Piper-specific settings
    piper_voice_dir: str = ""   # default: ~/.local/share/piper/voices
    piper_use_cuda: bool = False

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


class TTSProvider_Piper:
    """Offline neural TTS via Piper — much higher quality than espeak, no API key required.

    Voice model files (.onnx + .onnx.json) are auto-downloaded from Hugging Face
    on first use and cached in piper_voice_dir (default: ~/.local/share/piper/voices).
    The Docker image pre-bakes en_US-lessac-medium so the first container start is instant.

    Voice name follows the Piper naming convention:  lang_COUNTRY-speaker-quality
      e.g. en_US-lessac-medium  (default, ~65 MB)
           en_US-ryan-high      (highest quality English, ~120 MB)
           en_GB-alan-medium
           de_DE-thorsten-medium

    Set piper_use_cuda=True (PIPER_USE_CUDA=true) on platforms with CUDA onnxruntime
    for GPU-accelerated inference (faster synthesis on Jetson NX).
    """

    _DEFAULT_VOICE = "en_US-lessac-medium"
    _HF_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"

    def __init__(self, config: TTSConfig):
        try:
            from piper.voice import PiperVoice as _PiperVoice
            self._PiperVoice = _PiperVoice
        except ImportError as exc:
            raise RuntimeError(
                "piper-tts not installed — run: pip install piper-tts"
            ) from exc

        voice_name = config.voice_name if self._is_valid_piper_voice(config.voice_name) else self._DEFAULT_VOICE
        model_dir = config.piper_voice_dir or os.path.expanduser("~/.local/share/piper/voices")
        self._use_cuda = config.piper_use_cuda
        self._onnx_path, self._json_path = self._ensure_model(model_dir, voice_name)
        self._voice_name = voice_name
        self._voice = None  # lazy-loaded on first synthesize call

    @staticmethod
    def _is_valid_piper_voice(name: str) -> bool:
        """Check that name matches Piper's lang_COUNTRY-speaker-quality format."""
        parts = name.split('-')
        return len(parts) >= 3 and '_' in parts[0]

    def _ensure_model(self, model_dir: str, voice_name: str) -> tuple:
        """Return (onnx_path, json_path), downloading from Hugging Face if not present."""
        os.makedirs(model_dir, exist_ok=True)
        onnx_path = os.path.join(model_dir, f"{voice_name}.onnx")
        json_path = os.path.join(model_dir, f"{voice_name}.onnx.json")

        if os.path.exists(onnx_path) and os.path.exists(json_path):
            return onnx_path, json_path

        parts = voice_name.split('-', 2)
        if len(parts) < 3:
            raise RuntimeError(
                f"Invalid piper voice name '{voice_name}'. "
                "Expected format: lang_COUNTRY-speaker-quality (e.g. en_US-lessac-medium)."
            )
        lang_country, speaker, quality = parts
        lang = lang_country.split('_')[0].lower()
        base_url = f"{self._HF_BASE}/{lang}/{lang_country}/{speaker}/{quality}"

        for fname, dest in [
            (f"{voice_name}.onnx", onnx_path),
            (f"{voice_name}.onnx.json", json_path),
        ]:
            if not os.path.exists(dest):
                url = f"{base_url}/{fname}"
                try:
                    response = requests.get(url, stream=True, timeout=120)
                    response.raise_for_status()
                    with open(dest, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=65536):
                            f.write(chunk)
                except Exception as exc:
                    raise RuntimeError(
                        f"Failed to download piper model '{fname}': {exc}\n"
                        f"Pre-download: wget '{url}' -O '{dest}'"
                    ) from exc

        return onnx_path, json_path

    def _get_voice(self):
        """Load PiperVoice on first call (model parsing takes ~1 s)."""
        if self._voice is None:
            self._voice = self._PiperVoice.load(
                self._onnx_path,
                config_path=self._json_path,
                use_cuda=self._use_cuda,
            )
        return self._voice

    def synthesize(self, text: str) -> Optional[bytes]:
        """Return MP3 bytes synthesised by Piper, or None on failure."""
        import wave
        try:
            voice = self._get_voice()
            wav_buf = io.BytesIO()
            with wave.open(wav_buf, 'wb') as wav_file:
                voice.synthesize(text, wav_file)
            wav_buf.seek(0)
            audio = AudioSegment.from_wav(wav_buf)
            mp3_buf = io.BytesIO()
            audio.export(mp3_buf, format='mp3')
            return mp3_buf.getvalue()
        except Exception:
            return None


class TTSProvider_EspeakNG:
    """Offline TTS via espeak-ng — no API key, no internet, no display required.

    Install:  apt-get install espeak-ng
    Voice:    any espeak-ng voice string ('en', 'en-us', 'en-gb', 'de', …).
              Non-espeak names (e.g. 'nova') are silently replaced with 'en'.
    Speed:    words per minute — 150 is clearer than the espeak default of 175.
    """

    _ESPEAK_PREFIX = {'en', 'de', 'fr', 'es', 'it', 'pt', 'ru', 'zh', 'ja', 'ko', 'ar'}

    def __init__(self, config: TTSConfig):
        import subprocess
        try:
            subprocess.run(['espeak-ng', '--version'], capture_output=True, timeout=5, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            raise RuntimeError(
                "espeak-ng not found — install with: apt-get install espeak-ng"
            ) from exc

        # Accept any voice that starts with a known language code; fall back to 'en'
        v = config.voice_name
        self.voice = v if any(v == lc or v.startswith(f"{lc}-") for lc in self._ESPEAK_PREFIX) else 'en'
        self.speed = 150  # wpm

    def synthesize(self, text: str) -> Optional[bytes]:
        """Return MP3 bytes generated by espeak-ng, or None on failure."""
        import subprocess
        try:
            result = subprocess.run(
                ['espeak-ng', '--stdout', '-v', self.voice, '-s', str(self.speed), text],
                capture_output=True,
                timeout=30,
            )
            if result.returncode != 0 or not result.stdout:
                return None
            # espeak-ng --stdout produces WAV; convert to MP3 for the cache/robot pipeline
            audio = AudioSegment.from_wav(io.BytesIO(result.stdout))
            mp3_buf = io.BytesIO()
            audio.export(mp3_buf, format='mp3')
            return mp3_buf.getvalue()
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return None


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
        
        # Setup subscriptions and publishers
        self._setup_communication()
        
        # RTC topic constants (imported from domain)
        self.RTC_TOPIC = {"AUDIO_HUB_REQ": 1003}  # Fallback if import fails
        
        # Log initialization
        self._log_initialization()
    
    def _declare_parameters(self) -> None:
        """Declare all node parameters"""
        self.declare_parameter("api_key", "")
        self.declare_parameter("provider", "piper")
        self.declare_parameter("voice_name", "en_US-lessac-medium")
        self.declare_parameter("local_playback", False)
        self.declare_parameter("use_cache", True)
        self.declare_parameter("cache_dir", "tts_cache")
        self.declare_parameter("chunk_size", 16384)
        self.declare_parameter("audio_quality", "standard")
        self.declare_parameter("language", "en")
        self.declare_parameter("stability", 0.5)
        self.declare_parameter("similarity_boost", 0.5)
        self.declare_parameter("model_id", "eleven_turbo_v2_5")
        self.declare_parameter("piper_voice_dir", "")
        self.declare_parameter("piper_use_cuda", False)
    
    def _load_configuration(self) -> TTSConfig:
        """Load configuration from parameters"""
        provider_str = self.get_parameter("provider").get_parameter_value().string_value
        try:
            provider = TTSProvider(provider_str)
        except ValueError:
            self.get_logger().warn(
                f"Unknown TTS provider '{provider_str}' — falling back to espeak (offline)"
            )
            provider = TTSProvider.ESPEAK
        
        return TTSConfig(
            api_key=self.get_parameter("api_key").get_parameter_value().string_value,
            provider=provider,
            voice_name=self.get_parameter("voice_name").get_parameter_value().string_value,
            local_playback=self.get_parameter("local_playback").get_parameter_value().bool_value,
            use_cache=self.get_parameter("use_cache").get_parameter_value().bool_value,
            cache_dir=self.get_parameter("cache_dir").get_parameter_value().string_value,
            chunk_size=self.get_parameter("chunk_size").get_parameter_value().integer_value,
            audio_quality=self.get_parameter("audio_quality").get_parameter_value().string_value,
            language=self.get_parameter("language").get_parameter_value().string_value,
            stability=self.get_parameter("stability").get_parameter_value().double_value,
            similarity_boost=self.get_parameter("similarity_boost").get_parameter_value().double_value,
            model_id=self.get_parameter("model_id").get_parameter_value().string_value,
            piper_voice_dir=self.get_parameter("piper_voice_dir").get_parameter_value().string_value,
            piper_use_cuda=self.get_parameter("piper_use_cuda").get_parameter_value().bool_value,
        )
    
    def _create_tts_provider(self):
        """Create TTS provider based on configuration"""
        if self.config.provider == TTSProvider.PIPER:
            try:
                return TTSProvider_Piper(self.config)
            except RuntimeError as e:
                self.get_logger().error(str(e))
                return None
        elif self.config.provider == TTSProvider.ESPEAK:
            try:
                return TTSProvider_EspeakNG(self.config)
            except RuntimeError as e:
                self.get_logger().error(str(e))
                return None
        elif self.config.provider == TTSProvider.ELEVENLABS:
            if not self.config.api_key:
                self.get_logger().error("ElevenLabs API key not provided! Set ELEVENLABS_API_KEY or use TTS_PROVIDER=espeak.")
                return None
            return TTSProvider_ElevenLabs(self.config)
        elif self.config.provider == TTSProvider.OPENAI:
            if not self.config.api_key:
                self.get_logger().error("OpenAI API key not provided! Set OPENAI_API_KEY or use TTS_PROVIDER=espeak.")
                return None
            return TTSProvider_OpenAI(self.config)
        elif self.config.provider == TTSProvider.GEMINI:
            if not self.config.api_key:
                self.get_logger().error("Gemini API key not provided! Set GEMINI_API_KEY or use TTS_PROVIDER=espeak.")
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
        
        # Service for cache management
        # self.cache_service = self.create_service(
        #     Empty, "clear_tts_cache", self.clear_cache_callback
        # )
    
    def tts_callback(self, msg: String) -> None:
        """Handle incoming TTS requests"""
        try:
            text = msg.data.strip()
            if not text:
                self.get_logger().warn("Received empty TTS request")
                return
            
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
            
            # Process and play audio
            if self.config.local_playback:
                self._play_locally(audio_data)
            else:
                self._play_on_robot(audio_data)
            
            # Log success
            status = "cached" if cache_hit else "generated"
            self.get_logger().info(f"✅ TTS completed successfully ({status})")
            
        except Exception as e:
            self.get_logger().error(f"❌ TTS processing error: {str(e)}")
    
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
            
            # Wait for playback to complete
            self.get_logger().info(f"⏳ Waiting for playback completion ({duration:.1f}s)...")
            time.sleep(duration + 1.0)
            
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
        if self.config.provider == TTSProvider.PIPER:
            model_dir = self.config.piper_voice_dir or os.path.expanduser("~/.local/share/piper/voices")
            self.get_logger().info(f"   Model dir: {model_dir}")
            self.get_logger().info(f"   CUDA: {self.config.piper_use_cuda}")
        self.get_logger().info(f"   Playback: {'Local' if self.config.local_playback else 'Robot'}")
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