import json

from src.constants.constants import AbortReason, ListeningMode
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class Protocol:
    def __init__(self):
        self.session_id = ""
        # Khởi tạo hàm callback là None
        self._on_incoming_json = None
        self._on_incoming_audio = None
        self._on_audio_channel_opened = None
        self._on_audio_channel_closed = None
        self._on_network_error = None
        # Callback thay đổi trạng thái kết nối mới
        self._on_connection_state_changed = None
        self._on_reconnecting = None

    def on_incoming_json(self, callback):
        """
        Thiết lập hàm callback nhận tin nhắn JSON.
        """
        self._on_incoming_json = callback

    def on_incoming_audio(self, callback):
        """
        Thiết lập hàm callback nhận dữ liệu âm thanh.
        """
        self._on_incoming_audio = callback

    def on_audio_channel_opened(self, callback):
        """
        Thiết lập hàm callback mở kênh âm thanh.
        """
        self._on_audio_channel_opened = callback

    def on_audio_channel_closed(self, callback):
        """
        Thiết lập hàm callback đóng kênh âm thanh.
        """
        self._on_audio_channel_closed = callback

    def on_network_error(self, callback):
        """
        Thiết lập hàm callback lỗi mạng.
        """
        self._on_network_error = callback

    def on_connection_state_changed(self, callback):
        """Thiết lập hàm callback thay đổi trạng thái kết nối.

        Tham số:
            callback: Hàm callback, nhận tham số (connected: bool, reason: str)
        """
        self._on_connection_state_changed = callback

    def on_reconnecting(self, callback):
        """Thiết lập hàm callback thử kết nối lại.

        Tham số:
            callback: Hàm callback, nhận tham số (attempt: int, max_attempts: int)
        """
        self._on_reconnecting = callback

    async def send_text(self, message):
        """
        Phương thức trừu tượng gửi tin nhắn văn bản, cần được thực hiện trong lớp con.
        """
        raise NotImplementedError("Phương thức send_text phải được thực hiện bởi lớp con")

    async def send_audio(self, data: bytes):
        """
        Phương thức trừu tượng gửi dữ liệu âm thanh, cần được thực hiện trong lớp con.
        """
        raise NotImplementedError("Phương thức send_audio phải được thực hiện bởi lớp con")

    def is_audio_channel_opened(self) -> bool:
        """
        Phương thức trừu tượng kiểm tra xem kênh âm thanh có mở hay không, cần được thực hiện trong lớp con.
        """
        raise NotImplementedError("Phương thức is_audio_channel_opened phải được thực hiện bởi lớp con")

    async def open_audio_channel(self) -> bool:
        """
        Phương thức trừu tượng mở kênh âm thanh, cần được thực hiện trong lớp con.
        """
        raise NotImplementedError("Phương thức open_audio_channel phải được thực hiện bởi lớp con")

    async def close_audio_channel(self):
        """
        Phương thức trừu tượng đóng kênh âm thanh, cần được thực hiện trong lớp con.
        """
        raise NotImplementedError("Phương thức close_audio_channel phải được thực hiện bởi lớp con")

    async def send_abort_speaking(self, reason):
        """
        Gửi tin nhắn ngắt lời nói.
        """
        message = {"session_id": self.session_id, "type": "abort"}
        if reason == AbortReason.WAKE_WORD_DETECTED:
            message["reason"] = "wake_word_detected"
        await self.send_text(json.dumps(message))

    async def send_wake_word_detected(self, wake_word):
        """
        Gửi tin nhắn phát hiện từ đánh thức.
        """
        message = {
            "session_id": self.session_id,
            "type": "listen",
            "state": "detect",
            "text": wake_word,
        }
        await self.send_text(json.dumps(message))

    async def send_start_listening(self, mode):
        """
        Gửi tin nhắn bắt đầu nghe.
        """
        mode_map = {
            ListeningMode.REALTIME: "realtime",
            ListeningMode.AUTO_STOP: "auto",
            ListeningMode.MANUAL: "manual",
        }
        message = {
            "session_id": self.session_id,
            "type": "listen",
            "state": "start",
            "mode": mode_map[mode],
        }
        await self.send_text(json.dumps(message))

    async def send_stop_listening(self):
        """
        Gửi tin nhắn dừng nghe.
        """
        message = {"session_id": self.session_id, "type": "listen", "state": "stop"}
        await self.send_text(json.dumps(message))

    async def send_iot_descriptors(self, descriptors):
        """
        Gửi thông tin mô tả thiết bị IoT.
        """
        try:
            # Phân tích dữ liệu mô tả
            if isinstance(descriptors, str):
                descriptors_data = json.loads(descriptors)
            else:
                descriptors_data = descriptors

            # Kiểm tra xem có phải là mảng không
            if not isinstance(descriptors_data, list):
                logger.error("IoT descriptors should be an array")
                return

            # Gửi tin nhắn riêng cho mỗi mô tả
            for i, descriptor in enumerate(descriptors_data):
                if descriptor is None:
                    logger.error(f"Failed to get IoT descriptor at index {i}")
                    continue

                message = {
                    "session_id": self.session_id,
                    "type": "iot",
                    "update": True,
                    "descriptors": [descriptor],
                }

                try:
                    await self.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(
                        f"Failed to send JSON message for IoT descriptor "
                        f"at index {i}: {e}"
                    )
                    continue

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse IoT descriptors: {e}")
            return

    async def send_iot_states(self, states):
        """
        Gửi thông tin trạng thái thiết bị IoT.
        """
        if isinstance(states, str):
            states_data = json.loads(states)
        else:
            states_data = states

        message = {
            "session_id": self.session_id,
            "type": "iot",
            "update": True,
            "states": states_data,
        }
        await self.send_text(json.dumps(message))

    async def send_mcp_message(self, payload):
        """
        Gửi tin nhắn MCP.
        """
        if isinstance(payload, str):
            payload_data = json.loads(payload)
        else:
            payload_data = payload

        message = {
            "session_id": self.session_id,
            "type": "mcp",
            "payload": payload_data,
        }

        await self.send_text(json.dumps(message))
