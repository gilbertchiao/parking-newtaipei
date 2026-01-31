# parking-newtaipei

新北市停車場資料擷取與分析工具

## 資料來源

- [新北市路外公共停車場資訊](https://data.gov.tw/dataset/122955)
- 資料格式：CSV
- 更新頻率：不定期

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
# DB_PATH=data/db/parking.db
# RESPONSES_PATH=data/responses/
```

## 使用方式

### 顯示說明

```bash
uv run python -m parking_newtaipei --help
```

### 同步停車場資料

```bash
# 實際執行
uv run python -m parking_newtaipei sync-parking

# 測試模式（不實際執行）
uv run python -m parking_newtaipei sync-parking --dry-run
```

### 查看統計資訊

```bash
uv run python -m parking_newtaipei stats
```

### 除錯模式

```bash
uv run python -m parking_newtaipei --debug sync-parking
```

## 同步行為

執行 `sync-parking` 時的處理邏輯：

| 情況 | 處理方式 |
|------|----------|
| API 有、DB 無 | 新增資料 |
| API 有、DB 有 | 更新資料（含恢復已刪除的） |
| API 無、DB 有 | 標記 `deleted_at`（軟刪除） |
| 已標記刪除 | 不重複更新刪除時間 |

## 資料庫結構

停車場資料表 `parking_lots`：

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

## 目錄結構

```
parking-newtaipei/
├── src/parking_newtaipei/   # 主程式碼
│   ├── api/                 # API 客戶端
│   ├── db/                  # 資料庫模組
│   ├── etl/                 # ETL 模組
│   └── utils/               # 工具模組
├── data/
│   ├── db/                  # SQLite 資料庫
│   └── responses/           # API response 備份（.json.gz）
├── logs/                    # 執行日誌
├── scripts/                 # 部署腳本
├── tests/                   # 測試
└── docs/                    # 文件
```

## 定時執行（Cron）

參考 `scripts/crontab.example` 設定每日執行：

```cron
# 每日凌晨 2 點同步停車場資料
0 2 * * * cd /path/to/parking-newtaipei && /path/to/.venv/bin/python -m parking_newtaipei sync-parking
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
