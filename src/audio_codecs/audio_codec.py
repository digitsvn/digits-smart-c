import asyncio
import gc
import os
import subprocess
import time
from collections import deque
from typing import Optional

import numpy as np
import opuslib
import sounddevice as sd
import soxr

from src.audio_codecs.aec_processor import AECProcessor
from src.audio_codecs.beamforming import BeamformingProcessor
from src.constants.constants import AudioConfig
from src.utils.config_manager import ConfigManager
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class AudioCodec:
    """
    Bộ giải mã âm thanh, chịu trách nhiệm mã hóa ghi âm và giải mã phát lại
    Chức năng chính:
    1. Ghi âm: Micro -> Lấy mẫu lại 16kHz -> Mã hóa Opus -> Gửi
    2. Phát lại: Nhận -> Giải mã Opus 24kHz -> Hàng đợi phát -> Loa
    """

    def __init__(self):
        # Lấy trình quản lý cấu hình
        self.config = ConfigManager.get_instance()

        # Bộ mã hóa Opus: Ghi âm 16kHz, Phát lại 24kHz
        self.opus_encoder = None
        self.opus_decoder = None

        # Thông tin thiết bị
        self.device_input_sample_rate = None
        self.device_output_sample_rate = None
        self.mic_device_id = None  # ID thiết bị micro (chỉ số cố định, không ghi đè sau khi ghi cấu hình)
        self.speaker_device_id = None  # ID thiết bị loa (chỉ số cố định)

        # Bộ lấy mẫu lại: Ghi âm lấy mẫu lại về 16kHz, phát lại lấy mẫu lại theo thiết bị
        self.input_resampler = None  # Tỷ lệ mẫu thiết bị -> 16kHz
        self.output_resampler = None  # 24kHz -> Tỷ lệ mẫu thiết bị (để phát)

        # Bộ đệm lấy mẫu lại
        self._resample_input_buffer = deque()
        self._resample_output_buffer = deque()

        self._device_input_frame_size = None
        self._is_closing = False

        # Đối tượng luồng âm thanh
        self.input_stream = None  # Luồng ghi âm
        self.output_stream = None  # Luồng phát lại

        # Hàng đợi: Phát hiện từ đánh thức và bộ đệm phát
        self._wakeword_buffer = asyncio.Queue(maxsize=100)
        self._output_buffer = asyncio.Queue(maxsize=500)

        # Callback mã hóa thời gian thực (gửi trực tiếp, không qua hàng đợi)
        self._encoded_audio_callback = None

        # Bộ xử lý AEC
        self.aec_processor = AECProcessor()
        self._aec_enabled = False
        
        # Echo suppression: Mute mic khi đang phát và ngay sau khi phát xong
        self._is_playing = False
        self._playback_end_time = 0
        self._echo_guard_duration = 0.5  # 500ms guard time sau khi ngừng phát
        self._last_audio_write_time = 0  # Track khi nào lần cuối write audio
        self._echo_timeout = 10.0  # Tự động reset echo period sau 10s nếu stuck
        
        # I2S INMP441 Microphone support
        self._i2s_enabled = False
        self._i2s_stereo = False  # True nếu có 2 mic (stereo beamforming)
        
        # HDMI Audio output
        self._hdmi_audio = False
        self._hdmi_device_name = None  # e.g., "vc4hdmi0"
        self._hdmi_aplay_process = None  # Subprocess for HDMI output via aplay
        self._hdmi_use_aplay = False  # Flag to use aplay instead of sounddevice
        
        # 3.5mm Jack Audio output (đồng thời với HDMI)
        self._jack_audio = False  # Enable 3.5mm jack output
        self._jack_device_name = "Headphones"  # Default Pi headphone jack
        self._jack_aplay_process = None  # Subprocess for 3.5mm output
        self._jack_use_aplay = False
        
        # PulseAudio support (giải quyết conflict video vs AI audio)
        self._pulseaudio_enabled = False
        
        # Beamforming processor for dual mic
        self.beamforming = BeamformingProcessor()
        self._beamforming_enabled = False
        self._mic_distance = 8.0  # Default 8cm giữa 2 mic
        self._speaker_angle = 180.0  # Default loa ở phía sau
        
        # Software gain cho MIC (nhân lên để tăng amplitude)
        # I2S INMP441 có output thấp, cần gain ~8-16x
        self._mic_gain = 12.0  # Tăng 12x, có thể điều chỉnh
        
        # Debug logging
        self._last_log_time = 0

    # -----------------------
    # Phương thức hỗ trợ tự động chọn thiết bị
    # -----------------------
    def _auto_pick_device(self, kind: str) -> Optional[int]:
        """
        Tự động chọn chỉ mục thiết bị ổn định (ưu tiên WASAPI).
        kind: 'input' hoặc 'output'
        """
        assert kind in ("input", "output")
        try:
            devices = sd.query_devices()
            hostapis = sd.query_hostapis()
        except Exception as e:
            logger.warning(f"Liệt kê thiết bị thất bại: {e}")
            return None

        # 1) Ưu tiên sử dụng thiết bị mặc định của WASAPI HostAPI (nếu có)
        wasapi_index = None
        for idx, ha in enumerate(hostapis):
            name = ha.get("name", "")
            if "WASAPI" in name:
                key = (
                    "default_input_device"
                    if kind == "input"
                    else "default_output_device"
                )
                cand = ha.get(key, -1)
                if isinstance(cand, int) and 0 <= cand < len(devices):
                    d = devices[cand]
                    if (kind == "input" and d["max_input_channels"] > 0) or (
                        kind == "output" and d["max_output_channels"] > 0
                    ):
                        wasapi_index = cand
                        break
        if wasapi_index is not None:
            return wasapi_index

        # 2) Phương án thay thế: Khớp tên trả về từ mặc định hệ thống (kind) + ưu tiên WASAPI
        try:
            default_info = sd.query_devices(kind=kind)  # Không kích hoạt -1
            default_name = default_info.get("name")
        except Exception:
            default_name = None

        scored = []
        for i, d in enumerate(devices):
            if kind == "input":
                ok = d["max_input_channels"] > 0
            else:
                ok = d["max_output_channels"] > 0
            if not ok:
                continue
            host_name = hostapis[d["hostapi"]]["name"]
            score = 0
            if "WASAPI" in host_name:
                score += 5
            if default_name and d["name"] == default_name:
                score += 10
            # Điểm cộng nhỏ: Từ khóa điểm cuối khả dụng phổ biến
            if any(
                k in d["name"]
                for k in [
                    "Speaker",
                    "Loa",
                    "扬声器",
                    "Realtek",
                    "USB",
                    "AMD",
                    "HDMI",
                    "Monitor",
                ]
            ):
                score += 1
            scored.append((score, i))

        if scored:
            scored.sort(reverse=True)
            return scored[0][1]

        # 3) Cuối cùng: Thiết bị đầu tiên có kênh
        for i, d in enumerate(devices):
            if (kind == "input" and d["max_input_channels"] > 0) or (
                kind == "output" and d["max_output_channels"] > 0
            ):
                return i
        return None
    
    def _find_i2s_device(self, devices) -> Optional[int]:
        """
        Tìm thiết bị I2S microphone (INMP441).
        Ưu tiên các tên chứa 'i2s', 'snd_rpi', 'googlevoicehat', 'seeed'.
        """
        i2s_keywords = [
            "i2s", "i2smic", "snd_rpi", "googlevoicehat", 
            "seeed", "respeaker", "inmp441", "mems"
        ]
        
        for i, d in enumerate(devices):
            device_name = d["name"].lower()
            if d["max_input_channels"] > 0:
                for keyword in i2s_keywords:
                    if keyword in device_name:
                        logger.info(f"Tìm thấy I2S device: [{i}] {d['name']}")
                        return i
        
        # Fallback: tìm thiết bị có tên "hw:..." (thường là I2S)
        for i, d in enumerate(devices):
            device_name = d["name"].lower()
            if d["max_input_channels"] > 0 and "hw:" in device_name:
                # Loại trừ USB và Headphones
                if "usb" not in device_name and "headphone" not in device_name:
                    logger.info(f"Fallback I2S device: [{i}] {d['name']}")
                    return i
        
        return None

    def _find_hdmi_device(self, devices) -> Optional[int]:
        """
        Tìm thiết bị HDMI audio output.
        Ưu tiên các tên chứa 'hdmi', 'vc4hdmi'.
        Cũng lưu tên device cho aplay.
        """
        hdmi_keywords = [
            "vc4hdmi", "hdmi", "vc4-hdmi"
        ]
        
        for i, d in enumerate(devices):
            device_name = d["name"].lower()
            if d["max_output_channels"] > 0:
                for keyword in hdmi_keywords:
                    if keyword in device_name:
                        logger.info(f"Tìm thấy HDMI device: [{i}] {d['name']}")
                        # Lưu device name cho aplay (extract CARD name)
                        # Device name format: "vc4hdmi0: vc4-hdmi-0, bcm2835 HDMI 1"
                        self._hdmi_device_name = self._extract_alsa_card_name(d["name"])
                        return i
        
        return None
    
    def _extract_alsa_card_name(self, device_name: str) -> str:
        """
        Extract ALSA card name từ sounddevice device name.
        Ví dụ: "vc4-hdmi-0: MAI PCM i2s-hifi-0 (hw:1,0)" -> "vc4hdmi0"
        """

        # Thử lấy từ aplay -l để có card name chính xác
        try:
            result = subprocess.run(
                ["aplay", "-l"],
                capture_output=True, text=True, timeout=5
            )
            
            # Tìm HDMI card trong output
            # Format: "card 1: vc4hdmi0 [vc4-hdmi-0], device 0:..."
            for line in result.stdout.split('\n'):
                if 'hdmi' in line.lower() and 'card' in line.lower():
                    # Extract card name từ format "card X: NAME [...
                    parts = line.split(':')
                    if len(parts) >= 2:
                        card_part = parts[1].strip()
                        # Card name là phần đầu trước space hoặc [
                        card_name = card_part.split()[0].split('[')[0].strip()
                        if card_name:
                            logger.info(f"Detected ALSA HDMI card: {card_name}")
                            return card_name
                            
        except Exception as e:
            logger.warning(f"aplay -l failed: {e}")
        
        # Fallback: thử các card name phổ biến
        hdmi_cards = ["vc4hdmi0", "vc4hdmi1", "vc4hdmi"]
        name_lower = device_name.lower()
        
        for card in hdmi_cards:
            if card in name_lower:
                return card
        
        # Fallback cuối: lấy phần đầu trước dấu :
        if ":" in device_name:
            first_part = device_name.split(":")[0].strip()
            # Loại bỏ ký tự không hợp lệ
            card_name = first_part.replace("-", "").replace(" ", "")
            return card_name if card_name else "vc4hdmi0"
        
        return "vc4hdmi0"  # Default
    
    def _set_alsa_hdmi_default(self):
        """
        Set ALSA default output device to HDMI.
        Tạo file ~/.asoundrc hoặc set environment.
        """

        try:
            hdmi_card = self._hdmi_device_name or "vc4hdmi0"
            
            # Set SDL và ALSA environment variables
            os.environ["SDL_AUDIODRIVER"] = "alsa"
            os.environ["AUDIODEV"] = f"plughw:CARD={hdmi_card}"
            
            # Thử set volume cho HDMI
            try:
                subprocess.run(
                    ["amixer", "-c", hdmi_card, "set", "PCM", "100%"],
                    capture_output=True, timeout=5
                )
                logger.info(f"HDMI volume set to 100% on {hdmi_card}")
            except Exception as e:
                logger.debug(f"amixer set volume failed: {e}")
            
            logger.info(f"ALSA HDMI default set: {hdmi_card}")
            
        except Exception as e:
            logger.warning(f"Set ALSA HDMI default failed: {e}")
    
    def _start_hdmi_aplay(self):
        """
        Khởi động audio subprocess cho HDMI output.
        - Nếu có PulseAudio: dùng paplay (chia sẻ output với video)
        - Nếu không: dùng aplay với nhiều device options
        """
        
        hdmi_card = self._hdmi_device_name or "vc4hdmi0"
        
        # Dùng ALSA aplay trực tiếp với plughw
        # Video đã bị mute bằng GST_AUDIO_SINK=fakesink nên HDMI free
        cmd = [
            "aplay",
            "-D", f"plughw:CARD={hdmi_card}",
            "-f", "S16_LE",
            "-r", str(AudioConfig.OUTPUT_SAMPLE_RATE),
            "-c", "1",
            "-q",
            "-"
        ]
        
        # Retry loop - đợi nếu device chưa sẵn sàng
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Starting HDMI aplay (attempt {attempt+1}/{max_retries}): plughw:CARD={hdmi_card}")
                self._hdmi_aplay_process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE
                )
                
                time.sleep(0.3)
                if self._hdmi_aplay_process.poll() is not None:
                    stderr_output = self._hdmi_aplay_process.stderr.read().decode('utf-8', errors='ignore')
                    if "busy" in stderr_output.lower():
                        logger.warning(f"HDMI device busy, waiting...")
                        time.sleep(2)
                        continue
                    else:
                        logger.warning(f"aplay failed: {stderr_output[:100]}")
                        continue
                
                # Warmup
                try:
                    silence = b'\x00' * 4800
                    self._hdmi_aplay_process.stdin.write(silence)
                    self._hdmi_aplay_process.stdin.flush()
                except Exception as e:
                    logger.warning(f"aplay warmup failed: {e}")
                    continue
                
                self._hdmi_use_aplay = True
                logger.info(f"🔊 HDMI aplay started successfully!")
                return
                
            except Exception as e:
                logger.warning(f"aplay attempt {attempt+1} failed: {e}")
                time.sleep(1)
        
        # Hết retry
        logger.error(f"Failed to start HDMI aplay after {max_retries} attempts")
        self._hdmi_use_aplay = False
    
    def _stop_hdmi_aplay(self):
        """Dừng HDMI aplay subprocess."""
        if self._hdmi_aplay_process:
            try:
                self._hdmi_aplay_process.stdin.close()
                self._hdmi_aplay_process.terminate()
                self._hdmi_aplay_process.wait(timeout=2)
            except Exception as e:
                logger.debug(f"HDMI aplay terminate failed: {e}")
                try:
                    self._hdmi_aplay_process.kill()
                except Exception:
                    pass
            self._hdmi_aplay_process = None
            logger.info("HDMI aplay stopped")
    
    def _start_jack_aplay(self):
        """Khởi động aplay subprocess cho 3.5mm jack output."""
        
        jack_card = self._jack_device_name or "Headphones"
        
        # Thử nhiều device format
        device_options = [
            f"dmix:CARD={jack_card}",
            f"default:CARD={jack_card}",
            f"plughw:CARD={jack_card}",
        ]
        
        for device in device_options:
            cmd = [
                "aplay",
                "-D", device,
                "-f", "S16_LE",
                "-r", str(AudioConfig.OUTPUT_SAMPLE_RATE),
                "-c", "1",
                "-q",
                "-"
            ]
            
            try:
                logger.info(f"Trying Jack device: {device}")
                self._jack_aplay_process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE
                )
                
                time.sleep(0.3)
                if self._jack_aplay_process.poll() is not None:
                    stderr_output = self._jack_aplay_process.stderr.read().decode('utf-8', errors='ignore')
                    logger.warning(f"Jack device {device} failed: {stderr_output[:100]}")
                    continue
                
                # Warmup
                try:
                    silence = b'\x00' * 4800
                    self._jack_aplay_process.stdin.write(silence)
                    self._jack_aplay_process.stdin.flush()
                except Exception as e:
                    logger.warning(f"Jack aplay warmup failed: {e}")
                    continue
                
                self._jack_use_aplay = True
                logger.info(f"🎧 Jack aplay started with device: {device}")
                return
                
            except Exception as e:
                logger.warning(f"Jack device {device} exception: {e}")
                continue
        
        logger.warning(f"Failed to start Jack aplay (not critical)")
        self._jack_use_aplay = False
    
    def _stop_jack_aplay(self):
        """Dừng 3.5mm jack aplay subprocess."""
        if self._jack_aplay_process:
            try:
                self._jack_aplay_process.stdin.close()
                self._jack_aplay_process.terminate()
                self._jack_aplay_process.wait(timeout=2)
            except Exception as e:
                logger.debug(f"Jack aplay terminate failed: {e}")
                try:
                    self._jack_aplay_process.kill()
                except Exception:
                    pass
            self._jack_aplay_process = None
            logger.info("Jack aplay stopped")
    
    def _write_jack_audio(self, audio_data):
        """Ghi audio data vào 3.5mm jack aplay process."""
        if self._jack_aplay_process and self._jack_aplay_process.stdin:
            try:
                self._jack_aplay_process.stdin.write(audio_data.tobytes())
                self._jack_aplay_process.stdin.flush()
            except BrokenPipeError:
                logger.warning("Jack aplay broken pipe, restarting...")
                self._stop_jack_aplay()
                self._start_jack_aplay()
            except Exception as e:
                logger.warning(f"Jack aplay write error: {e}")
    
    def _check_aplay_health(self) -> bool:
        """
        Kiểm tra aplay process còn hoạt động không.
        Returns True nếu healthy, False nếu cần restart.
        """
        if not self._hdmi_aplay_process:
            return False
        
        # poll() returns None nếu process còn chạy
        return self._hdmi_aplay_process.poll() is None
    
    def _write_hdmi_audio(self, audio_data):
        """
        Ghi audio data vào HDMI aplay process.
        audio_data: numpy array int16
        """
        # Health check trước khi ghi
        if not self._check_aplay_health():
            logger.warning("HDMI aplay process died, restarting...")
            self._stop_hdmi_aplay()
            self._start_hdmi_aplay()
            if not self._check_aplay_health():
                logger.error("Failed to restart HDMI aplay")
                return
        
        if self._hdmi_aplay_process and self._hdmi_aplay_process.stdin:
            try:
                self._hdmi_aplay_process.stdin.write(audio_data.tobytes())
                self._hdmi_aplay_process.stdin.flush()
            except BrokenPipeError:
                # aplay process đã chết
                logger.warning("HDMI aplay broken pipe, restarting...")
                self._stop_hdmi_aplay()
                self._start_hdmi_aplay()
            except Exception as e:
                logger.warning(f"HDMI aplay write error: {e}")

    async def initialize(self):
        """
        Khởi tạo thiết bị âm thanh.
        """
        try:
            logger.info("=== Bắt đầu khởi tạo Audio Codec ===")
            
            # 🔊 Audio Setup: Restart PulseAudio và các services
            # Giải quyết conflict giữa video (gstreamer) và AI audio (aplay)
            try:
                from src.audio_codecs.audio_setup import setup_audio_environment
                self._pulseaudio_enabled = setup_audio_environment()
                if self._pulseaudio_enabled:
                    logger.info("✅ PulseAudio ready - sẽ dùng paplay cho audio output")
            except Exception as e:
                logger.warning(f"Audio setup failed: {e}")
                self._pulseaudio_enabled = False
            
            # Hiển thị và chọn thiết bị âm thanh (tự động chọn lần đầu và ghi vào cấu hình; không ghi đè sau đó)
            await self._select_audio_devices()
            
            logger.info(f"MIC device ID: {self.mic_device_id}")
            logger.info(f"Speaker device ID: {self.speaker_device_id}")
            
            # Set ALSA default device cho HDMI nếu enabled
            if self._hdmi_audio and self._hdmi_device_name:
                self._set_alsa_hdmi_default()
                # Khởi động aplay/paplay subprocess cho HDMI output
                self._start_hdmi_aplay()
                if self._hdmi_use_aplay:
                    logger.info("🔊 HDMI output sẽ dùng aplay thay vì sounddevice")
                else:
                    logger.warning("⚠️ HDMI aplay failed, sẽ thử sounddevice hoặc skip output")
            
            # Khởi động 3.5mm Jack aplay nếu enabled (đồng thời với HDMI)
            if self._jack_audio:
                self._start_jack_aplay()
                if self._jack_use_aplay:
                    logger.info("🎧 Jack output ready (đồng thời với HDMI)")
                else:
                    logger.warning("⚠️ Jack aplay failed (không ảnh hưởng HDMI)")

            # Lấy thông tin mặc định đầu vào/đầu ra an toàn (tránh -1)
            try:
                if self.mic_device_id is not None and self.mic_device_id >= 0:
                    input_device_info = sd.query_devices(self.mic_device_id)
                    logger.info(f"Input device: {input_device_info['name']}")
                else:
                    input_device_info = sd.query_devices(kind="input")
                    logger.info(f"Using default input: {input_device_info['name']}")
            except Exception as e:
                logger.error(f"Lỗi query input device: {e}")
                input_device_info = sd.query_devices(kind="input")

            try:
                if self.speaker_device_id is not None and self.speaker_device_id >= 0:
                    output_device_info = sd.query_devices(self.speaker_device_id)
                    logger.info(f"Output device: {output_device_info['name']}")
                else:
                    output_device_info = sd.query_devices(kind="output")
                    logger.info(f"Using default output: {output_device_info['name']}")
            except Exception as e:
                logger.error(f"Lỗi query output device: {e}")
                output_device_info = sd.query_devices(kind="output")

            self.device_input_sample_rate = int(input_device_info["default_samplerate"])
            self.device_output_sample_rate = int(
                output_device_info["default_samplerate"]
            )

            frame_duration_sec = AudioConfig.FRAME_DURATION / 1000
            self._device_input_frame_size = int(
                self.device_input_sample_rate * frame_duration_sec
            )

            logger.info(
                f"Tỷ lệ mẫu đầu vào: {self.device_input_sample_rate}Hz, Đầu ra: {self.device_output_sample_rate}Hz"
            )

            await self._create_resamplers()

            # Không thay đổi mặc định toàn cục, để mỗi luồng tự mang device / samplerate
            sd.default.samplerate = None
            sd.default.channels = AudioConfig.CHANNELS
            sd.default.dtype = np.int16

            await self._create_streams()

            # Bộ giải mã Opus
            self.opus_encoder = opuslib.Encoder(
                AudioConfig.INPUT_SAMPLE_RATE,
                AudioConfig.CHANNELS,
                opuslib.APPLICATION_AUDIO,
            )
            self.opus_decoder = opuslib.Decoder(
                AudioConfig.OUTPUT_SAMPLE_RATE, AudioConfig.CHANNELS
            )

            # Khởi tạo bộ xử lý AEC
            try:
                await self.aec_processor.initialize()
                self._aec_enabled = True
                logger.info("Bộ xử lý AEC đã được bật")
            except Exception as e:
                logger.warning(f"Khởi tạo AEC thất bại, sẽ sử dụng âm thanh gốc: {e}")
                self._aec_enabled = False

            logger.info("Khởi tạo âm thanh hoàn tất")
        except Exception as e:
            logger.error(f"Khởi tạo thiết bị âm thanh thất bại: {e}")
            await self.close()
            raise

    async def _create_resamplers(self):
        """
        Tạo bộ lấy mẫu lại. Đầu vào: Tỷ lệ mẫu thiết bị -> 16kHz (để mã hóa). Đầu ra: 24kHz -> Tỷ lệ mẫu thiết bị (để phát).
        """
        # Bộ lấy mẫu lại đầu vào: Tỷ lệ mẫu thiết bị -> 16kHz (để mã hóa)
        if self.device_input_sample_rate != AudioConfig.INPUT_SAMPLE_RATE:
            self.input_resampler = soxr.ResampleStream(
                self.device_input_sample_rate,
                AudioConfig.INPUT_SAMPLE_RATE,
                AudioConfig.CHANNELS,
                dtype="int16",
                quality="QQ",
            )
            logger.info(f"Lấy mẫu lại đầu vào: {self.device_input_sample_rate}Hz -> 16kHz")

        # Bộ lấy mẫu lại đầu ra: 24kHz -> Tỷ lệ mẫu thiết bị
        if self.device_output_sample_rate != AudioConfig.OUTPUT_SAMPLE_RATE:
            self.output_resampler = soxr.ResampleStream(
                AudioConfig.OUTPUT_SAMPLE_RATE,
                self.device_output_sample_rate,
                AudioConfig.CHANNELS,
                dtype="int16",
                quality="QQ",
            )
            logger.info(
                f"Lấy mẫu lại đầu ra: {AudioConfig.OUTPUT_SAMPLE_RATE}Hz -> {self.device_output_sample_rate}Hz"
            )

    async def _select_audio_devices(self):
        """Hiển thị và chọn thiết bị âm thanh.

        Ưu tiên thiết bị trong file cấu hình, nếu không có sẽ tự động chọn và lưu vào cấu hình (chỉ ghi lần đầu, không ghi đè sau đó).
        """
        try:
            audio_config = self.config.get_config("AUDIO_DEVICES", {}) or {}
            
            # Load I2S configuration
            self._i2s_enabled = audio_config.get("i2s_enabled", False)
            self._i2s_stereo = audio_config.get("i2s_stereo", False)
            
            # Load beamforming configuration
            self._beamforming_enabled = audio_config.get("beamforming_enabled", False)
            self._mic_distance = audio_config.get("mic_distance", 8.0)
            self._speaker_angle = audio_config.get("speaker_angle", 180.0)
            
            if self._i2s_enabled:
                logger.info(f"I2S Mode: {'Stereo (2 INMP441)' if self._i2s_stereo else 'Mono (1 INMP441)'}")
            
            # Cấu hình beamforming nếu stereo enabled
            if self._i2s_stereo and self._beamforming_enabled:
                self.beamforming.set_mic_distance(self._mic_distance)
                self.beamforming.enable(True)
                self.beamforming.enable_null_steering(True)
                logger.info(f"Beamforming enabled: mic_distance={self._mic_distance}cm, speaker_angle={self._speaker_angle}°")

            # HDMI audio configuration
            self._hdmi_audio = audio_config.get("hdmi_audio", False)
            if self._hdmi_audio:
                logger.info("HDMI Audio output enabled")
            
            # 3.5mm Jack audio configuration (có thể dùng đồng thời với HDMI)
            self._jack_audio = audio_config.get("jack_audio", False)
            if self._jack_audio:
                self._jack_device_name = audio_config.get("jack_device_name", "Headphones")
                logger.info(f"3.5mm Jack audio enabled: {self._jack_device_name}")

            # Có cấu hình rõ ràng chưa (quyết định có ghi lại hay không)
            had_cfg_input = "input_device_id" in audio_config
            had_cfg_output = "output_device_id" in audio_config

            input_device_id = audio_config.get("input_device_id")
            output_device_id = audio_config.get("output_device_id")

            devices = sd.query_devices()
            
            # Auto-detect I2S microphone nếu enabled
            if self._i2s_enabled and input_device_id is None:
                i2s_device = self._find_i2s_device(devices)
                if i2s_device is not None:
                    input_device_id = i2s_device
                    logger.info(f"Auto-detected I2S microphone: [{i2s_device}] {devices[i2s_device]['name']}")

            # Auto-detect HDMI output device nếu enabled
            # BẮT BUỘC dùng HDMI khi hdmi_audio=True (bỏ qua config cũ)
            if self._hdmi_audio:
                hdmi_device = self._find_hdmi_device(devices)
                if hdmi_device is not None:
                    output_device_id = hdmi_device  # Force HDMI
                    logger.info(f"🔊 FORCED HDMI output: [{hdmi_device}] {devices[hdmi_device]['name']}")
                else:
                    logger.warning("HDMI enabled but no HDMI device found!")

            # --- Xác thực thiết bị đầu vào trong cấu hình ---
            if input_device_id is not None:
                try:
                    if isinstance(input_device_id, int) and 0 <= input_device_id < len(
                        devices
                    ):
                        d = devices[input_device_id]
                        if d["max_input_channels"] > 0:
                            self.mic_device_id = input_device_id
                            logger.info(
                                f"Sử dụng thiết bị micro đã cấu hình: [{input_device_id}] {d['name']}"
                            )
                        else:
                            logger.warning(
                                f"Thiết bị cấu hình [{input_device_id}] không hỗ trợ đầu vào, sẽ tự động chọn"
                            )
                            self.mic_device_id = None
                    else:
                        logger.warning(
                            f"ID thiết bị đầu vào cấu hình [{input_device_id}] không hợp lệ, sẽ tự động chọn"
                        )
                        self.mic_device_id = None
                except Exception as e:
                    logger.warning(f"Xác thực thiết bị đầu vào thất bại: {e}, sẽ tự động chọn")
                    self.mic_device_id = None
            else:
                self.mic_device_id = None

            # --- Xác thực thiết bị đầu ra trong cấu hình ---
            if output_device_id is not None:
                try:
                    if isinstance(
                        output_device_id, int
                    ) and 0 <= output_device_id < len(devices):
                        d = devices[output_device_id]
                        if d["max_output_channels"] > 0:
                            self.speaker_device_id = output_device_id
                            logger.info(
                                f"Sử dụng thiết bị loa đã cấu hình: [{output_device_id}] {d['name']}"
                            )
                        else:
                            logger.warning(
                                f"Thiết bị cấu hình [{output_device_id}] không hỗ trợ đầu ra, sẽ tự động chọn"
                            )
                            self.speaker_device_id = None
                    else:
                        logger.warning(
                            f"ID thiết bị đầu ra cấu hình [{output_device_id}] không hợp lệ, sẽ tự động chọn"
                        )
                        self.speaker_device_id = None
                except Exception as e:
                    logger.warning(f"Xác thực thiết bị đầu ra thất bại: {e}, sẽ tự động chọn")
                    self.speaker_device_id = None
            else:
                self.speaker_device_id = None

            # --- Nếu bất kỳ mục nào trống, tự động chọn (chỉ ghi vào cấu hình lần đầu) ---
            picked_input = self.mic_device_id
            picked_output = self.speaker_device_id

            if picked_input is None:
                picked_input = self._auto_pick_device("input")
                if picked_input is not None:
                    self.mic_device_id = picked_input
                    d = devices[picked_input]
                    logger.info(f"Tự động chọn thiết bị micro: [{picked_input}] {d['name']}")
                else:
                    logger.warning(
                        "Không tìm thấy thiết bị đầu vào khả dụng (sẽ sử dụng mặc định hệ thống, không ghi chỉ mục)."
                    )

            if picked_output is None:
                picked_output = self._auto_pick_device("output")
                if picked_output is not None:
                    self.speaker_device_id = picked_output
                    d = devices[picked_output]
                    logger.info(f"Tự động chọn thiết bị loa: [{picked_output}] {d['name']}")
                else:
                    logger.warning(
                        "Không tìm thấy thiết bị đầu ra khả dụng (sẽ sử dụng mặc định hệ thống, không ghi chỉ mục)."
                    )

            # --- Chỉ ghi khi cấu hình ban đầu thiếu mục tương ứng (tránh ghi đè lần thứ hai) ---
            need_write = (not had_cfg_input and picked_input is not None) or (
                not had_cfg_output and picked_output is not None
            )
            if need_write:
                await self._save_default_audio_config(
                    input_device_id=picked_input if not had_cfg_input else None,
                    output_device_id=picked_output if not had_cfg_output else None,
                )

        except Exception as e:
            logger.warning(f"Chọn thiết bị thất bại: {e}, sẽ sử dụng mặc định hệ thống (không ghi vào cấu hình)")
            # Cho phép None, để PortAudio dùng endpoint mặc định
            self.mic_device_id = (
                self.mic_device_id if isinstance(self.mic_device_id, int) else None
            )
            self.speaker_device_id = (
                self.speaker_device_id
                if isinstance(self.speaker_device_id, int)
                else None
            )

    async def _save_default_audio_config(
        self, input_device_id: Optional[int], output_device_id: Optional[int]
    ):
        """
        Lưu cấu hình thiết bị âm thanh mặc định vào tệp cấu hình (chỉ cho các thiết bị không trống được truyền vào; sẽ không ghi đè các trường hiện có).
        """
        try:
            devices = sd.query_devices()
            audio_config_patch = {}

            # Lưu cấu hình thiết bị đầu vào
            if input_device_id is not None and 0 <= input_device_id < len(devices):
                d = devices[input_device_id]
                audio_config_patch.update(
                    {
                        "input_device_id": input_device_id,
                        "input_device_name": d["name"],
                        "input_sample_rate": int(d["default_samplerate"]),
                    }
                )

            # Lưu cấu hình thiết bị đầu ra
            if output_device_id is not None and 0 <= output_device_id < len(devices):
                d = devices[output_device_id]
                audio_config_patch.update(
                    {
                        "output_device_id": output_device_id,
                        "output_device_name": d["name"],
                        "output_sample_rate": int(d["default_samplerate"]),
                    }
                )

            if audio_config_patch:
                # hợp nhất: không ghi đè khóa hiện có
                current = self.config.get_config("AUDIO_DEVICES", {}) or {}
                for k, v in audio_config_patch.items():
                    if k not in current:  # Chỉ ghi khi chưa có
                        current[k] = v
                success = self.config.update_config("AUDIO_DEVICES", current)
                if success:
                    logger.info("Đã ghi thiết bị âm thanh mặc định vào cấu hình (lần đầu).")
                else:
                    logger.warning("Lưu cấu hình thiết bị âm thanh thất bại")
        except Exception as e:
            logger.error(f"Lưu cấu hình thiết bị âm thanh mặc định thất bại: {e}")

    async def _create_streams(self):
        """
        Tạo luồng âm thanh.
        """
        try:
            # Luồng đầu vào micro
            self.input_stream = sd.InputStream(
                device=self.mic_device_id,  # None=mặc định hệ thống; hoặc chỉ mục cố định
                samplerate=self.device_input_sample_rate,
                channels=AudioConfig.CHANNELS,
                dtype=np.int16,
                blocksize=self._device_input_frame_size,
                callback=self._input_callback,
                finished_callback=self._input_finished_callback,
                latency="low",
            )

            # Chọn tỷ lệ mẫu đầu ra dựa trên tỷ lệ mẫu được thiết bị hỗ trợ
            if self.device_output_sample_rate == AudioConfig.OUTPUT_SAMPLE_RATE:
                # Thiết bị hỗ trợ 24kHz, sử dụng trực tiếp
                output_sample_rate = AudioConfig.OUTPUT_SAMPLE_RATE
                device_output_frame_size = AudioConfig.OUTPUT_FRAME_SIZE
            else:
                # Thiết bị không hỗ trợ 24kHz, sử dụng tỷ lệ mẫu mặc định của thiết bị và bật lấy mẫu lại
                output_sample_rate = self.device_output_sample_rate
                device_output_frame_size = int(
                    self.device_output_sample_rate * (AudioConfig.FRAME_DURATION / 1000)
                )

            # Log thông tin output device
            if self.speaker_device_id is not None:
                devices = sd.query_devices()
                if 0 <= self.speaker_device_id < len(devices):
                    out_dev = devices[self.speaker_device_id]
                    logger.info(f"🔊 Output device: [{self.speaker_device_id}] {out_dev['name']} (HDMI: {getattr(self, '_hdmi_audio', False)})")

            # vì aplay đã xử lý output rồi
            if self._hdmi_use_aplay:
                logger.info("🔊 Bỏ qua sounddevice OutputStream - dùng aplay cho HDMI")
                self.output_stream = None
            elif self._hdmi_audio and not self._hdmi_use_aplay:
                # HDMI được bật nhưng aplay fail (có thể device busy bởi video)
                # Skip sounddevice vì cũng sẽ fail với cùng lý do
                logger.warning("⚠️ HDMI audio enabled nhưng aplay không khởi động được - skip output")
                self.output_stream = None
            else:
                self.output_stream = sd.OutputStream(
                    device=self.speaker_device_id,  # None=mặc định hệ thống; hoặc chỉ mục cố định
                    samplerate=output_sample_rate,
                    channels=AudioConfig.CHANNELS,
                    dtype=np.int16,
                    blocksize=device_output_frame_size,
                    callback=self._output_callback,
                    finished_callback=self._output_finished_callback,
                    latency="low",
                )

            self.input_stream.start()
            if self.output_stream:
                self.output_stream.start()

            logger.info("Luồng âm thanh đã khởi động")

        except Exception as e:
            logger.error(f"Tạo luồng âm thanh thất bại: {e}")
            raise

    def _input_callback(self, indata, frames, time_info, status):
        """
        Callback ghi âm, driver phần cứng gọi quy trình xử lý: âm thanh gốc -> lấy mẫu lại 16kHz -> mã hóa gửi + phát hiện từ đánh thức.
        """
        if status and "overflow" not in str(status).lower():
            logger.warning(f"Trạng thái luồng đầu vào: {status}")

        if self._is_closing:
            return

        try:
            # Echo Suppression: Kiểm tra xem có đang phát hay không
            current_time = time.time()
            
            # Safety timeout: Nếu đang playing quá lâu (>10s), tự động reset
            # Tránh trường hợp TTS stop message bị miss
            if self._is_playing and self._last_audio_write_time > 0:
                time_since_last_write = current_time - self._last_audio_write_time
                if time_since_last_write > self._echo_timeout:
                    logger.info(f"⚠️ Echo period timeout ({time_since_last_write:.1f}s > {self._echo_timeout}s), auto-reset")
                    self._is_playing = False
                    self._playback_end_time = current_time
            
            is_echo_period = self._is_playing or (current_time - self._playback_end_time) < self._echo_guard_duration
            
            audio_data = indata.copy()
            
            # I2S Stereo Processing
            if self._i2s_enabled and self._i2s_stereo and len(audio_data.shape) > 1 and audio_data.shape[1] == 2:
                if self._beamforming_enabled:
                    # Delay-and-Sum Beamforming với null steering
                    audio_data = self.beamforming.process(
                        audio_data, 
                        speaker_angle=self._speaker_angle
                    )
                else:
                    # Simple averaging (fallback)
                    audio_data = np.mean(audio_data, axis=1).astype(np.int16)
            else:
                audio_data = audio_data.flatten()

            # Lấy mẫu lại về 16kHz (nếu thiết bị không phải 16kHz)
            if self.input_resampler is not None:
                audio_data = self._process_input_resampling(audio_data)
                if audio_data is None:
                    return

            # Apply software gain cho MIC (I2S INMP441 có output thấp)
            if self._mic_gain > 1.0 and self._i2s_enabled:
                # Chuyển sang float để tránh overflow
                audio_float = audio_data.astype(np.float32) * self._mic_gain
                # Clip để tránh vỡ tiếng (giới hạn trong range int16)
                audio_float = np.clip(audio_float, -32768, 32767)
                audio_data = audio_float.astype(np.int16)

            # DEBUG: Check for silence every 3 seconds
            now = time.time()
            if now - self._last_log_time > 3.0:
                self._last_log_time = now
                if len(audio_data) > 0:
                    max_val = np.max(np.abs(audio_data))
                    logger.info(f"Audio Input Check - Max Amplitude: {max_val} (Echo period: {is_echo_period})")
                else:
                    logger.info("Audio Input Check - No data")

            # Áp dụng xử lý AEC (chỉ macOS cần)
            if (
                self._aec_enabled
                and len(audio_data) == AudioConfig.INPUT_FRAME_SIZE
                and self.aec_processor._is_macos
            ):
                try:
                    audio_data = self.aec_processor.process_audio(audio_data)
                except Exception as e:
                    logger.warning(f"Xử lý AEC thất bại, sử dụng âm thanh gốc: {e}")

            # Mã hóa thời gian thực và gửi - CHỈ KHI KHÔNG TRONG ECHO PERIOD
            if not is_echo_period:
                if (
                    self._encoded_audio_callback
                    and len(audio_data) == AudioConfig.INPUT_FRAME_SIZE
                ):
                    try:
                        pcm_data = audio_data.astype(np.int16).tobytes()
                        encoded_data = self.opus_encoder.encode(
                            pcm_data, AudioConfig.INPUT_FRAME_SIZE
                        )
                        if encoded_data:
                            self._encoded_audio_callback(encoded_data)
                    except Exception as e:
                        logger.warning(f"Mã hóa ghi âm thời gian thực thất bại: {e}")

            # LUÔN cung cấp cho phát hiện từ đánh thức (wake word cần chạy liên tục!)
            self._put_audio_data_safe(self._wakeword_buffer, audio_data.copy())

        except Exception as e:
            logger.error(f"Lỗi callback đầu vào: {e}")

    def _process_input_resampling(self, audio_data):
        """
        Lấy mẫu lại đầu vào về 16kHz.
        """
        try:
            resampled_data = self.input_resampler.resample_chunk(audio_data, last=False)
            if len(resampled_data) > 0:
                self._resample_input_buffer.extend(resampled_data.astype(np.int16))

            expected_frame_size = AudioConfig.INPUT_FRAME_SIZE
            if len(self._resample_input_buffer) < expected_frame_size:
                return None

            frame_data = []
            for _ in range(expected_frame_size):
                frame_data.append(self._resample_input_buffer.popleft())

            return np.array(frame_data, dtype=np.int16)

        except Exception as e:
            logger.error(f"Lấy mẫu lại đầu vào thất bại: {e}")
            return None

    def _put_audio_data_safe(self, queue, audio_data):
        """
        Vào hàng đợi an toàn, khi hàng đợi đầy thì loại bỏ dữ liệu cũ nhất.
        """
        try:
            queue.put_nowait(audio_data)
        except asyncio.QueueFull:
            try:
                queue.get_nowait()
                queue.put_nowait(audio_data)
            except asyncio.QueueEmpty:
                queue.put_nowait(audio_data)

    def _output_callback(self, outdata: np.ndarray, frames: int, time_info, status):
        """
        Callback phát lại, driver phần cứng gọi lấy dữ liệu từ hàng đợi phát xuất ra loa.
        """
        if status:
            if "underflow" not in str(status).lower():
                logger.warning(f"Trạng thái luồng đầu ra: {status}")

        try:
            if self.output_resampler is not None:
                # Cần lấy mẫu lại: 24kHz -> Tỷ lệ mẫu thiết bị
                self._output_callback_with_resample(outdata, frames)
            else:
                # Phát trực tiếp: 24kHz
                self._output_callback_direct(outdata, frames)

        except Exception as e:
            logger.error(f"Lỗi callback đầu ra: {e}")
            outdata.fill(0)

    def _output_callback_direct(self, outdata: np.ndarray, frames: int):
        """
        Phát trực tiếp dữ liệu 24kHz (khi thiết bị hỗ trợ 24kHz)
        """
        try:
            # Lấy dữ liệu âm thanh từ hàng đợi phát
            audio_data = self._output_buffer.get_nowait()
            
            # Đánh dấu đang phát (cho echo suppression)
            self._is_playing = True

            if len(audio_data) >= frames * AudioConfig.CHANNELS:
                output_frames = audio_data[: frames * AudioConfig.CHANNELS]
                outdata[:] = output_frames.reshape(-1, AudioConfig.CHANNELS)
            else:
                out_len = len(audio_data) // AudioConfig.CHANNELS
                if out_len > 0:
                    outdata[:out_len] = audio_data[
                        : out_len * AudioConfig.CHANNELS
                    ].reshape(-1, AudioConfig.CHANNELS)
                if out_len < frames:
                    outdata[out_len:] = 0

        except asyncio.QueueEmpty:
            # Xuất im lặng khi không có dữ liệu
            outdata.fill(0)
            # Đánh dấu ngừng phát và lưu thời điểm
            if self._is_playing:
                self._is_playing = False
                self._playback_end_time = time.time()

    def _output_callback_with_resample(self, outdata: np.ndarray, frames: int):
        """
        Phát lấy mẫu lại (24kHz -> Tỷ lệ mẫu thiết bị)
        """
        had_data = False
        try:
            # Tiếp tục xử lý dữ liệu 24kHz để lấy mẫu lại
            while len(self._resample_output_buffer) < frames * AudioConfig.CHANNELS:
                try:
                    audio_data = self._output_buffer.get_nowait()
                    had_data = True
                    # Đánh dấu đang phát
                    self._is_playing = True
                    # Lấy mẫu lại 24kHz -> Tỷ lệ mẫu thiết bị
                    resampled_data = self.output_resampler.resample_chunk(
                        audio_data, last=False
                    )
                    if len(resampled_data) > 0:
                        self._resample_output_buffer.extend(
                            resampled_data.astype(np.int16)
                        )
                except asyncio.QueueEmpty:
                    break

            need = frames * AudioConfig.CHANNELS
            if len(self._resample_output_buffer) >= need:
                frame_data = [
                    self._resample_output_buffer.popleft() for _ in range(need)
                ]
                output_array = np.array(frame_data, dtype=np.int16)
                outdata[:] = output_array.reshape(-1, AudioConfig.CHANNELS)
            else:
                # Xuất im lặng khi không đủ dữ liệu
                outdata.fill(0)
                # Đánh dấu ngừng phát nếu không còn dữ liệu
                if self._is_playing and not had_data:
                    self._is_playing = False
                    self._playback_end_time = time.time()

        except Exception as e:
            logger.warning(f"Xuất lấy mẫu lại thất bại: {e}")
            outdata.fill(0)

    def _input_finished_callback(self):
        """
        Đã kết thúc luồng đầu vào.
        """
        logger.info("Đã kết thúc luồng đầu vào")

    def _reference_finished_callback(self):
        """
        Đã kết thúc luồng tín hiệu tham chiếu.
        """
        logger.info("Đã kết thúc luồng tín hiệu tham chiếu")

    def _output_finished_callback(self):
        """
        Đã kết thúc luồng đầu ra.
        """
        logger.info("Đã kết thúc luồng đầu ra")

    async def reinitialize_stream(self, is_input=True):
        """
        Khởi tạo lại luồng âm thanh.
        """
        if self._is_closing:
            return False if is_input else None

        try:
            if is_input:
                if self.input_stream:
                    self.input_stream.stop()
                    self.input_stream.close()

                self.input_stream = sd.InputStream(
                    device=self.mic_device_id,  # <- Sửa lỗi: Mang theo chỉ mục thiết bị, tránh rơi vào endpoint mặc định không ổn định
                    samplerate=self.device_input_sample_rate,
                    channels=AudioConfig.CHANNELS,
                    dtype=np.int16,
                    blocksize=self._device_input_frame_size,
                    callback=self._input_callback,
                    finished_callback=self._input_finished_callback,
                    latency="low",
                )
                self.input_stream.start()
                logger.info("Khởi tạo lại luồng đầu vào thành công")
                return True
            else:
                if self.output_stream:
                    self.output_stream.stop()
                    self.output_stream.close()

                # Chọn tỷ lệ mẫu đầu ra dựa trên tỷ lệ mẫu được thiết bị hỗ trợ
                if self.device_output_sample_rate == AudioConfig.OUTPUT_SAMPLE_RATE:
                    # Thiết bị hỗ trợ 24kHz, sử dụng trực tiếp
                    output_sample_rate = AudioConfig.OUTPUT_SAMPLE_RATE
                    device_output_frame_size = AudioConfig.OUTPUT_FRAME_SIZE
                else:
                    # Thiết bị không hỗ trợ 24kHz, sử dụng tỷ lệ mẫu mặc định của thiết bị và bật lấy mẫu lại
                    output_sample_rate = self.device_output_sample_rate
                    device_output_frame_size = int(
                        self.device_output_sample_rate
                        * (AudioConfig.FRAME_DURATION / 1000)
                    )

                self.output_stream = sd.OutputStream(
                    device=self.speaker_device_id,  # Chỉ định ID thiết bị loa
                    samplerate=output_sample_rate,
                    channels=AudioConfig.CHANNELS,
                    dtype=np.int16,
                    blocksize=device_output_frame_size,
                    callback=self._output_callback,
                    finished_callback=self._output_finished_callback,
                    latency="low",
                )
                self.output_stream.start()
                logger.info("Khởi tạo lại luồng đầu ra thành công")
                return None
        except Exception as e:
            stream_type = "Đầu vào" if is_input else "Đầu ra"
            logger.error(f"Tạo lại luồng {stream_type} thất bại: {e}")
            if is_input:
                return False
            else:
                raise

    async def get_raw_audio_for_detection(self) -> Optional[bytes]:
        """
        Lấy dữ liệu âm thanh từ đánh thức.
        """
        try:
            if self._wakeword_buffer.empty():
                return None

            audio_data = self._wakeword_buffer.get_nowait()

            if hasattr(audio_data, "tobytes"):
                return audio_data.tobytes()
            elif hasattr(audio_data, "astype"):
                return audio_data.astype("int16").tobytes()
            else:
                return audio_data

        except asyncio.QueueEmpty:
            return None
        except Exception as e:
            logger.error(f"Lấy dữ liệu âm thanh từ đánh thức thất bại: {e}")
            return None

    def set_encoded_audio_callback(self, callback):
        """
        Thiết lập callback mã hóa.
        """
        self._encoded_audio_callback = callback

        if callback:
            logger.info("Bật mã hóa thời gian thực")
        else:
            logger.info("Tắt callback mã hóa")

    def is_aec_enabled(self) -> bool:
        """
        Kiểm tra AEC có được bật hay không.
        """
        return self._aec_enabled

    def get_aec_status(self) -> dict:
        """
        Lấy thông tin trạng thái AEC.
        """
        if not self._aec_enabled or not self.aec_processor:
            return {"enabled": False, "reason": "AEC chưa được bật hoặc khởi tạo thất bại"}

        try:
            return {"enabled": True, **self.aec_processor.get_status()}
        except Exception as e:
            return {"enabled": False, "reason": f"Lấy trạng thái thất bại: {e}"}

    def toggle_aec(self, enabled: bool) -> bool:
        """Chuyển đổi trạng thái bật AEC.

        Args:
            enabled: Có bật AEC hay không

        Returns:
            Trạng thái AEC thực tế
        """
        if not self.aec_processor:
            logger.warning("Bộ xử lý AEC chưa khởi tạo, không thể chuyển đổi trạng thái")
            return False

        self._aec_enabled = enabled and self.aec_processor._is_initialized

        if enabled and not self._aec_enabled:
            logger.warning("Không thể bật AEC, bộ xử lý chưa được khởi tạo đúng cách")

        logger.info(f"Trạng thái AEC: {'Bật' if self._aec_enabled else 'Tắt'}")
        return self._aec_enabled

    async def write_audio(self, opus_data: bytes):
        """
        Giải mã âm thanh và phát Dữ liệu Opus nhận từ mạng -> Giải mã 24kHz -> Hàng đợi phát.
        """
        try:
            # Giải mã Opus thành dữ liệu PCM 24kHz
            pcm_data = self.opus_decoder.decode(
                opus_data, AudioConfig.OUTPUT_FRAME_SIZE
            )

            audio_array = np.frombuffer(pcm_data, dtype=np.int16)

            expected_length = AudioConfig.OUTPUT_FRAME_SIZE * AudioConfig.CHANNELS
            if len(audio_array) != expected_length:
                logger.warning(
                    f"Độ dài âm thanh giải mã bất thường: {len(audio_array)}, kỳ vọng: {expected_length}"
                )
                return

            # Nếu HDMI aplay được sử dụng, ghi trực tiếp vào aplay
            if self._hdmi_use_aplay:
                if not self._hdmi_aplay_process:
                    # aplay chưa có, thử start
                    logger.info("🔊 HDMI aplay not running, starting...")
                    self._start_hdmi_aplay()
                
                if self._hdmi_aplay_process:
                    self._write_hdmi_audio(audio_array)
                    self._is_playing = True
                    self._last_audio_write_time = time.time()  # Track để timeout
                else:
                    logger.warning("⚠️ Cannot write audio: aplay not available")
            elif self._hdmi_audio:
                # HDMI enabled nhưng aplay không active, thử khởi động lại
                logger.info("🔊 HDMI enabled but aplay not active, starting...")
                self._start_hdmi_aplay()
                if self._hdmi_use_aplay and self._hdmi_aplay_process:
                    self._write_hdmi_audio(audio_array)
                    self._is_playing = True
                    self._last_audio_write_time = time.time()  # Track để timeout
            else:
                # Đưa vào hàng đợi phát (sounddevice)
                self._put_audio_data_safe(self._output_buffer, audio_array)
            
            # 🎧 Đồng thời ghi ra 3.5mm jack (nếu enabled)
            if self._jack_audio:
                if self._jack_use_aplay:
                    if not self._jack_aplay_process:
                        self._start_jack_aplay()
                    if self._jack_aplay_process:
                        self._write_jack_audio(audio_array)
                elif not self._jack_use_aplay:
                    # Thử start lần đầu
                    self._start_jack_aplay()
                    if self._jack_aplay_process:
                        self._write_jack_audio(audio_array)

        except opuslib.OpusError as e:
            logger.warning(f"Giải mã Opus thất bại, bỏ qua khung này: {e}")
        except Exception as e:
            logger.warning(f"Ghi âm thanh thất bại, bỏ qua khung này: {e}")

    async def wait_for_audio_complete(self, timeout=10.0):
        """
        Chờ phát hoàn tất.
        """
        start = time.time()

        while not self._output_buffer.empty() and time.time() - start < timeout:
            await asyncio.sleep(0.05)

        await asyncio.sleep(0.3)

        if not self._output_buffer.empty():
            output_remaining = self._output_buffer.qsize()
            logger.warning(f"Phát âm thanh hết thời gian, hàng đợi còn lại - Đầu ra: {output_remaining} khung")

    async def clear_audio_queue(self):
        """
        Xóa hàng đợi âm thanh.
        """
        cleared_count = 0

        queues_to_clear = [
            self._wakeword_buffer,
            self._output_buffer,
        ]

        for queue in queues_to_clear:
            while not queue.empty():
                try:
                    queue.get_nowait()
                    cleared_count += 1
                except asyncio.QueueEmpty:
                    break

        if self._resample_input_buffer:
            cleared_count += len(self._resample_input_buffer)
            self._resample_input_buffer.clear()

        if self._resample_output_buffer:
            cleared_count += len(self._resample_output_buffer)
            self._resample_output_buffer.clear()

        if cleared_count > 0:
            logger.info(f"Đã xóa hàng đợi âm thanh, bỏ qua {cleared_count} khung dữ liệu âm thanh")

        if cleared_count > 100:
            gc.collect()
            logger.debug("Thực hiện thu gom rác để giải phóng bộ nhớ")

    def reset_playing_state(self):
        """
        Reset trạng thái playback.
        Dùng khi cần interrupt audio đang phát (e.g., wake word detected).
        """
        self._is_playing = False
        self._playback_end_time = 0
        logger.info("Playing state reset")

    def mark_playback_ended(self):
        """
        Đánh dấu TTS playback đã kết thúc.
        Gọi khi nhận được tts stop message từ server.
        Điều này sẽ reset echo period sau _echo_guard_duration.
        """
        self._is_playing = False
        self._playback_end_time = time.time()
        logger.info("🔊 Playback ended, echo guard active for 0.5s")

    async def start_streams(self):
        """
        Bắt đầu luồng âm thanh.
        """
        try:
            if self.input_stream and not self.input_stream.active:
                try:
                    self.input_stream.start()
                except Exception as e:
                    logger.warning(f"Lỗi khi bắt đầu luồng đầu vào: {e}")
                    await self.reinitialize_stream(is_input=True)

            if self.output_stream and not self.output_stream.active:
                try:
                    self.output_stream.start()
                except Exception as e:
                    logger.warning(f"Lỗi khi bắt đầu luồng đầu ra: {e}")
                    await self.reinitialize_stream(is_input=False)

            logger.info("Luồng âm thanh đã bắt đầu")
        except Exception as e:
            logger.error(f"Bắt đầu luồng âm thanh thất bại: {e}")

    async def stop_streams(self):
        """
        Dừng luồng âm thanh.
        """
        try:
            if self.input_stream and self.input_stream.active:
                self.input_stream.stop()
        except Exception as e:
            logger.warning(f"Dừng luồng đầu vào thất bại: {e}")

        try:
            if self.output_stream and self.output_stream.active:
                self.output_stream.stop()
        except Exception as e:
            logger.warning(f"Dừng luồng đầu ra thất bại: {e}")

    async def _cleanup_resampler(self, resampler, name):
        """
        清理重采样器 - 刷新缓冲区并释放资源.
        """
        if resampler:
            try:
                # 刷新缓冲区
                if hasattr(resampler, "resample_chunk"):
                    empty_array = np.array([], dtype=np.int16)
                    resampler.resample_chunk(empty_array, last=True)
            except Exception as e:
                logger.warning(f"刷新{name}重采样器缓冲区失败: {e}")

            try:
                # 尝试显式关闭（如果支持）
                if hasattr(resampler, "close"):
                    resampler.close()
                    logger.debug(f"{name}重采样器已关闭")
            except Exception as e:
                logger.warning(f"关闭{name}重采样器失败: {e}")

    async def close(self):
        """关闭音频编解码器.

        正确的销毁顺序：
        1. 设置关闭标志，阻止新的操作
        2. 停止音频流（停止硬件回调）
        3. 等待回调完全结束
        4. 清空所有队列和缓冲区（打破对 resampler 的间接引用）
        5. 清空回调引用
        6. 清理 resampler（刷新 + 关闭）
        7. 置 None + 强制 GC（释放 nanobind 包装的 C++ 对象）
        """
        if self._is_closing:
            return

        self._is_closing = True
        logger.info("Đang đóng audio codec...")
        
        # Stop HDMI aplay nếu đang chạy
        if self._hdmi_use_aplay:
            self._stop_hdmi_aplay()
        
        # Stop Jack aplay nếu đang chạy
        if self._jack_use_aplay:
            self._stop_jack_aplay()

        try:
            # 1. 停止音频流（停止硬件回调，这是最关键的第一步）
            if self.input_stream:
                try:
                    if self.input_stream.active:
                        self.input_stream.stop()
                    self.input_stream.close()
                except Exception as e:
                    logger.warning(f"关闭输入流失败: {e}")
                finally:
                    self.input_stream = None

            if self.output_stream:
                try:
                    if self.output_stream.active:
                        self.output_stream.stop()
                    self.output_stream.close()
                except Exception as e:
                    logger.warning(f"关闭输出流失败: {e}")
                finally:
                    self.output_stream = None

            # 2. 等待回调完全停止（给正在执行的回调一点时间完成）
            await asyncio.sleep(0.05)

            # 3. 清空回调引用（打破闭包引用链）
            self._encoded_audio_callback = None

            # 4. 清空所有队列和缓冲区（关键！必须在清理 resampler 之前）
            # 这些缓冲区可能间接持有 resampler 处理过的数据或引用
            await self.clear_audio_queue()

            # 清空重采样缓冲区（可能持有 numpy 数组，间接引用 resampler）
            if self._resample_input_buffer:
                self._resample_input_buffer.clear()
            if self._resample_output_buffer:
                self._resample_output_buffer.clear()

            # 5. 第一次 GC，清理队列和缓冲区中的对象
            gc.collect()

            # 6. 清理并释放重采样器（刷新缓冲区 + 显式关闭）
            await self._cleanup_resampler(self.input_resampler, "输入")
            await self._cleanup_resampler(self.output_resampler, "输出")

            # 7. 显式置 None（断开 Python 引用）
            self.input_resampler = None
            self.output_resampler = None

            # 8. 第二次 GC，释放 resampler 对象（触发 nanobind 析构）
            gc.collect()

            # 额外等待，确保 nanobind 有时间完成析构
            await asyncio.sleep(0.01)

            # 9. 关闭 AEC 处理器
            if self.aec_processor:
                try:
                    await self.aec_processor.close()
                except Exception as e:
                    logger.warning(f"关闭AEC处理器失败: {e}")
                finally:
                    self.aec_processor = None

            # 10. 释放编解码器
            self.opus_encoder = None
            self.opus_decoder = None

            # 11. 最后一次 GC，确保所有对象被回收
            gc.collect()

            logger.info("音频资源已完全释放")
        except Exception as e:
            logger.error(f"关闭音频编解码器过程中发生错误: {e}")
        finally:
            self._is_closing = True

    def __del__(self):
        """
        析构函数.
        """
        if not self._is_closing:
            logger.warning("AudioCodec未正确关闭，请调用close()")
