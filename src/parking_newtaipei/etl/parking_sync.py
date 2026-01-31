"""停車場資料同步模組

從新北市開放資料平台下載停車場資訊並同步至本地資料庫。
"""

import csv
from dataclasses import dataclass
from io import StringIO
from typing import Iterator

from parking_newtaipei.api.client import APIClient
from parking_newtaipei.db.connection import DatabaseConnection
from parking_newtaipei.db.models import ParkingLotRepository
from parking_newtaipei.utils.logger import get_logger

# 新北市路外公共停車場資訊 API
PARKING_LOT_API_URL = (
    "https://data.ntpc.gov.tw/api/datasets/"
    "b1464ef0-9c7c-4a6f-abf7-6bdf32847e68/csv/file"
)

# CSV 欄位對應
CSV_FIELD_MAPPING = {
    "ID": "id",
    "AREA": "area",
    "NAME": "name",
    "TYPE": "type",
    "SUMMARY": "summary",
    "ADDRESS": "address",
    "TEL": "tel",
    "PAYEX": "pay_ex",
    "SERVICETIME": "service_time",
    "TW97X": "tw97x",
    "TW97Y": "tw97y",
    "TOTALCAR": "total_car",
    "TOTALMOTOR": "total_motor",
    "TOTALBIKE": "total_bike",
}


@dataclass
class SyncResult:
    """同步結果"""

    inserted: int = 0
    updated: int = 0
    deleted: int = 0
    total_processed: int = 0
    errors: list[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class ParkingLotSync:
    """停車場資料同步器"""

    def __init__(
        self,
        db: DatabaseConnection,
        api_client: APIClient,
    ):
        """初始化同步器

        Args:
            db: 資料庫連線物件
            api_client: API 客戶端
        """
        self.db = db
        self.api_client = api_client
        self.repo = ParkingLotRepository(db)
        self.logger = get_logger()

    def _parse_csv(self, csv_content: str) -> Iterator[dict]:
        """解析 CSV 內容

        Args:
            csv_content: CSV 字串內容

        Yields:
            解析後的資料字典
        """
        # 移除 BOM（Byte Order Mark）
        if csv_content.startswith("\ufeff"):
            csv_content = csv_content[1:]

        reader = csv.DictReader(StringIO(csv_content))

        for row in reader:
            data = {}
            for csv_field, db_field in CSV_FIELD_MAPPING.items():
                value = row.get(csv_field, "").strip()

                # 數值欄位轉換
                if db_field in ("tw97x", "tw97y"):
                    data[db_field] = float(value) if value else None
                elif db_field in ("total_car", "total_motor", "total_bike"):
                    data[db_field] = int(value) if value else 0
                else:
                    data[db_field] = value

            # 確保有 ID
            if data.get("id"):
                yield data

    def download(self) -> str:
        """下載停車場資料

        Returns:
            CSV 內容字串
        """
        self.logger.info(f"正在下載停車場資料: {PARKING_LOT_API_URL}")

        response = self.api_client.get(PARKING_LOT_API_URL)
        response.raise_for_status()

        content = response.text
        self.logger.info(f"下載完成，資料大小: {len(content)} bytes")

        return content

    def sync(self) -> SyncResult:
        """執行同步作業

        Returns:
            同步結果
        """
        result = SyncResult()

        # 確保資料表存在
        self.repo.init_tables()

        # 下載資料
        try:
            csv_content = self.download()
        except Exception as e:
            error_msg = f"下載失敗: {e}"
            self.logger.error(error_msg)
            result.errors.append(error_msg)
            return result

        # 取得目前資料庫中所有有效的 ID
        existing_ids = self.repo.get_all_active_ids()
        downloaded_ids: set[str] = set()

        # 解析並更新資料
        for data in self._parse_csv(csv_content):
            try:
                parking_id, is_new = self.repo.upsert(data)
                downloaded_ids.add(parking_id)

                if is_new:
                    result.inserted += 1
                    self.logger.debug(f"新增停車場: {parking_id} - {data.get('name')}")
                else:
                    result.updated += 1
                    self.logger.debug(f"更新停車場: {parking_id} - {data.get('name')}")

                result.total_processed += 1

            except Exception as e:
                error_msg = f"處理資料失敗 (ID={data.get('id')}): {e}"
                self.logger.error(error_msg)
                result.errors.append(error_msg)

        # 標記已刪除的停車場（在資料庫中但不在下載資料中）
        ids_to_delete = existing_ids - downloaded_ids
        if ids_to_delete:
            deleted_count = self.repo.mark_deleted(ids_to_delete)
            result.deleted = deleted_count
            self.logger.info(f"標記 {deleted_count} 筆資料為已刪除")

        # 記錄結果
        self.logger.info(
            f"同步完成 - 新增: {result.inserted}, 更新: {result.updated}, "
            f"刪除: {result.deleted}, 總處理: {result.total_processed}"
        )

        if result.errors:
            self.logger.warning(f"同步過程中發生 {len(result.errors)} 個錯誤")

        return result
