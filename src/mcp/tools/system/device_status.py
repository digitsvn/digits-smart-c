"""
Mô-đun quản lý trạng thái thiết bị - Cung cấp thông tin cơ bản về trạng thái thiết bị hệ thống
"""

import datetime
import platform
import socket
from typing import Any, Dict

import psutil

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def get_device_status() -> Dict[str, Any]:
    """
    Lấy trạng thái thiết bị tổng thể của máy chủ hiện tại.
    """
    try:
        status = {}

        # Thông tin cơ bản về hệ thống (<1ms)
        uname = platform.uname()
        status["system"] = {
            "os": uname.system,
            "node_name": uname.node,
            "release": uname.release,
            "version": uname.version,
            "machine": uname.machine,
            "processor": uname.processor,
            "hostname": socket.gethostname(),
            "ip_address": _get_local_ip(),
            "timestamp": datetime.datetime.now().isoformat(),
        }

        # Thông tin CPU (Tối ưu hóa: giảm thời gian chặn)
        status["cpu"] = {
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
            "usage_percent": psutil.cpu_percent(interval=0.1),  # Giảm từ 1 giây xuống 0.1 giây
            "per_core_usage": psutil.cpu_percent(interval=0.1, percpu=True),
        }

        # Thông tin bộ nhớ (~1ms)
        virtual_mem = psutil.virtual_memory()
        status["memory"] = {
            "total": virtual_mem.total,
            "available": virtual_mem.available,
            "used": virtual_mem.used,
            "percent": virtual_mem.percent,
        }

        # Thông tin ổ đĩa (~5ms)
        disk = psutil.disk_usage("/")
        status["disk"] = {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent,
        }

        # Trạng thái pin (<1ms)
        battery = psutil.sensors_battery()
        if battery:
            status["battery"] = {
                "percent": battery.percent,
                "plugged": battery.power_plugged,
                "secs_left": battery.secsleft,
            }
        else:
            status["battery"] = None

        logger.info("[DeviceStatus] Lấy trạng thái thiết bị thành công")
        return status

    except Exception as e:
        logger.error(f"[DeviceStatus] Lấy trạng thái thiết bị thất bại: {e}", exc_info=True)
        return {"error": str(e), "timestamp": datetime.datetime.now().isoformat()}


def _get_local_ip() -> str:
    """
    Lấy địa chỉ IP cục bộ.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"
