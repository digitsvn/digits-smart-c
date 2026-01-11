from typing import Any, Optional

from src.mcp.mcp_server import McpServer
from src.plugins.base import Plugin


class McpPlugin(Plugin):
    name = "mcp"

    def __init__(self) -> None:
        super().__init__()
        self.app: Any = None
        self._server: Optional[McpServer] = None

    async def setup(self, app: Any) -> None:
        self.app = app
        self._server = McpServer.get_instance()

        # Gửi phản hồi MCP qua giao thức ứng dụng
        async def _send(msg: str):
            try:
                if not self.app or not getattr(self.app, "protocol", None):
                    return
                await self.app.protocol.send_mcp_message(msg)
            except Exception:
                pass

        try:
            self._server.set_send_callback(_send)
            # Đăng ký các công cụ chung (bao gồm lịch). Dịch vụ nhắc nhở được quản lý bởi CalendarPlugin.
            self._server.add_common_tools()
            # Nếu trình phát nhạc tồn tại, trỏ tham chiếu app của nó về ứng dụng hiện tại (dùng cập nhật UI trong chế độ example)
            try:
                from src.mcp.tools.music import get_music_player_instance

                player = get_music_player_instance()
                try:
                    player.app = self.app
                except Exception:
                    pass
            except Exception:
                pass
        except Exception:
            pass

    async def on_incoming_json(self, message: Any) -> None:
        if not isinstance(message, dict):
            return
        try:
            if message.get("type") != "mcp":
                return
            payload = message.get("payload")
            if not payload:
                return
            if self._server is None:
                self._server = McpServer.get_instance()
            await self._server.parse_message(payload)
        except Exception:
            pass

    async def shutdown(self) -> None:
        # Tùy chọn: gỡ bỏ tham chiếu callback, hỗ trợ GC
        try:
            if self._server:
                self._server.set_send_callback(None)  # type: ignore[arg-type]
        except Exception:
            pass
