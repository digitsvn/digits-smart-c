import paho.mqtt.client as mqtt


class MqttClient:
    def __init__(
        self,
        server,
        port,
        username,
        password,
        subscribe_topic,
        publish_topic=None,
        client_id="PythonClient",
        on_connect=None,
        on_message=None,
        on_publish=None,
        on_disconnect=None,
    ):
        """Khởi tạo instance MqttClient.

        :param server: Địa chỉ MQTT server
        :param port: Cổng MQTT server
        :param username: Tên đăng nhập
        :param password: Mật khẩu
        :param subscribe_topic: Topic để subscribe
        :param publish_topic: Topic để publish
        :param client_id: Client ID, mặc định "PythonClient"
        :param on_connect: Callback tùy chỉnh khi kết nối
        :param on_message: Callback tùy chỉnh khi nhận message
        :param on_publish: Callback tùy chỉnh khi publish
        :param on_disconnect: Callback tùy chỉnh khi ngắt kết nối
        """
        self.server = server
        self.port = port
        self.username = username
        self.password = password
        self.subscribe_topic = subscribe_topic
        self.publish_topic = publish_topic
        self.client_id = client_id

        # Tạo MQTT client (API mới)
        self.client = mqtt.Client(client_id=self.client_id, protocol=mqtt.MQTTv5)

        # Thiết lập username/password
        self.client.username_pw_set(self.username, self.password)

        # Thiết lập callback: ưu tiên callback tùy chỉnh nếu được truyền vào
        if on_connect:
            self.client.on_connect = on_connect
        else:
            self.client.on_connect = self._on_connect

        self.client.on_message = on_message if on_message else self._on_message
        self.client.on_publish = on_publish if on_publish else self._on_publish

        if on_disconnect:
            self.client.on_disconnect = on_disconnect
        else:
            self.client.on_disconnect = self._on_disconnect

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """
        Callback mặc định khi kết nối.
        """
        if rc == 0:
            print("✅ Kết nối MQTT server thành công")
            # Sau khi kết nối thành công, tự động subscribe topic
            client.subscribe(self.subscribe_topic)
            print(f"📥 Đã subscribe topic: {self.subscribe_topic}")
        else:
            print(f"❌ Kết nối thất bại, mã lỗi: {rc}")

    def _on_message(self, client, userdata, msg):
        """
        Callback mặc định khi nhận message.
        """
        topic = msg.topic
        content = msg.payload.decode()
        print(f"📩 Nhận message - topic: {topic}, nội dung: {content}")

    def _on_publish(self, client, userdata, mid, properties=None):
        """
        Callback mặc định khi publish.
        """
        print(f"📤 Đã publish message, message ID: {mid}")

    def _on_disconnect(self, client, userdata, rc, properties=None):
        """
        Callback mặc định khi ngắt kết nối.
        """
        print("🔌 Đã ngắt kết nối khỏi MQTT server")

    def connect(self):
        """
        Kết nối tới MQTT server.
        """
        try:
            self.client.connect(self.server, self.port, 60)
            print(f"🔗 Đang kết nối tới {self.server}:{self.port}")
        except Exception as e:
            print(f"❌ Kết nối thất bại, lỗi: {e}")

    def start(self):
        """
        Khởi động client và bắt đầu network loop.
        """
        self.client.loop_start()

    def publish(self, message):
        """
        Publish message tới topic chỉ định.
        """
        result = self.client.publish(self.publish_topic, message)
        status = result.rc
        if status == 0:
            print(f"✅ Publish thành công tới topic `{self.publish_topic}`")
        else:
            print(f"❌ Publish thất bại, mã lỗi: {status}")

    def stop(self):
        """
        Dừng network loop và ngắt kết nối.
        """
        self.client.loop_stop()
        self.client.disconnect()
        print("🛑 Client đã dừng và ngắt kết nối")


if __name__ == "__main__":
    pass
    # Callback tùy chỉnh
    # def custom_on_connect(client, userdata, flags, rc, properties=None):
    #     if rc == 0:
    #         print("🎉 Callback tùy chỉnh: kết nối MQTT server thành công")
    #         topic_data = userdata['subscribe_topic']
    #         client.subscribe(topic_data)
    #         print(f"📥 Callback tùy chỉnh: đã subscribe topic: {topic_data}")
    #     else:
    #         print(f"❌ Callback tùy chỉnh: kết nối thất bại, mã lỗi: {rc}")
    #
    # def custom_on_message(client, userdata, msg):
    #     topic = msg.topic
    #     content = msg.payload.decode()
    #     print(f"📩 Callback tùy chỉnh: nhận message - topic: {topic}, nội dung: {content}")
    #
    # def custom_on_publish(client, userdata, mid, properties=None):
    #     print(f"📤 Callback tùy chỉnh: đã publish message, message ID: {mid}")
    #
    # def custom_on_disconnect(client, userdata, rc, properties=None):
    #     print("🔌 Callback tùy chỉnh: đã ngắt kết nối khỏi MQTT server")
    #
    # # Tạo MqttClient và truyền callback tùy chỉnh
    # mqtt_client = MqttClient(
    #     server="8.130.181.98",
    #     port=1883,
    #     username="admin",
    #     password="dtwin@123",
    #     subscribe_topic="sensors/temperature/request",
    #     publish_topic="sensors/temperature/device_001/state",
    #     client_id="CustomClient",
    #     on_connect=custom_on_connect,
    #     on_message=custom_on_message,
    #     on_publish=custom_on_publish,
    #     on_disconnect=custom_on_disconnect
    # )
    #
    # # Truyền topic subscribe qua userdata
    # mqtt_client.client.user_data_set(
    #     {'subscribe_topic': mqtt_client.subscribe_topic}
    # )
    #
    # # Kết nối tới MQTT server
    # mqtt_client.connect()
    #
    # # Khởi động client
    # mqtt_client.start()
    #
    # try:
    #     while True:
    #         # Publish message
    #         message = input("Nhập message cần publish: ")
    #         mqtt_client.publish(message)
    # except KeyboardInterrupt:
    #     print("\n⛔️ Chương trình đã dừng")
    # finally:
    #     # Dừng và ngắt kết nối
    #     mqtt_client.stop()
