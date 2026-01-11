"""Triển khai công cụ hệ thống.

Cung cấp các chức năng cụ thể của công cụ hệ thống.
"""

import asyncio
import json
from typing import Any, Dict

from src.utils.logging_config import get_logger

from .device_status import get_device_status

logger = get_logger(__name__)


async def get_system_status(args: Dict[str, Any]) -> str:
    """
    Lấy trạng thái hệ thống hoàn chỉnh.
    """
    try:
        logger.info("[SystemTools] Bắt đầu lấy trạng thái hệ thống")

        # Sử dụng thread pool để thực thi việc lấy trạng thái thiết bị đồng bộ, tránh chặn vòng lặp sự kiện
        status = await asyncio.to_thread(get_device_status)

        # Thêm thông tin trạng thái âm thanh/âm lượng
        audio_status = await _get_audio_status()
        status["audio_speaker"] = audio_status

        # Thêm thông tin trạng thái ứng dụng
        app_status = _get_application_status()
        status["application"] = app_status

        logger.info("[SystemTools] Lấy trạng thái hệ thống thành công")
        return json.dumps(status, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"[SystemTools] Lấy trạng thái hệ thống thất bại: {e}", exc_info=True)
        # Trả về trạng thái mặc định
        fallback_status = {
            "error": str(e),
            "audio_speaker": {"volume": 50, "muted": False, "available": False},
            "application": {"device_state": "unknown", "iot_devices": 0},
        }
        return json.dumps(fallback_status, ensure_ascii=False)


async def set_volume(args: Dict[str, Any]) -> bool:
    """
    Thiết lập âm lượng.
    """
    try:
        volume = args["volume"]
        logger.info(f"[SystemTools] Đặt âm lượng thành {volume}")

        # Xác minh phạm vi âm lượng
        if not (0 <= volume <= 100):
            logger.warning(f"[SystemTools] Giá trị âm lượng nằm ngoài phạm vi: {volume}")
            return False

        # Sử dụng trực tiếp VolumeController để đặt âm lượng
        from src.utils.volume_controller import VolumeController

        # Kiểm tra sự phụ thuộc và tạo bộ điều khiển âm lượng
        if not VolumeController.check_dependencies():
            logger.warning("[SystemTools] Phụ thuộc điều khiển âm lượng không đầy đủ, không phát thể thiết lập âm lượng")
            return False

        volume_controller = VolumeController()
        await asyncio.to_thread(volume_controller.set_volume, volume)
        logger.info(f"[SystemTools] Thiết lập âm lượng thành công: {volume}")
        return True

    except KeyError:
        logger.error("[SystemTools] Thiếu tham số volume")
        return False
    except Exception as e:
        logger.error(f"[SystemTools] Thiết lập âm lượng thất bại: {e}", exc_info=True)
        return False


async def _get_audio_status() -> Dict[str, Any]:
    """
    Lấy trạng thái âm thanh.
    """
    try:
        from src.utils.volume_controller import VolumeController

        if VolumeController.check_dependencies():
            volume_controller = VolumeController()
            # Sử dụng thread pool để lấy âm lượng, tránh gây chặn
            current_volume = await asyncio.to_thread(volume_controller.get_volume)
            return {
                "volume": current_volume,
                "muted": current_volume == 0,
                "available": True,
            }
        else:
            return {
                "volume": 50,
                "muted": False,
                "available": False,
                "reason": "Dependencies not available",
            }

    except Exception as e:
        logger.warning(f"[SystemTools] Lấy trạng thái âm thanh thất bại: {e}")
        return {"volume": 50, "muted": False, "available": False, "error": str(e)}


def _get_application_status() -> Dict[str, Any]:
    """
    Lấy thông tin trạng thái ứng dụng.
    """
    try:
        from src.application import Application
        from src.iot.thing_manager import ThingManager

        app = Application.get_instance()
        thing_manager = ThingManager.get_instance()

        # Giá trị của DeviceState là chuỗi trực tiếp, không cần truy cập thuộc tính .name
        device_state = str(app.get_device_state())
        iot_count = len(thing_manager.things) if thing_manager else 0

        return {
            "device_state": device_state,
            "iot_devices": iot_count,
        }

    except Exception as e:
        logger.warning(f"[SystemTools] Lấy trạng thái ứng dụng thất bại: {e}")
        return {"device_state": "unknown", "iot_devices": 0, "error": str(e)}
