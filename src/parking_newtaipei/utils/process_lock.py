"""進程鎖工具

使用 fcntl file lock 防止同一命令重複執行。
"""

import fcntl
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator


class ProcessLockAcquireError(Exception):
    """無法取得進程鎖的例外

    當另一個進程已持有鎖時拋出。
    """

    pass


class ProcessLock:
    """進程鎖

    使用 fcntl.flock() 實作排他鎖，確保同一命令不會重複執行。
    當進程結束（正常結束、crash、kill -9）時，鎖會自動釋放。

    使用方式：
        lock = ProcessLock("sync-availability")
        try:
            with lock.acquire():
                # 執行同步邏輯
                ...
        except ProcessLockAcquireError:
            print("已有進程正在執行")
    """

    def __init__(self, name: str, lock_dir: str = "/tmp") -> None:
        """初始化進程鎖

        Args:
            name: 鎖名稱，用於生成鎖檔案路徑
            lock_dir: 鎖檔案目錄，預設為 /tmp
        """
        self.name = name
        self.lock_path = Path(lock_dir) / f"parking_newtaipei_{name}.lock"
        self._lock_file = None

    @contextmanager
    def acquire(self) -> Generator[None, None, None]:
        """取得鎖

        使用 context manager 確保鎖在離開時釋放。

        Raises:
            ProcessLockAcquireError: 無法取得鎖（另一個進程已持有）

        Yields:
            None
        """
        # 開啟或建立鎖檔案
        self._lock_file = open(self.lock_path, "w")

        try:
            # 嘗試取得排他鎖（非阻塞）
            fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (IOError, OSError):
            self._lock_file.close()
            self._lock_file = None
            raise ProcessLockAcquireError(
                f"無法取得鎖 '{self.name}'：另一個進程正在執行"
            )

        try:
            # 寫入 PID 供除錯
            self._lock_file.write(str(os.getpid()))
            self._lock_file.flush()
            yield
        finally:
            # 釋放鎖並關閉檔案
            fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)
            self._lock_file.close()
            self._lock_file = None
