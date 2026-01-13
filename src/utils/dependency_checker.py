"""
Dependency Checker - Kiểm tra và cài đặt tất cả system dependencies.

Chạy khi app khởi động:
- Fresh install: cài tất cả
- Update: kiểm tra và cài những gì thiếu
"""

import subprocess
import shutil
from typing import List, Tuple
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


# =========================================================================
# DANH SÁCH DEPENDENCIES - SMART C AI
# =========================================================================

# APT packages cần thiết cho Raspberry Pi
APT_PACKAGES = [
    # === AUDIO OUTPUT ===
    ("pulseaudio", "pulseaudio"),
    ("pactl", "pulseaudio-utils"),
    ("aplay", "alsa-utils"),
    
    # === MIC / AUDIO INPUT ===
    # PortAudio - cho sounddevice
    ("", "libportaudio2"),
    ("", "portaudio19-dev"),
    # ALSA development
    ("", "libasound2-dev"),
    # I2S MIC support
    ("", "i2c-tools"),
    # Jack audio (optional)
    ("", "libjack-dev"),
    
    # === OPUS CODEC ===
    ("", "libopus0"),
    ("", "libopus-dev"),
    
    # === VIDEO / MEDIA ===
    ("ffmpeg", "ffmpeg"),
    # GStreamer cho Qt Multimedia
    ("", "gstreamer1.0-tools"),
    ("", "gstreamer1.0-plugins-base"),
    ("", "gstreamer1.0-plugins-good"),
    ("", "gstreamer1.0-plugins-bad"),
    ("", "gstreamer1.0-plugins-ugly"),
    ("", "gstreamer1.0-libav"),
    ("", "gstreamer1.0-alsa"),
    ("", "gstreamer1.0-pulseaudio"),
    # Qt Multimedia for video
    ("", "libqt5multimedia5"),
    ("", "libqt5multimedia5-plugins"),
    ("", "qml-module-qtmultimedia"),
    
    # === PyQt5 / GUI ===
    ("", "python3-pyqt5"),
    ("", "python3-pyqt5.qtmultimedia"),
    ("", "python3-pyqt5.qtquick"),
    ("", "qml-module-qtquick2"),
    ("", "qml-module-qtquick-controls"),
    ("", "qml-module-qtquick-controls2"),
    ("", "qml-module-qtquick-layouts"),
    ("", "qml-module-qtquick-window2"),
    
    # === Python build dependencies ===
    ("", "python3-pip"),
    ("", "python3-dev"),
    ("", "python3-numpy"),
    ("", "python3-pil"),
    
    # === Network ===
    ("curl", "curl"),
    ("wget", "wget"),
    ("git", "git"),
]

# Python packages từ requirements-pi.txt
PIP_PACKAGES = [
    # === CORE (Bắt buộc) ===
    "numpy>=1.20.0",
    "sounddevice>=0.4.4",
    "websockets>=11.0",
    "aiohttp>=3.8.0",
    
    # === Wake Word Detection ===
    "sherpa-onnx>=1.10.0",
    
    # === Audio Processing ===
    "opuslib>=3.0.1",
    "webrtcvad-wheels>=2.0.10",
    "soxr>=0.3.0",
    
    # === Network & Protocol ===
    "paho-mqtt>=2.0.0",
    "requests>=2.28.0",
    
    # === Security ===
    "cryptography>=40.0.0",
    
    # === Utilities ===
    "colorlog>=6.0.0",
    "psutil>=5.9.0",
    "py-machineid>=0.6.0",
    "python-dateutil>=2.8.0",
    "pillow>=9.0.0",
    
    # === GUI ===
    "qasync>=0.27.0",
]


def is_raspberry_pi() -> bool:
    """Kiểm tra có đang chạy trên Raspberry Pi không."""
    try:
        with open('/proc/device-tree/model', 'r') as f:
            model = f.read().lower()
            return 'raspberry' in model or 'pi' in model
    except Exception:
        return False


def check_command_exists(command: str) -> bool:
    """Kiểm tra một command có tồn tại trong PATH không."""
    return shutil.which(command) is not None


def check_apt_package_installed(package: str) -> bool:
    """Kiểm tra apt package đã được cài đặt chưa."""
    try:
        result = subprocess.run(
            ['dpkg', '-s', package],
            capture_output=True, timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False


def install_apt_packages(packages: List[str]) -> bool:
    """Cài đặt apt packages."""
    if not packages:
        return True
    
    logger.info(f"📦 Installing apt packages: {', '.join(packages)}")
    
    try:
        # Update apt cache
        result = subprocess.run(
            ['sudo', 'apt-get', 'update', '-qq'],
            capture_output=True, timeout=120
        )
        
        # Install packages
        cmd = ['sudo', 'apt-get', 'install', '-y', '-qq'] + packages
        result = subprocess.run(cmd, capture_output=True, timeout=300)
        
        if result.returncode == 0:
            logger.info(f"✅ Installed: {', '.join(packages)}")
            return True
        else:
            stderr = result.stderr.decode('utf-8', errors='ignore')
            logger.error(f"❌ Install failed: {stderr[:200]}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("❌ Installation timed out")
        return False
    except Exception as e:
        logger.error(f"❌ Installation error: {e}")
        return False


def check_and_install_apt_dependencies() -> Tuple[int, int]:
    """
    Kiểm tra và cài đặt apt dependencies.
    Returns: (số package đã cài, số package lỗi)
    """
    missing_packages = []
    
    for command, package in APT_PACKAGES:
        # Nếu có command thì check command, không có thì check package trực tiếp
        if command:
            if not check_command_exists(command) and not check_apt_package_installed(package):
                missing_packages.append(package)
                logger.debug(f"📋 Missing: {package} (provides: {command})")
        else:
            # Không có command, chỉ check package
            if not check_apt_package_installed(package):
                missing_packages.append(package)
                logger.debug(f"📋 Missing: {package}")
    
    if not missing_packages:
        logger.info("✅ All apt dependencies already installed")
        return (0, 0)
    
    logger.info(f"📦 {len(missing_packages)} packages need to be installed")
    
    if install_apt_packages(missing_packages):
        return (len(missing_packages), 0)
    else:
        return (0, len(missing_packages))


def check_pip_package(package: str) -> bool:
    """Kiểm tra pip package đã được cài đặt chưa."""
    try:
        result = subprocess.run(
            ['pip3', 'show', package],
            capture_output=True, timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False


def install_pip_packages(packages: List[str]) -> bool:
    """Cài đặt pip packages."""
    if not packages:
        return True
    
    logger.info(f"📦 Installing pip packages: {', '.join(packages)}")
    
    try:
        cmd = ['pip3', 'install', '--quiet'] + packages
        result = subprocess.run(cmd, capture_output=True, timeout=300)
        
        if result.returncode == 0:
            logger.info(f"✅ Installed pip packages: {', '.join(packages)}")
            return True
        else:
            stderr = result.stderr.decode('utf-8', errors='ignore')
            logger.error(f"❌ Pip install failed: {stderr[:200]}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("❌ Pip installation timed out")
        return False
    except Exception as e:
        logger.error(f"❌ Pip installation error: {e}")
        return False


def check_and_install_pip_dependencies() -> Tuple[int, int]:
    """
    Kiểm tra và cài đặt pip dependencies.
    Returns: (số package đã cài, số package lỗi)
    """
    missing_packages = []
    
    for package_spec in PIP_PACKAGES:
        # Extract package name từ spec (ví dụ: numpy>=1.20.0 -> numpy)
        package_name = package_spec.split('>=')[0].split('==')[0].split('<')[0].split('>')[0]
        
        if not check_pip_package(package_name):
            missing_packages.append(package_spec)
            logger.debug(f"📋 Missing pip: {package_name}")
    
    if not missing_packages:
        logger.info("✅ All pip dependencies already installed")
        return (0, 0)
    
    logger.info(f"📦 Installing {len(missing_packages)} pip packages...")
    
    if install_pip_packages(missing_packages):
        return (len(missing_packages), 0)
    else:
        return (0, len(missing_packages))


def check_all_dependencies(force_install: bool = False) -> dict:
    """
    Main function - kiểm tra và cài đặt TẤT CẢ dependencies.
    
    Args:
        force_install: True để cài lại tất cả dù đã có
        
    Returns:
        dict với thông tin kết quả
    """
    if not is_raspberry_pi():
        logger.info("Not on Raspberry Pi, skip dependency check")
        return {"skipped": True, "reason": "not_raspberry_pi"}
    
    logger.info("=== Dependency Check: Starting ===")
    
    result = {
        "apt_installed": 0,
        "apt_failed": 0,
        "pip_installed": 0,
        "pip_failed": 0,
    }
    
    # Check APT packages
    apt_installed, apt_failed = check_and_install_apt_dependencies()
    result["apt_installed"] = apt_installed
    result["apt_failed"] = apt_failed
    
    # Check PIP packages
    pip_installed, pip_failed = check_and_install_pip_dependencies()
    result["pip_installed"] = pip_installed
    result["pip_failed"] = pip_failed
    
    total_installed = apt_installed + pip_installed
    total_failed = apt_failed + pip_failed
    
    if total_installed > 0:
        logger.info(f"✅ Installed {total_installed} packages")
    if total_failed > 0:
        logger.warning(f"⚠️ Failed to install {total_failed} packages")
    
    logger.info("=== Dependency Check: Complete ===")
    
    return result


def install_all_dependencies() -> bool:
    """
    Cài đặt TẤT CẢ dependencies (cho fresh install).
    """
    if not is_raspberry_pi():
        logger.info("Not on Raspberry Pi, skip dependency install")
        return True
    
    logger.info("=== Installing ALL Dependencies ===")
    
    # Install all APT packages
    apt_packages = [pkg for _, pkg in APT_PACKAGES]
    apt_ok = install_apt_packages(apt_packages)
    
    # Install all PIP packages
    pip_ok = install_pip_packages(PIP_PACKAGES)
    
    logger.info("=== Dependency Installation Complete ===")
    
    return apt_ok and pip_ok
