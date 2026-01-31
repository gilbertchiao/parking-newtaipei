"""即時車位資料模組

處理每月輪替的 SQLite 資料庫檔案。
"""

from datetime import datetime
from pathlib import Path

from parking_newtaipei.db.connection import DatabaseConnection
from parking_newtaipei.utils.logger import get_logger
from parking_newtaipei.utils.time import now_iso

# 即時車位資料表 SQL
CREATE_AVAILABILITY_TABLE = """
CREATE TABLE IF NOT EXISTS availability (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parking_id TEXT NOT NULL,
    available_car INTEGER NOT NULL,
    recorded_at TEXT NOT NULL
)
"""

# 建立索引
CREATE_AVAILABILITY_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_availability_parking_id ON availability(parking_id)",
    "CREATE INDEX IF NOT EXISTS idx_availability_recorded_at ON availability(recorded_at)",
]


def get_monthly_db_path(base_dir: Path, year: int | None = None, month: int | None = None) -> Path:
    """取得月份對應的資料庫檔案路徑

    Args:
        base_dir: 資料庫目錄
        year: 年份，預設為當前年份
        month: 月份，預設為當前月份

    Returns:
        資料庫檔案路徑，格式：availability_YYYYMM.db
    """
    now = datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month

    filename = f"availability_{year:04d}{month:02d}.db"
    return base_dir / filename


class AvailabilityRepository:
    """即時車位資料存取類別

    使用每月輪替的資料庫檔案。
    """

    def __init__(self, db_dir: Path):
        """初始化即時車位資料存取

        Args:
            db_dir: 資料庫目錄
        """
        self.db_dir = db_dir
        self.logger = get_logger()

        # 確保目錄存在
        self.db_dir.mkdir(parents=True, exist_ok=True)

    def _get_current_db(self) -> DatabaseConnection:
        """取得當前月份的資料庫連線

        Returns:
            資料庫連線物件
        """
        db_path = get_monthly_db_path(self.db_dir)
        return DatabaseConnection(db_path)

    def init_tables(self) -> None:
        """初始化當前月份的資料表"""
        db = self._get_current_db()
        db.execute(CREATE_AVAILABILITY_TABLE)
        for index_sql in CREATE_AVAILABILITY_INDEXES:
            db.execute(index_sql)
        self.logger.debug(f"即時車位資料表初始化完成: {get_monthly_db_path(self.db_dir)}")

    def insert_batch(self, records: list[dict]) -> int:
        """批次寫入即時車位資料

        Args:
            records: 資料列表，每筆包含 parking_id 和 available_car

        Returns:
            成功寫入的筆數
        """
        if not records:
            return 0

        db = self._get_current_db()
        now = now_iso()

        # 準備批次寫入資料
        params_list = [
            (record["parking_id"], record["available_car"], now)
            for record in records
        ]

        db.execute_many(
            """
            INSERT INTO availability (parking_id, available_car, recorded_at)
            VALUES (?, ?, ?)
            """,
            params_list,
        )

        return len(params_list)

    def get_stats(self, year: int | None = None, month: int | None = None) -> dict:
        """取得統計資訊

        Args:
            year: 年份，預設為當前年份
            month: 月份，預設為當前月份

        Returns:
            統計資訊字典
        """
        db_path = get_monthly_db_path(self.db_dir, year, month)

        if not db_path.exists():
            return {
                "db_file": db_path.name,
                "exists": False,
                "total_records": 0,
                "unique_parking_ids": 0,
                "first_record": None,
                "last_record": None,
            }

        db = DatabaseConnection(db_path)

        total = db.fetch_one("SELECT COUNT(*) as count FROM availability")
        unique = db.fetch_one("SELECT COUNT(DISTINCT parking_id) as count FROM availability")
        first = db.fetch_one("SELECT MIN(recorded_at) as ts FROM availability")
        last = db.fetch_one("SELECT MAX(recorded_at) as ts FROM availability")

        return {
            "db_file": db_path.name,
            "exists": True,
            "total_records": total["count"] if total else 0,
            "unique_parking_ids": unique["count"] if unique else 0,
            "first_record": first["ts"] if first else None,
            "last_record": last["ts"] if last else None,
        }

    def list_db_files(self) -> list[Path]:
        """列出所有月份的資料庫檔案

        Returns:
            資料庫檔案路徑列表（按時間排序）
        """
        files = list(self.db_dir.glob("availability_*.db"))
        return sorted(files)
