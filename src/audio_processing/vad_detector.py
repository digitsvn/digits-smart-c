import logging
import threading
import time

import numpy as np
import pyaudio
import webrtcvad

from src.constants.constants import AbortReason, DeviceState

# Cấu hình log
logger = logging.getLogger("VADDetector")


class VADDetector:
    """
    Detector hoạt động giọng nói dựa trên WebRTC VAD, dùng để phát hiện sự ngắt lời của người dùng.
    """

    def __init__(self, audio_codec, protocol, app_instance, loop):
        """Khởi tạo detector VAD.

        Tham số:
            audio_codec: Instance codec âm thanh
            protocol: Instance giao thức giao tiếp
            app_instance: Instance ứng dụng
            loop: Vòng lặp sự kiện
        """
        self.audio_codec = audio_codec
        self.protocol = protocol
        self.app = app_instance
        self.loop = loop

        # Cài đặt VAD
        self.vad = webrtcvad.Vad()
        self.vad.set_mode(3)  # Thiết lập độ nhạy cao nhất

        # Cài đặt tham số
        self.sample_rate = 16000
        self.frame_duration = 20  # mili giây
        self.frame_size = int(self.sample_rate * self.frame_duration / 1000)
        self.speech_window = 5  # Số khung hình liên tiếp cần phát hiện giọng nói để kích hoạt ngắt
        self.energy_threshold = 300  # Ngưỡng năng lượng

        # Biến trạng thái
        self.running = False
        self.paused = False
        self.thread = None
        self.speech_count = 0
        self.silence_count = 0
        self.triggered = False

        # Tạo instance PyAudio và luồng độc lập, tránh xung đột với luồng âm thanh chính
        self.pa = None
        self.stream = None

    def start(self):
        """
        Khởi động detector VAD.
        """
        if self.thread and self.thread.is_alive():
            logger.warning("Detector VAD đang chạy")
            return

        self.running = True
        self.paused = False

        # Khởi tạo PyAudio và luồng
        self._initialize_audio_stream()

        # Khởi động luồng phát hiện
        self.thread = threading.Thread(target=self._detection_loop, daemon=True)
        self.thread.start()
        logger.info("Detector VAD đã khởi động")

    def stop(self):
        """
        Dừng detector VAD.
        """
        self.running = False

        # Đóng luồng âm thanh
        self._close_audio_stream()

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)

        logger.info("Detector VAD đã dừng")

    def pause(self):
        """
        Tạm dừng phát hiện VAD.
        """
        self.paused = True
        logger.info("Detector VAD đã tạm dừng")

    def resume(self):
        """
        Khôi phục phát hiện VAD.
        """
        self.paused = False
        # Đặt lại trạng thái
        self.speech_count = 0
        self.silence_count = 0
        self.triggered = False
        logger.info("Detector VAD đã khôi phục")

    def is_running(self):
        """
        Kiểm tra xem detector VAD có đang chạy không.
        """
        return self.running and not self.paused

    def _initialize_audio_stream(self):
        """
        Khởi tạo luồng âm thanh độc lập.
        """
        try:
            # Tạo instance PyAudio
            self.pa = pyaudio.PyAudio()

            # Lấy thiết bị đầu vào mặc định
            device_index = None
            for i in range(self.pa.get_device_count()):
                device_info = self.pa.get_device_info_by_index(i)
                if device_info["maxInputChannels"] > 0:
                    device_index = i
                    break

            if device_index is None:
                logger.error("Không tìm thấy thiết bị đầu vào khả dụng")
                return False

            # Tạo luồng đầu vào
            self.stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.frame_size,
                start=True,
            )

            logger.info(f"Luồng âm thanh detector VAD đã khởi tạo, sử dụng chỉ số thiết bị: {device_index}")
            return True

        except Exception as e:
            logger.error(f"Khởi tạo luồng âm thanh VAD thất bại: {e}")
            return False

    def _close_audio_stream(self):
        """
        Đóng luồng âm thanh.
        """
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None

            if self.pa:
                self.pa.terminate()
                self.pa = None

            logger.info("Luồng âm thanh detector VAD đã đóng")
        except Exception as e:
            logger.error(f"Đóng luồng âm thanh VAD thất bại: {e}")

    def _detection_loop(self):
        """
        Vòng lặp chính phát hiện VAD.
        """
        logger.info("Vòng lặp phát hiện VAD đã bắt đầu")

        while self.running:
            # Nếu tạm dừng hoặc luồng âm thanh chưa khởi tạo, bỏ qua
            if self.paused or not self.stream:
                time.sleep(0.1)
                continue

            try:
                # Chỉ phát hiện khi đang ở trạng thái nói
                if self.app.device_state == DeviceState.SPEAKING:
                    # Đọc khung âm thanh
                    frame = self._read_audio_frame()
                    if not frame:
                        time.sleep(0.01)
                        continue

                    # Phát hiện xem có phải giọng nói không
                    is_speech = self._detect_speech(frame)

                    # Nếu phát hiện giọng nói và đạt điều kiện kích hoạt, xử lý ngắt
                    if is_speech:
                        self._handle_speech_frame(frame)
                    else:
                        self._handle_silence_frame(frame)
                else:
                    # Không ở trạng thái nói, đặt lại trạng thái
                    self._reset_state()

            except Exception as e:
                logger.error(f"Lỗi vòng lặp phát hiện VAD: {e}")

            time.sleep(0.01)  # Trễ nhỏ, giảm sử dụng CPU

        logger.info("Vòng lặp phát hiện VAD đã kết thúc")

    def _read_audio_frame(self):
        """
        Đọc một khung dữ liệu âm thanh.
        """
        try:
            if not self.stream or not self.stream.is_active():
                return None

            # Đọc dữ liệu âm thanh
            data = self.stream.read(self.frame_size, exception_on_overflow=False)
            return data
        except Exception as e:
            logger.error(f"Đọc khung âm thanh thất bại: {e}")
            return None

    def _detect_speech(self, frame):
        """
        Phát hiện xem có phải giọng nói không.
        """
        try:
            # Đảm bảo độ dài khung chính xác
            if len(frame) != self.frame_size * 2:  # Âm thanh 16-bit, mỗi mẫu 2 byte
                return False

            # Sử dụng VAD để phát hiện
            is_speech = self.vad.is_speech(frame, self.sample_rate)

            # Tính năng lượng âm thanh
            audio_data = np.frombuffer(frame, dtype=np.int16)
            energy = np.mean(np.abs(audio_data))

            # Kết hợp VAD và ngưỡng năng lượng
            is_valid_speech = is_speech and energy > self.energy_threshold

            if is_valid_speech:
                logger.debug(
                    f"Phát hiện giọng nói [Năng lượng: {energy:.2f}] [Khung giọng nói liên tiếp: {self.speech_count+1}]"
                )

            return is_valid_speech
        except Exception as e:
            logger.error(f"Phát hiện giọng nói thất bại: {e}")
            return False

    def _handle_speech_frame(self, frame):
        """
        Xử lý khung giọng nói.
        """
        self.speech_count += 1
        self.silence_count = 0

        # Phát hiện đủ khung giọng nói liên tiếp, kích hoạt ngắt
        if self.speech_count >= self.speech_window and not self.triggered:
            self.triggered = True
            logger.info("Phát hiện giọng nói liên tục, kích hoạt ngắt!")
            self._trigger_interrupt()

            # Tạm dừng ngay lập tức để ngăn kích hoạt lặp lại
            self.paused = True
            logger.info("Detector VAD đã tự động tạm dừng để ngăn kích hoạt lặp lại")

            # Đặt lại trạng thái
            self.speech_count = 0
            self.silence_count = 0
            self.triggered = False

    def _handle_silence_frame(self, frame):
        """
        Xử lý khung im lặng.
        """
        self.silence_count += 1
        self.speech_count = 0

    def _reset_state(self):
        """
        Đặt lại trạng thái.
        """
        self.speech_count = 0
        self.silence_count = 0
        self.triggered = False

    def _trigger_interrupt(self):
        """
        Kích hoạt ngắt.
        """
        # Thông báo cho ứng dụng hủy bỏ đầu ra giọng nói hiện tại
        self.app.schedule(
            lambda: self.app.abort_speaking(AbortReason.WAKE_WORD_DETECTED)
        )
