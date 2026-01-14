"""
Smart C AI - Cloud Device Agent
================================
Connects to cloud server for remote management.
Provides:
- Heartbeat & status updates
- Screenshot capture & streaming
- Remote command execution
- Config sync
"""

import asyncio
import json
import base64
import os
import subprocess
import time
from typing import Optional, Callable
from io import BytesIO

try:
    import websockets
except ImportError:
    websockets = None

from src.utils.logging_config import get_logger
from src.utils.resource_finder import get_project_root

logger = get_logger(__name__)


class CloudAgent:
    """
    Agent kết nối tới Cloud Server để quản lý từ xa.
    """
    
    def __init__(
        self,
        server_url: str,
        device_id: Optional[str] = None,
        device_name: Optional[str] = None
    ):
        """
        Args:
            server_url: WebSocket URL của cloud server (wss://0nline.vn/ws/device)
            device_id: ID thiết bị (tự tạo nếu None)
            device_name: Tên thiết bị hiển thị
        """
        self.server_url = server_url
        self.device_id = device_id or self._get_device_id()
        self.device_name = device_name or f"SmartC-{self.device_id[:8]}"
        
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.running = False
        self.connected = False
        
        # Callbacks for command handling
        self.command_handlers: dict[str, Callable] = {}
        
        # Screenshot settings
        self.screenshot_enabled = True
        self.screenshot_interval = 3  # seconds
        self.last_screenshot = None
        
        # Register default command handlers
        self._register_default_handlers()
    
    def _get_device_id(self) -> str:
        """Lấy hoặc tạo Device ID duy nhất."""
        id_file = get_project_root() / "config" / "device_id"
        
        if id_file.exists():
            return id_file.read_text().strip()
        
        # Generate new ID from machine info
        import uuid
        try:
            # Try to use MAC address
            mac = uuid.getnode()
            device_id = f"smartc-{mac:012x}"
        except Exception:
            device_id = f"smartc-{uuid.uuid4().hex[:12]}"
        
        # Save ID
        id_file.parent.mkdir(parents=True, exist_ok=True)
        id_file.write_text(device_id)
        
        return device_id
    
    def _register_default_handlers(self):
        """Đăng ký các command handlers mặc định."""
        self.command_handlers = {
            'restart': self._cmd_restart,
            'reboot': self._cmd_reboot,
            'update': self._cmd_update,
            'get_config': self._cmd_get_config,
            'set_volume': self._cmd_set_volume,
            # New remote config commands
            'set_video': self._cmd_set_video,
            'set_audio': self._cmd_set_audio,
            'test_mic': self._cmd_test_mic,
            'test_speaker': self._cmd_test_speaker,
            'set_wakeword': self._cmd_set_wakeword,
            'wifi_connect': self._cmd_wifi_connect,
            'set_system': self._cmd_set_system,
            'set_background_mode': self._cmd_set_background_mode,
        }

    async def _cmd_set_background_mode(self, params: dict):
        """
        Cấu hình background: Video hoặc Slideshow.
        Params:
            type: 'video' | 'slide'
            urls: list[str] (nếu slide)
            interval: int (ms)
            video_path: str (nếu video/legacy)
        """
        bg_type = params.get("type", "video")
        
        try:
            from src.application import Application
            app = Application._instance
            ui_plugin = app.plugins.get_plugin("ui") if app and hasattr(app, 'plugins') else None
            
            if bg_type == "slide":
                urls = params.get("urls", [])
                interval = params.get("interval", 5000)
                
                # Download images
                slide_dir = get_project_root() / "assets" / "slides"
                slide_dir.mkdir(parents=True, exist_ok=True)
                
                # Clear old slides? Maybe keep them.
                # For now let's just download new ones.
                local_paths = []
                
                for url in urls:
                    try:
                        filename = url.split("/")[-1]
                        local_path = slide_dir / filename
                        
                        # Download if not exists
                        # Use subprocess wget for simplicity and valid async simulation
                        if not local_path.exists():
                            logger.info(f"Downloading slide: {url}")
                            subprocess.run(
                                ["wget", "-q", "-O", str(local_path), url],
                                check=True,
                                timeout=30
                            )
                        local_paths.append(str(local_path))
                    except Exception as e:
                        logger.error(f"Failed to download slide {url}: {e}")

                if ui_plugin:
                    # Update config
                    app.config.config['display']['background_mode'] = 'slide'
                    app.config.config['display']['slide_images'] = local_paths
                    app.config.config['display']['slide_interval'] = interval
                    app.config.save_config()
                    
                    # Notify UI
                    # We need to implement set_slideshow in GuiPlugin/Display
                    if hasattr(ui_plugin.display, 'set_slideshow'):
                        ui_plugin.display.set_slideshow(local_paths, interval)
                        
                return {"status": "ok", "message": f"Slideshow set with {len(local_paths)} images"}

            else:
                # Video mode logic (existing or new)
                video_path = params.get("video_path")
                if not video_path and 'urls' in params and len(params['urls']) > 0:
                     video_path = params['urls'][0] # Fallback if user selected video url logic
                     
                if video_path and ui_plugin:
                    app.config.config['display']['background_mode'] = 'video'
                    app.config.config['display']['video_path'] = video_path
                    app.config.save_config()
                    
                    if hasattr(ui_plugin.display, 'set_video_background'):
                        ui_plugin.display.set_video_background(video_path)
                        
                return {"status": "ok", "message": "Video set"}
                
        except Exception as e:
            logger.error(f"Set background error: {e}")
            return {"status": "error", "message": str(e)}
    
    async def connect(self) -> bool:
        """Kết nối tới Cloud Server."""
        if not websockets:
            logger.error("websockets library not installed. Run: pip install websockets")
            return False
        
        try:
            logger.info(f"Connecting to Cloud Server: {self.server_url}")
            self.ws = await websockets.connect(
                self.server_url,
                ping_interval=30,
                ping_timeout=10
            )
            self.connected = True
            logger.info("Connected to Cloud Server!")
            
            # Register device
            await self._register()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Cloud Server: {e}")
            self.connected = False
            return False
    
    async def _register(self):
        """Đăng ký thiết bị với server."""
        system_info = self._get_system_info()
        
        await self._send({
            'type': 'register',
            'device_id': self.device_id,
            'name': self.device_name,
            'ip': self._get_local_ip(),
            'version': self._get_version(),
            'system': system_info
        })
        
        logger.info(f"Device registered: {self.device_id}")
    
    async def _send(self, data: dict):
        """Gửi message tới server."""
        if self.ws and self.connected:
            try:
                await self.ws.send(json.dumps(data))
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
                self.connected = False
    
    async def _send_heartbeat(self):
        """Gửi heartbeat định kỳ."""
        await self._send({
            'type': 'heartbeat',
            'device_id': self.device_id,
            'ip': self._get_local_ip(),
            'system': self._get_system_info()
        })
    
    async def _send_screenshot(self):
        """Chụp và gửi screenshot."""
        try:
            screenshot = self._capture_screenshot()
            if screenshot:
                await self._send({
                    'type': 'screenshot',
                    'device_id': self.device_id,
                    'image': screenshot
                })
                self.last_screenshot = time.time()
        except Exception as e:
            logger.error(f"Failed to send screenshot: {e}")
    
    def _capture_screenshot(self) -> Optional[str]:
        """
        Chụp screenshot màn hình.
        Returns:
            Base64 encoded PNG image hoặc None nếu lỗi
        """
        try:
            # Method 1: Try scrot (lightweight)
            output_file = "/tmp/smartc_screenshot.png"
            result = subprocess.run(
                ["scrot", "-o", output_file],
                capture_output=True,
                timeout=5,
                env={**os.environ, "DISPLAY": ":0"}
            )
            
            if result.returncode == 0 and os.path.exists(output_file):
                with open(output_file, "rb") as f:
                    image_data = f.read()
                
                # Convert to base64 data URL
                b64 = base64.b64encode(image_data).decode('utf-8')
                return f"data:image/png;base64,{b64}"
            
            # Method 2: Try raspi2png (Raspberry Pi specific)
            result = subprocess.run(
                ["raspi2png", "-p", output_file],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode == 0 and os.path.exists(output_file):
                with open(output_file, "rb") as f:
                    image_data = f.read()
                b64 = base64.b64encode(image_data).decode('utf-8')
                return f"data:image/png;base64,{b64}"
            
            # Method 3: Try fbgrab (framebuffer)
            result = subprocess.run(
                ["fbgrab", output_file],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode == 0 and os.path.exists(output_file):
                with open(output_file, "rb") as f:
                    image_data = f.read()
                b64 = base64.b64encode(image_data).decode('utf-8')
                return f"data:image/png;base64,{b64}"
                
        except subprocess.TimeoutExpired:
            logger.warning("Screenshot capture timeout")
        except FileNotFoundError:
            logger.warning("Screenshot tools not found (scrot, raspi2png, fbgrab)")
        except Exception as e:
            logger.error(f"Screenshot capture error: {e}")
        
        return None
    
    def _get_system_info(self) -> dict:
        """Lấy thông tin hệ thống."""
        info = {}
        
        try:
            import psutil
            info['cpu_percent'] = psutil.cpu_percent()
            info['memory_percent'] = round(psutil.virtual_memory().percent, 1)
            info['disk_percent'] = round(psutil.disk_usage('/').percent, 1)
        except ImportError:
            pass
        
        # CPU Temperature (Raspberry Pi)
        try:
            temp_file = "/sys/class/thermal/thermal_zone0/temp"
            if os.path.exists(temp_file):
                with open(temp_file) as f:
                    info['cpu_temp'] = round(int(f.read().strip()) / 1000, 1)
        except Exception:
            pass
        
        return info
    
    def _get_local_ip(self) -> str:
        """Lấy IP local."""
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "Unknown"
    
    def _get_version(self) -> str:
        """Lấy version của app."""
        try:
            version_file = get_project_root() / "VERSION"
            if version_file.exists():
                return version_file.read_text().strip()
        except Exception:
            pass
        return "Unknown"
    
    # ========== Command Handlers ==========
    
    async def _cmd_restart(self, params: dict):
        """Restart app."""
        logger.info("Executing restart command from cloud...")
        subprocess.Popen(["sudo", "systemctl", "restart", "smartc"])
        return {"status": "restarting"}
    
    async def _cmd_reboot(self, params: dict):
        """Reboot Pi."""
        logger.info("Executing reboot command from cloud...")
        subprocess.Popen(["sudo", "reboot"])
        return {"status": "rebooting"}
    
    async def _cmd_update(self, params: dict):
        """Update từ Git."""
        logger.info("Executing update command from cloud...")
        result = subprocess.run(
            ["git", "pull", "origin", "main"],
            cwd=str(get_project_root()),
            capture_output=True,
            text=True,
            timeout=60
        )
        return {
            "status": "completed" if result.returncode == 0 else "failed",
            "output": result.stdout or result.stderr
        }
    
    async def _cmd_get_config(self, params: dict):
        """Lấy config hiện tại."""
        try:
            config_file = get_project_root() / "config" / "config.json"
            if config_file.exists():
                with open(config_file) as f:
                    config = json.load(f)
                return {"config": config}
        except Exception as e:
            return {"error": str(e)}
        return {"error": "Config not found"}
    
    async def _cmd_set_volume(self, params: dict):
        """Set volume."""
        volume = params.get("volume", 80)
        subprocess.run(["amixer", "set", "Master", f"{volume}%"], capture_output=True)
        return {"status": "ok", "volume": volume}
    
    async def _cmd_set_video(self, params: dict):
        """Set video background."""
        video_path = params.get("video_path", "")
        if not video_path:
            return {"status": "error", "message": "Missing video_path"}
        
        logger.info(f"Setting video from cloud: {video_path}")
        
        try:
            from src.application import Application
            app = Application._instance
            if app:
                app.config.update_config("UI.VIDEO_PATH", video_path)
                # Trigger video change
                ui_plugin = app.plugins.get_plugin("ui")
                if ui_plugin and ui_plugin.display:
                    ui_plugin.display.set_video_path(video_path)
                return {"status": "ok", "video": video_path}
        except Exception as e:
            logger.error(f"Set video error: {e}")
            return {"status": "error", "message": str(e)}
        
        return {"status": "error", "message": "App not available"}
    
    async def _cmd_set_audio(self, params: dict):
        """Set audio devices."""
        input_device = params.get("input_device")
        output_device = params.get("output_device")
        
        logger.info(f"Setting audio from cloud: input={input_device}, output={output_device}")
        
        try:
            from src.application import Application
            app = Application._instance
            if app:
                if input_device:
                    app.config.update_config("AUDIO.INPUT_DEVICE", input_device)
                if output_device:
                    app.config.update_config("AUDIO.OUTPUT_DEVICE", output_device)
                return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        
        return {"status": "error", "message": "App not available"}
    
    async def _cmd_test_mic(self, params: dict):
        """Test microphone."""
        logger.info("Testing microphone from cloud...")
        try:
            from src.application import Application
            app = Application._instance
            if app and hasattr(app, 'plugins'):
                audio_plugin = app.plugins.get_plugin("audio")
                if audio_plugin:
                    # Trigger mic test via existing functionality
                    return {"status": "ok", "message": "Mic test started"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        
        return {"status": "ok", "message": "Test command sent"}
    
    async def _cmd_test_speaker(self, params: dict):
        """Test speaker."""
        hdmi_audio = params.get("hdmi_audio", False)
        logger.info(f"Testing speaker from cloud (HDMI={hdmi_audio})...")
        
        try:
            # Play test beep
            import numpy as np
            import wave
            import tempfile
            
            sample_rate = 44100
            duration = 0.3
            frequency = 880
            
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            beep = (np.sin(2 * np.pi * frequency * t) * 20000).astype(np.int16)
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                temp_wav = f.name
            
            with wave.open(temp_wav, 'w') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(beep.tobytes())
            
            if hdmi_audio:
                subprocess.run(["aplay", "-D", "plughw:CARD=vc4hdmi0", temp_wav], 
                              capture_output=True, timeout=5)
            else:
                subprocess.run(["aplay", temp_wav], capture_output=True, timeout=5)
            
            os.unlink(temp_wav)
            return {"status": "ok", "message": "Speaker test played"}
            
        except Exception as e:
            logger.error(f"Speaker test error: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _cmd_set_wakeword(self, params: dict):
        """Set wake word settings."""
        enabled = params.get("enabled", True)
        threshold = params.get("threshold", 0.5)
        
        logger.info(f"Setting wakeword from cloud: enabled={enabled}, threshold={threshold}")
        
        try:
            from src.application import Application
            app = Application._instance
            if app:
                app.config.update_config("WAKE_WORD.ENABLED", enabled)
                app.config.update_config("WAKE_WORD.THRESHOLD", threshold)
                
                # Apply to running plugin
                wakeword_plugin = app.plugins.get_plugin("wakeword")
                if wakeword_plugin:
                    if enabled:
                        wakeword_plugin.enable()
                    else:
                        wakeword_plugin.disable()
                
                return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        
        return {"status": "error", "message": "App not available"}
    
    async def _cmd_wifi_connect(self, params: dict):
        """Connect to WiFi."""
        ssid = params.get("ssid", "")
        password = params.get("password", "")
        
        if not ssid:
            return {"status": "error", "message": "Missing SSID"}
        
        logger.info(f"Connecting to WiFi from cloud: {ssid}")
        
        try:
            if password:
                cmd = ["sudo", "nmcli", "device", "wifi", "connect", ssid, "password", password]
            else:
                cmd = ["sudo", "nmcli", "device", "wifi", "connect", ssid]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                return {"status": "ok", "message": f"Connected to {ssid}"}
            else:
                return {"status": "error", "message": result.stderr or "Connection failed"}
                
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def _cmd_set_system(self, params: dict):
        """Set system settings."""
        logger.info(f"Setting system config from cloud: {params}")
        
        try:
            from src.application import Application
            app = Application._instance
            if app:
                if "language" in params:
                    app.config.update_config("SYSTEM.LANGUAGE", params["language"])
                if "ota_url" in params:
                    app.config.update_config("NETWORK.OTA_URL", params["ota_url"])
                if "ws_url" in params:
                    app.config.update_config("NETWORK.WS_URL", params["ws_url"])
                
                return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        
        return {"status": "error", "message": "App not available"}
    
    # ========== Main Loop ==========
    
    async def _handle_messages(self):
        """Xử lý messages từ server."""
        try:
            async for message in self.ws:
                try:
                    data = json.loads(message)
                    msg_type = data.get('type')
                    
                    if msg_type == 'registered':
                        logger.info(f"Registration confirmed: {data.get('device_id')}")
                        
                    elif msg_type == 'capture_screenshot':
                        await self._send_screenshot()
                        
                    elif msg_type == 'command':
                        command = data.get('command')
                        params = data.get('params', {})
                        
                        if command in self.command_handlers:
                            result = await self.command_handlers[command](params)
                            await self._send({
                                'type': 'command_result',
                                'command': command,
                                'result': result
                            })
                        else:
                            logger.warning(f"Unknown command: {command}")
                            
                    elif msg_type == 'update_config':
                        # TODO: Apply config changes
                        config = data.get('config', {})
                        logger.info(f"Config update received: {config}")
                        await self._send({
                            'type': 'config_updated',
                            'status': 'ok'
                        })
                        
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON message: {message}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    
        except websockets.ConnectionClosed:
            logger.warning("Connection to Cloud Server closed")
            self.connected = False
    
    async def _heartbeat_loop(self):
        """Gửi heartbeat định kỳ."""
        while self.running:
            if self.connected:
                await self._send_heartbeat()
            await asyncio.sleep(30)  # Every 30 seconds
    
    async def _screenshot_loop(self):
        """Gửi screenshot định kỳ (nếu enabled)."""
        while self.running:
            if self.connected and self.screenshot_enabled:
                await self._send_screenshot()
            await asyncio.sleep(self.screenshot_interval)
    
    async def _check_update_on_startup(self):
        """Kiểm tra update khi khởi động."""
        try:
            logger.info("Checking for startup updates...")
            result = subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=str(get_project_root()),
                capture_output=True,
                text=True,
                timeout=60
            )
            
            output = result.stdout or ""
            if result.returncode == 0 and "Already up to date" not in output:
                logger.info("✨ Startup Update found! Updating and restarting...")
                # Log to file or send to server could be added here
                # Restart service to apply changes
                subprocess.Popen(["sudo", "systemctl", "restart", "smartc"])
                return True
            else:
                logger.info("System is up to date.")
                return False
                
        except Exception as e:
            logger.warning(f"Startup update check failed: {e}")
            return False

    async def run(self):
        """Main loop."""
        self.running = True
        
        # Check update on startup (one time)
        await self._check_update_on_startup()
        
        while self.running:
            if not self.connected:
                success = await self.connect()
                if not success:
                    logger.info("Retrying connection in 10 seconds...")
                    await asyncio.sleep(10)
                    continue
            
            # Run tasks
            tasks = [
                asyncio.create_task(self._handle_messages()),
                asyncio.create_task(self._heartbeat_loop()),
            ]
            
            # Optional: Add screenshot loop
            if self.screenshot_enabled:
                tasks.append(asyncio.create_task(self._screenshot_loop()))
            
            # Wait for any task to complete (usually means disconnect)
            done, pending = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel pending tasks
            for task in pending:
                task.cancel()
            
            # If disconnected, wait before retry
            if not self.connected:
                logger.info("Reconnecting in 5 seconds...")
                await asyncio.sleep(5)
    
    async def stop(self):
        """Dừng agent."""
        self.running = False
        if self.ws:
            await self.ws.close()


# ========== Factory Function ==========

_cloud_agent: Optional[CloudAgent] = None

def get_cloud_agent() -> Optional[CloudAgent]:
    """Lấy Cloud Agent instance."""
    return _cloud_agent

async def start_cloud_agent(
    server_url: str,
    device_name: Optional[str] = None
) -> CloudAgent:
    """
    Khởi động Cloud Agent.
    
    Args:
        server_url: WebSocket URL (e.g., wss://0nline.vn/ws/device)
        device_name: Tên thiết bị
    
    Returns:
        CloudAgent instance
    """
    global _cloud_agent
    
    if _cloud_agent:
        await _cloud_agent.stop()
    
    _cloud_agent = CloudAgent(
        server_url=server_url,
        device_name=device_name
    )
    
    # Start in background
    asyncio.create_task(_cloud_agent.run())
    
    return _cloud_agent
