"""MCP module cho bộ đếm ngược.

Cung cấp chức năng đếm ngược để thực thi lệnh trễ, hỗ trợ truy vấn trạng thái và phản hồi.
"""

from .manager import get_timer_manager

__all__ = ["get_timer_manager"]
