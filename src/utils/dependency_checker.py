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
# DANH SÁCH DEPENDENCIES
# =========================================================================

# APT packages cần thiết
APT_PACKAGES = [
    # Audio
    ("pulseaudio", "pulseaudio"),
    ("pactl", "pulseaudio-utils"),
    ("aplay", "alsa-utils"),
    
    # Media
    ("ffmpeg", "ffmpeg"),
    
    # Display (cho GUI)
    # ("xdotool", "xdotool"),
]

# Python packages (pip)
PIP_PACKAGES = [
    "opuslib",
    "sounddevice",
    "numpy",
    "aiohttp",
    "websockets",
    "qasync",
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
        if not check_command_exists(command):
            if not check_apt_package_installed(package):
                missing_packages.append(package)
                logger.info(f"📋 Missing: {package} (provides: {command})")
    
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
    
    for package in PIP_PACKAGES:
        if not check_pip_package(package):
            missing_packages.append(package)
            logger.info(f"📋 Missing pip: {package}")
    
    if not missing_packages:
        logger.info("✅ All pip dependencies already installed")
        return (0, 0)
    
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
