import asyncio
import os
from typing import Any

from src.audio_codecs.audio_codec import AudioCodec
from src.constants.constants import DeviceState, ListeningMode
from src.plugins.base import Plugin

# from src.utils.opus_loader import setup_opus
# setup_opus()


class AudioPlugin(Plugin):
    name = "audio"

    def __init__(self) -> None:
        super().__init__()
        self.app = None  # ApplicationExample
        self.codec: AudioCodec | None = None
        self._loop = None
        self._send_sem = asyncio.Semaphore(4)

    async def setup(self, app: Any) -> None:
        self.app = app
        self._loop = app._main_loop

        if os.getenv("XIAOZHI_DISABLE_AUDIO") == "1":
            return

        try:
            self.codec = AudioCodec()
            await self.codec.initialize()
            # Callback mã hóa ghi âm (từ luồng âm thanh)
            self.codec.set_encoded_audio_callback(self._on_encoded_audio)
            # Công khai cho ứng dụng, tiện cho plugin phát hiện từ đánh thức sử dụng
            try:
                setattr(self.app, "audio_codec", self.codec)
            except Exception:
                pass
        except Exception as e:
            from src.utils.logging_config import get_logger
            logger = get_logger(__name__)
            logger.error(f"Failed to initialize AudioCodec: {e}", exc_info=True)
            self.codec = None

    async def start(self) -> None:
        if self.codec:
            try:
                await self.codec.start_streams()
            except Exception:
                pass

    async def on_protocol_connected(self, protocol: Any) -> None:
        # Đảm bảo luồng âm thanh được khởi động khi kết nối giao thức
        if self.codec:
            try:
                await self.codec.start_streams()
            except Exception:
                pass

    async def on_incoming_json(self, message: Any) -> None:
        # Xử lý TTS stop để reset echo period
        if isinstance(message, dict) and message.get("type") == "tts":
            state = message.get("state")
            if state == "stop" and self.codec:
                # Đợi audio buffer drain trước khi mark ended
                # aplay buffer ~0.5s + network latency
                await asyncio.sleep(0.8)
                # Đánh dấu playback kết thúc để reset echo period
                self.codec.mark_playback_ended()
        await asyncio.sleep(0)

    async def on_incoming_audio(self, data: bytes) -> None:
        if self.codec:
            try:
                await self.codec.write_audio(data)
            except Exception as e:
                from src.utils.logging_config import get_logger
                logger = get_logger(__name__)
                logger.error(f"Failed to write audio to codec: {e}", exc_info=True)
        else:
            from src.utils.logging_config import get_logger
            logger = get_logger(__name__)
            logger.warning("Audio codec not initialized, cannot play audio")

    async def stop(self) -> None:
        """
        Dừng luồng âm thanh (giữ lại instance codec)
        """
        if self.codec:
            try:
                await self.codec.stop_streams()
            except Exception:
                pass

    async def shutdown(self) -> None:
        """
        Tắt hoàn toàn và giải phóng tài nguyên âm thanh.
        """
        if self.codec:
            try:
                # Đảm bảo dừng luồng trước, sau đó đóng (tránh callback vẫn đang chạy)
                try:
                    await self.codec.stop_streams()
                except Exception:
                    pass

                # Đóng và giải phóng tất cả tài nguyên âm thanh
                await self.codec.close()
            except Exception:
                # Nhật ký đã được ghi trong codec.close()
                pass
            finally:
                # Xóa tham chiếu, hỗ trợ GC
                self.codec = None

        # Xóa tham chiếu ứng dụng, phá vỡ vòng tham chiếu tiềm ẩn
        if self.app and hasattr(self.app, "audio_codec"):
            try:
                self.app.audio_codec = None
            except Exception:
                pass

    # -------------------------
    # Nội bộ: Gửi âm thanh microphone
    # -------------------------
    def _on_encoded_audio(self, encoded_data: bytes) -> None:
        # Callback luồng âm thanh -> chuyển về vòng lặp chính
        try:
            if not self.app or not self._loop or not self.app.running:
                return
            if self._loop.is_closed():
                return
            self._loop.call_soon_threadsafe(self._schedule_send_audio, encoded_data)
        except Exception:
            pass

    def _schedule_send_audio(self, encoded_data: bytes) -> None:
        if not self.app or not self.app.running or not self.app.protocol:
            return

        async def _send():
            async with self._send_sem:
                # Chỉ gửi âm thanh microphone ở trạng thái thiết bị cho phép
                try:
                    if not (
                        self.app.protocol
                        and self.app.protocol.is_audio_channel_opened()
                    ):
                        return
                    if self._should_send_microphone_audio():
                        await self.app.protocol.send_audio(encoded_data)
                except Exception:
                    pass

        # Giao tác vụ cho quản lý ứng dụng
        self.app.spawn(_send(), name="audio:send")

    def _should_send_microphone_audio(self) -> bool:
        """Căn chỉnh với máy trạng thái ứng dụng:

        - Gửi khi LISTENING
        - Gửi khi SPEAKING và AEC bật và keep_listening và chế độ REALTIME
        """
        try:
            if not self.app:
                return False
            if self.app.device_state == DeviceState.LISTENING and not self.app.aborted:
                return True
            return (
                self.app.device_state == DeviceState.SPEAKING
                and getattr(self.app, "aec_enabled", False)
                and bool(getattr(self.app, "keep_listening", False))
                and getattr(self.app, "listening_mode", None) == ListeningMode.REALTIME
            )
        except Exception:
            return False
