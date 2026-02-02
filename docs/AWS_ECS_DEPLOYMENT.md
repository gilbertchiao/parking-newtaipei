# AWS ECS 部署方案

本文件說明如何將新北市停車場 ETL 專案部署到 AWS ECS，提供兩種部署方式供選擇。

## 部署方式比較

| 方式 | 說明 | 適用場景 |
|------|------|----------|
| **ECS Fargate 常駐** | 單一容器運行 cron 排程 | 簡單部署、與 Docker 部署一致 |
| **ECS Scheduled Tasks** | EventBridge 觸發排程任務 | 成本優化、AWS 最佳實踐 |

---

## 方式一：ECS Fargate 常駐

使用現有的 Dockerfile（含 cron），部署為常駐服務。

### 架構圖

```
┌─────────────────────────────────────────┐
│  ECS Fargate Service                    │
│  ┌───────────────────────────────────┐  │
│  │  Container (cron -f)              │  │
│  │  - sync-availability (每5分鐘)    │  │
│  │  - sync-parking (每天2:00)        │  │
│  └───────────────────────────────────┘  │
│              │                          │
│              ▼                          │
│  ┌───────────────────────────────────┐  │
│  │  EFS Volume (/app/data)           │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### 優缺點

**優點：**
- 使用現有 Docker 設定，無需改動程式碼
- 部署簡單，與本機 Docker 部署一致

**缺點：**
- 容器需常駐運行，即使沒有任務也佔用資源
- 不符合 AWS 最佳實踐（Serverless）

### 前置準備

#### 1. 建立 ECR Repository

```bash
# 建立 ECR repository
aws ecr create-repository \
    --repository-name parking-newtaipei \
    --image-scanning-configuration scanOnPush=true

# 取得 registry URI
ECR_URI=$(aws ecr describe-repositories \
    --repository-names parking-newtaipei \
    --query 'repositories[0].repositoryUri' \
    --output text)
echo $ECR_URI
```

#### 2. 建立 EFS 檔案系統

SQLite 需要持久化存儲，使用 EFS 掛載：

```bash
# 建立 EFS
aws efs create-file-system \
    --performance-mode generalPurpose \
    --throughput-mode bursting \
    --encrypted \
    --tags Key=Name,Value=parking-newtaipei-efs

# 記下 FileSystemId
EFS_ID=fs-xxxxxxxxx

# 建立 Mount Target（每個 subnet 一個）
aws efs create-mount-target \
    --file-system-id $EFS_ID \
    --subnet-id subnet-xxxxxxxx \
    --security-groups sg-xxxxxxxx

# 建立 Access Point
aws efs create-access-point \
    --file-system-id $EFS_ID \
    --posix-user Uid=1000,Gid=1000 \
    --root-directory "Path=/parking-data,CreationInfo={OwnerUid=1000,OwnerGid=1000,Permissions=755}"
```

#### 3. 建立 IAM Role

```bash
# 建立 Task Execution Role（用於拉取映像、寫入 CloudWatch Logs）
aws iam create-role \
    --role-name ecsTaskExecutionRole \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "ecs-tasks.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }'

aws iam attach-role-policy \
    --role-name ecsTaskExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
```

### 部署步驟

#### 1. 建構並推送映像

```bash
# 登入 ECR
aws ecr get-login-password --region ap-northeast-1 | \
    docker login --username AWS --password-stdin $ECR_URI

# 建構映像
docker build -t parking-newtaipei:latest .

# 標記映像
docker tag parking-newtaipei:latest $ECR_URI:latest

# 推送映像
docker push $ECR_URI:latest
```

#### 2. 建立 ECS Cluster

```bash
aws ecs create-cluster --cluster-name parking-cluster
```

#### 3. 註冊 Task Definition

使用 `aws/ecs/task-definition-fargate.json`：

```bash
aws ecs register-task-definition \
    --cli-input-json file://aws/ecs/task-definition-fargate.json
```

#### 4. 建立 ECS Service

```bash
aws ecs create-service \
    --cluster parking-cluster \
    --service-name parking-etl-service \
    --task-definition parking-etl-fargate \
    --desired-count 1 \
    --launch-type FARGATE \
    --platform-version LATEST \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-xxxxxxxx],securityGroups=[sg-xxxxxxxx],assignPublicIp=ENABLED}"
```

### 驗證

```bash
# 檢查服務狀態
aws ecs describe-services \
    --cluster parking-cluster \
    --services parking-etl-service

# 檢查 CloudWatch Logs
aws logs tail /ecs/parking-etl --follow

# 連接到容器執行命令
aws ecs execute-command \
    --cluster parking-cluster \
    --task <task-id> \
    --container parking-etl \
    --interactive \
    --command "/bin/bash"
```

---

## 方式二：ECS Scheduled Tasks

使用 EventBridge 排程觸發 ECS Task，任務完成後容器自動退出。

### 架構圖

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  EventBridge    │────▶│  ECS Task       │────▶│  執行完成退出   │
│  (排程規則)      │     │  (單次執行)      │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │
        │                       ▼
        │               ┌─────────────────┐
        │               │  EFS Volume     │
        │               └─────────────────┘
        │
        ├── rate(5 minutes) → sync-availability
        └── cron(0 18 * * ? *) → sync-parking (UTC 18:00 = UTC+8 02:00)
```

### 優缺點

**優點：**
- 按執行次數計費，無常駐成本
- 符合 AWS 最佳實踐（Serverless）
- 易於監控和管理
- 可獨立調整各任務的資源配置

**缺點：**
- 設定較複雜
- 需要額外的 Dockerfile

### 前置準備

同方式一的 ECR、EFS、IAM 設定，另外需要：

#### 建立 EventBridge IAM Role

```bash
# 建立 EventBridge 執行 ECS Task 的 Role
aws iam create-role \
    --role-name ecsEventsRole \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "events.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }'

# 附加執行 ECS Task 的權限
aws iam put-role-policy \
    --role-name ecsEventsRole \
    --policy-name ecsRunTaskPolicy \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": ["ecs:RunTask"],
            "Resource": ["*"],
            "Condition": {
                "ArnLike": {
                    "ecs:cluster": "arn:aws:ecs:*:*:cluster/parking-cluster"
                }
            }
        }, {
            "Effect": "Allow",
            "Action": "iam:PassRole",
            "Resource": ["*"],
            "Condition": {
                "StringLike": {
                    "iam:PassedToService": "ecs-tasks.amazonaws.com"
                }
            }
        }]
    }'
```

### 部署步驟

#### 1. 建構並推送 Scheduled 映像

```bash
# 建構 scheduled 版本映像
docker build -f aws/ecs/Dockerfile.scheduled -t parking-newtaipei:scheduled .

# 標記並推送
docker tag parking-newtaipei:scheduled $ECR_URI:scheduled
docker push $ECR_URI:scheduled
```

#### 2. 註冊 Task Definition

```bash
aws ecs register-task-definition \
    --cli-input-json file://aws/ecs/task-definition-scheduled.json
```

#### 3. 建立 EventBridge 排程規則

**sync-availability（每 5 分鐘）：**

```bash
# 建立規則
aws events put-rule \
    --name parking-sync-availability \
    --schedule-expression "rate(5 minutes)" \
    --state ENABLED

# 設定目標
aws events put-targets \
    --rule parking-sync-availability \
    --targets '[{
        "Id": "sync-availability-target",
        "Arn": "arn:aws:ecs:ap-northeast-1:123456789012:cluster/parking-cluster",
        "RoleArn": "arn:aws:iam::123456789012:role/ecsEventsRole",
        "EcsParameters": {
            "TaskDefinitionArn": "arn:aws:ecs:ap-northeast-1:123456789012:task-definition/parking-etl-scheduled",
            "TaskCount": 1,
            "LaunchType": "FARGATE",
            "NetworkConfiguration": {
                "awsvpcConfiguration": {
                    "Subnets": ["subnet-xxxxxxxx"],
                    "SecurityGroups": ["sg-xxxxxxxx"],
                    "AssignPublicIp": "ENABLED"
                }
            }
        },
        "Input": "{\"containerOverrides\":[{\"name\":\"parking-etl\",\"command\":[\"sync-availability\"]}]}"
    }]'
```

**sync-parking（每天 UTC 18:00 = UTC+8 02:00）：**

```bash
# 建立規則
aws events put-rule \
    --name parking-sync-parking \
    --schedule-expression "cron(0 18 * * ? *)" \
    --state ENABLED

# 設定目標
aws events put-targets \
    --rule parking-sync-parking \
    --targets '[{
        "Id": "sync-parking-target",
        "Arn": "arn:aws:ecs:ap-northeast-1:123456789012:cluster/parking-cluster",
        "RoleArn": "arn:aws:iam::123456789012:role/ecsEventsRole",
        "EcsParameters": {
            "TaskDefinitionArn": "arn:aws:ecs:ap-northeast-1:123456789012:task-definition/parking-etl-scheduled",
            "TaskCount": 1,
            "LaunchType": "FARGATE",
            "NetworkConfiguration": {
                "awsvpcConfiguration": {
                    "Subnets": ["subnet-xxxxxxxx"],
                    "SecurityGroups": ["sg-xxxxxxxx"],
                    "AssignPublicIp": "ENABLED"
                }
            }
        },
        "Input": "{\"containerOverrides\":[{\"name\":\"parking-etl\",\"command\":[\"sync-parking\"]}]}"
    }]'
```

### 驗證

```bash
# 檢查規則狀態
aws events list-rules --name-prefix parking-

# 手動觸發測試
aws ecs run-task \
    --cluster parking-cluster \
    --task-definition parking-etl-scheduled \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-xxxxxxxx],securityGroups=[sg-xxxxxxxx],assignPublicIp=ENABLED}" \
    --overrides '{"containerOverrides":[{"name":"parking-etl","command":["sync-availability"]}]}'

# 檢查 CloudWatch Logs
aws logs tail /ecs/parking-etl --follow
```

---

## AWS 資源需求

| 資源 | 用途 | 備註 |
|------|------|------|
| ECR Repository | 存放 Docker 映像 | 1-2 個（fargate/scheduled） |
| ECS Cluster | 運行容器 | 可共用現有 Cluster |
| EFS File System | SQLite 資料持久化 | 必須 |
| CloudWatch Log Group | 日誌收集 | 自動建立 |
| IAM Role | Task 執行權限 | ecsTaskExecutionRole |
| VPC/Subnet | 網路 | 需要 NAT 呼叫外部 API |

---

## 監控與日誌

### CloudWatch Logs

日誌自動寫入 CloudWatch Logs，可設定：

```bash
# 設定日誌保留期限
aws logs put-retention-policy \
    --log-group-name /ecs/parking-etl \
    --retention-in-days 30
```

### CloudWatch Alarms

建議設定的告警：

```bash
# Task 執行失敗告警
aws cloudwatch put-metric-alarm \
    --alarm-name parking-etl-task-failed \
    --metric-name FailedTaskCount \
    --namespace AWS/ECS \
    --statistic Sum \
    --period 300 \
    --threshold 1 \
    --comparison-operator GreaterThanOrEqualToThreshold \
    --dimensions Name=ClusterName,Value=parking-cluster \
    --evaluation-periods 1 \
    --alarm-actions arn:aws:sns:ap-northeast-1:123456789012:alerts
```

### Container Insights

啟用 Container Insights 獲得更詳細的監控：

```bash
aws ecs update-cluster-settings \
    --cluster parking-cluster \
    --settings name=containerInsights,value=enabled
```

---

## 故障排除

### 常見問題

#### 1. Task 無法啟動

**症狀**：Task 一直處於 PENDING 狀態

**檢查步驟**：
```bash
# 查看 Task 狀態
aws ecs describe-tasks \
    --cluster parking-cluster \
    --tasks <task-arn>

# 常見原因：
# - Subnet 沒有網路連線（缺少 NAT Gateway 或 Public IP）
# - Security Group 沒有開放對外連線
# - EFS Mount Target 不存在
```

#### 2. 無法連線到外部 API

**症狀**：同步失敗，Connection refused

**解決方案**：
- 確保 Subnet 有 NAT Gateway 或 assignPublicIp=ENABLED
- 檢查 Security Group outbound 規則

#### 3. EFS 掛載失敗

**症狀**：Task 啟動失敗，EFS mount error

**檢查步驟**：
```bash
# 確認 EFS Mount Target 存在
aws efs describe-mount-targets --file-system-id $EFS_ID

# 確認 Security Group 允許 NFS（port 2049）
aws ec2 describe-security-groups --group-ids sg-xxxxxxxx
```

#### 4. 記憶體不足

**症狀**：Task 突然停止，OOMKilled

**解決方案**：
增加 Task Definition 中的 memory 設定

---

## 成本估算

### Fargate 常駐（每月）

| 項目 | 規格 | 費用（USD） |
|------|------|------------|
| vCPU | 0.25 vCPU × 730 小時 | ~$7.50 |
| Memory | 0.5 GB × 730 小時 | ~$1.60 |
| EFS | 1 GB | ~$0.30 |
| **合計** | | **~$9.40** |

### Scheduled Tasks（每月）

| 項目 | 規格 | 費用（USD） |
|------|------|------------|
| sync-availability | 288 次/天 × 30 天 × 1 分鐘 | ~$2.50 |
| sync-parking | 30 次/月 × 2 分鐘 | ~$0.05 |
| EFS | 1 GB | ~$0.30 |
| EventBridge | 免費額度內 | $0 |
| **合計** | | **~$2.85** |

> 以上為 ap-northeast-1 區域估算，實際費用依使用量而定。

---

## 檔案結構

```
parking-newtaipei/
├── aws/
│   └── ecs/
│       ├── Dockerfile.scheduled          # Scheduled Tasks 專用 Dockerfile
│       ├── task-definition-fargate.json  # Fargate 常駐 Task Definition
│       ├── task-definition-scheduled.json # Scheduled Tasks Task Definition
│       └── eventbridge-rules.json        # EventBridge 規則範例
├── docs/
│   ├── AWS_ECS_DEPLOYMENT.md             # 本文件
│   └── DOCKER_DEPLOYMENT.md              # Docker 部署文件
├── Dockerfile                             # 原有 Dockerfile（含 cron）
└── docker-compose.yml
```
