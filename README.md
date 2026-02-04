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

# Healthcheck 通報 URL（選填，未設定則不通報）
# HEALTHCHECK_PARKING_URL=https://hc-ping.com/your-parking-uuid
# HEALTHCHECK_AVAILABILITY_URL=https://hc-ping.com/your-availability-uuid
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

### Healthcheck 通報

同步成功後可自動 ping 指定的 URL，用於監控服務健康狀態（如 [healthchecks.io](https://healthchecks.io/)）：

- 設定 `HEALTHCHECK_PARKING_URL`：停車場基本資料同步成功時通報
- 設定 `HEALTHCHECK_AVAILABILITY_URL`：即時車位資料同步成功時通報
- 未設定則不通報（預設行為）
- 通報失敗只記錄警告，不影響同步結果

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
├── docker/                  # Docker 相關檔案
│   ├── crontab              # Cron 排程設定
│   └── entrypoint.sh        # 容器進入點腳本
├── data/
│   ├── db/                  # 停車場基本資料庫
│   ├── availability/        # 即時車位資料庫（每月一檔）
│   └── responses/           # API response 備份（.json.gz，按 YYYYMM 分目錄）
├── logs/                    # 執行日誌
├── scripts/                 # 部署腳本
├── tests/                   # 測試
├── docs/                    # 文件
├── Dockerfile               # Docker 映像建構檔
└── docker-compose.yml       # Docker Compose 設定
```

## 部署方式

### 方式一：本機 Cron

參考 `scripts/crontab.example`：

```cron
# 每 5 分鐘同步即時剩餘車位資料
*/5 * * * * cd /path/to/parking-newtaipei && .venv/bin/python -m parking_newtaipei sync-availability

# 每日凌晨 2 點同步停車場基本資料
0 2 * * * cd /path/to/parking-newtaipei && .venv/bin/python -m parking_newtaipei sync-parking
```

### 方式二：Docker 部署

使用 Docker Compose 快速部署，內建 Cron 排程自動執行同步任務。

#### 啟動服務

```bash
# 建立並啟動（首次啟動會自動同步停車場資料）
docker compose up -d

# 檢視容器狀態
docker compose ps

# 檢視日誌
docker compose logs -f
```

#### 手動操作

```bash
# 同步停車場基本資料
docker compose exec parking-etl python -m parking_newtaipei sync-parking

# 同步即時車位資料
docker compose exec parking-etl python -m parking_newtaipei sync-availability

# 查看統計資訊
docker compose exec parking-etl python -m parking_newtaipei stats

# 查看 Cron 執行紀錄
docker compose exec parking-etl cat /app/logs/cron.log
```

#### 停止服務

```bash
# 停止（保留資料）
docker compose down

# 停止並刪除資料
docker compose down -v
```

#### 環境變數

| 變數名稱 | 預設值 | 說明 |
|---------|--------|------|
| `API_BASE_URL` | (選填) | API 基礎 URL |
| `LOG_LEVEL` | `INFO` | 日誌等級 |
| `LOG_BACKUP_DAYS` | `30` | 日誌保留天數 |
| `TZ` | `Asia/Taipei` | 時區設定 |
| `HEALTHCHECK_PARKING_URL` | (選填) | 停車場基本資料同步成功通報 URL |
| `HEALTHCHECK_AVAILABILITY_URL` | (選填) | 即時車位資料同步成功通報 URL |

詳細說明請參考 [docs/DOCKER_DEPLOYMENT.md](docs/DOCKER_DEPLOYMENT.md)。

### 方式三：AWS ECS Fargate 常駐

使用現有 Dockerfile 部署到 AWS ECS Fargate，容器內 cron 處理排程：

```bash
# 建構並推送映像到 ECR
docker build -t parking-newtaipei:latest .
docker tag parking-newtaipei:latest $ECR_URI:latest
docker push $ECR_URI:latest

# 建立 ECS Service
aws ecs create-service \
    --cluster parking-cluster \
    --service-name parking-etl-service \
    --task-definition parking-etl-fargate \
    --desired-count 1 \
    --launch-type FARGATE
```

### 方式四：AWS ECS Scheduled Tasks

使用 EventBridge 排程觸發 ECS Task，按執行次數計費：

```bash
# 建構並推送 scheduled 版本映像
docker build -f aws/ecs/Dockerfile.scheduled -t parking-newtaipei:scheduled .
docker push $ECR_URI:scheduled

# 建立 EventBridge 排程規則
aws events put-rule --name parking-sync-availability --schedule-expression "rate(5 minutes)"
aws events put-rule --name parking-sync-parking --schedule-expression "cron(0 18 * * ? *)"
```

詳細說明請參考 [docs/AWS_ECS_DEPLOYMENT.md](docs/AWS_ECS_DEPLOYMENT.md)。

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
