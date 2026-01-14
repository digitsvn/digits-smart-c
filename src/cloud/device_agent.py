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
        }
    
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
    
    async def run(self):
        """Main loop."""
        self.running = True
        
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
