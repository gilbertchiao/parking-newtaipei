# parking-newtaipei

新北市停車場資料擷取與分析工具

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

2. 編輯 `.env`，設定 API URL 等參數：

```env
API_BASE_URL=https://example.com/api
LOG_LEVEL=INFO
```

## 使用方式

### 顯示說明

```bash
uv run python -m parking_newtaipei --help
```

### 擷取資料

```bash
# 實際執行
uv run python -m parking_newtaipei fetch

# 測試模式（不呼叫 API）
uv run python -m parking_newtaipei fetch --dry-run
```

### 除錯模式

```bash
uv run python -m parking_newtaipei --debug fetch
```

## 目錄結構

```
parking-newtaipei/
├── src/parking_newtaipei/   # 主程式碼
├── data/
│   ├── db/                  # SQLite 資料庫
│   └── responses/           # API response 備份（.json.gz）
├── logs/                    # 執行日誌
├── scripts/                 # 部署腳本
├── tests/                   # 測試
└── docs/                    # 文件
```

## 定時執行（Cron）

參考 `scripts/crontab.example` 設定每 5 分鐘執行一次：

```cron
*/5 * * * * cd /path/to/parking-newtaipei && /path/to/.venv/bin/python -m parking_newtaipei fetch
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
