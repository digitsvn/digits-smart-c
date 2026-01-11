"""Module thao tác SQLite cho quản lý lịch."""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.utils.logging_config import get_logger
from src.utils.resource_finder import get_user_data_dir

logger = get_logger(__name__)


def _get_database_file_path() -> str:
    """
    Lấy đường dẫn file DB, đảm bảo nằm trong thư mục có quyền ghi.
    """
    data_dir = get_user_data_dir()
    database_file = str(data_dir / "calendar.db")
    logger.debug(f"Dùng đường dẫn DB: {database_file}")
    return database_file


# Đường dẫn DB - lấy qua hàm để đảm bảo có quyền ghi
DATABASE_FILE = _get_database_file_path()


class CalendarDatabase:
    """
    Lớp thao tác DB cho quản lý lịch.
    """

    def __init__(self):
        self.db_file = DATABASE_FILE
        self._ensure_database()

    def _ensure_database(self):
        """
        Đảm bảo DB và các bảng tồn tại.
        """
        os.makedirs(os.path.dirname(self.db_file), exist_ok=True)

        with self._get_connection() as conn:
            # Tạo bảng events
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    category TEXT DEFAULT 'Mặc định',
                    reminder_minutes INTEGER DEFAULT 15,
                    reminder_time TEXT,
                    reminder_sent BOOLEAN DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """
            )

            # Tạo bảng categories
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL
                )
            """
            )

            # Thêm danh mục mặc định
            default_categories = ["Mặc định", "Công việc", "Cá nhân", "Họp", "Nhắc nhở"]
            for category in default_categories:
                conn.execute(
                    "INSERT OR IGNORE INTO categories (name) VALUES (?)", (category,)
                )

            conn.commit()

            # Kiểm tra và thêm field mới (nâng cấp DB)
            self._upgrade_database(conn)

            logger.info("Khởi tạo cơ sở dữ liệu hoàn tất")

    @contextmanager
    def _get_connection(self):
        """
        Context manager để lấy kết nối DB.
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row  # cho phép truy cập theo tên cột
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Thao tác DB thất bại: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def add_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Thêm sự kiện.
        """
        try:
            with self._get_connection() as conn:
                # Kiểm tra trùng thời gian
                if self._has_conflict(conn, event_data):
                    return False

                conn.execute(
                    """
                    INSERT INTO events (
                        id, title, start_time, end_time, description,
                        category, reminder_minutes, reminder_time, reminder_sent,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        event_data["id"],
                        event_data["title"],
                        event_data["start_time"],
                        event_data["end_time"],
                        event_data["description"],
                        event_data["category"],
                        event_data["reminder_minutes"],
                        event_data.get("reminder_time"),
                        event_data.get("reminder_sent", False),
                        event_data["created_at"],
                        event_data["updated_at"],
                    ),
                )
                conn.commit()
                logger.info(f"Thêm sự kiện thành công: {event_data['title']}")
                return True
        except Exception as e:
            logger.error(f"Thêm sự kiện thất bại: {e}")
            return False

    def get_events(
        self, start_date: str = None, end_date: str = None, category: str = None
    ) -> List[Dict[str, Any]]:
        """
        Lấy danh sách sự kiện.
        """
        try:
            with self._get_connection() as conn:
                query = "SELECT * FROM events WHERE 1=1"
                params = []

                if start_date:
                    query += " AND start_time >= ?"
                    params.append(start_date)

                if end_date:
                    query += " AND start_time <= ?"
                    params.append(end_date)

                if category:
                    query += " AND category = ?"
                    params.append(category)

                query += " ORDER BY start_time"

                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

                events = []
                for row in rows:
                    events.append(dict(row))

                return events
        except Exception as e:
            logger.error(f"Lấy sự kiện thất bại: {e}")
            return []

    def update_event(self, event_id: str, **kwargs) -> bool:
        """
        Cập nhật sự kiện.
        """
        try:
            with self._get_connection() as conn:
                # Tạo câu query update
                set_clauses = []
                params = []

                for key, value in kwargs.items():
                    if key in [
                        "title",
                        "start_time",
                        "end_time",
                        "description",
                        "category",
                        "reminder_minutes",
                    ]:
                        set_clauses.append(f"{key} = ?")
                        params.append(value)

                if not set_clauses:
                    return False

                # Thêm updated_at
                set_clauses.append("updated_at = ?")
                params.append(datetime.now().isoformat())
                params.append(event_id)

                query = f"UPDATE events SET {', '.join(set_clauses)} WHERE id = ?"

                cursor = conn.execute(query, params)
                conn.commit()

                if cursor.rowcount > 0:
                    logger.info(f"Cập nhật sự kiện thành công: {event_id}")
                    return True
                else:
                    logger.warning(f"Không tìm thấy sự kiện: {event_id}")
                    return False
        except Exception as e:
            logger.error(f"Cập nhật sự kiện thất bại: {e}")
            return False

    def delete_event(self, event_id: str) -> bool:
        """
        Xoá sự kiện.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
                conn.commit()

                if cursor.rowcount > 0:
                    logger.info(f"Xoá sự kiện thành công: {event_id}")
                    return True
                else:
                    logger.warning(f"Không tìm thấy sự kiện: {event_id}")
                    return False
        except Exception as e:
            logger.error(f"Xoá sự kiện thất bại: {e}")
            return False

    def delete_events_batch(
        self,
        start_date: str = None,
        end_date: str = None,
        category: str = None,
        delete_all: bool = False,
    ) -> Dict[str, Any]:
        """Xoá sự kiện hàng loạt.

        Args:
            start_date: Ngày bắt đầu (ISO)
            end_date: Ngày kết thúc (ISO)
            category: Lọc theo danh mục
            delete_all: Có xoá tất cả sự kiện hay không

        Returns:
            Dict kết quả xoá
        """
        try:
            with self._get_connection() as conn:
                if delete_all:
                    # Xoá tất cả sự kiện
                    cursor = conn.execute("SELECT COUNT(*) FROM events")
                    total_count = cursor.fetchone()[0]

                    if total_count == 0:
                        return {
                            "success": True,
                            "deleted_count": 0,
                            "message": "Không có sự kiện nào để xoá",
                        }

                    cursor = conn.execute("DELETE FROM events")
                    conn.commit()

                    logger.info(
                        f"Xoá tất cả sự kiện thành công, tổng cộng {total_count} sự kiện"
                    )
                    return {
                        "success": True,
                        "deleted_count": total_count,
                        "message": f"Đã xoá tất cả {total_count} sự kiện",
                    }

                else:
                    # Xoá theo điều kiện
                    # Trước tiên truy vấn các sự kiện phù hợp
                    query = "SELECT id, title FROM events WHERE 1=1"
                    params = []

                    if start_date:
                        query += " AND start_time >= ?"
                        params.append(start_date)

                    if end_date:
                        query += " AND start_time <= ?"
                        params.append(end_date)

                    if category:
                        query += " AND category = ?"
                        params.append(category)

                    cursor = conn.execute(query, params)
                    events_to_delete = cursor.fetchall()

                    if not events_to_delete:
                        return {
                            "success": True,
                            "deleted_count": 0,
                            "message": "Không có sự kiện phù hợp để xoá",
                        }

                    # Thực hiện xoá
                    delete_query = "DELETE FROM events WHERE 1=1"
                    delete_params = []

                    if start_date:
                        delete_query += " AND start_time >= ?"
                        delete_params.append(start_date)

                    if end_date:
                        delete_query += " AND start_time <= ?"
                        delete_params.append(end_date)

                    if category:
                        delete_query += " AND category = ?"
                        delete_params.append(category)

                    cursor = conn.execute(delete_query, delete_params)
                    deleted_count = cursor.rowcount
                    conn.commit()

                    # Ghi lại tiêu đề các sự kiện đã xoá
                    deleted_titles = [event[1] for event in events_to_delete]
                    logger.info(
                        f"Xoá hàng loạt thành công, đã xoá {deleted_count} sự kiện: "
                        f"{', '.join(deleted_titles[:3])}"
                        f"{'...' if len(deleted_titles) > 3 else ''}"
                    )

                    return {
                        "success": True,
                        "deleted_count": deleted_count,
                        "deleted_titles": deleted_titles,
                        "message": f"Đã xoá {deleted_count} sự kiện",
                    }

        except Exception as e:
            logger.error(f"Xoá hàng loạt thất bại: {e}")
            return {
                "success": False,
                "deleted_count": 0,
                "message": f"Xoá hàng loạt thất bại: {str(e)}",
            }

    def get_event_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Lấy sự kiện theo ID.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,))
                row = cursor.fetchone()

                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"Lấy sự kiện thất bại: {e}")
            return None

    def get_categories(self) -> List[str]:
        """
        Lấy tất cả danh mục.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT name FROM categories ORDER BY name")
                rows = cursor.fetchall()
                return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"Lấy danh mục thất bại: {e}")
            return ["Mặc định"]

    def add_category(self, category_name: str) -> bool:
        """
        Thêm danh mục mới.
        """
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO categories (name) VALUES (?)",
                    (category_name,),
                )
                conn.commit()
                logger.info(f"Thêm danh mục thành công: {category_name}")
                return True
        except Exception as e:
            logger.error(f"Thêm danh mục thất bại: {e}")
            return False

    def delete_category(self, category_name: str) -> bool:
        """
        Xoá danh mục (chỉ khi không có sự kiện sử dụng)
        """
        try:
            with self._get_connection() as conn:
                # Kiểm tra xem có sự kiện nào đang dùng danh mục này không
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM events WHERE category = ?", (category_name,)
                )
                count = cursor.fetchone()[0]

                if count > 0:
                    logger.warning(
                        f"Danh mục '{category_name}' đang được dùng, không thể xoá"
                    )
                    return False

                cursor = conn.execute(
                    "DELETE FROM categories WHERE name = ?", (category_name,)
                )
                conn.commit()

                if cursor.rowcount > 0:
                    logger.info(f"Xoá danh mục thành công: {category_name}")
                    return True
                else:
                    logger.warning(f"Không tìm thấy danh mục: {category_name}")
                    return False
        except Exception as e:
            logger.error(f"Xoá danh mục thất bại: {e}")
            return False

    def _has_conflict(
        self, conn: sqlite3.Connection, event_data: Dict[str, Any]
    ) -> bool:
        """
        Kiểm tra trùng thời gian.
        """
        cursor = conn.execute(
            """
            SELECT title FROM events
            WHERE id != ? AND (
                (start_time < ? AND end_time > ?) OR
                (start_time < ? AND end_time > ?)
            )
        """,
            (
                event_data["id"],
                event_data["end_time"],
                event_data["start_time"],
                event_data["start_time"],
                event_data["end_time"],
            ),
        )

        conflicting_events = cursor.fetchall()

        if conflicting_events:
            for event in conflicting_events:
                logger.warning(f"Trùng thời gian: trùng với sự kiện '{event[0]}'")
            return True

        return False

    def get_statistics(self) -> Dict[str, Any]:
        """
        Lấy thống kê.
        """
        try:
            with self._get_connection() as conn:
                # Tổng số sự kiện
                cursor = conn.execute("SELECT COUNT(*) FROM events")
                total_events = cursor.fetchone()[0]

                # Thống kê theo danh mục
                cursor = conn.execute(
                    """
                    SELECT category, COUNT(*)
                    FROM events
                    GROUP BY category
                    ORDER BY COUNT(*) DESC
                """
                )
                category_stats = dict(cursor.fetchall())

                # Số sự kiện hôm nay
                today = datetime.now().strftime("%Y-%m-%d")
                cursor = conn.execute(
                    """
                    SELECT COUNT(*) FROM events
                    WHERE date(start_time) = ?
                """,
                    (today,),
                )
                today_events = cursor.fetchone()[0]

                return {
                    "total_events": total_events,
                    "category_stats": category_stats,
                    "today_events": today_events,
                }
        except Exception as e:
            logger.error(f"Lấy thống kê thất bại: {e}")
            return {}

    def migrate_from_json(self, json_file_path: str) -> bool:
        """
        Di chuyển dữ liệu từ file JSON.
        """
        try:
            import json

            if not os.path.exists(json_file_path):
                logger.info("Không có file JSON, bỏ qua di chuyển")
                return True

            with open(json_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            events_data = data.get("events", [])
            categories_data = data.get("categories", [])

            with self._get_connection() as conn:
                # Di chuyển danh mục
                for category in categories_data:
                    conn.execute(
                        "INSERT OR IGNORE INTO categories (name) VALUES (?)",
                        (category,),
                    )

                # Di chuyển sự kiện
                for event_data in events_data:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO events (
                            id, title, start_time, end_time, description,
                            category, reminder_minutes, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            event_data["id"],
                            event_data["title"],
                            event_data["start_time"],
                            event_data["end_time"],
                            event_data.get("description", ""),
                            event_data.get("category", "Mặc định"),
                            event_data.get("reminder_minutes", 15),
                            event_data.get("created_at", datetime.now().isoformat()),
                            event_data.get("updated_at", datetime.now().isoformat()),
                        ),
                    )

                conn.commit()
                logger.info(
                    f"Đã di chuyển {len(events_data)} sự kiện và {len(categories_data)} danh mục"
                )
                return True

        except Exception as e:
            logger.error(f"Di chuyển dữ liệu thất bại: {e}")
            return False

    def _upgrade_database(self, conn: sqlite3.Connection):
        """
        Nâng cấp cấu trúc DB.
        """
        try:
            # Kiểm tra các cột mới
            cursor = conn.execute("PRAGMA table_info(events)")
            columns = [col[1] for col in cursor.fetchall()]

            # Thêm cột reminder_time
            if "reminder_time" not in columns:
                conn.execute("ALTER TABLE events ADD COLUMN reminder_time TEXT")
                logger.info("Đã thêm cột reminder_time")

            # Thêm cột reminder_sent
            if "reminder_sent" not in columns:
                conn.execute(
                    "ALTER TABLE events ADD COLUMN reminder_sent BOOLEAN DEFAULT 0"
                )
                logger.info("Đã thêm cột reminder_sent")

            # Tính và gán reminder_time cho các sự kiện hiện có
            cursor = conn.execute(
                "SELECT id, start_time, reminder_minutes "
                "FROM events WHERE reminder_time IS NULL"
            )
            events_to_update = cursor.fetchall()

            for event in events_to_update:
                event_id, start_time, reminder_minutes = event
                try:
                    from datetime import timedelta

                    start_dt = datetime.fromisoformat(start_time)
                    reminder_dt = start_dt - timedelta(minutes=reminder_minutes)

                    conn.execute(
                        "UPDATE events SET reminder_time = ? WHERE id = ?",
                        (reminder_dt.isoformat(), event_id),
                    )
                except Exception as e:
                    logger.warning(
                        f"Tính thời gian nhắc cho sự kiện {event_id} thất bại: {e}"
                    )

            if events_to_update:
                logger.info(
                    f"Đã thiết lập thời gian nhắc cho {len(events_to_update)} sự kiện hiện có"
                )

            conn.commit()

        except Exception as e:
            logger.error(f"Nâng cấp DB thất bại: {e}", exc_info=True)


# Instance DB toàn cục
_calendar_db = None


def get_calendar_database() -> CalendarDatabase:
    """
    Lấy singleton database.
    """
    global _calendar_db
    if _calendar_db is None:
        _calendar_db = CalendarDatabase()
    return _calendar_db
