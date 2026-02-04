"""即時車位資料同步模組

從新北市開放資料平台下載即時剩餘車位數並寫入資料庫。
"""

import csv
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

from parking_newtaipei.api.client import APIClient
from parking_newtaipei.config import HEALTHCHECK_AVAILABILITY_URL
from parking_newtaipei.db.availability import AvailabilityRepository
from parking_newtaipei.utils.healthcheck import ping_healthcheck
from parking_newtaipei.utils.logger import get_logger

# 新北市公有路外停車場即時賸餘車位數 API
AVAILABILITY_API_URL = (
    "https://data.ntpc.gov.tw/api/datasets/"
    "e09b35a5-a738-48cc-b0f5-570b67ad9c78/csv/file"
)

# 無效資料的標記值
INVALID_VALUE = -9


@dataclass
class AvailabilitySyncResult:
    """同步結果"""

    inserted: int = 0
    skipped_invalid: int = 0
    total_downloaded: int = 0
    errors: list[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class AvailabilitySync:
    """即時車位資料同步器"""

    def __init__(
        self,
        db_dir: Path,
        api_client: APIClient,
    ):
        """初始化同步器

        Args:
            db_dir: 資料庫目錄
            api_client: API 客戶端
        """
        self.db_dir = db_dir
        self.api_client = api_client
        self.repo = AvailabilityRepository(db_dir)
        self.logger = get_logger()

    def _parse_csv(self, csv_content: str) -> list[dict]:
        """解析 CSV 內容

        Args:
            csv_content: CSV 字串內容

        Returns:
            解析後的有效資料列表
        """
        # 移除 BOM
        if csv_content.startswith("\ufeff"):
            csv_content = csv_content[1:]

        reader = csv.DictReader(StringIO(csv_content))
        records = []
        skipped = 0

        for row in reader:
            parking_id = row.get("ID", "").strip()
            available_car_str = row.get("AVAILABLECAR", "").strip()

            if not parking_id or not available_car_str:
                continue

            try:
                available_car = int(available_car_str)
            except ValueError:
                continue

            # 跳過無效資料（-9 表示無效）
            if available_car == INVALID_VALUE:
                skipped += 1
                continue

            records.append({
                "parking_id": parking_id,
                "available_car": available_car,
            })

        return records, skipped

    def download(self) -> str:
        """下載即時車位資料

        Returns:
            CSV 內容字串
        """
        self.logger.info(f"正在下載即時車位資料: {AVAILABILITY_API_URL}")

        response = self.api_client.get(AVAILABILITY_API_URL)
        response.raise_for_status()

        content = response.text
        self.logger.info(f"下載完成，資料大小: {len(content)} bytes")

        return content

    def sync(self) -> AvailabilitySyncResult:
        """執行同步作業

        Returns:
            同步結果
        """
        result = AvailabilitySyncResult()

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

        # 解析 CSV
        records, skipped = self._parse_csv(csv_content)
        result.total_downloaded = len(records) + skipped
        result.skipped_invalid = skipped

        # 批次寫入
        if records:
            try:
                inserted = self.repo.insert_batch(records)
                result.inserted = inserted
            except Exception as e:
                error_msg = f"寫入失敗: {e}"
                self.logger.error(error_msg)
                result.errors.append(error_msg)
                return result

        # 記錄結果
        self.logger.info(
            f"同步完成 - 寫入: {result.inserted}, "
            f"跳過無效: {result.skipped_invalid}, "
            f"總下載: {result.total_downloaded}"
        )

        if result.errors:
            self.logger.warning(f"同步過程中發生 {len(result.errors)} 個錯誤")
        else:
            # 同步成功，發送 healthcheck 通報
            ping_healthcheck(HEALTHCHECK_AVAILABILITY_URL, "即時車位資料同步")

        return result
