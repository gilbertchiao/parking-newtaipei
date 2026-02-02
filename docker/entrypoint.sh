#!/bin/bash
set -e

# 確保資料目錄存在
mkdir -p /app/data/db /app/data/availability /app/data/responses /app/logs

# 初始化標記檔案
INIT_FLAG="/app/data/.initialized"

# 首次啟動時執行初始同步
if [ ! -f "$INIT_FLAG" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] 首次啟動，執行停車場資料初始同步..."

    # 執行停車場基本資料同步
    if /app/.venv/bin/python -m parking_newtaipei sync-parking; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] 停車場資料初始同步完成"
        touch "$INIT_FLAG"
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] 停車場資料初始同步失敗"
    fi
fi

# 輸出啟動資訊
echo "=============================================="
echo "  新北市停車場 ETL 服務啟動"
echo "=============================================="
echo "時區: ${TZ:-Asia/Taipei}"
echo "日誌等級: ${LOG_LEVEL:-INFO}"
echo "日誌保留天數: ${LOG_BACKUP_DAYS:-30}"
echo ""
echo "排程任務:"
echo "  - 即時車位同步: 每 5 分鐘"
echo "  - 停車場資料同步: 每天 02:00"
echo ""
echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Cron 服務啟動中..."
echo "=============================================="

# 將環境變數寫入檔案供 cron 使用
printenv | grep -E '^(API_BASE_URL|LOG_LEVEL|LOG_BACKUP_DAYS|TZ|PROJECT_ROOT|DATA_DIR|LOGS_DIR|PATH|PYTHONUNBUFFERED|PYTHONDONTWRITEBYTECODE)=' > /etc/environment

# 前景執行 cron
exec cron -f
