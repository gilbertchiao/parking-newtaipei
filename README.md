# parking-newtaipei

新北市停車場資料擷取與分析工具

## 資料來源

| 資料集 | 更新頻率 | 說明 |
|--------|----------|------|
| [路外公共停車場資訊](https://data.gov.tw/dataset/122955) | 每日 | 停車場基本資料 |
| [即時剩餘車位數](https://data.gov.tw/dataset/122902) | 每 5 分鐘 | 即時車位資料 |

## 環境需求

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) 套件管理工具

## 安裝

```bash
# 安裝 uv（如尚未安裝）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安裝專案依賴
uv sync

# 安裝開發依賴（包含 pytest、ruff）
uv sync --all-extras
```

## 設定

1. 複製環境變數範例檔：

```bash
cp .env.example .env
```

2. 編輯 `.env`，設定參數（選填）：

```env
LOG_LEVEL=INFO
# LOG_BACKUP_DAYS=30
# DB_PATH=data/db/parking.db
# AVAILABILITY_DB_DIR=data/availability/
# RESPONSES_PATH=data/responses/
```

## 使用方式

### 顯示說明

```bash
uv run python -m parking_newtaipei --help
```

### 同步停車場基本資料（每日）

```bash
# 實際執行（自動檢查內容是否變更）
uv run python -m parking_newtaipei sync-parking

# 強制同步（忽略雜湊檢查）
uv run python -m parking_newtaipei sync-parking --force

# 測試模式（不實際執行）
uv run python -m parking_newtaipei sync-parking --dry-run
```

### 同步即時車位資料（每 5 分鐘）

```bash
# 實際執行
uv run python -m parking_newtaipei sync-availability

# 測試模式
uv run python -m parking_newtaipei sync-availability --dry-run
```

### 查看統計資訊

```bash
# 停車場基本資料統計
uv run python -m parking_newtaipei stats

# 即時車位資料統計
uv run python -m parking_newtaipei availability-stats
```

### 除錯模式

```bash
uv run python -m parking_newtaipei --debug sync-parking
```

## 同步行為

### 進程鎖保護

同步命令使用 `fcntl` 檔案鎖防止重複執行：

- 鎖檔案位置：`/tmp/parking_newtaipei_<command>.lock`
- 若已有進程執行，後續執行會跳過並記錄警告
- 進程結束（正常結束、crash、kill）時自動釋放鎖

**退出碼：**

| 退出碼 | 說明 |
|--------|------|
| 0 | 成功 |
| 1 | 錯誤 |
| 2 | 跳過（已有進程執行中） |

### 停車場基本資料（sync-parking）

每次下載後會計算 SHA256 雜湊值，與上次同步的雜湊值比對：
- **雜湊相同** + 資料表非空 → 跳過同步，避免不必要的資料庫操作
- **雜湊不同** 或 資料表為空 → 執行完整同步
- 使用 `--force` 可強制同步，忽略雜湊檢查

| 情況 | 處理方式 |
|------|----------|
| API 有、DB 無 | 新增資料 |
| API 有、DB 有 | 更新資料（含恢復已刪除的） |
| API 無、DB 有 | 標記 `deleted_at`（軟刪除） |
| 已標記刪除 | 不重複更新刪除時間 |

### 即時車位資料（sync-availability）

- 每次執行直接寫入資料庫，記錄時間序列
- `AVAILABLECAR = -9` 視為無效資料，不寫入
- 每月一個資料庫檔案（`availability_YYYYMM.db`），避免單檔過大

## 資料庫結構

### 停車場基本資料 `data/db/parking.db`

**parking_lots 表：**

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | TEXT | 停車場編號（主鍵） |
| area | TEXT | 行政區 |
| name | TEXT | 停車場名稱 |
| type | TEXT | 類型 |
| summary | TEXT | 摘要 |
| address | TEXT | 地址 |
| tel | TEXT | 電話 |
| pay_ex | TEXT | 收費方式 |
| service_time | TEXT | 服務時間 |
| tw97x | REAL | TWD97 X 座標 |
| tw97y | REAL | TWD97 Y 座標 |
| total_car | INTEGER | 汽車位數 |
| total_motor | INTEGER | 機車位數 |
| total_bike | INTEGER | 自行車位數 |
| created_at | TEXT | 建立時間 |
| updated_at | TEXT | 更新時間 |
| deleted_at | TEXT | 刪除時間（軟刪除） |

### 即時車位資料 `data/availability/availability_YYYYMM.db`

**availability 表：**

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER | 自動遞增主鍵 |
| parking_id | TEXT | 停車場編號 |
| available_car | INTEGER | 剩餘車位數 |
| recorded_at | TEXT | 記錄時間 |

## 目錄結構

```
parking-newtaipei/
├── src/parking_newtaipei/   # 主程式碼
│   ├── api/                 # API 客戶端
│   ├── db/                  # 資料庫模組
│   ├── etl/                 # ETL 模組
│   └── utils/               # 工具模組
├── data/
│   ├── db/                  # 停車場基本資料庫
│   ├── availability/        # 即時車位資料庫（每月一檔）
│   └── responses/           # API response 備份（.json.gz）
├── logs/                    # 執行日誌
├── scripts/                 # 部署腳本
├── tests/                   # 測試
└── docs/                    # 文件
```

## 定時執行（Cron）

參考 `scripts/crontab.example`：

```cron
# 每 5 分鐘同步即時剩餘車位資料
*/5 * * * * cd /path/to/parking-newtaipei && .venv/bin/python -m parking_newtaipei sync-availability

# 每日凌晨 2 點同步停車場基本資料
0 2 * * * cd /path/to/parking-newtaipei && .venv/bin/python -m parking_newtaipei sync-parking
```

## 開發

### 執行測試

```bash
uv run pytest
```

### 程式碼檢查

```bash
uv run ruff check src/
uv run ruff format src/
```

## 授權

MIT License
