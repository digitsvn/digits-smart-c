"""Các hàm MCP tool cho quản lý lịch.

Cung cấp các hàm async để MCP server gọi.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict

from src.utils.logging_config import get_logger

from .manager import get_calendar_manager
from .models import CalendarEvent

logger = get_logger(__name__)


async def create_event(args: Dict[str, Any]) -> str:
    """
    Tạo sự kiện lịch.
    """
    try:
        title = args["title"]
        start_time = args["start_time"]
        end_time = args.get("end_time")
        description = args.get("description", "")
        category = args.get("category", "Mặc định")
        reminder_minutes = args.get("reminder_minutes", 15)

        # Nếu không có end_time, tự đặt thời lượng theo danh mục
        if not end_time:
            start_dt = datetime.fromisoformat(start_time)

            # Đặt thời lượng mặc định theo danh mục
            if category in ["Nhắc nhở", "Nghỉ ngơi", "Đứng dậy"]:
                # Hoạt động ngắn: 5 phút
                end_dt = start_dt + timedelta(minutes=5)
            elif category in ["Họp", "Công việc"]:
                # Công việc: 1 giờ
                end_dt = start_dt + timedelta(hours=1)
            elif (
                "nhắc nhở" in title.lower()
                or "đứng dậy" in title.lower()
                or "nghỉ ngơi" in title.lower()
            ):
                # Theo tiêu đề: hoạt động ngắn
                end_dt = start_dt + timedelta(minutes=5)
            else:
                # Mặc định: 30 phút
                end_dt = start_dt + timedelta(minutes=30)

            end_time = end_dt.isoformat()

        # Kiểm tra định dạng thời gian
        datetime.fromisoformat(start_time)
        datetime.fromisoformat(end_time)

        # Tạo event
        event = CalendarEvent(
            title=title,
            start_time=start_time,
            end_time=end_time,
            description=description,
            category=category,
            reminder_minutes=reminder_minutes,
        )

        manager = get_calendar_manager()
        if manager.add_event(event):
            return json.dumps(
                {
                    "success": True,
                    "message": "Tạo lịch thành công",
                    "event_id": event.id,
                    "event": event.to_dict(),
                },
                ensure_ascii=False,
            )
        else:
            return json.dumps(
                {"success": False, "message": "Tạo lịch thất bại, có thể bị trùng thời gian"},
                ensure_ascii=False,
            )

    except Exception as e:
        logger.error(f"Tạo lịch thất bại: {e}")
        return json.dumps(
            {"success": False, "message": f"Tạo lịch thất bại: {str(e)}"}, ensure_ascii=False
        )


async def get_events_by_date(args: Dict[str, Any]) -> str:
    """
    Truy vấn lịch theo ngày.
    """
    try:
        date_type = args.get("date_type", "today")  # today, tomorrow, week, month
        category = args.get("category")

        now = datetime.now()

        if date_type == "today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)
        elif date_type == "tomorrow":
            start_date = (now + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            end_date = start_date + timedelta(days=1)
        elif date_type == "week":
            # Tuần này
            days_since_monday = now.weekday()
            start_date = (now - timedelta(days=days_since_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            end_date = start_date + timedelta(days=7)
        elif date_type == "month":
            # Tháng này
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if now.month == 12:
                end_date = start_date.replace(year=now.year + 1, month=1)
            else:
                end_date = start_date.replace(month=now.month + 1)
        else:
            # Phạm vi ngày tùy chỉnh
            start_date = (
                datetime.fromisoformat(args["start_date"])
                if args.get("start_date")
                else None
            )
            end_date = (
                datetime.fromisoformat(args["end_date"])
                if args.get("end_date")
                else None
            )

        manager = get_calendar_manager()
        events = manager.get_events(
            start_date=start_date.isoformat() if start_date else None,
            end_date=end_date.isoformat() if end_date else None,
            category=category,
        )

        # Format output
        events_data = []
        for event in events:
            event_dict = event.to_dict()
            # Thêm display_time dễ đọc
            start_dt = datetime.fromisoformat(event.start_time)
            end_dt = datetime.fromisoformat(event.end_time)
            event_dict["display_time"] = (
                f"{start_dt.strftime('%m/%d %H:%M')} - {end_dt.strftime('%H:%M')}"
            )
            events_data.append(event_dict)

        return json.dumps(
            {
                "success": True,
                "date_type": date_type,
                "total_events": len(events_data),
                "events": events_data,
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        logger.error(f"Truy vấn lịch thất bại: {e}")
        return json.dumps(
            {"success": False, "message": f"Truy vấn lịch thất bại: {str(e)}"}, ensure_ascii=False
        )


async def update_event(args: Dict[str, Any]) -> str:
    """
    Cập nhật sự kiện lịch.
    """
    try:
        event_id = args["event_id"]

        # Tạo dict field cần update
        update_fields = {}
        for field in [
            "title",
            "start_time",
            "end_time",
            "description",
            "category",
            "reminder_minutes",
        ]:
            if field in args:
                update_fields[field] = args[field]

        if not update_fields:
            return json.dumps(
                {"success": False, "message": "Không có trường nào để cập nhật"},
                ensure_ascii=False,
            )

        manager = get_calendar_manager()
        if manager.update_event(event_id, **update_fields):
            return json.dumps(
                {
                    "success": True,
                    "message": "Cập nhật lịch thành công",
                    "updated_fields": list(update_fields.keys()),
                },
                ensure_ascii=False,
            )
        else:
            return json.dumps(
                {"success": False, "message": "Cập nhật lịch thất bại: không tìm thấy sự kiện"},
                ensure_ascii=False,
            )

    except Exception as e:
        logger.error(f"Cập nhật lịch thất bại: {e}")
        return json.dumps(
            {"success": False, "message": f"Cập nhật lịch thất bại: {str(e)}"}, ensure_ascii=False
        )


async def delete_event(args: Dict[str, Any]) -> str:
    """
    Xóa sự kiện lịch.
    """
    try:
        event_id = args["event_id"]

        manager = get_calendar_manager()
        if manager.delete_event(event_id):
            return json.dumps(
                {"success": True, "message": "Xóa lịch thành công"}, ensure_ascii=False
            )
        else:
            return json.dumps(
                {"success": False, "message": "Xóa lịch thất bại: không tìm thấy sự kiện"},
                ensure_ascii=False,
            )

    except Exception as e:
        logger.error(f"Xóa lịch thất bại: {e}")
        return json.dumps(
            {"success": False, "message": f"Xóa lịch thất bại: {str(e)}"}, ensure_ascii=False
        )


async def delete_events_batch(args: Dict[str, Any]) -> str:
    """
    Xóa sự kiện lịch hàng loạt.
    """
    try:
        start_date = args.get("start_date")
        end_date = args.get("end_date")
        category = args.get("category")
        delete_all = args.get("delete_all", False)
        date_type = args.get("date_type")

        # Xử lý tham số date_type (tương tự get_events_by_date)
        if date_type and not (start_date and end_date):
            now = datetime.now()

            if date_type == "today":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date + timedelta(days=1)
            elif date_type == "tomorrow":
                start_date = (now + timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                end_date = start_date + timedelta(days=1)
            elif date_type == "week":
                # Tuần này
                days_since_monday = now.weekday()
                start_date = (now - timedelta(days=days_since_monday)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                end_date = start_date + timedelta(days=7)
            elif date_type == "month":
                # Tháng này
                start_date = now.replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                )
                if now.month == 12:
                    end_date = start_date.replace(year=now.year + 1, month=1)
                else:
                    end_date = start_date.replace(month=now.month + 1)

            # Chuyển sang chuỗi ISO
            if isinstance(start_date, datetime):
                start_date = start_date.isoformat()
            if isinstance(end_date, datetime):
                end_date = end_date.isoformat()

        manager = get_calendar_manager()
        result = manager.delete_events_batch(
            start_date=start_date,
            end_date=end_date,
            category=category,
            delete_all=delete_all,
        )

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Xóa lịch hàng loạt thất bại: {e}")
        return json.dumps(
            {"success": False, "message": f"Xóa lịch hàng loạt thất bại: {str(e)}"},
            ensure_ascii=False,
        )


async def get_categories(args: Dict[str, Any]) -> str:
    """
    Lấy tất cả danh mục lịch.
    """
    try:
        manager = get_calendar_manager()
        categories = manager.get_categories()

        return json.dumps(
            {"success": True, "categories": categories}, ensure_ascii=False
        )

    except Exception as e:
        logger.error(f"Lấy danh mục thất bại: {e}")
        return json.dumps(
            {"success": False, "message": f"Lấy danh mục thất bại: {str(e)}"}, ensure_ascii=False
        )


async def get_upcoming_events(args: Dict[str, Any]) -> str:
    """
    Lấy các sự kiện sắp tới (trong X giờ tới)
    """
    try:
        hours = args.get("hours", 24)  # mặc định 24 giờ

        now = datetime.now()
        end_time = now + timedelta(hours=hours)

        manager = get_calendar_manager()
        events = manager.get_events(
            start_date=now.isoformat(), end_date=end_time.isoformat()
        )

        # Tính thời gian còn lại
        upcoming_events = []
        for event in events:
            event_dict = event.to_dict()
            start_dt = datetime.fromisoformat(event.start_time)

            # Tính khoảng thời gian tới lúc bắt đầu
            time_until = start_dt - now
            if time_until.total_seconds() > 0:
                hours_until = int(time_until.total_seconds() // 3600)
                minutes_until = int((time_until.total_seconds() % 3600) // 60)

                if hours_until > 0:
                    time_display = f"sau {hours_until} giờ {minutes_until} phút"
                else:
                    time_display = f"sau {minutes_until} phút"

                event_dict["time_until"] = time_display
                event_dict["time_until_minutes"] = int(time_until.total_seconds() // 60)
                upcoming_events.append(event_dict)

        return json.dumps(
            {
                "success": True,
                "query_hours": hours,
                "total_events": len(upcoming_events),
                "events": upcoming_events,
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        logger.error(f"Lấy sự kiện sắp tới thất bại: {e}")
        return json.dumps(
            {"success": False, "message": f"Lấy sự kiện sắp tới thất bại: {str(e)}"},
            ensure_ascii=False,
        )
