import platform
from collections import deque
from typing import Any, Dict, Optional

import numpy as np
import sounddevice as sd

from src.constants.constants import AudioConfig
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class AECProcessor:
    """
    Bộ xử lý khử tiếng vọng âm thanh (AEC), chuyên xử lý tín hiệu tham chiếu (đầu ra loa) và đầu vào micro.
    """

    def __init__(self):
        # Thông tin nền tảng
        self._platform = platform.system().lower()
        self._is_macos = self._platform == "darwin"
        self._is_linux = self._platform == "linux"
        self._is_windows = self._platform == "windows"

        # Thực thể WebRTC APM (chỉ macOS sử dụng)
        self.apm = None
        self.apm_config = None
        self.capture_config = None
        self.render_config = None

        # Luồng tín hiệu tham chiếu (chỉ macOS sử dụng)
        self.reference_stream = None
        self.reference_device_id = None
        self.reference_sample_rate = None

        # Bộ đệm
        self._reference_buffer = deque()
        self._webrtc_frame_size = 160  # Tiêu chuẩn WebRTC: 16kHz, 10ms = 160 mẫu
        self._system_frame_size = AudioConfig.INPUT_FRAME_SIZE  # Kích thước khung hình cấu hình hệ thống

        # Cờ trạng thái
        self._is_initialized = False
        self._is_closing = False

    async def initialize(self):
        """
        Khởi tạo bộ xử lý AEC.
        """
        try:
            if self._is_windows or self._is_linux:
                # Nền tảng Windows và Linux sử dụng AEC cấp hệ thống, không cần xử lý thêm
                logger.info(
                    f"Nền tảng {self._platform.capitalize()} sử dụng khử tiếng vọng cấp hệ thống, bộ xử lý AEC đã được bật"
                )
                self._is_initialized = True
                return
            elif self._is_macos:
                # Nền tảng macOS sử dụng WebRTC + BlackHole
                await self._initialize_apm()
                await self._initialize_reference_capture()
            else:
                logger.warning(f"Nền tảng hiện tại {self._platform} tạm thời không hỗ trợ tính năng AEC")
                self._is_initialized = True
                return

            self._is_initialized = True
            logger.info("Khởi tạo bộ xử lý AEC hoàn tất")

        except Exception as e:
            logger.error(f"Khởi tạo bộ xử lý AEC thất bại: {e}")
            await self.close()
            raise

    async def _initialize_apm(self):
        """
        Khởi tạo module xử lý âm thanh WebRTC (chỉ macOS)
        """
        if not self._is_macos:
            logger.warning("Nền tảng không phải macOS đã gọi _initialize_apm, điều này không nên xảy ra")
            return

        try:
            # Nhập trễ, chỉ tải thư viện cục bộ khi macOS cần
            from libs.webrtc_apm import WebRTCAudioProcessing, create_default_config

            self.apm = WebRTCAudioProcessing()

            # Tạo cấu hình
            self.apm_config = create_default_config()

            # Bật khử tiếng vọng
            self.apm_config.echo.enabled = True
            self.apm_config.echo.mobile_mode = False
            self.apm_config.echo.enforce_high_pass_filtering = True

            # Bật khử nhiễu
            self.apm_config.noise_suppress.enabled = True
            self.apm_config.noise_suppress.noise_level = 2  # HIGH

            # Bật bộ lọc thông cao
            self.apm_config.high_pass.enabled = True
            self.apm_config.high_pass.apply_in_full_band = True

            # Áp dụng cấu hình
            result = self.apm.apply_config(self.apm_config)
            if result != 0:
                raise RuntimeError(f"Cấu hình WebRTC APM thất bại, mã lỗi: {result}")

            # Tạo cấu hình luồng
            sample_rate = AudioConfig.INPUT_SAMPLE_RATE  # 16kHz
            channels = AudioConfig.CHANNELS  # 1

            self.capture_config = self.apm.create_stream_config(sample_rate, channels)
            self.render_config = self.apm.create_stream_config(sample_rate, channels)

            # Thiết lập độ trễ luồng
            self.apm.set_stream_delay_ms(40)  # 50ms độ trễ

            logger.info("Khởi tạo WebRTC APM hoàn tất")

        except Exception as e:
            logger.error(f"Khởi tạo WebRTC APM thất bại: {e}")
            raise

    async def _initialize_reference_capture(self):
        """
        Khởi tạo thu tín hiệu tham chiếu (chỉ macOS)
        """
        if not self._is_macos:
            return

        try:
            # Tìm thiết bị BlackHole 2ch
            reference_device = self._find_blackhole_device()
            if reference_device is None:
                logger.warning("Không tìm thấy thiết bị BlackHole 2ch, thu tín hiệu tham chiếu không khả dụng")
                return

            self.reference_device_id = reference_device["id"]
            self.reference_sample_rate = int(reference_device["default_samplerate"])

            # Tạo luồng đầu vào tín hiệu tham chiếu (cố định dùng khung 10ms, khớp tiêu chuẩn WebRTC)
            webrtc_frame_duration = 0.01  # 10ms, WebRTC tiêu chuẩn khung hình
            reference_frame_size = int(
                self.reference_sample_rate * webrtc_frame_duration
            )

            self.reference_stream = sd.InputStream(
                device=self.reference_device_id,
                samplerate=self.reference_sample_rate,
                channels=AudioConfig.CHANNELS,
                dtype=np.int16,
                blocksize=reference_frame_size,
                callback=self._reference_callback,
                finished_callback=self._reference_finished_callback,
                latency="low",
            )

            self.reference_stream.start()

            logger.info(
                f"Thu tín hiệu tham chiếu đã khởi động: [{self.reference_device_id}] {reference_device['name']}"
            )

        except Exception as e:
            logger.error(f"Khởi tạo thu tín hiệu tham chiếu thất bại: {e}")
            # Không ném ngoại lệ, cho phép AEC hoạt động mà không có tín hiệu tham chiếu

    def _find_blackhole_device(self) -> Optional[Dict[str, Any]]:
        """
        Tìm thiết bị ảo BlackHole 2ch.
        """
        try:
            devices = sd.query_devices()
            for i, device in enumerate(devices):
                device_name = device["name"].lower()
                # Tìm thiết bị BlackHole 2ch
                if "blackhole" in device_name and "2ch" in device_name:
                    # Đảm bảo là thiết bị đầu vào
                    if device["max_input_channels"] >= 1:
                        device_info = dict(device)
                        device_info["id"] = i
                        logger.info(f"Tìm thấy thiết bị BlackHole: [{i}] {device['name']}")
                        return device_info

            # Nếu không tìm thấy BlackHole 2ch cụ thể, thử tìm bất kỳ thiết bị BlackHole nào
            for i, device in enumerate(devices):
                device_name = device["name"].lower()
                if "blackhole" in device_name and device["max_input_channels"] >= 1:
                    device_info = dict(device)
                    device_info["id"] = i
                    logger.info(f"Tìm thấy thiết bị BlackHole: [{i}] {device['name']}")
                    return device_info

            return None

        except Exception as e:
            logger.error(f"Tìm thiết bị BlackHole thất bại: {e}")
            return None

    def _reference_callback(self, indata, frames, time_info, status):
        """
        Callback tín hiệu tham chiếu.
        """
        # frames, time_info được sử dụng cho callback sounddevice, không dùng ở đây nhưng cần giữ lại chữ ký
        _ = frames, time_info

        if status and "overflow" not in str(status).lower():
            logger.warning(f"Trạng thái luồng tín hiệu tham chiếu: {status}")

        if self._is_closing:
            return

        try:
            audio_data = indata.copy().flatten()

            # Lấy mẫu lại về 16kHz (nếu cần)
            if self.reference_sample_rate != AudioConfig.INPUT_SAMPLE_RATE:
                # Xử lý giảm mẫu đơn giản (ứng dụng thực tế nên dùng bộ lấy mẫu lại tốt hơn)
                ratio = AudioConfig.INPUT_SAMPLE_RATE / self.reference_sample_rate
                target_length = int(len(audio_data) * ratio)
                audio_data = np.interp(
                    np.linspace(0, len(audio_data) - 1, target_length),
                    np.arange(len(audio_data)),
                    audio_data,
                ).astype(np.int16)

            # Thêm vào bộ đệm tham chiếu
            self._reference_buffer.extend(audio_data)

            # Giữ kích thước bộ đệm hợp lý
            max_buffer_size = self._webrtc_frame_size * 20  # Giữ khoảng 200ms dữ liệu
            while len(self._reference_buffer) > max_buffer_size:
                self._reference_buffer.popleft()

        except Exception as e:
            logger.error(f"Lỗi callback tín hiệu tham chiếu: {e}")

    def _reference_finished_callback(self):
        """
        Callback kết thúc luồng tín hiệu tham chiếu.
        """
        logger.info("Luồng tín hiệu tham chiếu đã kết thúc")

    def process_audio(self, capture_audio: np.ndarray) -> np.ndarray:
        """Xử lý khung âm thanh, áp dụng AEC. Hỗ trợ độ dài khung khác nhau 10ms/20ms/40ms/60ms, thực hiện thông qua xử lý phân đoạn.

        Args:
            capture_audio: Dữ liệu âm thanh thu từ micro (16kHz, int16)

        Returns:
            Dữ liệu âm thanh sau xử lý
        """
        if not self._is_initialized:
            return capture_audio

        # Nền tảng Windows và Linux trả về âm thanh gốc trực tiếp (xử lý cấp hệ thống)
        if self._is_windows or self._is_linux:
            return capture_audio

        # Nền tảng macOS sử dụng xử lý WebRTC AEC
        if not self._is_macos or self.apm is None:
            return capture_audio

        try:
            # Kiểm tra kích thước khung đầu vào có phải là bội số nguyên của kích thước khung WebRTC không
            if len(capture_audio) % self._webrtc_frame_size != 0:
                logger.warning(
                    f"Kích thước khung âm thanh không phải là bội số nguyên của khung WebRTC: {len(capture_audio)}, khung WebRTC: {self._webrtc_frame_size}"
                )
                return capture_audio

            # Tính toán số lượng khối cần chia
            num_chunks = len(capture_audio) // self._webrtc_frame_size

            if num_chunks == 1:
                # Khung 10ms, xử lý trực tiếp
                return self._process_single_aec_frame(capture_audio)
            else:
                # Khung 20ms/40ms/60ms, xử lý phân đoạn
                return self._process_chunked_aec_frames(capture_audio, num_chunks)

        except Exception as e:
            logger.error(f"Xử lý AEC thất bại: {e}")
            return capture_audio

    def _process_single_aec_frame(self, capture_audio: np.ndarray) -> np.ndarray:
        """
        Xử lý khung WebRTC 10ms đơn lẻ (chỉ macOS)
        """
        if not self._is_macos:
            return capture_audio

        try:
            # Chỉ nhập ctypes trên macOS
            import ctypes

            # Lấy tín hiệu tham chiếu
            reference_audio = self._get_reference_frame(self._webrtc_frame_size)

            # Tạo bộ đệm ctypes
            capture_buffer = (ctypes.c_short * self._webrtc_frame_size)(*capture_audio)
            reference_buffer = (ctypes.c_short * self._webrtc_frame_size)(
                *reference_audio
            )

            processed_capture = (ctypes.c_short * self._webrtc_frame_size)()
            processed_reference = (ctypes.c_short * self._webrtc_frame_size)()

            # Trước tiên xử lý tín hiệu tham chiếu (luồng render)
            render_result = self.apm.process_reverse_stream(
                reference_buffer,
                self.render_config,
                self.render_config,
                processed_reference,
            )

            if render_result != 0:
                logger.warning(f"Xử lý tín hiệu tham chiếu thất bại, mã lỗi: {render_result}")

            # Sau đó xử lý tín hiệu thu thập (luồng capture)
            capture_result = self.apm.process_stream(
                capture_buffer,
                self.capture_config,
                self.capture_config,
                processed_capture,
            )

            if capture_result != 0:
                logger.warning(f"Xử lý tín hiệu thu thập thất bại, mã lỗi: {capture_result}")
                return capture_audio

            # Chuyển đổi lại thành mảng numpy
            return np.array(processed_capture, dtype=np.int16)

        except Exception as e:
            logger.error(f"Xử lý khung AEC thất bại: {e}")
            return capture_audio

    def _process_chunked_aec_frames(
        self, capture_audio: np.ndarray, num_chunks: int
    ) -> np.ndarray:
        """
        Xử lý phân đoạn khung lớn (20ms/40ms/60ms v.v...)
        """
        processed_chunks = []

        for i in range(num_chunks):
            # Trích xuất khối 10ms hiện tại
            start_idx = i * self._webrtc_frame_size
            end_idx = (i + 1) * self._webrtc_frame_size
            chunk = capture_audio[start_idx:end_idx]

            # Xử lý khối 10ms này
            processed_chunk = self._process_single_aec_frame(chunk)
            processed_chunks.append(processed_chunk)

        # Kết hợp lại tất cả các khối đã xử lý
        return np.concatenate(processed_chunks)

    def _get_reference_frame(self, frame_size: int) -> np.ndarray:
        """
        Lấy khung tín hiệu tham chiếu có kích thước chỉ định.
        """
        # Nếu không có tín hiệu tham chiếu hoặc bộ đệm không đủ, trả về im lặng
        if len(self._reference_buffer) < frame_size:
            return np.zeros(frame_size, dtype=np.int16)

        # Trích xuất một khung từ bộ đệm
        frame_data = []
        for _ in range(frame_size):
            frame_data.append(self._reference_buffer.popleft())

        return np.array(frame_data, dtype=np.int16)

    def is_reference_available(self) -> bool:
        """
        Kiểm tra xem tín hiệu tham chiếu có khả dụng không.
        """
        if self._is_windows or self._is_linux:
            # Windows và Linux sử dụng AEC cấp hệ thống, luôn khả dụng
            return self._is_initialized

        # macOS cần kiểm tra luồng tín hiệu tham chiếu
        return (
            self.reference_stream is not None
            and self.reference_stream.active
            and len(self._reference_buffer) >= self._webrtc_frame_size
        )

    def get_status(self) -> Dict[str, Any]:
        """
        Lấy trạng thái bộ xử lý AEC.
        """
        status = {
            "initialized": self._is_initialized,
            "platform": self._platform,
            "reference_available": self.is_reference_available(),
        }

        if self._is_windows:
            status.update(
                {"aec_type": "system_level", "description": "Khử tiếng vọng tầng dưới hệ thống Windows"}
            )
        elif self._is_linux:
            status.update(
                {
                    "aec_type": "system_level",
                    "description": "Khử tiếng vọng cấp hệ thống Linux (PulseAudio)",
                }
            )
        elif self._is_macos:
            status.update(
                {
                    "aec_type": "webrtc_blackhole",
                    "description": "Tín hiệu tham chiếu WebRTC + BlackHole",
                    "reference_device_id": self.reference_device_id,
                    "reference_buffer_size": len(self._reference_buffer),
                    "webrtc_apm_active": self.apm is not None,
                }
            )
        else:
            status.update(
                {
                    "aec_type": "unsupported",
                    "description": f"Nền tảng {self._platform} tạm thời không hỗ trợ AEC",
                }
            )

        return status

    async def close(self):
        """
        Đóng bộ xử lý AEC.
        """
        if self._is_closing:
            return

        self._is_closing = True
        logger.info("Bắt đầu đóng bộ xử lý AEC...")

        try:
            # Chỉ dọn dẹp tài nguyên liên quan đến WebRTC trên nền tảng macOS
            if self._is_macos:
                # Dừng luồng tín hiệu tham chiếu
                if self.reference_stream:
                    try:
                        self.reference_stream.stop()
                        self.reference_stream.close()
                    except Exception as e:
                        logger.warning(f"Dừng luồng tín hiệu tham chiếu thất bại: {e}")
                    finally:
                        self.reference_stream = None

                # Dọn dẹp WebRTC APM
                if self.apm:
                    try:
                        if self.capture_config:
                            self.apm.destroy_stream_config(self.capture_config)
                        if self.render_config:
                            self.apm.destroy_stream_config(self.render_config)
                    except Exception as e:
                        logger.warning(f"Dọn dẹp cấu hình APM thất bại: {e}")
                    finally:
                        self.capture_config = None
                        self.render_config = None
                        self.apm = None

            # Dọn dẹp bộ đệm
            self._reference_buffer.clear()

            self._is_initialized = False
            logger.info("Bộ xử lý AEC đã đóng")

        except Exception as e:
            logger.error(f"Xảy ra lỗi khi đóng bộ xử lý AEC: {e}")