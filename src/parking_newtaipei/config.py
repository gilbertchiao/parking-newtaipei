"""設定管理模組

集中管理所有路徑與設定，載入 .env 環境變數。
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# 載入 .env 檔案
load_dotenv()

# 專案根目錄（config.py 位於 src/parking_newtaipei/，往上 3 層即為專案根目錄）
PROJECT_ROOT = Path(__file__).parent.parent.parent

# 資料目錄
DATA_DIR = PROJECT_ROOT / "data"
DB_DIR = DATA_DIR / "db"
AVAILABILITY_DB_DIR = Path(
    os.getenv("AVAILABILITY_DB_DIR", str(DATA_DIR / "availability"))
)  # 即時車位資料庫（每月一個檔案）
RESPONSES_DIR = DATA_DIR / "responses"

# 日誌目錄
LOGS_DIR = PROJECT_ROOT / "logs"

# 環境變數設定
API_BASE_URL = os.getenv("API_BASE_URL", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
DB_PATH = Path(os.getenv("DB_PATH", str(DB_DIR / "parking.db")))
RESPONSES_PATH = Path(os.getenv("RESPONSES_PATH", str(RESPONSES_DIR)))

# 日誌設定
LOG_FILE = LOGS_DIR / "app.log"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 5


def ensure_directories() -> None:
    """確保所有必要目錄存在"""
    for directory in [DB_DIR, AVAILABILITY_DB_DIR, RESPONSES_DIR, LOGS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def get_config_summary() -> dict:
    """取得設定摘要，用於除錯"""
    return {
        "project_root": str(PROJECT_ROOT),
        "api_base_url": API_BASE_URL or "(未設定)",
        "log_level": LOG_LEVEL,
        "db_path": str(DB_PATH),
        "availability_db_dir": str(AVAILABILITY_DB_DIR),
        "responses_path": str(RESPONSES_PATH),
        "log_file": str(LOG_FILE),
    }
