"""儲存模組測試"""

from datetime import datetime
from pathlib import Path

from parking_newtaipei.utils.storage import (
    generate_filename,
    list_responses,
    load_response,
    save_response,
)


class TestGenerateFilename:
    """generate_filename 測試"""

    def test_format(self) -> None:
        """測試檔名格式"""
        timestamp = datetime(2026, 2, 4, 10, 30, 45)
        filename = generate_filename("/api/test", timestamp)

        assert filename.startswith("20260204_103045_")
        assert filename.endswith(".json.gz")

    def test_consistent_hash(self) -> None:
        """測試相同 endpoint 產生相同 hash"""
        timestamp = datetime(2026, 2, 4, 10, 30, 45)
        filename1 = generate_filename("/api/test", timestamp)
        filename2 = generate_filename("/api/test", timestamp)

        assert filename1 == filename2

    def test_different_hash_for_different_endpoint(self) -> None:
        """測試不同 endpoint 產生不同 hash"""
        timestamp = datetime(2026, 2, 4, 10, 30, 45)
        filename1 = generate_filename("/api/test1", timestamp)
        filename2 = generate_filename("/api/test2", timestamp)

        assert filename1 != filename2


class TestSaveResponse:
    """save_response 測試"""

    def test_save_to_yyyymm_subdir(self, tmp_path: Path) -> None:
        """測試儲存到 YYYYMM 子目錄"""
        timestamp = datetime(2026, 2, 4, 10, 30, 45)
        data = {"test": "data"}

        filepath = save_response(
            data=data,
            output_dir=tmp_path,
            endpoint="/api/test",
            timestamp=timestamp,
        )

        # 檢查路徑格式
        assert filepath.parent.name == "202602"
        assert filepath.parent.parent == tmp_path
        assert filepath.exists()

    def test_different_months_different_dirs(self, tmp_path: Path) -> None:
        """測試不同月份儲存到不同目錄"""
        data = {"test": "data"}

        filepath1 = save_response(
            data=data,
            output_dir=tmp_path,
            endpoint="/api/test",
            timestamp=datetime(2026, 1, 15),
        )
        filepath2 = save_response(
            data=data,
            output_dir=tmp_path,
            endpoint="/api/test",
            timestamp=datetime(2026, 2, 15),
        )

        assert filepath1.parent.name == "202601"
        assert filepath2.parent.name == "202602"

    def test_saved_content_can_be_loaded(self, tmp_path: Path) -> None:
        """測試儲存的內容可以載入"""
        timestamp = datetime(2026, 2, 4, 10, 30, 45)
        data = {"key": "value", "number": 123, "chinese": "中文測試"}

        filepath = save_response(
            data=data,
            output_dir=tmp_path,
            endpoint="/api/test",
            timestamp=timestamp,
        )

        loaded = load_response(filepath)
        assert loaded == data


class TestListResponses:
    """list_responses 測試"""

    def test_list_files_in_subdirs(self, tmp_path: Path) -> None:
        """測試列出子目錄中的檔案"""
        data = {"test": "data"}

        # 建立兩個不同月份的檔案
        save_response(
            data=data,
            output_dir=tmp_path,
            endpoint="/api/test1",
            timestamp=datetime(2026, 1, 15, 10, 0, 0),
        )
        save_response(
            data=data,
            output_dir=tmp_path,
            endpoint="/api/test2",
            timestamp=datetime(2026, 2, 15, 10, 0, 0),
        )

        files = list_responses(tmp_path)

        assert len(files) == 2
        # 確認兩個檔案來自不同的子目錄
        parent_names = {f.parent.name for f in files}
        assert parent_names == {"202601", "202602"}

    def test_empty_dir_returns_empty_list(self, tmp_path: Path) -> None:
        """測試空目錄回傳空列表"""
        files = list_responses(tmp_path)
        assert files == []

    def test_nonexistent_dir_returns_empty_list(self, tmp_path: Path) -> None:
        """測試不存在目錄回傳空列表"""
        files = list_responses(tmp_path / "nonexistent")
        assert files == []
