#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WiFi Captive Portal Server - Web server phục vụ trang cấu hình WiFi.

Khi hotspot bật, server này cung cấp:
- Trang web để người dùng chọn và nhập WiFi
- API endpoint để nhận cấu hình WiFi
- Captive portal redirect cho các thiết bị kết nối
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Callable, Optional

from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# HTML Template cho trang cấu hình WiFi
WIFI_SETUP_HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart C - Cấu hình WiFi</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 20px;
            padding: 40px;
            max-width: 400px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        
        .logo {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .logo h1 {
            color: #667eea;
            font-size: 28px;
            margin-bottom: 5px;
        }
        
        .logo p {
            color: #666;
            font-size: 14px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 500;
        }
        
        select, input[type="password"], input[type="text"] {
            width: 100%;
            padding: 14px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        
        select:focus, input:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .wifi-list {
            max-height: 200px;
            overflow-y: auto;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        
        .wifi-item {
            padding: 12px 15px;
            border-bottom: 1px solid #f0f0f0;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: background 0.2s;
        }
        
        .wifi-item:hover {
            background: #f5f5f5;
        }
        
        .wifi-item.selected {
            background: #e8f0fe;
            border-left: 3px solid #667eea;
        }
        
        .wifi-item:last-child {
            border-bottom: none;
        }
        
        .wifi-name {
            font-weight: 500;
        }
        
        .wifi-signal {
            color: #666;
            font-size: 14px;
        }
        
        .signal-bars {
            display: inline-flex;
            align-items: flex-end;
            height: 16px;
            gap: 2px;
        }
        
        .signal-bar {
            width: 4px;
            background: #ccc;
            border-radius: 1px;
        }
        
        .signal-bar.active {
            background: #667eea;
        }
        
        .signal-bar:nth-child(1) { height: 4px; }
        .signal-bar:nth-child(2) { height: 8px; }
        .signal-bar:nth-child(3) { height: 12px; }
        .signal-bar:nth-child(4) { height: 16px; }
        
        .btn {
            width: 100%;
            padding: 16px;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
        }
        
        .btn-secondary {
            background: #f0f0f0;
            color: #333;
            margin-top: 10px;
        }
        
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        .status {
            text-align: center;
            padding: 15px;
            border-radius: 10px;
            margin-top: 20px;
            display: none;
        }
        
        .status.success {
            display: block;
            background: #d4edda;
            color: #155724;
        }
        
        .status.error {
            display: block;
            background: #f8d7da;
            color: #721c24;
        }
        
        .status.loading {
            display: block;
            background: #cce5ff;
            color: #004085;
        }
        
        .spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 2px solid #fff;
            border-top-color: transparent;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-right: 10px;
            vertical-align: middle;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .manual-input {
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #e0e0e0;
        }
        
        .toggle-manual {
            color: #667eea;
            cursor: pointer;
            font-size: 14px;
            text-align: center;
            display: block;
            margin-bottom: 15px;
        }
        
        .hidden {
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <h1>🤖 Smart C</h1>
            <p>Trợ lý AI thông minh</p>
        </div>
        
        <form id="wifiForm">
            <label>Chọn mạng WiFi:</label>
            <div class="wifi-list" id="wifiList">
                <div class="wifi-item" style="justify-content: center; color: #666;">
                    Đang quét mạng WiFi...
                </div>
            </div>
            
            <span class="toggle-manual" onclick="toggleManualInput()">
                Nhập tên WiFi thủ công ▼
            </span>
            
            <div id="manualInput" class="manual-input hidden">
                <div class="form-group">
                    <label for="ssid">Tên WiFi (SSID):</label>
                    <input type="text" id="ssid" name="ssid" placeholder="Nhập tên mạng WiFi">
                </div>
            </div>
            
            <div class="form-group">
                <label for="password">Mật khẩu WiFi:</label>
                <input type="password" id="password" name="password" placeholder="Nhập mật khẩu">
            </div>
            
            <button type="submit" class="btn btn-primary" id="connectBtn">
                Kết nối WiFi
            </button>
            
            <button type="button" class="btn btn-secondary" onclick="scanWifi()">
                🔄 Quét lại
            </button>
        </form>
        
        <div id="status" class="status"></div>
    </div>
    
    <script>
        let selectedSsid = '';
        
        function toggleManualInput() {
            const manualInput = document.getElementById('manualInput');
            manualInput.classList.toggle('hidden');
        }
        
        function createSignalBars(strength) {
            const bars = Math.ceil(strength / 25);
            let html = '<div class="signal-bars">';
            for (let i = 1; i <= 4; i++) {
                html += `<div class="signal-bar ${i <= bars ? 'active' : ''}"></div>`;
            }
            html += '</div>';
            return html;
        }
        
        function selectWifi(ssid, element) {
            selectedSsid = ssid;
            document.getElementById('ssid').value = ssid;
            
            // Remove selection from all items
            document.querySelectorAll('.wifi-item').forEach(item => {
                item.classList.remove('selected');
            });
            
            // Add selection to clicked item
            element.classList.add('selected');
        }
        
        async function scanWifi() {
            const wifiList = document.getElementById('wifiList');
            wifiList.innerHTML = '<div class="wifi-item" style="justify-content: center; color: #666;">Đang quét mạng WiFi...</div>';
            
            try {
                const response = await fetch('/api/wifi/scan');
                const networks = await response.json();
                
                if (networks.length === 0) {
                    wifiList.innerHTML = '<div class="wifi-item" style="justify-content: center; color: #666;">Không tìm thấy mạng WiFi</div>';
                    return;
                }
                
                wifiList.innerHTML = networks.map(net => `
                    <div class="wifi-item ${net.in_use ? 'selected' : ''}" 
                         onclick="selectWifi('${net.ssid.replace(/'/g, "\\'")}', this)">
                        <span class="wifi-name">${net.ssid} ${net.security !== 'open' ? '🔒' : ''}</span>
                        ${createSignalBars(net.signal_strength)}
                    </div>
                `).join('');
                
                // Auto-select first network if connected
                const connectedNet = networks.find(n => n.in_use);
                if (connectedNet) {
                    selectedSsid = connectedNet.ssid;
                    document.getElementById('ssid').value = connectedNet.ssid;
                }
                
            } catch (error) {
                wifiList.innerHTML = '<div class="wifi-item" style="justify-content: center; color: #c00;">Lỗi quét WiFi</div>';
            }
        }
        
        function showStatus(message, type) {
            const status = document.getElementById('status');
            status.className = 'status ' + type;
            status.innerHTML = type === 'loading' 
                ? '<span class="spinner"></span>' + message 
                : message;
        }
        
        document.getElementById('wifiForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const ssid = document.getElementById('ssid').value || selectedSsid;
            const password = document.getElementById('password').value;
            
            if (!ssid) {
                showStatus('Vui lòng chọn hoặc nhập tên mạng WiFi', 'error');
                return;
            }
            
            const connectBtn = document.getElementById('connectBtn');
            connectBtn.disabled = true;
            showStatus('Đang kết nối...', 'loading');
            
            try {
                const response = await fetch('/api/wifi/connect', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ ssid, password })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showStatus('✅ Kết nối thành công! Thiết bị sẽ khởi động lại...', 'success');
                    
                    // Redirect sau 3 giây
                    setTimeout(() => {
                        window.location.href = '/success';
                    }, 3000);
                } else {
                    showStatus('❌ ' + (result.error || 'Kết nối thất bại'), 'error');
                    connectBtn.disabled = false;
                }
                
            } catch (error) {
                showStatus('❌ Lỗi kết nối: ' + error.message, 'error');
                connectBtn.disabled = false;
            }
        });
        
        // Quét WiFi khi tải trang
        scanWifi();
    </script>
</body>
</html>
"""

WIFI_SUCCESS_HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart C - Kết nối thành công</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 0;
        }
        .container {
            background: white;
            border-radius: 20px;
            padding: 60px 40px;
            text-align: center;
            max-width: 400px;
        }
        .success-icon {
            font-size: 80px;
            margin-bottom: 20px;
        }
        h1 { color: #155724; margin-bottom: 15px; }
        p { color: #666; line-height: 1.6; }
    </style>
</head>
<body>
    <div class="container">
        <div class="success-icon">✅</div>
        <h1>Kết nối thành công!</h1>
        <p>Thiết bị Smart C đã kết nối WiFi thành công.</p>
        <p>Bạn có thể đóng trang này và sử dụng thiết bị.</p>
    </div>
</body>
</html>
"""


class CaptivePortalServer:
    """
    Web server phục vụ trang cấu hình WiFi.
    
    Sử dụng aiohttp để tạo web server async.
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 80):
        self.host = host
        self.port = port
        self._server = None
        self._site = None
        self._runner = None
        self._on_wifi_connect: Optional[Callable] = None
        self._wifi_manager = None
    
    def set_wifi_connect_callback(self, callback: Callable):
        """Đặt callback khi nhận yêu cầu kết nối WiFi"""
        self._on_wifi_connect = callback
    
    def set_wifi_manager(self, wifi_manager):
        """Đặt WiFi manager để quét và kết nối"""
        self._wifi_manager = wifi_manager
    
    async def start(self):
        """Khởi động web server"""
        try:
            from aiohttp import web
        except ImportError:
            logger.error("aiohttp chưa được cài đặt. Chạy: pip install aiohttp")
            return False
        
        try:
            app = web.Application()
            
            # Routes
            app.router.add_get('/', self._handle_index)
            app.router.add_get('/success', self._handle_success)
            app.router.add_get('/api/wifi/scan', self._handle_scan)
            app.router.add_post('/api/wifi/connect', self._handle_connect)
            
            # Captive portal routes (redirect tất cả về trang chính)
            app.router.add_get('/generate_204', self._handle_captive)  # Android
            app.router.add_get('/hotspot-detect.html', self._handle_captive)  # iOS
            app.router.add_get('/connecttest.txt', self._handle_captive)  # Windows
            app.router.add_get('/ncsi.txt', self._handle_captive)  # Windows
            
            self._runner = web.AppRunner(app)
            await self._runner.setup()
            
            self._site = web.TCPSite(self._runner, self.host, self.port)
            await self._site.start()
            
            logger.info(f"Captive Portal Server đang chạy tại http://{self.host}:{self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khởi động Captive Portal: {e}")
            return False
    
    async def stop(self):
        """Dừng web server"""
        try:
            if self._runner:
                await self._runner.cleanup()
                self._runner = None
                self._site = None
            logger.info("Captive Portal Server đã dừng")
        except Exception as e:
            logger.error(f"Lỗi dừng Captive Portal: {e}")
    
    async def _handle_index(self, request):
        """Trang chính - form cấu hình WiFi"""
        from aiohttp import web
        return web.Response(text=WIFI_SETUP_HTML, content_type='text/html')
    
    async def _handle_success(self, request):
        """Trang thành công"""
        from aiohttp import web
        return web.Response(text=WIFI_SUCCESS_HTML, content_type='text/html')
    
    async def _handle_captive(self, request):
        """Redirect captive portal về trang chính"""
        from aiohttp import web
        raise web.HTTPFound('/')
    
    async def _handle_scan(self, request):
        """API quét mạng WiFi"""
        from aiohttp import web
        
        try:
            if self._wifi_manager:
                networks = await self._wifi_manager.scan_wifi_networks_async()
                result = [
                    {
                        "ssid": net.ssid,
                        "signal_strength": net.signal_strength,
                        "security": net.security,
                        "in_use": net.in_use
                    }
                    for net in networks
                ]
                return web.json_response(result)
            else:
                return web.json_response([])
                
        except Exception as e:
            logger.error(f"Lỗi quét WiFi: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def _handle_connect(self, request):
        """API kết nối WiFi"""
        from aiohttp import web
        
        try:
            data = await request.json()
            ssid = data.get('ssid')
            password = data.get('password', '')
            
            if not ssid:
                return web.json_response(
                    {"success": False, "error": "Thiếu tên mạng WiFi"},
                    status=400
                )
            
            logger.info(f"Nhận yêu cầu kết nối WiFi: {ssid}")
            
            # Gọi callback nếu có
            if self._on_wifi_connect:
                success = await self._on_wifi_connect(ssid, password)
            elif self._wifi_manager:
                success = await self._wifi_manager.connect_to_wifi_async(ssid, password)
            else:
                success = False
            
            if success:
                return web.json_response({"success": True})
            else:
                return web.json_response(
                    {"success": False, "error": "Không thể kết nối WiFi"},
                    status=500
                )
                
        except Exception as e:
            logger.error(f"Lỗi xử lý kết nối WiFi: {e}")
            return web.json_response(
                {"success": False, "error": str(e)},
                status=500
            )


class WiFiSetupService:
    """
    Service tổng hợp cho việc cấu hình WiFi.
    
    Bao gồm:
    - Kiểm tra WiFi
    - Bật hotspot nếu chưa kết nối
    - Chạy captive portal
    - Chờ người dùng cấu hình
    """
    
    def __init__(self):
        self._wifi_manager = None
        self._portal_server = None
        self._setup_complete = asyncio.Event()
        self._setup_result = False
    
    async def run_wifi_setup(self) -> bool:
        """
        Chạy quy trình cấu hình WiFi.
        
        Returns:
            bool: True nếu WiFi đã được cấu hình thành công
        """
        from src.network.wifi_manager import get_wifi_manager
        
        self._wifi_manager = get_wifi_manager()
        
        # Kiểm tra đã có WiFi chưa
        if self._wifi_manager.check_wifi_connection():
            current_ssid = self._wifi_manager.get_current_ssid()
            logger.info(f"Đã kết nối WiFi: {current_ssid}")
            
            # Kiểm tra có Internet không
            if await self._wifi_manager.check_internet_connection_async():
                logger.info("Có kết nối Internet, bỏ qua WiFi setup")
                return True
            else:
                logger.warning("Đã kết nối WiFi nhưng không có Internet")
        
        logger.info("Chưa có kết nối WiFi, bắt đầu WiFi Setup...")
        
        # Bật hotspot
        if not self._wifi_manager.start_hotspot():
            logger.error("Không thể bật WiFi Hotspot")
            return False
        
        # Khởi động captive portal
        self._portal_server = CaptivePortalServer()
        self._portal_server.set_wifi_manager(self._wifi_manager)
        self._portal_server.set_wifi_connect_callback(self._on_wifi_connect)
        
        if not await self._portal_server.start():
            logger.error("Không thể khởi động Captive Portal")
            self._wifi_manager.stop_hotspot()
            return False
        
        logger.info("WiFi Setup đang chạy. Kết nối tới WiFi 'SmartC-Setup' để cấu hình.")
        
        # Chờ cho đến khi cấu hình hoàn tất
        try:
            await asyncio.wait_for(
                self._setup_complete.wait(),
                timeout=300  # 5 phút timeout
            )
        except asyncio.TimeoutError:
            logger.warning("WiFi Setup timeout")
            self._setup_result = False
        
        # Dọn dẹp
        await self._portal_server.stop()
        
        return self._setup_result
    
    async def _on_wifi_connect(self, ssid: str, password: str) -> bool:
        """Callback khi người dùng gửi yêu cầu kết nối WiFi"""
        logger.info(f"Đang kết nối tới WiFi: {ssid}")
        
        # Dừng hotspot trước
        self._wifi_manager.stop_hotspot()
        
        # Đợi một chút để hotspot tắt hoàn toàn
        await asyncio.sleep(2)
        
        # Kết nối WiFi
        success = await self._wifi_manager.connect_to_wifi_async(ssid, password)
        
        if success:
            # Đợi và kiểm tra Internet
            await asyncio.sleep(3)
            has_internet = await self._wifi_manager.check_internet_connection_async()
            
            if has_internet:
                logger.info("Kết nối WiFi và Internet thành công!")
            else:
                logger.warning("Kết nối WiFi nhưng không có Internet")
            
            # Update GUI với IP mới sau khi kết nối thành công
            await self._update_gui_with_new_ip()
            
            self._setup_result = True
            self._setup_complete.set()
            return True
        else:
            logger.error("Kết nối WiFi thất bại")
            # Bật lại hotspot để thử lại
            self._wifi_manager.start_hotspot()
            return False
    
    async def _update_gui_with_new_ip(self):
        """Update GUI với IP mới sau khi kết nối WiFi thành công và restart services"""
        try:
            from src.network.network_status import get_current_ip, generate_qr_code
            from src.utils.resource_finder import get_project_root
            from src.application import Application
            
            # Lấy IP mới
            ip = get_current_ip()
            if not ip:
                logger.warning("Không lấy được IP sau khi kết nối")
                return
            
            logger.info(f"IP mới sau kết nối: {ip}")
            
            # Tạo QR code cho URL settings
            qr_path = get_project_root() / "assets" / "qr_settings.png"
            url = f"http://{ip}:8080"
            if generate_qr_code(url, qr_path):
                qr_path_str = str(qr_path)
            else:
                qr_path_str = ""
            
            # Update GUI
            app = Application.get_instance()
            if app:
                await app._update_gui_network_info(ip, "connected", qr_path_str)
                logger.info(f"Đã update GUI với IP mới: {ip}")
                
                # Trigger WebSocket reconnect nếu chưa connected
                if not app.is_audio_channel_opened():
                    logger.info("Triggering WebSocket reconnect sau khi có mạng...")
                    app.spawn(app._auto_connect_protocol(), "post-wifi-connect")
                    
        except Exception as e:
            logger.error(f"Lỗi update GUI với IP mới: {e}")
    
    def cancel(self):
        """Hủy quá trình setup"""
        self._setup_result = False
        self._setup_complete.set()


# Factory function
async def run_wifi_setup() -> bool:
    """Chạy WiFi setup service"""
    service = WiFiSetupService()
    return await service.run_wifi_setup()
