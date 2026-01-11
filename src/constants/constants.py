import platform

from src.utils.config_manager import ConfigManager

config = ConfigManager.get_instance()


class ListeningMode:
    """
    Chế độ nghe.
    """

    REALTIME = "realtime"
    AUTO_STOP = "auto_stop"
    MANUAL = "manual"


class AbortReason:
    """
    Lý do hủy bỏ.
    """

    NONE = "none"
    WAKE_WORD_DETECTED = "wake_word_detected"
    USER_INTERRUPTION = "user_interruption"


class DeviceState:
    """
    Trạng thái thiết bị.
    """

    IDLE = "idle"
    CONNECTING = "connecting"
    LISTENING = "listening"
    SPEAKING = "speaking"


class EventType:
    """
    Loại sự kiện.
    """

    SCHEDULE_EVENT = "schedule_event"
    AUDIO_INPUT_READY_EVENT = "audio_input_ready_event"
    AUDIO_OUTPUT_READY_EVENT = "audio_output_ready_event"


def is_official_server(ws_addr: str) -> bool:
    """Xác định xem có phải là địa chỉ máy chủ chính thức của Xiaozhi hay không.

    Args:
        ws_addr (str): WebSocket địa chỉ

    Returns:
        bool: Có phải là máy chủ chính thức của Xiaozhi hay không
    """
    return "api.tenclass.net" in ws_addr


def get_frame_duration() -> int:
    """Lấy độ dài khung hình của thiết bị.

    Returns:
        int: Độ dài khung hình (ms)
    """
    try:
        # Kiểm tra xem có phải máy chủ chính thức không
        ota_url = config.get_config("SYSTEM_OPTIONS.NETWORK.OTA_VERSION_URL")
        if not is_official_server(ota_url):
            return 60

        # Phát hiện thiết bị kiến trúc ARM (như Raspberry Pi)
        machine = platform.machine().lower()
        arm_archs = ["arm", "aarch64", "armv7l", "armv6l"]
        is_arm_device = any(arch in machine for arch in arm_archs)

        if is_arm_device:
            # Thiết bị ARM (như Raspberry Pi) sử dụng độ dài khung lớn hơn để giảm tải CPU
            return 60
        else:
            # Các thiết bị khác (Windows/macOS/Linux x86) có hiệu suất đủ, sử dụng độ trễ thấp
            return 20

    except Exception:
        # Nếu không lấy được, trả về giá trị mặc định 20ms (phù hợp với hầu hết các thiết bị hiện đại)
        return 20


class AudioConfig:
    """
    Cấu hình âm thanh.
    """

    # Cấu hình cố định
    INPUT_SAMPLE_RATE = 16000  # Tốc độ lấy mẫu đầu vào 16kHz
    # Tốc độ lấy mẫu đầu ra: máy chủ chính thức sử dụng 24kHz, các máy chủ khác sử dụng 16kHz
    _ota_url = config.get_config("SYSTEM_OPTIONS.NETWORK.OTA_VERSION_URL")
    OUTPUT_SAMPLE_RATE = 24000 if is_official_server(_ota_url) else 16000
    CHANNELS = 1

    # Lấy độ dài khung hình động
    FRAME_DURATION = get_frame_duration()

    # Tính kích thước khung dựa trên tốc độ lấy mẫu khác nhau
    INPUT_FRAME_SIZE = int(INPUT_SAMPLE_RATE * (FRAME_DURATION / 1000))
    # Hệ thống Linux sử dụng kích thước khung cố định để giảm in PCM, các hệ thống khác tính toán động
    OUTPUT_FRAME_SIZE = int(OUTPUT_SAMPLE_RATE * (FRAME_DURATION / 1000))
