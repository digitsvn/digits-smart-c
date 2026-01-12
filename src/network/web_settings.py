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
        
        loadStatus();
        loadAudioDevices();
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
        self.app.router.add_post('/api/youtube', self._handle_youtube)
        self.app.router.add_get('/api/audio/devices', self._handle_audio_devices)
        self.app.router.add_post('/api/audio', self._handle_audio)
        self.app.router.add_post('/api/restart', self._handle_restart)
        self.app.router.add_post('/api/reboot', self._handle_reboot)
    
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
            
            self.config.update_config("VIDEO_BACKGROUND.ENABLED", bool(path))
            self.config.update_config("VIDEO_BACKGROUND.SOURCE_TYPE", "file")
            self.config.update_config("VIDEO_BACKGROUND.VIDEO_FILE_PATH", path)
            self.config.update_config("VIDEO_BACKGROUND.YOUTUBE_URL", "")
            
            # Reload video trong app
            self._reload_video()
            
            return web.json_response({"success": True, "message": "Đã lưu! Video sẽ áp dụng ngay."})
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
            app = Application.get_instance()
            if app and hasattr(app, 'display') and app.display:
                app.display.reload_video_from_config()
        except Exception as e:
            logger.error(f"Reload video failed: {e}")
    
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
