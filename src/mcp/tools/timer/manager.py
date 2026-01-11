"""Bộ quản lý công cụ hẹn giờ đếm ngược.

Phụ trách khởi tạo, cấu hình và đăng ký MCP tool cho bộ đếm ngược.
"""

from typing import Any, Dict

from src.utils.logging_config import get_logger

from .tools import (
    cancel_countdown_timer,
    get_active_countdown_timers,
    start_countdown_timer,
)

logger = get_logger(__name__)


class TimerToolsManager:
    """
    Bộ quản lý công cụ hẹn giờ đếm ngược.
    """

    def __init__(self):
        """
        Khởi tạo TimerToolsManager.
        """
        self._initialized = False
        logger.info("[TimerManager] Khởi tạo TimerToolsManager")

    def init_tools(self, add_tool, PropertyList, Property, PropertyType):
        """
        Khởi tạo và đăng ký toàn bộ tool đếm ngược.
        """
        try:
            logger.info("[TimerManager] Bắt đầu đăng ký các tool timer")

            # Đăng ký tool start_countdown
            self._register_start_countdown_tool(
                add_tool, PropertyList, Property, PropertyType
            )

            # Đăng ký tool cancel_countdown
            self._register_cancel_countdown_tool(
                add_tool, PropertyList, Property, PropertyType
            )

            # Đăng ký tool get_active_timers
            self._register_get_active_timers_tool(add_tool, PropertyList)

            self._initialized = True
            logger.info("[TimerManager] Đăng ký tool timer hoàn tất")

        except Exception as e:
            logger.error(f"[TimerManager] Đăng ký tool đếm ngược thất bại: {e}", exc_info=True)
            raise

    def _register_start_countdown_tool(
        self, add_tool, PropertyList, Property, PropertyType
    ):
        """
        Đăng ký tool bắt đầu đếm ngược.
        """
        timer_props = PropertyList(
            [
                Property(
                    "command",
                    PropertyType.STRING,
                ),
                Property(
                    "delay",
                    PropertyType.INTEGER,
                    default_value=5,
                    min_value=1,
                    max_value=3600,  # tối đa 1 giờ
                ),
                Property(
                    "description",
                    PropertyType.STRING,
                    default_value="",
                ),
            ]
        )

        add_tool(
            (
                "timer.start_countdown",
                "Start a countdown timer that will execute an MCP tool after a specified delay. "
                "The command should be a JSON string containing MCP tool name and arguments. "
                'For example: \'{"name": "self.audio_speaker.set_volume", "arguments": {"volume": 50}}\' '
                "Use this when the user wants to: \n"
                "1. Set a timer to control system settings (volume, device status, etc.) \n"
                "2. Schedule delayed MCP tool executions \n"
                "3. Create reminders with automatic tool calls \n"
                "The timer will return a timer_id that can be used to cancel it later.",
                timer_props,
                start_countdown_timer,
            )
        )
        logger.debug("[TimerManager] Đăng ký tool start_countdown thành công")

    def _register_cancel_countdown_tool(
        self, add_tool, PropertyList, Property, PropertyType
    ):
        """
        Đăng ký tool hủy đếm ngược.
        """
        cancel_props = PropertyList(
            [
                Property(
                    "timer_id",
                    PropertyType.INTEGER,
                )
            ]
        )

        add_tool(
            (
                "timer.cancel_countdown",
                "Cancel an active countdown timer by its ID. "
                "Use this when the user wants to: \n"
                "1. Cancel a previously set timer \n"
                "2. Stop a scheduled action before it executes \n"
                "You need the timer_id which is returned when starting a countdown.",
                cancel_props,
                cancel_countdown_timer,
            )
        )
        logger.debug("[TimerManager] Đăng ký tool cancel_countdown thành công")

    def _register_get_active_timers_tool(self, add_tool, PropertyList):
        """
        Đăng ký tool lấy danh sách timer đang chạy.
        """
        add_tool(
            (
                "timer.get_active_timers",
                "Get information about all currently active countdown timers. "
                "Returns details including timer IDs, remaining time, commands to execute, "
                "and progress for each active timer. "
                "Use this when the user wants to: \n"
                "1. Check what timers are currently running \n"
                "2. See remaining time for active timers \n"
                "3. Get timer IDs for cancellation \n"
                "4. Monitor timer progress and status",
                PropertyList(),
                get_active_countdown_timers,
            )
        )
        logger.debug("[TimerManager] Đăng ký tool get_active_timers thành công")

    def is_initialized(self) -> bool:
        """
        Kiểm tra manager đã khởi tạo hay chưa.
        """
        return self._initialized

    def get_status(self) -> Dict[str, Any]:
        """
        Lấy trạng thái manager.
        """
        return {
            "initialized": self._initialized,
            "tools_count": 3,  # số lượng tool đã đăng ký
            "available_tools": [
                "start_countdown",
                "cancel_countdown",
                "get_active_timers",
            ],
        }


# Global manager instance
_timer_tools_manager = None


def get_timer_manager() -> TimerToolsManager:
    """
    Lấy singleton của TimerToolsManager.
    """
    global _timer_tools_manager
    if _timer_tools_manager is None:
        _timer_tools_manager = TimerToolsManager()
        logger.debug("[TimerManager] Tạo instance TimerToolsManager")
    return _timer_tools_manager
