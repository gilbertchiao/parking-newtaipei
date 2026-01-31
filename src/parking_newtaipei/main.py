"""CLI 進入點

支援 --help 和 fetch 指令。
"""

import argparse
import sys

from parking_newtaipei import __version__
from parking_newtaipei.config import (
    API_BASE_URL,
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

    # fetch 指令
    fetch_parser = subparsers.add_parser(
        "fetch",
        help="擷取停車場資料",
    )
    fetch_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="測試模式，不實際呼叫 API",
    )

    return parser


def cmd_fetch(args: argparse.Namespace) -> int:
    """執行 fetch 指令

    Args:
        args: 命令列參數

    Returns:
        結束代碼（0 = 成功）
    """
    logger = get_logger()

    if args.dry_run:
        logger.info("=== Dry Run 模式 ===")
        logger.info("API Base URL: %s", API_BASE_URL or "(未設定)")
        logger.info("Responses 目錄: %s", RESPONSES_PATH)
        logger.info("測試完成，未實際呼叫 API")
        return 0

    if not API_BASE_URL:
        logger.error("請先在 .env 設定 API_BASE_URL")
        return 1

    # TODO: 實作實際的 API 擷取邏輯
    logger.info("開始擷取停車場資料...")
    logger.warning("API 擷取功能尚未實作，請待 API 規格確認後完成")

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
    if args.command == "fetch":
        return cmd_fetch(args)

    # 無指令時顯示說明
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
