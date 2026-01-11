import asyncio
import json
from typing import Optional

import aiohttp

from src.utils.common_utils import handle_verification_code
from src.utils.device_fingerprint import DeviceFingerprint
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class DeviceActivator:
    """Trình quản lý kích hoạt thiết bị - phiên bản hoàn toàn bất đồng bộ"""

    def __init__(self, config_manager):
        """
        Khởi tạo trình kích hoạt thiết bị.
        """
        self.logger = get_logger(__name__)
        self.config_manager = config_manager
        # Sử dụng instance device_fingerprint để quản lý danh tính thiết bị
        self.device_fingerprint = DeviceFingerprint.get_instance()
        # Đảm bảo thông tin danh tính thiết bị đã được tạo
        self._ensure_device_identity()

        # Nhiệm vụ kích hoạt hiện tại
        self._activation_task: Optional[asyncio.Task] = None

    def _ensure_device_identity(self):
        """
        Đảm bảo thông tin danh tính thiết bị đã được tạo.
        """
        (
            serial_number,
            hmac_key,
            is_activated,
        ) = self.device_fingerprint.ensure_device_identity()
        self.logger.info(
            f"Thông tin danh tính thiết bị: Số sê-ri: {serial_number}, Trạng thái: {'Đã kích hoạt' if is_activated else 'Chưa kích hoạt'}"
        )

    def cancel_activation(self):
        """
        Hủy quy trình kích hoạt.
        """
        if self._activation_task and not self._activation_task.done():
            self.logger.info("Đang hủy nhiệm vụ kích hoạt")
            self._activation_task.cancel()

    def has_serial_number(self) -> bool:
        """
        Kiểm tra xem có số sê-ri hay không.
        """
        return self.device_fingerprint.has_serial_number()

    def get_serial_number(self) -> str:
        """
        Lấy số sê-ri.
        """
        return self.device_fingerprint.get_serial_number()

    def get_hmac_key(self) -> str:
        """
        Lấy khóa HMAC.
        """
        return self.device_fingerprint.get_hmac_key()

    def set_activation_status(self, status: bool) -> bool:
        """
        Thiết lập trạng thái kích hoạt.
        """
        return self.device_fingerprint.set_activation_status(status)

    def is_activated(self) -> bool:
        """
        Kiểm tra xem thiết bị đã được kích hoạt chưa.
        """
        return self.device_fingerprint.is_activated()

    def generate_hmac(self, challenge: str) -> str:
        """
        Sử dụng khóa HMAC để tạo chữ ký.
        """
        return self.device_fingerprint.generate_hmac(challenge)

    async def process_activation(self, activation_data: dict) -> bool:
        """Xử lý quy trình kích hoạt bất đồng bộ.

        Args:
            activation_data: Từ điển chứa thông tin kích hoạt, ít nhất phải chứa challenge và code

        Returns:
            bool: Kích hoạt có thành công hay không
        """
        try:
            # Ghi lại nhiệm vụ hiện tại
            self._activation_task = asyncio.current_task()

            # Kiểm tra xem có challenge kích hoạt và mã xác minh hay không
            if not activation_data.get("challenge"):
                self.logger.error("Thiếu trường challenge trong dữ liệu kích hoạt")
                return False

            if not activation_data.get("code"):
                self.logger.error("Thiếu trường code trong dữ liệu kích hoạt")
                return False

            challenge = activation_data["challenge"]
            code = activation_data["code"]
            message = activation_data.get("message", "Vui lòng nhập mã xác minh tại xiaozhi-ai-iot.vn")
            # Chuẩn hóa nội dung/URL nếu máy chủ trả về domain cũ
            if isinstance(message, str) and "xiaozhi.me" in message:
                message = message.replace("xiaozhi.me", "xiaozhi-ai-iot.vn")

            # Kiểm tra số sê-ri
            if not self.has_serial_number():
                self.logger.error("Thiết bị không có số sê-ri, không thể thực hiện kích hoạt")

                # Sử dụng device_fingerprint để tạo số sê-ri và khóa HMAC
                (
                    serial_number,
                    hmac_key,
                    _,
                ) = self.device_fingerprint.ensure_device_identity()

                if serial_number and hmac_key:
                    self.logger.info("Đã tự động tạo số sê-ri thiết bị và khóa HMAC")
                else:
                    self.logger.error("Tạo số sê-ri hoặc khóa HMAC thất bại")
                    return False

            # Hiển thị thông tin kích hoạt cho người dùng
            self.logger.info(f"Yêu cầu kích hoạt: {message}")
            self.logger.info(f"Mã xác minh: {code}")

            # Xây dựng văn bản gợi ý mã xác minh và in ra
            text = f".Vui lòng đăng nhập vào bảng điều khiển để thêm thiết bị, nhập mã xác minh: {' '.join(code)}..."
            print("\n==================")
            print(text)
            print("==================\n")
            handle_verification_code(text)

            # Phát giọng nói mã xác minh
            try:
                # Phát giọng nói trong luồng không chặn
                from src.utils.common_utils import play_audio_nonblocking

                play_audio_nonblocking(text)
                self.logger.info("Đang phát giọng nói gợi ý mã xác minh")
            except Exception as e:
                self.logger.error(f"Phát giọng nói mã xác minh thất bại: {e}")

            # Thử kích hoạt thiết bị (có truyền mã xác minh để phát lại khi retry)
            return await self.activate(challenge, code)

        except asyncio.CancelledError:
            self.logger.info("Quy trình kích hoạt đã bị hủy")
            return False

    async def activate(self, challenge: str, code: str = None) -> bool:
        """Thực hiện quy trình kích hoạt bất đồng bộ.

        Args:
            challenge: Chuỗi challenge gửi từ máy chủ
            code: Mã xác minh, dùng để phát lại khi thử lại

        Returns:
            bool: Kích hoạt có thành công hay không
        """
        try:
            # Kiểm tra số sê-ri
            serial_number = self.get_serial_number()
            if not serial_number:
                self.logger.error("Thiết bị không có số sê-ri, không thể hoàn thành bước xác minh HMAC")
                return False

            # Tính chữ ký HMAC
            hmac_signature = self.generate_hmac(challenge)
            if not hmac_signature:
                self.logger.error("Không thể tạo chữ ký HMAC, kích hoạt thất bại")
                return False

            # Không bao payload bên ngoài, khớp với định dạng mong đợi của máy chủ
            payload = {
                "Payload": {
                    "algorithm": "hmac-sha256",
                    "serial_number": serial_number,
                    "challenge": challenge,
                    "hmac": hmac_signature,
                }
            }

            # Lấy URL kích hoạt
            ota_url = self.config_manager.get_config(
                "SYSTEM_OPTIONS.NETWORK.OTA_VERSION_URL"
            )
            if not ota_url:
                self.logger.error("Không tìm thấy cấu hình URL OTA")
                return False

            # Đảm bảo URL kết thúc bằng dấu gạch chéo
            if not ota_url.endswith("/"):
                ota_url += "/"

            activate_url = f"{ota_url}activate"
            self.logger.info(f"URL kích hoạt: {activate_url}")

            # Đặt tiêu đề yêu cầu
            headers = {
                "Activation-Version": "2",
                "Device-Id": self.config_manager.get_config("SYSTEM_OPTIONS.DEVICE_ID"),
                "Client-Id": self.config_manager.get_config("SYSTEM_OPTIONS.CLIENT_ID"),
                "Content-Type": "application/json",
            }

            # In thông tin gỡ lỗi
            self.logger.debug(f"Tiêu đề yêu cầu: {headers}")
            payload_str = json.dumps(payload, indent=2, ensure_ascii=False)
            self.logger.debug(f"Tải trọng yêu cầu: {payload_str}")

            # Logic thử lại
            max_retries = 60  # Chờ tối đa 5 phút
            retry_interval = 5  # Đặt khoảng thời gian thử lại là 5 giây

            error_count = 0
            last_error = None

            # Tạo phiên aiohttp, đặt thời gian chờ hợp lý
            timeout = aiohttp.ClientTimeout(total=10)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                for attempt in range(max_retries):
                    try:
                        self.logger.info(
                            f"Đang thử kích hoạt (lần {attempt + 1}/{max_retries})..."
                        )

                        # Phát lại mã xác minh mỗi lần thử lại (bắt đầu từ lần thứ 2)
                        if attempt > 0 and code:
                            try:
                                from src.utils.common_utils import (
                                    play_audio_nonblocking,
                                )

                                text = f".Vui lòng đăng nhập vào bảng điều khiển để thêm thiết bị, nhập mã xác minh: {' '.join(code)}..."
                                play_audio_nonblocking(text)
                                self.logger.info(f"Thử phát lại mã xác minh: {code}")
                            except Exception as e:
                                self.logger.error(f"Thử phát lại xác minh thất bại: {e}")

                        # Gửi yêu cầu kích hoạt
                        # FIX: macOS SSL certificate issue workaround
                        async with session.post(
                            activate_url, headers=headers, json=payload, ssl=False
                        ) as response:
                            # Đọc phản hồi
                            response_text = await response.text()

                            # In phản hồi đầy đủ
                            self.logger.warning(f"\nPhản hồi kích hoạt (HTTP {response.status}):")
                            try:
                                response_json = json.loads(response_text)
                                self.logger.warning(json.dumps(response_json, indent=2))
                            except json.JSONDecodeError:
                                self.logger.warning(response_text)

                            # Kiểm tra mã trạng thái phản hồi
                            if response.status == 200:
                                # Kích hoạt thành công
                                self.logger.info("Thiết bị kích hoạt thành công!")
                                self.set_activation_status(True)
                                return True

                            elif response.status == 202:
                                # Chờ người dùng nhập mã xác minh
                                self.logger.info("Đang chờ người dùng nhập mã xác minh, tiếp tục chờ...")

                                # Sử dụng chờ có thể hủy
                                await asyncio.sleep(retry_interval)

                            else:
                                # Xử lý các lỗi khác nhưng tiếp tục thử lại
                                error_msg = "Lỗi không xác định"
                                try:
                                    error_data = json.loads(response_text)
                                    error_msg = error_data.get(
                                        "error", f"Lỗi không xác định (mã trạng thái: {response.status})"
                                    )
                                except json.JSONDecodeError:
                                    error_msg = (
                                        f"Máy chủ trả về lỗi (mã trạng thái: {response.status})"
                                    )

                                # Ghi lại lỗi nhưng không chấm dứt quy trình
                                if error_msg != last_error:
                                    self.logger.warning(
                                        f"Máy chủ trả về: {error_msg}, tiếp tục chờ xác minh kích hoạt"
                                    )
                                    last_error = error_msg

                                # Đếm lỗi liên tiếp giống nhau
                                if "Device not found" in error_msg:
                                    error_count += 1
                                    if error_count >= 5 and error_count % 5 == 0:
                                        self.logger.warning(
                                            "\nGợi ý: Nếu lỗi vẫn tiếp tục, có thể cần làm mới trang trên trang web để lấy mã xác minh mới\n"
                                        )

                                # Sử dụng chờ có thể hủy
                                await asyncio.sleep(retry_interval)

                    except asyncio.CancelledError:
                        # Phản hồi tín hiệu hủy
                        self.logger.info("Quy trình kích hoạt bị hủy")
                        return False

                    except aiohttp.ClientError as e:
                        self.logger.warning(f"Yêu cầu mạng thất bại: {e}, đang thử lại...")
                        await asyncio.sleep(retry_interval)

                    except asyncio.TimeoutError as e:
                        self.logger.warning(f"Yêu cầu hết thời gian chờ: {e}, đang thử lại...")
                        await asyncio.sleep(retry_interval)

                    except Exception as e:
                        # Lấy chi tiết ngoại lệ
                        import traceback

                        error_detail = (
                            str(e) if str(e) else f"{type(e).__name__}: Lỗi không xác định"
                        )
                        self.logger.warning(
                            f"Xảy ra lỗi trong quá trình kích hoạt: {error_detail}, đang thử lại..."
                        )
                        # In thông tin ngoại lệ đầy đủ trong chế độ gỡ lỗi
                        self.logger.debug(f"Thông tin ngoại lệ đầy đủ: {traceback.format_exc()}")
                        await asyncio.sleep(retry_interval)

            # Đạt số lần thử lại tối đa
            self.logger.error(
                f"Kích hoạt thất bại, đạt số lần thử tối đa ({max_retries}), lỗi cuối cùng: {last_error}"
            )
            return False

        except asyncio.CancelledError:
            self.logger.info("Quy trình kích hoạt bị hủy")
            return False
