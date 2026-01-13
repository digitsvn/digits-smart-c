"""
Audio Setup Module - Khởi động lại tất cả audio services khi app start.

Giải quyết vấn đề:
- Video chiếm HDMI device
- aplay không truy cập được HDMI
- Conflict giữa gstreamer và aplay

Giải pháp:
1. Kill tất cả audio processes (aplay, paplay, pulseaudio)
2. Restart PulseAudio
3. Set HDMI làm default sink
4. Dùng paplay qua PulseAudio thay vì aplay trực tiếp
"""

import subprocess
import time
import os
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def is_raspberry_pi() -> bool:
    """Kiểm tra có đang chạy trên Raspberry Pi không."""
    try:
        with open('/proc/device-tree/model', 'r') as f:
            model = f.read().lower()
            return 'raspberry' in model or 'pi' in model
    except Exception:
        return False


def kill_audio_processes():
    """Kill tất cả audio processes để giải phóng devices."""
    processes_to_kill = ['aplay', 'paplay', 'mpv', 'ffplay', 'mplayer']
    
    for proc in processes_to_kill:
        try:
            subprocess.run(['pkill', '-9', proc], 
                         capture_output=True, timeout=2)
        except Exception:
            pass
    
    logger.info("🔇 Killed stale audio processes")


def check_pulseaudio_installed() -> bool:
    """Kiểm tra PulseAudio đã được cài đặt chưa."""
    try:
        result = subprocess.run(['which', 'pulseaudio'], 
                               capture_output=True, timeout=5)
        return result.returncode == 0
    except Exception:
        return False


def install_pulseaudio() -> bool:
    """Cài đặt PulseAudio nếu chưa có."""
    logger.info("📦 PulseAudio chưa được cài đặt, đang cài...")
    
    try:
        # Update apt cache
        result = subprocess.run(
            ['sudo', 'apt-get', 'update', '-qq'],
            capture_output=True, timeout=60
        )
        
        # Install pulseaudio
        result = subprocess.run(
            ['sudo', 'apt-get', 'install', '-y', '-qq', 
             'pulseaudio', 'pulseaudio-utils'],
            capture_output=True, timeout=120
        )
        
        if result.returncode == 0:
            logger.info("✅ PulseAudio installed successfully!")
            return True
        else:
            stderr = result.stderr.decode('utf-8', errors='ignore')
            logger.error(f"❌ Failed to install PulseAudio: {stderr[:200]}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("❌ PulseAudio installation timed out")
        return False
    except Exception as e:
        logger.error(f"❌ PulseAudio installation error: {e}")
        return False


def restart_pulseaudio():
    """Restart PulseAudio daemon. Cài đặt nếu chưa có."""
    
    # Kiểm tra và cài đặt nếu cần
    if not check_pulseaudio_installed():
        if not install_pulseaudio():
            logger.warning("PulseAudio not available, using ALSA directly")
            return False
    
    try:
        # Kill existing pulseaudio
        subprocess.run(['pulseaudio', '--kill'], 
                      capture_output=True, timeout=5)
        time.sleep(0.5)
        
        # Start pulseaudio daemon
        subprocess.run(['pulseaudio', '--start', '--daemonize=yes'], 
                      capture_output=True, timeout=5)
        time.sleep(1)
        
        # Verify it's running
        result = subprocess.run(['pulseaudio', '--check'], 
                               capture_output=True, timeout=2)
        if result.returncode == 0:
            logger.info("🔊 PulseAudio restarted successfully")
            return True
        else:
            logger.warning("PulseAudio check failed")
            return False
            
    except FileNotFoundError:
        logger.warning("PulseAudio not installed, using ALSA directly")
        return False
    except Exception as e:
        logger.warning(f"PulseAudio restart failed: {e}")
        return False


def find_hdmi_sink() -> str | None:
    """Tìm HDMI sink trong PulseAudio."""
    try:
        result = subprocess.run(
            ['pactl', 'list', 'sinks', 'short'],
            capture_output=True, text=True, timeout=5
        )
        
        if result.returncode != 0:
            return None
            
        for line in result.stdout.strip().split('\n'):
            parts = line.split('\t')
            if len(parts) >= 2:
                sink_name = parts[1]
                # HDMI sinks thường có "hdmi" hoặc "vc4" trong tên
                if 'hdmi' in sink_name.lower() or 'vc4' in sink_name.lower():
                    logger.info(f"Found HDMI sink: {sink_name}")
                    return sink_name
        
        return None
        
    except Exception as e:
        logger.warning(f"Failed to find HDMI sink: {e}")
        return None


def set_default_sink(sink_name: str) -> bool:
    """Set default PulseAudio sink."""
    try:
        result = subprocess.run(
            ['pactl', 'set-default-sink', sink_name],
            capture_output=True, timeout=5
        )
        
        if result.returncode == 0:
            logger.info(f"🔊 Set default sink: {sink_name}")
            return True
        else:
            logger.warning(f"Failed to set default sink: {result.stderr}")
            return False
            
    except Exception as e:
        logger.warning(f"pactl set-default-sink failed: {e}")
        return False


def setup_audio_environment():
    """
    Main setup function - gọi khi app khởi động.
    
    Flow:
    1. Kiểm tra dependencies (cài nếu thiếu)
    2. Kill tất cả audio processes
    3. Restart PulseAudio
    4. Set environment để video không chiếm HDMI
    5. Return True để dùng aplay trực tiếp
    """
    if not is_raspberry_pi():
        logger.info("Not on Raspberry Pi, skip audio setup")
        return False
    
    logger.info("=== Audio Setup: Starting ===")
    
    # Step 0: Check and install dependencies
    try:
        from src.utils.dependency_checker import check_all_dependencies
        check_all_dependencies()
    except Exception as e:
        logger.warning(f"Dependency check failed: {e}")
    
    # Step 1: Kill stale audio processes để giải phóng HDMI
    kill_audio_processes()
    
    # Step 2: Set environment để video KHÔNG dùng audio
    # Điều này ngăn gstreamer/Qt Video chiếm HDMI audio device
    os.environ['GST_AUDIO_SINK'] = 'fakesink'
    os.environ['PULSE_SINK'] = 'null'
    logger.info("📺 Video audio disabled (GST_AUDIO_SINK=fakesink)")
    
    # Step 3: Đợi một chút để các process cũ release device
    import time
    time.sleep(1)
    
    logger.info("=== Audio Setup: Complete - HDMI ready for AI audio ===")
    return True  # Báo hiệu dùng aplay trực tiếp, không cần PulseAudio


def get_pulseaudio_sink_for_aplay() -> str | None:
    """
    Lấy tên sink để dùng với paplay.
    Returns None nếu không có PulseAudio.
    """
    try:
        result = subprocess.run(
            ['pactl', 'get-default-sink'],
            capture_output=True, text=True, timeout=5
        )
        
        if result.returncode == 0:
            sink = result.stdout.strip()
            logger.debug(f"Default PulseAudio sink: {sink}")
            return sink
        return None
        
    except Exception:
        return None
