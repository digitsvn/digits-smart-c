from typing import Any

from src.constants.constants import AbortReason
from src.plugins.base import Plugin


class WakeWordPlugin(Plugin):
    name = "wake_word"

    def __init__(self) -> None:
        super().__init__()
        self.app = None
        self.detector = None

    async def setup(self, app: Any) -> None:
        self.app = app
        try:
            from src.audio_processing.wake_word_detect import WakeWordDetector

            self.detector = WakeWordDetector()
            if not getattr(self.detector, "enabled", False):
                self.detector = None
                return

            # Gắn kết callback
            self.detector.on_detected(self._on_detected)
            self.detector.on_error = self._on_error
        except Exception:
            self.detector = None

    async def start(self) -> None:
        if not self.detector:
            return
        try:
            # Cần bộ giải mã âm thanh để cung cấp dữ liệu PCM thô
            audio_codec = getattr(self.app, "audio_codec", None)
            if audio_codec is None:
                from src.utils.logging_config import get_logger
                logger = get_logger(__name__)
                logger.warning("WakeWordPlugin: audio_codec not found in app, detection will not start.")
                return
            await self.detector.start(audio_codec)
        except Exception:
            pass

    async def stop(self) -> None:
        if self.detector:
            try:
                await self.detector.stop()
            except Exception:
                pass

    async def shutdown(self) -> None:
        if self.detector:
            try:
                await self.detector.stop()
            except Exception:
                pass

    async def _on_detected(self, wake_word, full_text):
        # Phát hiện từ đánh thức: chuyển sang đối thoại tự động (tự động chọn thời gian thực/dừng tự động dựa trên AEC)
        from src.utils.logging_config import get_logger
        logger = get_logger(__name__)
        
        try:
            logger.info(f"🎤 WakeWordPlugin: Detected '{wake_word}' - '{full_text}'")
            
            # Nếu đang nói, để logic ngắt/máy trạng thái của ứng dụng xử lý
            if hasattr(self.app, "device_state") and hasattr(
                self.app, "start_auto_conversation"
            ):
                # Check cả device_state lẫn audio playback flag
                is_playing_audio = False
                audio_plugin = self.app.plugins.get_plugin("audio")
                if audio_plugin and hasattr(audio_plugin, "codec"):
                    is_playing_audio = getattr(audio_plugin.codec, "_is_playing", False)
                
                if self.app.is_speaking() or is_playing_audio:
                    logger.info(f"Interrupting current speech... (state={self.app.device_state}, playing={is_playing_audio})")
                    await self.app.abort_speaking(AbortReason.WAKE_WORD_DETECTED)
                    if audio_plugin and hasattr(audio_plugin, "codec"):
                        await audio_plugin.codec.clear_audio_queue()
                        # Reset playing state via method (không access private attr trực tiếp)
                        if hasattr(audio_plugin.codec, "reset_playing_state"):
                            audio_plugin.codec.reset_playing_state()
                    # Sau khi interrupt, bắt đầu nghe lại
                    logger.info("Starting auto conversation after interrupt...")
                    await self.app.start_auto_conversation()
                else:
                    logger.info("Starting auto conversation...")
                    await self.app.start_auto_conversation()
            else:
                logger.warning("App doesn't have required methods for auto conversation")
        except Exception as e:
            logger.error(f"Error handling wake word detection: {e}", exc_info=True)

    def _on_error(self, error):
        try:
            if hasattr(self.app, "set_chat_message"):
                self.app.set_chat_message("assistant", f"[Lỗi KWS] {error}")
        except Exception:
            pass
