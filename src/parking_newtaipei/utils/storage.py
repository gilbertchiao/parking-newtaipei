"""檔案儲存模組

提供 JSON 序列化與 gzip 壓縮儲存功能。
"""

import gzip
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def generate_filename(endpoint: str, timestamp: datetime | None = None) -> str:
    """產生唯一檔名

    格式：{timestamp}_{endpoint_hash}.json.gz

    Args:
        endpoint: API endpoint 路徑
        timestamp: 時間戳記，預設為當前時間

    Returns:
        產生的檔名
    """
    if timestamp is None:
        timestamp = datetime.now()

    timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
    endpoint_hash = hashlib.md5(endpoint.encode()).hexdigest()[:8]

    return f"{timestamp_str}_{endpoint_hash}.json.gz"


def save_response(
    data: dict[str, Any],
    output_dir: Path,
    endpoint: str,
    timestamp: datetime | None = None,
) -> Path:
    """儲存 API response 為 gzip 壓縮的 JSON 檔案

    Args:
        data: 要儲存的資料（包含 request 和 response）
        output_dir: 輸出目錄
        endpoint: API endpoint（用於產生檔名）
        timestamp: 時間戳記，預設為當前時間

    Returns:
        儲存的檔案路徑
    """
    if timestamp is None:
        timestamp = datetime.now()

    # 建立 YYYYMM 子目錄
    month_subdir = timestamp.strftime("%Y%m")
    actual_output_dir = output_dir / month_subdir
    actual_output_dir.mkdir(parents=True, exist_ok=True)

    filename = generate_filename(endpoint, timestamp)
    filepath = actual_output_dir / filename

    json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")

    with gzip.open(filepath, "wb") as f:
        f.write(json_bytes)

    return filepath


def load_response(filepath: Path) -> dict[str, Any]:
    """載入 gzip 壓縮的 JSON 檔案

    Args:
        filepath: 檔案路徑

    Returns:
        解析後的資料字典
    """
    with gzip.open(filepath, "rb") as f:
        json_bytes = f.read()

    return json.loads(json_bytes.decode("utf-8"))


def list_responses(
    responses_dir: Path,
    pattern: str = "*.json.gz",
) -> list[Path]:
    """列出所有備份檔案

    Args:
        responses_dir: responses 目錄路徑
        pattern: 檔案 glob 模式

    Returns:
        符合條件的檔案路徑列表（按修改時間排序，最新的在前）
    """
    if not responses_dir.exists():
        return []

    # 搜尋 YYYYMM 子目錄中的檔案
    files = list(responses_dir.glob(f"*/{pattern}"))
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)
