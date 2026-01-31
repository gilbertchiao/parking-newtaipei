"""進程鎖測試"""

import multiprocessing
import tempfile
import time
from pathlib import Path

import pytest

from parking_newtaipei.utils.process_lock import ProcessLock, ProcessLockAcquireError


class TestProcessLock:
    """ProcessLock 測試"""

    def test_acquire_and_release(self, tmp_path: Path) -> None:
        """測試取得與釋放鎖"""
        lock = ProcessLock("test", lock_dir=str(tmp_path))

        # 取得鎖
        with lock.acquire():
            # 鎖檔案應存在
            assert lock.lock_path.exists()

            # 檔案內容應為 PID
            content = lock.lock_path.read_text()
            assert content.isdigit()

    def test_cannot_acquire_twice(self, tmp_path: Path) -> None:
        """測試無法同時取得兩次相同的鎖"""
        lock1 = ProcessLock("test", lock_dir=str(tmp_path))
        lock2 = ProcessLock("test", lock_dir=str(tmp_path))

        with lock1.acquire():
            # 第二個鎖應無法取得
            with pytest.raises(ProcessLockAcquireError):
                with lock2.acquire():
                    pass

    def test_different_names_can_coexist(self, tmp_path: Path) -> None:
        """測試不同名稱的鎖可共存"""
        lock1 = ProcessLock("test1", lock_dir=str(tmp_path))
        lock2 = ProcessLock("test2", lock_dir=str(tmp_path))

        with lock1.acquire():
            # 不同名稱的鎖應可同時取得
            with lock2.acquire():
                assert lock1.lock_path.exists()
                assert lock2.lock_path.exists()

    def test_lock_released_after_context_exit(self, tmp_path: Path) -> None:
        """測試離開 context 後鎖被釋放"""
        lock1 = ProcessLock("test", lock_dir=str(tmp_path))
        lock2 = ProcessLock("test", lock_dir=str(tmp_path))

        # 取得並釋放第一個鎖
        with lock1.acquire():
            pass

        # 現在應可取得第二個鎖
        with lock2.acquire():
            pass

    def test_lock_released_on_exception(self, tmp_path: Path) -> None:
        """測試發生例外時鎖仍會被釋放"""
        lock1 = ProcessLock("test", lock_dir=str(tmp_path))
        lock2 = ProcessLock("test", lock_dir=str(tmp_path))

        # 在持有鎖時拋出例外
        with pytest.raises(ValueError):
            with lock1.acquire():
                raise ValueError("測試例外")

        # 例外後應可取得鎖
        with lock2.acquire():
            pass


def _hold_lock_subprocess(lock_dir: str, name: str, ready_event, done_event) -> None:
    """子進程持有鎖的輔助函數"""
    lock = ProcessLock(name, lock_dir=lock_dir)
    with lock.acquire():
        ready_event.set()  # 通知主進程鎖已取得
        done_event.wait()  # 等待主進程發出結束信號


class TestProcessLockMultiprocess:
    """跨進程的 ProcessLock 測試"""

    def test_cross_process_lock(self, tmp_path: Path) -> None:
        """測試跨進程的鎖互斥"""
        ready_event = multiprocessing.Event()
        done_event = multiprocessing.Event()

        # 啟動子進程持有鎖
        process = multiprocessing.Process(
            target=_hold_lock_subprocess,
            args=(str(tmp_path), "test", ready_event, done_event),
        )
        process.start()

        try:
            # 等待子進程取得鎖
            ready_event.wait(timeout=5)

            # 主進程嘗試取得相同的鎖應失敗
            lock = ProcessLock("test", lock_dir=str(tmp_path))
            with pytest.raises(ProcessLockAcquireError):
                with lock.acquire():
                    pass
        finally:
            # 通知子進程結束
            done_event.set()
            process.join(timeout=5)

    def test_lock_available_after_process_ends(self, tmp_path: Path) -> None:
        """測試進程結束後鎖自動釋放"""
        ready_event = multiprocessing.Event()
        done_event = multiprocessing.Event()

        # 啟動子進程持有鎖
        process = multiprocessing.Process(
            target=_hold_lock_subprocess,
            args=(str(tmp_path), "test", ready_event, done_event),
        )
        process.start()

        # 等待子進程取得鎖
        ready_event.wait(timeout=5)

        # 通知子進程結束並等待
        done_event.set()
        process.join(timeout=5)

        # 子進程結束後，應可取得鎖
        lock = ProcessLock("test", lock_dir=str(tmp_path))
        with lock.acquire():
            pass
