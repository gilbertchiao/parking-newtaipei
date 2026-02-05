#!/bin/bash
#
# sync-data.sh - 將停車場資料同步到遠端伺服器或 AWS S3
#
# 使用方式:
#   ./scripts/sync-data.sh [METHOD] [TARGET]
#
# METHOD: scp | awscli | s3cmd
# TARGET:
#   - scp:    user@host:/path/to/destination
#   - awscli: s3://bucket-name/path
#   - s3cmd:  s3://bucket-name/path
#
# 範例:
#   ./scripts/sync-data.sh scp ubuntu@192.168.1.100:/data/parking
#   ./scripts/sync-data.sh awscli s3://my-bucket/parking-data
#   ./scripts/sync-data.sh s3cmd s3://my-bucket/parking-data
#
# 環境變數（可選）:
#   SYNC_METHOD  - 預設傳輸方式
#   SYNC_TARGET  - 預設目標位置
#   SSH_KEY      - SSH 私鑰路徑（用於 scp）
#   AWS_PROFILE  - AWS profile 名稱（用於 awscli）
#

set -euo pipefail

# 取得腳本所在目錄，並切換到專案根目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# 要同步的檔案
FILES=(
    "data/db/parking.db"
    "data/availability/availability.json"
)

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 輸出函數
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 顯示使用說明
show_usage() {
    cat << EOF
使用方式: $0 [METHOD] [TARGET]

METHOD (傳輸方式):
  scp      使用 SCP 傳輸到遠端伺服器
  awscli   使用 AWS CLI 上傳到 S3
  s3cmd    使用 s3cmd 上傳到 S3

TARGET (目標位置):
  scp:     user@host:/path/to/destination
  awscli:  s3://bucket-name/path
  s3cmd:   s3://bucket-name/path

環境變數:
  SYNC_METHOD  預設傳輸方式
  SYNC_TARGET  預設目標位置
  SSH_KEY      SSH 私鑰路徑 (用於 scp)
  AWS_PROFILE  AWS profile 名稱 (用於 awscli)

範例:
  $0 scp ubuntu@192.168.1.100:/data/parking
  $0 awscli s3://my-bucket/parking-data
  $0 s3cmd s3://my-bucket/parking-data

  # 使用環境變數
  export SYNC_METHOD=awscli
  export SYNC_TARGET=s3://my-bucket/parking-data
  $0
EOF
}

# 檢查檔案是否存在
check_files() {
    local missing=0
    for file in "${FILES[@]}"; do
        if [[ ! -f "$file" ]]; then
            log_warn "檔案不存在: $file"
            missing=$((missing + 1))
        fi
    done

    if [[ $missing -eq ${#FILES[@]} ]]; then
        log_error "所有檔案都不存在，無法同步"
        exit 1
    fi
}

# 檢查命令是否存在
check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "找不到命令: $1"
        log_error "請先安裝 $1"
        exit 1
    fi
}

# 使用 SCP 傳輸
sync_scp() {
    local target="$1"
    check_command "scp"

    log_info "使用 SCP 傳輸到: $target"

    local scp_opts="-p"  # 保留檔案時間戳記

    # 如果有指定 SSH 私鑰
    if [[ -n "${SSH_KEY:-}" ]]; then
        scp_opts="$scp_opts -i $SSH_KEY"
        log_info "使用 SSH 私鑰: $SSH_KEY"
    fi

    for file in "${FILES[@]}"; do
        if [[ -f "$file" ]]; then
            log_info "傳輸: $file"
            scp $scp_opts "$file" "$target/"
        fi
    done

    log_info "SCP 傳輸完成"
}

# 使用 AWS CLI 傳輸
sync_awscli() {
    local target="$1"
    check_command "aws"

    log_info "使用 AWS CLI 上傳到: $target"

    local aws_opts=""

    # 如果有指定 AWS profile
    if [[ -n "${AWS_PROFILE:-}" ]]; then
        aws_opts="--profile $AWS_PROFILE"
        log_info "使用 AWS Profile: $AWS_PROFILE"
    fi

    for file in "${FILES[@]}"; do
        if [[ -f "$file" ]]; then
            local filename
            filename=$(basename "$file")
            log_info "上傳: $file -> $target/$filename"
            aws s3 cp "$file" "$target/$filename" $aws_opts
        fi
    done

    log_info "AWS CLI 上傳完成"
}

# 使用 s3cmd 傳輸
sync_s3cmd() {
    local target="$1"
    check_command "s3cmd"

    log_info "使用 s3cmd 上傳到: $target"

    for file in "${FILES[@]}"; do
        if [[ -f "$file" ]]; then
            local filename
            filename=$(basename "$file")
            log_info "上傳: $file -> $target/$filename"
            s3cmd put "$file" "$target/$filename"
        fi
    done

    log_info "s3cmd 上傳完成"
}

# 主程式
main() {
    # 從參數或環境變數取得設定
    local method="${1:-${SYNC_METHOD:-}}"
    local target="${2:-${SYNC_TARGET:-}}"

    # 檢查參數
    if [[ -z "$method" ]] || [[ -z "$target" ]]; then
        show_usage
        exit 1
    fi

    # 檢查檔案
    check_files

    # 根據方法執行同步
    case "$method" in
        scp)
            sync_scp "$target"
            ;;
        awscli)
            sync_awscli "$target"
            ;;
        s3cmd)
            sync_s3cmd "$target"
            ;;
        *)
            log_error "不支援的傳輸方式: $method"
            log_error "支援的方式: scp, awscli, s3cmd"
            exit 1
            ;;
    esac

    log_info "同步完成！"
}

# 執行主程式
main "$@"
