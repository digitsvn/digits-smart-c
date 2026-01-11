import argparse
import asyncio
import signal
import sys
from pathlib import Path

from src.application import Application
from src.utils.logging_config import get_logger, setup_logging

logger = get_logger(__name__)


def parse_args():
    """
    Phân tích tham số dòng lệnh.
    """
    parser = argparse.ArgumentParser(description="Trợ lý AI Smart C")
    parser.add_argument(
        "--mode",
        choices=["gui", "cli"],
        default="gui",
        help="Chế độ chạy: gui (giao diện đồ họa) hoặc cli (dòng lệnh)",
    )
    parser.add_argument(
        "--protocol",
        choices=["mqtt", "websocket"],
        default="websocket",
        help="Giao thức truyền thông: mqtt hoặc websocket",
    )
    parser.add_argument(
        "--skip-activation",
        action="store_true",
        help="Bỏ qua quy trình kích hoạt và khởi chạy ứng dụng trực tiếp (chỉ dùng để gỡ lỗi)",
    )
    return parser.parse_args()


async def handle_activation(mode: str) -> bool:
    """Xử lý quy trình kích hoạt thiết bị, phụ thuộc vào vòng lặp sự kiện hiện có.

    Args:
        mode: Chế độ chạy, "gui" hoặc "cli"

    Returns:
        bool: Kích hoạt thành công hay không
    """
    try:
        from src.core.system_initializer import SystemInitializer

        logger.info("Bắt đầu kiểm tra quy trình kích hoạt thiết bị...")

        system_initializer = SystemInitializer()
        # Sử dụng phương pháp xử lý kích hoạt trong SystemInitializer, tự động thích ứng với GUI/CLI
        result = await system_initializer.handle_activation_process(mode=mode)
        success = bool(result.get("is_activated", False))
        logger.info(f"Quy trình kích hoạt hoàn tất, kết quả: {success}")
        return success
    except Exception as e:
        logger.error(f"Lỗi quy trình kích hoạt: {e}", exc_info=True)
        return False


async def start_app(mode: str, protocol: str, skip_activation: bool) -> int:
    """
    Điểm khởi đầu chung để chạy ứng dụng (thực hiện trong vòng lặp sự kiện hiện có).
    """
    logger.info("Khởi chạy Trợ lý AI Smart C")

    # =====================================
    # BƯỚC 0: Kiểm tra và thiết lập WiFi (chỉ trên Raspberry Pi)
    # =====================================
    try:
        from src.core.startup_flow import is_raspberry_pi, check_wifi_connection
        
        if is_raspberry_pi():
            logger.info("Phát hiện Raspberry Pi, kiểm tra kết nối WiFi...")
            
            if not check_wifi_connection():
                logger.info("Chưa có kết nối WiFi, chạy WiFi Setup...")
                
                from src.core.startup_flow import run_startup_flow
                wifi_ok, wifi_msg = await run_startup_flow(mode)
                
                if not wifi_ok:
                    logger.error(f"WiFi Setup thất bại: {wifi_msg}")
                    # Hiển thị thông báo cho user nếu GUI
                    if mode == "gui":
                        try:
                            from PyQt5.QtWidgets import QMessageBox
                            QMessageBox.critical(
                                None, 
                                "Lỗi WiFi",
                                f"Không thể thiết lập kết nối WiFi.\n{wifi_msg}\n\nỨng dụng sẽ thoát."
                            )
                        except Exception:
                            pass
                    return 1
                
                logger.info(f"WiFi Setup hoàn tất: {wifi_msg}")
            else:
                logger.info("Đã có kết nối WiFi ✓")
    except ImportError:
        logger.debug("Startup flow module không khả dụng, bỏ qua WiFi check")
    except Exception as e:
        logger.warning(f"Lỗi kiểm tra WiFi (tiếp tục): {e}")

    # =====================================
    # BƯỚC 1: First-run Settings (WiFi + Audio + Wakeword)
    # =====================================
    if mode == "gui":
        try:
            from src.utils.resource_finder import resource_finder

            config_dir = resource_finder.find_config_dir()
            if not config_dir:
                config_dir = resource_finder.get_project_root() / "config"

            first_run_marker = Path(config_dir) / ".first_run_done"
            if not first_run_marker.exists():
                from src.views.settings.settings_window import SettingsWindow
                from PyQt5.QtWidgets import QMessageBox

                logger.info("Lần chạy đầu tiên: mở Settings trước khi kích hoạt")
                
                # Hiện thông báo chào mừng
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Information)
                msg.setWindowTitle("🎉 Chào mừng đến với Smart C!")
                msg.setText(
                    "Đây là lần đầu tiên bạn sử dụng ứng dụng.\n\n"
                    "Vui lòng cấu hình các thiết lập cơ bản:\n"
                    "• WiFi - Kết nối mạng Internet\n"
                    "• Âm thanh - Chọn MIC và Loa\n"
                    "• Wakeword - Từ đánh thức (alexa, hey lily...)\n\n"
                    "Nhấn OK để tiếp tục."
                )
                msg.exec_()
                
                dlg = SettingsWindow()
                result = dlg.exec_()
                if result == 0:
                    logger.warning("Người dùng đã đóng Settings. Thoát ứng dụng.")
                    return 1
        except Exception as e:
            logger.error(f"Không thể mở Settings lần đầu: {e}", exc_info=True)
            return 1

    # =====================================
    # BƯỚC 2: Xử lý quy trình kích hoạt với Server
    # =====================================
    if skip_activation:
        logger.warning("Bỏ qua quy trình kích hoạt (chế độ gỡ lỗi)")
    else:
        activation_success = await handle_activation(mode)
        if not activation_success:
            logger.error("Kích hoạt thiết bị thất bại, thoát chương trình")
            return 1


    # Tạo và khởi chạy ứng dụng
    app = Application.get_instance()
    return await app.run(mode=mode, protocol=protocol)


if __name__ == "__main__":
    exit_code = 1
    try:
        args = parse_args()
        setup_logging()

        # Phát hiện môi trường Wayland và thiết lập cấu hình plugin nền tảng Qt
        import os

        is_wayland = (
            os.environ.get("WAYLAND_DISPLAY")
            or os.environ.get("XDG_SESSION_TYPE") == "wayland"
        )

        if args.mode == "gui" and is_wayland:
            # Trong môi trường Wayland, đảm bảo Qt sử dụng plugin nền tảng chính xác
            if "QT_QPA_PLATFORM" not in os.environ:
                # Ưu tiên sử dụng plugin wayland, nếu thất bại thì quay về xcb (lớp tương thích X11)
                os.environ["QT_QPA_PLATFORM"] = "wayland;xcb"
                logger.info("Môi trường Wayland: Thiết lập QT_QPA_PLATFORM=wayland;xcb")

            # Vô hiệu hóa một số tính năng Qt không ổn định trong Wayland
            os.environ.setdefault("QT_WAYLAND_DISABLE_WINDOWDECORATION", "1")
            logger.info("Phát hiện môi trường Wayland hoàn tất, đã áp dụng cấu hình tương thích")

        # Thiết lập xử lý tín hiệu thống nhất: bỏ qua SIGTRAP trên macOS để tránh "trace trap" làm thoát tiến trình
        try:
            if hasattr(signal, "SIGINT"):
                # Để qasync/Qt xử lý Ctrl+C; giữ mặc định hoặc xử lý sau bởi lớp GUI
                pass
            if hasattr(signal, "SIGTERM"):
                # Cho phép tiến trình nhận tín hiệu kết thúc và đi theo đường dẫn đóng bình thường
                pass
            if hasattr(signal, "SIGTRAP"):
                signal.signal(signal.SIGTRAP, signal.SIG_IGN)
        except Exception:
            # Một số nền tảng/môi trường không hỗ trợ thiết lập các tín hiệu này, bỏ qua là được
            pass

        if args.mode == "gui":
            # Trong chế độ GUI, tạo QApplication và vòng lặp sự kiện qasync từ main
            try:
                import qasync
                from PyQt5.QtWidgets import QApplication
            except ImportError as e:
                logger.error(f"Chế độ GUI yêu cầu thư viện qasync và PyQt5: {e}")
                sys.exit(1)

            qt_app = QApplication.instance() or QApplication(sys.argv)

            loop = qasync.QEventLoop(qt_app)
            asyncio.set_event_loop(loop)
            logger.info("Đã tạo vòng lặp sự kiện qasync trong main")

            # Đảm bảo việc đóng cửa sổ cuối cùng không tự động thoát ứng dụng, tránh vòng lặp sự kiện dừng trước
            try:
                qt_app.setQuitOnLastWindowClosed(False)
            except Exception:
                pass

            with loop:
                exit_code = loop.run_until_complete(
                    start_app(args.mode, args.protocol, args.skip_activation)
                )
        else:
            # Chế độ CLI sử dụng vòng lặp sự kiện asyncio tiêu chuẩn
            exit_code = asyncio.run(
                start_app(args.mode, args.protocol, args.skip_activation)
            )

    except KeyboardInterrupt:
        logger.info("Chương trình bị người dùng gián đoạn")
        exit_code = 0
    except Exception as e:
        logger.error(f"Chương trình thoát bất thường: {e}", exc_info=True)
        exit_code = 1
    finally:
        sys.exit(exit_code)
