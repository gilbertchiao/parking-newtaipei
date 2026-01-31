"""日誌設定模組

提供 TimedRotatingFileHandler（每日輪詢）和 console 輸出的日誌設定。
"""

import logging
import sys
from logging.handlers import TimedRotatingFileHandler
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
    backup_days: int = 30,
) -> logging.Logger:
    """設定並回傳 logger

    Args:
        name: Logger 名稱
        level: 日誌等級（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        log_file: 日誌檔案路徑，若為 None 則只輸出到 console
        backup_days: 日誌保留天數（預設 30 天）

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
    # 使用 TimedRotatingFileHandler 每日輪詢
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = TimedRotatingFileHandler(
            log_file,
            when="midnight",  # 每天午夜輪詢
            interval=1,
            backupCount=backup_days,
            encoding="utf-8",
        )
        # 設定備份檔案後綴格式：app.log.2026-02-01
        file_handler.suffix = "%Y-%m-%d"
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
    from parking_newtaipei.config import LOG_BACKUP_DAYS, LOG_FILE, LOG_LEVEL

    return setup_logger(
        name=name,
        level=LOG_LEVEL,
        log_file=LOG_FILE,
        backup_days=LOG_BACKUP_DAYS,
    )
