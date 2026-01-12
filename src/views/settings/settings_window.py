import os
from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog,
    QMessageBox,
    QPushButton,
    QTabWidget,
)

from src.utils.config_manager import ConfigManager
from src.utils.logging_config import get_logger
from src.views.settings.components.audio import AudioWidget
from src.views.settings.components.video_background import VideoBackgroundWidget
from src.views.settings.components.shortcuts_settings import ShortcutsSettingsWidget
from src.views.settings.components.system_options import SystemOptionsWidget
from src.views.settings.components.wake_word import WakeWordWidget
from src.views.settings.components.wifi import WiFiSetupWidget


class SettingsWindow(QDialog):
    """
    Cửa sổ cấu hình tham số.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self.config_manager = ConfigManager.get_instance()

        # Tham chiếu component
        self.wifi_tab = None
        self.system_options_tab = None
        self.wake_word_tab = None
        self.video_bg_tab = None
        self.audio_tab = None
        self.shortcuts_tab = None

        # Điều khiển UI
        self.ui_controls = {}

        # Khởi tạo UI
        self._setup_ui()
        self._connect_events()

    def _setup_ui(self):
        """
        Thiết lập giao diện UI.
        """
        try:
            from PyQt5 import uic
            from src.utils.resource_finder import resource_finder

            # Tìm file .ui, ưu tiên tìm bằng resource_finder
            ui_path = None
            found_ui = resource_finder.find_file("settings_window.ui")
            if found_ui:
                ui_path = found_ui
            else:
                ui_path = Path(__file__).parent / "settings_window.ui"

            uic.loadUi(str(ui_path), self)


            # Lấy tham chiếu điều khiển UI
            self._get_ui_controls()

            # Thêm các tab component
            self._add_component_tabs()

        except Exception as e:
            self.logger.error(f"Thiết lập UI thất bại: {e}", exc_info=True)
            raise

    def _add_component_tabs(self):
        """
        Thêm các tab component.
        """
        try:
            # Lấy TabWidget
            tab_widget = self.findChild(QTabWidget, "tabWidget")
            if not tab_widget:
                self.logger.error("Không tìm thấy điều khiển TabWidget")
                return

            # Xóa các tab hiện có (nếu có)
            tab_widget.clear()

            from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget

            def add_tab_safely(widget_class, title, attr_name):
                try:
                    widget = widget_class()
                    setattr(self, attr_name, widget)
                    tab_widget.addTab(widget, title)
                    if hasattr(widget, "settings_changed"):
                        widget.settings_changed.connect(self._on_settings_changed)
                except Exception as e:
                    self.logger.error(f"Failed to load tab {title}: {e}", exc_info=True)
                    # Create a dummy widget with the error message
                    err_widget = QWidget()
                    layout = QVBoxLayout()
                    layout.addWidget(QLabel(f"Lỗi tải tab {title}:"))
                    layout.addWidget(QLabel(str(e)))
                    err_widget.setLayout(layout)
                    tab_widget.addTab(err_widget, f"{title} (Lỗi)")

            # Tạo và thêm tab WiFi (đầu tiên cho first-run setup)
            add_tab_safely(WiFiSetupWidget, "📶 WiFi", "wifi_tab")

            # Tạo và thêm component thiết bị âm thanh (quan trọng cho MIC/Speaker)
            add_tab_safely(AudioWidget, "🔊 Âm thanh", "audio_tab")

            # Tạo và thêm component tùy chọn hệ thống
            add_tab_safely(SystemOptionsWidget, "⚙️ Tùy chọn", "system_options_tab")

            # Tạo và thêm component từ đánh thức
            add_tab_safely(WakeWordWidget, "🎤 Wakeword", "wake_word_tab")

            # Tạo và thêm component nền video
            add_tab_safely(VideoBackgroundWidget, "🎬 Nền", "video_bg_tab")

            # Tạo và thêm component cài đặt phím tắt
            add_tab_safely(ShortcutsSettingsWidget, "⌨️ Phím tắt", "shortcuts_tab")

            self.logger.debug("Thêm tất cả các tab component thành công")

        except Exception as e:
            self.logger.error(f"Thêm tab component thất bại: {e}", exc_info=True)
            QMessageBox.critical(self, "Lỗi giao diện", f"Không thể khởi tạo tabs: {e}")

    def _on_settings_changed(self):
        """
        Callback thay đổi cài đặt.
        """
        # Có thể thêm một số gợi ý hoặc logic khác ở đây

    def _get_ui_controls(self):
        """
        Lấy tham chiếu điều khiển UI.
        """
        # Chỉ cần lấy các điều khiển nút chính
        self.ui_controls.update(
            {
                "save_btn": self.findChild(QPushButton, "save_btn"),
                "cancel_btn": self.findChild(QPushButton, "cancel_btn"),
                "reset_btn": self.findChild(QPushButton, "reset_btn"),
            }
        )

    def _connect_events(self):
        """
        Kết nối xử lý sự kiện.
        """
        if self.ui_controls["save_btn"]:
            self.ui_controls["save_btn"].clicked.connect(self._on_save_clicked)

        if self.ui_controls["cancel_btn"]:
            self.ui_controls["cancel_btn"].clicked.connect(self.reject)

        if self.ui_controls["reset_btn"]:
            self.ui_controls["reset_btn"].clicked.connect(self._on_reset_clicked)

    # Tải cấu hình hiện được xử lý bởi từng component, không cần xử lý trong cửa sổ chính

    # Đã xóa các phương thức thao tác điều khiển không còn cần thiết, hiện được xử lý bởi từng component

    def _on_save_clicked(self):
        """
        Sự kiện click nút lưu.
        """
        try:
            # Thu thập tất cả dữ liệu cấu hình
            success = self._save_all_config()

            if success:
                # Mark first-run as completed (idempotent)
                try:
                    marker_path = Path(self.config_manager.config_dir) / ".first_run_done"
                    marker_path.write_text("ok\n", encoding="utf-8")
                except Exception as e:
                    self.logger.warning(f"Failed to write first-run marker: {e}")

                # Chỉ cần thông báo, video tự reload không cần restart
                QMessageBox.information(
                    self,
                    "Lưu cấu hình thành công",
                    "Cấu hình đã được lưu!\n\n• Video nền: Áp dụng ngay\n• Từ đánh thức: Cần khởi động lại",
                )
                self.accept()
            else:
                QMessageBox.warning(self, "Lỗi", "Lưu cấu hình thất bại, vui lòng kiểm tra giá trị đã nhập.")

        except Exception as e:
            self.logger.error(f"Lưu cấu hình thất bại: {e}", exc_info=True)
            QMessageBox.critical(self, "Lỗi", f"Xảy ra lỗi khi lưu cấu hình: {str(e)}")

    def _save_all_config(self) -> bool:
        """
        Lưu tất cả cấu hình.
        """
        try:
            # Thu thập dữ liệu cấu hình từ các component
            all_config_data = {}

            # Cấu hình tùy chọn hệ thống
            if self.system_options_tab:
                system_config = self.system_options_tab.get_config_data()
                all_config_data.update(system_config)

            # Cấu hình từ đánh thức
            if self.wake_word_tab:
                wake_word_config = self.wake_word_tab.get_config_data()
                all_config_data.update(wake_word_config)

            # Cấu hình nền video
            if self.video_bg_tab:
                video_config = self.video_bg_tab.get_config_data()
                all_config_data.update(video_config)

            # Cấu hình thiết bị âm thanh
            if self.audio_tab:
                audio_config = self.audio_tab.get_config_data()
                all_config_data.update(audio_config)

            # Cấu hình phím tắt
            if self.shortcuts_tab:
                # Component phím tắt có phương thức lưu riêng
                self.shortcuts_tab.apply_settings()

            # Cập nhật cấu hình hàng loạt
            for config_path, value in all_config_data.items():
                self.config_manager.update_config(config_path, value)

            self.logger.info("Lưu cấu hình thành công")
            return True

        except Exception as e:
            self.logger.error(f"Lỗi khi lưu cấu hình: {e}", exc_info=True)
            return False

    def _on_reset_clicked(self):
        """
        Sự kiện click nút reset.
        """
        reply = QMessageBox.question(
            self,
            "Xác nhận reset",
            "Bạn có chắc chắn muốn reset tất cả cấu hình về giá trị mặc định không?\nĐiều này sẽ xóa tất cả cài đặt hiện tại.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self._reset_to_defaults()

    def _reset_to_defaults(self):
        """
        Reset về giá trị mặc định.
        """
        try:
            # Để các component reset về giá trị mặc định
            if self.system_options_tab:
                self.system_options_tab.reset_to_defaults()

            if self.wake_word_tab:
                self.wake_word_tab.reset_to_defaults()

            if self.video_bg_tab:
                self.video_bg_tab.reset_to_defaults()

            if self.audio_tab:
                self.audio_tab.reset_to_defaults()

            if self.shortcuts_tab:
                self.shortcuts_tab.reset_to_defaults()

            self.logger.info("Cấu hình tất cả component đã được reset về giá trị mặc định")

        except Exception as e:
            self.logger.error(f"Reset cấu hình thất bại: {e}", exc_info=True)
            QMessageBox.critical(self, "Lỗi", f"Xảy ra lỗi khi reset cấu hình: {str(e)}")

    def _restart_application(self):
        """
        Khởi động lại ứng dụng.
        """
        try:
            self.logger.info("Người dùng chọn khởi động lại ứng dụng")

            # Đóng cửa sổ cài đặt
            self.accept()

            # Khởi động lại chương trình trực tiếp
            self._direct_restart()

        except Exception as e:
            self.logger.error(f"Khởi động lại ứng dụng thất bại: {e}", exc_info=True)
            QMessageBox.warning(
                self, "Khởi động lại thất bại", "Khởi động lại tự động thất bại, vui lòng khởi động lại phần mềm thủ công để cấu hình có hiệu lực."
            )

    def _direct_restart(self):
        """
        Khởi động lại chương trình trực tiếp.
        """
        try:
            import sys

            from PyQt5.QtWidgets import QApplication

            # Lấy đường dẫn và tham số của chương trình đang thực thi
            python = sys.executable
            script = sys.argv[0]
            args = sys.argv[1:]

            self.logger.info(f"Lệnh khởi động lại: {python} {script} {' '.join(args)}")

            # Đóng ứng dụng hiện tại
            QApplication.quit()

            # Khởi động instance mới
            if getattr(sys, "frozen", False):
                # Môi trường đóng gói
                os.execv(sys.executable, [sys.executable] + args)
            else:
                # Môi trường phát triển
                os.execv(python, [python, script] + args)

        except Exception as e:
            self.logger.error(f"Khởi động lại trực tiếp thất bại: {e}", exc_info=True)

    def closeEvent(self, event):
        """
        Sự kiện đóng cửa sổ.
        """
        self.logger.debug("Cửa sổ cài đặt đã đóng")
        super().closeEvent(event)
