import asyncio
import json
from typing import Any, Dict, Optional, Tuple

from src.iot.thing import Thing
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class ThingManager:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ThingManager()
        return cls._instance

    def __init__(self):
        self.things = []
        self.last_states = {}  # Thêm từ điển cache trạng thái, lưu trữ trạng thái lần trước

    async def initialize_iot_devices(self, config):
        """Khởi tạo thiết bị IoT.

        Lưu ý: Chức năng đồng hồ đếm ngược đã được chuyển sang công cụ MCP, cung cấp tích hợp AI và phản hồi trạng thái tốt hơn.
        """
        from src.iot.things.lamp import Lamp

        # Thêm thiết bị
        self.add_thing(Lamp())

    def add_thing(self, thing: Thing) -> None:
        self.things.append(thing)

    async def get_descriptors_json(self) -> str:
        """
        Lấy JSON mô tả của tất cả các thiết bị.
        """
        # Vì get_descriptor_json() là phương thức đồng bộ (trả về dữ liệu tĩnh),
        # ở đây giữ cách gọi đồng bộ đơn giản
        descriptors = [thing.get_descriptor_json() for thing in self.things]
        return json.dumps(descriptors)

    async def get_states_json(self, delta=False) -> Tuple[bool, str]:
        """Lấy JSON trạng thái của tất cả các thiết bị.

        Args:
            delta: Có chỉ trả về phần thay đổi hay không, True nghĩa là chỉ trả về phần thay đổi

        Returns:
            Tuple[bool, str]: Trả về boolean có thay đổi trạng thái hay không và chuỗi JSON
        """
        if not delta:
            self.last_states.clear()

        changed = False

        tasks = [thing.get_state_json() for thing in self.things]
        states_results = await asyncio.gather(*tasks)

        states = []
        for i, thing in enumerate(self.things):
            state_json = states_results[i]

            if delta:
                # Kiểm tra trạng thái có thay đổi không
                is_same = (
                    thing.name in self.last_states
                    and self.last_states[thing.name] == state_json
                )
                if is_same:
                    continue
                changed = True
                self.last_states[thing.name] = state_json

            # Kiểm tra state_json đã là đối tượng dictionary chưa
            if isinstance(state_json, dict):
                states.append(state_json)
            else:
                states.append(json.loads(state_json))  # Chuyển đổi chuỗi JSON thành dictionary

        return changed, json.dumps(states)

    async def get_states_json_str(self) -> str:
        """
        Để tương thích với mã cũ, giữ lại tên phương thức và kiểu giá trị trả về ban đầu.
        """
        _, json_str = await self.get_states_json(delta=False)
        return json_str

    async def invoke(self, command: Dict) -> Optional[Any]:
        """Gọi phương thức thiết bị.

        Args:
            command: Từ điển lệnh chứa thông tin như name và method

        Returns:
            Optional[Any]: Nếu tìm thấy thiết bị và gọi thành công, trả về kết quả gọi; ngược lại ném ra ngoại lệ
        """
        thing_name = command.get("name")
        for thing in self.things:
            if thing.name == thing_name:
                return await thing.invoke(command)

        # Ghi nhật ký lỗi
        logger.error(f"Thiết bị không tồn tại: {thing_name}")
        raise ValueError(f"Thiết bị không tồn tại: {thing_name}")
