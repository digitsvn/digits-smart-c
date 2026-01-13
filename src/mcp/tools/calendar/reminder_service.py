"""
Dịch vụ nhắc nhở lịch trình - Kiểm tra định kỳ các sự kiện và phát thông báo qua TTS.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional

from src.utils.logging_config import get_logger

from .database import get_calendar_database

logger = get_logger(__name__)


class CalendarReminderService:
    """
    Dịch vụ nhắc nhở lịch trình.
    """

    def __init__(self):
        self.db = get_calendar_database()
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self.check_interval = 30  # Khoảng thời gian kiểm tra (giây)

    def _get_application(self):
        """
        Lấy instance ứng dụng (lazy loading).
        """
        try:
            from src.application import Application

            return Application.get_instance()
        except Exception as e:
            logger.warning(f"Không thể lấy instance ứng dụng: {e}")
            return None

    async def start(self):
        """
        Khởi động dịch vụ nhắc nhở.
        """
        if self.is_running:
            logger.warning("Dịch vụ nhắc nhở đang chạy")
            return

        self.is_running = True
        self._task = asyncio.create_task(self._reminder_loop())
        logger.info("Dịch vụ nhắc nhở lịch đã khởi động")

        # Reset cờ nhắc nhở cho các sự kiện tương lai khi khởi động
        await self.reset_reminder_flags_for_future_events()

    async def stop(self):
        """
        Dừng dịch vụ nhắc nhở.
        """
        if not self.is_running:
            return

        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("Dịch vụ nhắc nhở lịch đã dừng")

    async def _reminder_loop(self):
        """
        Vòng lặp kiểm tra nhắc nhở.
        """
        logger.info("Bắt đầu vòng lặp kiểm tra lịch nhắc")

        while self.is_running:
            try:
                await self._check_and_send_reminders()
                # Dọn dẹp định kỳ các cờ nhắc nhở hết hạn
                await self._cleanup_expired_reminders()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Lỗi trong vòng lặp kiểm tra: {e}", exc_info=True)
                await asyncio.sleep(self.check_interval)

    async def _check_and_send_reminders(self):
        """
        Kiểm tra và gửi nhắc nhở.
        """
        try:
            now = datetime.now()

            # Truy vấn các sự kiện chưa gửi nhắc nhở và đã đến thời gian nhắc
            with self.db._get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM events
                    WHERE reminder_sent = 0
                    AND reminder_time IS NOT NULL
                    AND reminder_time <= ?
                    AND start_time > ?
                    ORDER BY reminder_time
                """,
                    (now.isoformat(), (now - timedelta(hours=1)).isoformat()),
                )

                pending_reminders = cursor.fetchall()

            if not pending_reminders:
                return

            logger.info(f"Tìm thấy {len(pending_reminders)} nhắc nhở cần gửi")

            # Xử lý từng nhắc nhở
            for reminder in pending_reminders:
                await self._send_reminder(dict(reminder))

        except Exception as e:
            logger.error(f"Kiểm tra nhắc nhở thất bại: {e}", exc_info=True)

    async def _send_reminder(self, event_data: dict):
        """
        Gửi một nhắc nhở.
        """
        try:
            event_id = event_data["id"]
            title = event_data["title"]
            start_time = event_data["start_time"]
            description = event_data.get("description", "")
            category = event_data.get("category", "Mặc định")

            # Tính thời gian đến lúc bắt đầu
            start_dt = datetime.fromisoformat(start_time)
            now = datetime.now()
            time_until = start_dt - now

            if time_until.total_seconds() > 0:
                hours = int(time_until.total_seconds() // 3600)
                minutes = int((time_until.total_seconds() % 3600) // 60)

                if hours > 0:
                    time_str = f"{hours} giờ {minutes} phút nữa"
                else:
                    time_str = f"{minutes} phút nữa"
            else:
                time_str = "bây giờ"

            # Xây dựng thông điệp nhắc nhở
            reminder_message = {
                "type": "calendar_reminder",
                "event": {
                    "id": event_id,
                    "title": title,
                    "start_time": start_time,
                    "description": description,
                    "category": category,
                    "time_until": time_str,
                },
                "message": self._format_reminder_text(
                    title, time_str, category, description
                ),
            }

            # Serialize thành JSON
            reminder_json = json.dumps(reminder_message, ensure_ascii=False)

            # Lấy instance ứng dụng và gọi TTS
            application = self._get_application()
            if application and hasattr(application, "_send_text_tts"):
                await application._send_text_tts(reminder_json)
                logger.info(f"Đã gửi nhắc nhở: {title} ({time_str})")
            else:
                logger.warning("Không thể gửi nhắc nhở: ứng dụng hoặc TTS không khả dụng")

            # Đánh dấu đã gửi nhắc nhở
            await self._mark_reminder_sent(event_id)

        except Exception as e:
            logger.error(f"Gửi nhắc nhở thất bại: {e}", exc_info=True)

    def _format_reminder_text(
        self, title: str, time_str: str, category: str, description: str
    ) -> str:
        """
        Định dạng văn bản nhắc nhở.
        """
        # Thông tin nhắc nhở cơ bản
        if time_str == "bây giờ":
            message = f"【{category}】Nhắc lịch: {title} sắp bắt đầu"
        else:
            message = f"【{category}】Nhắc lịch: {title} sẽ bắt đầu trong {time_str}"

        # Thêm mô tả nếu có
        if description:
            message += f", ghi chú: {description}"

        return message

    async def _mark_reminder_sent(self, event_id: str):
        """
        Đánh dấu nhắc nhở đã gửi.
        """
        try:
            with self.db._get_connection() as conn:
                conn.execute(
                    """
                    UPDATE events
                    SET reminder_sent = 1, updated_at = ?
                    WHERE id = ?
                """,
                    (datetime.now().isoformat(), event_id),
                )
                conn.commit()

            logger.debug(f"Đã đánh dấu nhắc nhở đã gửi: {event_id}")

        except Exception as e:
            logger.error(f"Đánh dấu nhắc nhở thất bại: {e}", exc_info=True)

    async def check_daily_events(self):
        """
        Kiểm tra sự kiện trong ngày (gọi khi khởi động chương trình)
        """
        try:
            now = datetime.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)

            with self.db._get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM events
                    WHERE start_time >= ? AND start_time < ?
                    ORDER BY start_time
                """,
                    (today_start.isoformat(), today_end.isoformat()),
                )

                today_events = cursor.fetchall()

            if today_events:
                logger.info(f"Hôm nay có {len(today_events)} lịch hẹn")

                # Xây dựng tóm tắt lịch ngày
                summary_message = {
                    "type": "daily_schedule",
                    "date": today_start.strftime("%Y-%m-%d"),
                    "total_events": len(today_events),
                    "events": [dict(event) for event in today_events],
                    "message": self._format_daily_summary(today_events),
                }

                summary_json = json.dumps(summary_message, ensure_ascii=False)

                # Lấy instance và gửi tóm tắt
                application = self._get_application()
                if application and hasattr(application, "_send_text_tts"):
                    await application._send_text_tts(summary_json)
                    logger.info("Đã gửi tóm tắt lịch hôm nay")

            else:
                logger.info("Hôm nay không có lịch hẹn")

        except Exception as e:
            logger.error(f"Kiểm tra lịch hôm nay thất bại: {e}", exc_info=True)

    def _format_daily_summary(self, events) -> str:
        """
        Định dạng tóm tắt lịch ngày.
        """
        if not events:
            return "Hôm nay không có lịch hẹn nào"

        summary = f"Hôm nay có {len(events)} lịch hẹn:"

        for i, event in enumerate(events, 1):
            start_dt = datetime.fromisoformat(event["start_time"])
            time_str = start_dt.strftime("%H:%M")
            summary += f" {i}.{time_str} {event['title']}"

            if i < len(events):
                summary += ","

        return summary

    async def reset_reminder_flags_for_future_events(self):
        """
        Reset cờ nhắc nhở cho các sự kiện tương lai (gọi khi khởi động lại)
        """
        try:
            now = datetime.now()

            with self.db._get_connection() as conn:
                # Reset tất cả cờ nhắc nhở cho sự kiện tương lai
                cursor = conn.execute(
                    """
                    UPDATE events
                    SET reminder_sent = 0, updated_at = ?
                    WHERE start_time > ? AND reminder_sent = 1
                """,
                    (now.isoformat(), now.isoformat()),
                )

                reset_count = cursor.rowcount
                conn.commit()

            if reset_count > 0:
                logger.info(f"Đã reset {reset_count} cờ nhắc nhở sự kiện tương lai")

        except Exception as e:
            logger.error(f"Reset cờ nhắc nhở thất bại: {e}", exc_info=True)

    async def _cleanup_expired_reminders(self):
        """
        Dọn dẹp cờ nhắc nhở cho sự kiện hết hạn (quá 24 giờ)
        """
        try:
            now = datetime.now()
            cleanup_threshold = now - timedelta(hours=24)

            with self.db._get_connection() as conn:
                cursor = conn.execute(
                    """
                    UPDATE events
                    SET reminder_sent = 1, updated_at = ?
                    WHERE start_time < ? AND reminder_sent = 0
                """,
                    (now.isoformat(), cleanup_threshold.isoformat()),
                )

                cleanup_count = cursor.rowcount
                conn.commit()

            if cleanup_count > 0:
                logger.info(f"Đã dọn dẹp {cleanup_count} cờ nhắc nhở hết hạn")

        except Exception as e:
            logger.error(f"Dọn dẹp cờ nhắc nhở hết hạn thất bại: {e}", exc_info=True)


# Instance dịch vụ nhắc nhở toàn cục
_reminder_service = None


def get_reminder_service() -> CalendarReminderService:
    """
    Lấy singleton dịch vụ nhắc nhở.
    """
    global _reminder_service
    if _reminder_service is None:
        _reminder_service = CalendarReminderService()
    return _reminder_service
