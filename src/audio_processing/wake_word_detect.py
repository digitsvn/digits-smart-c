import asyncio
import time
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import sherpa_onnx

from src.constants.constants import AudioConfig
from src.utils.config_manager import ConfigManager
from src.utils.logging_config import get_logger
from src.utils.resource_finder import resource_finder

logger = get_logger(__name__)


class WakeWordDetector:

    def __init__(self):
        # Thuộc tính cơ bản
        self.audio_codec = None
        self.is_running_flag = False
        self.paused = False
        self.detection_task = None

        # Cơ chế chống kích hoạt lặp lại - rút ngắn thời gian hồi chiêu để tăng phản hồi
        self.last_detection_time = 0
        self.detection_cooldown = 1.5  # 1.5 giây thời gian hồi chiêu

        # Hàm callback
        self.on_detected_callback: Optional[Callable] = None
        self.on_error: Optional[Callable] = None

        # Kiểm tra cấu hình
        config = ConfigManager.get_instance()
        if not config.get_config("WAKE_WORD_OPTIONS.USE_WAKE_WORD", False):
            logger.info("Chức năng từ đánh thức đã bị vô hiệu hóa")
            self.enabled = False
            return

        # Khởi tạo tham số cơ bản
        self.enabled = True
        self.sample_rate = AudioConfig.INPUT_SAMPLE_RATE

        # Thành phần KWS Sherpa-ONNX
        self.keyword_spotter = None
        self.stream = None

        # Khởi tạo cấu hình
        self._load_config(config)
        self._init_kws_model()
        self._validate_config()

    def _load_config(self, config):
        """
        Tải tham số cấu hình.
        """
        # Cấu hình đường dẫn mô hình
        model_path = config.get_config("WAKE_WORD_OPTIONS.MODEL_PATH", "models")
        self.model_dir = resource_finder.find_directory(model_path)

        if self.model_dir is None:
            # Phương án dự phòng: thử sử dụng đường dẫn trực tiếp
            self.model_dir = Path(model_path)
            logger.warning(
                f"ResourceFinder không tìm thấy thư mục mô hình, sử dụng đường dẫn gốc: {self.model_dir}"
            )

        # Cấu hình tham số KWS - tối ưu hóa tốc độ
        self.num_threads = config.get_config(
            "WAKE_WORD_OPTIONS.NUM_THREADS", 4
        )  # Tăng số luồng
        self.provider = config.get_config("WAKE_WORD_OPTIONS.PROVIDER", "cpu")
        self.max_active_paths = config.get_config(
            "WAKE_WORD_OPTIONS.MAX_ACTIVE_PATHS", 2
        )  # Giảm đường dẫn tìm kiếm
        self.keywords_score = config.get_config(
            "WAKE_WORD_OPTIONS.KEYWORDS_SCORE", 1.8
        )  # Giảm điểm số để tăng tốc độ
        self.keywords_threshold = config.get_config(
            "WAKE_WORD_OPTIONS.KEYWORDS_THRESHOLD", 0.2
        )  # Giảm ngưỡng để tăng độ nhạy
        self.num_trailing_blanks = config.get_config(
            "WAKE_WORD_OPTIONS.NUM_TRAILING_BLANKS", 1
        )

        logger.info(
            f"Đã tải cấu hình KWS - Ngưỡng: {self.keywords_threshold}, Điểm số: {self.keywords_score}"
        )

    def _init_kws_model(self):
        """
        Khởi tạo mô hình Sherpa-ONNX KeywordSpotter.
        """
        try:
            # Kiểm tra tệp mô hình
            encoder_path = self.model_dir / "encoder.onnx"
            decoder_path = self.model_dir / "decoder.onnx"
            joiner_path = self.model_dir / "joiner.onnx"
            tokens_path = self.model_dir / "tokens.txt"
            keywords_path = self.model_dir / "keywords.txt"

            required_files = [
                encoder_path,
                decoder_path,
                joiner_path,
                tokens_path,
                keywords_path,
            ]
            for file_path in required_files:
                if not file_path.exists():
                    raise FileNotFoundError(f"Tệp tin mô hình không tồn tại: {file_path}")

            logger.info(f"Đang tải mô hình Sherpa-ONNX KeywordSpotter: {self.model_dir}")

            # Tạo KeywordSpotter
            self.keyword_spotter = sherpa_onnx.KeywordSpotter(
                tokens=str(tokens_path),
                encoder=str(encoder_path),
                decoder=str(decoder_path),
                joiner=str(joiner_path),
                keywords_file=str(keywords_path),
                num_threads=self.num_threads,
                sample_rate=self.sample_rate,
                feature_dim=80,
                max_active_paths=self.max_active_paths,
                keywords_score=self.keywords_score,
                keywords_threshold=self.keywords_threshold,
                num_trailing_blanks=self.num_trailing_blanks,
                provider=self.provider,
            )

            logger.info("Tải mô hình Sherpa-ONNX KeywordSpotter thành công")
            
            # Log keywords configuration
            try:
                with open(keywords_path, 'r') as f:
                    keywords_content = f.read().strip()
                    logger.info(f"Keywords configured:\n{keywords_content}")
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Khởi tạo Sherpa-ONNX KeywordSpotter thất bại: {e}", exc_info=True)
            self.enabled = False

    def on_detected(self, callback: Callable):
        """
        Thiết lập hàm callback khi phát hiện từ đánh thức.
        """
        self.on_detected_callback = callback

    async def start(self, audio_codec) -> bool:
        """
        Khởi động bộ phát hiện từ đánh thức.
        """
        if not self.enabled:
            logger.warning("Chức năng từ đánh thức chưa được bật")
            return False

        if not self.keyword_spotter:
            logger.error("KeywordSpotter chưa được khởi tạo")
            return False

        try:
            self.audio_codec = audio_codec
            self.is_running_flag = True
            self.paused = False

            # Tạo luồng phát hiện
            self.stream = self.keyword_spotter.create_stream()

            # Khởi động tác vụ phát hiện
            self.detection_task = asyncio.create_task(self._detection_loop())

            logger.info("Bộ phát hiện Sherpa-ONNX KeywordSpotter khởi động thành công")
            return True
        except Exception as e:
            logger.error(f"Khởi động bộ phát hiện KeywordSpotter thất bại: {e}")
            self.enabled = False
            return False

    async def _detection_loop(self):
        """
        Vòng lặp phát hiện.
        """
        error_count = 0
        MAX_ERRORS = 5

        while self.is_running_flag:
            try:
                if self.paused:
                    await asyncio.sleep(0.1)
                    continue

                if not self.audio_codec:
                    await asyncio.sleep(0.5)
                    continue

                # Xử lý dữ liệu âm thanh
                await self._process_audio()

                # Giảm độ trễ để tăng tốc độ phản hồi
                await asyncio.sleep(0.005)
                error_count = 0

            except asyncio.CancelledError:
                break
            except Exception as e:
                error_count += 1
                logger.error(f"Lỗi vòng lặp phát hiện KWS ({error_count}/{MAX_ERRORS}): {e}")

                # Gọi callback lỗi
                if self.on_error:
                    try:
                        if asyncio.iscoroutinefunction(self.on_error):
                            await self.on_error(e)
                        else:
                            self.on_error(e)
                    except Exception as callback_error:
                        logger.error(f"Thực thi callback lỗi thất bại: {callback_error}")

                if error_count >= MAX_ERRORS:
                    logger.critical("Đạt số lần lỗi tối đa, dừng phát hiện KWS")
                    break
                await asyncio.sleep(1)

    async def _process_audio(self):
        """Xử lý dữ liệu âm thanh - Tối ưu hóa xử lý hàng loạt"""
        try:
            if not self.audio_codec or not self.stream:
                return

            # Lấy hàng loạt nhiều khung âm thanh để cải thiện hiệu suất
            audio_batches = []
            for _ in range(3):  # Xử lý tối đa 3 khung cùng lúc
                data = await self.audio_codec.get_raw_audio_for_detection()
                if data:
                    audio_batches.append(data)

            if not audio_batches:
                # Debug: Count empty batches
                if not hasattr(self, '_empty_batch_count'):
                    self._empty_batch_count = 0
                self._empty_batch_count += 1
                if self._empty_batch_count % 300 == 0:
                    logger.warning(f"KWS: {self._empty_batch_count} consecutive empty batches from audio_codec")
                return
            else:
                self._empty_batch_count = 0  # Reset on successful batch

            # Xử lý hàng loạt dữ liệu âm thanh
            for data in audio_batches:
                # Chuyển đổi định dạng âm thanh
                if isinstance(data, bytes):
                    samples = (
                        np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                    )
                else:
                    samples = np.array(data, dtype=np.float32)

                # Cung cấp dữ liệu âm thanh cho KeywordSpotter
                self.stream.accept_waveform(
                    sample_rate=self.sample_rate, waveform=samples
                )
                
                # DEBUG: Log audio input every 100 frames
                if not hasattr(self, '_frame_count'):
                    self._frame_count = 0
                self._frame_count += 1
                if self._frame_count % 100 == 0:
                    logger.debug(f"KWS: Processed {self._frame_count} frames, max amplitude: {np.max(np.abs(samples)):.3f}")
                
                # Debug: Log every 100 batches
                if not hasattr(self, '_batch_count'):
                    self._batch_count = 0
                self._batch_count += 1
                if self._batch_count % 100 == 0:
                    logger.debug(f"KWS processed {self._batch_count} batches, samples shape: {samples.shape}, max: {np.max(np.abs(samples)):.4f}")

            # Xử lý kết quả phát hiện
            decode_count = 0
            while self.keyword_spotter.is_ready(self.stream):
                self.keyword_spotter.decode_stream(self.stream)
                result = self.keyword_spotter.get_result(self.stream)
                decode_count += 1

                # Debug: Log decode attempts
                if not hasattr(self, '_decode_count'):
                    self._decode_count = 0
                self._decode_count += 1
                if self._decode_count % 100 == 0:
                    logger.debug(f"KWS: {self._decode_count} decode calls, current result: {result}")
                
                if result:
                    logger.info(f"🎯 Wake word detected! Result: {result}")
                    await self._handle_detection_result(result)
                    # Đặt lại trạng thái luồng
                    self.keyword_spotter.reset_stream(self.stream)
                    break  # Xử lý ngay khi phát hiện, không tiếp tục xử lý hàng loạt

        except Exception as e:
            logger.debug(f"Lỗi xử lý âm thanh KWS: {e}")

    async def _handle_detection_result(self, result):
        """
        Xử lý kết quả phát hiện.
        """
        # Log tất cả result để debug
        logger.info(f"🔍 Detection result received: {result} (type: {type(result)})")
        
        # Kiểm tra chống kích hoạt lặp lại
        current_time = time.time()
        if current_time - self.last_detection_time < self.detection_cooldown:
            logger.debug(f"Cooldown active, ignoring detection (last: {current_time - self.last_detection_time:.1f}s ago)")
            return

        self.last_detection_time = current_time
        logger.info(f"✅ Wake word ACCEPTED! Result: {result}")

        # Kích hoạt callback
        if self.on_detected_callback:
            try:
                if asyncio.iscoroutinefunction(self.on_detected_callback):
                    await self.on_detected_callback(result, result)
                else:
                    self.on_detected_callback(result, result)
            except Exception as e:
                logger.error(f"Thực thi callback từ đánh thức thất bại: {e}", exc_info=True)
        else:
            logger.warning("No on_detected_callback registered!")

    async def stop(self):
        """
        Dừng bộ phát hiện.
        """
        self.is_running_flag = False

        if self.detection_task:
            self.detection_task.cancel()
            try:
                await self.detection_task
            except asyncio.CancelledError:
                pass

        logger.info("Bộ phát hiện Sherpa-ONNX KeywordSpotter đã dừng")

    async def pause(self):
        """
        Tạm dừng phát hiện.
        """
        self.paused = True
        logger.debug("Phát hiện KWS đã tạm dừng")

    async def resume(self):
        """
        Tiếp tục phát hiện.
        """
        self.paused = False
        logger.debug("Phát hiện KWS đã tiếp tục")

    def is_running(self) -> bool:
        """
        Kiểm tra xem có đang chạy hay không.
        """
        return self.is_running_flag and not self.paused

    def _validate_config(self):
        """
        Xác thực tham số cấu hình.
        """
        if not self.enabled:
            return

        # Xác thực tham số ngưỡng
        if not 0.1 <= self.keywords_threshold <= 1.0:
            logger.warning(f"Ngưỡng từ khóa {self.keywords_threshold} vượt quá phạm vi, đặt lại thành 0.25")
            self.keywords_threshold = 0.25

        if not 0.1 <= self.keywords_score <= 10.0:
            logger.warning(f"Điểm số từ khóa {self.keywords_score} vượt quá phạm vi, đặt lại thành 2.0")
            self.keywords_score = 2.0

        logger.info(
            f"Xác thực cấu hình KWS hoàn tất - Ngưỡng: {self.keywords_threshold}, Điểm số: {self.keywords_score}"
        )

    def get_performance_stats(self):
        """
        Lấy thông tin thống kê hiệu suất.
        """
        return {
            "enabled": self.enabled,
            "engine": "sherpa-onnx-kws",
            "provider": self.provider,
            "num_threads": self.num_threads,
            "keywords_threshold": self.keywords_threshold,
            "keywords_score": self.keywords_score,
            "is_running": self.is_running(),
        }

    def clear_cache(self):
        """
        Xóa bộ nhớ đệm.
        """
