#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Network Status Overlay - Hiển thị IP và QR code trên màn hình.

- Khi chưa có mạng: Hiển thị thông tin Hotspot
- Khi đã có mạng: Hiển thị IP + QR code để scan vào Web Settings
"""

import asyncio
import subprocess
from pathlib import Path
from typing import Optional

from src.utils.logging_config import get_logger
from src.utils.resource_finder import get_project_root

logger = get_logger(__name__)


def get_current_ip() -> Optional[str]:
    """Lấy IP hiện tại của Pi."""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


def is_connected() -> bool:
    """Kiểm tra có kết nối internet không."""
    try:
        import socket
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False


def generate_qr_code(url: str, output_path: Path) -> bool:
    """Tạo QR code từ URL."""
    try:
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="white", back_color="transparent")
        img.save(str(output_path))
        return True
    except ImportError:
        # Fallback: dùng command line
        try:
            subprocess.run(
                ["qrencode", "-o", str(output_path), "-s", "8", url],
                capture_output=True, timeout=5
            )
            return output_path.exists()
        except Exception:
            return False
    except Exception as e:
        logger.error(f"Generate QR failed: {e}")
        return False


def get_network_status_text() -> str:
    """Lấy text hiển thị trạng thái mạng."""
    ip = get_current_ip()
    
    if ip:
        return f"📱 Cấu hình: http://{ip}:8080"
    else:
        return "📶 Kết nối WiFi để cấu hình"


def get_hotspot_info() -> dict:
    """Lấy thông tin Hotspot."""
    return {
        "ssid": "SmartC-Setup",
        "password": "smartc123",
        "ip": "192.168.4.1",
        "url": "http://192.168.4.1"
    }


async def start_hotspot_if_no_network():
    """Tự động bật hotspot nếu không có mạng."""
    if is_connected():
        logger.info("Đã kết nối mạng, không cần hotspot")
        return False
    
    logger.info("Không có mạng, đang bật hotspot...")
    
    try:
        from src.network.wifi_manager import WiFiManager
        wifi = WiFiManager()
        success = wifi.start_hotspot()
        
        if success:
            logger.info("Hotspot đã bật: SmartC-Setup / smartc123")
            return True
        else:
            logger.error("Không thể bật hotspot")
            return False
    except Exception as e:
        logger.error(f"Start hotspot failed: {e}")
        return False


def update_gui_network_status(display_model):
    """Cập nhật trạng thái mạng lên GUI."""
    ip = get_current_ip()
    
    if ip:
        # Đã kết nối mạng
        url = f"http://{ip}:8080"
        status_text = f"📱 Settings: {url}"
        
        # Tạo QR code
        qr_path = get_project_root() / "assets" / "qr_settings.png"
        generate_qr_code(url, qr_path)
        
        # Cập nhật lên display model
        if hasattr(display_model, 'networkStatusText'):
            display_model.networkStatusText = status_text
        if hasattr(display_model, 'qrCodePath'):
            display_model.qrCodePath = str(qr_path)
    else:
        # Chưa kết nối
        hotspot = get_hotspot_info()
        status_text = f"📶 WiFi: {hotspot['ssid']} | Pass: {hotspot['password']}"
        
        if hasattr(display_model, 'networkStatusText'):
            display_model.networkStatusText = status_text
