from typing import Any, List

from .base import Plugin


class PluginManager:
    """
    Trình quản lý plugin nhẹ: Thống nhất phát setup/start/stop/shutdown; cách ly lỗi.
    """

    def __init__(self) -> None:
        self._plugins: List[Plugin] = []
        self._by_name: dict[str, Plugin] = {}

    def register(self, *plugins: Plugin) -> None:
        for p in plugins:
            if p not in self._plugins:
                self._plugins.append(p)
                try:
                    name = getattr(p, "name", None)
                    if isinstance(name, str) and name:
                        self._by_name[name] = p
                except Exception:
                    pass

    def get_plugin(self, name: str) -> Plugin | None:
        """
        Lấy instance plugin theo tên. Trả về None nếu chưa đăng ký.
        """
        try:
            return self._by_name.get(name)
        except Exception:
            return None

    async def setup_all(self, app: Any) -> None:
        for p in list(self._plugins):
            try:
                await p.setup(app)
            except Exception:
                # Lỗi không chặn các plugin khác
                pass

    async def start_all(self) -> None:
        for p in list(self._plugins):
            try:
                await p.start()
            except Exception:
                pass

    async def notify_protocol_connected(self, protocol: Any) -> None:
        for p in list(self._plugins):
            try:
                p.on_protocol_connected and await p.on_protocol_connected(protocol)
            except Exception:
                pass

    async def notify_incoming_json(self, message: Any) -> None:
        for p in list(self._plugins):
            try:
                await p.on_incoming_json(message)
            except Exception:
                pass

    async def notify_incoming_audio(self, data: bytes) -> None:
        for p in list(self._plugins):
            try:
                await p.on_incoming_audio(data)
            except Exception:
                pass

    async def notify_device_state_changed(self, state: Any) -> None:
        for p in list(self._plugins):
            try:
                await p.on_device_state_changed(state)
            except Exception:
                pass

    async def stop_all(self) -> None:
        # Thứ tự ngược lại an toàn hơn
        for p in reversed(self._plugins):
            try:
                await p.stop()
            except Exception:
                pass


    async def shutdown_all(self) -> None:
        for p in reversed(self._plugins):
            try:
                await p.shutdown()
            except Exception:
                pass
