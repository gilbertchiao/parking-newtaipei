"""時間工具模組

提供統一的時間處理函數，確保時區一致性。
"""

from datetime import datetime


def now_iso() -> str:
    """取得當前時間的 ISO 8601 格式字串（含時區）

    使用系統本地時區，例如：2026-02-01T01:04:08.123456+08:00

    Returns:
        ISO 8601 格式的時間字串（含時區）
    """
    return datetime.now().astimezone().isoformat()
