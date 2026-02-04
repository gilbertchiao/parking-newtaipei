# 專案說明

新北市停車場資料擷取與分析工具（parking-newtaipei）

## 技術棧

- **語言**: Python 3.12+
- **套件管理**: uv
- **HTTP 客戶端**: httpx
- **資料庫**: SQLite 3
- **測試框架**: pytest
- **程式碼檢查**: ruff

## 目錄結構

```
src/parking_newtaipei/
├── __main__.py          # CLI 入口
├── main.py              # 主程式邏輯（argparse 子命令）
├── config.py            # 環境變數與路徑設定
├── api/
│   └── client.py        # 通用 HTTP API 客戶端
├── db/
│   ├── connection.py    # SQLite 連線管理（context manager）
│   ├── models.py        # 停車場資料模型與 Repository
│   └── availability.py  # 即時車位資料模型與 Repository
├── etl/
│   ├── parking_sync.py      # 停車場基本資料同步
│   └── availability_sync.py # 即時車位資料同步
└── utils/
    ├── logger.py        # 日誌管理（TimedRotatingFileHandler）
    ├── storage.py       # API Response 備份（gzip JSON）
    ├── process_lock.py  # 進程鎖（fcntl file lock）
    ├── time.py          # 時間工具（ISO 8601）
    └── healthcheck.py   # Healthcheck 通報
```

## 資料來源

| 資料集 | API URL | 更新頻率 |
|--------|---------|----------|
| 停車場基本資料 | `data.ntpc.gov.tw/.../b1464ef0-9c7c-4a6f-abf7-6bdf32847e68/csv/file` | 每日 |
| 即時車位資料 | `data.ntpc.gov.tw/.../e09b35a5-a738-48cc-b0f5-570b67ad9c78/csv/file` | 每 5 分鐘 |

## 資料庫

- **停車場基本資料**: `data/db/parking.db` - 單一檔案
- **即時車位資料**: `data/availability/availability_YYYYMM.db` - 每月一檔

### 主要資料表

- `parking_lots`: 停車場基本資料（軟刪除機制，deleted_at 欄位）
- `sync_metadata`: 同步雜湊值記錄
- `availability`: 即時車位時序資料

## CLI 指令

```bash
# 同步停車場基本資料
uv run python -m parking_newtaipei sync-parking [--force] [--dry-run]

# 同步即時車位資料
uv run python -m parking_newtaipei sync-availability [--dry-run]

# 統計資訊
uv run python -m parking_newtaipei stats
uv run python -m parking_newtaipei availability-stats

# 除錯模式
uv run python -m parking_newtaipei --debug <command>
```

## 環境變數

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `LOG_LEVEL` | `INFO` | 日誌等級 |
| `LOG_BACKUP_DAYS` | `90` | 日誌保留天數 |
| `DB_PATH` | `data/db/parking.db` | 停車場資料庫路徑 |
| `AVAILABILITY_DB_DIR` | `data/availability/` | 即時車位資料庫目錄 |
| `RESPONSES_PATH` | `data/responses/` | API Response 備份路徑 |
| `HEALTHCHECK_PARKING_URL` | (空) | 停車場同步成功通報 URL |
| `HEALTHCHECK_AVAILABILITY_URL` | (空) | 即時車位同步成功通報 URL |

## 同步邏輯

### 停車場基本資料 (sync-parking)

1. 下載 CSV 並計算 SHA256 雜湊
2. 比對上次雜湊，相同則跳過（除非 `--force`）
3. 執行 upsert（新增/更新）
4. 標記已刪除資料（軟刪除）
5. 成功時 ping healthcheck URL

### 即時車位資料 (sync-availability)

1. 下載 CSV
2. 過濾無效資料（`AVAILABLECAR = -9`）
3. 批次寫入當月資料庫
4. 成功時 ping healthcheck URL

## 進程鎖

- 鎖檔案: `/tmp/parking_newtaipei_<command>.lock`
- 使用 `fcntl.flock()` 排他鎖
- 退出碼: 0=成功, 1=錯誤, 2=跳過（已有進程執行）

## 開發指令

```bash
# 測試
uv run pytest

# 程式碼檢查
uv run ruff check src/
uv run ruff format src/
```

## 部署方式

- 本機 Cron
- Docker Compose（內建 cron）
- AWS ECS Fargate（常駐或 Scheduled Tasks）

詳見 `docs/DOCKER_DEPLOYMENT.md` 和 `docs/AWS_ECS_DEPLOYMENT.md`。
