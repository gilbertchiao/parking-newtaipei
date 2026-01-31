"""日誌設定模組

提供 RotatingFileHandler 和 console 輸出的日誌設定。
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# 日誌格式
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 模組層級的 logger 快取
_loggers: dict[str, logging.Logger] = {}


def setup_logger(
    name: str = "parking_newtaipei",
    level: str = "INFO",
    log_file: Path | None = None,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> logging.Logger:
    """設定並回傳 logger

    Args:
        name: Logger 名稱
        level: 日誌等級（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        log_file: 日誌檔案路徑，若為 None 則只輸出到 console
        max_bytes: 單一日誌檔案最大大小（預設 10MB）
        backup_count: 保留的日誌檔案數量（預設 5 個）

    Returns:
        設定好的 Logger 物件
    """
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()

    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler（如果有指定）
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # 避免重複輸出
    logger.propagate = False

    _loggers[name] = logger
    return logger


def get_logger(name: str = "parking_newtaipei") -> logging.Logger:
    """取得已存在的 logger，若不存在則建立預設 logger

    Args:
        name: Logger 名稱

    Returns:
        Logger 物件
    """
    if name in _loggers:
        return _loggers[name]

    # 延遲載入 config 以避免循環引用
    from parking_newtaipei.config import LOG_FILE, LOG_LEVEL, LOG_MAX_BYTES, LOG_BACKUP_COUNT

    return setup_logger(
        name=name,
        level=LOG_LEVEL,
        log_file=LOG_FILE,
        max_bytes=LOG_MAX_BYTES,
        backup_count=LOG_BACKUP_COUNT,
    )
