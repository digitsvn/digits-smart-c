# Xử lý thư viện động opus trước khi import opuslib
import ctypes
import os
import platform
import shutil
import sys
from enum import Enum
from pathlib import Path
from typing import List, Tuple, Union, cast

# Logger
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


# Hằng số nền tảng
class PLATFORM(Enum):
    WINDOWS = "windows"
    MACOS = "darwin"
    LINUX = "linux"


# Hằng số kiến trúc
class ARCH(Enum):
    WINDOWS = {"arm": "x64", "intel": "x64"}
    MACOS = {"arm": "arm64", "intel": "x64"}
    LINUX = {"arm": "arm64", "intel": "x64"}


# Hằng số đường dẫn thư viện động
class LIB_PATH(Enum):
    WINDOWS = "libs/libopus/win/x64"
    MACOS = "libs/libopus/mac/{arch}"
    LINUX = "libs/libopus/linux/{arch}"


# Hằng số tên thư viện động
class LIB_INFO(Enum):
    WINDOWS = {"name": "opus.dll", "system_name": ["opus"]}
    MACOS = {"name": "libopus.dylib", "system_name": ["libopus.dylib"]}
    LINUX = {"name": "libopus.so", "system_name": ["libopus.so.0", "libopus.so"]}


def get_platform() -> str:
    system = platform.system().lower()
    if system == "windows" or system.startswith("win"):
        system = PLATFORM.WINDOWS
    elif system == "darwin":
        system = PLATFORM.MACOS
    else:
        system = PLATFORM.LINUX
    return system


def get_arch(system: PLATFORM) -> str:
    architecture = platform.machine().lower()
    is_arm = "arm" in architecture or "aarch64" in architecture
    if system == PLATFORM.WINDOWS:
        arch_name = ARCH.WINDOWS.value["arm" if is_arm else "intel"]
    elif system == PLATFORM.MACOS:
        arch_name = ARCH.MACOS.value["arm" if is_arm else "intel"]
    else:
        arch_name = ARCH.LINUX.value["arm" if is_arm else "intel"]
    return architecture, arch_name


def get_lib_path(system: PLATFORM, arch_name: str):
    if system == PLATFORM.WINDOWS:
        lib_name = LIB_PATH.WINDOWS.value
    elif system == PLATFORM.MACOS:
        lib_name = LIB_PATH.MACOS.value.format(arch=arch_name)
    else:
        lib_name = LIB_PATH.LINUX.value.format(arch=arch_name)
    return lib_name


def get_lib_name(system: PLATFORM, local: bool = True) -> Union[str, List[str]]:
    """Lấy tên thư viện.

    Args:
        system (PLATFORM): Nền tảng
        local (bool, optional): Lấy tên local (str) hay danh sách tên hệ thống (List). Mặc định True.

    Returns:
        str | List: Tên thư viện
    """
    key = "name" if local else "system_name"
    if system == PLATFORM.WINDOWS:
        lib_name = LIB_INFO.WINDOWS.value[key]
    elif system == PLATFORM.MACOS:
        lib_name = LIB_INFO.MACOS.value[key]
    else:
        lib_name = LIB_INFO.LINUX.value[key]
    return lib_name


def get_system_info() -> Tuple[str, str]:
    """
    Lấy thông tin hệ thống hiện tại.
    """
    # Chuẩn hóa tên hệ thống
    system = get_platform()

    # Chuẩn hóa kiến trúc
    _, arch_name = get_arch(system)
    logger.info(f"Phát hiện hệ thống: {system}, kiến trúc: {arch_name}")

    return system, arch_name


def get_search_paths(system: PLATFORM, arch_name: str) -> List[Tuple[Path, str]]:
    """
    Lấy danh sách đường dẫn tìm kiếm thư viện (dùng resource finder thống nhất)
    """
    from .resource_finder import find_libs_dir, get_project_root

    lib_name = cast(str, get_lib_name(system))

    search_paths: List[Tuple[Path, str]] = []

    # Map tên hệ thống -> tên thư mục
    system_dir_map = {
        PLATFORM.WINDOWS: "win",
        PLATFORM.MACOS: "mac",
        PLATFORM.LINUX: "linux",
    }

    system_dir = system_dir_map.get(system)

    # Ưu tiên: thư mục libs theo nền tảng + kiến trúc
    if system_dir:
        specific_libs_dir = find_libs_dir(f"libopus/{system_dir}", arch_name)
        if specific_libs_dir:
            search_paths.append((specific_libs_dir, lib_name))
            logger.debug(f"Tìm thấy thư mục libs theo nền tảng/kiến trúc: {specific_libs_dir}")

    # Kế tiếp: thư mục libs theo nền tảng
    if system_dir:
        platform_libs_dir = find_libs_dir(f"libopus/{system_dir}")
        if platform_libs_dir:
            search_paths.append((platform_libs_dir, lib_name))
            logger.debug(f"Tìm thấy thư mục libs theo nền tảng: {platform_libs_dir}")

    # Thư mục libs chung
    general_libs_dir = find_libs_dir()
    if general_libs_dir:
        search_paths.append((general_libs_dir, lib_name))
        logger.debug(f"Thêm thư mục libs chung: {general_libs_dir}")

    # Thêm project root làm phương án cuối
    project_root = get_project_root()
    search_paths.append((project_root, lib_name))

    # In các đường dẫn để debug
    for dir_path, filename in search_paths:
        full_path = dir_path / filename
        logger.debug(f"Đường dẫn tìm kiếm: {full_path} (tồn tại: {full_path.exists()})")
    return search_paths


def find_system_opus() -> str:
    """
    Tìm thư viện opus từ hệ thống.
    """
    system, _ = get_system_info()
    lib_path = ""

    try:
        # Lấy danh sách tên thư viện opus trên hệ thống
        lib_names = cast(List[str], get_lib_name(system, False))

        # Thử lần lượt từng tên có thể
        for lib_name in lib_names:
            try:
                # Import ctypes.util để dùng find_library
                import ctypes.util

                system_lib_path = ctypes.util.find_library(lib_name)

                if system_lib_path:
                    lib_path = system_lib_path
                    logger.info(f"Tìm thấy thư viện opus trong hệ thống: {lib_path}")
                    break
                else:
                    # Thử load trực tiếp theo tên thư viện
                    ctypes.cdll.LoadLibrary(lib_name)
                    lib_path = lib_name
                    logger.info(f"Load trực tiếp thư viện opus hệ thống: {lib_name}")
                    break
            except Exception as e:
                logger.debug(f"Load thư viện hệ thống {lib_name} thất bại: {e}")
                continue

    except Exception as e:
        logger.error(f"Tìm thư viện opus hệ thống thất bại: {e}")

    return lib_path


def copy_opus_to_project(system_lib_path):
    """
    Sao chép thư viện hệ thống vào thư mục dự án.
    """
    from .resource_finder import get_project_root

    system, arch_name = get_system_info()

    if not system_lib_path:
        logger.error("Không thể sao chép thư viện opus: đường dẫn thư viện hệ thống rỗng")
        return None

    try:
        # Dùng resource_finder để lấy project root
        project_root = get_project_root()

        # Lấy thư mục đích theo cấu trúc thực tế
        target_path = get_lib_path(system, arch_name)
        target_dir = project_root / target_path

        # Tạo thư mục đích (nếu chưa tồn tại)
        target_dir.mkdir(parents=True, exist_ok=True)

        # Xác định tên file đích
        lib_name = cast(str, get_lib_name(system))
        target_file = target_dir / lib_name

        # Sao chép file
        shutil.copy2(system_lib_path, target_file)
        logger.info(f"Đã sao chép thư viện opus từ {system_lib_path} tới {target_file}")

        return str(target_file)

    except Exception as e:
        logger.error(f"Sao chép thư viện opus vào thư mục dự án thất bại: {e}")
        return None


def setup_opus() -> bool:
    """
    Thiết lập thư viện động opus.
    """
    # Kiểm tra xem runtime_hook đã load chưa
    if hasattr(sys, "_opus_loaded"):
        logger.info("Thư viện opus đã được load bởi runtime hook")
        return True

    # Lấy thông tin hệ thống hiện tại
    system, arch_name = get_system_info()
    logger.info(f"Hệ thống hiện tại: {system}, kiến trúc: {arch_name}")

    # Tạo danh sách đường dẫn tìm kiếm
    search_paths = get_search_paths(system, arch_name)

    # Tìm thư viện local
    lib_path = ""
    lib_dir = ""

    for dir_path, file_name in search_paths:
        full_path = dir_path / file_name
        if full_path.exists():
            lib_path = str(full_path)
            lib_dir = str(dir_path)
            logger.info(f"Tìm thấy file thư viện opus: {lib_path}")
            break

    # Nếu không tìm thấy local, thử tìm từ hệ thống
    if not lib_path:
        logger.warning("Không tìm thấy file thư viện opus ở local, thử load từ hệ thống")
        system_lib_path = find_system_opus()

        if system_lib_path:
            # Thử dùng trực tiếp thư viện hệ thống
            try:
                _ = ctypes.cdll.LoadLibrary(system_lib_path)
                logger.info(f"Đã load thư viện opus từ hệ thống: {system_lib_path}")
                sys._opus_loaded = True
                return True
            except Exception as e:
                logger.warning(f"Load thư viện opus hệ thống thất bại: {e}, thử sao chép vào dự án")

            # Nếu load trực tiếp thất bại, thử sao chép vào dự án
            lib_path = copy_opus_to_project(system_lib_path)
            if lib_path:
                lib_dir = str(Path(lib_path).parent)
            else:
                logger.error("Không thể tìm thấy hoặc sao chép file thư viện opus")
                return False
        else:
            logger.error("Cũng không tìm thấy file thư viện opus trong hệ thống")
            return False

    # Xử lý riêng cho Windows
    if system == PLATFORM.WINDOWS and lib_dir:
        # Thêm đường dẫn tìm DLL
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(lib_dir)
                logger.debug(f"Đã thêm đường dẫn tìm DLL: {lib_dir}")
            except Exception as e:
                logger.warning(f"Thêm đường dẫn tìm DLL thất bại: {e}")

        # Thiết lập biến môi trường
        os.environ["PATH"] = lib_dir + os.pathsep + os.environ.get("PATH", "")

    # Patch đường dẫn thư viện
    _patch_find_library("opus", lib_path)

    # Thử load thư viện
    try:
        # Load DLL và giữ reference để tránh bị GC
        _ = ctypes.CDLL(lib_path)
        logger.info(f"Load thư viện opus thành công: {lib_path}")
        sys._opus_loaded = True
        return True
    except Exception as e:
        logger.error(f"Load thư viện opus thất bại: {e}")
        return False


def _patch_find_library(lib_name: str, lib_path: str):
    """
    Patch hàm ctypes.util.find_library.
    """
    import ctypes.util

    original_find_library = ctypes.util.find_library

    def patched_find_library(name):
        if name == lib_name:
            return lib_path
        return original_find_library(name)

    ctypes.util.find_library = patched_find_library
