"""Trình quản lý công cụ hệ thống.

Chịu trách nhiệm khởi tạo, cấu hình công cụ hệ thống và đăng ký công cụ MCP.
"""

from typing import Any, Dict

from src.utils.logging_config import get_logger

from .app_management.killer import kill_application, list_running_applications
from .app_management.launcher import launch_application
from .app_management.scanner import scan_installed_applications
from .tools import get_system_status, set_volume

logger = get_logger(__name__)


class SystemToolsManager:
    """
    Trình quản lý công cụ hệ thống.
    """

    def __init__(self):
        """
        Khởi tạo trình quản lý công cụ hệ thống.
        """
        self._initialized = False
        logger.info("[SystemManager] Khởi tạo trình quản lý công cụ hệ thống")

    def init_tools(self, add_tool, PropertyList, Property, PropertyType):
        """
        Khởi tạo và đăng ký tất cả các công cụ hệ thống.
        """
        try:
            logger.info("[SystemManager] Bắt đầu đăng ký công cụ hệ thống")

            # Đăng ký công cụ lấy trạng thái thiết bị
            self._register_device_status_tool(add_tool, PropertyList)

            # Đăng ký công cụ điều khiển âm lượng
            self._register_volume_control_tool(
                add_tool, PropertyList, Property, PropertyType
            )

            # Đăng ký công cụ khởi chạy ứng dụng
            self._register_app_launcher_tool(
                add_tool, PropertyList, Property, PropertyType
            )

            # Đăng ký công cụ quét ứng dụng
            self._register_app_scanner_tool(
                add_tool, PropertyList, Property, PropertyType
            )

            # Đăng ký công cụ đóng ứng dụng
            self._register_app_killer_tools(
                add_tool, PropertyList, Property, PropertyType
            )

            self._initialized = True
            logger.info("[SystemManager] Hoàn tất đăng ký công cụ hệ thống")

        except Exception as e:
            logger.error(f"[SystemManager] Đăng ký công cụ hệ thống thất bại: {e}", exc_info=True)
            raise

    def _register_device_status_tool(self, add_tool, PropertyList):
        """
        Đăng ký công cụ truy vấn trạng thái thiết bị.
        """
        add_tool(
            (
                "self.get_device_status",
                "Provides comprehensive real-time system information including "
                "OS details, CPU usage, memory status, disk usage, battery info, "
                "audio speaker volume and settings, and application state.\n"
                "Use this tool for: \n"
                "1. Answering questions about current system condition\n"
                "2. Getting detailed hardware and software status\n"
                "3. Checking current audio volume level and mute status\n"
                "4. As the first step before controlling device settings",
                PropertyList(),
                get_system_status,
            )
        )
        logger.debug("[SystemManager] Đăng ký thành công công cụ trạng thái thiết bị")

    def _register_volume_control_tool(
        self, add_tool, PropertyList, Property, PropertyType
    ):
        """
        Đăng ký công cụ điều khiển âm lượng.
        """
        volume_props = PropertyList(
            [Property("volume", PropertyType.INTEGER, min_value=0, max_value=100)]
        )
        add_tool(
            (
                "self.audio_speaker.set_volume",
                "Set system speaker volume to an absolute value (0–100). Always "
                "provide integer 'volume'.\n"
                "Use this tool when:\n"
                "1. User asks to set volume to a specific percent/number (e.g., '音量设为50%')\n"
                "2. User asks to increase/decrease volume relatively ('调大/调小一点'): first call "
                "`self.get_device_status` to read current audio_speaker.volume, compute a target within 0–100, "
                "then call this tool\n"
                "3. Ensuring volume stays within 0–100 (do not guess current value)\n\n"
                "Parameters:\n"
                "- volume: INTEGER in [0, 100] (absolute target)\n\n"
                "Notes: If the current volume is unknown, do NOT assume it — call `self.get_device_status` first. "
                "To mute, set volume=0. This tool does not toggle mute state.",
                volume_props,
                set_volume,
            )
        )
        logger.debug("[SystemManager] Đăng ký thành công công cụ điều khiển âm lượng")

    def _register_app_launcher_tool(
        self, add_tool, PropertyList, Property, PropertyType
    ):
        """
        Đăng ký công cụ khởi chạy ứng dụng.
        """
        app_props = PropertyList([Property("app_name", PropertyType.STRING)])
        add_tool(
            (
                "self.application.launch",
                "Launch desktop applications and software programs by name. This tool "
                "opens applications installed on the user's computer across Windows, "
                "macOS, and Linux platforms. It automatically detects the operating "
                "system and uses appropriate launch methods.\n"
                "Use this tool when the user wants to:\n"
                "1. Open specific software applications (e.g., 'QQ', 'QQ音乐', 'WeChat', '微信')\n"
                "2. Launch system utilities (e.g., 'Calculator', '计算器', 'Notepad', '记事本')\n"
                "3. Start browsers (e.g., 'Chrome', 'Firefox', 'Safari')\n"
                "4. Open media players (e.g., 'VLC', 'Windows Media Player')\n"
                "5. Launch development tools (e.g., 'VS Code', 'PyCharm')\n"
                "6. Start games or other installed programs\n\n"
                "Examples of valid app names:\n"
                "- Chinese: 'QQ音乐', '微信', '计算器', '记事本', '浏览器'\n"
                "- English: 'QQ', 'WeChat', 'Calculator', 'Notepad', 'Chrome'\n"
                "- Mixed: 'QQ Music', 'Microsoft Word', 'Adobe Photoshop'\n\n"
                "The system will try multiple launch strategies including direct execution, "
                "system commands, and path searching to find and start the application.",
                app_props,
                launch_application,
            )
        )
        logger.debug("[SystemManager] Đăng ký thành công công cụ khởi chạy ứng dụng")

    def _register_app_scanner_tool(
        self, add_tool, PropertyList, Property, PropertyType
    ):
        """
        Đăng ký công cụ quét ứng dụng.
        """
        scanner_props = PropertyList(
            [Property("force_refresh", PropertyType.BOOLEAN, default_value=False)]
        )
        add_tool(
            (
                "self.application.scan_installed",
                "Scan and list all installed applications on the system. This tool "
                "provides a comprehensive list of available applications that can be "
                "launched using the launch tool. It scans system directories, registry "
                "(Windows), and application folders to find installed software.\n"
                "Use this tool when:\n"
                "1. User asks what applications are available on the system\n"
                "2. You need to find the correct application name before launching\n"
                "3. User wants to see all installed software\n"
                "4. Application launch fails and you need to check available apps\n\n"
                "The scan results include both system applications (Calculator, Notepad) "
                "and user-installed software (QQ, WeChat, Chrome, etc.). Each application "
                "entry contains the clean name for launching and display name for reference.\n\n"
                "After scanning, use the 'name' field from results with self.application.launch "
                "to start applications. For example, if scan shows {name: 'QQ', display_name: 'QQ音乐'}, "
                "use self.application.launch with app_name='QQ' to launch it.",
                scanner_props,
                scan_installed_applications,
            )
        )
        logger.debug("[SystemManager] Đăng ký thành công công cụ quét ứng dụng")

    def _register_app_killer_tools(
        self, add_tool, PropertyList, Property, PropertyType
    ):
        """
        Đăng ký công cụ đóng ứng dụng.
        """
        # Đăng ký công cụ đóng ứng dụng
        killer_props = PropertyList(
            [
                Property("app_name", PropertyType.STRING),
                Property("force", PropertyType.BOOLEAN, default_value=False),
            ]
        )
        add_tool(
            (
                "self.application.kill",
                "Close or terminate running applications by name. This tool can gracefully "
                "close applications or force-kill them if needed. It automatically finds "
                "running processes matching the application name and terminates them.\n"
                "Use this tool when:\n"
                "1. User asks to close, quit, or exit an application\n"
                "2. User wants to stop or terminate a running program\n"
                "3. Application is unresponsive and needs to be force-closed\n"
                "4. User says 'close QQ', 'quit Chrome', 'stop music player', etc.\n\n"
                "Parameters:\n"
                "- app_name: Name of the application to close (e.g., 'QQ', 'Chrome', 'Calculator')\n"
                "- force: Set to true for force-kill unresponsive applications (default: false)\n\n"
                "The tool will find all running processes matching the application name and "
                "attempt to close them gracefully. If force=true, it will use system kill "
                "commands to immediately terminate the processes.",
                killer_props,
                kill_application,
            )
        )

        # Đăng ký công cụ danh sách ứng dụng đang chạy
        list_props = PropertyList(
            [Property("filter_name", PropertyType.STRING, default_value="")]
        )
        add_tool(
            (
                "self.application.list_running",
                "List all currently running applications and processes. This tool provides "
                "real-time information about active applications on the system, including "
                "process IDs, names, and commands.\n"
                "Use this tool when:\n"
                "1. User asks what applications are currently running\n"
                "2. You need to check if a specific application is running before closing it\n"
                "3. User wants to see active processes or programs\n"
                "4. Troubleshooting application issues\n\n"
                "Parameters:\n"
                "- filter_name: Optional filter to show only applications containing this name\n\n"
                "Returns detailed information about running applications including process IDs "
                "which can be useful for targeted application management.",
                list_props,
                list_running_applications,
            )
        )
        logger.debug("[SystemManager] Đăng ký thành công công cụ đóng ứng dụng")

    def is_initialized(self) -> bool:
        """
        Kiểm tra xem trình quản lý có được khởi tạo hay không.
        """
        return self._initialized

    def get_status(self) -> Dict[str, Any]:
        """
        Lấy trạng thái trình quản lý.
        """
        return {
            "initialized": self._initialized,
            "tools_count": 6,  # Số lượng công cụ hiện được đăng ký
            "available_tools": [
                "get_device_status",
                "set_volume",
                "launch_application",
                "scan_installed_applications",
                "kill_application",
                "list_running_applications",
            ],
        }


# Một phiên bản trình quản lý toàn cầu
_system_tools_manager = None


def get_system_tools_manager() -> SystemToolsManager:
    """
    Lấy singleton trình quản lý công cụ hệ thống.
    """
    global _system_tools_manager
    if _system_tools_manager is None:
        _system_tools_manager = SystemToolsManager()
        logger.debug("[SystemManager] Tạo một phiên bản trình quản lý công cụ hệ thống")
    return _system_tools_manager
