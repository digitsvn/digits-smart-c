#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WiFi Setup Widget - UI component để cấu hình WiFi trong Settings.

Widget này hiển thị:
- Trạng thái kết nối WiFi hiện tại
- Danh sách mạng WiFi khả dụng
- Form nhập mật khẩu và kết nối
"""

import asyncio
from pathlib import Path
from typing import List, Optional

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class WiFiScanWorker(QThread):
    """Worker thread để quét WiFi không block UI"""
    
    scan_complete = pyqtSignal(list)
    scan_error = pyqtSignal(str)
    
    def __init__(self, wifi_manager):
        super().__init__()
        self._wifi_manager = wifi_manager
    
    def run(self):
        try:
            networks = self._wifi_manager.scan_wifi_networks()
            self.scan_complete.emit(networks)
        except Exception as e:
            self.scan_error.emit(str(e))


class WiFiConnectWorker(QThread):
    """Worker thread để kết nối WiFi"""
    
    connect_complete = pyqtSignal(bool, str)
    
    def __init__(self, wifi_manager, ssid: str, password: str):
        super().__init__()
        self._wifi_manager = wifi_manager
        self._ssid = ssid
        self._password = password
    
    def run(self):
        try:
            success = self._wifi_manager.connect_to_wifi(self._ssid, self._password)
            if success:
                self.connect_complete.emit(True, "Kết nối thành công!")
            else:
                self.connect_complete.emit(False, "Không thể kết nối. Kiểm tra lại mật khẩu.")
        except Exception as e:
            self.connect_complete.emit(False, str(e))


class WiFiSetupWidget(QWidget):
    """
    Widget cấu hình WiFi trong Settings.
    """
    
    # Signals
    settings_changed = pyqtSignal()
    wifi_connected = pyqtSignal(str)  # SSID
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger(__name__)
        
        # WiFi Manager
        self._wifi_manager = None
        self._init_wifi_manager()
        
        # Workers
        self._scan_worker = None
        self._connect_worker = None
        
        # Data
        self._networks = []
        self._selected_ssid = ""
        
        # Setup UI
        self._setup_ui()
        self._connect_events()
        
        # Initial scan
        self._refresh_status()
    
    def _init_wifi_manager(self):
        """Khởi tạo WiFi Manager"""
        try:
            from src.network.wifi_manager import get_wifi_manager
            self._wifi_manager = get_wifi_manager()
        except Exception as e:
            self.logger.error(f"Không thể khởi tạo WiFi Manager: {e}")
    
    def _setup_ui(self):
        """Thiết lập giao diện"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # === Trạng thái hiện tại ===
        status_group = QWidget()
        status_layout = QHBoxLayout(status_group)
        status_layout.setContentsMargins(0, 0, 0, 0)
        
        self._status_icon = QLabel("📶")
        self._status_icon.setStyleSheet("font-size: 24px;")
        status_layout.addWidget(self._status_icon)
        
        status_text_layout = QVBoxLayout()
        self._status_label = QLabel("Đang kiểm tra...")
        self._status_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        status_text_layout.addWidget(self._status_label)
        
        self._ip_label = QLabel("")
        self._ip_label.setStyleSheet("color: #666; font-size: 12px;")
        status_text_layout.addWidget(self._ip_label)
        
        status_layout.addLayout(status_text_layout)
        status_layout.addStretch()
        
        self._refresh_btn = QPushButton("🔄 Làm mới")
        self._refresh_btn.setFixedWidth(100)
        status_layout.addWidget(self._refresh_btn)
        
        layout.addWidget(status_group)
        
        # === Danh sách mạng WiFi ===
        wifi_label = QLabel("Mạng WiFi khả dụng:")
        wifi_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(wifi_label)
        
        self._wifi_list = QListWidget()
        self._wifi_list.setMinimumHeight(150)
        self._wifi_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ccc;
                border-radius: 5px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: black;
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)
        layout.addWidget(self._wifi_list)
        
        # Loading indicator
        self._progress_bar = QProgressBar()
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setMaximum(0)  # Indeterminate
        self._progress_bar.setVisible(False)
        self._progress_bar.setFixedHeight(3)
        layout.addWidget(self._progress_bar)
        
        # === Form kết nối ===
        connect_group = QWidget()
        connect_layout = QVBoxLayout(connect_group)
        connect_layout.setContentsMargins(0, 0, 0, 0)
        
        # SSID (hiển thị hoặc nhập thủ công)
        ssid_layout = QHBoxLayout()
        ssid_layout.addWidget(QLabel("Mạng WiFi:"))
        self._ssid_combo = QComboBox()
        self._ssid_combo.setEditable(True)
        self._ssid_combo.setMinimumWidth(200)
        ssid_layout.addWidget(self._ssid_combo, 1)
        connect_layout.addLayout(ssid_layout)
        
        # Password
        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel("Mật khẩu:"))
        self._password_input = QLineEdit()
        self._password_input.setEchoMode(QLineEdit.Password)
        self._password_input.setPlaceholderText("Nhập mật khẩu WiFi")
        password_layout.addWidget(self._password_input, 1)
        
        self._show_password_btn = QPushButton("👁")
        self._show_password_btn.setFixedWidth(40)
        self._show_password_btn.setCheckable(True)
        password_layout.addWidget(self._show_password_btn)
        connect_layout.addLayout(password_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self._disconnect_btn = QPushButton("Ngắt kết nối")
        self._disconnect_btn.setVisible(False)
        button_layout.addWidget(self._disconnect_btn)
        
        self._connect_btn = QPushButton("🔗 Kết nối")
        self._connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        button_layout.addWidget(self._connect_btn)
        connect_layout.addLayout(button_layout)
        
        layout.addWidget(connect_group)
        
        # === Hotspot mode ===
        hotspot_group = QWidget()
        hotspot_layout = QHBoxLayout(hotspot_group)
        hotspot_layout.setContentsMargins(0, 10, 0, 0)
        
        hotspot_label = QLabel("🌐 Chế độ Hotspot (cho phép cấu hình từ điện thoại):")
        hotspot_layout.addWidget(hotspot_label)
        hotspot_layout.addStretch()
        
        self._hotspot_btn = QPushButton("Bật Hotspot")
        self._hotspot_btn.setCheckable(True)
        hotspot_layout.addWidget(self._hotspot_btn)
        
        layout.addWidget(hotspot_group)
        
        # Hotspot info
        self._hotspot_info = QLabel("")
        self._hotspot_info.setStyleSheet("color: #1976D2; padding: 10px; background: #E3F2FD; border-radius: 5px;")
        self._hotspot_info.setVisible(False)
        self._hotspot_info.setWordWrap(True)
        layout.addWidget(self._hotspot_info)
        
        layout.addStretch()
    
    def _connect_events(self):
        """Kết nối các sự kiện"""
        self._refresh_btn.clicked.connect(self._refresh_status)
        self._wifi_list.itemClicked.connect(self._on_wifi_selected)
        self._connect_btn.clicked.connect(self._on_connect_clicked)
        self._disconnect_btn.clicked.connect(self._on_disconnect_clicked)
        self._show_password_btn.toggled.connect(self._toggle_password_visibility)
        self._hotspot_btn.toggled.connect(self._on_hotspot_toggled)
        self._ssid_combo.currentTextChanged.connect(self._on_ssid_changed)
    
    def _refresh_status(self):
        """Làm mới trạng thái và quét WiFi"""
        if not self._wifi_manager:
            self._status_label.setText("WiFi Manager không khả dụng")
            self._status_icon.setText("❌")
            return
        
        # Cập nhật trạng thái
        is_connected = self._wifi_manager.check_wifi_connection()
        
        if is_connected:
            current_ssid = self._wifi_manager.get_current_ssid()
            ip = self._wifi_manager.get_ip_address()
            
            self._status_label.setText(f"Đã kết nối: {current_ssid}")
            self._ip_label.setText(f"IP: {ip}" if ip else "")
            self._status_icon.setText("✅")
            self._disconnect_btn.setVisible(True)
        else:
            if self._wifi_manager.is_hotspot_active():
                self._status_label.setText("Đang chạy Hotspot")
                self._ip_label.setText(f"IP: {self._wifi_manager.get_hotspot_ip()}")
                self._status_icon.setText("📡")
                self._hotspot_btn.setChecked(True)
            else:
                self._status_label.setText("Chưa kết nối WiFi")
                self._ip_label.setText("")
                self._status_icon.setText("📶")
            self._disconnect_btn.setVisible(False)
        
        # Quét mạng WiFi
        self._scan_wifi()
    
    def _scan_wifi(self):
        """Quét danh sách mạng WiFi"""
        if not self._wifi_manager:
            return
        
        if self._scan_worker and self._scan_worker.isRunning():
            return
        
        self._progress_bar.setVisible(True)
        self._wifi_list.clear()
        self._wifi_list.addItem("Đang quét...")
        
        self._scan_worker = WiFiScanWorker(self._wifi_manager)
        self._scan_worker.scan_complete.connect(self._on_scan_complete)
        self._scan_worker.scan_error.connect(self._on_scan_error)
        self._scan_worker.start()
    
    def _on_scan_complete(self, networks):
        """Callback khi quét xong"""
        self._progress_bar.setVisible(False)
        self._networks = networks
        
        self._wifi_list.clear()
        self._ssid_combo.clear()
        
        if not networks:
            self._wifi_list.addItem("Không tìm thấy mạng WiFi")
            return
        
        for net in networks:
            # Signal bars
            bars = "█" * net.signal_bars + "░" * (4 - net.signal_bars)
            
            # Security icon
            lock = "🔒" if net.security != "open" else "🔓"
            
            # In use marker
            connected = " ✓" if net.in_use else ""
            
            item_text = f"{net.ssid} {lock} {bars}{connected}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, net.ssid)
            
            if net.in_use:
                item.setBackground(Qt.lightGray)
            
            self._wifi_list.addItem(item)
            self._ssid_combo.addItem(net.ssid)
    
    def _on_scan_error(self, error):
        """Callback khi quét lỗi"""
        self._progress_bar.setVisible(False)
        self._wifi_list.clear()
        self._wifi_list.addItem(f"Lỗi quét: {error}")
    
    def _on_wifi_selected(self, item):
        """Callback khi chọn mạng WiFi"""
        ssid = item.data(Qt.UserRole)
        if ssid:
            self._selected_ssid = ssid
            self._ssid_combo.setCurrentText(ssid)
            self._password_input.setFocus()
    
    def _on_ssid_changed(self, ssid):
        """Callback khi SSID thay đổi"""
        self._selected_ssid = ssid
    
    def _on_connect_clicked(self):
        """Xử lý click nút kết nối"""
        ssid = self._ssid_combo.currentText().strip()
        password = self._password_input.text()
        
        if not ssid:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn hoặc nhập tên mạng WiFi")
            return
        
        self._connect_btn.setEnabled(False)
        self._connect_btn.setText("Đang kết nối...")
        self._progress_bar.setVisible(True)
        
        # Tắt hotspot nếu đang bật
        if self._wifi_manager.is_hotspot_active():
            self._wifi_manager.stop_hotspot()
            self._hotspot_btn.setChecked(False)
        
        self._connect_worker = WiFiConnectWorker(self._wifi_manager, ssid, password)
        self._connect_worker.connect_complete.connect(self._on_connect_complete)
        self._connect_worker.start()
    
    def _on_connect_complete(self, success, message):
        """Callback khi kết nối xong"""
        self._connect_btn.setEnabled(True)
        self._connect_btn.setText("🔗 Kết nối")
        self._progress_bar.setVisible(False)
        
        if success:
            QMessageBox.information(self, "Thành công", message)
            self._refresh_status()
            self.wifi_connected.emit(self._selected_ssid)
            self.settings_changed.emit()
        else:
            QMessageBox.warning(self, "Lỗi", message)
    
    def _on_disconnect_clicked(self):
        """Ngắt kết nối WiFi hiện tại"""
        if self._wifi_manager:
            self._wifi_manager.disconnect_wifi()
            self._refresh_status()
    
    def _toggle_password_visibility(self, checked):
        """Ẩn/hiện mật khẩu"""
        if checked:
            self._password_input.setEchoMode(QLineEdit.Normal)
            self._show_password_btn.setText("🙈")
        else:
            self._password_input.setEchoMode(QLineEdit.Password)
            self._show_password_btn.setText("👁")
    
    def _on_hotspot_toggled(self, checked):
        """Bật/tắt hotspot"""
        if not self._wifi_manager:
            return
        
        if checked:
            success = self._wifi_manager.start_hotspot()
            if success:
                self._hotspot_info.setText(
                    "📱 Hotspot đang chạy!\n"
                    f"Tên WiFi: {self._wifi_manager.DEFAULT_HOTSPOT_SSID}\n"
                    f"Mật khẩu: {self._wifi_manager.DEFAULT_HOTSPOT_PASSWORD}\n"
                    f"Mở trình duyệt tới http://{self._wifi_manager.get_hotspot_ip()} để cấu hình"
                )
                self._hotspot_info.setVisible(True)
            else:
                QMessageBox.warning(self, "Lỗi", "Không thể bật Hotspot")
                self._hotspot_btn.setChecked(False)
        else:
            self._wifi_manager.stop_hotspot()
            self._hotspot_info.setVisible(False)
        
        self._refresh_status()
    
    def get_config_data(self):
        """Trả về dữ liệu cấu hình (để tích hợp với Settings)"""
        return {
            "current_ssid": self._wifi_manager.get_current_ssid() if self._wifi_manager else None,
            "is_connected": self._wifi_manager.check_wifi_connection() if self._wifi_manager else False,
        }
    
    def reset_to_defaults(self):
        """Reset về mặc định"""
        self._password_input.clear()
        self._refresh_status()
