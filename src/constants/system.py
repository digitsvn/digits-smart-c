from enum import Enum


class InitializationStage(Enum):
    """
    De phan nay tieng Anh cho de hieu
    """

    DEVICE_FINGERPRINT = "Phase 1: Device Identity Preparation"
    CONFIG_MANAGEMENT = "Phase 2: Configuration Management Initialization"
    OTA_CONFIG = "Phase 3: OTA Configuration Acquisition"
    ACTIVATION = "Phase 4: Activation Process"


class SystemConstants:
    """
   System constants.
    """

    # Thông tin ứng dụng (giữ nguyên để tương thích giao thức/máy chủ)
    APP_NAME = "py-xiaozhi"
    APP_VERSION = "2.0.0"
    BOARD_TYPE = "bread-compact-wifi"

    # Thiết lập timeout mặc định
    DEFAULT_TIMEOUT = 10
    ACTIVATION_MAX_RETRIES = 60
    ACTIVATION_RETRY_INTERVAL = 5

    # Hằng số tên file
    CONFIG_FILE = "config.json"
    EFUSE_FILE = "efuse.json"
