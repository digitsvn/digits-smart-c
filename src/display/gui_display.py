# -*- coding: utf-8 -*-
"""
Mô-đun hiển thị GUI - sử dụng QML.
"""

import asyncio
import os
import signal
import threading
import time
from abc import ABCMeta
from pathlib import Path
from typing import Callable, Optional

from PyQt5.QtCore import QObject, Qt, QTimer, QUrl
from PyQt5.QtGui import QCursor, QFont
from PyQt5.QtQuickWidgets import QQuickWidget
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QWidget

from src.display.base_display import BaseDisplay
from src.display.gui_display_model import GuiDisplayModel
from src.utils.resource_finder import find_assets_dir, get_user_cache_dir


# Tạo metaclass tương thích
class CombinedMeta(type(QObject), ABCMeta):
    pass


class _VideoCaptureWorker(threading.Thread):
    """Đọc frame từ camera hoặc file MP4 trên thread nền.

    - Lưu JPEG bytes mới nhất + seq, để UI thread poll qua QTimer.
    - Với MP4: tự động seek về đầu khi đọc hết (loop).
    """

    def __init__(
        self,
        *,
        source: str,
        camera_index: int,
        frame_width: int,
        frame_height: int,
        file_path: str,
        loop: bool,
        fps: int,
    ):
        super().__init__(daemon=True)
        self.source = (source or "none").lower()
        self.camera_index = int(camera_index)
        self.frame_width = int(frame_width)
        self.frame_height = int(frame_height)
        self.file_path = file_path or ""
        self.loop = bool(loop)
        self.fps = max(1, int(fps) if fps else 10)

        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._latest_jpeg: bytes | None = None
        self._seq = 0
        self._cap = None

    def stop(self):
        self._stop_event.set()

    def pop_latest(self) -> tuple[int, bytes | None]:
        with self._lock:
            return self._seq, self._latest_jpeg

    def _open_capture(self):
        try:
            import cv2

            if self.source == "camera":
                cap = cv2.VideoCapture(self.camera_index)
                if cap is not None and cap.isOpened():
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
                return cap
            if self.source == "file":
                if not self.file_path:
                    return None
                return cv2.VideoCapture(self.file_path)
        except Exception:
            return None
        return None

    def _close_capture(self):
        try:
            if self._cap is not None:
                self._cap.release()
        except Exception:
            pass
        self._cap = None

    def run(self):
        target_dt = 1.0 / float(self.fps)
        try:
            import cv2

            while not self._stop_event.is_set():
                start_t = time.time()

                if self._cap is None or not getattr(self._cap, "isOpened", lambda: False)():
                    self._close_capture()
                    self._cap = self._open_capture()
                    if self._cap is None or not self._cap.isOpened():
                        time.sleep(0.5)
                        continue

                ret, frame = self._cap.read()
                if not ret or frame is None:
                    if self.source == "file" and self.loop:
                        # Seek về đầu video để loop
                        try:
                            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            # Đọc frame đầu tiên ngay lập tức để tránh màn hình đen
                            ret, frame = self._cap.read()
                            if ret and frame is not None:
                                # Có frame, encode ngay không cần sleep
                                pass
                            else:
                                # Không đọc được, reopen capture
                                self._close_capture()
                                time.sleep(0.05)
                                continue
                        except Exception:
                            self._close_capture()
                            time.sleep(0.05)
                            continue
                    else:
                        time.sleep(0.1)
                        continue

                try:
                    # Giảm JPEG quality để tối ưu cho Pi (60 thay vì 80)
                    ok, jpeg = cv2.imencode(
                        ".jpg",
                        frame,
                        [int(cv2.IMWRITE_JPEG_QUALITY), 60],
                    )
                    if ok:
                        data = jpeg.tobytes()
                        with self._lock:
                            self._seq += 1
                            self._latest_jpeg = data
                except Exception:
                    pass

                elapsed = time.time() - start_t
                sleep_t = target_dt - elapsed
                if sleep_t > 0:
                    time.sleep(min(sleep_t, 0.5))

        finally:
            self._close_capture()


class GuiDisplay(BaseDisplay, QObject, metaclass=CombinedMeta):
    """Lớp hiển thị GUI - giao diện hiện đại dựa trên QML"""

    # Định nghĩa hằng số
    EMOTION_EXTENSIONS = (".gif", ".png", ".jpg", ".jpeg", ".webp")
    DEFAULT_WINDOW_SIZE = (1024, 768)
    DEFAULT_FONT_SIZE = 12
    QUIT_TIMEOUT_MS = 3000

    def __init__(self):
        super().__init__()
        QObject.__init__(self)

        # Thành phần Qt
        self.app = None
        self.root = None
        self.qml_widget = None
        self.system_tray = None

        # Mô hình dữ liệu
        self.display_model = GuiDisplayModel()

        # Quản lý biểu cảm
        self._emotion_cache = {}
        self._last_emotion_name = None

        # Quản lý trạng thái
        self.auto_mode = False
        self._running = True
        self.current_status = ""
        self.is_connected = True

        # Trạng thái kéo cửa sổ
        self._dragging = False
        self._drag_position = None

        # Bản đồ hàm callback
        self._callbacks = {
            "button_press": None,
            "button_release": None,
            "mode": None,
            "auto": None,
            "abort": None,
            "send_text": None,
        }

        # Video (camera / mp4): chạy nền + đẩy frame qua display_model.videoFrameUrl
        self._video_worker: _VideoCaptureWorker | None = None
        self._video_timer: Optional[QTimer] = None
        self._video_last_seq: int = -1
        self._video_frame_file: Optional[Path] = None

    # =========================================================================
    # API công cộng - Callback và cập nhật
    # =========================================================================

    async def set_callbacks(
        self,
        press_callback: Optional[Callable] = None,
        release_callback: Optional[Callable] = None,
        mode_callback: Optional[Callable] = None,
        auto_callback: Optional[Callable] = None,
        abort_callback: Optional[Callable] = None,
        send_text_callback: Optional[Callable] = None,
    ):
        """
        Thiết lập các hàm callback.
        """
        self._callbacks.update(
            {
                "button_press": press_callback,
                "button_release": release_callback,
                "mode": mode_callback,
                "auto": auto_callback,
                "abort": abort_callback,
                "send_text": send_text_callback,
            }
        )

    async def update_status(self, status: str, connected: bool):
        """
        Cập nhật văn bản trạng thái và xử lý logic liên quan.
        """
        self.display_model.update_status(status, connected)

        # Theo dõi sự thay đổi trạng thái
        status_changed = status != self.current_status
        connected_changed = bool(connected) != self.is_connected

        if status_changed:
            self.current_status = status
        if connected_changed:
            self.is_connected = bool(connected)

        # Cập nhật khay hệ thống
        if (status_changed or connected_changed) and self.system_tray:
            self.system_tray.update_status(status, self.is_connected)

    async def update_text(self, text: str):
        """
        Cập nhật văn bản TTS.
        """
        self.display_model.update_text(text)

    async def update_user_text(self, text: str):
        """
        Cập nhật văn bản người dùng (STT).
        """
        self.display_model.update_user_text(text)

    async def update_emotion(self, emotion_name: str):
        """
        Cập nhật biểu cảm hiển thị.
        """
        if emotion_name == self._last_emotion_name:
            return

        self._last_emotion_name = emotion_name
        asset_path = self._get_emotion_asset_path(emotion_name)

        # Chuyển đường dẫn file cục bộ thành URL có thể sử dụng trong QML (file:///...),
        # Không phải file (như ký tự emoji) giữ nguyên.
        def to_qml_url(p: str) -> str:
            if not p:
                return ""
            if p.startswith(("qrc:/", "file:")):
                return p
            # Chỉ chuyển thành URL file khi đường dẫn tồn tại, tránh nhầm emoji thành đường dẫn
            try:
                if os.path.exists(p):
                    return QUrl.fromLocalFile(p).toString()
            except Exception:
                pass
            return p

        url_or_text = to_qml_url(asset_path)
        self.display_model.update_emotion(url_or_text)

    async def update_button_status(self, text: str):
        """
        Cập nhật trạng thái nút.
        """
        if self.auto_mode:
            self.display_model.update_button_text(text)

    async def toggle_mode(self):
        """
        Chuyển đổi chế độ đối thoại.
        """
        if self._callbacks["mode"]:
            self._on_mode_button_click()
            self.logger.debug("Đã chuyển chế độ đối thoại thông qua phím tắt")

    async def toggle_window_visibility(self):
        """
        Chuyển đổi khả năng hiển thị của cửa sổ.
        """
        if not self.root:
            return

        if self.root.isVisible():
            self.logger.debug("Đã ẩn cửa sổ thông qua phím tắt")
            self.root.hide()
        else:
            self.logger.debug("Đã hiển thị cửa sổ thông qua phím tắt")
            self._show_main_window()

    async def close(self):
        """
        Xử lý đóng cửa sổ.
        """
        self._running = False
        try:
            self._stop_video()
        except Exception:
            pass
        if self.system_tray:
            self.system_tray.hide()
        if self.root:
            self.root.close()

    # =========================================================================
    # Video (camera / mp4) trong GUI
    # =========================================================================

    def _start_video_from_config(self) -> None:
        """Đọc cấu hình CAMERA.VIDEO_SOURCE để bật video trong GUI.

        - none: tắt video (hiển thị emotion như cũ)
        - camera: dùng OpenCV với camera_index (cần xử lý frame)
        - file: dùng native QML Video player (hardware accelerated, mượt hơn)
        """
        from src.utils.config_manager import ConfigManager
        from src.utils.resource_finder import get_project_root

        cfg = ConfigManager.get_instance()
        camera_cfg = cfg.get_config("CAMERA", {}) or {}
        source = str(camera_cfg.get("VIDEO_SOURCE", "none") or "none").lower()

        if source not in ("camera", "file"):
            self.display_model.update_video_frame_url("")
            self.display_model.update_video_file_path("")
            self._stop_video()
            return

        file_path = str(camera_cfg.get("VIDEO_FILE_PATH", "") or "")
        
        # === VIDEO FILE: Dùng native QML Video player (hardware accelerated) ===
        if source == "file":
            if file_path and not os.path.isabs(file_path):
                file_path = str(get_project_root() / file_path)
            if not file_path or not Path(file_path).exists():
                self.logger.warning("VIDEO_SOURCE=file nhưng VIDEO_FILE_PATH không hợp lệ; tắt video")
                self.display_model.update_video_frame_url("")
                self.display_model.update_video_file_path("")
                self._stop_video()
                return

            # Dùng native video player - mượt mà, có hardware acceleration
            self.logger.info(f"Sử dụng native video player cho: {file_path}")
            self._stop_video()
            self.display_model.update_video_frame_url("")  # Tắt Image-based
            self.display_model.update_video_file_path(file_path)  # Bật native Video
            return

        # === CAMERA: Dùng OpenCV (cần xử lý frame) ===
        loop = bool(camera_cfg.get("VIDEO_LOOP", True))
        fps = int(camera_cfg.get("VIDEO_FPS", camera_cfg.get("fps", 10) or 10))

        camera_index = int(camera_cfg.get("camera_index", 0) or 0)
        frame_width = int(camera_cfg.get("frame_width", 640) or 640)
        frame_height = int(camera_cfg.get("frame_height", 480) or 480)

        cache_dir = get_user_cache_dir(create=True)
        self._video_frame_file = Path(cache_dir) / "digits_video_frame.jpg"

        self._stop_video()
        self.display_model.update_video_file_path("")  # Tắt native Video
        
        self._video_worker = _VideoCaptureWorker(
            source=source,
            camera_index=camera_index,
            frame_width=frame_width,
            frame_height=frame_height,
            file_path=file_path,
            loop=loop,
            fps=fps,
        )
        self._video_worker.start()
        self._video_last_seq = -1

        if self._video_timer is None:
            self._video_timer = QTimer(self.root)
            self._video_timer.timeout.connect(self._on_video_tick)
        self._video_timer.start(max(50, int(1000 / max(1, fps))))

    def _stop_video(self) -> None:
        if self._video_timer is not None:
            try:
                self._video_timer.stop()
            except Exception:
                pass

        if self._video_worker is not None:
            try:
                self._video_worker.stop()
                self._video_worker.join(timeout=1.0)
            except Exception:
                pass

        self._video_worker = None
        self._video_last_seq = -1

    def _on_video_tick(self) -> None:
        """UI thread: poll JPEG bytes mới nhất, ghi ra cache file, cập nhật URL."""
        try:
            if not self._video_worker or not self._video_frame_file:
                return
            seq, jpeg = self._video_worker.pop_latest()
            if jpeg is None or seq == self._video_last_seq:
                return

            tmp = self._video_frame_file.with_suffix(".tmp")
            try:
                tmp.write_bytes(jpeg)
                tmp.replace(self._video_frame_file)
            except Exception:
                try:
                    self._video_frame_file.write_bytes(jpeg)
                except Exception:
                    return

            self._video_last_seq = seq
            url = QUrl.fromLocalFile(str(self._video_frame_file)).toString() + f"?t={seq}"
            self.display_model.update_video_frame_url(url)
        except Exception:
            pass

    # =========================================================================
    # Quy trình khởi động
    # =========================================================================

    async def start(self):
        """
        Khởi động GUI.
        """
        try:
            self._configure_environment()
            self._create_main_window()
            self._load_qml()
            self._setup_interactions()
            await self._finalize_startup()
        except Exception as e:
            self.logger.error(f"Khởi động GUI thất bại: {e}", exc_info=True)
            raise

    def _configure_environment(self):
        """
        Cấu hình môi trường.
        """
        os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.fonts.debug=false")

        self.app = QApplication.instance()
        if self.app is None:
            raise RuntimeError("QApplication không tìm thấy, hãy đảm bảo chạy trong môi trường qasync")

        self.app.setQuitOnLastWindowClosed(False)
        self.app.setFont(QFont("Tahoma, Arial", self.DEFAULT_FONT_SIZE))

        self._setup_signal_handlers()
        self._setup_activation_handler()

    def _create_main_window(self):
        """
        Tạo cửa sổ chính.
        """
        self.root = QWidget()
        self.root.setWindowTitle("")
        self.root.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)

        # Tính kích thước cửa sổ dựa trên cấu hình
        window_size, is_fullscreen = self._calculate_window_size()
        self.root.resize(*window_size)

        # Lưu trạng thái toàn màn hình, sử dụng khi hiển thị
        self._is_fullscreen = is_fullscreen

        self.root.closeEvent = self._closeEvent

    def _setup_interactions(self):
        """
        Thiết lập các tương tác giữa Python và QML.
        """
        self._connect_qml_signals()

    def _calculate_window_size(self) -> tuple:
        """
        Tính kích thước cửa sổ dựa trên cấu hình, trả về (rộng, cao, có toàn màn hình hay không)
        
        Các chế độ hỗ trợ:
        - default: 50% màn hình
        - fullhd: 1920x1080 (Full HD)
        - hd: 1280x720 (HD)
        - vertical_916: tỷ lệ 9:16 dọc
        - screen_75: 75% màn hình
        - screen_100: toàn màn hình
        """
        try:
            from src.utils.config_manager import ConfigManager

            config_manager = ConfigManager.get_instance()
            # Ưu tiên đọc SYSTEM_OPTIONS.WINDOW_SIZE_MODE (chuẩn),
            # nhưng hỗ trợ fallback cho các bản config cũ/khác key.
            window_size_mode = config_manager.get_config("SYSTEM_OPTIONS.WINDOW_SIZE_MODE", None)
            if window_size_mode in (None, "", "null"):
                window_size_mode = config_manager.get_config("WINDOW_SIZE_MODE", "default")
            if window_size_mode in (None, "", "null"):
                window_size_mode = "default"

            # Lấy kích thước màn hình (khu vực khả dụng, loại trừ thanh tác vụ, v.v.)
            desktop = QApplication.desktop()
            screen_rect = desktop.availableGeometry()
            screen_width = screen_rect.width()
            screen_height = screen_rect.height()

            # Tính kích thước cửa sổ dựa trên chế độ
            if window_size_mode == "fullhd":
                # Full HD: 1920x1080, nếu màn hình nhỏ hơn thì dùng toàn màn hình
                if screen_width >= 1920 and screen_height >= 1080:
                    width = 1920
                    height = 1080
                    is_fullscreen = False
                else:
                    # Màn hình nhỏ hơn Full HD => fullscreen
                    width = screen_width
                    height = screen_height
                    is_fullscreen = True
            elif window_size_mode == "hd":
                # HD: 1280x720
                if screen_width >= 1280 and screen_height >= 720:
                    width = 1280
                    height = 720
                    is_fullscreen = False
                else:
                    width = screen_width
                    height = screen_height
                    is_fullscreen = True
            elif window_size_mode == "vertical_916":
                # Tỷ lệ 9:16 dọc (cho video dọc)
                # Dùng 60% chiều cao màn hình
                height = int(screen_height * 0.6)
                width = int(height * 9 / 16)
                is_fullscreen = False
            elif window_size_mode == "screen_75":
                width = int(screen_width * 0.75)
                height = int(screen_height * 0.75)
                is_fullscreen = False
            elif window_size_mode == "screen_100":
                # 100% sử dụng chế độ toàn màn hình thực sự
                width = screen_width
                height = screen_height
                is_fullscreen = True
            elif window_size_mode == "default":
                # Mặc định: chọn theo kích thước màn hình
                # Nếu màn hình >= Full HD thì dùng Full HD, không thì 75%
                if screen_width >= 1920 and screen_height >= 1080:
                    width = 1920
                    height = 1080
                    is_fullscreen = False
                else:
                    width = int(screen_width * 0.75)
                    height = int(screen_height * 0.75)
                    is_fullscreen = False
            else:
                # Chế độ không xác định sử dụng 75%
                width = int(screen_width * 0.75)
                height = int(screen_height * 0.75)
                is_fullscreen = False

            return ((width, height), is_fullscreen)

        except Exception as e:
            self.logger.error(f"Tính kích thước cửa sổ thất bại: {e}", exc_info=True)
            # Khi lỗi, trả về Full HD hoặc 75% màn hình
            try:
                desktop = QApplication.desktop()
                screen_rect = desktop.availableGeometry()
                if screen_rect.width() >= 1920 and screen_rect.height() >= 1080:
                    return ((1920, 1080), False)
                return (
                    (int(screen_rect.width() * 0.75), int(screen_rect.height() * 0.75)),
                    False,
                )
            except Exception:
                return (self.DEFAULT_WINDOW_SIZE, False)

    def _load_qml(self):
        """
        Tải giao diện QML.
        """
        self.qml_widget = QQuickWidget()
        self.qml_widget.setResizeMode(QQuickWidget.SizeRootObjectToView)
        # Nếu QML load lỗi (thiếu module), QQuickWidget sẽ hiển thị clearColor.
        # Dùng nền tối để tránh "màn hình trắng tinh" gây hiểu nhầm app bị treo.
        self.qml_widget.setClearColor(Qt.black)

        # Đăng ký mô hình dữ liệu vào ngữ cảnh QML
        qml_context = self.qml_widget.rootContext()
        qml_context.setContextProperty("displayModel", self.display_model)

        # Logic tải QML: Ưu tiên tệp cục bộ (dev), sau đó dùng ResourceFinder (prod)
        try:
            from src.utils.resource_finder import resource_finder

            found_qml = resource_finder.find_file("gui_display.qml")
            if found_qml:
                qml_file = found_qml
            else:
                # Fallback về đường dẫn tương đối (dev mode)
                qml_file = Path(__file__).parent / "gui_display.qml"
        except ImportError:
            qml_file = Path(__file__).parent / "gui_display.qml"

        if not qml_file.exists():
             print(f"ERROR: Cannot find gui_display.qml at {qml_file}")

        self.qml_widget.setSource(QUrl.fromLocalFile(str(qml_file)))

        # Đặt làm widget trung tâm của cửa sổ chính
        layout = QVBoxLayout(self.root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.qml_widget)
        
        # Đảm bảo cửa sổ cho phép thay đổi kích thước.
        # Tránh đặt min-size quá lớn (có thể khiến WM ép full-screen trên màn hình nhỏ).
        self.root.setMinimumSize(320, 240)

    async def _finalize_startup(self):
        """
        Hoàn thành quy trình khởi động.
        """
        await self.update_emotion("neutral")

        # Video: khởi động theo cấu hình (camera hoặc mp4)
        try:
            self._start_video_from_config()
        except Exception as e:
            self.logger.error(f"Khởi động video thất bại: {e}", exc_info=True)

        # Quyết định chế độ hiển thị dựa trên cấu hình
        if getattr(self, "_is_fullscreen", False):
            self.root.showFullScreen()
        else:
            self.root.show()

        self._setup_system_tray()

    # =========================================================================
    # Kết nối tín hiệu
    # =========================================================================

    def _connect_qml_signals(self):
        """
        Kết nối tín hiệu QML với các slot Python.
        """
        root_object = self.qml_widget.rootObject()
        if not root_object:
            self.logger.warning("Không tìm thấy đối tượng gốc QML, không thể thiết lập kết nối tín hiệu")
            return

        # Bản đồ tín hiệu nút
        button_signals = {
            "manualButtonPressed": self._on_manual_button_press,
            "manualButtonReleased": self._on_manual_button_release,
            "autoButtonClicked": self._on_auto_button_click,
            "abortButtonClicked": self._on_abort_button_click,
            "modeButtonClicked": self._on_mode_button_click,
            "sendButtonClicked": self._on_send_button_click,
            "settingsButtonClicked": self._on_settings_button_click,
        }

        # Bản đồ tín hiệu điều khiển tiêu đề
        titlebar_signals = {
            "titleMinimize": self._minimize_window,
            "titleClose": self._quit_application,
            "titleDragStart": self._on_title_drag_start,
            "titleDragMoveTo": self._on_title_drag_move,
            "titleDragEnd": self._on_title_drag_end,
        }

        # Kết nối tín hiệu hàng loạt
        for signal_name, handler in {**button_signals, **titlebar_signals}.items():
            try:
                getattr(root_object, signal_name).connect(handler)
            except AttributeError:
                self.logger.debug(f"Tín hiệu {signal_name} không tồn tại (có thể là tính năng tùy chọn)")

        self.logger.debug("Kết nối tín hiệu QML đã được thiết lập")

    # =========================================================================
    # Xử lý sự kiện nút
    # =========================================================================

    def _on_manual_button_press(self):
        """
        Nút chế độ thủ công được nhấn.
        """
        self._dispatch_callback("button_press")

    def _on_manual_button_release(self):
        """
        Nút chế độ thủ công được thả.
        """
        self._dispatch_callback("button_release")

    def _on_auto_button_click(self):
        """
        Nút chế độ tự động được nhấn.
        """
        self._dispatch_callback("auto")

    def _on_abort_button_click(self):
        """
        Nút hủy được nhấn.
        """
        self._dispatch_callback("abort")

    def _on_mode_button_click(self):
        """
        Nút chuyển đổi chế độ đối thoại được nhấn.
        """
        if self._callbacks["mode"] and not self._callbacks["mode"]():
            return

        self.auto_mode = not self.auto_mode
        mode_text = "Đối thoại tự động" if self.auto_mode else "Đối thoại thủ công"
        self.display_model.update_mode_text(mode_text)
        self.display_model.set_auto_mode(self.auto_mode)

    def _on_send_button_click(self, text: str):
        """
        Xử lý nút gửi văn bản được nhấn.
        """
        text = text.strip()
        if not text or not self._callbacks["send_text"]:
            return

        try:
            task = asyncio.create_task(self._callbacks["send_text"](text))
            task.add_done_callback(
                lambda t: t.cancelled()
                or not t.exception()
                or self.logger.error(
                    f"Nhiệm vụ gửi văn bản lỗi: {t.exception()}", exc_info=True
                )
            )
        except Exception as e:
            self.logger.error(f"Lỗi khi gửi văn bản: {e}")

    def _on_settings_button_click(self):
        """
        Xử lý nút cài đặt được nhấn.
        """
        try:
            from src.views.settings import SettingsWindow

            # Tạm dừng video để giải phóng camera cho phần xem trước trong cài đặt
            was_video_running = self._video_worker is not None
            if was_video_running:
                self._stop_video()

            settings_window = SettingsWindow(self.root)
            result = settings_window.exec_()
            
            # Luôn tải lại cấu hình video sau khi đóng cài đặt
            # (dù Save hay Cancel, cần khôi phục hoặc cập nhật)
            self.reload_video_from_config()

        except Exception as e:
            self.logger.error(f"Mở cửa sổ cài đặt thất bại: {e}", exc_info=True)
            # Cố gắng khôi phục video nếu có lỗi
            try:
                self.reload_video_from_config()
            except:
                pass

    def reload_video_from_config(self) -> None:
        """Áp dụng ngay cấu hình video GUI (không cần restart app)."""
        try:
            # Tính lại kích thước cửa sổ dựa trên WINDOW_SIZE_MODE mới
            window_size, is_fullscreen = self._calculate_window_size()
            
            # Resize cửa sổ theo cấu hình mới
            if self.root:
                self.root.resize(*window_size)
                self._is_fullscreen = is_fullscreen
                self.logger.info(f"Đã resize cửa sổ: {window_size} (fullscreen={is_fullscreen})")
            
            # Khởi động lại video với cấu hình mới
            self._start_video_from_config()
        except Exception as e:
            self.logger.error(f"Áp dụng cấu hình video thất bại: {e}", exc_info=True)

    def _dispatch_callback(self, callback_name: str, *args):
        """
        Bộ phân phối callback chung.
        """
        callback = self._callbacks.get(callback_name)
        if callback:
            callback(*args)

    # =========================================================================
    # Kéo cửa sổ
    # =========================================================================

    def _on_title_drag_start(self, _x, _y):
        """
        Bắt đầu kéo tiêu đề.
        """
        self._dragging = True
        self._drag_position = QCursor.pos() - self.root.pos()

    def _on_title_drag_move(self, _x, _y):
        """
        Di chuyển tiêu đề khi kéo.
        """
        if self._dragging and self._drag_position:
            self.root.move(QCursor.pos() - self._drag_position)

    def _on_title_drag_end(self):
        """
        Kết thúc kéo tiêu đề.
        """
        self._dragging = False
        self._drag_position = None

    # =========================================================================
    # Quản lý biểu cảm
    # =========================================================================

    def _get_emotion_asset_path(self, emotion_name: str) -> str:
        """
        Lấy đường dẫn file tài nguyên biểu cảm, tự động khớp với các phần mở rộng phổ biến.
        """
        if emotion_name in self._emotion_cache:
            return self._emotion_cache[emotion_name]

        assets_dir = find_assets_dir()
        if not assets_dir:
            path = "😊"
        else:
            emotion_dir = assets_dir / "emojis"
            # Thử tìm file biểu cảm, nếu thất bại thì quay lại trạng thái neutral
            path = (
                str(self._find_emotion_file(emotion_dir, emotion_name))
                or str(self._find_emotion_file(emotion_dir, "neutral"))
                or "😊"
            )

        self._emotion_cache[emotion_name] = path
        return path

    def _find_emotion_file(self, emotion_dir: Path, name: str) -> Optional[Path]:
        """
        Tìm file biểu cảm trong thư mục chỉ định.
        """
        for ext in self.EMOTION_EXTENSIONS:
            file_path = emotion_dir / f"{name}{ext}"
            if file_path.exists():
                return file_path
        return None

    # =========================================================================
    # Cài đặt hệ thống
    # =========================================================================

    def _setup_signal_handlers(self):
        """
        Thiết lập bộ xử lý tín hiệu (Ctrl+C)
        """
        try:
            signal.signal(
                signal.SIGINT,
                lambda *_: QTimer.singleShot(0, self._quit_application),
            )
        except Exception as e:
            self.logger.warning(f"Thiết lập bộ xử lý tín hiệu thất bại: {e}")

    def _setup_activation_handler(self):
        """
        Thiết lập bộ xử lý kích hoạt ứng dụng (nhấp vào biểu tượng Dock trên macOS để khôi phục cửa sổ)
        """
        try:
            import platform

            if platform.system() != "Darwin":
                return

            self.app.applicationStateChanged.connect(self._on_application_state_changed)
            self.logger.debug("Đã thiết lập bộ xử lý kích hoạt ứng dụng (hỗ trợ Dock trên macOS)")
        except Exception as e:
            self.logger.warning(f"Thiết lập bộ xử lý kích hoạt ứng dụng thất bại: {e}")

    def _on_application_state_changed(self, state):
        """
        Xử lý thay đổi trạng thái ứng dụng (khi nhấp vào Dock trên macOS để khôi phục cửa sổ)
        """
        if state == Qt.ApplicationActive and self.root and not self.root.isVisible():
            QTimer.singleShot(0, self._show_main_window)

    def _setup_system_tray(self):
        """
        Thiết lập khay hệ thống.
        """
        if os.getenv("DIGITS_DISABLE_TRAY") == "1" or os.getenv("XIAOZHI_DISABLE_TRAY") == "1":
            self.logger.warning("Đã vô hiệu hóa khay hệ thống thông qua biến môi trường (DIGITS_DISABLE_TRAY=1)")
            return

        try:
            from src.views.components.system_tray import SystemTray

            self.system_tray = SystemTray(self.root)

            # Kết nối tín hiệu khay (sử dụng QTimer để đảm bảo thực hiện trên luồng chính)
            tray_signals = {
                "show_window_requested": self._show_main_window,
                "settings_requested": self._on_settings_button_click,
                "quit_requested": self._quit_application,
            }

            for signal_name, handler in tray_signals.items():
                getattr(self.system_tray, signal_name).connect(
                    lambda h=handler: QTimer.singleShot(0, h)
                )

        except Exception as e:
            self.logger.error(f"Khởi tạo thành phần khay hệ thống thất bại: {e}", exc_info=True)

    # =========================================================================
    # Điều khiển cửa sổ
    # =========================================================================

    def _show_main_window(self):
        """
        Hiển thị cửa sổ chính.
        """
        if not self.root:
            return

        if self.root.isMinimized():
            self.root.showNormal()
        if not self.root.isVisible():
            self.root.show()
        self.root.activateWindow()
        self.root.raise_()

    def _minimize_window(self):
        """
        Thu nhỏ cửa sổ.
        """
        if self.root:
            self.root.showMinimized()

    def _quit_application(self):
        """
        Thoát ứng dụng.
        """
        self.logger.info("Bắt đầu thoát ứng dụng...")
        self._running = False

        if self.system_tray:
            self.system_tray.hide()

        try:
            from src.application import Application

            app = Application.get_instance()
            if not app:
                QApplication.quit()
                return

            loop = asyncio.get_event_loop()
            if not loop.is_running():
                QApplication.quit()
                return

            # Tạo nhiệm vụ đóng và thiết lập thời gian chờ
            shutdown_task = asyncio.create_task(app.shutdown())

            def on_shutdown_complete(task):
                if not task.cancelled() and task.exception():
                    self.logger.error(f"Lỗi khi đóng ứng dụng: {task.exception()}")
                else:
                    self.logger.info("Ứng dụng đã đóng bình thường")
                QApplication.quit()

            def force_quit():
                if not shutdown_task.done():
                    self.logger.warning("Đóng quá thời gian chờ, buộc thoát")
                    shutdown_task.cancel()
                QApplication.quit()

            shutdown_task.add_done_callback(on_shutdown_complete)
            QTimer.singleShot(self.QUIT_TIMEOUT_MS, force_quit)

        except Exception as e:
            self.logger.error(f"Đóng ứng dụng thất bại: {e}")
            QApplication.quit()

    def _closeEvent(self, event):
        """
        Xử lý sự kiện đóng cửa sổ.
        """
        # Nếu khay hệ thống khả dụng, thu nhỏ vào khay
        if self.system_tray and (
            getattr(self.system_tray, "is_available", lambda: False)()
            or getattr(self.system_tray, "is_visible", lambda: False)()
        ):
            self.logger.info("Đóng cửa sổ: Thu nhỏ vào khay")
            QTimer.singleShot(0, self.root.hide)
            event.ignore()
        else:
            QTimer.singleShot(0, self._quit_application)
            event.accept()
