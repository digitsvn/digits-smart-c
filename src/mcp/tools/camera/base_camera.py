"""
Base camera implementation.
"""

import threading
from abc import ABC, abstractmethod
from typing import Dict

from src.utils.config_manager import ConfigManager
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class BaseCamera(ABC):
    """
    Lớp cơ sở Camera, định nghĩa các giao diện.
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        """
        Khởi tạo Camera cơ sở.
        """
        self.jpeg_data = {"buf": b"", "len": 0}  # Dữ liệu byte JPEG của hình ảnh # Độ dài dữ liệu byte

        # Đọc tham số camera từ cấu hình
        config = ConfigManager.get_instance()
        self.camera_index = config.get_config("CAMERA.camera_index", 0)
        self.frame_width = config.get_config("CAMERA.frame_width", 640)
        self.frame_height = config.get_config("CAMERA.frame_height", 480)

    @abstractmethod
    def capture(self) -> bool:
        """
        Chụp ảnh.
        """

    @abstractmethod
    def analyze(self, question: str) -> str:
        """
        Phân tích hình ảnh.
        """

    def get_jpeg_data(self) -> Dict[str, any]:
        """
        Lấy dữ liệu JPEG.
        """
        return self.jpeg_data

    def set_jpeg_data(self, data_bytes: bytes):
        """
        Thiết lập dữ liệu JPEG.
        """
        self.jpeg_data["buf"] = data_bytes
        self.jpeg_data["len"] = len(data_bytes)

    def reload_config(self):
        """
        Reload camera configuration from ConfigManager (for hot-reload without app restart).
        """
        config = ConfigManager.get_instance()
        self.camera_index = config.get_config("CAMERA.camera_index", 0)
        self.frame_width = config.get_config("CAMERA.frame_width", 640)
        self.frame_height = config.get_config("CAMERA.frame_height", 480)
        logger.info(f"Camera config reloaded: index={self.camera_index}, size={self.frame_width}x{self.frame_height}")
