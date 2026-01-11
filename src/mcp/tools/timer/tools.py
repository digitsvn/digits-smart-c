"""Các hàm MCP tool cho bộ đếm ngược.

Cung cấp các hàm async để MCP server gọi.
"""

import json
from typing import Any, Dict

from src.utils.logging_config import get_logger

from .timer_service import get_timer_service

logger = get_logger(__name__)


async def start_countdown_timer(args: Dict[str, Any]) -> str:
    """Bắt đầu một tác vụ đếm ngược.

    Args:
        args: Dict gồm các tham số:
            - command: Lệnh gọi MCP tool (chuỗi JSON gồm name và arguments)
            - delay: (tùy chọn) thời gian trễ (giây), mặc định 5
            - description: (tùy chọn) mô tả

    Returns:
        str: Chuỗi kết quả dạng JSON
    """
    try:
        command = args["command"]
        delay = args.get("delay")
        description = args.get("description", "")

        logger.info(f"[TimerTools] Bắt đầu đếm ngược - command: {command}, delay: {delay} giây")

        timer_service = get_timer_service()
        result = await timer_service.start_countdown(
            command=command, delay=delay, description=description
        )

        logger.info(f"[TimerTools] Kết quả start timer: {result['success']}")
        return json.dumps(result, ensure_ascii=False, indent=2)

    except KeyError as e:
        error_msg = f"Thiếu tham số bắt buộc: {e}"
        logger.error(f"[TimerTools] {error_msg}")
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
    except Exception as e:
        error_msg = f"Bắt đầu đếm ngược thất bại: {str(e)}"
        logger.error(f"[TimerTools] {error_msg}", exc_info=True)
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)


async def cancel_countdown_timer(args: Dict[str, Any]) -> str:
    """Hủy tác vụ đếm ngược theo ID.

    Args:
        args: Dict gồm:
            - timer_id: ID của timer cần hủy

    Returns:
        str: Chuỗi kết quả dạng JSON
    """
    try:
        timer_id = args["timer_id"]

        logger.info(f"[TimerTools] Hủy timer {timer_id}")

        timer_service = get_timer_service()
        result = await timer_service.cancel_countdown(timer_id)

        logger.info(f"[TimerTools] Kết quả hủy timer: {result['success']}")
        return json.dumps(result, ensure_ascii=False, indent=2)

    except KeyError as e:
        error_msg = f"Thiếu tham số bắt buộc: {e}"
        logger.error(f"[TimerTools] {error_msg}")
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
    except Exception as e:
        error_msg = f"Hủy timer thất bại: {str(e)}"
        logger.error(f"[TimerTools] {error_msg}", exc_info=True)
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)


async def get_active_countdown_timers(args: Dict[str, Any]) -> str:
    """Lấy trạng thái các timer đang chạy.

    Args:
        args: Dict rỗng (hàm này không cần tham số)

    Returns:
        str: Danh sách timer đang chạy dạng JSON
    """
    try:
        logger.info("[TimerTools] Lấy danh sách timer đang chạy")

        timer_service = get_timer_service()
        result = await timer_service.get_active_timers()

        logger.info(f"[TimerTools] Số timer đang chạy: {result['total_active_timers']}")
        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        error_msg = f"Lấy danh sách timer đang chạy thất bại: {str(e)}"
        logger.error(f"[TimerTools] {error_msg}", exc_info=True)
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
