# Stage 1: Builder - 使用 uv 安裝依賴
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

# 複製依賴定義檔案（包含 README.md 供 hatchling 建構）
COPY pyproject.toml uv.lock README.md ./

# 安裝依賴到虛擬環境
RUN uv sync --frozen --no-dev --no-install-project

# 複製原始碼
COPY src/ ./src/

# 安裝專案本身
RUN uv sync --frozen --no-dev


# Stage 2: Runtime - 輕量執行環境
FROM python:3.12-slim-bookworm

# 安裝 cron
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 從 builder 複製虛擬環境
COPY --from=builder /app/.venv /app/.venv

# 複製原始碼
COPY src/ ./src/

# 複製 Docker 相關檔案
COPY docker/crontab /etc/cron.d/parking-cron
COPY docker/entrypoint.sh /entrypoint.sh

# 設定 crontab 權限
RUN chmod 0644 /etc/cron.d/parking-cron && \
    crontab /etc/cron.d/parking-cron && \
    chmod +x /entrypoint.sh

# 建立資料與日誌目錄
RUN mkdir -p /app/data /app/logs

# 設定環境變數
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PROJECT_ROOT=/app \
    DATA_DIR=/app/data \
    LOGS_DIR=/app/logs \
    LOG_LEVEL=INFO \
    LOG_BACKUP_DAYS=30 \
    TZ=Asia/Taipei

# 健康檢查
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -m parking_newtaipei stats || exit 1

ENTRYPOINT ["/entrypoint.sh"]
