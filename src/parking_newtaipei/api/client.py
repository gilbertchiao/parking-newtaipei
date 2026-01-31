"""通用 API 客戶端

自動保存每次 API 呼叫的 request 和 response。
"""

from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx

from parking_newtaipei.utils.logger import get_logger
from parking_newtaipei.utils.storage import save_response


class APIClient:
    """通用 HTTP API 客戶端

    自動記錄所有 request/response 到指定目錄。
    """

    def __init__(
        self,
        base_url: str,
        responses_dir: Path,
        timeout: float = 30.0,
        auto_save: bool = True,
    ):
        """初始化 API 客戶端

        Args:
            base_url: API 基底 URL
            responses_dir: response 備份目錄
            timeout: 請求逾時時間（秒）
            auto_save: 是否自動儲存 request/response
        """
        self.base_url = base_url.rstrip("/")
        self.responses_dir = responses_dir
        self.timeout = timeout
        self.auto_save = auto_save
        self.logger = get_logger()

        self._client = httpx.Client(timeout=timeout)

    def __enter__(self) -> "APIClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        """關閉 HTTP 客戶端"""
        self._client.close()

    def _build_url(self, endpoint: str) -> str:
        """建立完整 URL

        Args:
            endpoint: API endpoint（可以是相對或絕對路徑）

        Returns:
            完整的 URL
        """
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint
        return urljoin(self.base_url + "/", endpoint.lstrip("/"))

    def _save_exchange(
        self,
        endpoint: str,
        method: str,
        request_data: dict[str, Any] | None,
        response: httpx.Response,
        timestamp: datetime,
    ) -> Path | None:
        """儲存 request/response 交換記錄

        Args:
            endpoint: API endpoint
            method: HTTP 方法
            request_data: 請求資料
            response: HTTP response 物件
            timestamp: 請求時間

        Returns:
            儲存的檔案路徑，若未儲存則為 None
        """
        if not self.auto_save:
            return None

        # 嘗試解析 response body 為 JSON
        try:
            response_body = response.json()
        except (ValueError, httpx.DecodingError):
            response_body = response.text

        exchange_data = {
            "timestamp": timestamp.isoformat(),
            "request": {
                "method": method,
                "url": str(response.request.url),
                "endpoint": endpoint,
                "headers": dict(response.request.headers),
                "body": request_data,
            },
            "response": {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response_body,
            },
        }

        filepath = save_response(
            data=exchange_data,
            output_dir=self.responses_dir,
            endpoint=endpoint,
            timestamp=timestamp,
        )

        self.logger.debug(f"已儲存 API 交換記錄: {filepath}")
        return filepath

    def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """發送 GET 請求

        Args:
            endpoint: API endpoint
            params: 查詢參數
            headers: 額外的 HTTP headers

        Returns:
            HTTP response 物件
        """
        timestamp = datetime.now()
        url = self._build_url(endpoint)

        self.logger.info(f"GET {url}")

        response = self._client.get(url, params=params, headers=headers)

        self._save_exchange(
            endpoint=endpoint,
            method="GET",
            request_data={"params": params},
            response=response,
            timestamp=timestamp,
        )

        return response

    def post(
        self,
        endpoint: str,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """發送 POST 請求

        Args:
            endpoint: API endpoint
            json: JSON 請求體
            data: Form data 請求體
            headers: 額外的 HTTP headers

        Returns:
            HTTP response 物件
        """
        timestamp = datetime.now()
        url = self._build_url(endpoint)

        self.logger.info(f"POST {url}")

        response = self._client.post(url, json=json, data=data, headers=headers)

        self._save_exchange(
            endpoint=endpoint,
            method="POST",
            request_data={"json": json, "data": data},
            response=response,
            timestamp=timestamp,
        )

        return response

    def request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """發送自訂 HTTP 請求

        Args:
            method: HTTP 方法
            endpoint: API endpoint
            **kwargs: 傳遞給 httpx.Client.request 的其他參數

        Returns:
            HTTP response 物件
        """
        timestamp = datetime.now()
        url = self._build_url(endpoint)

        self.logger.info(f"{method.upper()} {url}")

        response = self._client.request(method, url, **kwargs)

        self._save_exchange(
            endpoint=endpoint,
            method=method.upper(),
            request_data=kwargs,
            response=response,
            timestamp=timestamp,
        )

        return response
