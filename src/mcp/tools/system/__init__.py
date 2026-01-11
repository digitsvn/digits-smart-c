"""Gói công cụ hệ thống.

Cung cấp chức năng quản lý hệ thống hoàn chỉnh, bao gồm truy vấn trạng thái thiết bị, điều khiển âm thanh và các thao tác khác.
"""

from .device_status import get_device_status
from .manager import SystemToolsManager, get_system_tools_manager
from .tools import get_system_status, set_volume

__all__ = [
    "SystemToolsManager",
    "get_system_tools_manager",
    "get_device_status",
    "get_system_status",
    "set_volume",
]
