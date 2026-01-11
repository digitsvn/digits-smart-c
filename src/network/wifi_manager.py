#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WiFi Manager Module - Quản lý kết nối WiFi và Hotspot trên Raspberry Pi.

Sử dụng NetworkManager (nmcli) để:
- Kiểm tra trạng thái kết nối WiFi
- Tạo WiFi Hotspot để cấu hình
- Kết nối tới WiFi network
- Quét danh sách WiFi khả dụng
"""

import asyncio
import os
import re
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Callable, List, Optional

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class WiFiState(Enum):
    """Trạng thái kết nối WiFi"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    HOTSPOT_ACTIVE = "hotspot_active"
    ERROR = "error"


@dataclass
class WiFiNetwork:
    """Thông tin mạng WiFi"""
    ssid: str
    signal_strength: int  # 0-100
    security: str  # "open", "wpa", "wpa2", etc.
    in_use: bool = False
    
    @property
    def signal_bars(self) -> int:
        """Trả về số thanh tín hiệu (0-4)"""
        if self.signal_strength >= 80:
            return 4
        elif self.signal_strength >= 60:
            return 3
        elif self.signal_strength >= 40:
            return 2
        elif self.signal_strength >= 20:
            return 1
        return 0


class WiFiManager:
    """
    Quản lý WiFi và Hotspot cho Raspberry Pi.
    
    Sử dụng nmcli (NetworkManager CLI) để thao tác với WiFi.
    """
    
    # Cấu hình Hotspot mặc định
    DEFAULT_HOTSPOT_SSID = "SmartC-Setup"
    DEFAULT_HOTSPOT_PASSWORD = "smartc123"
    DEFAULT_HOTSPOT_CHANNEL = 6
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self._state = WiFiState.DISCONNECTED
        self._hotspot_connection_name = "SmartC-Hotspot"
        self._state_callbacks: List[Callable[[WiFiState], None]] = []
        self._wifi_interface = self._detect_wifi_interface()
        
        logger.info(f"WiFi Manager khởi tạo, interface: {self._wifi_interface}")
    
    @classmethod
    def get_instance(cls) -> "WiFiManager":
        """Lấy instance singleton"""
        return cls()
    
    def _detect_wifi_interface(self) -> str:
        """Phát hiện interface WiFi (thường là wlan0)"""
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "DEVICE,TYPE", "device"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    parts = line.split(':')
                    if len(parts) >= 2 and parts[1] == 'wifi':
                        return parts[0]
        except Exception as e:
            logger.warning(f"Không thể phát hiện WiFi interface: {e}")
        
        return "wlan0"  # Mặc định
    
    @property
    def state(self) -> WiFiState:
        """Trạng thái hiện tại"""
        return self._state
    
    def add_state_callback(self, callback: Callable[[WiFiState], None]):
        """Đăng ký callback khi trạng thái thay đổi"""
        self._state_callbacks.append(callback)
    
    def remove_state_callback(self, callback: Callable[[WiFiState], None]):
        """Hủy đăng ký callback"""
        if callback in self._state_callbacks:
            self._state_callbacks.remove(callback)
    
    def _notify_state_change(self, new_state: WiFiState):
        """Thông báo thay đổi trạng thái"""
        self._state = new_state
        for callback in self._state_callbacks:
            try:
                callback(new_state)
            except Exception as e:
                logger.error(f"Lỗi callback trạng thái WiFi: {e}")
    
    def _run_nmcli(self, args: List[str], timeout: int = 30) -> subprocess.CompletedProcess:
        """Chạy lệnh nmcli"""
        cmd = ["nmcli"] + args
        logger.debug(f"Chạy lệnh: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            if result.returncode != 0 and result.stderr:
                logger.warning(f"nmcli stderr: {result.stderr}")
            return result
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout chạy lệnh: {' '.join(cmd)}")
            raise
        except Exception as e:
            logger.error(f"Lỗi chạy nmcli: {e}")
            raise
    
    def check_wifi_connection(self) -> bool:
        """
        Kiểm tra thiết bị đã kết nối WiFi chưa.
        
        Returns:
            bool: True nếu đã kết nối WiFi
        """
        try:
            # Kiểm tra trạng thái kết nối
            result = self._run_nmcli(["-t", "-f", "DEVICE,STATE", "device"])
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    parts = line.split(':')
                    if len(parts) >= 2 and parts[0] == self._wifi_interface:
                        state = parts[1].lower()
                        if state == "connected":
                            self._notify_state_change(WiFiState.CONNECTED)
                            return True
                        elif state == "disconnected":
                            self._notify_state_change(WiFiState.DISCONNECTED)
                            return False
            
            # Fallback: kiểm tra có IP không
            result = subprocess.run(
                ["ip", "addr", "show", self._wifi_interface],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and "inet " in result.stdout:
                self._notify_state_change(WiFiState.CONNECTED)
                return True
            
            self._notify_state_change(WiFiState.DISCONNECTED)
            return False
            
        except Exception as e:
            logger.error(f"Lỗi kiểm tra kết nối WiFi: {e}")
            self._notify_state_change(WiFiState.ERROR)
            return False
    
    def get_current_ssid(self) -> Optional[str]:
        """Lấy SSID đang kết nối"""
        try:
            result = self._run_nmcli(["-t", "-f", "NAME,DEVICE", "connection", "show", "--active"])
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    parts = line.split(':')
                    if len(parts) >= 2 and parts[1] == self._wifi_interface:
                        return parts[0]
            
            return None
        except Exception as e:
            logger.error(f"Lỗi lấy SSID hiện tại: {e}")
            return None
    
    def scan_wifi_networks(self) -> List[WiFiNetwork]:
        """
        Quét danh sách mạng WiFi khả dụng.
        
        Returns:
            List[WiFiNetwork]: Danh sách mạng WiFi
        """
        networks = []
        
        try:
            # Yêu cầu quét lại
            self._run_nmcli(["device", "wifi", "rescan"], timeout=15)
            
            # Đợi quét hoàn tất
            asyncio.get_event_loop().run_until_complete(asyncio.sleep(2))
        except Exception:
            pass  # Bỏ qua lỗi rescan
        
        try:
            # Lấy danh sách WiFi
            result = self._run_nmcli([
                "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY",
                "device", "wifi", "list"
            ])
            
            if result.returncode == 0:
                seen_ssids = set()
                for line in result.stdout.strip().split('\n'):
                    if not line:
                        continue
                    
                    parts = line.split(':')
                    if len(parts) >= 4:
                        in_use = parts[0] == '*'
                        ssid = parts[1]
                        
                        # Bỏ qua SSID trống hoặc đã thấy
                        if not ssid or ssid in seen_ssids:
                            continue
                        
                        seen_ssids.add(ssid)
                        
                        try:
                            signal = int(parts[2])
                        except ValueError:
                            signal = 0
                        
                        security = parts[3] if parts[3] else "open"
                        
                        networks.append(WiFiNetwork(
                            ssid=ssid,
                            signal_strength=signal,
                            security=security,
                            in_use=in_use
                        ))
                
                # Sắp xếp theo tín hiệu mạnh nhất
                networks.sort(key=lambda x: x.signal_strength, reverse=True)
            
            logger.info(f"Quét được {len(networks)} mạng WiFi")
            
        except Exception as e:
            logger.error(f"Lỗi quét mạng WiFi: {e}")
        
        return networks
    
    async def scan_wifi_networks_async(self) -> List[WiFiNetwork]:
        """Quét mạng WiFi bất đồng bộ"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.scan_wifi_networks)
    
    def connect_to_wifi(self, ssid: str, password: str = None) -> bool:
        """
        Kết nối tới mạng WiFi.
        
        Args:
            ssid: Tên mạng WiFi
            password: Mật khẩu (None nếu mạng mở)
        
        Returns:
            bool: True nếu kết nối thành công
        """
        try:
            self._notify_state_change(WiFiState.CONNECTING)
            logger.info(f"Đang kết nối tới WiFi: {ssid}")
            
            # Dừng hotspot nếu đang chạy
            self.stop_hotspot()
            
            # Xóa kết nối cũ cùng tên nếu có
            self._run_nmcli(["connection", "delete", ssid])
            
            # Tạo kết nối mới
            if password:
                result = self._run_nmcli([
                    "device", "wifi", "connect", ssid,
                    "password", password,
                    "ifname", self._wifi_interface
                ], timeout=60)
            else:
                result = self._run_nmcli([
                    "device", "wifi", "connect", ssid,
                    "ifname", self._wifi_interface
                ], timeout=60)
            
            if result.returncode == 0:
                logger.info(f"Kết nối WiFi thành công: {ssid}")
                self._notify_state_change(WiFiState.CONNECTED)
                return True
            else:
                logger.error(f"Kết nối WiFi thất bại: {result.stderr}")
                self._notify_state_change(WiFiState.DISCONNECTED)
                return False
                
        except Exception as e:
            logger.error(f"Lỗi kết nối WiFi: {e}")
            self._notify_state_change(WiFiState.ERROR)
            return False
    
    async def connect_to_wifi_async(self, ssid: str, password: str = None) -> bool:
        """Kết nối WiFi bất đồng bộ"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.connect_to_wifi, ssid, password)
    
    def start_hotspot(
        self,
        ssid: str = None,
        password: str = None,
        channel: int = None
    ) -> bool:
        """
        Bật WiFi Hotspot để cho phép cấu hình.
        
        Args:
            ssid: Tên hotspot (mặc định: SmartC-Setup)
            password: Mật khẩu (mặc định: smartc123)
            channel: Kênh WiFi (mặc định: 6)
        
        Returns:
            bool: True nếu bật thành công
        """
        ssid = ssid or self.DEFAULT_HOTSPOT_SSID
        password = password or self.DEFAULT_HOTSPOT_PASSWORD
        channel = channel or self.DEFAULT_HOTSPOT_CHANNEL
        
        try:
            logger.info(f"Bật WiFi Hotspot: {ssid}")
            
            # Dừng hotspot cũ nếu có
            self.stop_hotspot()
            
            # Tạo hotspot
            result = self._run_nmcli([
                "device", "wifi", "hotspot",
                "ifname", self._wifi_interface,
                "ssid", ssid,
                "password", password,
                "band", "bg",  # 2.4GHz
                "channel", str(channel)
            ], timeout=30)
            
            if result.returncode == 0:
                logger.info(f"Hotspot đã bật: {ssid} (mật khẩu: {password})")
                self._notify_state_change(WiFiState.HOTSPOT_ACTIVE)
                return True
            else:
                # Thử cách khác: tạo connection profile
                logger.warning(f"Hotspot command thất bại, thử cách khác: {result.stderr}")
                return self._start_hotspot_via_connection(ssid, password)
                
        except Exception as e:
            logger.error(f"Lỗi bật hotspot: {e}")
            self._notify_state_change(WiFiState.ERROR)
            return False
    
    def _start_hotspot_via_connection(self, ssid: str, password: str) -> bool:
        """Tạo hotspot bằng cách tạo connection profile"""
        try:
            # Xóa connection cũ
            self._run_nmcli(["connection", "delete", self._hotspot_connection_name])
            
            # Tạo connection mới
            result = self._run_nmcli([
                "connection", "add",
                "type", "wifi",
                "con-name", self._hotspot_connection_name,
                "autoconnect", "no",
                "wifi.mode", "ap",
                "wifi.ssid", ssid,
                "wifi-sec.key-mgmt", "wpa-psk",
                "wifi-sec.psk", password,
                "ipv4.method", "shared",
                "ipv4.addresses", "192.168.4.1/24"
            ])
            
            if result.returncode != 0:
                logger.error(f"Tạo connection hotspot thất bại: {result.stderr}")
                return False
            
            # Kích hoạt connection
            result = self._run_nmcli([
                "connection", "up", self._hotspot_connection_name,
                "ifname", self._wifi_interface
            ])
            
            if result.returncode == 0:
                logger.info("Hotspot đã bật qua connection profile")
                self._notify_state_change(WiFiState.HOTSPOT_ACTIVE)
                return True
            else:
                logger.error(f"Kích hoạt hotspot thất bại: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Lỗi tạo hotspot via connection: {e}")
            return False
    
    def stop_hotspot(self) -> bool:
        """
        Tắt WiFi Hotspot.
        
        Returns:
            bool: True nếu tắt thành công
        """
        try:
            # Tắt connection hotspot nếu có
            result = self._run_nmcli([
                "connection", "down", self._hotspot_connection_name
            ])
            
            # Xóa connection hotspot
            self._run_nmcli([
                "connection", "delete", self._hotspot_connection_name
            ])
            
            logger.info("Đã tắt Hotspot")
            return True
            
        except Exception as e:
            logger.warning(f"Lỗi tắt hotspot (có thể đã tắt): {e}")
            return True  # Không quan trọng nếu đã tắt
    
    def get_hotspot_ip(self) -> str:
        """Lấy IP của hotspot (gateway)"""
        return "192.168.4.1"
    
    def is_hotspot_active(self) -> bool:
        """Kiểm tra hotspot có đang chạy không"""
        try:
            result = self._run_nmcli(["-t", "-f", "NAME", "connection", "show", "--active"])
            
            if result.returncode == 0:
                active_connections = result.stdout.strip().split('\n')
                return self._hotspot_connection_name in active_connections
            
            return False
        except Exception:
            return False
    
    def disconnect_wifi(self) -> bool:
        """Ngắt kết nối WiFi hiện tại"""
        try:
            result = self._run_nmcli([
                "device", "disconnect", self._wifi_interface
            ])
            
            if result.returncode == 0:
                logger.info("Đã ngắt kết nối WiFi")
                self._notify_state_change(WiFiState.DISCONNECTED)
                return True
            
            return False
        except Exception as e:
            logger.error(f"Lỗi ngắt kết nối WiFi: {e}")
            return False
    
    def forget_network(self, ssid: str) -> bool:
        """Quên mạng WiFi đã lưu"""
        try:
            result = self._run_nmcli(["connection", "delete", ssid])
            
            if result.returncode == 0:
                logger.info(f"Đã quên mạng WiFi: {ssid}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Lỗi quên mạng WiFi: {e}")
            return False
    
    def get_saved_networks(self) -> List[str]:
        """Lấy danh sách mạng WiFi đã lưu"""
        try:
            result = self._run_nmcli([
                "-t", "-f", "NAME,TYPE",
                "connection", "show"
            ])
            
            if result.returncode == 0:
                networks = []
                for line in result.stdout.strip().split('\n'):
                    parts = line.split(':')
                    if len(parts) >= 2 and parts[1] == '802-11-wireless':
                        if parts[0] != self._hotspot_connection_name:
                            networks.append(parts[0])
                return networks
            
            return []
        except Exception as e:
            logger.error(f"Lỗi lấy danh sách mạng đã lưu: {e}")
            return []
    
    def get_ip_address(self) -> Optional[str]:
        """Lấy địa chỉ IP hiện tại"""
        try:
            result = subprocess.run(
                ["ip", "-4", "addr", "show", self._wifi_interface],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', result.stdout)
                if match:
                    return match.group(1)
            
            return None
        except Exception as e:
            logger.error(f"Lỗi lấy IP: {e}")
            return None
    
    def check_internet_connection(self) -> bool:
        """Kiểm tra có kết nối Internet không"""
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "3", "8.8.8.8"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    async def check_internet_connection_async(self) -> bool:
        """Kiểm tra Internet bất đồng bộ"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.check_internet_connection)


# Factory function
def get_wifi_manager() -> WiFiManager:
    """Lấy instance WiFiManager"""
    return WiFiManager.get_instance()
