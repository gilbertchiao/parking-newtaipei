# 專案初始化計劃：parking-newtaipei

## 專案概述
建立一個 Python 3.12+ 專案基礎架構，用於擷取 API 資料、分析並儲存至 SQLite 資料庫。
- **執行頻率**：每 5 分鐘（cron）
- **部署環境**：Ubuntu 22.04/24.04+

## 目錄結構

```
parking-newtaipei/
├── src/
│   └── parking_newtaipei/          # 主套件
│       ├── __init__.py
│       ├── main.py                  # CLI 進入點
│       ├── config.py                # 設定管理
│       ├── api/
│       │   ├── __init__.py
│       │   └── client.py            # 通用 API 客戶端（自動保存 request/response）
│       ├── db/
│       │   ├── __init__.py
│       │   ├── connection.py        # SQLite 連線管理
│       │   └── models.py            # 資料模型（待 API 規格後定義）
│       └── utils/
│           ├── __init__.py
│           ├── logger.py            # 日誌設定（rotating file handler）
│           └── storage.py           # 檔案儲存與 gzip 壓縮
├── data/
│   ├── db/                          # SQLite 資料庫
│   │   └── .gitkeep
│   └── responses/                   # API request/response 備份（.json.gz，按 YYYYMM 分目錄）
│       └── .gitkeep
├── logs/                            # 執行日誌
│   └── .gitkeep
├── scripts/
│   └── crontab.example              # cron 設定範例
├── tests/
│   └── __init__.py
├── docs/
│   └── INIT_PLAN.md                 # 專案初始化計劃（本文件）
├── .env.example                     # 環境變數範例
├── .gitignore
├── .python-version                  # Python 版本鎖定
├── pyproject.toml                   # 專案設定（uv）
└── README.md
```

## 建立檔案清單

### 1. 專案設定檔
| 檔案 | 說明 |
|------|------|
| `pyproject.toml` | uv 專案設定，依賴套件定義 |
| `.python-version` | 指定 Python 3.12 |
| `.gitignore` | 排除 data/db/、logs/、.env、__pycache__ 等 |
| `.env.example` | 環境變數範本 |

### 2. 核心模組（基礎架構）
| 檔案 | 說明 |
|------|------|
| `main.py` | CLI 進入點，支援 `--help`、`fetch` 指令 |
| `config.py` | 載入 .env，集中管理路徑與設定 |
| `api/client.py` | 通用 HTTP 客戶端，自動記錄 request/response |
| `db/connection.py` | SQLite 連線管理器 |
| `db/models.py` | 預留資料模型（待 API 規格後實作） |
| `utils/logger.py` | RotatingFileHandler + console 輸出 |
| `utils/storage.py` | JSON 序列化 + gzip 壓縮儲存 |

### 3. 部署相關
| 檔案 | 說明 |
|------|------|
| `scripts/crontab.example` | cron 設定範例（每 5 分鐘） |
| `README.md` | 安裝與使用說明 |

## 依賴套件

```toml
[project]
dependencies = [
    "httpx>=0.27",        # HTTP 客戶端
    "python-dotenv>=1.0", # 環境變數
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "ruff>=0.4",          # linter
]
```

## 實作重點

### API Client（自動保存機制）
```python
# 每次呼叫 API 時自動保存：
# 1. 建立唯一檔名：{timestamp}_{endpoint_hash}.json.gz
# 2. 記錄內容：{"request": {...}, "response": {...}, "timestamp": "..."}
# 3. 使用 gzip 壓縮後存入 data/responses/{YYYYMM}/（依呼叫時間分目錄）
```

### Logger 設定
```python
# 同時輸出到 console 和檔案
# 檔案使用 RotatingFileHandler：
#   - 位置：logs/app.log
#   - 單檔上限：10MB
#   - 保留數量：5 個
```

### Cron 設定範例
```cron
*/5 * * * * cd /path/to/parking-newtaipei && /path/to/.venv/bin/python -m parking_newtaipei fetch >> /dev/null 2>&1
```

## 驗證方式

1. `uv sync` - 確認套件安裝正確
2. `uv run python -m parking_newtaipei --help` - 確認 CLI 可用
3. `uv run python -m parking_newtaipei fetch --dry-run` - 測試執行（不實際呼叫 API）
4. 檢查目錄結構是否正確建立

---

## 附註
此計劃文件將保存至專案 `docs/INIT_PLAN.md`，作為專案初始化的參考文件。
