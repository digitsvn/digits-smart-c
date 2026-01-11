import hashlib
import hmac
import json
import platform
from pathlib import Path
from typing import Dict, Optional, Tuple

import machineid
import psutil

from src.utils.logging_config import get_logger
from src.utils.resource_finder import find_config_dir

# Lấy logger
logger = get_logger(__name__)


class DeviceFingerprint:
    """Trình thu thập dấu vân tay thiết bị - dùng để tạo định danh thiết bị duy nhất"""

    _instance = None

    def __new__(cls):
        """
        Đảm bảo mô hình singleton.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """
        Khởi tạo trình thu thập dấu vân tay thiết bị.
        """
        if self._initialized:
            return
        self._initialized = True

        self.system = platform.system()
        self._efuse_cache: Optional[Dict] = None  # Cache dữ liệu efuse

        # Khởi tạo đường dẫn tệp
        self._init_file_paths()

        # Đảm bảo tệp efuse tồn tại và đầy đủ khi khởi tạo
        self._ensure_efuse_file()

    def _init_file_paths(self):
        """
        Khởi tạo đường dẫn tệp.
        """
        config_dir = find_config_dir()
        if config_dir:
            self.efuse_file = config_dir / "efuse.json"
            logger.debug(f"Sử dụng thư mục cấu hình: {config_dir}")
        else:
            # Phương án dự phòng: sử dụng đường dẫn tương đối và đảm bảo thư mục tồn tại
            config_path = Path("config")
            config_path.mkdir(parents=True, exist_ok=True)
            self.efuse_file = config_path / "efuse.json"
            logger.info(f"Tạo thư mục cấu hình: {config_path.absolute()}")

    def get_hostname(self) -> str:
        """
        Lấy tên máy chủ.
        """
        return platform.node()

    def _normalize_mac_address(self, mac_address: str) -> str:
        """Chuẩn hóa định dạng địa chỉ MAC thành định dạng phân rã bởi dấu hai chấm chữ thường.

        Args:
            mac_address: Địa chỉ MAC gốc, có thể sử dụng dấu gạch ngang, dấu hai chấm hoặc ký tự phân cách khác

        Returns:
            str: Địa chỉ MAC đã chuẩn hóa, định dạng "00:00:00:00:00:00"
        """
        if not mac_address:
            return mac_address

        # Xóa tất cả các ký tự phân cách có thể, chỉ giữ lại ký tự thập lục phân
        clean_mac = "".join(c for c in mac_address if c.isalnum())

        # Đảm bảo độ dài là 12 ký tự (biểu diễn thập lục phân của 6 byte)
        if len(clean_mac) != 12:
            logger.warning(f"Độ dài địa chỉ MAC không chính xác: {mac_address} -> {clean_mac}")
            return mac_address.lower()

        # Định dạng lại thành chuẩn dấu hai chấm phân cách
        formatted_mac = ":".join(clean_mac[i : i + 2] for i in range(0, 12, 2))

        # Chuyển đổi thành chữ thường
        return formatted_mac.lower()

    def get_mac_address(self) -> Optional[str]:
        """
        Lấy địa chỉ MAC của card mạng chính.
        """
        try:
            # Lấy thông tin địa chỉ của tất cả các giao diện mạng
            net_if_addrs = psutil.net_if_addrs()

            # Ưu tiên chọn địa chỉ MAC của giao diện không phải loopback
            for iface, addrs in net_if_addrs.items():
                # Bỏ qua giao diện loopback
                if iface.lower().startswith(("lo", "loopback")):
                    continue

                for snic in addrs:
                    if snic.family == psutil.AF_LINK and snic.address:
                        # Chuẩn hóa định dạng địa chỉ MAC
                        normalized_mac = self._normalize_mac_address(snic.address)
                        # Lọc bỏ các địa chỉ MAC không hợp lệ
                        if normalized_mac != "00:00:00:00:00:00":
                            return normalized_mac

            # Nếu không tìm thấy địa chỉ MAC phù hợp, trả về None
            logger.warning("Không tìm thấy địa chỉ MAC hợp lệ")
            return None

        except Exception as e:
            logger.error(f"Xảy ra lỗi khi lấy địa chỉ MAC: {e}")
            return None

    def get_machine_id(self) -> Optional[str]:
        """
        Lấy định danh duy nhất của thiết bị.
        """
        try:
            return machineid.id()
        except machineid.MachineIdNotFound:
            logger.warning("Không tìm thấy ID máy")
            return None
        except Exception as e:
            logger.error(f"Xảy ra lỗi khi lấy ID máy: {e}")
            return None

    def _generate_fresh_fingerprint(self) -> Dict:
        """
        Tạo dấu vân tay thiết bị hoàn toàn mới (không dựa vào cache hoặc tệp).
        """
        return {
            "system": self.system,
            "hostname": self.get_hostname(),
            "mac_address": self.get_mac_address(),
            "machine_id": self.get_machine_id(),
        }

    def generate_fingerprint(self) -> Dict:
        """
        Tạo dấu vân tay thiết bị hoàn chỉnh (ưu tiên đọc từ efuse.json).
        """
        # Đầu tiên thử đọc dấu vân tay thiết bị từ efuse.json
        if self.efuse_file.exists():
            try:
                efuse_data = self._load_efuse_data()
                if efuse_data.get("device_fingerprint"):
                    logger.debug("Đọc dấu vân tay thiết bị từ efuse.json")
                    return efuse_data["device_fingerprint"]
            except Exception as e:
                logger.warning(f"Đọc dấu vân tay thiết bị từ efuse.json thất bại: {e}")

        # Nếu đọc thất bại hoặc không tồn tại, tạo dấu vân tay thiết bị mới
        logger.info("Tạo dấu vân tay thiết bị mới")
        return self._generate_fresh_fingerprint()

    def generate_hardware_hash(self) -> str:
        """
        Tạo giá trị băm duy nhất dựa trên thông tin phần cứng.
        """
        fingerprint = self.generate_fingerprint()

        # Trích xuất các định danh phần cứng ít thay đổi nhất
        identifiers = []

        # Tên máy chủ
        hostname = fingerprint.get("hostname")
        if hostname:
            identifiers.append(hostname)

        # Địa chỉ MAC
        mac_address = fingerprint.get("mac_address")
        if mac_address:
            identifiers.append(mac_address)

        # ID máy
        machine_id = fingerprint.get("machine_id")
        if machine_id:
            identifiers.append(machine_id)

        # Nếu không có định danh nào, sử dụng thông tin hệ thống làm dự phòng
        if not identifiers:
            identifiers.append(self.system)
            logger.warning("Không tìm thấy định danh phần cứng, sử dụng thông tin hệ thống làm dự phòng")

        # Nối tất cả các định danh và tính toán giá trị băm
        fingerprint_str = "||".join(identifiers)
        return hashlib.sha256(fingerprint_str.encode("utf-8")).hexdigest()

    def generate_serial_number(self) -> str:
        """
        Tạo số sê-ri thiết bị.
        """
        fingerprint = self.generate_fingerprint()

        # Ưu tiên sử dụng địa chỉ MAC của card mạng chính để tạo số sê-ri
        mac_address = fingerprint.get("mac_address")

        if not mac_address:
            # Nếu không có địa chỉ MAC, sử dụng ID máy hoặc tên máy chủ
            machine_id = fingerprint.get("machine_id")
            hostname = fingerprint.get("hostname")

            if machine_id:
                identifier = machine_id[:12]  # Lấy 12 ký tự đầu
            elif hostname:
                identifier = hostname.replace("-", "").replace("_", "")[:12]
            else:
                identifier = "unknown"

            short_hash = hashlib.md5(identifier.encode()).hexdigest()[:8].upper()
            return f"SN-{short_hash}-{identifier.upper()}"

        # Đảm bảo địa chỉ MAC là chữ thường và không có dấu hai chấm
        mac_clean = mac_address.lower().replace(":", "")
        short_hash = hashlib.md5(mac_clean.encode()).hexdigest()[:8].upper()
        serial_number = f"SN-{short_hash}-{mac_clean}"
        return serial_number

    def _ensure_efuse_file(self):
        """
        Đảm bảo tệp efuse tồn tại và chứa thông tin đầy đủ.
        """
        logger.info(f"Kiểm tra tệp efuse: {self.efuse_file.absolute()}")

        # Tạo dấu vân tay thiết bị trước (để đảm bảo thông tin phần cứng khả dụng)
        fingerprint = self._generate_fresh_fingerprint()
        mac_address = fingerprint.get("mac_address")

        if not self.efuse_file.exists():
            logger.info("Tệp efuse.json không tồn tại, tạo tệp mới")
            self._create_new_efuse_file(fingerprint, mac_address)
        else:
            logger.info("Tệp efuse.json đã tồn tại, xác minh tính toàn vẹn")
            self._validate_and_fix_efuse_file(fingerprint, mac_address)

    def _create_new_efuse_file(self, fingerprint: Dict, mac_address: Optional[str]):
        """
        Tạo tệp efuse mới.
        """
        # Tạo số sê-ri và khóa HMAC
        serial_number = self.generate_serial_number()
        hmac_key = self.generate_hardware_hash()

        logger.info(f"Tạo số sê-ri: {serial_number}")
        logger.debug(f"Tạo khóa HMAC: {hmac_key[:8]}...")  # Chỉ ghi lại 8 ký tự đầu

        # Tạo dữ liệu efuse đầy đủ
        efuse_data = {
            "mac_address": mac_address,
            "serial_number": serial_number,
            "hmac_key": hmac_key,
            "activation_status": False,
            "device_fingerprint": fingerprint,
        }

        # Đảm bảo thư mục tồn tại
        self.efuse_file.parent.mkdir(parents=True, exist_ok=True)

        # Ghi dữ liệu
        success = self._save_efuse_data(efuse_data)
        if success:
            logger.info(f"Đã tạo tệp cấu hình efuse: {self.efuse_file}")
        else:
            logger.error("Tạo tệp cấu hình efuse thất bại")

    def _validate_and_fix_efuse_file(
        self, fingerprint: Dict, mac_address: Optional[str]
    ):
        """
        Xác minh và sửa chữa tính toàn vẹn của tệp efuse.
        """
        try:
            efuse_data = self._load_efuse_data_from_file()

            # Kiểm tra các trường bắt buộc có tồn tại hay không
            required_fields = [
                "mac_address",
                "serial_number",
                "hmac_key",
                "activation_status",
                "device_fingerprint",
            ]
            missing_fields = [
                field for field in required_fields if field not in efuse_data
            ]

            if missing_fields:
                logger.warning(f"Tệp cấu hình efuse thiếu các trường: {missing_fields}")
                self._fix_missing_fields(
                    efuse_data, missing_fields, fingerprint, mac_address
                )
            else:
                logger.debug("Kiểm tra tính toàn vẹn tệp cấu hình efuse thành công")
                # Cập nhật cache
                self._efuse_cache = efuse_data

        except Exception as e:
            logger.error(f"Lỗi khi xác minh tệp cấu hình efuse: {e}")
            # Nếu xác minh thất bại, tạo lại tệp
            logger.info("Tạo lại tệp cấu hình efuse")
            self._create_new_efuse_file(fingerprint, mac_address)

    def _fix_missing_fields(
        self,
        efuse_data: Dict,
        missing_fields: list,
        fingerprint: Dict,
        mac_address: Optional[str],
    ):
        """
        Sửa chữa các trường bị thiếu.
        """
        for field in missing_fields:
            if field == "device_fingerprint":
                efuse_data[field] = fingerprint
            elif field == "mac_address":
                efuse_data[field] = mac_address
            elif field == "serial_number":
                efuse_data[field] = self.generate_serial_number()
            elif field == "hmac_key":
                efuse_data[field] = self.generate_hardware_hash()
            elif field == "activation_status":
                efuse_data[field] = False

        # Lưu dữ liệu đã sửa chữa
        success = self._save_efuse_data(efuse_data)
        if success:
            logger.info("Đã sửa tệp cấu hình efuse")
        else:
            logger.error("Sửa tệp cấu hình efuse thất bại")

    def _load_efuse_data_from_file(self) -> Dict:
        """
        Tải dữ liệu efuse trực tiếp từ tệp (không dùng cache).
        """
        with open(self.efuse_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_efuse_data(self) -> Dict:
        """
        Tải dữ liệu efuse (có cache).
        """
        # Nếu có cache, trả về trực tiếp
        if self._efuse_cache is not None:
            return self._efuse_cache

        try:
            data = self._load_efuse_data_from_file()
            # Cache dữ liệu
            self._efuse_cache = data
            return data
        except Exception as e:
            logger.error(f"Tải dữ liệu efuse thất bại: {e}")
            # Trả về dữ liệu mặc định rỗng, nhưng không cache
            return {
                "mac_address": None,
                "serial_number": None,
                "hmac_key": None,
                "activation_status": False,
                "device_fingerprint": {},
            }

    def _save_efuse_data(self, data: Dict) -> bool:
        """
        Lưu dữ liệu efuse.
        """
        try:
            # Đảm bảo thư mục tồn tại
            self.efuse_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.efuse_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            # Cập nhật cache
            self._efuse_cache = data
            logger.debug(f"Dữ liệu efuse đã được lưu vào: {self.efuse_file}")
            return True
        except Exception as e:
            logger.error(f"Lưu dữ liệu efuse thất bại: {e}")
            return False

    def ensure_device_identity(self) -> Tuple[Optional[str], Optional[str], bool]:
        """
        Đảm bảo thông tin định danh thiết bị đã được tải - trả về số sê-ri, khóa HMAC và trạng thái kích hoạt

        Returns:
            Tuple[Optional[str], Optional[str], bool]: (số sê-ri, khóa HMAC, trạng thái kích hoạt)
        """
        # Tải dữ liệu efuse (lúc này tệp nên đã tồn tại và hoàn chỉnh)
        efuse_data = self._load_efuse_data()

        # Lấy số sê-ri, khóa HMAC và trạng thái kích hoạt
        serial_number = efuse_data.get("serial_number")
        hmac_key = efuse_data.get("hmac_key")
        is_activated = efuse_data.get("activation_status", False)

        return serial_number, hmac_key, is_activated

    def has_serial_number(self) -> bool:
        """
        Kiểm tra xem có số sê-ri hay không.
        """
        efuse_data = self._load_efuse_data()
        return efuse_data.get("serial_number") is not None

    def get_serial_number(self) -> Optional[str]:
        """
        Lấy số sê-ri.
        """
        efuse_data = self._load_efuse_data()
        return efuse_data.get("serial_number")

    def get_hmac_key(self) -> Optional[str]:
        """
        Lấy khóa HMAC.
        """
        efuse_data = self._load_efuse_data()
        return efuse_data.get("hmac_key")

    def get_mac_address_from_efuse(self) -> Optional[str]:
        """
        Lấy địa chỉ MAC từ efuse.json.
        """
        efuse_data = self._load_efuse_data()
        return efuse_data.get("mac_address")

    def set_activation_status(self, status: bool) -> bool:
        """
        Thiết lập trạng thái kích hoạt.
        """
        efuse_data = self._load_efuse_data()
        efuse_data["activation_status"] = status
        return self._save_efuse_data(efuse_data)

    def is_activated(self) -> bool:
        """
        Kiểm tra xem thiết bị đã được kích hoạt hay chưa.
        """
        efuse_data = self._load_efuse_data()
        return efuse_data.get("activation_status", False)

    def generate_hmac(self, challenge: str) -> Optional[str]:
        """
        Sử dụng khóa HMAC để tạo chữ ký.
        """
        if not challenge:
            logger.error("Chuỗi thử thách không được để trống")
            return None

        hmac_key = self.get_hmac_key()

        if not hmac_key:
            logger.error("Không tìm thấy khóa HMAC, không thể tạo chữ ký")
            return None

        try:
            # Tính toán chữ ký HMAC-SHA256
            signature = hmac.new(
                hmac_key.encode(), challenge.encode(), hashlib.sha256
            ).hexdigest()

            return signature
        except Exception as e:
            logger.error(f"Tạo chữ ký HMAC thất bại: {e}")
            return None

    @classmethod
    def get_instance(cls) -> "DeviceFingerprint":
        """
        Lấy instance dấu vân tay thiết bị.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
