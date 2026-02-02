# Docker 部署方案

## 目標

為新北市停車場 ETL 專案新增 Docker 部署支援，可透過 `docker compose up -d` 快速部署運行。

## 方案選擇

採用**容器內 Cron 方案**（單一常駐容器處理所有排程）：

- **簡單部署**：一個容器完成所有工作
- **自動恢復**：容器重啟時排程自動恢復
- **資料持久化**：透過 Docker volumes

---

## 新增檔案清單

### 1. `Dockerfile`

Multi-stage build，使用官方 uv 映像安裝依賴：

- **Stage 1 (builder)**: 使用 `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` 執行 `uv sync`
- **Stage 2 (runtime)**: 使用 `python:3.12-slim-bookworm`，安裝 cron，複製虛擬環境
- 設定預設環境變數
- 健康檢查：`python -m parking_newtaipei stats`

### 2. `docker-compose.yml`

- 服務名稱：`parking-etl`
- 環境變數支援（LOG_LEVEL, LOG_BACKUP_DAYS, TZ）
- Volumes：
  - `parking-data`：持久化 data/
  - `parking-logs`：持久化 logs/
- 記憶體限制：256MB

### 3. `docker/crontab`

```cron
# 每 5 分鐘同步即時車位資料
*/5 * * * * cd /app && /app/.venv/bin/python -m parking_newtaipei sync-availability >> /app/logs/cron.log 2>&1

# 每天凌晨 2 點同步停車場基本資料
0 2 * * * cd /app && /app/.venv/bin/python -m parking_newtaipei sync-parking >> /app/logs/cron.log 2>&1
```

### 4. `docker/entrypoint.sh`

- 確保資料目錄存在
- 首次啟動時自動執行初始同步（sync-parking）
- 輸出啟動資訊
- 執行 `cron -f` 前景運行

### 5. `.dockerignore`

排除不需複製的檔案：
- `.git/`
- `.venv/`
- `data/`
- `logs/`
- `tests/`
- `__pycache__/`
- `.env`

---

## 修改檔案

### `src/parking_newtaipei/config.py`

調整路徑設定支援環境變數覆蓋：

```python
# 專案根目錄（支援環境變數覆蓋，用於 Docker 環境）
PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", Path(__file__).parent.parent.parent))

# 資料目錄（支援環境變數覆蓋）
DATA_DIR = Path(os.getenv("DATA_DIR", str(PROJECT_ROOT / "data")))

# 日誌目錄（支援環境變數覆蓋）
LOGS_DIR = Path(os.getenv("LOGS_DIR", str(PROJECT_ROOT / "logs")))
```

---

## 使用方式

### 建立並啟動

```bash
docker compose up -d
```

### 檢視日誌

```bash
# 容器日誌
docker compose logs -f

# Cron 執行日誌
docker compose exec parking-etl cat /app/logs/cron.log
```

### 手動執行同步

```bash
# 同步停車場基本資料
docker compose exec parking-etl python -m parking_newtaipei sync-parking

# 同步即時車位資料
docker compose exec parking-etl python -m parking_newtaipei sync-availability
```

### 檢視統計

```bash
docker compose exec parking-etl python -m parking_newtaipei stats
```

### 停止服務

```bash
docker compose down
```

### 停止並刪除資料

```bash
docker compose down -v
```

---

## 環境變數

| 變數名稱 | 預設值 | 說明 |
|---------|--------|------|
| `API_BASE_URL` | (必填) | 新北市停車場 API 基礎 URL |
| `LOG_LEVEL` | `INFO` | 日誌等級 (DEBUG/INFO/WARNING/ERROR) |
| `LOG_BACKUP_DAYS` | `30` | 日誌保留天數 |
| `TZ` | `Asia/Taipei` | 時區設定 |

---

## 驗證步驟

1. **建構映像**
   ```bash
   docker compose build
   ```
   應無錯誤完成

2. **啟動容器**
   ```bash
   docker compose up -d
   docker compose ps
   ```
   顯示 running 狀態

3. **初始同步**
   首次啟動會自動執行 sync-parking，檢查 logs：
   ```bash
   docker compose logs
   ```

4. **手動測試**
   ```bash
   # 顯示統計
   docker compose exec parking-etl python -m parking_newtaipei stats

   # 測試 dry-run
   docker compose exec parking-etl python -m parking_newtaipei sync-availability --dry-run
   ```

5. **Cron 驗證**
   等待 5 分鐘，確認 sync-availability 自動執行：
   ```bash
   docker compose exec parking-etl cat /app/logs/cron.log
   ```

6. **持久化驗證**
   ```bash
   docker compose down
   docker compose up -d
   docker compose exec parking-etl python -m parking_newtaipei stats
   ```
   資料應仍然存在

---

## 檔案結構

實作完成後的專案結構：

```
parking-newtaipei/
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── docker/
│   ├── crontab
│   └── entrypoint.sh
├── src/
│   └── parking_newtaipei/
│       └── config.py  (修改)
└── ...
```
