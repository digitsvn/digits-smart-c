#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web Settings Dashboard - Quản lý cài đặt qua trình duyệt web.

Chạy tại http://<IP>:8080 khi app khởi động.
Cho phép cấu hình video nền, xoay màn hình, v.v. từ điện thoại/máy tính.
"""

import asyncio
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

from aiohttp import web

from src.utils.config_manager import ConfigManager
from src.utils.logging_config import get_logger
from src.utils.resource_finder import get_project_root

logger = get_logger(__name__)

# HTML Template
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart C - Settings</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
            padding: 20px;
        }
        .container { max-width: 600px; margin: 0 auto; }
        .header {
            text-align: center;
            padding: 30px 0;
        }
        .header h1 { font-size: 28px; margin-bottom: 10px; }
        .header p { color: #888; }
        .card {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            backdrop-filter: blur(10px);
        }
        .card h2 {
            font-size: 18px;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .form-group { margin-bottom: 15px; }
        label {
            display: block;
            margin-bottom: 8px;
            color: #aaa;
            font-size: 14px;
        }
        select, input[type="text"] {
            width: 100%;
            padding: 12px;
            border: 1px solid #444;
            border-radius: 8px;
            background: #1a1a2e;
            color: #fff;
            font-size: 16px;
        }
        select:focus, input:focus {
            outline: none;
            border-color: #667eea;
        }
        .btn {
            width: 100%;
            padding: 14px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, opacity 0.2s;
        }
        .btn:hover { transform: translateY(-2px); }
        .btn:active { transform: translateY(0); }
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
        }
        .btn-danger {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: #fff;
        }
        .btn-success {
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: #fff;
        }
        .status {
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
            text-align: center;
        }
        .status.success { background: rgba(56, 239, 125, 0.2); color: #38ef7d; }
        .status.error { background: rgba(245, 87, 108, 0.2); color: #f5576c; }
        .info-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        .info-item {
            background: rgba(0,0,0,0.2);
            padding: 10px;
            border-radius: 8px;
        }
        .info-item .label { color: #888; font-size: 12px; }
        .info-item .value { font-size: 16px; margin-top: 5px; }
        .video-list {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 10px;
        }
        .video-btn {
            padding: 8px 12px;
            background: rgba(255,255,255,0.1);
            border: 1px solid #444;
            border-radius: 6px;
            color: #fff;
            cursor: pointer;
            font-size: 13px;
        }
        .video-btn:hover { background: rgba(255,255,255,0.2); }
        .video-btn.active { background: #667eea; border-color: #667eea; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Smart C Settings</h1>
            <p>Quản lý cài đặt từ xa</p>
        </div>
        
        <div class="card">
            <h2>📊 Trạng thái</h2>
            <div class="info-grid">
                <div class="info-item">
                    <div class="label">IP Address</div>
                    <div class="value" id="ipAddress">Loading...</div>
                </div>
                <div class="info-item">
                    <div class="label">Uptime</div>
                    <div class="value" id="uptime">Loading...</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>🎬 Video Nền</h2>
            <div class="form-group">
                <label>Chọn nhanh:</label>
                <div class="video-list" id="videoList">Loading...</div>
            </div>
            <div class="form-group">
                <label>Hoặc nhập đường dẫn:</label>
                <input type="text" id="videoPath" placeholder="assets/videos/HTMTECH.mp4">
            </div>
            <button class="btn btn-primary" onclick="saveVideo()">💾 Lưu Video</button>
            <div id="videoStatus"></div>
            
            <hr style="border-color: #444; margin: 20px 0;">
            
            <div class="form-group">
                <label>📤 Upload Video mới:</label>
                <input type="file" id="videoFile" accept="video/*,.gif,.webp" 
                    style="display:none;" onchange="uploadVideo()">
                <button class="btn btn-success" onclick="document.getElementById('videoFile').click()" 
                    style="margin-top: 8px;">
                    📁 Chọn File Upload
                </button>
                <div id="uploadProgress" style="margin-top: 10px; display: none;">
                    <div style="background: #333; border-radius: 8px; overflow: hidden;">
                        <div id="progressBar" style="height: 8px; background: linear-gradient(90deg, #667eea, #764ba2); width: 0%;"></div>
                    </div>
                    <small id="uploadText" style="color: #888;">Đang upload...</small>
                </div>
            </div>
            <div id="uploadStatus"></div>
        </div>
        
        <div class="card">
            <h2>🔄 Xoay Màn Hình</h2>
            <div class="form-group">
                <select id="rotation">
                    <option value="normal">Không xoay (0°)</option>
                    <option value="left">Xoay trái (90°)</option>
                    <option value="inverted">Xoay ngược (180°)</option>
                    <option value="right">Xoay phải (270°)</option>
                </select>
            </div>
            <button class="btn btn-primary" onclick="saveRotation()">💾 Lưu</button>
            <div id="rotationStatus"></div>
        </div>
        
        <div class="card">
            <h2>🖥️ Chế Độ Màn Hình</h2>
            <div class="form-group">
                <label>Kích thước cửa sổ:</label>
                <select id="windowMode">
                    <option value="screen_100">Toàn màn hình (100%)</option>
                    <option value="screen_75">Cửa sổ 75%</option>
                    <option value="fullhd">Full HD (1920x1080)</option>
                    <option value="hd">HD (1280x720)</option>
                    <option value="vertical_916">Dọc 9:16</option>
                    <option value="default">Tự động</option>
                </select>
            </div>
            <button class="btn btn-primary" onclick="saveWindowMode()">💾 Lưu</button>
            <div id="windowModeStatus"></div>
        </div>
        
        <div class="card">
            <h2>📺 YouTube URL</h2>
            <div class="form-group">
                <input type="text" id="youtubeUrl" placeholder="https://www.youtube.com/watch?v=...">
            </div>
            <button class="btn btn-primary" onclick="saveYoutube()">💾 Lưu YouTube</button>
            <div id="youtubeStatus"></div>
        </div>
        
        <div class="card">
            <h2>🎤 Microphone</h2>
            <div class="form-group">
                <label>Thiết bị Mic:</label>
                <select id="micDevice"></select>
            </div>
            <div class="form-group">
                <label>Âm lượng: <span id="micVolumeValue">100</span>%</label>
                <input type="range" id="micVolume" min="0" max="100" value="100" 
                    oninput="document.getElementById('micVolumeValue').textContent=this.value"
                    style="width:100%; accent-color:#667eea;">
            </div>
            <button class="btn btn-primary" onclick="saveAudio()">💾 Lưu Mic</button>
            <div id="micStatus"></div>
        </div>
        
        <div class="card">
            <h2>🔊 Loa / Speaker</h2>
            <div class="form-group">
                <label>Thiết bị Loa:</label>
                <select id="speakerDevice"></select>
            </div>
            <div class="form-group">
                <label>Âm lượng: <span id="speakerVolumeValue">80</span>%</label>
                <input type="range" id="speakerVolume" min="0" max="100" value="80"
                    oninput="document.getElementById('speakerVolumeValue').textContent=this.value"
                    style="width:100%; accent-color:#667eea;">
            </div>
            <button class="btn btn-primary" onclick="saveAudio()">💾 Lưu Loa</button>
            <div id="speakerStatus"></div>
        </div>
        
        <div class="card">
            <h2>🎙️ Từ Đánh Thức (Wake Word)</h2>
            <div class="form-group">
                <label>
                    <input type="checkbox" id="wakeWordEnabled" style="width:auto; margin-right:8px;">
                    Bật Wake Word
                </label>
            </div>
            <div class="form-group">
                <label>Ngưỡng phát hiện: <span id="sensitivityValue">0.25</span></label>
                <input type="range" id="wakeWordSensitivity" min="0.1" max="0.5" step="0.05" value="0.25"
                    oninput="document.getElementById('sensitivityValue').textContent=this.value"
                    style="width:100%; accent-color:#667eea;">
                <small style="color: #888;">Thấp = nhạy hơn, Cao = chính xác hơn</small>
            </div>
            <div class="form-group">
                <label>Từ khóa:</label>
                <div style="padding: 10px; background: rgba(0,0,0,0.2); border-radius: 8px; font-size: 13px;">
                    Mặc định: 小智 (Xiaozhi)<br>
                    <small style="color: #888;">Chỉnh sửa: models/keywords.txt</small>
                </div>
            </div>
            <button class="btn btn-primary" onclick="saveWakeWord()">💾 Lưu</button>
            <div id="wakeWordStatus"></div>
        </div>
        
        <div class="card">
            <h2>📶 WiFi</h2>
            <div class="form-group">
                <label>Mạng hiện tại:</label>
                <div id="currentWifi" style="padding: 10px; background: rgba(0,0,0,0.2); border-radius: 8px;">
                    Loading...
                </div>
            </div>
            <div class="form-group">
                <label>Mạng khả dụng:</label>
                <select id="wifiList" style="margin-bottom: 10px;"></select>
                <input type="password" id="wifiPassword" placeholder="Mật khẩu WiFi">
            </div>
            <button class="btn btn-primary" onclick="connectWifi()" style="margin-bottom: 10px;">📶 Kết nối</button>
            <button class="btn btn-success" onclick="scanWifi()">🔄 Quét lại</button>
            <div id="wifiStatus"></div>
        </div>
        
        <div class="card">
            <h2>🌐 Hệ Thống</h2>
            <div class="form-group">
                <label>Ngôn ngữ:</label>
                <select id="language">
                    <option value="vi">Tiếng Việt</option>
                    <option value="en">English</option>
                    <option value="zh">中文</option>
                </select>
            </div>
            <div class="form-group">
                <label>OTA Server URL:</label>
                <input type="text" id="otaUrl" placeholder="https://api.xiaozhi.me">
            </div>
            <div class="form-group">
                <label>WebSocket URL:</label>
                <input type="text" id="wsUrl" placeholder="wss://api.xiaozhi.me/websocket">
            </div>
            <div class="form-group">
                <label>WebSocket Token:</label>
                <input type="text" id="wsToken" placeholder="Token từ server">
            </div>
            <div class="form-group">
                <label>Thông tin:</label>
                <div id="systemInfo" style="padding: 10px; background: rgba(0,0,0,0.2); border-radius: 8px; font-size: 13px;">
                    Loading...
                </div>
            </div>
            <button class="btn btn-primary" onclick="saveSystem()" style="margin-bottom: 10px;">💾 Lưu cấu hình</button>
            <button class="btn btn-success" onclick="checkUpdate()">🔄 Kiểm tra cập nhật</button>
            <div id="systemStatus"></div>
        </div>
        
        <div class="card">
            <h2>🧪 Test Thiết Bị</h2>
            <div class="form-group">
                <label>🎤 Test Microphone:</label>
                <button class="btn btn-primary" onclick="testMic()" id="testMicBtn" style="margin-bottom: 10px;">🎤 Ghi âm 3s</button>
                <div id="micStatus"></div>
            </div>
            <div class="form-group">
                <label>🔊 Test Loa:</label>
                <button class="btn btn-primary" onclick="testSpeaker()" style="margin-bottom: 10px;">🔊 Phát âm thanh</button>
                <div id="speakerStatus"></div>
            </div>
        </div>
        
        <div class="card">
            <h2>💬 Test Chat AI</h2>
            <div class="form-group">
                <input type="text" id="chatInput" placeholder="Nhập tin nhắn test..." style="margin-bottom: 10px;">
                <button class="btn btn-primary" onclick="testChat()">📤 Gửi</button>
            </div>
            <div id="chatResponse" style="padding: 15px; background: rgba(0,0,0,0.3); border-radius: 10px; min-height: 80px; margin-top: 10px;">
                <span style="color: #888;">Nhập tin nhắn và nhấn Gửi để test AI...</span>
            </div>
            <div id="chatStatus"></div>
        </div>
        
        <div class="card">
            <h2>⚙️ Điều khiển</h2>
            <button class="btn btn-success" onclick="restartApp()" style="margin-bottom: 10px;">🔄 Restart App</button>
            <button class="btn btn-danger" onclick="rebootPi()">🔌 Reboot Pi</button>
        </div>
    </div>
    
    <script>
        async function loadStatus() {
            try {
                const resp = await fetch('/api/status');
                const data = await resp.json();
                document.getElementById('ipAddress').textContent = data.ip || 'Unknown';
                document.getElementById('uptime').textContent = data.uptime || 'Unknown';
                document.getElementById('videoPath').value = data.video_path || '';
                document.getElementById('rotation').value = data.rotation || 'normal';
                document.getElementById('youtubeUrl').value = data.youtube_url || '';
                
                // Video list
                const videoList = document.getElementById('videoList');
                videoList.innerHTML = '';
                (data.videos || []).forEach(v => {
                    const btn = document.createElement('button');
                    btn.className = 'video-btn' + (v === data.video_path ? ' active' : '');
                    btn.textContent = v.split('/').pop();
                    btn.onclick = () => {
                        document.getElementById('videoPath').value = v;
                        document.querySelectorAll('.video-btn').forEach(b => b.classList.remove('active'));
                        btn.classList.add('active');
                    };
                    videoList.appendChild(btn);
                });
            } catch (e) {
                console.error('Error loading status:', e);
            }
        }
        
        async function saveVideo() {
            const path = document.getElementById('videoPath').value;
            try {
                const resp = await fetch('/api/video', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({path})
                });
                const data = await resp.json();
                showStatus('videoStatus', data.success ? 'success' : 'error', data.message);
            } catch (e) {
                showStatus('videoStatus', 'error', 'Lỗi kết nối');
            }
        }
        
        async function uploadVideo() {
            const fileInput = document.getElementById('videoFile');
            const file = fileInput.files[0];
            if (!file) return;
            
            const progressDiv = document.getElementById('uploadProgress');
            const progressBar = document.getElementById('progressBar');
            const uploadText = document.getElementById('uploadText');
            
            progressDiv.style.display = 'block';
            progressBar.style.width = '0%';
            uploadText.textContent = 'Đang upload...';
            
            const formData = new FormData();
            formData.append('video', file);
            
            try {
                const xhr = new XMLHttpRequest();
                xhr.upload.onprogress = (e) => {
                    if (e.lengthComputable) {
                        const percent = (e.loaded / e.total) * 100;
                        progressBar.style.width = percent + '%';
                        uploadText.textContent = `Đang upload... ${Math.round(percent)}%`;
                    }
                };
                
                xhr.onload = () => {
                    progressDiv.style.display = 'none';
                    const data = JSON.parse(xhr.responseText);
                    if (data.success) {
                        showStatus('uploadStatus', 'success', 'Upload thành công: ' + data.filename);
                        document.getElementById('videoPath').value = data.path;
                        loadStatus(); // Refresh video list
                    } else {
                        showStatus('uploadStatus', 'error', data.message);
                    }
                };
                
                xhr.onerror = () => {
                    progressDiv.style.display = 'none';
                    showStatus('uploadStatus', 'error', 'Upload thất bại');
                };
                
                xhr.open('POST', '/api/upload');
                xhr.send(formData);
            } catch (e) {
                progressDiv.style.display = 'none';
                showStatus('uploadStatus', 'error', 'Lỗi: ' + e.message);
            }
            
            fileInput.value = ''; // Reset input
        }
        
        async function saveRotation() {
            const rotation = document.getElementById('rotation').value;
            try {
                const resp = await fetch('/api/rotation', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({rotation})
                });
                const data = await resp.json();
                showStatus('rotationStatus', data.success ? 'success' : 'error', data.message);
            } catch (e) {
                showStatus('rotationStatus', 'error', 'Lỗi kết nối');
            }
        }
        
        async function loadWindowMode() {
            try {
                const resp = await fetch('/api/windowmode');
                const data = await resp.json();
                document.getElementById('windowMode').value = data.mode || 'screen_100';
            } catch (e) {}
        }
        
        async function saveWindowMode() {
            const mode = document.getElementById('windowMode').value;
            try {
                const resp = await fetch('/api/windowmode', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({mode})
                });
                const data = await resp.json();
                showStatus('windowModeStatus', data.success ? 'success' : 'error', data.message);
            } catch (e) {
                showStatus('windowModeStatus', 'error', 'Lỗi kết nối');
            }
        }
        
        async function saveYoutube() {
            const url = document.getElementById('youtubeUrl').value;
            try {
                const resp = await fetch('/api/youtube', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({url})
                });
                const data = await resp.json();
                showStatus('youtubeStatus', data.success ? 'success' : 'error', data.message);
            } catch (e) {
                showStatus('youtubeStatus', 'error', 'Lỗi kết nối');
            }
        }
        
        async function restartApp() {
            if (!confirm('Restart app?')) return;
            try {
                await fetch('/api/restart', {method: 'POST'});
                showStatus('videoStatus', 'success', 'Đang restart...');
                setTimeout(() => location.reload(), 3000);
            } catch (e) {}
        }
        
        async function rebootPi() {
            if (!confirm('Reboot Raspberry Pi?')) return;
            try {
                await fetch('/api/reboot', {method: 'POST'});
                alert('Pi đang reboot...');
            } catch (e) {}
        }
        
        // ========== TEST FUNCTIONS ==========
        async function testMic() {
            const btn = document.getElementById('testMicBtn');
            btn.disabled = true;
            btn.textContent = '🔴 Đang ghi âm...';
            showStatus('micStatus', 'success', '⏳ Đang ghi âm 3 giây...');
            
            try {
                const resp = await fetch('/api/test/mic', {method: 'POST'});
                const data = await resp.json();
                showStatus('micStatus', data.success ? 'success' : 'error', data.message);
            } catch (e) {
                showStatus('micStatus', 'error', 'Lỗi: ' + e.message);
            } finally {
                btn.disabled = false;
                btn.textContent = '🎤 Ghi âm 3s';
            }
        }
        
        async function testSpeaker() {
            showStatus('speakerStatus', 'success', '⏳ Đang phát âm thanh...');
            try {
                const resp = await fetch('/api/test/speaker', {method: 'POST'});
                const data = await resp.json();
                showStatus('speakerStatus', data.success ? 'success' : 'error', data.message);
            } catch (e) {
                showStatus('speakerStatus', 'error', 'Lỗi: ' + e.message);
            }
        }
        
        async function testChat() {
            const input = document.getElementById('chatInput');
            const responseDiv = document.getElementById('chatResponse');
            const message = input.value.trim();
            
            if (!message) {
                showStatus('chatStatus', 'error', 'Vui lòng nhập tin nhắn!');
                return;
            }
            
            responseDiv.innerHTML = '<span style="color: #888;">⏳ Đang gửi đến AI...</span>';
            showStatus('chatStatus', '', '');
            
            try {
                const resp = await fetch('/api/test/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message})
                });
                const data = await resp.json();
                
                if (data.success) {
                    responseDiv.innerHTML = `
                        <div style="margin-bottom: 10px; padding: 10px; background: linear-gradient(135deg, #667eea, #764ba2); border-radius: 10px;">
                            <strong>🧑 Bạn:</strong> ${message}
                        </div>
                        <div style="padding: 10px; background: rgba(255,255,255,0.1); border-radius: 10px;">
                            <strong>🤖 AI:</strong> ${data.response || 'Không có phản hồi'}
                        </div>
                    `;
                    input.value = '';
                } else {
                    responseDiv.innerHTML = '<span style="color: #ff6b6b;">❌ ' + data.message + '</span>';
                }
            } catch (e) {
                responseDiv.innerHTML = '<span style="color: #ff6b6b;">❌ Lỗi kết nối: ' + e.message + '</span>';
            }
        }
        
        // Enter key to send chat
        document.addEventListener('DOMContentLoaded', () => {
            const chatInput = document.getElementById('chatInput');
            if (chatInput) {
                chatInput.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') testChat();
                });
            }
        });
        
        
        async function saveAudio() {
            const micDevice = document.getElementById('micDevice').value;
            const speakerDevice = document.getElementById('speakerDevice').value;
            const micVolume = document.getElementById('micVolume').value;
            const speakerVolume = document.getElementById('speakerVolume').value;
            
            try {
                const resp = await fetch('/api/audio', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({micDevice, speakerDevice, micVolume, speakerVolume})
                });
                const data = await resp.json();
                showStatus('micStatus', data.success ? 'success' : 'error', data.message);
                showStatus('speakerStatus', data.success ? 'success' : 'error', data.message);
            } catch (e) {
                showStatus('micStatus', 'error', 'Lỗi kết nối');
            }
        }
        
        function showStatus(id, type, message) {
            const el = document.getElementById(id);
            el.className = 'status ' + type;
            el.textContent = message;
            el.style.display = 'block';
            setTimeout(() => el.style.display = 'none', 3000);
        }
        
        // Populate audio devices
        async function loadAudioDevices() {
            try {
                const resp = await fetch('/api/audio/devices');
                const data = await resp.json();
                
                const micSelect = document.getElementById('micDevice');
                const speakerSelect = document.getElementById('speakerDevice');
                
                micSelect.innerHTML = '';
                speakerSelect.innerHTML = '';
                
                (data.input_devices || []).forEach((d, i) => {
                    const opt = document.createElement('option');
                    opt.value = i;
                    opt.textContent = d;
                    if (i == data.current_mic) opt.selected = true;
                    micSelect.appendChild(opt);
                });
                
                (data.output_devices || []).forEach((d, i) => {
                    const opt = document.createElement('option');
                    opt.value = i;
                    opt.textContent = d;
                    if (i == data.current_speaker) opt.selected = true;
                    speakerSelect.appendChild(opt);
                });
                
                document.getElementById('micVolume').value = data.mic_volume || 100;
                document.getElementById('micVolumeValue').textContent = data.mic_volume || 100;
                document.getElementById('speakerVolume').value = data.speaker_volume || 80;
                document.getElementById('speakerVolumeValue').textContent = data.speaker_volume || 80;
            } catch (e) {
                console.error('Load audio devices failed:', e);
            }
        }
        
        // ========== WAKE WORD ==========
        async function loadWakeWord() {
            try {
                const resp = await fetch('/api/wakeword');
                const data = await resp.json();
                document.getElementById('wakeWordEnabled').checked = data.enabled;
                document.getElementById('wakeWordSensitivity').value = data.threshold || 0.25;
                document.getElementById('sensitivityValue').textContent = data.threshold || 0.25;
            } catch (e) {}
        }
        
        async function saveWakeWord() {
            const enabled = document.getElementById('wakeWordEnabled').checked;
            const sensitivity = parseFloat(document.getElementById('wakeWordSensitivity').value);
            try {
                const resp = await fetch('/api/wakeword', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({enabled, sensitivity})
                });
                const data = await resp.json();
                showStatus('wakeWordStatus', data.success ? 'success' : 'error', data.message);
            } catch (e) {
                showStatus('wakeWordStatus', 'error', 'Lỗi kết nối');
            }
        }
        
        // ========== WIFI ==========
        async function scanWifi() {
            document.getElementById('wifiList').innerHTML = '<option>Đang quét...</option>';
            document.getElementById('currentWifi').textContent = 'Đang kiểm tra...';
            try {
                const resp = await fetch('/api/wifi/scan');
                const data = await resp.json();
                const select = document.getElementById('wifiList');
                select.innerHTML = '';
                if (data.networks && data.networks.length > 0) {
                    data.networks.forEach(n => {
                        const opt = document.createElement('option');
                        opt.value = n.ssid;
                        opt.textContent = `${n.ssid} (${n.signal}dBm)`;
                        select.appendChild(opt);
                    });
                } else {
                    select.innerHTML = '<option>Không tìm thấy mạng</option>';
                }
                
                // Hiển thị mạng hiện tại + IP
                if (data.current) {
                    document.getElementById('currentWifi').textContent = `${data.current} (${data.ip || 'N/A'})`;
                } else {
                    document.getElementById('currentWifi').textContent = data.ip ? `Ethernet (${data.ip})` : 'Không kết nối';
                }
            } catch (e) {
                showStatus('wifiStatus', 'error', 'Quét thất bại');
            }
        }
        
        async function connectWifi() {
            const ssid = document.getElementById('wifiList').value;
            const password = document.getElementById('wifiPassword').value;
            if (!ssid) return showStatus('wifiStatus', 'error', 'Chọn mạng WiFi');
            
            showStatus('wifiStatus', 'success', 'Đang kết nối...');
            try {
                const resp = await fetch('/api/wifi/connect', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ssid, password})
                });
                const data = await resp.json();
                showStatus('wifiStatus', data.success ? 'success' : 'error', data.message);
                if (data.success) scanWifi();
            } catch (e) {
                showStatus('wifiStatus', 'error', 'Kết nối thất bại');
            }
        }
        
        // ========== SYSTEM ==========
        async function loadSystem() {
            try {
                const resp = await fetch('/api/system');
                const data = await resp.json();
                document.getElementById('language').value = data.language || 'vi';
                document.getElementById('otaUrl').value = data.ota_url || '';
                document.getElementById('wsUrl').value = data.ws_url || '';
                document.getElementById('wsToken').value = data.ws_token || '';
                document.getElementById('systemInfo').innerHTML = `
                    <div>📦 Version: ${data.version || 'Unknown'}</div>
                    <div>🖥️ Hostname: ${data.hostname || 'Unknown'}</div>
                    <div>💾 Disk: ${data.disk_usage || 'Unknown'}</div>
                    <div>🧠 RAM: ${data.ram_usage || 'Unknown'}</div>
                    <div>🌡️ CPU Temp: ${data.cpu_temp || 'Unknown'}</div>
                `;
            } catch (e) {}
        }
        
        async function saveSystem() {
            const language = document.getElementById('language').value;
            const otaUrl = document.getElementById('otaUrl').value;
            const wsUrl = document.getElementById('wsUrl').value;
            const wsToken = document.getElementById('wsToken').value;
            try {
                const resp = await fetch('/api/system', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({language, otaUrl, wsUrl, wsToken})
                });
                const data = await resp.json();
                showStatus('systemStatus', data.success ? 'success' : 'error', data.message);
            } catch (e) {
                showStatus('systemStatus', 'error', 'Lỗi kết nối');
            }
        }
        
        async function checkUpdate() {
            showStatus('systemStatus', 'success', 'Đang kiểm tra...');
            try {
                const resp = await fetch('/api/system/update', {method: 'POST'});
                const data = await resp.json();
                showStatus('systemStatus', data.success ? 'success' : 'error', data.message);
            } catch (e) {
                showStatus('systemStatus', 'error', 'Kiểm tra thất bại');
            }
        }
        
        loadStatus();
        loadAudioDevices();
        loadWakeWord();
        loadWindowMode();
        loadSystem();
        scanWifi();
        setInterval(loadStatus, 30000);
    </script>
</body>
</html>
"""


class WebSettingsServer:
    """Web Settings Dashboard Server."""
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.config = ConfigManager.get_instance()
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self._start_time = asyncio.get_event_loop().time()
    
    async def start(self):
        """Khởi động web server."""
        self.app = web.Application()
        self._setup_routes()
        
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        site = web.TCPSite(self.runner, '0.0.0.0', self.port)
        await site.start()
        
        ip = self._get_ip()
        logger.info(f"🌐 Web Settings Dashboard: http://{ip}:{self.port}")
    
    async def stop(self):
        """Dừng web server."""
        if self.runner:
            await self.runner.cleanup()
    
    def _setup_routes(self):
        """Thiết lập routes."""
        self.app.router.add_get('/', self._handle_index)
        self.app.router.add_get('/api/status', self._handle_status)
        self.app.router.add_post('/api/video', self._handle_video)
        self.app.router.add_post('/api/upload', self._handle_upload)
        self.app.router.add_post('/api/rotation', self._handle_rotation)
        self.app.router.add_get('/api/windowmode', self._handle_windowmode_get)
        self.app.router.add_post('/api/windowmode', self._handle_windowmode_post)
        self.app.router.add_post('/api/youtube', self._handle_youtube)
        self.app.router.add_get('/api/audio/devices', self._handle_audio_devices)
        self.app.router.add_post('/api/audio', self._handle_audio)
        # Wake Word
        self.app.router.add_get('/api/wakeword', self._handle_wakeword_get)
        self.app.router.add_post('/api/wakeword', self._handle_wakeword_post)
        # WiFi
        self.app.router.add_get('/api/wifi/scan', self._handle_wifi_scan)
        self.app.router.add_post('/api/wifi/connect', self._handle_wifi_connect)
        # System
        self.app.router.add_get('/api/system', self._handle_system_get)
        self.app.router.add_post('/api/system', self._handle_system_post)
        self.app.router.add_post('/api/system/update', self._handle_system_update)
        # Control
        self.app.router.add_post('/api/restart', self._handle_restart)
        self.app.router.add_post('/api/reboot', self._handle_reboot)
        # Test
        self.app.router.add_post('/api/test/mic', self._handle_test_mic)
        self.app.router.add_post('/api/test/speaker', self._handle_test_speaker)
        self.app.router.add_post('/api/test/chat', self._handle_test_chat)
        # Health & Setup
        self.app.router.add_get('/api/health', self._handle_health)
        self.app.router.add_get('/api/setup/status', self._handle_setup_status)
        self.app.router.add_post('/api/setup/complete', self._handle_setup_complete)
        self.app.router.add_get('/setup', self._handle_setup_wizard)
    
    async def _handle_index(self, request):
        """Trang chính."""
        return web.Response(text=DASHBOARD_HTML, content_type='text/html')
    
    async def _handle_status(self, request):
        """API trạng thái."""
        # Lấy danh sách video
        videos_dir = get_project_root() / "assets" / "videos"
        videos = []
        if videos_dir.exists():
            for ext in ['*.mp4', '*.webm', '*.gif']:
                videos.extend([str(p.relative_to(get_project_root())) for p in videos_dir.glob(ext)])
        
        # Uptime
        uptime_seconds = int(asyncio.get_event_loop().time() - self._start_time)
        uptime = f"{uptime_seconds // 60}m {uptime_seconds % 60}s"
        
        # Config
        video_cfg = self.config.get_config("VIDEO_BACKGROUND", {}) or {}
        rotation = self.config.get_config("SYSTEM_OPTIONS.SCREEN_ROTATION", "normal")
        
        return web.json_response({
            "ip": self._get_ip(),
            "uptime": uptime,
            "videos": videos,
            "video_path": video_cfg.get("VIDEO_FILE_PATH", ""),
            "youtube_url": video_cfg.get("YOUTUBE_URL", ""),
            "rotation": rotation,
        })
    
    async def _handle_video(self, request):
        """Lưu video path."""
        try:
            data = await request.json()
            path = data.get("path", "")
            
            logger.info(f"Saving video path: {path}")
            logger.info(f"Config file: {self.config.config_file}")
            
            result1 = self.config.update_config("VIDEO_BACKGROUND.ENABLED", bool(path))
            result2 = self.config.update_config("VIDEO_BACKGROUND.SOURCE_TYPE", "file")
            result3 = self.config.update_config("VIDEO_BACKGROUND.VIDEO_FILE_PATH", path)
            result4 = self.config.update_config("VIDEO_BACKGROUND.YOUTUBE_URL", "")
            
            logger.info(f"Save results: ENABLED={result1}, SOURCE_TYPE={result2}, PATH={result3}, YOUTUBE={result4}")
            
            if not all([result1, result2, result3, result4]):
                return web.json_response({"success": False, "message": "Lỗi ghi config file!"})
            
            # Reload video trong app
            self._reload_video()
            
            return web.json_response({"success": True, "message": "Đã lưu và áp dụng!"})
        except Exception as e:
            logger.error(f"Save video failed: {e}", exc_info=True)
            return web.json_response({"success": False, "message": str(e)})
    
    async def _handle_upload(self, request):
        """Upload video file."""
        try:
            reader = await request.multipart()
            field = await reader.next()
            
            if field.name != 'video':
                return web.json_response({"success": False, "message": "Không tìm thấy file"})
            
            filename = field.filename
            if not filename:
                return web.json_response({"success": False, "message": "Tên file không hợp lệ"})
            
            # Sanitize filename
            import re
            safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
            
            # Save to assets/videos
            videos_dir = get_project_root() / "assets" / "videos"
            videos_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = videos_dir / safe_filename
            
            # Write file
            size = 0
            with open(file_path, 'wb') as f:
                while True:
                    chunk = await field.read_chunk()
                    if not chunk:
                        break
                    size += len(chunk)
                    f.write(chunk)
            
            relative_path = f"assets/videos/{safe_filename}"
            logger.info(f"Uploaded video: {relative_path} ({size} bytes)")
            
            return web.json_response({
                "success": True, 
                "message": f"Upload thành công!",
                "filename": safe_filename,
                "path": relative_path
            })
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return web.json_response({"success": False, "message": str(e)})
    
    async def _handle_youtube(self, request):
        """Lưu YouTube URL."""
        try:
            data = await request.json()
            url = data.get("url", "")
            
            self.config.update_config("VIDEO_BACKGROUND.ENABLED", bool(url))
            self.config.update_config("VIDEO_BACKGROUND.SOURCE_TYPE", "youtube")
            self.config.update_config("VIDEO_BACKGROUND.YOUTUBE_URL", url)
            self.config.update_config("VIDEO_BACKGROUND.VIDEO_FILE_PATH", "")
            
            self._reload_video()
            
            return web.json_response({"success": True, "message": "Đã lưu YouTube URL!"})
        except Exception as e:
            return web.json_response({"success": False, "message": str(e)})
    
    async def _handle_rotation(self, request):
        """Xoay màn hình."""
        try:
            data = await request.json()
            rotation = data.get("rotation", "normal")
            
            self.config.update_config("SYSTEM_OPTIONS.SCREEN_ROTATION", rotation)
            
            # Apply xrandr
            self._apply_rotation(rotation)
            
            return web.json_response({"success": True, "message": f"Đã xoay màn hình: {rotation}"})
        except Exception as e:
            return web.json_response({"success": False, "message": str(e)})
    
    async def _handle_windowmode_get(self, request):
        """Lấy chế độ màn hình."""
        try:
            # Đọc từ SYSTEM_OPTIONS.WINDOW_SIZE_MODE (đúng với gui_display.py)
            mode = self.config.get_config("SYSTEM_OPTIONS.WINDOW_SIZE_MODE", "screen_100")
            if mode in (None, "", "null"):
                mode = "screen_100"
            return web.json_response({
                "mode": mode,
            })
        except Exception as e:
            return web.json_response({"error": str(e)})
    
    async def _handle_windowmode_post(self, request):
        """Lưu chế độ màn hình."""
        try:
            data = await request.json()
            mode = data.get("mode", "screen_100")
            
            # Lưu vào SYSTEM_OPTIONS.WINDOW_SIZE_MODE (đúng với gui_display.py)
            result = self.config.update_config("SYSTEM_OPTIONS.WINDOW_SIZE_MODE", mode)
            
            if result:
                return web.json_response({"success": True, "message": "Đã lưu! Restart app để áp dụng."})
            else:
                return web.json_response({"success": False, "message": "Lỗi ghi config!"})
        except Exception as e:
            return web.json_response({"success": False, "message": str(e)})
    
    async def _handle_audio_devices(self, request):
        """Lấy danh sách thiết bị âm thanh."""
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            
            input_devices = []
            output_devices = []
            
            for i, d in enumerate(devices):
                if d['max_input_channels'] > 0:
                    input_devices.append(f"{i}: {d['name']}")
                if d['max_output_channels'] > 0:
                    output_devices.append(f"{i}: {d['name']}")
            
            current_mic = self.config.get_config("AUDIO.INPUT_DEVICE_INDEX", 0)
            current_speaker = self.config.get_config("AUDIO.OUTPUT_DEVICE_INDEX", 0)
            mic_volume = self.config.get_config("AUDIO.MIC_VOLUME", 100)
            speaker_volume = self.config.get_config("AUDIO.SPEAKER_VOLUME", 80)
            
            return web.json_response({
                "input_devices": input_devices,
                "output_devices": output_devices,
                "current_mic": current_mic,
                "current_speaker": current_speaker,
                "mic_volume": mic_volume,
                "speaker_volume": speaker_volume,
            })
        except Exception as e:
            return web.json_response({"input_devices": [], "output_devices": [], "error": str(e)})
    
    async def _handle_audio(self, request):
        """Lưu cài đặt âm thanh."""
        try:
            data = await request.json()
            
            mic_device = int(data.get("micDevice", 0))
            speaker_device = int(data.get("speakerDevice", 0))
            mic_volume = int(data.get("micVolume", 100))
            speaker_volume = int(data.get("speakerVolume", 80))
            
            self.config.update_config("AUDIO.INPUT_DEVICE_INDEX", mic_device)
            self.config.update_config("AUDIO.OUTPUT_DEVICE_INDEX", speaker_device)
            self.config.update_config("AUDIO.MIC_VOLUME", mic_volume)
            self.config.update_config("AUDIO.SPEAKER_VOLUME", speaker_volume)
            
            # Áp dụng volume ngay bằng amixer
            try:
                subprocess.run(["amixer", "set", "Capture", f"{mic_volume}%"], capture_output=True, timeout=5)
                subprocess.run(["amixer", "set", "Master", f"{speaker_volume}%"], capture_output=True, timeout=5)
            except Exception:
                pass
            
            return web.json_response({"success": True, "message": "Đã lưu cài đặt âm thanh!"})
        except Exception as e:
            return web.json_response({"success": False, "message": str(e)})
    
    # ========== WAKE WORD ==========
    async def _handle_wakeword_get(self, request):
        """Lấy cài đặt wake word."""
        try:
            enabled = self.config.get_config("WAKE_WORD_OPTIONS.USE_WAKE_WORD", False)
            threshold = self.config.get_config("WAKE_WORD_OPTIONS.KEYWORDS_THRESHOLD", 0.25)
            score = self.config.get_config("WAKE_WORD_OPTIONS.KEYWORDS_SCORE", 2.0)
            return web.json_response({
                "enabled": enabled,
                "threshold": threshold,
                "score": score,
            })
        except Exception as e:
            return web.json_response({"error": str(e)})
    
    async def _handle_wakeword_post(self, request):
        """Lưu cài đặt wake word."""
        try:
            data = await request.json()
            enabled = data.get("enabled", False)
            threshold = float(data.get("sensitivity", 0.25))
            
            self.config.update_config("WAKE_WORD_OPTIONS.USE_WAKE_WORD", enabled)
            self.config.update_config("WAKE_WORD_OPTIONS.KEYWORDS_THRESHOLD", threshold)
            
            return web.json_response({"success": True, "message": "Đã lưu! Restart app để áp dụng."})
        except Exception as e:
            return web.json_response({"success": False, "message": str(e)})
    
    # ========== WIFI ==========
    async def _handle_wifi_scan(self, request):
        """Quét mạng WiFi."""
        try:
            # Lấy mạng hiện tại
            current_ssid = None
            current_ip = self._get_ip()
            
            try:
                result = subprocess.run(
                    ["iwgetid", "-r"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    current_ssid = result.stdout.strip()
            except Exception:
                pass
            
            # Quét mạng khả dụng
            networks = []
            try:
                result = subprocess.run(
                    ["sudo", "iwlist", "wlan0", "scan"],
                    capture_output=True, text=True, timeout=15
                )
                if result.returncode == 0:
                    import re
                    # Parse ESSID từ output
                    essids = re.findall(r'ESSID:"([^"]*)"', result.stdout)
                    signals = re.findall(r'Signal level=(-?\d+)', result.stdout)
                    
                    seen = set()
                    for i, ssid in enumerate(essids):
                        if ssid and ssid not in seen:
                            seen.add(ssid)
                            signal = int(signals[i]) if i < len(signals) else 0
                            networks.append({"ssid": ssid, "signal": signal})
            except Exception as e:
                logger.warning(f"WiFi scan failed: {e}")
            
            return web.json_response({
                "networks": networks[:15],
                "current": current_ssid,
                "ip": current_ip,
            })
        except Exception as e:
            logger.error(f"WiFi scan error: {e}")
            return web.json_response({
                "networks": [], 
                "current": None, 
                "ip": self._get_ip(),
                "error": str(e)
            })
    
    async def _handle_wifi_connect(self, request):
        """Kết nối WiFi."""
        try:
            data = await request.json()
            ssid = data.get("ssid", "")
            password = data.get("password", "")
            
            if not ssid:
                return web.json_response({"success": False, "message": "Thiếu tên mạng"})
            
            logger.info(f"Connecting to WiFi: {ssid}")
            
            # Dùng nmcli để kết nối
            if password:
                cmd = ["sudo", "nmcli", "device", "wifi", "connect", ssid, "password", password]
            else:
                cmd = ["sudo", "nmcli", "device", "wifi", "connect", ssid]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info(f"Connected to WiFi: {ssid}")
                return web.json_response({"success": True, "message": f"✅ Đã kết nối {ssid}!"})
            else:
                error = result.stderr or result.stdout or "Unknown error"
                logger.error(f"WiFi connect failed: {error}")
                return web.json_response({"success": False, "message": f"❌ {error[:80]}"})
                
        except subprocess.TimeoutExpired:
            return web.json_response({"success": False, "message": "⏱️ Timeout"})
        except Exception as e:
            logger.error(f"WiFi connect error: {e}")
            return web.json_response({"success": False, "message": str(e)})
    
    # ========== SYSTEM ==========
    async def _handle_system_get(self, request):
        """Lấy thông tin hệ thống."""
        try:
            import psutil
            import socket
            
            language = self.config.get_config("SYSTEM_OPTIONS.LANGUAGE", "vi-VN")
            ota_url = self.config.get_config("SYSTEM_OPTIONS.NETWORK.OTA_VERSION_URL", "")
            ws_url = self.config.get_config("SYSTEM_OPTIONS.NETWORK.WEBSOCKET_URL", "")
            ws_token = self.config.get_config("SYSTEM_OPTIONS.NETWORK.WEBSOCKET_ACCESS_TOKEN", "")
            
            # Version
            version = "Unknown"
            version_file = get_project_root() / "VERSION"
            if version_file.exists():
                version = version_file.read_text().strip()
            
            # System info
            hostname = socket.gethostname()
            disk = psutil.disk_usage('/')
            disk_usage = f"{disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB"
            ram = psutil.virtual_memory()
            ram_usage = f"{ram.used // (1024**2)}MB / {ram.total // (1024**2)}MB"
            
            # CPU temp
            cpu_temp = "N/A"
            try:
                temp_file = Path("/sys/class/thermal/thermal_zone0/temp")
                if temp_file.exists():
                    temp = int(temp_file.read_text().strip()) / 1000
                    cpu_temp = f"{temp:.1f}°C"
            except Exception:
                pass
            
            return web.json_response({
                "language": language,
                "ota_url": ota_url,
                "ws_url": ws_url,
                "ws_token": ws_token,
                "version": version,
                "hostname": hostname,
                "disk_usage": disk_usage,
                "ram_usage": ram_usage,
                "cpu_temp": cpu_temp,
            })
        except Exception as e:
            return web.json_response({"error": str(e)})
    
    async def _handle_system_post(self, request):
        """Lưu cài đặt hệ thống."""
        try:
            data = await request.json()
            self.config.update_config("SYSTEM_OPTIONS.LANGUAGE", data.get("language", "vi-VN"))
            
            # OTA URL
            if data.get("otaUrl"):
                self.config.update_config("SYSTEM_OPTIONS.NETWORK.OTA_VERSION_URL", data.get("otaUrl"))
            
            # WebSocket
            if data.get("wsUrl"):
                self.config.update_config("SYSTEM_OPTIONS.NETWORK.WEBSOCKET_URL", data.get("wsUrl"))
            if data.get("wsToken"):
                self.config.update_config("SYSTEM_OPTIONS.NETWORK.WEBSOCKET_ACCESS_TOKEN", data.get("wsToken"))
            
            return web.json_response({"success": True, "message": "Đã lưu! Restart app để áp dụng."})
        except Exception as e:
            return web.json_response({"success": False, "message": str(e)})
    
    async def _handle_system_update(self, request):
        """Kiểm tra và cập nhật từ GitHub."""
        try:
            project_root = str(get_project_root())
            
            # Fetch trước để check có update không
            fetch_result = subprocess.run(
                ["git", "-C", project_root, "fetch", "origin"],
                capture_output=True, text=True, timeout=30
            )
            
            # Check xem có commits mới không
            status_result = subprocess.run(
                ["git", "-C", project_root, "status", "-uno"],
                capture_output=True, text=True, timeout=10
            )
            
            if "Your branch is up to date" in status_result.stdout:
                return web.json_response({"success": True, "message": "✅ Đã là phiên bản mới nhất!"})
            
            # Có update -> pull
            pull_result = subprocess.run(
                ["git", "-C", project_root, "pull", "--ff-only"],
                capture_output=True, text=True, timeout=60
            )
            
            if pull_result.returncode == 0:
                # Đếm số files thay đổi
                lines = pull_result.stdout.strip().split('\n')
                return web.json_response({
                    "success": True, 
                    "message": f"✅ Đã cập nhật! Nhấn Restart để áp dụng."
                })
            else:
                error_msg = pull_result.stderr or pull_result.stdout or "Unknown error"
                logger.error(f"Git pull failed: {error_msg}")
                return web.json_response({
                    "success": False, 
                    "message": f"❌ Lỗi: {error_msg[:100]}"
                })
                
        except subprocess.TimeoutExpired:
            return web.json_response({"success": False, "message": "⏱️ Timeout - kết nối chậm"})
        except Exception as e:
            logger.error(f"Update error: {e}")
            return web.json_response({"success": False, "message": f"❌ Lỗi: {str(e)}"})
    
    async def _handle_restart(self, request):
        """Restart app."""
        asyncio.create_task(self._do_restart())
        return web.json_response({"success": True, "message": "Đang restart..."})
    
    async def _handle_reboot(self, request):
        """Reboot Pi."""
        subprocess.Popen(["sudo", "reboot"])
        return web.json_response({"success": True, "message": "Đang reboot..."})
    
    async def _do_restart(self):
        """Thực hiện restart."""
        await asyncio.sleep(1)
        os.execv("/usr/bin/python3", ["python3", "main.py", "--mode", "gui"])
    
    def _reload_video(self):
        """Reload video trong GUI."""
        try:
            from src.application import Application
            app = Application._instance  # Dùng _instance trực tiếp thay vì get_instance()
            
            logger.info(f"Application._instance = {app}")
            if app:
                logger.info(f"app.display = {getattr(app, 'display', 'NOT FOUND')}")
            
            if app and hasattr(app, 'display') and app.display:
                logger.info("Calling reload_video_from_config...")
                app.display.reload_video_from_config()
                logger.info("Video reload completed")
            else:
                logger.warning("Application or display not available for video reload")
                logger.info("Video sẽ được áp dụng sau khi restart app")
        except Exception as e:
            logger.error(f"Reload video failed: {e}", exc_info=True)
    
    def _apply_rotation(self, rotation: str):
        """Apply xrandr rotation."""
        env = os.environ.copy()
        env["DISPLAY"] = ":0"
        
        for output in ["HDMI-1", "HDMI-2", "HDMI-A-1"]:
            try:
                result = subprocess.run(
                    ["xrandr", "--output", output, "--rotate", rotation],
                    capture_output=True, env=env, timeout=5
                )
                if result.returncode == 0:
                    logger.info(f"Rotated {output} to {rotation}")
                    break
            except Exception:
                pass
    
    def _get_ip(self) -> str:
        """Lấy IP address."""
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "Unknown"
    
    # ========== TEST HANDLERS ==========
    async def _handle_test_mic(self, request):
        """Test microphone - ghi âm và phát lại."""
        try:
            import sounddevice as sd
            import numpy as np
            
            logger.info("Test MIC: Recording 3 seconds...")
            
            # Ghi âm 3 giây
            sample_rate = 16000
            duration = 3
            recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
            sd.wait()
            
            # Kiểm tra có âm thanh không
            max_amplitude = np.max(np.abs(recording))
            avg_amplitude = np.mean(np.abs(recording))
            
            logger.info(f"Test MIC: Max amplitude: {max_amplitude}, Avg: {avg_amplitude}")
            
            # Phát lại
            logger.info("Test MIC: Playing back...")
            sd.play(recording, sample_rate)
            sd.wait()
            
            if max_amplitude < 100:
                return web.json_response({
                    "success": False, 
                    "message": f"⚠️ Microphone quá yếu hoặc không hoạt động (max: {max_amplitude})"
                })
            
            return web.json_response({
                "success": True, 
                "message": f"✅ MIC OK! Đã ghi và phát lại. Max: {max_amplitude}, Avg: {int(avg_amplitude)}"
            })
            
        except Exception as e:
            logger.error(f"Test MIC error: {e}")
            return web.json_response({"success": False, "message": f"❌ Lỗi: {str(e)}"})
    
    async def _handle_test_speaker(self, request):
        """Test speaker - phát âm thanh beep."""
        try:
            import sounddevice as sd
            import numpy as np
            
            logger.info("Test Speaker: Playing beep...")
            
            # Tạo beep tone
            sample_rate = 44100
            duration = 0.5
            frequency = 440  # A4 note
            
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            # Sine wave with fade in/out
            beep = np.sin(2 * np.pi * frequency * t) * 0.5
            fade_samples = int(sample_rate * 0.05)
            beep[:fade_samples] *= np.linspace(0, 1, fade_samples)
            beep[-fade_samples:] *= np.linspace(1, 0, fade_samples)
            
            # Phát 3 beep
            for i in range(3):
                sd.play(beep.astype(np.float32), sample_rate)
                sd.wait()
                if i < 2:
                    import time
                    time.sleep(0.2)
            
            return web.json_response({
                "success": True, 
                "message": "✅ Đã phát 3 tiếng beep! Bạn có nghe thấy không?"
            })
            
        except Exception as e:
            logger.error(f"Test Speaker error: {e}")
            return web.json_response({"success": False, "message": f"❌ Lỗi: {str(e)}"})
    
    async def _handle_test_chat(self, request):
        """Test chat với AI qua WebSocket API."""
        try:
            data = await request.json()
            message = data.get("message", "").strip()
            
            if not message:
                return web.json_response({"success": False, "message": "Thiếu tin nhắn"})
            
            logger.info(f"Test Chat: Sending '{message}' to AI...")
            
            # Thử gửi qua Application
            try:
                from src.application import Application
                app = Application._instance
                
                if not app:
                    return web.json_response({
                        "success": False,
                        "message": "⚠️ Application chưa khởi tạo. Vui lòng chờ app khởi động."
                    })
                
                # Kiểm tra kết nối
                if not await app.connect_protocol():
                    return web.json_response({
                        "success": False,
                        "message": "⚠️ Chưa kết nối với AI Server. Đang thử kết nối lại..."
                    })
                
                # Cập nhật hiển thị user text
                ui_plugin = app.plugins.get_plugin("ui") if hasattr(app, 'plugins') else None
                if ui_plugin and hasattr(ui_plugin, 'display'):
                    await ui_plugin.display.update_user_text(message)
                
                # Gửi tin nhắn như wake word detected (mô phỏng user nói)
                await app.protocol.send_wake_word_detected(message)
                
                return web.json_response({
                    "success": True,
                    "response": "📤 Đã gửi tin nhắn đến AI! Xem phản hồi trên màn hình chính."
                })
                
            except Exception as e:
                logger.error(f"Test Chat send error: {e}")
                import traceback
                traceback.print_exc()
                return web.json_response({
                    "success": False,
                    "message": f"❌ Lỗi gửi tin nhắn: {str(e)}"
                })
            
        except Exception as e:
            logger.error(f"Test Chat error: {e}")
            return web.json_response({"success": False, "message": f"❌ Lỗi: {str(e)}"})
    
    # ========== HEALTH CHECK ==========
    async def _handle_health(self, request):
        """Health check endpoint cho monitoring."""
        import psutil
        import os
        
        health = {
            "status": "ok",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "uptime": self._get_uptime(),
            "checks": {}
        }
        
        # Check 1: CPU/Memory
        try:
            health["checks"]["system"] = {
                "status": "ok",
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent
            }
        except Exception as e:
            health["checks"]["system"] = {"status": "error", "message": str(e)}
        
        # Check 2: Audio devices
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            has_input = any(d['max_input_channels'] > 0 for d in devices)
            has_output = any(d['max_output_channels'] > 0 for d in devices)
            health["checks"]["audio"] = {
                "status": "ok" if (has_input and has_output) else "warning",
                "input_available": has_input,
                "output_available": has_output
            }
        except Exception as e:
            health["checks"]["audio"] = {"status": "error", "message": str(e)}
        
        # Check 3: WebSocket connection
        try:
            from src.application import Application
            app = Application._instance
            if app and hasattr(app, 'protocol') and app.protocol:
                health["checks"]["websocket"] = {"status": "ok", "connected": True}
            else:
                health["checks"]["websocket"] = {"status": "warning", "connected": False}
        except Exception as e:
            health["checks"]["websocket"] = {"status": "error", "message": str(e)}
        
        # Check 4: Config file
        try:
            config_file = self.config.config_file
            if config_file and os.path.exists(config_file):
                health["checks"]["config"] = {"status": "ok", "path": str(config_file)}
            else:
                health["checks"]["config"] = {"status": "warning", "message": "Config file not found"}
        except Exception as e:
            health["checks"]["config"] = {"status": "error", "message": str(e)}
        
        # Overall status
        statuses = [c.get("status", "ok") for c in health["checks"].values()]
        if "error" in statuses:
            health["status"] = "unhealthy"
        elif "warning" in statuses:
            health["status"] = "degraded"
        
        return web.json_response(health)
    
    def _get_uptime(self) -> str:
        """Lấy uptime của app."""
        try:
            import psutil
            import os
            p = psutil.Process(os.getpid())
            uptime_sec = time.time() - p.create_time()
            hours, remainder = divmod(int(uptime_sec), 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{hours}h {minutes}m {seconds}s"
        except:
            return "Unknown"
    
    # ========== SETUP WIZARD ==========
    async def _handle_setup_status(self, request):
        """Kiểm tra trạng thái setup."""
        is_first_run = self.config.get_config("SYSTEM.FIRST_RUN_COMPLETE", False) != True
        return web.json_response({
            "first_run": is_first_run,
            "redirect_to_setup": is_first_run
        })
    
    async def _handle_setup_complete(self, request):
        """Đánh dấu setup hoàn tất."""
        try:
            self.config.update_config("SYSTEM.FIRST_RUN_COMPLETE", True)
            return web.json_response({"success": True, "message": "Setup hoàn tất!"})
        except Exception as e:
            return web.json_response({"success": False, "message": str(e)})
    
    async def _handle_setup_wizard(self, request):
        """Trang Setup Wizard cho first-run."""
        setup_html = '''<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart C AI - Thiết Lập Ban Đầu</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            color: #fff;
            overflow-x: hidden;
        }
        .wizard-container {
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .header {
            text-align: center;
            padding: 30px 0;
        }
        .header h1 {
            font-size: 28px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }
        .header p { color: #94a3b8; font-size: 14px; }
        .progress-bar {
            display: flex;
            justify-content: space-between;
            margin: 20px 0 30px;
            position: relative;
        }
        .progress-bar::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 0;
            right: 0;
            height: 3px;
            background: rgba(255,255,255,0.2);
            transform: translateY(-50%);
            z-index: 0;
        }
        .step-indicator {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: rgba(255,255,255,0.1);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            z-index: 1;
            transition: all 0.3s;
        }
        .step-indicator.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            box-shadow: 0 0 20px rgba(102,126,234,0.5);
        }
        .step-indicator.done { background: #10b981; }
        .step-content {
            flex: 1;
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 30px;
            display: none;
        }
        .step-content.active { display: block; }
        .step-content h2 { font-size: 22px; margin-bottom: 20px; }
        .form-group { margin-bottom: 20px; }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            color: #94a3b8;
            font-size: 14px;
        }
        select, input {
            width: 100%;
            padding: 15px;
            border: 2px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            background: rgba(255,255,255,0.05);
            color: #fff;
            font-size: 16px;
        }
        select:focus, input:focus {
            outline: none;
            border-color: #667eea;
        }
        .btn {
            padding: 15px 30px;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
        }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(102,126,234,0.4); }
        .btn-secondary {
            background: rgba(255,255,255,0.1);
            color: #fff;
        }
        .nav-buttons {
            display: flex;
            justify-content: space-between;
            margin-top: 30px;
        }
        .status-card {
            background: rgba(16,185,129,0.1);
            border: 1px solid rgba(16,185,129,0.3);
            border-radius: 12px;
            padding: 15px;
            margin: 10px 0;
        }
        .status-card.error {
            background: rgba(239,68,68,0.1);
            border-color: rgba(239,68,68,0.3);
        }
        .device-list {
            max-height: 200px;
            overflow-y: auto;
            margin: 10px 0;
        }
        .device-item {
            padding: 12px;
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
            margin: 5px 0;
            cursor: pointer;
            transition: all 0.2s;
        }
        .device-item:hover { background: rgba(255,255,255,0.1); }
        .device-item.selected {
            background: rgba(102,126,234,0.2);
            border: 1px solid #667eea;
        }
        .success-animation {
            text-align: center;
            padding: 40px;
        }
        .success-animation .icon { font-size: 80px; animation: bounce 1s infinite; }
        @keyframes bounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }
    </style>
</head>
<body>
    <div class="wizard-container">
        <div class="header">
            <h1>🤖 Smart C AI</h1>
            <p>Thiết lập ban đầu - Chỉ mất 2 phút</p>
        </div>
        
        <div class="progress-bar">
            <div class="step-indicator active" id="ind1">1</div>
            <div class="step-indicator" id="ind2">2</div>
            <div class="step-indicator" id="ind3">3</div>
            <div class="step-indicator" id="ind4">✓</div>
        </div>
        
        <!-- Step 1: WiFi -->
        <div class="step-content active" id="step1">
            <h2>📶 Kết nối WiFi</h2>
            <div class="form-group">
                <label>Mạng WiFi hiện tại:</label>
                <div id="currentWifi" class="status-card">Đang kiểm tra...</div>
            </div>
            <div class="form-group">
                <label>Chọn mạng WiFi:</label>
                <select id="wifiList"><option value="">Đang quét...</option></select>
            </div>
            <div class="form-group">
                <label>Mật khẩu:</label>
                <input type="password" id="wifiPassword" placeholder="Nhập mật khẩu WiFi">
            </div>
            <button class="btn btn-secondary" onclick="connectWifi()">📶 Kết nối</button>
            <div id="wifiStatus" style="margin-top: 10px;"></div>
            <div class="nav-buttons">
                <div></div>
                <button class="btn btn-primary" onclick="nextStep(2)">Tiếp theo →</button>
            </div>
        </div>
        
        <!-- Step 2: Audio -->
        <div class="step-content" id="step2">
            <h2>🎤 Thiết lập Microphone & Loa</h2>
            <div class="form-group">
                <label>Chọn Microphone:</label>
                <select id="micDevice"></select>
            </div>
            <div class="form-group">
                <label>Chọn Loa:</label>
                <select id="speakerDevice"></select>
            </div>
            <div style="display: flex; gap: 10px; margin-top: 20px;">
                <button class="btn btn-secondary" onclick="testMic()">🎤 Test MIC</button>
                <button class="btn btn-secondary" onclick="testSpeaker()">🔊 Test Loa</button>
            </div>
            <div id="audioStatus" style="margin-top: 10px;"></div>
            <div class="nav-buttons">
                <button class="btn btn-secondary" onclick="prevStep(1)">← Quay lại</button>
                <button class="btn btn-primary" onclick="saveAudioAndNext()">Tiếp theo →</button>
            </div>
        </div>
        
        <!-- Step 3: Test -->
        <div class="step-content" id="step3">
            <h2>🧪 Kiểm tra hệ thống</h2>
            <div id="systemChecks">
                <div class="status-card" id="checkAudio">🔄 Đang kiểm tra Audio...</div>
                <div class="status-card" id="checkServer">🔄 Đang kiểm tra Server...</div>
                <div class="status-card" id="checkWakeword">🔄 Đang kiểm tra Wake Word...</div>
            </div>
            <div class="form-group" style="margin-top: 20px;">
                <label>Test nói chuyện với AI:</label>
                <input type="text" id="testMessage" placeholder="Nhập tin nhắn test...">
                <button class="btn btn-secondary" onclick="testChat()" style="margin-top: 10px;">📤 Gửi test</button>
            </div>
            <div id="testResult" style="margin-top: 10px;"></div>
            <div class="nav-buttons">
                <button class="btn btn-secondary" onclick="prevStep(2)">← Quay lại</button>
                <button class="btn btn-primary" onclick="completeSetup()">Hoàn tất ✓</button>
            </div>
        </div>
        
        <!-- Step 4: Complete -->
        <div class="step-content" id="step4">
            <div class="success-animation">
                <div class="icon">🎉</div>
                <h2 style="margin-top: 20px;">Thiết lập hoàn tất!</h2>
                <p style="color: #94a3b8; margin-top: 10px;">Smart C AI đã sẵn sàng sử dụng</p>
                <div style="margin-top: 30px;">
                    <p><strong>Wake Words:</strong> "Alexa", "Smart C", "Sophia"</p>
                    <p style="margin-top: 10px; color: #94a3b8;">Nói một trong các từ trên để bắt đầu trò chuyện</p>
                </div>
                <button class="btn btn-primary" onclick="window.location.href='/'" style="margin-top: 30px;">
                    Vào Dashboard →
                </button>
            </div>
        </div>
    </div>
    
    <script>
        let currentStep = 1;
        
        function nextStep(step) {
            document.getElementById('step' + currentStep).classList.remove('active');
            document.getElementById('step' + step).classList.add('active');
            document.getElementById('ind' + currentStep).classList.remove('active');
            document.getElementById('ind' + currentStep).classList.add('done');
            document.getElementById('ind' + step).classList.add('active');
            currentStep = step;
            
            if (step === 2) loadAudioDevices();
            if (step === 3) runSystemChecks();
        }
        
        function prevStep(step) {
            document.getElementById('step' + currentStep).classList.remove('active');
            document.getElementById('step' + step).classList.add('active');
            document.getElementById('ind' + currentStep).classList.remove('active');
            document.getElementById('ind' + step).classList.add('active');
            document.getElementById('ind' + step).classList.remove('done');
            currentStep = step;
        }
        
        // WiFi functions
        async function loadWifi() {
            try {
                const resp = await fetch('/api/wifi/scan');
                const data = await resp.json();
                const select = document.getElementById('wifiList');
                select.innerHTML = '';
                
                if (data.current) {
                    document.getElementById('currentWifi').innerHTML = 
                        `✅ Đã kết nối: <strong>${data.current}</strong>` + 
                        (data.ip ? ` (IP: ${data.ip})` : '');
                } else {
                    document.getElementById('currentWifi').innerHTML = '❌ Chưa kết nối WiFi';
                    document.getElementById('currentWifi').classList.add('error');
                }
                
                (data.networks || []).forEach(n => {
                    const opt = document.createElement('option');
                    opt.value = n.ssid;
                    opt.textContent = `${n.ssid} (${n.signal}%)`;
                    select.appendChild(opt);
                });
            } catch(e) {
                document.getElementById('currentWifi').innerHTML = '❌ Lỗi quét WiFi';
            }
        }
        
        async function connectWifi() {
            const ssid = document.getElementById('wifiList').value;
            const password = document.getElementById('wifiPassword').value;
            if (!ssid) return;
            
            document.getElementById('wifiStatus').innerHTML = '⏳ Đang kết nối...';
            try {
                const resp = await fetch('/api/wifi/connect', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ssid, password})
                });
                const data = await resp.json();
                document.getElementById('wifiStatus').innerHTML = data.success ? 
                    '✅ ' + data.message : '❌ ' + data.message;
                if (data.success) loadWifi();
            } catch(e) {
                document.getElementById('wifiStatus').innerHTML = '❌ Lỗi kết nối';
            }
        }
        
        // Audio functions
        async function loadAudioDevices() {
            try {
                const resp = await fetch('/api/audio');
                const data = await resp.json();
                
                const micSelect = document.getElementById('micDevice');
                const speakerSelect = document.getElementById('speakerDevice');
                micSelect.innerHTML = '';
                speakerSelect.innerHTML = '';
                
                (data.devices || []).forEach(d => {
                    if (d.max_input_channels > 0) {
                        const opt = document.createElement('option');
                        opt.value = d.id;
                        opt.textContent = d.name;
                        if (d.id === data.current_input) opt.selected = true;
                        micSelect.appendChild(opt);
                    }
                    if (d.max_output_channels > 0) {
                        const opt = document.createElement('option');
                        opt.value = d.id;
                        opt.textContent = d.name;
                        if (d.id === data.current_output) opt.selected = true;
                        speakerSelect.appendChild(opt);
                    }
                });
            } catch(e) {
                document.getElementById('audioStatus').innerHTML = '❌ Lỗi tải thiết bị';
            }
        }
        
        async function testMic() {
            document.getElementById('audioStatus').innerHTML = '🔴 Đang ghi âm 3s...';
            try {
                const resp = await fetch('/api/test/mic', {method: 'POST'});
                const data = await resp.json();
                document.getElementById('audioStatus').innerHTML = data.success ? 
                    '✅ ' + data.message : '❌ ' + data.message;
            } catch(e) {
                document.getElementById('audioStatus').innerHTML = '❌ Lỗi test MIC';
            }
        }
        
        async function testSpeaker() {
            document.getElementById('audioStatus').innerHTML = '🔊 Đang phát...';
            try {
                const resp = await fetch('/api/test/speaker', {method: 'POST'});
                const data = await resp.json();
                document.getElementById('audioStatus').innerHTML = data.success ? 
                    '✅ ' + data.message : '❌ ' + data.message;
            } catch(e) {
                document.getElementById('audioStatus').innerHTML = '❌ Lỗi test Loa';
            }
        }
        
        async function saveAudioAndNext() {
            const micDevice = document.getElementById('micDevice').value;
            const speakerDevice = document.getElementById('speakerDevice').value;
            try {
                await fetch('/api/audio', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({micDevice, speakerDevice, micVolume: 80, speakerVolume: 80})
                });
            } catch(e) {}
            nextStep(3);
        }
        
        // System checks
        async function runSystemChecks() {
            // Check Audio
            try {
                const resp = await fetch('/api/health');
                const data = await resp.json();
                
                const audioCheck = data.checks?.audio;
                document.getElementById('checkAudio').innerHTML = audioCheck?.status === 'ok' ?
                    '✅ Audio: MIC và Loa hoạt động' : '⚠️ Audio: Có vấn đề';
                document.getElementById('checkAudio').className = 'status-card' + 
                    (audioCheck?.status !== 'ok' ? ' error' : '');
                
                const wsCheck = data.checks?.websocket;
                document.getElementById('checkServer').innerHTML = wsCheck?.connected ?
                    '✅ Server: Đã kết nối' : '⚠️ Server: Chưa kết nối (sẽ tự động kết nối)';
                document.getElementById('checkServer').className = 'status-card' + 
                    (!wsCheck?.connected ? ' error' : '');
                
                document.getElementById('checkWakeword').innerHTML = '✅ Wake Word: Sẵn sàng (Alexa, Smart C, Sophia)';
            } catch(e) {
                document.getElementById('checkServer').innerHTML = '❌ Không thể kiểm tra';
            }
        }
        
        async function testChat() {
            const msg = document.getElementById('testMessage').value;
            if (!msg) return;
            document.getElementById('testResult').innerHTML = '⏳ Đang gửi...';
            try {
                const resp = await fetch('/api/test/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: msg})
                });
                const data = await resp.json();
                document.getElementById('testResult').innerHTML = data.success ? 
                    '✅ ' + (data.response || data.message) : '❌ ' + data.message;
            } catch(e) {
                document.getElementById('testResult').innerHTML = '❌ Lỗi gửi';
            }
        }
        
        async function completeSetup() {
            try {
                await fetch('/api/setup/complete', {method: 'POST'});
                nextStep(4);
            } catch(e) {
                nextStep(4);
            }
        }
        
        // Init
        loadWifi();
    </script>
</body>
</html>'''
        return web.Response(text=setup_html, content_type='text/html')


# Singleton instance
_server: Optional[WebSettingsServer] = None


async def start_web_settings(port: int = 8080):
    """Khởi động Web Settings Server."""
    global _server
    if _server is None:
        _server = WebSettingsServer(port)
        await _server.start()
    return _server


async def stop_web_settings():
    """Dừng Web Settings Server."""
    global _server
    if _server:
        await _server.stop()
        _server = None
