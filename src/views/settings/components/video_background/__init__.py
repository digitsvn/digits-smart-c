"""
Widget cài đặt nền video/emotion.
Cho phép chọn video nền hoặc dùng emotion từ server.
"""

from pathlib import Path
from typing import Dict, Any

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QButtonGroup,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QGroupBox,
    QMessageBox,
)

from src.utils.config_manager import ConfigManager
from src.utils.logging_config import get_logger
from src.utils.resource_finder import get_project_root


class VideoBackgroundWidget(QWidget):
    """Widget cài đặt nền video/emotion."""

    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self.config_manager = ConfigManager.get_instance()

        self._setup_ui()
        self._load_current_config()

    def _setup_ui(self):
        """Thiết lập giao diện."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Title
        title = QLabel("🎬 Cài Đặt Nền Hiển Thị")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # Description
        desc = QLabel(
            "Chọn hiển thị video nền hoặc để app hiển thị emotion từ server.\n"
            "Video nền sử dụng hardware acceleration cho hiệu năng tốt nhất."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666;")
        layout.addWidget(desc)


        # Background Mode Group
        mode_group = QGroupBox("Chế độ nền")
        mode_layout = QVBoxLayout(mode_group)

        self.mode_button_group = QButtonGroup(self)

        # Option 1: Emotion from server
        self.emotion_radio = QRadioButton("🎭 Emotion từ server (mặc định)")
        self.emotion_radio.setToolTip("Hiển thị emotion/avatar từ server AI")
        self.mode_button_group.addButton(self.emotion_radio, 0)
        mode_layout.addWidget(self.emotion_radio)

        # Option 2: Video background
        self.video_radio = QRadioButton("🎬 Video/WebP nền")
        self.video_radio.setToolTip("Phát video hoặc WebP animation làm nền")
        self.mode_button_group.addButton(self.video_radio, 1)
        mode_layout.addWidget(self.video_radio)

        # Video file path
        video_path_layout = QHBoxLayout()
        video_path_layout.addSpacing(25)  # Indent
        
        self.video_path_edit = QLineEdit()
        self.video_path_edit.setPlaceholderText("Đường dẫn file video (.mp4, .webp, ...)")
        video_path_layout.addWidget(self.video_path_edit)

        self.browse_btn = QPushButton("📁 Chọn file")
        self.browse_btn.clicked.connect(self._browse_video)
        video_path_layout.addWidget(self.browse_btn)

        mode_layout.addLayout(video_path_layout)

        # Option 3: YouTube URL
        self.youtube_radio = QRadioButton("📺 YouTube URL")
        self.youtube_radio.setToolTip("Stream video từ YouTube (cần internet, có thể lag)")
        self.mode_button_group.addButton(self.youtube_radio, 2)
        mode_layout.addWidget(self.youtube_radio)

        # YouTube URL input
        youtube_layout = QHBoxLayout()
        youtube_layout.addSpacing(25)
        
        self.youtube_url_edit = QLineEdit()
        self.youtube_url_edit.setPlaceholderText("https://www.youtube.com/watch?v=... hoặc https://youtu.be/...")
        youtube_layout.addWidget(self.youtube_url_edit)
        
        mode_layout.addLayout(youtube_layout)

        layout.addWidget(mode_group)

        # Available videos
        videos_group = QGroupBox("Video có sẵn")
        videos_layout = QVBoxLayout(videos_group)

        self.video_list_label = QLabel("Đang tìm video...")
        self.video_list_label.setWordWrap(True)
        videos_layout.addWidget(self.video_list_label)

        # Quick select buttons
        self.quick_select_layout = QHBoxLayout()
        videos_layout.addLayout(self.quick_select_layout)

        layout.addWidget(videos_group)

        # Spacer
        layout.addStretch()

        # Connect signals
        self.mode_button_group.buttonClicked.connect(self._on_mode_changed)
        self.video_path_edit.textChanged.connect(self._on_settings_changed)
        self.youtube_url_edit.textChanged.connect(self._on_settings_changed)

        # Load available videos
        self._refresh_video_list()

    def _browse_video(self):
        """Mở dialog chọn file video."""
        start_dir = str(get_project_root() / "assets" / "videos")
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn file video",
            start_dir,
            "Video/Animation Files (*.mp4 *.webp *.gif *.webm *.mkv);;All Files (*)"
        )
        if file_path:
            # Convert to relative path if inside project
            try:
                rel_path = Path(file_path).relative_to(get_project_root())
                self.video_path_edit.setText(str(rel_path))
            except ValueError:
                self.video_path_edit.setText(file_path)
            
            self.video_radio.setChecked(True)
            self._on_settings_changed()

    def _refresh_video_list(self):
        """Tìm và hiển thị danh sách video có sẵn."""
        videos_dir = get_project_root() / "assets" / "videos"
        
        if not videos_dir.exists():
            self.video_list_label.setText("Không tìm thấy thư mục assets/videos/")
            return

        videos = (
            list(videos_dir.glob("*.mp4")) + 
            list(videos_dir.glob("*.webm")) +
            list(videos_dir.glob("*.webp")) +
            list(videos_dir.glob("*.gif"))
        )
        
        if not videos:
            self.video_list_label.setText("Không có video trong assets/videos/")
            return

        # Clear old buttons
        for i in reversed(range(self.quick_select_layout.count())):
            widget = self.quick_select_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        self.video_list_label.setText(f"Tìm thấy {len(videos)} video:")

        # Add quick select buttons
        for video_path in videos[:5]:  # Max 5 buttons
            btn = QPushButton(video_path.name)
            btn.clicked.connect(lambda checked, p=video_path: self._quick_select_video(p))
            self.quick_select_layout.addWidget(btn)

    def _quick_select_video(self, video_path: Path):
        """Chọn nhanh video."""
        try:
            rel_path = video_path.relative_to(get_project_root())
            self.video_path_edit.setText(str(rel_path))
        except ValueError:
            self.video_path_edit.setText(str(video_path))
        
        self.video_radio.setChecked(True)
        self._on_settings_changed()

    def _on_mode_changed(self, button):
        """Xử lý khi đổi mode."""
        self._update_ui_state()
        self._on_settings_changed()

    def _update_ui_state(self):
        """Cập nhật trạng thái UI theo mode."""
        is_video = self.video_radio.isChecked()
        is_youtube = self.youtube_radio.isChecked()
        
        self.video_path_edit.setEnabled(is_video)
        self.browse_btn.setEnabled(is_video)
        self.youtube_url_edit.setEnabled(is_youtube)

    def _on_settings_changed(self):
        """Phát signal khi settings thay đổi."""
        self.settings_changed.emit()

    def _load_current_config(self):
        """Load cấu hình hiện tại."""
        try:
            video_cfg = self.config_manager.get_config("VIDEO_BACKGROUND", {}) or {}
            
            enabled = video_cfg.get("ENABLED", False)
            video_path = video_cfg.get("VIDEO_FILE_PATH", "")
            youtube_url = video_cfg.get("YOUTUBE_URL", "")
            source_type = video_cfg.get("SOURCE_TYPE", "file")  # file, youtube

            if enabled:
                if source_type == "youtube" and youtube_url:
                    self.youtube_radio.setChecked(True)
                    self.youtube_url_edit.setText(youtube_url)
                elif video_path:
                    self.video_radio.setChecked(True)
                    self.video_path_edit.setText(video_path)
                else:
                    self.emotion_radio.setChecked(True)
            else:
                self.emotion_radio.setChecked(True)
                self.video_path_edit.setText(video_path if video_path else "")
                self.youtube_url_edit.setText(youtube_url if youtube_url else "")

            self._update_ui_state()

        except Exception as e:
            self.logger.error(f"Lỗi load config: {e}")
            self.emotion_radio.setChecked(True)

    def get_config_data(self) -> Dict[str, Any]:
        """Lấy dữ liệu cấu hình để lưu."""
        is_video = self.video_radio.isChecked()
        is_youtube = self.youtube_radio.isChecked()
        video_path = self.video_path_edit.text().strip()
        youtube_url = self.youtube_url_edit.text().strip()

        config = {
            "VIDEO_BACKGROUND.VIDEO_LOOP": True,
        }
        
        if is_youtube and youtube_url:
            config["VIDEO_BACKGROUND.ENABLED"] = True
            config["VIDEO_BACKGROUND.SOURCE_TYPE"] = "youtube"
            config["VIDEO_BACKGROUND.YOUTUBE_URL"] = youtube_url
            config["VIDEO_BACKGROUND.VIDEO_FILE_PATH"] = ""
        elif is_video and video_path:
            config["VIDEO_BACKGROUND.ENABLED"] = True
            config["VIDEO_BACKGROUND.SOURCE_TYPE"] = "file"
            config["VIDEO_BACKGROUND.VIDEO_FILE_PATH"] = video_path
            config["VIDEO_BACKGROUND.YOUTUBE_URL"] = ""
        else:
            config["VIDEO_BACKGROUND.ENABLED"] = False
            config["VIDEO_BACKGROUND.SOURCE_TYPE"] = "file"
            config["VIDEO_BACKGROUND.VIDEO_FILE_PATH"] = video_path
            config["VIDEO_BACKGROUND.YOUTUBE_URL"] = youtube_url
        
        return config

    def reset_to_defaults(self):
        """Reset về giá trị mặc định."""
        self.emotion_radio.setChecked(True)
        self.video_path_edit.setText("assets/videos/HTMTECH.webp")
        self.youtube_url_edit.setText("")
        self._update_ui_state()
