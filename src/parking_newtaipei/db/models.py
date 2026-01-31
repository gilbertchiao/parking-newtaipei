"""資料模型模組

定義停車場資料表結構與操作。
"""

from datetime import datetime

from parking_newtaipei.db.connection import DatabaseConnection
from parking_newtaipei.utils.logger import get_logger

# 停車場資料表 SQL
CREATE_PARKING_LOT_TABLE = """
CREATE TABLE IF NOT EXISTS parking_lots (
    id TEXT PRIMARY KEY,
    area TEXT,
    name TEXT,
    type TEXT,
    summary TEXT,
    address TEXT,
    tel TEXT,
    pay_ex TEXT,
    service_time TEXT,
    tw97x REAL,
    tw97y REAL,
    total_car INTEGER,
    total_motor INTEGER,
    total_bike INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT DEFAULT NULL
)
"""

# 建立索引
CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_parking_lots_area ON parking_lots(area)",
    "CREATE INDEX IF NOT EXISTS idx_parking_lots_deleted_at ON parking_lots(deleted_at)",
]


class ParkingLotRepository:
    """停車場資料存取類別"""

    def __init__(self, db: DatabaseConnection):
        """初始化停車場資料存取

        Args:
            db: 資料庫連線物件
        """
        self.db = db
        self.logger = get_logger()

    def init_tables(self) -> None:
        """初始化資料表"""
        self.db.execute(CREATE_PARKING_LOT_TABLE)
        for index_sql in CREATE_INDEXES:
            self.db.execute(index_sql)
        self.logger.info("停車場資料表初始化完成")

    def upsert(self, data: dict) -> tuple[str, bool]:
        """新增或更新停車場資料

        Args:
            data: 停車場資料字典，需包含 id 欄位

        Returns:
            (id, is_new) - 停車場 ID 與是否為新增
        """
        parking_id = data["id"]
        now = datetime.now().isoformat()

        # 檢查是否存在
        existing = self.db.fetch_one(
            "SELECT id, deleted_at FROM parking_lots WHERE id = ?",
            (parking_id,),
        )

        if existing is None:
            # 新增
            self.db.execute(
                """
                INSERT INTO parking_lots (
                    id, area, name, type, summary, address, tel,
                    pay_ex, service_time, tw97x, tw97y,
                    total_car, total_motor, total_bike,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    parking_id,
                    data.get("area", ""),
                    data.get("name", ""),
                    data.get("type", ""),
                    data.get("summary", ""),
                    data.get("address", ""),
                    data.get("tel", ""),
                    data.get("pay_ex", ""),
                    data.get("service_time", ""),
                    data.get("tw97x"),
                    data.get("tw97y"),
                    data.get("total_car"),
                    data.get("total_motor"),
                    data.get("total_bike"),
                    now,
                    now,
                ),
            )
            return parking_id, True
        else:
            # 更新（包含恢復已刪除的資料）
            self.db.execute(
                """
                UPDATE parking_lots SET
                    area = ?, name = ?, type = ?, summary = ?, address = ?, tel = ?,
                    pay_ex = ?, service_time = ?, tw97x = ?, tw97y = ?,
                    total_car = ?, total_motor = ?, total_bike = ?,
                    updated_at = ?, deleted_at = NULL
                WHERE id = ?
                """,
                (
                    data.get("area", ""),
                    data.get("name", ""),
                    data.get("type", ""),
                    data.get("summary", ""),
                    data.get("address", ""),
                    data.get("tel", ""),
                    data.get("pay_ex", ""),
                    data.get("service_time", ""),
                    data.get("tw97x"),
                    data.get("tw97y"),
                    data.get("total_car"),
                    data.get("total_motor"),
                    data.get("total_bike"),
                    now,
                    parking_id,
                ),
            )
            return parking_id, False

    def mark_deleted(self, parking_ids: set[str]) -> int:
        """標記停車場為已刪除

        只標記尚未被刪除的資料，已刪除的不更新刪除時間。

        Args:
            parking_ids: 要標記刪除的停車場 ID 集合

        Returns:
            實際標記刪除的數量
        """
        if not parking_ids:
            return 0

        now = datetime.now().isoformat()
        count = 0

        for parking_id in parking_ids:
            # 只更新 deleted_at 為 NULL 的資料
            with self.db.get_cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE parking_lots
                    SET deleted_at = ?
                    WHERE id = ? AND deleted_at IS NULL
                    """,
                    (now, parking_id),
                )
                count += cursor.rowcount

        return count

    def get_all_active_ids(self) -> set[str]:
        """取得所有未刪除的停車場 ID

        Returns:
            停車場 ID 集合
        """
        rows = self.db.fetch_all(
            "SELECT id FROM parking_lots WHERE deleted_at IS NULL"
        )
        return {row["id"] for row in rows}

    def get_stats(self) -> dict:
        """取得統計資訊

        Returns:
            統計資訊字典
        """
        total = self.db.fetch_one("SELECT COUNT(*) as count FROM parking_lots")
        active = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM parking_lots WHERE deleted_at IS NULL"
        )
        deleted = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM parking_lots WHERE deleted_at IS NOT NULL"
        )

        return {
            "total": total["count"] if total else 0,
            "active": active["count"] if active else 0,
            "deleted": deleted["count"] if deleted else 0,
        }
