"""SQLite 連線管理模組"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from parking_newtaipei.utils.logger import get_logger


class DatabaseConnection:
    """SQLite 資料庫連線管理器"""

    def __init__(self, db_path: Path):
        """初始化資料庫連線管理器

        Args:
            db_path: 資料庫檔案路徑
        """
        self.db_path = db_path
        self.logger = get_logger()

        # 確保目錄存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """取得資料庫連線（context manager）

        Yields:
            SQLite 連線物件
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 讓查詢結果可以用欄位名稱存取

        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            self.logger.error(f"資料庫操作失敗: {e}")
            raise
        finally:
            conn.close()

    @contextmanager
    def get_cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        """取得資料庫 cursor（context manager）

        Yields:
            SQLite cursor 物件
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            yield cursor

    def execute(self, sql: str, params: tuple = ()) -> None:
        """執行 SQL 語句

        Args:
            sql: SQL 語句
            params: SQL 參數
        """
        with self.get_cursor() as cursor:
            cursor.execute(sql, params)

    def execute_many(self, sql: str, params_list: list[tuple]) -> None:
        """批次執行 SQL 語句

        Args:
            sql: SQL 語句
            params_list: SQL 參數列表
        """
        with self.get_cursor() as cursor:
            cursor.executemany(sql, params_list)

    def fetch_all(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        """查詢並回傳所有結果

        Args:
            sql: SQL 查詢語句
            params: SQL 參數

        Returns:
            查詢結果列表
        """
        with self.get_cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()

    def fetch_one(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        """查詢並回傳單一結果

        Args:
            sql: SQL 查詢語句
            params: SQL 參數

        Returns:
            查詢結果，若無結果則為 None
        """
        with self.get_cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()

    def table_exists(self, table_name: str) -> bool:
        """檢查資料表是否存在

        Args:
            table_name: 資料表名稱

        Returns:
            資料表是否存在
        """
        result = self.fetch_one(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        )
        return result is not None
