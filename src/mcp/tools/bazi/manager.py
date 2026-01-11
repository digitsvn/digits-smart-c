"""Bộ quản lý Bát Tự (Tứ trụ).

Phụ trách các chức năng cốt lõi cho phân tích Bát Tự và tính toán mệnh lý.
"""

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class BaziManager:
    """Bộ quản lý Bát Tự (Tứ trụ)."""

    def __init__(self):
        """Khởi tạo bộ quản lý Bát Tự."""

    def init_tools(self, add_tool, PropertyList, Property, PropertyType):
        """Khởi tạo và đăng ký toàn bộ công cụ Bát Tự."""
        from .marriage_tools import (
            analyze_marriage_compatibility,
            analyze_marriage_timing,
        )
        from .tools import (
            build_bazi_from_lunar_datetime,
            build_bazi_from_solar_datetime,
            get_bazi_detail,
            get_chinese_calendar,
            get_solar_times,
        )

        # Lấy chi tiết Bát Tự (công cụ chính)
        bazi_detail_props = PropertyList(
            [
                Property("solar_datetime", PropertyType.STRING, default_value=""),
                Property("lunar_datetime", PropertyType.STRING, default_value=""),
                Property("gender", PropertyType.INTEGER, default_value=1),
                Property(
                    "eight_char_provider_sect", PropertyType.INTEGER, default_value=2
                ),
            ]
        )
        add_tool(
            (
                "self.bazi.get_bazi_detail",
                "Lấy thông tin phân tích Bát Tự đầy đủ theo thời gian (dương lịch hoặc âm lịch) và giới tính. "
                "Đây là công cụ cốt lõi cho phân tích Bát Tự, cung cấp diễn giải tổng quan.\n"
                "Tình huống sử dụng:\n"
                "1. Phân tích Bát Tự cá nhân\n"
                "2. Tra cứu Bát Tự theo ngày giờ sinh\n"
                "3. Tư vấn/diễn giải mệnh lý\n"
                "4. Phân tích hợp hôn theo Bát Tự\n"
                "5. Dữ liệu nền cho phân tích vận trình\n"
                "\nĐặc điểm:\n"
                "- Hỗ trợ nhập thời gian dương lịch và âm lịch\n"
                "- Cung cấp đầy đủ thông tin Tứ trụ\n"
                "- Bao gồm phân tích thần sát, đại vận, xung/hợp/hình/hại\n"
                "- Hỗ trợ cấu hình cách tính giờ Tý\n"
                "\nTham số:\n"
                "  solar_datetime: Thời gian dương lịch (ISO), ví dụ '2008-03-01T13:00:00+08:00'\n"
                "  lunar_datetime: Thời gian âm lịch, ví dụ '2000-5-5 12:00:00'\n"
                "  gender: Giới tính, 0=nữ, 1=nam\n"
                "  eight_char_provider_sect: Cấu hình giờ Tý, 1=23:00-23:59 tính sang ngày hôm sau, 2=tính trong ngày hiện tại (mặc định)\n"
                "\nLưu ý: bắt buộc truyền đúng 1 trong 2 tham số solar_datetime hoặc lunar_datetime",
                bazi_detail_props,
                get_bazi_detail,
            )
        )

        # Suy ra danh sách thời gian dương lịch theo Bát Tự
        solar_times_props = PropertyList([Property("bazi", PropertyType.STRING)])
        add_tool(
            (
                "self.bazi.get_solar_times",
                "Dựa trên Bát Tự để suy ra danh sách thời gian dương lịch có thể. "
                "Định dạng thời gian trả về: YYYY-MM-DD hh:mm:ss.\n"
                "Tình huống sử dụng:\n"
                "1. Phản suy giờ sinh theo Bát Tự\n"
                "2. Xác thực độ chính xác của Bát Tự\n"
                "3. Tìm các mốc thời gian có cùng Bát Tự\n"
                "4. Kiểm tra/hiệu chỉnh thời gian Bát Tự\n"
                "\nĐặc điểm:\n"
                "- Suy ra thời gian theo tổ hợp thiên can/địa chi\n"
                "- Hỗ trợ truy vấn nhiều thời điểm khả dĩ\n"
                "- Có thể cấu hình phạm vi thời gian\n"
                "\nTham số:\n"
                "  bazi: Bát Tự theo thứ tự năm/tháng/ngày/giờ, cách nhau bởi khoảng trắng\n"
                "        Ví dụ: 'Mậu Dần Kỷ Mùi Kỷ Mão Tân Mùi'",
                solar_times_props,
                get_solar_times,
            )
        )

        # Lấy thông tin hoàng lịch
        chinese_calendar_props = PropertyList(
            [Property("solar_datetime", PropertyType.STRING, default_value="")]
        )
        add_tool(
            (
                "self.bazi.get_chinese_calendar",
                "Lấy thông tin hoàng lịch truyền thống theo thời gian dương lịch chỉ định (mặc định: hôm nay). "
                "Cung cấp ngày âm lịch, can chi, việc nên/không nên, phương vị thần sát, v.v.\n"
                "Tình huống sử dụng:\n"
                "1. Tra cứu hoàng lịch hôm nay\n"
                "2. Tham khảo chọn ngày/giờ\n"
                "3. Tra cứu lễ tết truyền thống\n"
                "4. Tham khảo phương vị phong thủy\n"
                "5. Tìm hiểu văn hóa dân gian\n"
                "\nĐặc điểm:\n"
                "- Thông tin âm lịch đầy đủ\n"
                "- Nhị thập bát tú và tiết khí\n"
                "- Gợi ý phương vị thần sát\n"
                "- Nhắc nhở (theo truyền thống)\n"
                "- Đánh dấu lễ tết truyền thống\n"
                "- Gợi ý việc nên/không nên\n"
                "\nTham số:\n"
                "  solar_datetime: Thời gian dương lịch (ISO), ví dụ '2008-03-01T13:00:00+08:00'\n"
                "                 Nếu không cung cấp sẽ dùng thời gian hiện tại",
                chinese_calendar_props,
                get_chinese_calendar,
            )
        )

        # Lấy Bát Tự từ thời gian âm lịch (đã bỏ/không khuyến nghị)
        lunar_bazi_props = PropertyList(
            [
                Property("lunar_datetime", PropertyType.STRING),
                Property("gender", PropertyType.INTEGER, default_value=1),
                Property(
                    "eight_char_provider_sect", PropertyType.INTEGER, default_value=2
                ),
            ]
        )
        add_tool(
            (
                "self.bazi.build_bazi_from_lunar_datetime",
                "Lấy thông tin Bát Tự theo thời gian âm lịch và giới tính.\n"
                "Lưu ý: công cụ này đã bỏ/không khuyến nghị; hãy dùng get_bazi_detail thay thế.\n"
                "\nTham số:\n"
                "  lunar_datetime: Thời gian âm lịch, ví dụ '2000-5-15 12:00:00'\n"
                "  gender: Giới tính, 0=nữ, 1=nam\n"
                "  eight_char_provider_sect: Cấu hình giờ Tý",
                lunar_bazi_props,
                build_bazi_from_lunar_datetime,
            )
        )

        # Lấy Bát Tự từ thời gian dương lịch (đã bỏ/không khuyến nghị)
        solar_bazi_props = PropertyList(
            [
                Property("solar_datetime", PropertyType.STRING),
                Property("gender", PropertyType.INTEGER, default_value=1),
                Property(
                    "eight_char_provider_sect", PropertyType.INTEGER, default_value=2
                ),
            ]
        )
        add_tool(
            (
                "self.bazi.build_bazi_from_solar_datetime",
                "Lấy thông tin Bát Tự theo thời gian dương lịch và giới tính.\n"
                "Lưu ý: công cụ này đã bỏ/không khuyến nghị; hãy dùng get_bazi_detail thay thế.\n"
                "\nTham số:\n"
                "  solar_datetime: Thời gian dương lịch (ISO), ví dụ '2008-03-01T13:00:00+08:00'\n"
                "  gender: Giới tính, 0=nữ, 1=nam\n"
                "  eight_char_provider_sect: Cấu hình giờ Tý",
                solar_bazi_props,
                build_bazi_from_solar_datetime,
            )
        )

        # Phân tích thời điểm hôn nhân
        marriage_timing_props = PropertyList(
            [
                Property("solar_datetime", PropertyType.STRING, default_value=""),
                Property("lunar_datetime", PropertyType.STRING, default_value=""),
                Property("gender", PropertyType.INTEGER, default_value=1),
                Property(
                    "eight_char_provider_sect", PropertyType.INTEGER, default_value=2
                ),
            ]
        )
        add_tool(
            (
                "self.bazi.analyze_marriage_timing",
                "Phân tích thời điểm hôn nhân, đặc điểm bạn đời và chất lượng hôn nhân."
                "Tập trung vào các phân tích mệnh lý liên quan hôn nhân như dự đoán thời điểm kết hôn, đặc điểm bạn đời, v.v.\\n"
                "Tình huống sử dụng:\\n"
                "1. Dự đoán thời điểm kết hôn phù hợp\\n"
                "2. Phân tích ngoại hình/tính cách bạn đời\\n"
                "3. Đánh giá chất lượng và độ ổn định hôn nhân\\n"
                "4. Nhận diện trở ngại tiềm ẩn trong hôn nhân\\n"
                "5. Tìm năm kết hôn thuận lợi\\n"
                "\\nĐặc điểm:\\n"
                "- Phân tích mức mạnh/yếu của yếu tố liên quan bạn đời\\n"
                "- Dự đoán khoảng tuổi kết hôn\\n"
                "- Diễn giải cung/phần liên quan bạn đời\\n"
                "- Nhận diện trở ngại hôn nhân\\n"
                "- Gợi ý thời điểm thuận lợi\\n"
                "\\nTham số:\\n"
                "  solar_datetime: Thời gian dương lịch (ISO), ví dụ '2008-03-01T13:00:00+08:00'\\n"
                "  lunar_datetime: Thời gian âm lịch, ví dụ '2000-5-5 12:00:00'\\n"
                "  gender: Giới tính, 0=nữ, 1=nam\\n"
                "  eight_char_provider_sect: Cấu hình giờ Tý\\n"
                "\\nLưu ý: bắt buộc truyền đúng 1 trong 2 tham số solar_datetime hoặc lunar_datetime",
                marriage_timing_props,
                analyze_marriage_timing,
            )
        )

        # Phân tích hợp hôn
        marriage_compatibility_props = PropertyList(
            [
                Property("male_solar_datetime", PropertyType.STRING, default_value=""),
                Property("male_lunar_datetime", PropertyType.STRING, default_value=""),
                Property(
                    "female_solar_datetime", PropertyType.STRING, default_value=""
                ),
                Property(
                    "female_lunar_datetime", PropertyType.STRING, default_value=""
                ),
            ]
        )
        add_tool(
            (
                "self.bazi.analyze_marriage_compatibility",
                "Phân tích hợp hôn theo Bát Tự của hai người, đánh giá mức độ phù hợp và cách tương tác."
                "So sánh Bát Tự hai bên để đưa ra mức độ phù hợp và các điểm cần lưu ý.\\n"
                "Tình huống sử dụng:\\n"
                "1. Phân tích hợp hôn trước khi cưới\\n"
                "2. Đánh giá mức độ phù hợp\\n"
                "3. Nhận diện vấn đề khi chung sống\\n"
                "4. Gợi ý cải thiện hôn nhân\\n"
                "5. Chọn thời điểm kết hôn phù hợp\\n"
                "\\nĐặc điểm:\\n"
                "- Phân tích ngũ hành tương hợp\\n"
                "- Đánh giá theo con giáp (tham khảo)\\n"
                "- Nhận định tổ hợp trụ ngày\\n"
                "- Chấm điểm tổng hợp\\n"
                "- Gợi ý cải thiện cụ thể\\n"
                "\\nTham số:\\n"
                "  male_solar_datetime: Thời gian dương lịch của nam\\n"
                "  male_lunar_datetime: Thời gian âm lịch của nam\\n"
                "  female_solar_datetime: Thời gian dương lịch của nữ\\n"
                "  female_lunar_datetime: Thời gian âm lịch của nữ\\n"
                "\\nLưu ý: mỗi bên chỉ cần cung cấp 1 trong 2 (dương lịch hoặc âm lịch)",
                marriage_compatibility_props,
                analyze_marriage_compatibility,
            )
        )


# Instance singleton toàn cục
_bazi_manager = None


def get_bazi_manager() -> BaziManager:
    """Lấy singleton của bộ quản lý Bát Tự."""
    global _bazi_manager
    if _bazi_manager is None:
        _bazi_manager = BaziManager()
    return _bazi_manager
