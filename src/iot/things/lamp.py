from src.iot.thing import Thing


class Lamp(Thing):
    def __init__(self):
        super().__init__("Lamp", "Một đèn thử nghiệm")
        self.power = False

        # Định nghĩa thuộc tính - Sử dụng getter bất đồng bộ
        self.add_property("power", "Đèn có bật không", self.get_power)

        # Định nghĩa phương thức - Sử dụng bộ xử lý phương thức bất đồng bộ
        self.add_method("TurnOn", "Bật đèn", [], self._turn_on)

        self.add_method("TurnOff", "Tắt đèn", [], self._turn_off)

    async def get_power(self):
        return self.power

    async def _turn_on(self, params):
        self.power = True
        return {"status": "success", "message": "Đèn đã bật"}

    async def _turn_off(self, params):
        self.power = False
        return {"status": "success", "message": "Đèn đã tắt"}
