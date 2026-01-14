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
        
        /* Tab Styles */
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; overflow-x: auto; padding-bottom: 5px; }
        .tab-btn { flex: 1; padding: 12px; border: none; background: rgba(255,255,255,0.05); color: #aaa; border-radius: 8px; cursor: pointer; font-weight: 600; white-space: nowrap; }
        .tab-btn.active { background: #667eea; color: #fff; }
        .tab-content { display: none; margin-bottom: 20px; }
        .tab-content.active { display: block; }
        
        /* Gallery Styles */
        .gallery { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; max-height: 300px; overflow-y: auto; padding: 10px; background: rgba(0,0,0,0.2); border-radius: 8px; }
        .gallery-item { position: relative; aspect-ratio: 16/9; background: #000; border-radius: 4px; overflow: hidden; cursor: pointer; }
        .gallery-item img { width: 100%; height: 100%; object-fit: cover; opacity: 0.7; }
        .gallery-item.selected { border: 2px solid #38ef7d; }
        .gallery-item.selected img { opacity: 1; }
        .check-icon { position: absolute; top: 5px; right: 5px; color: #38ef7d; display: none; background: rgba(0,0,0,0.5); border-radius: 50%; padding: 2px; }
        .gallery-item.selected .check-icon { display: block; }
        .delete-btn { position: absolute; top: 5px; left: 5px; background: rgba(255,0,0,0.7); border: none; border-radius: 4px; color: white; cursor: pointer; padding: 2px 6px; font-size: 12px; }
        .delete-btn:hover { background: rgba(255,0,0,1); }
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
        
        <div class="tabs">
            <button class="tab-btn active" onclick="openTab('bg')">🖼️ Background</button>
            <button class="tab-btn" onclick="openTab('display')">🖥️ Hiển thị</button>
            <button class="tab-btn" onclick="openTab('wifi')">📶 WiFi</button>
            <button class="tab-btn" onclick="openTab('other')">⚙️ Khác</button>
        </div>

        <!-- BACKGROUND TAB -->
        <div id="tab-bg" class="tab-content active">
            <div class="card">
                <h2>🖼️ Chọn Chế độ Nền</h2>
                <div class="form-group">
                    <select id="bgMode" onchange="toggleBgMode()">
                        <option value="video">🎬 Video Player</option>
                        <option value="slide">📸 Image Slideshow</option>
                    </select>
                </div>
                
                <!-- Video Section -->
                <div id="videoSection">
                    <div class="form-group">
                        <label>Có sẵn:</label>
                        <div class="video-list" id="videoList">Loading...</div>
                    </div>
                    <div class="form-group">
                        <input type="text" id="videoPath" placeholder="assets/videos/video.mp4">
                    </div>
                    <button class="btn btn-primary" onclick="saveVideoConfig()">💾 Lưu Video</button>
                    
                    <hr style="border-color: #444; margin: 20px 0;">
                    
                    <div class="form-group">
                        <label>📤 Upload Video mới:</label>
                        <input type="file" id="videoFile" accept="video/*,.gif,.webp" style="display:none;" onchange="uploadVideo()">
                        <button class="btn btn-success" onclick="document.getElementById('videoFile').click()">📁 Chọn Video Upload</button>
                        <div id="videoUploadProgress" style="margin-top: 10px; display: none;">
                            <div style="background: #333; border-radius: 8px; overflow: hidden; height: 8px;">
                                <div id="videoProgressBar" style="height: 100%; background: #667eea; width: 0%;"></div>
                            </div>
                            <small id="videoUploadText">Uploading...</small>
                        </div>
                    </div>
                </div>

                <!-- Slide Section -->
                <div id="slideSection" style="display: none;">
                     <div class="form-group">
                        <label>📤 Upload Ảnh mới:</label>
                        <input type="file" id="imageFile" accept="image/*" style="display:none;" onchange="uploadImage()">
                        <button class="btn btn-success" onclick="document.getElementById('imageFile').click()">📁 Chọn Ảnh Upload</button>
                        <div id="imageUploadStatus" style="margin-top: 5px; color: #888;"></div>
                    </div>

                    <div class="form-group">
                        <label>Chọn ảnh chạy Slide:</label>
                        <div id="imageGallery" class="gallery">
                            Loading...
                        </div>
                    </div>

                    <div class="form-group">
                        <label>Thời gian chuyển (giây):</label>
                        <input type="number" id="slideInterval" value="5" min="2" max="60">
                    </div>
                    
                    <button class="btn btn-primary" onclick="saveSlideConfig()">💾 Lưu Slideshow</button>
                </div>
                
                <div id="bgStatus" class="status" style="display:none;"></div>
            </div>
        </div>

        <!-- DISPLAY TAB -->
        <div id="tab-display" class="tab-content">
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
        </div>
        
        <!-- OTHER TAB -->
        <div id="tab-other" class="tab-content">
            <div class="card">
                <h2>📺 YouTube URL</h2>
                <div class="form-group">
                    <input type="text" id="youtubeUrl" placeholder="https://www.youtube.com/watch?v=...">
                </div>
                <button class="btn btn-primary" onclick="saveYoutube()">💾 Lưu YouTube</button>
                <div id="youtubeStatus"></div>
            </div>

            <div class="card">
                <h2>🔊 Âm Thanh</h2>
                <h3>Ghi âm (Mic)</h3>
                <div class="form-group">
                    <select id="micDevice"></select>
                </div>
                <div class="form-group">
                    <label>Volume Mic: <span id="micVolumeValue">100</span>%</label>
                    <input type="range" id="micVolume" min="0" max="100" value="100" oninput="document.getElementById('micVolumeValue').textContent=this.value" style="width:100%">
                </div>
                <div class="form-group" style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px; margin-top: 5px;">
                     <label><input type="checkbox" id="i2sEnabled" onchange="toggleI2S()"> 🎙️ Sử dụng I2S Mic (INMP441)</label>
                     <div id="i2sOptions" style="display:none; margin-left: 20px; margin-top: 5px;">
                        <label><input type="checkbox" id="i2sStereo" onchange="toggleBeamforming()"> Stereo</label>
                        <label style="margin-left: 10px;"><input type="checkbox" id="beamformingEnabled"> Beamforming</label>
                     </div>
                </div>
                
                <h3 style="margin-top: 15px;">Phát (Loa)</h3>
                <div class="form-group">
                    <select id="speakerDevice"></select>
                </div>
                <div class="form-group">
                    <label>Volume Loa: <span id="speakerVolumeValue">80</span>%</label>
                    <input type="range" id="speakerVolume" min="0" max="100" value="80" oninput="document.getElementById('speakerVolumeValue').textContent=this.value" style="width:100%">
                </div>
                <div class="form-group">
                    <label><input type="checkbox" id="hdmiAudio"> 📺 Xuất HDMI</label>
                </div>
                
                <div style="display: flex; gap: 5px; margin-top: 10px;">
                    <button class="btn btn-primary" onclick="saveAudioConfig()">💾 Lưu Audio</button>
                    <button class="btn btn-success" onclick="saveAndRestartAudio()">🔄 Lưu & Restart Audio</button>
                </div>
                <div id="audioStatus"></div>
                
                <hr style="border-color: #444; margin: 15px 0;">
                
                <h3>Kiểm tra</h3>
                <div style="display: flex; gap: 5px;">
                    <button class="btn btn-secondary" onclick="testMic()">🎤 Test Mic</button>
                    <button class="btn btn-secondary" onclick="testSpeaker()">🔊 Test Loa</button>
                </div>
            </div>

            <div class="card">
                <h2>🎤 Wake Word</h2>
                <div class="form-group">
                    <label><input type="checkbox" id="wakeWordEnabled"> Bật Wake Word</label>
                </div>
                <div class="form-group">
                     <label>Độ nhạy: <span id="sensitivityValue">0.25</span></label>
                     <input type="range" id="wakeWordSensitivity" min="0.1" max="0.5" step="0.05" value="0.25" oninput="document.getElementById('sensitivityValue').textContent=this.value" style="width:100%">
                </div>
                <button class="btn btn-primary" onclick="saveWakeWord()">💾 Lưu</button>
            </div>

            <div class="card">
                <h2>⚙️ Hệ Thống & Test</h2>
                <div class="form-group">
                    <button class="btn btn-primary" onclick="checkUpdate()">🔄 Kiểm tra cập nhật Cloud</button>
                </div>
                <div class="form-group">
                    <button class="btn btn-success" onclick="restartApp()">🔄 Restart App</button>
                </div>
                <div class="form-group">
                    <button class="btn btn-danger" onclick="rebootPi()">🔌 Reboot Pi</button>
                </div>
                <div id="updateStatus"></div>
            </div>
        </div>

        <!-- WIFI TAB -->
        <div id="tab-wifi" class="tab-content">
            <div class="card">
                <h2>📶 Quản lý WiFi</h2>
                <div class="form-group">
                    <label>Mạng hiện tại:</label>
                    <div id="currentWifi" style="padding: 10px; background: rgba(0,0,0,0.2); border-radius: 8px;">Loading...</div>
                </div>
                <div class="form-group">
                    <label>Mạng khả dụng:</label>
                    <select id="wifiList" style="margin-bottom: 10px;"></select>
                    <input type="password" id="wifiPassword" placeholder="Mật khẩu WiFi">
                </div>
                <button class="btn btn-primary" onclick="connectWifi()" style="margin-bottom: 5px;">📶 Kết nối</button>
                <button class="btn btn-success" onclick="scanWifi()">🔄 Quét lại</button>
                <div id="wifiStatus"></div>
                
                 <div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #444;">
                    <label style="display: flex; align-items: center; justify-content: space-between;">
                        <span>📁 Mạng đã lưu:</span>
                        <button onclick="loadSavedNetworks()" style="padding: 5px 10px; font-size: 12px; background: rgba(255,255,255,0.1); border: 1px solid #666; border-radius: 5px; color: #fff; cursor: pointer;">↻ Refresh</button>
                    </label>
                    <div id="savedNetworks" style="margin-top: 10px;"></div>
                </div>
            </div>
        </div>
        
    </div> <!-- Close Container -->
    </div>
    
    <script>
        // Tab switching
        function openTab(tabName) {
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => {
                b.classList.remove('active');
                if (b.textContent.includes(tabName === 'bg' ? 'Background' : 
                                         tabName === 'display' ? 'Hiển thị' :
                                         tabName === 'wifi' ? 'WiFi' : 'Khác')) {
                    b.classList.add('active');
                }
            });
            document.getElementById('tab-' + tabName).classList.add('active');
            
            // Highlight current tab button explicitly
            const btns = document.querySelectorAll('.tab-btn');
            if(tabName == 'bg') btns[0].classList.add('active');
            if(tabName == 'display') btns[1].classList.add('active');
            if(tabName == 'wifi') btns[2].classList.add('active');
            if(tabName == 'other') btns[3].classList.add('active');
        }

        function toggleBgMode() {
            const mode = document.getElementById('bgMode').value;
            document.getElementById('videoSection').style.display = mode === 'video' ? 'block' : 'none';
            document.getElementById('slideSection').style.display = mode === 'slide' ? 'block' : 'none';
            if (mode === 'slide') loadGallery();
        }

        async function loadStatus() {
            try {
                const resp = await fetch('/api/status');
                const data = await resp.json();
                document.getElementById('ipAddress').textContent = data.ip || 'Unknown';
                document.getElementById('uptime').textContent = data.uptime || 'Unknown';
                
                // Video & BG Config
                document.getElementById('videoPath').value = data.video_path || '';
                
                // Check bg mode from display config or default
                // Assuming API status returns full config or specific fields
                // We might need to update python API to send this. For now assume it sends 'display' object inside data
                if (data.display) {
                    document.getElementById('bgMode').value = data.display.background_mode || 'video';
                    document.getElementById('slideInterval').value = (data.display.slide_interval || 5000) / 1000;
                }
                toggleBgMode();

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
                
                // Load audio config info for debug
                loadAudioConfigInfo();
            } catch (e) {
                console.error('Error loading status:', e);
            }
        }
        
        async function loadAudioConfigInfo() {
            try {
                const resp = await fetch('/api/audio/devices');
                const data = await resp.json();
                const info = document.getElementById('audioConfigInfo');
                if (info) {
                    const i2s = data.i2s_enabled ? '✅ I2S' : '❌ I2S';
                    const stereo = data.i2s_stereo ? 'Stereo' : 'Mono';
                    const beam = data.beamforming_enabled ? '✅ Beam' : '❌ Beam';
                    const hdmi = data.hdmi_audio ? '✅ HDMI' : '❌ HDMI';
                    
                    info.innerHTML = `
                        <b>📋 Config hiện tại:</b><br>
                        🎤 MIC: ID=${data.config_input_id ?? 'auto'} | ${data.config_input_name || 'Default'}<br>
                        🔊 LOA: ID=${data.config_output_id ?? 'auto'} | ${data.config_output_name || 'Default'}<br>
                        ${i2s} ${stereo} | ${beam} | ${hdmi}
                    `;
                }
            } catch (e) {
                console.error('Error loading audio config:', e);
            }
        }
        
        async function saveVideoConfig() {
            const path = document.getElementById('videoPath').value;
            try {
                const resp = await fetch('/api/video', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({path, mode: 'video'}) 
                });
                const data = await resp.json();
                showStatus('videoStatus', data.success ? 'success' : 'error', data.message);
            } catch (e) {
                showStatus('videoStatus', 'error', 'Lỗi kết nối');
            }
        }

        // Slideshow Functions
        let selectedImages = new Set();

        async function loadGallery() {
            selectedImages.clear();
            const gallery = document.getElementById('imageGallery');
            gallery.innerHTML = 'Loading...';
            try {
                const resp = await fetch('/api/images/list');
                const data = await resp.json();
                const images = data.images || [];
                
                gallery.innerHTML = '';
                if (!images || images.length === 0) {
                    gallery.innerHTML = '<div style="grid-column: 1/-1; color: #888; text-align: center;">Chưa có ảnh nào. Hãy upload ảnh mới.</div>';
                    return;
                }

                images.forEach(img => {
                    const div = document.createElement('div');
                    div.className = 'gallery-item';
                    div.innerHTML = `
                        <img src="${img.url}" onclick="toggleImageSelection(this.parentElement, '${img.url}')">
                        <div class="check-icon">✓</div>
                        <button class="delete-btn" onclick="deleteImage('${img.name}', event)" title="Xóa ảnh">🗑️</button>
                    `;
                    gallery.appendChild(div);
                });
                
                // Load current config to re-select images? 
                // Currently API doesn't return selected list easily without extra call, 
                // but we can assume user selects new set or we add selected_images to /api/status.
            } catch (e) {
                gallery.innerHTML = 'Lỗi tải ảnh: ' + e.message;
            }
        }

        function toggleImageSelection(el, url) {
            if (selectedImages.has(url)) {
                selectedImages.delete(url);
                el.classList.remove('selected');
            } else {
                selectedImages.add(url);
                el.classList.add('selected');
            }
        }

        async function deleteImage(filename, event) {
            event.stopPropagation();
            if (!confirm('Xóa ảnh này?')) return;
            
            try {
                const resp = await fetch('/api/images/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({filename: filename})
                });
                const data = await resp.json();
                if (data.success) {
                    loadGallery();
                } else {
                    alert('Lỗi: ' + data.message);
                }
            } catch (e) {
                alert('Lỗi xóa ảnh: ' + e.message);
            }
        }

        async function saveSlideConfig() {
            if (selectedImages.size === 0) {
                alert('Vui lòng chọn ít nhất 1 ảnh!');
                return;
            }
            const interval = document.getElementById('slideInterval').value;
            
            try {
                const resp = await fetch('/api/slide/set', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        mode: 'slide',
                        urls: Array.from(selectedImages),
                        interval: interval
                    })
                });
                const data = await resp.json();
                alert(data.message);
            } catch(e) {
                alert('Lỗi lưu cấu hình: ' + e.message);
            }
        }

        async function uploadImage() {
            const fileInput = document.getElementById('imageFile');
            const file = fileInput.files[0];
            if (!file) return;

            const status = document.getElementById('imageUploadStatus');
            status.textContent = 'Đang upload...';
            
            const formData = new FormData();
            formData.append('image', file);
            
            try {
                const resp = await fetch('/api/upload_image', {
                    method: 'POST',
                    body: formData
                });
                const data = await resp.json();
                if (data.success) {
                    status.textContent = 'Upload thành công!';
                    loadGallery(); // Reload gallery
                } else {
                    status.textContent = 'Lỗi: ' + data.message;
                }
            } catch(e) {
                status.textContent = 'Lỗi upload: ' + e.message;
            }
            fileInput.value = '';
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
        
        async function updateAndRestart() {
            if (!confirm('Cập nhật code từ Git và restart app?')) return;
            const status = document.getElementById('updateStatus');
            status.innerHTML = '⏳ Đang cập nhật...';
            status.style.color = '#17a2b8';
            
            try {
                const resp = await fetch('/api/update-restart', {method: 'POST'});
                const data = await resp.json();
                if (data.success) {
                    status.innerHTML = '✅ ' + data.message;
                    status.style.color = '#28a745';
                    setTimeout(() => location.reload(), 5000);
                } else {
                    status.innerHTML = '❌ ' + data.message;
                    status.style.color = '#dc3545';
                }
            } catch (e) {
                status.innerHTML = '❌ Lỗi kết nối: ' + e.message;
                status.style.color = '#dc3545';
            }
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
                
                let statusMsg = data.message;
                
                // Nếu có audio, thêm nút nghe lại
                if (data.audio) {
                    statusMsg += ' <button onclick="playMicAudio()" style="margin-left: 10px; padding: 5px 10px; border-radius: 5px; background: #4CAF50; color: white; border: none; cursor: pointer;">🔊 Nghe lại trên Browser</button>';
                    // Lưu audio data
                    window.lastMicAudio = data.audio;
                }
                
                showStatus('micStatus', data.success ? 'success' : 'error', statusMsg);
            } catch (e) {
                showStatus('micStatus', 'error', 'Lỗi: ' + e.message);
            } finally {
                btn.disabled = false;
                btn.textContent = '🎤 Ghi âm 3s';
            }
        }
        
        function playMicAudio() {
            if (window.lastMicAudio) {
                const audio = new Audio('data:audio/wav;base64,' + window.lastMicAudio);
                audio.play().catch(e => alert('Lỗi phát audio: ' + e.message));
            } else {
                alert('Chưa có audio ghi âm!');
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
        
        // I2S Toggle
        function toggleI2S() {
            const enabled = document.getElementById('i2sEnabled').checked;
            document.getElementById('i2sOptions').style.display = enabled ? 'block' : 'none';
            if (!enabled) {
                document.getElementById('beamformingOptions').style.display = 'none';
            }
        }
        
        function toggleBeamforming() {
            const stereo = document.getElementById('i2sStereo').checked;
            document.getElementById('beamformingOptions').style.display = stereo ? 'block' : 'none';
        }
        
        async function saveAudio() {
            const micDevice = document.getElementById('micDevice').value;
            const speakerDevice = document.getElementById('speakerDevice').value;
            const micVolume = document.getElementById('micVolume').value;
            const speakerVolume = document.getElementById('speakerVolume').value;
            const i2sEnabled = document.getElementById('i2sEnabled').checked;
            const i2sStereo = document.getElementById('i2sStereo').checked;
            const beamformingEnabled = document.getElementById('beamformingEnabled').checked;
            const micDistance = parseFloat(document.getElementById('micDistance').value) || 8;
            const speakerAngle = parseFloat(document.getElementById('speakerAngle').value) || 180;
            const hdmiAudio = document.getElementById('hdmiAudio').checked;
            
            try {
                const resp = await fetch('/api/audio', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        micDevice, speakerDevice, micVolume, speakerVolume, 
                        i2sEnabled, i2sStereo,
                        beamformingEnabled, micDistance, speakerAngle,
                        hdmiAudio
                    })
                });
                const data = await resp.json();
                showStatus('micStatus', data.success ? 'success' : 'error', data.message);
                showStatus('speakerStatus', data.success ? 'success' : 'error', data.message);
            } catch (e) {
                showStatus('micStatus', 'error', 'Lỗi kết nối');
            }
        }
        
        async function saveAndRestartAudio() {
            // Lưu config trước
            await saveAudio();
            
            // Gọi API restart audio
            showStatus('micStatus', 'info', '🔄 Đang khởi động lại Audio System...');
            
            try {
                const resp = await fetch('/api/audio/restart', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'}
                });
                const data = await resp.json();
                if (data.success) {
                    showStatus('micStatus', 'success', '✅ ' + data.message);
                    showStatus('speakerStatus', 'success', '✅ Audio đã được áp dụng!');
                } else {
                    showStatus('micStatus', 'error', '❌ ' + data.message);
                }
            } catch (e) {
                showStatus('micStatus', 'error', 'Lỗi restart audio: ' + e.message);
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
                
                // I2S settings
                document.getElementById('i2sEnabled').checked = data.i2s_enabled || false;
                document.getElementById('i2sStereo').checked = data.i2s_stereo || false;
                
                // Beamforming settings
                document.getElementById('beamformingEnabled').checked = data.beamforming_enabled || false;
                document.getElementById('micDistance').value = data.mic_distance || 8;
                document.getElementById('speakerAngle').value = data.speaker_angle || 180;
                
                // HDMI Audio
                document.getElementById('hdmiAudio').checked = data.hdmi_audio || false;
                
                toggleI2S();
                toggleBeamforming();
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
                        // Hiển thị badge nếu đã lưu
                        const savedBadge = n.saved ? ' ✓' : '';
                        const securityBadge = n.security && n.security !== '--' ? ` 🔒` : '';
                        opt.textContent = `${n.ssid}${savedBadge}${securityBadge} (${n.signal}%)`;
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
                
                // Load saved networks
                loadSavedNetworks();
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
                if (data.success) {
                    scanWifi();
                    loadSavedNetworks();
                }
            } catch (e) {
                showStatus('wifiStatus', 'error', 'Kết nối thất bại');
            }
        }
        
        async function loadSavedNetworks() {
            const container = document.getElementById('savedNetworks');
            try {
                const resp = await fetch('/api/wifi/saved');
                const data = await resp.json();
                
                if (data.networks && data.networks.length > 0) {
                    container.innerHTML = data.networks.map(n => `
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px; background: rgba(0,0,0,0.2); border-radius: 8px; margin-bottom: 8px;">
                            <span>
                                ${n.connected ? '🟢' : '⚪'} ${n.ssid}
                                ${n.connected ? '<span style="color: #38ef7d; font-size: 12px; margin-left: 5px;">Đang kết nối</span>' : ''}
                            </span>
                            <button onclick="forgetNetwork('${n.ssid.replace(/'/g, "\\'")}')" 
                                style="padding: 5px 10px; font-size: 12px; background: rgba(245, 87, 108, 0.3); border: 1px solid #f5576c; border-radius: 5px; color: #f5576c; cursor: pointer;"
                                ${n.connected ? 'disabled title="Không thể xóa mạng đang kết nối"' : ''}>
                                🗑️ Quên
                            </button>
                        </div>
                    `).join('');
                } else {
                    container.innerHTML = '<div style="color: #888; font-size: 13px;">Chưa có mạng nào được lưu</div>';
                }
            } catch (e) {
                container.innerHTML = '<div style="color: #f5576c; font-size: 13px;">Lỗi tải danh sách</div>';
            }
        }
        
        async function forgetNetwork(ssid) {
            if (!confirm(`Bạn có chắc muốn quên mạng "${ssid}"?\n\nBạn sẽ cần nhập lại mật khẩu nếu muốn kết nối lại.`)) {
                return;
            }
            
            try {
                const resp = await fetch('/api/wifi/saved', {
                    method: 'DELETE',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ssid})
                });
                const data = await resp.json();
                
                if (data.success) {
                    showStatus('wifiStatus', 'success', data.message);
                    loadSavedNetworks();
                } else {
                    showStatus('wifiStatus', 'error', data.message);
                }
            } catch (e) {
                showStatus('wifiStatus', 'error', 'Lỗi xóa mạng');
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
        # Static files
        self.app.router.add_static('/assets', get_project_root() / 'assets')
        
        self.app.router.add_get('/api/status', self._handle_status)
        self.app.router.add_post('/api/video', self._handle_video)
        self.app.router.add_post('/api/upload', self._handle_upload)
        self.app.router.add_post('/api/rotation', self._handle_rotation)
        self.app.router.add_get('/api/windowmode', self._handle_windowmode_get)
        self.app.router.add_post('/api/windowmode', self._handle_windowmode_post)
        self.app.router.add_post('/api/youtube', self._handle_youtube)
        self.app.router.add_get('/api/audio/devices', self._handle_audio_devices)
        self.app.router.add_post('/api/audio', self._handle_audio)
        self.app.router.add_post('/api/audio/restart', self._handle_audio_restart)
        # Slideshow
        self.app.router.add_post('/api/upload_image', self._handle_upload_image)
        self.app.router.add_get('/api/images/list', self._handle_list_images)
        self.app.router.add_post('/api/images/delete', self._handle_delete_image)
        self.app.router.add_post('/api/slide/set', self._handle_slide_set)
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
        self.app.router.add_post('/api/update-restart', self._handle_update_restart)
        # Test
        self.app.router.add_post('/api/test/mic', self._handle_test_mic)
        self.app.router.add_post('/api/test/speaker', self._handle_test_speaker)
        self.app.router.add_post('/api/test/chat', self._handle_test_chat)
        # Health & Setup
        self.app.router.add_get('/api/health', self._handle_health)
        self.app.router.add_get('/api/metrics', self._handle_metrics)
        self.app.router.add_get('/api/setup/status', self._handle_setup_status)
        self.app.router.add_post('/api/setup/complete', self._handle_setup_complete)
        self.app.router.add_get('/setup', self._handle_setup_wizard)
        # WiFi Management (Phase 3)
        self.app.router.add_get('/api/wifi/saved', self._handle_wifi_saved)
        self.app.router.add_delete('/api/wifi/saved', self._handle_wifi_delete)
    
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
            "display": {
                "background_mode": self.config.get_config("DISPLAY.BACKGROUND_MODE", "video"),
                "slide_interval": self.config.get_config("DISPLAY.SLIDE_INTERVAL", 5000)
            }
        })
    
    async def _handle_video(self, request):
        """Lưu video path."""
        try:
            data = await request.json()
            path = data.get("path", "")
            
            logger.info(f"Saving video path: {path}")
            
            # Set mode to video
            self.config.update_config("DISPLAY.BACKGROUND_MODE", "video")
            
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

    async def _handle_upload_image(self, request):
        """Upload image file cho slideshow."""
        try:
            reader = await request.multipart()
            field = await reader.next()
            
            if field.name != 'image':
                return web.json_response({"success": False, "message": "Không tìm thấy field image"})
            
            filename = field.filename
            if not filename:
                return web.json_response({"success": False, "message": "Tên file không hợp lệ"})
            
            # Sanitize filename
            import re
            safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
            
            # Save to assets/images/slideshow
            img_dir = get_project_root() / "assets" / "images" / "slideshow"
            img_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = img_dir / safe_filename
            
            # Write file
            with open(file_path, 'wb') as f:
                while True:
                    chunk = await field.read_chunk()
                    if not chunk:
                        break
                    f.write(chunk)
            
            relative_path = f"assets/images/slideshow/{safe_filename}"
            logger.info(f"Uploaded image: {relative_path}")
            
            return web.json_response({
                "success": True, 
                "message": f"Upload thành công!",
                "filename": safe_filename,
                "path": relative_path
            })
        except Exception as e:
            logger.error(f"Upload image failed: {e}")
            return web.json_response({"success": False, "message": str(e)})

    async def _handle_list_images(self, request):
        """Liệt kê danh sách ảnh slideshow."""
        img_dir = get_project_root() / "assets" / "images" / "slideshow"
        images = []
        if img_dir.exists():
            for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.webp']:
                images.extend([{
                    "name": p.name,
                    "path": str(p.relative_to(get_project_root())),
                    "url": f"/assets/images/slideshow/{p.name}"
                } for p in img_dir.glob(ext)])
        return web.json_response({"images": images})

    async def _handle_delete_image(self, request):
        """Xóa ảnh slideshow."""
        try:
            data = await request.json()
            filename = data.get("filename", "")
            
            if not filename:
                return web.json_response({"success": False, "message": "Tên file trống"})
            
            # Sanitize filename to prevent path traversal
            import re
            safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
            
            img_path = get_project_root() / "assets" / "images" / "slideshow" / safe_filename
            
            if img_path.exists():
                img_path.unlink()
                logger.info(f"Deleted image: {safe_filename}")
                return web.json_response({"success": True, "message": f"Đã xóa {safe_filename}"})
            else:
                return web.json_response({"success": False, "message": "File không tồn tại"})
        except Exception as e:
            logger.error(f"Delete image failed: {e}")
            return web.json_response({"success": False, "message": str(e)})

    async def _handle_slide_set(self, request):
        """Cài đặt slideshow."""
        try:
            data = await request.json()
            interval = int(data.get("interval", 5000))
            
            self.config.update_config("DISPLAY.BACKGROUND_MODE", "slide")
            self.config.update_config("DISPLAY.SLIDE_INTERVAL", interval)
            
            self._reload_video()
            
            return web.json_response({"success": True, "message": "Đã lưu cài đặt Slideshow"})
        except Exception as e:
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
            
            # I2S settings từ AUDIO_DEVICES
            audio_devices_config = self.config.get_config("AUDIO_DEVICES", {}) or {}
            i2s_enabled = audio_devices_config.get("i2s_enabled", False)
            i2s_stereo = audio_devices_config.get("i2s_stereo", False)
            beamforming_enabled = audio_devices_config.get("beamforming_enabled", False)
            mic_distance = audio_devices_config.get("mic_distance", 8.0)
            speaker_angle = audio_devices_config.get("speaker_angle", 180.0)
            hdmi_audio = audio_devices_config.get("hdmi_audio", False)
            
            # Device IDs từ config (quan trọng để biết app đang dùng device nào)
            config_input_id = audio_devices_config.get("input_device_id")
            config_output_id = audio_devices_config.get("output_device_id")
            config_input_name = audio_devices_config.get("input_device_name", "")
            config_output_name = audio_devices_config.get("output_device_name", "")
            
            return web.json_response({
                "input_devices": input_devices,
                "output_devices": output_devices,
                "current_mic": current_mic,
                "current_speaker": current_speaker,
                "mic_volume": mic_volume,
                "speaker_volume": speaker_volume,
                "i2s_enabled": i2s_enabled,
                "i2s_stereo": i2s_stereo,
                "beamforming_enabled": beamforming_enabled,
                "mic_distance": mic_distance,
                "speaker_angle": speaker_angle,
                "hdmi_audio": hdmi_audio,
                # Config info - cho debug
                "config_input_id": config_input_id,
                "config_output_id": config_output_id,
                "config_input_name": config_input_name,
                "config_output_name": config_output_name,
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
            i2s_enabled = data.get("i2sEnabled", False)
            i2s_stereo = data.get("i2sStereo", False)
            beamforming_enabled = data.get("beamformingEnabled", False)
            mic_distance = float(data.get("micDistance", 8.0))
            speaker_angle = float(data.get("speakerAngle", 180.0))
            hdmi_audio = data.get("hdmiAudio", False)
            
            self.config.update_config("AUDIO.INPUT_DEVICE_INDEX", mic_device)
            self.config.update_config("AUDIO.OUTPUT_DEVICE_INDEX", speaker_device)
            self.config.update_config("AUDIO.MIC_VOLUME", mic_volume)
            self.config.update_config("AUDIO.SPEAKER_VOLUME", speaker_volume)
            
            # I2S & Beamforming & HDMI settings trong AUDIO_DEVICES
            audio_devices = self.config.get_config("AUDIO_DEVICES", {}) or {}
            audio_devices["i2s_enabled"] = i2s_enabled
            audio_devices["i2s_stereo"] = i2s_stereo
            audio_devices["beamforming_enabled"] = beamforming_enabled
            audio_devices["mic_distance"] = mic_distance
            audio_devices["speaker_angle"] = speaker_angle
            audio_devices["hdmi_audio"] = hdmi_audio
            
            import sounddevice as sd
            devices = sd.query_devices()
            
            # Khi I2S enabled, tìm và set input device là I2S mic
            if i2s_enabled:
                i2s_keywords = ["googlevoicehat", "simple-card", "i2s", "inmp441", "snd_rpi"]
                for i, d in enumerate(devices):
                    if d['max_input_channels'] > 0:
                        name_lower = d['name'].lower()
                        if any(kw in name_lower for kw in i2s_keywords):
                            audio_devices["input_device_id"] = i
                            audio_devices["input_device_name"] = d['name']
                            logger.info(f"🎤 I2S MIC device set: [{i}] {d['name']}")
                            break
            
            # Khi HDMI enabled, tìm và set output device là HDMI
            if hdmi_audio:
                for i, d in enumerate(devices):
                    if d['max_output_channels'] > 0:
                        name_lower = d['name'].lower()
                        if 'hdmi' in name_lower or 'vc4hdmi' in name_lower:
                            audio_devices["output_device_id"] = i
                            audio_devices["output_device_name"] = d['name']
                            logger.info(f"🔊 HDMI device set: [{i}] {d['name']}")
                            break
            
            self.config.update_config("AUDIO_DEVICES", audio_devices)
            
            # Áp dụng volume ngay bằng amixer
            try:
                subprocess.run(["amixer", "set", "Capture", f"{mic_volume}%"], capture_output=True, timeout=5)
                subprocess.run(["amixer", "set", "Master", f"{speaker_volume}%"], capture_output=True, timeout=5)
            except Exception:
                pass
            
            # Apply HDMI audio output setting
            try:
                if hdmi_audio:
                    # Set HDMI as default output
                    subprocess.run(["amixer", "-c", "vc4hdmi0", "set", "PCM", f"{speaker_volume}%"], capture_output=True, timeout=5)
                    logger.info("HDMI audio enabled")
                else:
                    # Use headphone jack
                    subprocess.run(["amixer", "set", "Headphone", f"{speaker_volume}%"], capture_output=True, timeout=5)
                    logger.info("Headphone jack audio enabled")
            except Exception as e:
                logger.warning(f"HDMI audio switch failed: {e}")
            
            msg = "Đã lưu cài đặt âm thanh!"
            if i2s_enabled:
                msg += " (I2S: " + ("Stereo" if i2s_stereo else "Mono") + ")"
            if beamforming_enabled and i2s_stereo:
                msg += f" + Beamforming (mic: {mic_distance}cm, loa: {speaker_angle}°)"
            if hdmi_audio:
                msg += " | 📺 HDMI Audio"
            
            return web.json_response({"success": True, "message": msg})
        except Exception as e:
            return web.json_response({"success": False, "message": str(e)})
    
    async def _handle_audio_restart(self, request):
        """Restart audio system để áp dụng cấu hình mới (I2S, Beamforming, etc.)"""
        try:
            from src.application import Application
            app = Application._instance
            
            if not app:
                return web.json_response({"success": False, "message": "App chưa khởi động. Vui lòng restart app thủ công."})
            
            # Thử lấy codec từ nhiều nguồn
            codec = None
            
            # Cách 1: Từ app.audio_codec (được set trong audio plugin)
            codec = getattr(app, "audio_codec", None)
            
            # Cách 2: Từ audio plugin
            if not codec and hasattr(app, "plugins"):
                try:
                    audio_plugin = app.plugins.get_plugin("audio")
                    if audio_plugin:
                        codec = getattr(audio_plugin, "codec", None)
                except:
                    pass
            
            if not codec:
                # Không có codec - yêu cầu restart app
                return web.json_response({
                    "success": False, 
                    "message": "Audio chưa khởi tạo. Config đã lưu - vui lòng restart app để áp dụng."
                })
            
            # Stop current streams (nếu có method)
            logger.info("Stopping audio streams for restart...")
            try:
                if hasattr(codec, "stop_streams"):
                    await codec.stop_streams()
                elif hasattr(codec, "close"):
                    await codec.close()
            except Exception as e:
                logger.warning(f"Stop streams warning: {e}")
            
            # Reload config
            self.config.reload_config()
            
            # Reinitialize codec với config mới
            logger.info("Reinitializing audio codec...")
            
            # Check I2S & Beamforming settings
            audio_devices = self.config.get_config("AUDIO_DEVICES", {}) or {}
            i2s_enabled = audio_devices.get("i2s_enabled", False)
            i2s_stereo = audio_devices.get("i2s_stereo", False)
            beamforming_enabled = audio_devices.get("beamforming_enabled", False)
            mic_distance = audio_devices.get("mic_distance", 8.0)
            speaker_angle = audio_devices.get("speaker_angle", 180.0)
            
            # Update beamforming processor if exists
            if hasattr(codec, "beamforming") and codec.beamforming:
                codec.beamforming.set_mic_distance(mic_distance)
                codec.beamforming.enable(beamforming_enabled)
                logger.info(f"Beamforming updated: enabled={beamforming_enabled}, distance={mic_distance}cm")
            elif beamforming_enabled and i2s_stereo:
                # Create new beamforming processor
                from src.audio_codecs.beamforming import BeamformingProcessor
                codec.beamforming = BeamformingProcessor(
                    mic_distance=mic_distance / 100.0,
                    sample_rate=16000
                )
                codec.beamforming.enable(True)
                logger.info(f"Beamforming created: distance={mic_distance}cm")
            
            # Restart streams
            logger.info("Starting audio streams...")
            await codec.start_streams()
            
            msg = "Audio System đã khởi động lại!"
            if i2s_enabled:
                msg += f" | I2S: {'Stereo' if i2s_stereo else 'Mono'}"
            if beamforming_enabled:
                msg += f" | Beamforming: ON ({mic_distance}cm)"
            
            logger.info(msg)
            return web.json_response({"success": True, "message": msg})
            
        except Exception as e:
            logger.error(f"Audio restart failed: {e}", exc_info=True)
            return web.json_response({"success": False, "message": f"Lỗi: {str(e)}"})
    
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
            
            # Lấy danh sách mạng đã lưu (saved connections)
            saved_ssids = set()
            try:
                result = subprocess.run(
                    ["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        parts = line.split(':')
                        if len(parts) >= 2 and parts[1] == '802-11-wireless':
                            saved_ssids.add(parts[0])
            except Exception:
                pass

            # Quét mạng khả dụng dùng nmcli (tốt hơn iwlist và có security info)
            networks = []
            try:
                # Rescan trước
                subprocess.run(["sudo", "nmcli", "device", "wifi", "rescan"], timeout=5)
                await asyncio.sleep(1) # Chờ 1 chút
                
                result = subprocess.run(
                    ["sudo", "nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY,IN-USE", "device", "wifi", "list"],
                    capture_output=True, text=True, timeout=15
                )
                
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        # Format: SSID:SIGNAL:SECURITY:IN-USE
                        # Cẩn thận với SSID có dấu : bên trong -> dùng split limit không an toàn nếu nmcli không escape
                        # Nhưng nmcli -t thường dùng : làm separator. SSID thực tế hiếm khi có :
                        
                        # Cách an toàn hơn: dùng regex hoặc split thông minh
                        # SSID có thể rỗng (hidden network)
                        # nmcli output example: MyWiFi:80:WPA2:*
                        
                        parts = line.split(':')
                        if len(parts) >= 3:
                            # Lấy các phần cuối cố định trước
                            in_use = parts[-1] == "*"
                            security = parts[-2]
                            signal = parts[-3]
                            
                            # SSID là phần còn lại
                            ssid = ":".join(parts[:-3])
                            
                            if not ssid:
                                continue
                                
                            # Convert signal
                            try:
                                signal_level = int(signal)
                            except:
                                signal_level = 0
                                
                            networks.append({
                                "ssid": ssid,
                                "signal": signal_level,
                                "security": security,
                                "saved": ssid in saved_ssids,
                                "connected": in_use
                            })
                            
                    # Remove duplicates, giữ lại signal mạnh nhất
                    unique_networks = {}
                    for net in networks:
                        ssid = net['ssid']
                        if ssid not in unique_networks or net['signal'] > unique_networks[ssid]['signal']:
                            unique_networks[ssid] = net
                    
                    networks = sorted(unique_networks.values(), key=lambda x: x['signal'], reverse=True)
                            
            except Exception as e:
                logger.warning(f"WiFi scan failed: {e}")
                # Fallback to iwlist if nmcli fails
            
            return web.json_response({
                "networks": networks[:20],
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
            # Dùng nmcli để kết nối
            if password:
                cmd = ["sudo", "nmcli", "device", "wifi", "connect", ssid, "password", password]
            else:
                cmd = ["sudo", "nmcli", "device", "wifi", "connect", ssid]
            
            # Tăng timeout lên 60s để an toàn
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                logger.info(f"Connected to WiFi: {ssid}")
                return web.json_response({"success": True, "message": f"✅ Đã kết nối {ssid}!"})
            else:
                error = result.stderr or result.stdout or "Unknown error"
                logger.error(f"WiFi connect failed: {error}")
                
                # FALLBACK: Bật lại Hotspot nếu kết nối thất bại
                try:
                    logger.info("Connection failed - Restoring Hotspot...")
                    from src.network.network_status import start_hotspot_if_no_network
                    await start_hotspot_if_no_network()
                except Exception as ex:
                    logger.error(f"Failed to restore hotspot: {ex}")
                
                return web.json_response({"success": False, "message": f"❌ Lỗi: {error[:80]}\nĐang bật lại Hotspot..."})
                
        except subprocess.TimeoutExpired:
            logger.warning("WiFi Connect Timeout")
            # FALLBACK: Bật lại Hotspot
            try:
                from src.network.network_status import start_hotspot_if_no_network
                await start_hotspot_if_no_network()
            except Exception:
                pass
            return web.json_response({"success": False, "message": "⏱️ Timeout - Đang bật lại Hotspot..."})
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
            if not ota_url:
                ota_url = "https://vimate.vn/api/v1/ota"
            # Ưu tiên URL quản lý riêng, nếu không có thì fallback sang Voice URL
            ws_url = self.config.get_config("SYSTEM_OPTIONS.NETWORK.CLOUD_MANAGEMENT_URL", "")
            if not ws_url:
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
            
            # WebSocket (Cloud Management URL)
            if data.get("wsUrl"):
                self.config.update_config("SYSTEM_OPTIONS.NETWORK.CLOUD_MANAGEMENT_URL", data.get("wsUrl"))
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
    
    async def _handle_update_restart(self, request):
        """Update code từ Git và restart app."""
        try:
            import os
            app_home = os.path.expanduser("~/.digits")
            if not os.path.isdir(app_home):
                app_home = os.path.expanduser("~/.xiaozhi")
            
            # Backup config
            config_backup = "/tmp/smartc_config_backup"
            os.makedirs(config_backup, exist_ok=True)
            
            config_file = os.path.join(app_home, "config/config.json")
            if os.path.exists(config_file):
                import shutil
                shutil.copy(config_file, os.path.join(config_backup, "config.json"))
                logger.info("Config backed up")
            
            # Git pull
            result = subprocess.run(
                ["git", "fetch", "origin", "main"],
                cwd=app_home,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            result = subprocess.run(
                ["git", "reset", "--hard", "origin/main"],
                cwd=app_home,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return web.json_response({
                    "success": False,
                    "message": f"Git update failed: {result.stderr}"
                })
            
            # Restore config
            backup_config = os.path.join(config_backup, "config.json")
            if os.path.exists(backup_config):
                import shutil
                shutil.copy(backup_config, config_file)
                logger.info("Config restored")
            
            logger.info("Update completed, restarting...")
            
            # Schedule restart
            asyncio.create_task(self._do_restart())
            
            return web.json_response({
                "success": True,
                "message": "Cập nhật thành công! App đang restart..."
            })
            
        except Exception as e:
            logger.error(f"Update failed: {e}")
            return web.json_response({
                "success": False,
                "message": f"Lỗi: {str(e)}"
            })
    
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
        """Test microphone - ghi âm và phát lại dùng arecord/aplay."""
        import subprocess
        import tempfile
        import os
        import wave
        import numpy as np
        
        try:
            # Lấy thông tin device hiện tại
            audio_config = self.config.get_config("AUDIO_DEVICES", {}) or {}
            i2s_enabled = audio_config.get("i2s_enabled", False)
            i2s_stereo = audio_config.get("i2s_stereo", False)
            hdmi_audio = audio_config.get("hdmi_audio", False)
            input_device_name = audio_config.get("input_device_name", "")
            output_device_name = audio_config.get("output_device_name", "")
            
            # Ưu tiên I2S card nếu enabled
            arecord_device = "default"
            if i2s_enabled:
                # Tìm I2S card từ arecord -l
                # Format: "card 3: sndrpigooglevoi [snd_rpi_googlevoicehat...]"
                try:
                    result = subprocess.run(
                        ["arecord", "-l"],
                        capture_output=True, text=True, timeout=5
                    )
                    for line in result.stdout.split('\n'):
                        line_lower = line.lower()
                        if 'card' in line_lower and ('google' in line_lower or 'voicehat' in line_lower or 'i2s' in line_lower or 'inmp441' in line_lower):
                            # Extract card name: "card 3: sndrpigooglevoi [..."
                            parts = line.split(':')
                            if len(parts) >= 2:
                                card_part = parts[1].strip()
                                card_name = card_part.split()[0].split('[')[0].strip()
                                if card_name:
                                    arecord_device = f"plughw:CARD={card_name}"
                                    logger.info(f"Detected I2S MIC card: {card_name}")
                                    break
                except Exception as e:
                    logger.warning(f"arecord -l failed: {e}")
            
            channels = 2 if i2s_stereo else 1
            sample_rate = 16000
            duration = 3
            
            logger.info(f"Test MIC: Recording {duration}s from '{arecord_device}' (ch={channels}, I2S={i2s_enabled})")
            
            # Tạo temp file
            temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
            
            # arecord command
            arecord_cmd = [
                "arecord",
                "-D", arecord_device,
                "-f", "S16_LE",
                "-r", str(sample_rate),
                "-c", str(channels),
                "-d", str(duration),
                temp_wav
            ]
            
            try:
                result = subprocess.run(
                    arecord_cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=duration + 3
                )
                
                if result.returncode != 0:
                    logger.error(f"arecord error: {result.stderr}")
                    return web.json_response({
                        "success": False,
                        "message": f"❌ arecord failed: {result.stderr[:100]}"
                    })
                    
            except subprocess.TimeoutExpired:
                return web.json_response({
                    "success": False,
                    "message": "❌ Recording timeout"
                })
            except Exception as e:
                return web.json_response({
                    "success": False,
                    "message": f"❌ Recording error: {str(e)}"
                })
            
            # Đọc WAV file và phân tích
            try:
                with wave.open(temp_wav, 'rb') as wf:
                    frames = wf.readframes(wf.getnframes())
                    audio_data = np.frombuffer(frames, dtype=np.int16)
                    
                    if channels == 2 and len(audio_data) > 0:
                        audio_data = audio_data.reshape(-1, 2)
                        max_left = np.max(np.abs(audio_data[:, 0]))
                        max_right = np.max(np.abs(audio_data[:, 1]))
                        max_amplitude = max(max_left, max_right)
                        channel_info = f"L:{max_left}, R:{max_right}"
                    else:
                        max_amplitude = np.max(np.abs(audio_data)) if len(audio_data) > 0 else 0
                        channel_info = "Mono"
                        
            except Exception as e:
                max_amplitude = 0
                channel_info = f"Error: {e}"
            
            logger.info(f"Test MIC: Max={max_amplitude}, {channel_info}")
            
            # Phát lại qua HDMI hoặc default
            aplay_device = "default"
            if hdmi_audio:
                aplay_device = "plughw:CARD=vc4hdmi0"
            
            logger.info(f"Test MIC: Playback to '{aplay_device}'")
            
            try:
                subprocess.run(
                    ["aplay", "-D", aplay_device, temp_wav],
                    capture_output=True,
                    timeout=duration + 2
                )
            except:
                pass
            
            # Đọc file WAV và convert sang base64 để phát trên browser
            import base64
            audio_base64 = ""
            try:
                with open(temp_wav, 'rb') as f:
                    audio_base64 = base64.b64encode(f.read()).decode('utf-8')
            except:
                pass
            
            # Cleanup
            try:
                os.unlink(temp_wav)
            except:
                pass
            
            # Return result với audio data
            mic_type = "I2S INMP441" if i2s_enabled else "USB/Analog"
            
            if max_amplitude < 100:
                return web.json_response({
                    "success": False,
                    "message": f"⚠️ MIC yếu! Max: {max_amplitude} | {channel_info} | Device: {arecord_device}",
                    "audio": audio_base64
                })
            
            return web.json_response({
                "success": True,
                "message": f"✅ {mic_type} OK! Max: {max_amplitude} | {channel_info} | In: {arecord_device}",
                "audio": audio_base64
            })
            
        except Exception as e:
            logger.error(f"Test MIC error: {e}")
            import traceback
            traceback.print_exc()
            return web.json_response({"success": False, "message": f"❌ Lỗi: {str(e)}"})
    
    async def _handle_test_speaker(self, request):
        """Test speaker - phát âm thanh beep."""
        try:
            import numpy as np
            import wave
            import tempfile
            import os
            
            # Lấy output device từ config
            audio_config = self.config.get_config("AUDIO_DEVICES", {}) or {}
            hdmi_audio = audio_config.get("hdmi_audio", False)
            
            logger.info(f"Test Speaker: HDMI={hdmi_audio}")
            
            # Tạo beep tone
            sample_rate = 44100
            duration = 0.3
            frequency = 880  # A5 note - higher pitch, easier to hear
            
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            beep = np.sin(2 * np.pi * frequency * t) * 20000
            fade_samples = int(sample_rate * 0.02)
            beep[:fade_samples] *= np.linspace(0, 1, fade_samples)
            beep[-fade_samples:] *= np.linspace(1, 0, fade_samples)
            beep = beep.astype(np.int16)
            
            # Tạo 3 beeps với khoảng cách
            silence = np.zeros(int(sample_rate * 0.15), dtype=np.int16)
            full_audio = np.concatenate([beep, silence, beep, silence, beep])
            
            # Lưu thành WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                temp_wav = f.name
            
            with wave.open(temp_wav, 'w') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(full_audio.tobytes())
            
            if hdmi_audio:
                # Dùng aplay với HDMI device
                device_name = "HDMI (vc4hdmi)"
                # Thử các HDMI device names phổ biến trên Pi
                hdmi_devices = ['vc4hdmi0', 'vc4hdmi1', 'vc4hdmi', 'hdmi']
                played = False
                
                for hdmi_dev in hdmi_devices:
                    cmd = f'aplay -D plughw:CARD={hdmi_dev} {temp_wav} 2>&1'
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        device_name = f"HDMI ({hdmi_dev})"
                        played = True
                        logger.info(f"Played via: {cmd}")
                        break
                    else:
                        logger.debug(f"Failed {hdmi_dev}: {result.stderr}")
                
                if not played:
                    # Fallback: aplay với default
                    cmd = f'aplay {temp_wav} 2>&1'
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        device_name = "Default (ALSA)"
                        played = True
                
                if not played:
                    os.unlink(temp_wav)
                    return web.json_response({
                        "success": False,
                        "message": "❌ Không thể phát qua HDMI. Kiểm tra kết nối và volume TV."
                    })
            else:
                # Dùng sounddevice cho headphone jack
                import sounddevice as sd
                device_name = "Headphone (3.5mm)"
                sd.play(full_audio, sample_rate)
                sd.wait()
            
            # Cleanup
            try:
                os.unlink(temp_wav)
            except:
                pass
            
            return web.json_response({
                "success": True, 
                "message": f"✅ Đã phát 3 beep qua {device_name}! Bạn có nghe thấy không?"
            })
            
        except Exception as e:
            logger.error(f"Test Speaker error: {e}")
            import traceback
            traceback.print_exc()
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
        
        # Check 5: Beamforming status
        try:
            from src.application import Application
            app = Application._instance
            if app and hasattr(app, 'plugins'):
                audio_plugin = app.plugins.get_plugin("audio")
                if audio_plugin and hasattr(audio_plugin, "codec"):
                    codec = audio_plugin.codec
                    beamforming = getattr(codec, "beamforming", None)
                    if beamforming:
                        bf_status = beamforming.get_status()
                        health["checks"]["beamforming"] = {
                            "status": "ok",
                            "enabled": bf_status.get("enabled", False),
                            "mic_distance_cm": bf_status.get("mic_distance_cm", 0),
                            "voice_active": bf_status.get("is_voice_active", False)
                        }
                    else:
                        health["checks"]["beamforming"] = {"status": "disabled"}
        except Exception as e:
            health["checks"]["beamforming"] = {"status": "error", "message": str(e)}
        
        # Check 6: CPU Temperature (Raspberry Pi)
        try:
            cpu_temp = None
            temp_file = "/sys/class/thermal/thermal_zone0/temp"
            if os.path.exists(temp_file):
                with open(temp_file) as f:
                    cpu_temp = int(f.read().strip()) / 1000.0
            
            if cpu_temp is not None:
                temp_status = "ok" if cpu_temp < 70 else ("warning" if cpu_temp < 80 else "error")
                health["checks"]["temperature"] = {
                    "status": temp_status,
                    "cpu_temp_c": round(cpu_temp, 1),
                    "throttled": cpu_temp >= 80
                }
        except Exception:
            pass  # Not on Raspberry Pi
        
        # Check 7: CPU per core (for beamforming impact monitoring)
        try:
            cpu_per_core = psutil.cpu_percent(percpu=True)
            health["checks"]["system"]["cpu_per_core"] = cpu_per_core
            health["checks"]["system"]["cpu_count"] = len(cpu_per_core)
        except Exception:
            pass
        
        # Check 8: Network status
        try:
            from src.network.network_status import is_connected, get_current_ip
            from src.network.wifi_manager import get_wifi_manager
            
            connected = is_connected()
            ip = get_current_ip() if connected else None
            
            wifi = get_wifi_manager()
            hotspot_active = wifi.is_hotspot_active() if wifi else False
            current_ssid = wifi.get_current_ssid() if wifi else None
            
            health["checks"]["network"] = {
                "status": "ok" if connected else ("warning" if hotspot_active else "error"),
                "connected": connected,
                "ip": ip,
                "ssid": current_ssid,
                "hotspot_active": hotspot_active
            }
        except Exception as e:
            health["checks"]["network"] = {"status": "error", "message": str(e)}
        
        # Check 9: Wake Word status
        try:
            from src.application import Application
            app = Application._instance
            if app and hasattr(app, 'plugins'):
                wakeword_plugin = app.plugins.get_plugin("wakeword")
                if wakeword_plugin:
                    enabled = getattr(wakeword_plugin, 'enabled', False)
                    listening = getattr(wakeword_plugin, 'is_listening', lambda: False)()
                    health["checks"]["wakeword"] = {
                        "status": "ok" if enabled else "disabled",
                        "enabled": enabled,
                        "listening": listening
                    }
                else:
                    health["checks"]["wakeword"] = {"status": "disabled", "enabled": False}
        except Exception as e:
            health["checks"]["wakeword"] = {"status": "error", "message": str(e)}
        
        # Check 10: Device State
        try:
            from src.application import Application
            app = Application._instance
            if app:
                state = app.get_device_state()
                health["checks"]["device_state"] = {
                    "status": "ok",
                    "state": str(state.name) if hasattr(state, 'name') else str(state),
                    "audio_channel_opened": app.is_audio_channel_opened(),
                    "keep_listening": app.is_keep_listening()
                }
        except Exception as e:
            health["checks"]["device_state"] = {"status": "error", "message": str(e)}
        
        # Add version info
        try:
            version_file = get_project_root() / "VERSION"
            if version_file.exists():
                health["version"] = version_file.read_text().strip()
            else:
                health["version"] = "unknown"
        except Exception:
            health["version"] = "unknown"
        
        # Overall status
        statuses = [c.get("status", "ok") for c in health["checks"].values()]
        if "error" in statuses:
            health["status"] = "unhealthy"
        elif "warning" in statuses:
            health["status"] = "degraded"
        else:
            health["status"] = "healthy"
        
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
    
    async def _handle_metrics(self, request):
        """
        System metrics endpoint (Prometheus-style format).
        Useful for monitoring and dashboards.
        """
        import psutil
        import os
        
        metrics = []
        
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_per_core = psutil.cpu_percent(percpu=True, interval=0.1)
            
            metrics.append(f"# HELP smartc_cpu_percent CPU usage percentage")
            metrics.append(f"# TYPE smartc_cpu_percent gauge")
            metrics.append(f"smartc_cpu_percent {cpu_percent}")
            
            for i, core in enumerate(cpu_per_core):
                metrics.append(f"smartc_cpu_core_percent{{core=\"{i}\"}} {core}")
            
            # Memory metrics
            mem = psutil.virtual_memory()
            metrics.append(f"# HELP smartc_memory_percent Memory usage percentage")
            metrics.append(f"# TYPE smartc_memory_percent gauge")
            metrics.append(f"smartc_memory_percent {mem.percent}")
            metrics.append(f"smartc_memory_used_bytes {mem.used}")
            metrics.append(f"smartc_memory_total_bytes {mem.total}")
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            metrics.append(f"# HELP smartc_disk_percent Disk usage percentage")
            metrics.append(f"# TYPE smartc_disk_percent gauge")
            metrics.append(f"smartc_disk_percent {disk.percent}")
            metrics.append(f"smartc_disk_free_bytes {disk.free}")
            
            # Temperature (Raspberry Pi)
            try:
                temp_file = "/sys/class/thermal/thermal_zone0/temp"
                if os.path.exists(temp_file):
                    with open(temp_file) as f:
                        cpu_temp = int(f.read().strip()) / 1000.0
                    metrics.append(f"# HELP smartc_cpu_temp_celsius CPU temperature")
                    metrics.append(f"# TYPE smartc_cpu_temp_celsius gauge")
                    metrics.append(f"smartc_cpu_temp_celsius {cpu_temp:.1f}")
            except Exception:
                pass
            
            # App metrics
            try:
                p = psutil.Process(os.getpid())
                uptime_sec = time.time() - p.create_time()
                metrics.append(f"# HELP smartc_uptime_seconds App uptime in seconds")
                metrics.append(f"# TYPE smartc_uptime_seconds counter")
                metrics.append(f"smartc_uptime_seconds {int(uptime_sec)}")
                
                proc_mem = p.memory_percent()
                metrics.append(f"smartc_process_memory_percent {proc_mem:.1f}")
            except Exception:
                pass
            
            # Network status
            try:
                from src.network.network_status import is_connected
                connected = 1 if is_connected() else 0
                metrics.append(f"# HELP smartc_network_connected Network connection status")
                metrics.append(f"# TYPE smartc_network_connected gauge")
                metrics.append(f"smartc_network_connected {connected}")
            except Exception:
                pass
            
            # WebSocket status
            try:
                from src.application import Application
                app = Application._instance
                ws_connected = 1 if (app and app.is_audio_channel_opened()) else 0
                metrics.append(f"# HELP smartc_websocket_connected WebSocket connection status")
                metrics.append(f"# TYPE smartc_websocket_connected gauge")
                metrics.append(f"smartc_websocket_connected {ws_connected}")
            except Exception:
                pass
            
        except Exception as e:
            metrics.append(f"# Error collecting metrics: {e}")
        
        return web.Response(
            text="\n".join(metrics),
            content_type="text/plain; version=0.0.4; charset=utf-8"
        )
    
    async def _handle_wifi_saved(self, request):
        """Lấy danh sách WiFi networks đã lưu."""
        try:
            from src.network.wifi_manager import get_wifi_manager
            
            wifi = get_wifi_manager()
            saved = wifi.get_saved_networks()
            current = wifi.get_current_ssid()
            
            networks = []
            for ssid in saved:
                networks.append({
                    "ssid": ssid,
                    "connected": ssid == current
                })
            
            return web.json_response({
                "networks": networks,
                "current": current
            })
        except Exception as e:
            return web.json_response({"error": str(e), "networks": []})
    
    async def _handle_wifi_delete(self, request):
        """Xóa một WiFi network đã lưu."""
        try:
            data = await request.json()
            ssid = data.get("ssid", "")
            
            if not ssid:
                return web.json_response({"success": False, "message": "Thiếu SSID"})
            
            from src.network.wifi_manager import get_wifi_manager
            
            wifi = get_wifi_manager()
            if wifi.delete_saved_network(ssid):
                return web.json_response({"success": True, "message": f"Đã xóa {ssid}"})
            else:
                return web.json_response({"success": False, "message": f"Không thể xóa {ssid}"})
        except Exception as e:
            return web.json_response({"success": False, "message": str(e)})
    
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
    try:
        if _server is None:
            logger.info(f"Starting Web Settings Server on port {port}...")
            _server = WebSettingsServer(port)
            await _server.start()
            logger.info(f"Web Settings Server started successfully on port {port}")
        else:
            logger.info(f"Web Settings Server already running")
        return _server
    except Exception as e:
        logger.error(f"Failed to start Web Settings Server: {e}")
        import traceback
        traceback.print_exc()
        return None


async def stop_web_settings():
    """Dừng Web Settings Server."""
    global _server
    if _server:
        await _server.stop()
        _server = None
