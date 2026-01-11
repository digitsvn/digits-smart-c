from typing import Any

from src.plugins.base import Plugin
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class _AppAdapter:
    """
    Cung cấp adapter _send_text_tts cho dịch vụ nhắc lịch.
    """

    def __init__(self, app: Any) -> None:
        self._app = app

    async def _send_text_tts(self, text: str):
        try:
            # Kích hoạt TTS qua giao thức (căn chỉnh hành vi với ApplicationMain)
            if not getattr(self._app, "protocol", None):
                return
            try:
                if not self._app.is_audio_channel_opened():
                    await self._app.connect_protocol()
            except Exception:
                pass
            await self._app.protocol.send_wake_word_detected(text)
        except Exception:
            # Dự phòng: chuyển sang văn bản UI nếu không thể TTS
            try:
                if hasattr(self._app, "set_chat_message"):
                    self._app.set_chat_message("assistant", text)
            except Exception:
                pass


class CalendarPlugin(Plugin):
    name = "calendar"

    def __init__(self) -> None:
        super().__init__()
        self.app: Any = None
        self._service = None
        self._adapter: _AppAdapter | None = None

    async def setup(self, app: Any) -> None:
        self.app = app
        self._adapter = _AppAdapter(app)
        try:
            from src.mcp.tools.calendar import get_reminder_service

            self._service = get_reminder_service()
            # Ghi đè hàm lấy ứng dụng, trả về đối tượng adapter
            try:
                setattr(self._service, "_get_application", lambda: self._adapter)
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Khởi tạo dịch vụ nhắc lịch thất bại: {e}")
            self._service = None

    async def start(self) -> None:
        if not self._service:
            return
        try:
            await self._service.start()
            # Tùy chọn: kiểm tra lịch trình hôm nay khi khởi động
            try:
                await self._service.check_daily_events()
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Khởi động dịch vụ nhắc lịch thất bại: {e}")

    async def stop(self) -> None:
        try:
            if self._service:
                await self._service.stop()
        except Exception:
            pass

    async def shutdown(self) -> None:
        try:
            if self._service:
                await self._service.stop()
        except Exception:
            pass
