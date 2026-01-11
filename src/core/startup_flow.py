#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Startup Flow Manager - Quản lý luồng khởi động ứng dụng.

Luồng khởi động:
1. Kiểm tra kết nối WiFi → Nếu không có → Bật Hotspot + Hiện WiFi Setup
2. Kiểm tra first-run → Nếu lần đầu → Mở Settings (MIC/Speaker)
3. Kiểm tra kích hoạt → Nếu chưa kích hoạt → Hiện màn hình Activation
4. Đã kích hoạt → Vào Chat với Wake Word luôn lắng nghe
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional, Tuple

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class StartupFlowManager:
    """
    Quản lý luồng khởi động ứng dụng trên Raspberry Pi.
    
    Đảm bảo:
    - Có kết nối WiFi trước khi tiếp tục
    - Audio devices được cấu hình
    - Thiết bị được kích hoạt với server
    """
    
    def __init__(self):
        self._wifi_manager = None
        self._config_manager = None
        self._wifi_setup_complete = asyncio.Event()
        self._settings_complete = asyncio.Event()
    
    async def run_startup_flow(self, mode: str = "gui") -> Tuple[bool, str]:
        """
        Chạy luồng khởi động hoàn chỉnh.
        
        Args:
            mode: "gui" hoặc "cli"
        
        Returns:
            Tuple[bool, str]: (success, message)
        """
        logger.info("=== BẮT ĐẦU LUỒNG KHỞI ĐỘNG ===")
        
        # Bước 1: Kiểm tra và thiết lập WiFi
        wifi_ok = await self._check_and_setup_wifi(mode)
        if not wifi_ok:
            return False, "Không thể thiết lập kết nối WiFi"
        
        # Bước 2: Kiểm tra first-run và mở Settings
        settings_ok = await self._check_first_run_settings(mode)
        if not settings_ok:
            return False, "Người dùng hủy cấu hình Settings"
        
        # Bước 3: Kiểm tra và xử lý Activation
        # (Được xử lý bởi handle_activation trong main.py)
        
        logger.info("=== LUỒNG KHỞI ĐỘNG HOÀN TẤT ===")
        return True, "Khởi động thành công"
    
    async def _check_and_setup_wifi(self, mode: str) -> bool:
        """
        Kiểm tra và thiết lập kết nối WiFi.
        
        Nếu chưa có WiFi, sẽ:
        - CLI mode: In hướng dẫn và chờ
        - GUI mode: Hiện WiFi setup UI hoặc bật hotspot
        """
        logger.info("Bước 1: Kiểm tra kết nối WiFi...")
        
        try:
            from src.network.wifi_manager import get_wifi_manager
            self._wifi_manager = get_wifi_manager()
        except ImportError:
            logger.warning("WiFi Manager không khả dụng, bỏ qua kiểm tra WiFi")
            return True
        except Exception as e:
            logger.error(f"Lỗi khởi tạo WiFi Manager: {e}")
            return True  # Tiếp tục dù có lỗi
        
        # Kiểm tra kết nối hiện tại
        if self._wifi_manager.check_wifi_connection():
            current_ssid = self._wifi_manager.get_current_ssid()
            logger.info(f"Đã có kết nối WiFi: {current_ssid}")
            
            # Kiểm tra Internet
            has_internet = await self._wifi_manager.check_internet_connection_async()
            if has_internet:
                logger.info("Có kết nối Internet ✓")
                return True
            else:
                logger.warning("Đã kết nối WiFi nhưng không có Internet")
                # Vẫn tiếp tục, có thể là mạng nội bộ
                return True
        
        logger.info("Chưa có kết nối WiFi, bắt đầu WiFi Setup...")
        
        if mode == "gui":
            return await self._run_wifi_setup_gui()
        else:
            return await self._run_wifi_setup_cli()
    
    async def _run_wifi_setup_gui(self) -> bool:
        """Chạy WiFi setup trong GUI mode"""
        try:
            # Import WiFi setup service
            from src.network.wifi_captive_portal import WiFiSetupService
            
            # Bật hotspot và captive portal
            service = WiFiSetupService()
            
            # Hiển thị thông báo cho người dùng
            logger.info("=" * 50)
            logger.info("📡 WIFI SETUP MODE")
            logger.info("=" * 50)
            logger.info(f"Kết nối tới WiFi: {self._wifi_manager.DEFAULT_HOTSPOT_SSID}")
            logger.info(f"Mật khẩu: {self._wifi_manager.DEFAULT_HOTSPOT_PASSWORD}")
            logger.info(f"Mở trình duyệt: http://{self._wifi_manager.get_hotspot_ip()}")
            logger.info("=" * 50)
            
            # Chạy WiFi setup (blocking cho đến khi hoàn tất)
            result = await service.run_wifi_setup()
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi WiFi Setup GUI: {e}")
            return False
    
    async def _run_wifi_setup_cli(self) -> bool:
        """Chạy WiFi setup trong CLI mode"""
        try:
            print("\n" + "=" * 50)
            print("📡 CẦN CẤU HÌNH WIFI")
            print("=" * 50)
            print(f"\n1. Kết nối tới WiFi hotspot: {self._wifi_manager.DEFAULT_HOTSPOT_SSID}")
            print(f"   Mật khẩu: {self._wifi_manager.DEFAULT_HOTSPOT_PASSWORD}")
            print(f"\n2. Mở trình duyệt và truy cập: http://{self._wifi_manager.get_hotspot_ip()}")
            print("\n3. Chọn WiFi và nhập mật khẩu")
            print("\n" + "=" * 50)
            
            # Bật hotspot
            if not self._wifi_manager.start_hotspot():
                print("❌ Không thể bật WiFi Hotspot")
                return False
            
            # Import và chạy captive portal
            from src.network.wifi_captive_portal import WiFiSetupService
            service = WiFiSetupService()
            result = await service.run_wifi_setup()
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi WiFi Setup CLI: {e}")
            return False
    
    async def _check_first_run_settings(self, mode: str) -> bool:
        """
        Kiểm tra first-run và mở Settings nếu cần.
        
        First-run yêu cầu:
        - Cấu hình MIC/Speaker
        - Các tùy chọn cơ bản khác
        """
        logger.info("Bước 2: Kiểm tra first-run settings...")
        
        try:
            from src.utils.resource_finder import resource_finder
            from src.utils.config_manager import ConfigManager
            
            self._config_manager = ConfigManager.get_instance()
            
            config_dir = resource_finder.find_config_dir()
            if not config_dir:
                config_dir = resource_finder.get_project_root() / "config"
            
            first_run_marker = Path(config_dir) / ".first_run_done"
            
            if first_run_marker.exists():
                logger.info("First-run đã hoàn tất trước đó ✓")
                return True
            
            logger.info("Phát hiện lần chạy đầu tiên, cần cấu hình Settings")
            
            if mode == "gui":
                return await self._show_first_run_settings_gui()
            else:
                return await self._show_first_run_settings_cli()
                
        except Exception as e:
            logger.error(f"Lỗi kiểm tra first-run: {e}")
            return True  # Tiếp tục dù có lỗi
    
    async def _show_first_run_settings_gui(self) -> bool:
        """Hiển thị Settings GUI cho first-run"""
        try:
            from PyQt5.QtWidgets import QMessageBox
            from src.views.settings.settings_window import SettingsWindow
            
            # Hiển thị thông báo hướng dẫn
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("🎉 Chào mừng đến với Smart C!")
            msg.setText(
                "Đây là lần đầu tiên bạn sử dụng ứng dụng.\n\n"
                "Vui lòng cấu hình các thiết lập cơ bản:\n"
                "• WiFi - Kết nối mạng\n"
                "• Âm thanh - Chọn MIC và Loa\n"
                "• Wakeword - Từ đánh thức\n\n"
                "Nhấn OK để tiếp tục."
            )
            msg.exec_()
            
            # Mở Settings window
            logger.info("Mở Settings window cho first-run")
            dlg = SettingsWindow()
            result = dlg.exec_()
            
            if result == 0:
                logger.warning("Người dùng đóng Settings mà không lưu")
                # Vẫn cho tiếp tục nhưng cảnh báo
                return True
            
            logger.info("First-run Settings hoàn tất ✓")
            return True
            
        except Exception as e:
            logger.error(f"Lỗi hiển thị Settings GUI: {e}")
            return True
    
    async def _show_first_run_settings_cli(self) -> bool:
        """Hiển thị hướng dẫn cấu hình CLI"""
        print("\n" + "=" * 50)
        print("🎉 CHÀO MỪNG ĐẾN VỚI SMART C!")
        print("=" * 50)
        print("\nĐây là lần đầu tiên sử dụng ứng dụng.")
        print("\nVui lòng chạy với tham số --mode gui để cấu hình:")
        print("  python main.py --mode gui")
        print("\nHoặc chỉnh sửa file config/config.json trực tiếp.")
        print("=" * 50 + "\n")
        
        # Trong CLI mode, đánh dấu first-run done và tiếp tục
        try:
            from src.utils.resource_finder import resource_finder
            
            config_dir = resource_finder.find_config_dir()
            if config_dir:
                marker_path = Path(config_dir) / ".first_run_done"
                marker_path.write_text("cli\n", encoding="utf-8")
        except Exception:
            pass
        
        return True


def check_wifi_connection() -> bool:
    """
    Hàm tiện ích kiểm tra kết nối WiFi.
    Sử dụng trong các scripts khởi động.
    """
    try:
        from src.network.wifi_manager import get_wifi_manager
        wifi_manager = get_wifi_manager()
        return wifi_manager.check_wifi_connection()
    except Exception as e:
        logger.error(f"Lỗi kiểm tra WiFi: {e}")
        return False


def is_raspberry_pi() -> bool:
    """Kiểm tra đang chạy trên Raspberry Pi không"""
    try:
        with open('/proc/device-tree/model', 'r') as f:
            model = f.read().lower()
            return 'raspberry pi' in model
    except Exception:
        return False


def is_headless() -> bool:
    """Kiểm tra đang chạy headless (không có display)"""
    return os.environ.get('DISPLAY') is None and os.environ.get('WAYLAND_DISPLAY') is None


# Singleton instance
_startup_flow_manager: Optional[StartupFlowManager] = None


def get_startup_flow_manager() -> StartupFlowManager:
    """Lấy singleton instance"""
    global _startup_flow_manager
    if _startup_flow_manager is None:
        _startup_flow_manager = StartupFlowManager()
    return _startup_flow_manager


async def run_startup_flow(mode: str = "gui") -> Tuple[bool, str]:
    """Chạy startup flow"""
    manager = get_startup_flow_manager()
    return await manager.run_startup_flow(mode)
