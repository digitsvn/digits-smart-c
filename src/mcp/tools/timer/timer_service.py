"""Dịch vụ đếm ngược.

Quản lý việc tạo, chạy, hủy và truy vấn trạng thái các tác vụ đếm ngược.
"""

import asyncio
import json
from asyncio import Task
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class TimerService:
    """
    Dịch vụ đếm ngược, quản lý tất cả tác vụ đếm ngược.
    """

    def __init__(self):
        # Lưu timer đang chạy trong dict: key=timer_id, value=TimerTask
        self._timers: Dict[int, "TimerTask"] = {}
        self._next_timer_id = 0
        # Dùng lock để bảo vệ truy cập _timers và _next_timer_id
        self._lock = asyncio.Lock()
        self.DEFAULT_DELAY = 5  # delay mặc định (giây)

    async def start_countdown(
        self, command: str, delay: int = None, description: str = ""
    ) -> Dict[str, Any]:
        """Bắt đầu một tác vụ đếm ngược.

        Args:
            command: Lệnh gọi MCP tool cần thực thi (chuỗi JSON gồm name và arguments)
            delay: Thời gian trễ (giây), mặc định 5
            description: Mô tả tác vụ

        Returns:
            Dict[str, Any]: Dict chứa thông tin tác vụ
        """
        if delay is None:
            delay = self.DEFAULT_DELAY

        # Kiểm tra delay
        try:
            delay = int(delay)
            if delay <= 0:
                logger.warning(
                    f"Delay {delay} không hợp lệ, dùng mặc định {self.DEFAULT_DELAY} giây"
                )
                delay = self.DEFAULT_DELAY
        except (ValueError, TypeError):
            logger.warning(
                f"Delay '{delay}' không hợp lệ, dùng mặc định {self.DEFAULT_DELAY} giây"
            )
            delay = self.DEFAULT_DELAY

        # Kiểm tra định dạng command
        try:
            json.loads(command)
        except json.JSONDecodeError:
            logger.error(f"Bắt đầu đếm ngược thất bại: command sai định dạng, không parse được JSON: {command}")
            return {
                "success": False,
                "message": f"Command sai định dạng, không parse được JSON: {command}",
            }

        # Lấy event loop hiện tại
        loop = asyncio.get_running_loop()

        async with self._lock:
            timer_id = self._next_timer_id
            self._next_timer_id += 1

            # Tạo tác vụ đếm ngược
            timer_task = TimerTask(
                timer_id=timer_id,
                command=command,
                delay=delay,
                description=description,
                service=self,
            )

            # Tạo async task
            task = loop.create_task(timer_task.run())
            timer_task.task = task

            self._timers[timer_id] = timer_task

        logger.info(f"Bắt đầu đếm ngược {timer_id}, sẽ chạy sau {delay} giây: {command}")

        return {
            "success": True,
            "message": f"Đếm ngược {timer_id} đã bắt đầu, sẽ chạy sau {delay} giây",
            "timer_id": timer_id,
            "delay": delay,
            "command": command,
            "description": description,
            "start_time": datetime.now().isoformat(),
            "estimated_execution_time": (
                datetime.now() + timedelta(seconds=delay)
            ).isoformat(),
        }

    async def cancel_countdown(self, timer_id: int) -> Dict[str, Any]:
        """Hủy tác vụ đếm ngược theo ID.

        Args:
            timer_id: ID của timer cần hủy

        Returns:
            Dict[str, Any]: Kết quả hủy
        """
        try:
            timer_id = int(timer_id)
        except (ValueError, TypeError):
            logger.error(f"Hủy đếm ngược thất bại: timer_id không hợp lệ {timer_id}")
            return {"success": False, "message": f"timer_id không hợp lệ: {timer_id}"}

        async with self._lock:
            if timer_id in self._timers:
                timer_task = self._timers.pop(timer_id)
                if timer_task.task:
                    timer_task.task.cancel()

                logger.info(f"Đếm ngược {timer_id} đã được hủy")
                return {
                    "success": True,
                    "message": f"Đếm ngược {timer_id} đã hủy",
                    "timer_id": timer_id,
                    "cancelled_at": datetime.now().isoformat(),
                }
            else:
                logger.warning(f"Yêu cầu hủy timer không tồn tại hoặc đã xong: {timer_id}")
                return {
                    "success": False,
                    "message": f"Không tìm thấy timer đang chạy với ID {timer_id}",
                    "timer_id": timer_id,
                }

    async def get_active_timers(self) -> Dict[str, Any]:
        """Lấy trạng thái tất cả timer đếm ngược đang chạy.

        Returns:
            Dict[str, Any]: Danh sách timer đang chạy
        """
        async with self._lock:
            active_timers = []
            current_time = datetime.now()

            for timer_id, timer_task in self._timers.items():
                remaining_time = timer_task.get_remaining_time()
                if remaining_time > 0:
                    active_timers.append(
                        {
                            "timer_id": timer_id,
                            "command": timer_task.command,
                            "description": timer_task.description,
                            "delay": timer_task.delay,
                            "remaining_seconds": remaining_time,
                            "start_time": timer_task.start_time.isoformat(),
                            "estimated_execution_time": timer_task.execution_time.isoformat(),
                            "progress": timer_task.get_progress(),
                        }
                    )

            return {
                "success": True,
                "total_active_timers": len(active_timers),
                "timers": active_timers,
                "current_time": current_time.isoformat(),
            }

    async def cleanup_timer(self, timer_id: int):
        """
        Gỡ timer đã hoàn thành khỏi manager.
        """
        async with self._lock:
            if timer_id in self._timers:
                del self._timers[timer_id]
                logger.debug(f"Đã dọn dẹp timer đã hoàn thành: {timer_id}")

    async def cleanup_all(self):
        """
        Dọn dẹp toàn bộ timer (khi ứng dụng đóng)
        """
        logger.info("Đang dọn dẹp toàn bộ timer...")
        async with self._lock:
            active_timer_ids = list(self._timers.keys())
            for timer_id in active_timer_ids:
                if timer_id in self._timers:
                    timer_task = self._timers.pop(timer_id)
                    if timer_task.task:
                        timer_task.task.cancel()
                    logger.info(f"Đã hủy timer {timer_id}")
        logger.info("Dọn dẹp timer hoàn tất")


class TimerTask:
    """
    Một tác vụ đếm ngược.
    """

    def __init__(
        self,
        timer_id: int,
        command: str,
        delay: int,
        description: str,
        service: TimerService,
    ):
        self.timer_id = timer_id
        self.command = command
        self.delay = delay
        self.description = description
        self.service = service
        self.start_time = datetime.now()
        self.execution_time = self.start_time + timedelta(seconds=delay)
        self.task: Optional[Task] = None

    async def run(self):
        """
        Chạy tác vụ đếm ngược.
        """
        try:
            # Chờ hết thời gian delay
            await asyncio.sleep(self.delay)

            # Thực thi lệnh
            await self._execute_command()

        except asyncio.CancelledError:
            logger.info(f"Timer {self.timer_id} đã bị hủy")
        except Exception as e:
            logger.error(f"Timer {self.timer_id} lỗi khi thực thi: {e}", exc_info=True)
        finally:
            # Tự dọn dẹp
            await self.service.cleanup_timer(self.timer_id)

    async def _execute_command(self):
        """
        Thực thi lệnh khi đếm ngược kết thúc.
        """
        logger.info(f"Timer {self.timer_id} kết thúc, chuẩn bị chạy MCP tool: {self.command}")

        try:
            # Parse lệnh gọi MCP tool
            command_dict = json.loads(self.command)

            # Validate format
            if "name" not in command_dict or "arguments" not in command_dict:
                raise ValueError("Command MCP sai định dạng: bắt buộc có 'name' và 'arguments'")

            tool_name = command_dict["name"]
            arguments = command_dict["arguments"]

            # Lấy MCP server và thực thi tool
            from src.mcp.mcp_server import McpServer

            mcp_server = McpServer.get_instance()

            # Tìm tool
            tool = None
            for t in mcp_server.tools:
                if t.name == tool_name:
                    tool = t
                    break

            if not tool:
                raise ValueError(f"Không tìm thấy MCP tool: {tool_name}")

            # Thực thi MCP tool
            result = await tool.call(arguments)

            # Parse kết quả
            result_data = json.loads(result)
            is_success = not result_data.get("isError", False)

            if is_success:
                logger.info(
                    f"Timer {self.timer_id} chạy MCP tool thành công: {tool_name}"
                )
                await self._notify_execution_result(True, f"Đã thực thi {tool_name}")
            else:
                error_text = result_data.get("content", [{}])[0].get("text", "Lỗi không xác định")
                logger.error(f"Timer {self.timer_id} chạy MCP tool thất bại: {error_text}")
                await self._notify_execution_result(False, error_text)

        except json.JSONDecodeError:
            error_msg = f"Timer {self.timer_id}: command MCP sai định dạng, không parse được JSON"
            logger.error(error_msg)
            await self._notify_execution_result(False, error_msg)
        except Exception as e:
            error_msg = f"Timer {self.timer_id} lỗi khi chạy MCP tool: {e}"
            logger.error(error_msg, exc_info=True)
            await self._notify_execution_result(False, error_msg)

    async def _notify_execution_result(self, success: bool, result: Any):
        """
        Thông báo kết quả thực thi (qua TTS)
        """
        try:
            from src.application import Application

            app = Application.get_instance()
            if success:
                message = f"Timer {self.timer_id} đã hoàn thành"
                if self.description:
                    message = f"{self.description} đã hoàn thành"
            else:
                message = f"Timer {self.timer_id} thực thi thất bại"
                if self.description:
                    message = f"{self.description} thất bại"

            print("Đếm ngược:", message)
            await app._send_text_tts(message)
        except Exception as e:
            logger.warning(f"Thông báo kết quả timer thất bại: {e}")

    def get_remaining_time(self) -> float:
        """
        Lấy thời gian còn lại (giây)
        """
        now = datetime.now()
        remaining = (self.execution_time - now).total_seconds()
        return max(0, remaining)

    def get_progress(self) -> float:
        """
        Lấy tiến độ (số thực trong khoảng 0-1)
        """
        elapsed = (datetime.now() - self.start_time).total_seconds()
        return min(1.0, elapsed / self.delay)


# Global service instance
_timer_service = None


def get_timer_service() -> TimerService:
    """
    Lấy singleton của TimerService.
    """
    global _timer_service
    if _timer_service is None:
        _timer_service = TimerService()
        logger.debug("Tạo instance TimerService")
    return _timer_service
