import logging
from logging.handlers import TimedRotatingFileHandler

from colorlog import ColoredFormatter


def setup_logging():
    """
    Thiết lập hệ thống ghi log.
    """
    from .resource_finder import get_project_root

    # Dùng resource_finder để lấy project root và tạo thư mục logs
    project_root = get_project_root()
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)

    # Đường dẫn file log
    log_file = log_dir / "app.log"

    # Tạo root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)  # mức log mặc định

    # Xóa các handler cũ (tránh add trùng)
    if root_logger.handlers:
        root_logger.handlers.clear()

    # Handler log ra console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Handler log ra file, xoay vòng theo ngày
    file_handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",  # cắt log lúc 0h
        interval=1,  # mỗi 1 ngày
        backupCount=30,  # giữ 30 ngày
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.suffix = "%Y-%m-%d.log"  # hậu tố file log

    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s[%(name)s] - %(levelname)s - %(message)s - %(threadName)s"
    )

    # Formatter màu cho console
    color_formatter = ColoredFormatter(
        "%(green)s%(asctime)s%(reset)s[%(blue)s%(name)s%(reset)s] - "
        "%(log_color)s%(levelname)s%(reset)s - %(green)s%(message)s%(reset)s - "
        "%(cyan)s%(threadName)s%(reset)s",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "white",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
        secondary_log_colors={"asctime": {"green": "green"}, "name": {"blue": "blue"}},
    )
    console_handler.setFormatter(color_formatter)
    file_handler.setFormatter(formatter)

    # Gắn handler vào root logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Thông báo cấu hình log
    logging.info("Hệ thống log đã khởi tạo, file log: %s", log_file)

    return log_file


def get_logger(name):
    """Lấy logger đã được cấu hình thống nhất.

    Args:
        name: Tên logger (thường dùng __name__)

    Returns:
        logging.Logger: Logger đã cấu hình

    Ví dụ:
        logger = get_logger(__name__)
        logger.info("Đây là một thông tin")
        logger.error("Có lỗi: %s", error_msg)
    """
    logger = logging.getLogger(name)

    # Thêm helper method
    def log_error_with_exc(msg, *args, **kwargs):
        """
        Ghi lỗi và tự động kèm stacktrace.
        """
        kwargs["exc_info"] = True
        logger.error(msg, *args, **kwargs)

    # Gắn vào logger
    logger.error_exc = log_error_with_exc

    return logger
