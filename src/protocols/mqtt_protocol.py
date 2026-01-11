import asyncio
import json
import socket
import threading
import time

import paho.mqtt.client as mqtt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from src.constants.constants import AudioConfig
from src.protocols.protocol import Protocol
from src.utils.config_manager import ConfigManager
from src.utils.logging_config import get_logger

# Cấu hình log
logger = get_logger(__name__)


class MqttProtocol(Protocol):
    def __init__(self, loop):
        super().__init__()
        self.loop = loop
        self.config = ConfigManager.get_instance()
        self.mqtt_client = None
        self.udp_socket = None
        self.udp_thread = None
        self.udp_running = False
        self.connected = False

        # Giám sát trạng thái kết nối
        self._is_closing = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 0  # Mặc định không kết nối lại
        self._auto_reconnect_enabled = False  # Mặc định tắt tự động kết nối lại
        self._connection_monitor_task = None
        self._last_activity_time = None
        self._keep_alive_interval = 60  # Khoảng thời gian keep-alive MQTT (giây)
        self._connection_timeout = 120  # Thời gian chờ kết nối (giây)

        # Cấu hình MQTT
        self.endpoint = None
        self.client_id = None
        self.username = None
        self.password = None
        self.publish_topic = None
        self.subscribe_topic = None

        # Cấu hình UDP
        self.udp_server = ""
        self.udp_port = 0
        self.aes_key = None
        self.aes_nonce = None
        self.local_sequence = 0
        self.remote_sequence = 0

        # Sự kiện
        self.server_hello_event = asyncio.Event()

    def _parse_endpoint(self, endpoint: str) -> tuple[str, int]:
        """Phân tích chuỗi endpoint, trích xuất máy chủ và cổng.

        Tham số:
            endpoint: Chuỗi endpoint, định dạng có thể là:
                     - "hostname" (sử dụng cổng mặc định 8883)
                     - "hostname:port" (sử dụng cổng được chỉ định)

        Trả về:
            tuple: (host, port) tên máy chủ báo và số cổng
        """
        if not endpoint:
            raise ValueError("Endpoint không được để trống")

        # Kiểm tra xem có chứa cổng không
        if ":" in endpoint:
            host, port_str = endpoint.rsplit(":", 1)
            try:
                port = int(port_str)
                if port < 1 or port > 65535:
                    raise ValueError(f"Số cổng phải nằm trong khoảng 1-65535: {port}")
            except ValueError as e:
                raise ValueError(f"Số cổng không hợp lệ: {port_str}") from e
        else:
            # Không chỉ định cổng, sử dụng cổng mặc định 8883
            host = endpoint
            port = 8883

        return host, port

    async def connect(self):
        """
        Kết nối đến máy chủ MQTT.
        """
        if self._is_closing:
            logger.warning("Kết nối đang đóng, hủy các nỗ lực kết nối mới")
            return False

        # Đặt lại sự kiện hello
        self.server_hello_event = asyncio.Event()

        # Trước hết cố gắng lấy cấu hình MQTT
        try:
            # Cố gắng lấy cấu hình MQTT từ máy chủ OTA
            mqtt_config = self.config.get_config("SYSTEM_OPTIONS.NETWORK.MQTT_INFO")

            print(mqtt_config)

            # Cập nhật cấu hình MQTT
            self.endpoint = mqtt_config.get("endpoint")
            self.client_id = mqtt_config.get("client_id")
            self.username = mqtt_config.get("username")
            self.password = mqtt_config.get("password")
            self.publish_topic = mqtt_config.get("publish_topic")
            self.subscribe_topic = mqtt_config.get("subscribe_topic")

            logger.info(f"Đã lấy cấu hình MQTT từ máy chủ OTA: {self.endpoint}")
        except Exception as e:
            logger.warning(f"Lấy cấu hình MQTT từ máy chủ OTA thất bại: {e}")

        # Xác minh cấu hình MQTT
        if (
            not self.endpoint
            or not self.username
            or not self.password
            or not self.publish_topic
        ):
            logger.error("Cấu hình MQTT không đầy đủ")
            if self._on_network_error:
                await self._on_network_error("Cấu hình MQTT không đầy đủ")
            return False

        # subscribe_topic có thể là chuỗi "null", cần xử lý đặc biệt
        if self.subscribe_topic == "null":
            self.subscribe_topic = None
            logger.info("Chủ đề đăng ký là null, sẽ không đăng ký bất kỳ chủ đề nào")

        # Nếu đã có client MQTT, ngắt kết nối trước
        if self.mqtt_client:
            try:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            except Exception as e:
                logger.warning(f"Lỗi khi ngắt kết nối client MQTT: {e}")

        # Phân tích endpoint, trích xuất máy chủ và cổng
        try:
            host, port = self._parse_endpoint(self.endpoint)
            use_tls = port == 8883  # Chỉ sử dụng TLS khi dùng cổng 8883

            logger.info(
                f"Phân tích endpoint: {self.endpoint} -> Máy chủ: {host}, Cổng: {port}, Sử dụng TLS: {use_tls}"
            )
        except ValueError as e:
            logger.error(f"Phân tích endpoint thất bại: {e}")
            if self._on_network_error:
                await self._on_network_error(f"Phân tích endpoint thất bại: {e}")
            return False

        # Tạo client MQTT mới
        self.mqtt_client = mqtt.Client(client_id=self.client_id)
        self.mqtt_client.username_pw_set(self.username, self.password)

        # Quyết định xem có định cấu hình kết nối mã hóa TLS dựa trên cổng hay không
        if use_tls:
            try:
                self.mqtt_client.tls_set(
                    ca_certs=None,
                    certfile=None,
                    keyfile=None,
                    cert_reqs=mqtt.ssl.CERT_REQUIRED,
                    tls_version=mqtt.ssl.PROTOCOL_TLS,
                )
                logger.info("Đã định cấu hình kết nối mã hóa TLS")
            except Exception as e:
                logger.error(f"Cấu hình TLS thất bại, không thể kết nối an toàn đến máy chủ MQTT: {e}")
                if self._on_network_error:
                    await self._on_network_error(f"Cấu hình TLS thất bại: {str(e)}")
                return False
        else:
            logger.info("Sử dụng kết nối không TLS")

        # Tạo Future kết nối
        connect_future = self.loop.create_future()

        def on_connect_callback(client, userdata, flags, rc, properties=None):
            if rc == 0:
                logger.info("Đã kết nối đến máy chủ MQTT")
                self._last_activity_time = time.time()
                self.loop.call_soon_threadsafe(lambda: connect_future.set_result(True))
            else:
                logger.error(f"Kết nối máy chủ MQTT thất bại, mã trả về: {rc}")
                self.loop.call_soon_threadsafe(
                    lambda: connect_future.set_exception(
                        Exception(f"Kết nối máy chủ MQTT thất bại, mã trả về: {rc}")
                    )
                )

        def on_message_callback(client, userdata, msg):
            try:
                self._last_activity_time = time.time()  # Cập nhật thời gian hoạt động
                payload = msg.payload.decode("utf-8")
                self._handle_mqtt_message(payload)
            except Exception as e:
                logger.error(f"Lỗi khi xử lý tin nhắn MQTT: {e}")

        def on_disconnect_callback(client, userdata, rc):
            """MQTT ngắt kết nối callback.

            Args:
                client: Instance client MQTT
                userdata: Dữ liệu người dùng
                rc: Mã trả về (0=ngắt kết nối bình thường, >0=ngắt kết nối bất thường)
            """
            try:
                if rc == 0:
                    logger.info("Kết nối MQTT ngắt bình thường")
                else:
                    logger.warning(f"Kết nối MQTT ngắt bất thường, mã trả về: {rc}")

                was_connected = self.connected
                self.connected = False

                # Thông báo thay đổi trạng thái kết nối
                if self._on_connection_state_changed and was_connected:
                    reason = "Ngắt bình thường" if rc == 0 else f"Ngắt bất thường(rc={rc})"
                    self.loop.call_soon_threadsafe(
                        lambda: self._on_connection_state_changed(False, reason)
                    )

                # Dừng luồng nhận UDP
                self._stop_udp_receiver()

                # Chỉ thử kết nối lại khi ngắt bất thường và bật tự động kết nối lại
                if (
                    rc != 0
                    and not self._is_closing
                    and self._auto_reconnect_enabled
                    and self._reconnect_attempts < self._max_reconnect_attempts
                ):
                    # Lên lịch kết nối lại trong vòng lặp sự kiện
                    self.loop.call_soon_threadsafe(
                        lambda: asyncio.create_task(
                            self._attempt_reconnect(f"Ngắt MQTT(rc={rc})")
                        )
                    )
                else:
                    # Thông báo đóng kênh âm thanh
                    if self._on_audio_channel_closed:
                        asyncio.run_coroutine_threadsafe(
                            self._on_audio_channel_closed(), self.loop
                        )

                    # Thông báo lỗi mạng
                    if rc != 0 and self._on_network_error:
                        error_msg = f"Kết nối MQTT bị ngắt: {rc}"
                        if (
                            self._auto_reconnect_enabled
                            and self._reconnect_attempts >= self._max_reconnect_attempts
                        ):
                            error_msg += " (Kết nối lại thất bại)"
                        self.loop.call_soon_threadsafe(
                            lambda: self._on_network_error(error_msg)
                        )

            except Exception as e:
                logger.error(f"Xử lý ngắt kết nối MQTT thất bại: {e}")

        def on_publish_callback(client, userdata, mid):
            """
            Callback xuất bản tin nhắn MQTT.
            """
            self._last_activity_time = time.time()  # Cập nhật thời gian hoạt động

        def on_subscribe_callback(client, userdata, mid, granted_qos):
            """
            Callback đăng ký MQTT.
            """
            logger.info(f"Đăng ký thành công, chủ đề: {self.subscribe_topic}")
            self._last_activity_time = time.time()  # Cập nhật thời gian hoạt động

        # Thiết lập callback
        self.mqtt_client.on_connect = on_connect_callback
        self.mqtt_client.on_message = on_message_callback
        self.mqtt_client.on_disconnect = on_disconnect_callback
        self.mqtt_client.on_publish = on_publish_callback
        self.mqtt_client.on_subscribe = on_subscribe_callback

        try:
            # Kết nối đến máy chủ MQTT, cấu hình khoảng thời gian keepalive
            logger.info(f"Đang kết nối đến máy chủ MQTT: {host}:{port}")
            self.mqtt_client.connect_async(
                host, port, keepalive=self._keep_alive_interval
            )
            self.mqtt_client.loop_start()

            # Chờ kết nối hoàn tất
            await asyncio.wait_for(connect_future, timeout=10.0)

            # Đăng ký chủ đề
            if self.subscribe_topic:
                self.mqtt_client.subscribe(self.subscribe_topic, qos=1)

            # Khởi động giám sát kết nối
            self._start_connection_monitor()

            # Gửi tin nhắn hello
            hello_message = {
                "type": "hello",
                "version": 3,
                "features": {
                    "mcp": True,
                },
                "transport": "udp",
                "audio_params": {
                    "format": "opus",
                    "sample_rate": AudioConfig.OUTPUT_SAMPLE_RATE,
                    "channels": AudioConfig.CHANNELS,
                    "frame_duration": AudioConfig.FRAME_DURATION,
                },
            }

            # Gửi tin nhắn và chờ phản hồi
            if not await self.send_text(json.dumps(hello_message)):
                logger.error("Gửi tin nhắn hello thất bại")
                return False

            try:
                await asyncio.wait_for(self.server_hello_event.wait(), timeout=10.0)
            except asyncio.TimeoutError:
                logger.error("Chờ tin nhắn hello từ máy chủ quá thời gian")
                if self._on_network_error:
                    await self._on_network_error("Chờ phản hồi quá thời gian")
                return False

            # Tạo socket UDP
            try:
                if self.udp_socket:
                    self.udp_socket.close()

                self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.udp_socket.settimeout(0.5)

                # Khởi động luồng nhận UDP
                if self.udp_thread and self.udp_thread.is_alive():
                    self.udp_running = False
                    self.udp_thread.join(1.0)

                self.udp_running = True
                self.udp_thread = threading.Thread(target=self._udp_receive_thread)
                self.udp_thread.daemon = True
                self.udp_thread.start()

                self.connected = True
                self._reconnect_attempts = 0  # Đặt lại bộ đếm kết nối lại

                # Thông báo thay đổi trạng thái kết nối
                if self._on_connection_state_changed:
                    self._on_connection_state_changed(True, "Kết nối thành công")

                return True
            except Exception as e:
                logger.error(f"Tạo socket UDP thất bại: {e}")
                if self._on_network_error:
                    await self._on_network_error(f"Tạo kết nối UDP thất bại: {e}")
                return False

        except Exception as e:
            logger.error(f"Kết nối máy chủ MQTT thất bại: {e}")
            if self._on_network_error:
                await self._on_network_error(f"Kết nối máy chủ MQTT thất bại: {e}")
            return False

    def _handle_mqtt_message(self, payload):
        """
        Xử lý tin nhắn MQTT.
        """
        try:
            data = json.loads(payload)
            msg_type = data.get("type")

            if msg_type == "goodbye":
                # Xử lý tin nhắn goodbye
                session_id = data.get("session_id")
                if not session_id or session_id == self.session_id:
                    # Thực hiện dọn dẹp trong vòng lặp sự kiện chính
                    asyncio.run_coroutine_threadsafe(self._handle_goodbye(), self.loop)
                return

            elif msg_type == "hello":
                print("Liên kết dịch vụ trả về cấu hình khởi tạo", data)
                # Xử lý phản hồi hello từ máy chủ
                transport = data.get("transport")
                if transport != "udp":
                    logger.error(f"Giao thức truyền không hỗ trợ: {transport}")
                    return

                # Lấy ID phiên
                self.session_id = data.get("session_id", "")

                # Lấy cấu hình UDP
                udp = data.get("udp")
                if not udp:
                    logger.error("Thiếu cấu hình UDP")
                    return

                self.udp_server = udp.get("server")
                self.udp_port = udp.get("port")
                self.aes_key = udp.get("key")
                self.aes_nonce = udp.get("nonce")

                # Đặt lại số thứ tự
                self.local_sequence = 0
                self.remote_sequence = 0

                logger.info(
                    f"Nhận được phản hồi hello từ máy chủ, máy chủ UDP: {self.udp_server}:{self.udp_port}"
                )

                # Thiết lập sự kiện hello
                self.loop.call_soon_threadsafe(self.server_hello_event.set)

                # Kích hoạt callback mở kênh âm thanh
                if self._on_audio_channel_opened:
                    self.loop.call_soon_threadsafe(
                        lambda: asyncio.create_task(self._on_audio_channel_opened())
                    )

            else:
                # Xử lý các tin nhắn JSON khác
                if self._on_incoming_json:

                    def process_json(json_data=data):
                        if asyncio.iscoroutinefunction(self._on_incoming_json):
                            coro = self._on_incoming_json(json_data)
                            if coro is not None:
                                asyncio.create_task(coro)
                        else:
                            self._on_incoming_json(json_data)

                    self.loop.call_soon_threadsafe(process_json)
        except json.JSONDecodeError:
            logger.error(f"Dữ liệu JSON không hợp lệ: {payload}")
        except Exception as e:
            logger.error(f"Lỗi khi xử lý tin nhắn MQTT: {e}")

    def _udp_receive_thread(self):
        """Luồng nhận UDP.

        Tham khảo cách triển khai của audio_player.py
        """
        logger.info(
            f"Luồng nhận UDP đã khởi động, đang lắng nghe dữ liệu từ {self.udp_server}:{self.udp_port}"
        )

        self.udp_running = True
        debug_counter = 0

        while self.udp_running:
            try:
                data, addr = self.udp_socket.recvfrom(4096)
                debug_counter += 1

                try:
                    # Xác minh gói dữ liệu
                    if len(data) < 16:  # Cần ít nhất 16 byte nonce
                        logger.error(f"Kích thước gói dữ liệu âm thanh không hợp lệ: {len(data)}")
                        continue

                    # Tách nonce và dữ liệu mã hóa
                    received_nonce = data[:16]
                    encrypted_audio = data[16:]

                    # Sử dụng AES-CTR để giải mã
                    decrypted = self.aes_ctr_decrypt(
                        bytes.fromhex(self.aes_key), received_nonce, encrypted_audio
                    )

                    # Thông tin gỡ lỗi
                    if debug_counter % 100 == 0:
                        logger.debug(
                            f"Đã giải mã gói dữ liệu âm thanh #{debug_counter}, kích thước: {len(decrypted)} byte"
                        )

                    # Xử lý dữ liệu âm thanh sau giải mã
                    if self._on_incoming_audio:

                        def process_audio(audio_data=decrypted):
                            if asyncio.iscoroutinefunction(self._on_incoming_audio):
                                coro = self._on_incoming_audio(audio_data)
                                if coro is not None:
                                    asyncio.create_task(coro)
                            else:
                                self._on_incoming_audio(audio_data)

                        self.loop.call_soon_threadsafe(process_audio)

                except Exception as e:
                    logger.error(f"Lỗi xử lý gói dữ liệu âm thanh: {e}")
                    continue

            except socket.timeout:
                # Quá thời gian chờ là bình thường, tiếp tục vòng lặp
                pass
            except Exception as e:
                logger.error(f"Lỗi luồng nhận UDP: {e}")
                if not self.udp_running:
                    break
                time.sleep(0.1)  # Tránh tiêu thụ quá nhiều CPU trong trường hợp lỗi

        logger.info("Luồng nhận UDP đã dừng")

    async def send_text(self, message):
        """
        Gửi tin nhắn văn bản.
        """
        if not self.mqtt_client:
            logger.error("Client MQTT chưa được khởi tạo")
            return False

        try:
            result = self.mqtt_client.publish(self.publish_topic, message)
            result.wait_for_publish()
            return True
        except Exception as e:
            logger.error(f"Gửi tin nhắn MQTT thất bại: {e}")
            if self._on_network_error:
                await self._on_network_error(f"Gửi tin nhắn MQTT thất bại: {e}")
            return False

    async def send_audio(self, audio_data):
        """Gửi dữ liệu âm thanh.

        Tham khảo cách triển khai của audio_sender.py
        """
        if not self.udp_socket or not self.udp_server or not self.udp_port:
            logger.error("Kênh UDP chưa được khởi tạo")
            return False

        try:
            # Tạo nonce mới (tương tự như trong audio_sender.py)
            # Định dạng: 0x01 (1 byte) + 0x00 (3 byte) + độ dài (2 byte) + nonce gốc (8 byte) + số thứ tự (8 byte)
            self.local_sequence = (self.local_sequence + 1) & 0xFFFFFFFF
            new_nonce = (
                self.aes_nonce[:4]  # Tiền tố cố định
                + format(len(audio_data), "04x")  # Độ dài dữ liệu
                + self.aes_nonce[8:24]  # Nonce gốc
                + format(self.local_sequence, "08x")  # Số thứ tự
            )

            encrypt_encoded_data = self.aes_ctr_encrypt(
                bytes.fromhex(self.aes_key), bytes.fromhex(new_nonce), bytes(audio_data)
            )

            # Ghép nonce và dữ liệu mã hóa
            packet = bytes.fromhex(new_nonce) + encrypt_encoded_data

            # Gửi gói dữ liệu
            self.udp_socket.sendto(packet, (self.udp_server, self.udp_port))

            # In nhật ký mỗi 10 gói gửi đi
            if self.local_sequence % 10 == 0:
                logger.info(
                    f"Đã gửi gói dữ liệu âm thanh, số thứ tự: {self.local_sequence}，đích: "
                    f"{self.udp_server}:{self.udp_port}"
                )

            self.local_sequence += 1
            return True
        except Exception as e:
            logger.error(f"Gửi dữ liệu âm thanh thất bại: {e}")
            if self._on_network_error:
                asyncio.create_task(self._on_network_error(f"Gửi dữ liệu âm thanh thất bại: {e}"))
            return False

    async def open_audio_channel(self):
        """
        Mở kênh âm thanh.
        """
        if not self.connected:
            return await self.connect()
        return True

    async def close_audio_channel(self):
        """
        Đóng kênh âm thanh.
        """
        self._is_closing = True

        try:
            # Nếu có ID phiên, gửi tin nhắn goodbye
            if self.session_id:
                goodbye_msg = {"type": "goodbye", "session_id": self.session_id}
                await self.send_text(json.dumps(goodbye_msg))

            # Xử lý goodbye
            await self._handle_goodbye()

        except Exception as e:
            logger.error(f"Lỗi khi đóng kênh âm thanh: {e}")
            # Đảm bảo gọi callback ngay cả khi có lỗi
            if self._on_audio_channel_closed:
                await self._on_audio_channel_closed()
        finally:
            self._is_closing = False

    def is_audio_channel_opened(self) -> bool:
        """Kiểm tra xem kênh âm thanh đã mở hay chưa.

        Kiểm tra chính xác hơn trạng thái kết nối, bao gồm trạng thái thực tế của MQTT và UDP
        """
        if not self.connected or self._is_closing:
            return False

        # Kiểm tra trạng thái kết nối MQTT
        if not self.mqtt_client or not self.mqtt_client.is_connected():
            return False

        # Kiểm tra trạng thái kết nối UDP
        return self.udp_socket is not None and self.udp_running

    def aes_ctr_encrypt(self, key, nonce, plaintext):
        """Hàm mã hóa chế độ AES-CTR
        Args:
            key: Khóa mã hóa dạng bytes
            nonce: Vector khởi tạo dạng bytes
            plaintext: Dữ liệu gốc cần mã hóa
        Returns:
            Dữ liệu đã mã hóa dạng bytes
        """
        cipher = Cipher(
            algorithms.AES(key), modes.CTR(nonce), backend=default_backend()
        )
        encryptor = cipher.encryptor()
        return encryptor.update(plaintext) + encryptor.finalize()

    def aes_ctr_decrypt(self, key, nonce, ciphertext):
        """Hàm giải mã chế độ AES-CTR
        Args:
            key: Khóa giải mã dạng bytes
            nonce: Vector khởi tạo dạng bytes (phải giống như khi mã hóa)
            ciphertext: Dữ liệu đã mã hóa dạng bytes
        Returns:
            Dữ liệu gốc sau khi giải mã dạng bytes
        """
        cipher = Cipher(
            algorithms.AES(key), modes.CTR(nonce), backend=default_backend()
        )
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        return plaintext

    async def _handle_goodbye(self):
        """
        Xử lý tin nhắn goodbye.
        """
        try:
            # Dừng luồng nhận UDP
            if self.udp_thread and self.udp_thread.is_alive():
                self.udp_running = False
                self.udp_thread.join(1.0)
                self.udp_thread = None
            logger.info("Luồng nhận UDP đã dừng")

            # Đóng socket UDP
            if self.udp_socket:
                try:
                    self.udp_socket.close()
                except Exception as e:
                    logger.error(f"Đóng socket UDP thất bại: {e}")
                self.udp_socket = None

            # Dừng client MQTT
            if self.mqtt_client:
                try:
                    self.mqtt_client.loop_stop()
                    self.mqtt_client.disconnect()
                    self.mqtt_client.loop_forever()  # Đảm bảo ngắt kết nối hoàn toàn
                except Exception as e:
                    logger.error(f"Ngắt kết nối MQTT thất bại: {e}")
                self.mqtt_client = None

            # Đặt lại tất cả trạng thái
            self.connected = False
            self.session_id = None
            self.local_sequence = 0
            self.remote_sequence = 0
            self.udp_server = ""
            self.udp_port = 0
            self.aes_key = None
            self.aes_nonce = None

            # Gọi callback đóng kênh âm thanh
            if self._on_audio_channel_closed:
                await self._on_audio_channel_closed()

        except Exception as e:
            logger.error(f"Lỗi khi xử lý tin nhắn goodbye: {e}")

    def _stop_udp_receiver(self):
        """
        Dừng luồng nhận UDP và đóng socket UDP.
        """
        # Đóng luồng nhận UDP
        if (
            hasattr(self, "udp_thread")
            and self.udp_thread
            and self.udp_thread.is_alive()
        ):
            self.udp_running = False
            try:
                self.udp_thread.join(1.0)
            except RuntimeError:
                pass  # Xử lý trường hợp luồng đã kết thúc

        # Đóng socket UDP
        if hasattr(self, "udp_socket") and self.udp_socket:
            try:
                self.udp_socket.close()
            except Exception as e:
                logger.error(f"Đóng socket UDP thất bại: {e}")

    def __del__(self):
        """
        Hàm hủy, dọn dẹp tài nguyên.
        """
        # Dừng các tài nguyên liên quan đến nhận UDP
        self._stop_udp_receiver()

        # Đóng client MQTT
        if hasattr(self, "mqtt_client") and self.mqtt_client:
            try:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
                self.mqtt_client.loop_forever()  # Đảm bảo ngắt kết nối hoàn toàn
            except Exception as e:
                logger.error(f"Ngắt kết nối MQTT thất bại: {e}")

    def _start_connection_monitor(self):
        """
        Khởi động tác vụ giám sát kết nối.
        """
        if (
            self._connection_monitor_task is None
            or self._connection_monitor_task.done()
        ):
            self._connection_monitor_task = asyncio.create_task(
                self._connection_monitor()
            )

    async def _connection_monitor(self):
        """
        Giám sát tình trạng sức khỏe kết nối.
        """
        try:
            while self.connected and not self._is_closing:
                await asyncio.sleep(30)  # Kiểm tra mỗi 30 giây

                # Kiểm tra trạng thái kết nối MQTT
                if self.mqtt_client and not self.mqtt_client.is_connected():
                    logger.warning("Phát hiện kết nối MQTT đã ngắt")
                    await self._handle_connection_loss("Kiểm tra kết nối MQTT thất bại")
                    break

                # Kiểm tra thời gian hoạt động cuối cùng (phát hiện quá thời gian)
                if self._last_activity_time:
                    time_since_activity = time.time() - self._last_activity_time
                    if time_since_activity > self._connection_timeout:
                        logger.warning(
                            f"Kết nối quá thời gian, hoạt động cuối: {time_since_activity:.1f} giây trước"
                        )
                        await self._handle_connection_loss("Kết nối quá thời gian")
                        break

        except asyncio.CancelledError:
            logger.debug("Tác vụ giám sát kết nối MQTT đã bị hủy")
        except Exception as e:
            logger.error(f"Ngoại lệ giám sát kết nối MQTT: {e}")

    async def _handle_connection_loss(self, reason: str):
        """
        Xử lý mất kết nối.
        """
        logger.warning(f"Mất kết nối MQTT: {reason}")

        # Cập nhật trạng thái kết nối
        was_connected = self.connected
        self.connected = False

        # Thông báo thay đổi trạng thái kết nối
        if self._on_connection_state_changed and was_connected:
            try:
                self._on_connection_state_changed(False, reason)
            except Exception as e:
                logger.error(f"Gọi callback thay đổi trạng thái kết nối thất bại: {e}")

        # Dọn dẹp kết nối
        await self._cleanup_connection()

        # Thông báo đóng kênh âm thanh
        if self._on_audio_channel_closed:
            try:
                await self._on_audio_channel_closed()
            except Exception as e:
                logger.error(f"Gọi callback đóng kênh âm thanh thất bại: {e}")

        # Chỉ thử kết nối lại khi không phải đang đóng thủ công và bật tự động kết nối lại
        if (
            not self._is_closing
            and self._auto_reconnect_enabled
            and self._reconnect_attempts < self._max_reconnect_attempts
        ):
            await self._attempt_reconnect(reason)
        else:
            # Thông báo lỗi mạng
            if self._on_network_error:
                if (
                    self._auto_reconnect_enabled
                    and self._reconnect_attempts >= self._max_reconnect_attempts
                ):
                    await self._on_network_error(f"Mất kết nối MQTT và kết nối lại thất bại: {reason}")
                else:
                    await self._on_network_error(f"Mất kết nối MQTT: {reason}")

    async def _attempt_reconnect(self, original_reason: str):
        """
        Thử tự động kết nối lại.
        """
        self._reconnect_attempts += 1

        # Thông báo bắt đầu kết nối lại
        if self._on_reconnecting:
            try:
                self._on_reconnecting(
                    self._reconnect_attempts, self._max_reconnect_attempts
                )
            except Exception as e:
                logger.error(f"Gọi callback kết nối lại thất bại: {e}")

        logger.info(
            f"Thử tự động kết nối lại MQTT ({self._reconnect_attempts}/{self._max_reconnect_attempts})"
        )

        # Chờ một khoảng thời gian trước khi kết nối lại (tăng theo cấp số nhân)
        await asyncio.sleep(min(self._reconnect_attempts * 2, 30))

        try:
            success = await self.connect()
            if success:
                logger.info("Tự động kết nối lại MQTT thành công")
                # Thông báo trạng thái kết nối thay đổi
                if self._on_connection_state_changed:
                    self._on_connection_state_changed(True, "Kết nối lại thành công")
            else:
                logger.warning(
                    f"Tự động kết nối lại MQTT thất bại ({self._reconnect_attempts}/{self._max_reconnect_attempts})"
                )
                # Nếu còn có thể thử lại, không báo lỗi ngay
                if self._reconnect_attempts >= self._max_reconnect_attempts:
                    if self._on_network_error:
                        await self._on_network_error(
                            f"Kết nối lại MQTT thất bại, đã đạt số lần thử tối đa: {original_reason}"
                        )
        except Exception as e:
            logger.error(f"Lỗi trong quá trình kết nối lại MQTT: {e}")
            if self._reconnect_attempts >= self._max_reconnect_attempts:
                if self._on_network_error:
                    await self._on_network_error(f"Ngoại lệ kết nối lại MQTT: {str(e)}")

    def enable_auto_reconnect(self, enabled: bool = True, max_attempts: int = 5):
        """Bật hoặc tắt chức năng tự động kết nối lại.

        Args:
            enabled: Có bật tự động kết nối lại hay không
            max_attempts: Số lần thử kết nối lại tối đa
        """
        self._auto_reconnect_enabled = enabled
        if enabled:
            self._max_reconnect_attempts = max_attempts
            logger.info(f"Đã bật tự động kết nối lại MQTT, số lần thử tối đa: {max_attempts}")
        else:
            self._max_reconnect_attempts = 0
            logger.info("Đã tắt tự động kết nối lại MQTT")

    def get_connection_info(self) -> dict:
        """Lấy thông tin kết nối.

        Returns:
            dict: Từ điển chứa trạng thái kết nối, số lần thử kết nối lại, v.v.
        """
        return {
            "connected": self.connected,
            "mqtt_connected": (
                self.mqtt_client.is_connected() if self.mqtt_client else False
            ),
            "is_closing": self._is_closing,
            "auto_reconnect_enabled": self._auto_reconnect_enabled,
            "reconnect_attempts": self._reconnect_attempts,
            "max_reconnect_attempts": self._max_reconnect_attempts,
            "last_activity_time": self._last_activity_time,
            "keep_alive_interval": self._keep_alive_interval,
            "connection_timeout": self._connection_timeout,
            "mqtt_endpoint": self.endpoint,
            "udp_server": (
                f"{self.udp_server}:{self.udp_port}" if self.udp_server else None
            ),
            "session_id": self.session_id,
        }

    async def _cleanup_connection(self):
        """
        Dọn dẹp tài nguyên liên quan đến kết nối.
        """
        self.connected = False

        # Hủy tác vụ giám sát kết nối
        if self._connection_monitor_task and not self._connection_monitor_task.done():
            self._connection_monitor_task.cancel()
            try:
                await self._connection_monitor_task
            except asyncio.CancelledError:
                pass

        # Dừng luồng nhận UDP
        self._stop_udp_receiver()

        # Dừng client MQTT
        if self.mqtt_client:
            try:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            except Exception as e:
                logger.error(f"Lỗi khi ngắt kết nối MQTT: {e}")

        # Đặt lại dấu thời gian
        self._last_activity_time = None
