"""Bộ công cụ trình phát nhạc.

Cung cấp các chức năng phát nhạc đầy đủ, bao gồm tìm kiếm, phát, tạm dừng, dừng, chuyển bài, v.v.
"""

from .manager import MusicToolsManager, get_music_tools_manager
from .music_player import get_music_player_instance

__all__ = [
    "MusicToolsManager",
    "get_music_tools_manager",
    "get_music_player_instance",
]
