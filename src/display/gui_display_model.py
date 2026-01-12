# -*- coding: utf-8 -*-
"""
Mô hình dữ liệu hiển thị GUI - dùng để liên kết dữ liệu với QML.
"""

from PyQt5.QtCore import QObject, pyqtProperty, pyqtSignal


class GuiDisplayModel(QObject):
    """
    Mô hình dữ liệu của cửa sổ chính GUI, dùng để liên kết dữ liệu giữa Python và QML.
    """

    # Tín hiệu thay đổi thuộc tính
    statusTextChanged = pyqtSignal()
    emotionPathChanged = pyqtSignal()
    ttsTextChanged = pyqtSignal()
    userTextChanged = pyqtSignal()
    buttonTextChanged = pyqtSignal()
    modeTextChanged = pyqtSignal()
    autoModeChanged = pyqtSignal()
    videoFrameUrlChanged = pyqtSignal()
    videoFilePathChanged = pyqtSignal()  # Path cho native video player

    # Tín hiệu thao tác người dùng
    manualButtonPressed = pyqtSignal()
    manualButtonReleased = pyqtSignal()
    autoButtonClicked = pyqtSignal()
    abortButtonClicked = pyqtSignal()
    modeButtonClicked = pyqtSignal()
    sendButtonClicked = pyqtSignal(str)  # Kèm theo văn bản nhập vào
    settingsButtonClicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Thuộc tính riêng tư
        self._status_text = "Trạng thái: Chưa kết nối"
        self._emotion_path = ""  # Đường dẫn tài nguyên biểu cảm (GIF/hình ảnh) hoặc ký tự emoji
        self._tts_text = "Đang chờ"
        self._user_text = ""
        self._button_text = "Bắt đầu đối thoại"  # Văn bản nút chế độ tự động
        self._mode_text = "Đối thoại thủ công"  # Văn bản nút chuyển đổi chế độ
        self._auto_mode = False  # Có đang ở chế độ tự động hay không
        self._is_connected = False
        self._video_frame_url = ""  # URL file:///... (kèm cache-bust query) cho khung video
        self._video_file_path = ""  # Path file video để native player phát (hardware accelerated)

    # Thuộc tính văn bản trạng thái
    @pyqtProperty(str, notify=statusTextChanged)
    def statusText(self):
        return self._status_text

    @statusText.setter
    def statusText(self, value):
        if self._status_text != value:
            self._status_text = value
            self.statusTextChanged.emit()

    # Thuộc tính đường dẫn biểu cảm
    @pyqtProperty(str, notify=emotionPathChanged)
    def emotionPath(self):
        return self._emotion_path

    @emotionPath.setter
    def emotionPath(self, value):
        if self._emotion_path != value:
            self._emotion_path = value
            self.emotionPathChanged.emit()

    # Thuộc tính văn bản TTS
    @pyqtProperty(str, notify=ttsTextChanged)
    def ttsText(self):
        return self._tts_text

    @ttsText.setter
    def ttsText(self, value):
        if self._tts_text != value:
            self._tts_text = value
            self.ttsTextChanged.emit()

    # Thuộc tính văn bản người dùng (Câu hỏi)
    @pyqtProperty(str, notify=userTextChanged)
    def userText(self):
        return self._user_text

    @userText.setter
    def userText(self, value):
        if self._user_text != value:
            self._user_text = value
            self.userTextChanged.emit()

    # Thuộc tính văn bản nút chế độ tự động
    @pyqtProperty(str, notify=buttonTextChanged)
    def buttonText(self):
        return self._button_text

    @buttonText.setter
    def buttonText(self, value):
        if self._button_text != value:
            self._button_text = value
            self.buttonTextChanged.emit()

    # Thuộc tính văn bản nút chuyển đổi chế độ
    @pyqtProperty(str, notify=modeTextChanged)
    def modeText(self):
        return self._mode_text

    @modeText.setter
    def modeText(self, value):
        if self._mode_text != value:
            self._mode_text = value
            self.modeTextChanged.emit()

    # Thuộc tính trạng thái chế độ tự động
    @pyqtProperty(bool, notify=autoModeChanged)
    def autoMode(self):
        return self._auto_mode

    @autoMode.setter
    def autoMode(self, value):
        if self._auto_mode != value:
            self._auto_mode = value
            self.autoModeChanged.emit()

    # URL khung video (file:///...?...)
    @pyqtProperty(str, notify=videoFrameUrlChanged)
    def videoFrameUrl(self):
        return self._video_frame_url

    @videoFrameUrl.setter
    def videoFrameUrl(self, value):
        if self._video_frame_url != value:
            self._video_frame_url = value
            self.videoFrameUrlChanged.emit()

    # Path file video cho native player (hardware accelerated)
    @pyqtProperty(str, notify=videoFilePathChanged)
    def videoFilePath(self):
        return self._video_file_path

    @videoFilePath.setter
    def videoFilePath(self, value):
        if self._video_file_path != value:
            self._video_file_path = value
            self.videoFilePathChanged.emit()

    def update_video_file_path(self, path: str):
        """Cập nhật path file video cho native player."""
        from PyQt5.QtCore import QUrl
        if path:
            self.videoFilePath = QUrl.fromLocalFile(path).toString()
        else:
            self.videoFilePath = ""

    # Phương pháp tiện ích
    def update_status(self, status: str, connected: bool):
        """
        Cập nhật văn bản trạng thái và trạng thái kết nối.
        """
        self.statusText = f"Trạng thái: {status}"
        self._is_connected = connected

    def update_text(self, text: str):
        """
        Cập nhật văn bản TTS.
        """
        self.ttsText = text

    def update_user_text(self, text: str):
        """
        Cập nhật văn bản người dùng (Câu hỏi).
        """
        self.userText = text

    def update_emotion(self, emotion_path: str):
        """
        Cập nhật đường dẫn biểu cảm.
        """
        self.emotionPath = emotion_path

    def update_button_text(self, text: str):
        """
        Cập nhật văn bản nút chế độ tự động.
        """
        self.buttonText = text

    def update_mode_text(self, text: str):
        """
        Cập nhật văn bản nút chuyển đổi chế độ.
        """
        self.modeText = text

    def set_auto_mode(self, is_auto: bool):
        """
        Thiết lập chế độ tự động.
        """
        self.autoMode = is_auto
        if is_auto:
            self.modeText = "Đối thoại tự động"
        else:
            self.modeText = "Đối thoại thủ công"

    def update_video_frame_url(self, url: str):
        """Cập nhật URL khung video (dùng cho QML Image)."""
        self.videoFrameUrl = url or ""
