"""健康檢查通報模組

成功執行任務後，ping 指定的 URL 進行通報。
"""

import httpx

from parking_newtaipei.utils.logger import get_logger


def ping_healthcheck(url: str | None, task_name: str = "") -> bool:
    """Ping healthcheck URL 通報執行成功

    Args:
        url: 要 ping 的 URL，如果為 None 或空字串則跳過
        task_name: 任務名稱，用於日誌記錄

    Returns:
        True 表示成功或跳過，False 表示 ping 失敗
    """
    logger = get_logger()

    if not url:
        logger.debug(f"Healthcheck URL 未設定，跳過通報 ({task_name})")
        return True

    try:
        # 使用 httpx 發送 GET 請求，timeout 10 秒
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url)
            response.raise_for_status()

        logger.info(f"Healthcheck 通報成功: {task_name} -> {url}")
        return True

    except httpx.TimeoutException:
        logger.warning(f"Healthcheck 通報逾時: {task_name} -> {url}")
        return False

    except httpx.HTTPStatusError as e:
        logger.warning(
            f"Healthcheck 通報失敗 (HTTP {e.response.status_code}): "
            f"{task_name} -> {url}"
        )
        return False

    except Exception as e:
        logger.warning(f"Healthcheck 通報失敗: {task_name} -> {url}, 錯誤: {e}")
        return False
