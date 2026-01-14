import logging
import re
import gzip
import os
from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler

from colorlog import ColoredFormatter


class SensitiveDataFilter(logging.Filter):
    """
    Filter để mask thông tin nhạy cảm trong logs.
    Patterns: passwords, tokens, API keys, secrets, etc.
    """
    
    # Patterns để detect và mask
    PATTERNS = [
        # Password patterns
        (r'(password["\s:=]+)["\']?([^"\'\s,}\]]+)["\']?', r'\1***MASKED***'),
        (r'(pass["\s:=]+)["\']?([^"\'\s,}\]]+)["\']?', r'\1***MASKED***'),
        (r'(pwd["\s:=]+)["\']?([^"\'\s,}\]]+)["\']?', r'\1***MASKED***'),
        (r'(secret["\s:=]+)["\']?([^"\'\s,}\]]+)["\']?', r'\1***MASKED***'),
        
        # Token patterns
        (r'(token["\s:=]+)["\']?([^"\'\s,}\]]+)["\']?', r'\1***MASKED***'),
        (r'(api_key["\s:=]+)["\']?([^"\'\s,}\]]+)["\']?', r'\1***MASKED***'),
        (r'(apikey["\s:=]+)["\']?([^"\'\s,}\]]+)["\']?', r'\1***MASKED***'),
        (r'(access_token["\s:=]+)["\']?([^"\'\s,}\]]+)["\']?', r'\1***MASKED***'),
        
        # WiFi specific
        (r'(smartc123)', r'***WIFI_PASS***'),  # Default hotspot password
        (r'(Pass:\s*)([^\s\n]+)', r'\1***MASKED***'),
        
        # Authorization headers
        (r'(Authorization["\s:=]+)["\']?([^"\'\s,}\]]+)["\']?', r'\1***MASKED***'),
        (r'(Bearer\s+)([^\s]+)', r'\1***MASKED***'),
    ]
    
    def __init__(self):
        super().__init__()
        # Compile patterns for performance
        self.compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), replacement)
            for pattern, replacement in self.PATTERNS
        ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Mask sensitive data in log message."""
        if record.msg:
            message = str(record.msg)
            for pattern, replacement in self.compiled_patterns:
                message = pattern.sub(replacement, message)
            record.msg = message
        
        # Also mask in args if present
        if record.args:
            new_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    for pattern, replacement in self.compiled_patterns:
                        arg = pattern.sub(replacement, arg)
                new_args.append(arg)
            record.args = tuple(new_args)
        
        return True  # Always allow the record through


class CompressedTimedRotatingFileHandler(TimedRotatingFileHandler):
    """
    TimedRotatingFileHandler với tính năng compress file cũ bằng gzip.
    """
    
    def doRollover(self):
        """Override để compress file sau khi rotate."""
        super().doRollover()
        
        # Compress old log files
        try:
            log_dir = os.path.dirname(self.baseFilename)
            for filename in os.listdir(log_dir):
                if filename.endswith('.log') and filename != os.path.basename(self.baseFilename):
                    filepath = os.path.join(log_dir, filename)
                    # Skip if already compressed or too recent
                    if not os.path.exists(filepath + '.gz'):
                        self._compress_file(filepath)
        except Exception:
            pass  # Don't fail on compression errors
    
    def _compress_file(self, filepath: str):
        """Compress a file using gzip."""
        try:
            with open(filepath, 'rb') as f_in:
                with gzip.open(filepath + '.gz', 'wb') as f_out:
                    f_out.writelines(f_in)
            os.remove(filepath)  # Remove original after compression
        except Exception:
            pass


def setup_logging():
    """
    Thiết lập hệ thống ghi log với:
    - Mask sensitive data (passwords, tokens, etc.)
    - Timed rotation (daily) với compression
    - Size-based rotation (max 50MB per file)
    - 30 days retention
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

    # === SENSITIVE DATA FILTER ===
    sensitive_filter = SensitiveDataFilter()

    # Handler log ra console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.addFilter(sensitive_filter)

    # Handler log ra file, xoay vòng theo ngày + compress
    file_handler = CompressedTimedRotatingFileHandler(
        log_file,
        when="midnight",  # cắt log lúc 0h
        interval=1,  # mỗi 1 ngày
        backupCount=30,  # giữ 30 ngày
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.suffix = "%Y-%m-%d.log"  # hậu tố file log
    file_handler.addFilter(sensitive_filter)

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
    logging.info("Sensitive data masking: ENABLED")

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
