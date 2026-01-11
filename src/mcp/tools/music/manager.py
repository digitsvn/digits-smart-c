"""Trình quản lý công cụ nhạc.

Chịu trách nhiệm khởi tạo, cấu hình và đăng ký công cụ MCP cho công cụ nhạc.
"""

from typing import Any, Dict

from src.utils.logging_config import get_logger

from .music_player import get_music_player_instance

logger = get_logger(__name__)


class MusicToolsManager:
    """
    Trình quản lý công cụ nhạc.
    """

    def __init__(self):
        """
        Khởi tạo trình quản lý công cụ nhạc.
        """
        self._initialized = False
        self._music_player = None
        logger.info("[MusicManager] Khởi tạo trình quản lý công cụ nhạc")

    def init_tools(self, add_tool, PropertyList, Property, PropertyType):
        """
        Khởi tạo và đăng ký tất cả các công cụ nhạc.
        """
        try:
            logger.info("[MusicManager] Bắt đầu đăng ký công cụ nhạc")

            # Lấy instance trình phát nhạc singleton
            self._music_player = get_music_player_instance()

            # Đăng ký công cụ tìm kiếm và phát
            self._register_search_and_play_tool(
                add_tool, PropertyList, Property, PropertyType
            )

            # Đăng ký công cụ phát/tạm dừng
            self._register_play_pause_tool(add_tool, PropertyList)

            # Đăng ký công cụ dừng
            self._register_stop_tool(add_tool, PropertyList)

            # Đăng ký công cụ tua
            self._register_seek_tool(add_tool, PropertyList, Property, PropertyType)

            # Đăng ký công cụ lấy lời bài hát
            self._register_get_lyrics_tool(add_tool, PropertyList)

            # Đăng ký công cụ lấy trạng thái
            self._register_get_status_tool(add_tool, PropertyList)

            # Đăng ký công cụ lấy danh sách phát cục bộ
            self._register_get_local_playlist_tool(
                add_tool, PropertyList, Property, PropertyType
            )

            self._initialized = True
            logger.info("[MusicManager] Đăng ký công cụ nhạc hoàn tất")

        except Exception as e:
            logger.error(f"[MusicManager] Đăng ký công cụ nhạc thất bại: {e}", exc_info=True)
            raise

    def _register_search_and_play_tool(
        self, add_tool, PropertyList, Property, PropertyType
    ):
        """
        Đăng ký công cụ tìm kiếm và phát.
        """

        async def search_and_play_wrapper(args: Dict[str, Any]) -> str:
            song_name = args.get("song_name", "")
            result = await self._music_player.search_and_play(song_name)
            return result.get("message", "Tìm kiếm và phát hoàn tất")

        search_props = PropertyList([Property("song_name", PropertyType.STRING)])

        add_tool(
            (
                "music_player.search_and_play",
                "Search for a song and start playing it. Finds songs by name and "
                "automatically starts playback. Use this to play specific songs "
                "requested by the user.",
                search_props,
                search_and_play_wrapper,
            )
        )
        logger.debug("[MusicManager] Đăng ký công cụ tìm kiếm và phát thành công")

    def _register_play_pause_tool(self, add_tool, PropertyList):
        """
        Đăng ký công cụ phát/tạm dừng.
        """

        async def play_pause_wrapper(args: Dict[str, Any]) -> str:
            result = await self._music_player.play_pause()
            return result.get("message", "Chuyển trạng thái phát hoàn tất")

        add_tool(
            (
                "music_player.play_pause",
                "Toggle between play and pause states. If music is playing, it will "
                "pause. If music is paused or stopped, it will resume or start playing. "
                "Use this when user wants to pause/resume music.",
                PropertyList(),
                play_pause_wrapper,
            )
        )
        logger.debug("[MusicManager] Đăng ký công cụ phát/tạm dừng thành công")

    def _register_stop_tool(self, add_tool, PropertyList):
        """
        Đăng ký công cụ dừng.
        """

        async def stop_wrapper(args: Dict[str, Any]) -> str:
            result = await self._music_player.stop()
            return result.get("message", "Dừng phát hoàn tất")

        add_tool(
            (
                "music_player.stop",
                "Stop music playback completely. This will stop the current song "
                "and reset the position to the beginning. Use this when user wants "
                "to stop music completely.",
                PropertyList(),
                stop_wrapper,
            )
        )
        logger.debug("[MusicManager] Đăng ký công cụ dừng thành công")

    def _register_seek_tool(self, add_tool, PropertyList, Property, PropertyType):
        """
        Đăng ký công cụ tua.
        """

        async def seek_wrapper(args: Dict[str, Any]) -> str:
            position = args.get("position", 0)
            result = await self._music_player.seek(float(position))
            return result.get("message", "Tua hoàn tất")

        seek_props = PropertyList(
            [Property("position", PropertyType.INTEGER, min_value=0)]
        )

        add_tool(
            (
                "music_player.seek",
                "Jump to a specific position in the currently playing song. "
                "Position is specified in seconds from the beginning. Use this "
                "when user wants to skip to a specific part of a song.",
                seek_props,
                seek_wrapper,
            )
        )
        logger.debug("[MusicManager] Đăng ký công cụ tua thành công")

    def _register_get_lyrics_tool(self, add_tool, PropertyList):
        """
        Đăng ký công cụ lấy lời bài hát.
        """

        async def get_lyrics_wrapper(args: Dict[str, Any]) -> str:
            result = await self._music_player.get_lyrics()
            if result.get("status") == "success":
                lyrics = result.get("lyrics", [])
                return "Lời bài hát:\n" + "\n".join(lyrics)
            else:
                return result.get("message", "Lấy lời bài hát thất bại")

        add_tool(
            (
                "music_player.get_lyrics",
                "Get the lyrics of the currently playing song. Returns the complete "
                "lyrics with timestamps. Use this when user asks for lyrics or wants "
                "to see the words of the current song.",
                PropertyList(),
                get_lyrics_wrapper,
            )
        )
        logger.debug("[MusicManager] Đăng ký công cụ lấy lời bài hát thành công")

    def _register_get_status_tool(self, add_tool, PropertyList):
        """
        Đăng ký công cụ lấy trạng thái.
        """

        async def get_status_wrapper(args: Dict[str, Any]) -> str:
            result = await self._music_player.get_status()
            if result.get("status") == "success":
                status_info = []
                status_info.append(f"Bài hát hiện tại: {result.get('current_song', 'Không có')}")
                status_info.append(
                    f"Trạng thái phát: {'Đang phát' if result.get('is_playing') else 'Đã dừng'}"
                )
                if result.get("is_playing"):
                    if result.get("paused"):
                        status_info.append("Trạng thái: Đã tạm dừng")
                    else:
                        status_info.append("Trạng thái: Đang phát")

                    duration = result.get("duration", 0)
                    position = result.get("position", 0)
                    progress = result.get("progress", 0)

                    status_info.append(f"Thời lượng: {self._format_time(duration)}")
                    status_info.append(f"Vị trí hiện tại: {self._format_time(position)}")
                    status_info.append(f"Tiến độ phát: {progress}%")
                    has_lyrics = "Có" if result.get("has_lyrics") else "Không"
                    status_info.append(f"Lời bài hát có sẵn: {has_lyrics}")

                return "\n".join(status_info)
            else:
                return "Lấy trạng thái trình phát thất bại"

        add_tool(
            (
                "music_player.get_status",
                "Get the current status of the music player including current song, "
                "play state, position, duration, and progress. Use this to check "
                "what's currently playing or get detailed playback information.",
                PropertyList(),
                get_status_wrapper,
            )
        )
        logger.debug("[MusicManager] Đăng ký công cụ lấy trạng thái thành công")

    def _register_get_local_playlist_tool(
        self, add_tool, PropertyList, Property, PropertyType
    ):
        """
        Đăng ký công cụ lấy danh sách phát cục bộ.
        """

        async def get_local_playlist_wrapper(args: Dict[str, Any]) -> str:
            force_refresh = args.get("force_refresh", False)
            result = await self._music_player.get_local_playlist(force_refresh)

            if result.get("status") == "success":
                playlist = result.get("playlist", [])
                total_count = result.get("total_count", 0)

                if playlist:
                    playlist_text = f"Danh sách nhạc cục bộ ({total_count} bài):\n"
                    playlist_text += "\n".join(playlist)
                    return playlist_text
                else:
                    return "Không có tệp nhạc trong bộ nhớ đệm cục bộ"
            else:
                return result.get("message", "Lấy danh sách phát cục bộ thất bại")

        refresh_props = PropertyList(
            [Property("force_refresh", PropertyType.BOOLEAN, default_value=False)]
        )

        add_tool(
            (
                "music_player.get_local_playlist",
                "Get the local music playlist from cache. Shows all songs that have been "
                "downloaded and cached locally. Returns songs in format 'Title - Artist'. "
                "To play a song from this list, use search_and_play with just the song title "
                "(not the full 'Title - Artist' format). For example: if the list shows "
                "'菊花台 - 周杰伦', call search_and_play with song_name='菊花台'.",
                refresh_props,
                get_local_playlist_wrapper,
            )
        )
        logger.debug("[MusicManager] Đăng ký công cụ lấy danh sách phát cục bộ thành công")

    def _format_time(self, seconds: float) -> str:
        """
        Định dạng giây thành định dạng mm:ss.
        """
        minutes = int(seconds) // 60
        seconds = int(seconds) % 60
        return f"{minutes:02d}:{seconds:02d}"

    def is_initialized(self) -> bool:
        """
        Kiểm tra xem trình quản lý đã được khởi tạo chưa.
        """
        return self._initialized

    def get_status(self) -> Dict[str, Any]:
        """
        Lấy trạng thái trình quản lý.
        """
        return {
            "initialized": self._initialized,
            "tools_count": 7,  # Số lượng công cụ đã đăng ký hiện tại
            "available_tools": [
                "search_and_play",
                "play_pause",
                "stop",
                "seek",
                "get_lyrics",
                "get_status",
                "get_local_playlist",
            ],
            "music_player_ready": self._music_player is not None,
        }


# Instance trình quản lý toàn cục
_music_tools_manager = None


def get_music_tools_manager() -> MusicToolsManager:
    """
    Lấy singleton trình quản lý công cụ nhạc.
    """
    global _music_tools_manager
    if _music_tools_manager is None:
        _music_tools_manager = MusicToolsManager()
        logger.debug("[MusicManager] Đã tạo instance trình quản lý công cụ nhạc")
    return _music_tools_manager
