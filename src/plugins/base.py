import asyncio
from typing import Any


class Plugin:
    """
    Lớp cơ sở plugin tối thiểu: Cung cấp các hook vòng đời bất đồng bộ. Ghi đè khi cần thiết.
    """

    name: str = "plugin"

    def __init__(self) -> None:
        self._started = False

    async def setup(self, app: Any) -> None:
        """
        Giai đoạn chuẩn bị plugin (được gọi sớm trong quá trình chạy ứng dụng).
        """
        await asyncio.sleep(0)

    async def start(self) -> None:
        """
        Khởi động plugin (thường được gọi sau khi kết nối giao thức được thiết lập).
        """
        self._started = True
        await asyncio.sleep(0)

    async def on_protocol_connected(self, protocol: Any) -> None:
        """
        Thông báo sau khi kênh giao thức được thiết lập.
        """
        await asyncio.sleep(0)

    async def on_incoming_json(self, message: Any) -> None:
        """
        Thông báo khi nhận được tin nhắn JSON.
        """
        await asyncio.sleep(0)

    async def on_incoming_audio(self, data: bytes) -> None:
        """
        Thông báo khi nhận được dữ liệu âm thanh.
        """
        await asyncio.sleep(0)

    async def on_device_state_changed(self, state: Any) -> None:
        """
        Thông báo thay đổi trạng thái thiết bị (do ứng dụng phát sóng).
        """
        await asyncio.sleep(0)

    async def stop(self) -> None:
        """
        Dừng plugin (được gọi trước khi ứng dụng tắt).
        """
        self._started = False
        await asyncio.sleep(0)

    async def shutdown(self) -> None:
        """
        Dọn dẹp plugin lần cuối (được gọi trong quá trình tắt ứng dụng).
        """
        await asyncio.sleep(0)
