"""CLI 進入點

支援 --help、sync-parking 等指令。
"""

import argparse
import sys

from parking_newtaipei import __version__
from parking_newtaipei.config import (
    DB_PATH,
    RESPONSES_PATH,
    ensure_directories,
    get_config_summary,
)
from parking_newtaipei.utils.logger import get_logger


def create_parser() -> argparse.ArgumentParser:
    """建立命令列參數解析器"""
    parser = argparse.ArgumentParser(
        prog="parking_newtaipei",
        description="新北市停車場資料擷取與分析工具",
    )

    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="啟用除錯模式，顯示詳細設定資訊",
    )

    # 子命令
    subparsers = parser.add_subparsers(dest="command", help="可用指令")

    # sync-parking 指令
    sync_parser = subparsers.add_parser(
        "sync-parking",
        help="同步路外公共停車場資料",
    )
    sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="測試模式，顯示設定但不實際執行",
    )

    # stats 指令
    subparsers.add_parser(
        "stats",
        help="顯示資料庫統計資訊",
    )

    return parser


def cmd_sync_parking(args: argparse.Namespace) -> int:
    """執行停車場資料同步

    Args:
        args: 命令列參數

    Returns:
        結束代碼（0 = 成功）
    """
    from parking_newtaipei.api.client import APIClient
    from parking_newtaipei.db.connection import DatabaseConnection
    from parking_newtaipei.etl.parking_sync import PARKING_LOT_API_URL, ParkingLotSync

    logger = get_logger()

    if args.dry_run:
        logger.info("=== Dry Run 模式 ===")
        logger.info(f"API URL: {PARKING_LOT_API_URL}")
        logger.info(f"資料庫路徑: {DB_PATH}")
        logger.info(f"Response 備份目錄: {RESPONSES_PATH}")
        logger.info("測試完成，未實際執行同步")
        return 0

    logger.info("開始同步停車場資料...")

    # 初始化元件
    db = DatabaseConnection(DB_PATH)
    api_client = APIClient(
        base_url="",  # 使用完整 URL，不需要 base_url
        responses_dir=RESPONSES_PATH,
        auto_save=True,
    )

    try:
        # 執行同步
        sync = ParkingLotSync(db=db, api_client=api_client)
        result = sync.sync()

        # 顯示結果
        logger.info("=== 同步結果 ===")
        logger.info(f"  新增: {result.inserted}")
        logger.info(f"  更新: {result.updated}")
        logger.info(f"  刪除: {result.deleted}")
        logger.info(f"  總處理: {result.total_processed}")

        if result.errors:
            logger.warning(f"  錯誤數: {len(result.errors)}")
            return 1

        return 0

    finally:
        api_client.close()


def cmd_stats(args: argparse.Namespace) -> int:
    """顯示資料庫統計資訊

    Args:
        args: 命令列參數

    Returns:
        結束代碼（0 = 成功）
    """
    from parking_newtaipei.db.connection import DatabaseConnection
    from parking_newtaipei.db.models import ParkingLotRepository

    logger = get_logger()

    if not DB_PATH.exists():
        logger.warning(f"資料庫不存在: {DB_PATH}")
        logger.info("請先執行 sync-parking 指令建立資料庫")
        return 0

    db = DatabaseConnection(DB_PATH)
    repo = ParkingLotRepository(db)

    stats = repo.get_stats()

    logger.info("=== 資料庫統計 ===")
    logger.info(f"  總筆數: {stats['total']}")
    logger.info(f"  有效筆數: {stats['active']}")
    logger.info(f"  已刪除筆數: {stats['deleted']}")

    return 0


def main() -> int:
    """主程式進入點

    Returns:
        結束代碼（0 = 成功）
    """
    # 確保必要目錄存在
    ensure_directories()

    parser = create_parser()
    args = parser.parse_args()

    logger = get_logger()

    # 除錯模式
    if args.debug:
        logger.info("=== 設定資訊 ===")
        for key, value in get_config_summary().items():
            logger.info(f"  {key}: {value}")

    # 執行對應指令
    if args.command == "sync-parking":
        return cmd_sync_parking(args)
    elif args.command == "stats":
        return cmd_stats(args)

    # 無指令時顯示說明
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
