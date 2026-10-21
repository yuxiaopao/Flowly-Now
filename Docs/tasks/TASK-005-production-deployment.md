# 任务 5：生产环境部署与运维

## 任务概述

| 属性 | 值 |
|------|-----|
| **任务名称** | 生产环境部署与运维 |
| **优先级** | P1 - 重要功能 |
| **预估工时** | 3-4 天 |
| **前置依赖** | 所有核心功能开发完成 |

## 任务目标

完成生产环境部署配置，建立运维监控体系。

## 详细需求

### 1.1 Docker 部署配置

#### 1.1.1 Docker Compose 配置

```yaml
# docker/docker-compose.yml

version: '3.8'

services:
  # ============== 数据库 ==============
  db:
    image: mysql:8.0
    container_name: flowly-mysql
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_ROOT_PASSWORD}
      MYSQL_DATABASE: ${DB_NAME}
      MYSQL_USER: ${DB_USER}
      MYSQL_PASSWORD: ${DB_PASSWORD}
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
      - ./mysql/conf.d:/etc/mysql/conf.d
      - ./mysql/init:/docker-entrypoint-initdb.d
    command:
      - --character-set-server=utf8mb4
      - --collation-server=utf8mb4_unicode_ci
      - --default-authentication-plugin=mysql_native_password
    networks:
      - flowly-network
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ============== Redis ==============
  redis:
    image: redis:7-alpine
    container_name: flowly-redis
    restart: always
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
      - ./redis/redis.conf:/usr/local/etc/redis/redis.conf
    networks:
      - flowly-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ============== 后端 ==============
  backend:
    build:
      context: ../Backend
      dockerfile: ../docker/Dockerfile.backend
    container_name: flowly-backend
    restart: always
    environment:
      - DB_HOST=db
      - DB_NAME=${DB_NAME}
      - DB_USER=${DB_USER}
      - DB_PASSWORD=${DB_PASSWORD}
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_PASSWORD=${REDIS_PASSWORD}
      - SECRET_KEY=${SECRET_KEY}
      - DEBUG=False
      - ALLOWED_HOSTS=${ALLOWED_HOSTS}
      - CORS_ALLOWED_ORIGINS=${CORS_ALLOWED_ORIGINS}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    ports:
      - "8000:8000"
    volumes:
      - ../Backend:/app
      - media_data:/app/media
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - flowly-network
    command: >
      sh -c "python manage.py migrate &&
             python manage.py collectstatic --noinput &&
             gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4 --threads 2"

  # ============== Celery Worker ==============
  celery:
    build:
      context: ../Backend
      dockerfile: ../docker/Dockerfile.backend
    container_name: flowly-celery
    restart: always
    command: celery -A config worker -l info
    environment:
      - DB_HOST=db
      - DB_NAME=${DB_NAME}
      - DB_USER=${DB_USER}
      - DB_PASSWORD=${DB_PASSWORD}
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_PASSWORD=${REDIS_PASSWORD}
    volumes:
      - ../Backend:/app
    depends_on:
      - backend
    networks:
      - flowly-network

  # ============== Celery Beat (定时任务) ==============
  celery-beat:
    build:
      context: ../Backend
      dockerfile: ../docker/Dockerfile.backend
    container_name: flowly-celery-beat
    restart: always
    command: celery -A config beat -l info
    environment:
      - DB_HOST=db
      - DB_NAME=${DB_NAME}
      - DB_USER=${DB_USER}
      - DB_PASSWORD=${DB_PASSWORD}
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_PASSWORD=${REDIS_PASSWORD}
    volumes:
      - ../Backend:/app
    depends_on:
      - celery
    networks:
      - flowly-network

  # ============== 前端 ==============
  frontend:
    build:
      context: ../Frontend
      dockerfile: ../docker/Dockerfile.frontend
    container_name: flowly-frontend
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/html:/usr/share/nginx/html
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - backend
    networks:
      - flowly-network

  # ============== Nginx ==============
  nginx:
    image: nginx:alpine
    container_name: flowly-nginx
    restart: always
    ports:
      - "8080:8080"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d
      - ./nginx/ssl:/etc/nginx/ssl
      - nginx_logs:/var/log/nginx
    depends_on:
      - backend
      - frontend
    networks:
      - flowly-network

  # ============== 向量数据库 (可选) ==============
  qdrant:
    image: qdrant/qdrant:latest
    container_name: flowly-qdrant
    restart: always
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    networks:
      - flowly-network

  # ============== Prometheus ==============
  prometheus:
    image: prom/prometheus:latest
    container_name: flowly-prometheus
    restart: always
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - flowly-network

  # ============== Grafana ==============
  grafana:
    image: grafana/grafana:latest
    container_name: flowly-grafana
    restart: always
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=${GRAFANA_USER}
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
    depends_on:
      - prometheus
    networks:
      - flowly-network

# ============== 网络和卷 ==============
networks:
  flowly-network:
    driver: bridge

volumes:
  mysql_data:
  redis_data:
  media_data:
  qdrant_data:
  prometheus_data:
  grafana_data:
  nginx_logs:
```

#### 1.1.2 后端 Dockerfile

```dockerfile
# docker/Dockerfile.backend

FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    libmariadb-dev \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 设置 Python 环境
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 复制依赖文件
COPY Backend/requirements.txt /app/

# 安装 Python 依赖
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 复制应用代码
COPY Backend /app/

# 创建 media 目录
RUN mkdir -p /app/media

# 收集静态文件
RUN python manage.py collectstatic --noinput || true

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
```

#### 1.1.3 前端 Dockerfile

```dockerfile
# docker/Dockerfile.frontend

FROM node:20-alpine as builder

WORKDIR /app

# 复制 package 文件
COPY Frontend/package*.json ./

# 安装依赖
RUN npm ci

# 复制源代码
COPY Frontend ./

# 构建生产版本
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# Nginx 生产镜像
FROM nginx:alpine

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 Nginx 配置
COPY docker/nginx/conf.d/default.conf /etc/nginx/conf.d/

# 暴露端口
EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
```

### 1.2 Nginx 配置

#### 1.2.1 主配置文件

```nginx
# docker/nginx/conf.d/default.conf

upstream backend {
    server backend:8000;
}

server {
    listen 80;
    server_name _;
    
    # 重定向到 HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name _;
    
    # SSL 证书
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    # SSL 配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    
    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # 前端静态文件
    root /usr/share/nginx/html;
    index index.html;
    
    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/json application/xml;
    
    # 前端路由
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # API 代理
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # WebSocket 代理
    location /ws/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }
    
    # 媒体文件
    location /media/ {
        proxy_pass http://backend;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # 静态文件
    location /static/ {
        proxy_pass http://backend;
        expires 7d;
        add_header Cache-Control "public";
    }
    
    # 日志
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;
}

# 上游服务器配置
upstream backend {
    server backend:8000 max_fails=3 fail_timeout=30s;
    keepalive 32;
}
```

### 1.3 环境变量配置

#### 1.3.1 环境变量文件

```bash
# .env.production

# ============== 数据库 ==============
DB_NAME=flowly_db
DB_USER=flowly_user
DB_PASSWORD=your_secure_db_password
DB_ROOT_PASSWORD=your_secure_root_password
DB_HOST=db
DB_PORT=3306

# ============== Redis ==============
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=your_secure_redis_password
REDIS_URL=redis://:${REDIS_PASSWORD}@${REDIS_HOST}:${REDIS_PORT}/0

# ============== Django ==============
SECRET_KEY=your_very_long_and_secure_secret_key_here
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# ============== CORS ==============
CORS_ALLOWED_ORIGINS=https://your-domain.com,https://app.your-domain.com

# ============== API Keys ==============
OPENAI_API_KEY=<your-openai-api-key>
ANTHROPIC_API_KEY=<your-anthropic-api-key>

# ============== 向量数据库 ==============
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_URL=http://${QDRANT_HOST}:${QDRANT_PORT}

# ============== 监控 ==============
GRAFANA_USER=admin
GRAFANA_PASSWORD=your_secure_grafana_password

# ============== 邮件 ==============
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=noreply@your-domain.com
EMAIL_HOST_PASSWORD=your_email_password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=noreply@your-domain.com
```

### 1.4 监控配置

#### 1.4.1 Prometheus 配置

```yaml
# docker/prometheus/prometheus.yml

global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets: []

rule_files:
  - /etc/prometheus/rules/*.yml

scrape_configs:
  # Prometheus 自身
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Django 应用
  - job_name: 'flowly-backend'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['backend:8000']
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
        regex: '(.+):\d+'
        replacement: '${1}'

  # Nginx
  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx:8080']

  # Redis
  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

  # MySQL (需要 exporter)
  - job_name: 'mysql'
    static_configs:
      - targets: ['mysql-exporter:9104']
```

#### 1.4.2 告警规则

```yaml
# docker/prometheus/rules/flowly-alerts.yml

groups:
  - name: flowly_alerts
    rules:
      # 高错误率告警
      - alert: HighErrorRate
        expr: |
          rate(http_requests_total{status=~"5.."}[5m]) / 
          rate(http_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "高错误率告警"
          description: "错误率超过 5%，当前值: {{ $value | humanizePercentage }}"

      # 服务不可用告警
      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "服务不可用"
          description: "{{ $labels.job }} 服务已停止运行"

      # 响应时间过长
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "响应时间过长"
          description: "95% 响应时间超过 2 秒，当前值: {{ $value }}s"

      # 内存使用率高
      - alert: HighMemoryUsage
        expr: |
          (container_memory_usage_bytes / container_spec_memory_limit_bytes) > 0.85
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "内存使用率过高"
          description: "内存使用率超过 85%，当前值: {{ $value | humanizePercentage }}"

      # CPU 使用率高
      - alert: HighCPUUsage
        expr: rate(container_cpu_usage_seconds_total[5m]) > 0.8
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "CPU 使用率过高"
          description: "CPU 使用率超过 80%"

      # 数据库连接池耗尽
      - alert: DatabaseConnectionPoolExhausted
        expr: |
          django_db_pool_connections_available / 
          django_db_pool_connections_max < 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "数据库连接池即将耗尽"
          description: "可用连接数不足 10%"

      # Celery 任务积压
      - alert: CeleryTaskBacklog
        expr: |
          rabbitmq_queue_messages > 1000
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Celery 任务积压"
          description: "队列中有 {{ $value }} 个任务等待处理"

      # 执行失败率
      - alert: WorkflowExecutionFailures
        expr: |
          rate(workflow_executions_total{status="failed"}[1h]) /
          rate(workflow_executions_total[1h]) > 0.1
        for: 30m
        labels:
          severity: warning
        annotations:
          summary: "工作流执行失败率过高"
          description: "过去 1 小时内执行失败率超过 10%"
```

### 1.5 数据库备份策略

#### 1.5.1 备份脚本

```bash
#!/bin/bash
# scripts/backup.sh

set -e

# 配置
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_HOST="${DB_HOST:-db}"
DB_NAME="${DB_NAME}"
DB_USER="${DB_USER}"
DB_PASSWORD="${DB_PASSWORD}"
RETENTION_DAYS=30

# 创建备份目录
mkdir -p ${BACKUP_DIR}

# 备份数据库
echo "开始备份数据库: ${DB_NAME}"
mysqldump \
    -h ${DB_HOST} \
    -u ${DB_USER} \
    -p${DB_PASSWORD} \
    --single-transaction \
    --routines \
    --triggers \
    --events \
    --hex-blob \
    ${DB_NAME} | gzip > ${BACKUP_DIR}/db_${DB_NAME}_${DATE}.sql.gz

# 备份媒体文件
echo "开始备份媒体文件"
tar -czf ${BACKUP_DIR}/media_${DATE}.tar.gz -C /app/media .

# 上传到 S3 (可选)
if [ -n "${S3_BUCKET}" ]; then
    echo "上传到 S3"
    aws s3 cp ${BACKUP_DIR}/db_${DB_NAME}_${DATE}.sql.gz s3://${S3_BUCKET}/backups/
    aws s3 cp ${BACKUP_DIR}/media_${DATE}.tar.gz s3://${S3_BUCKET}/backups/
fi

# 清理旧备份
echo "清理超过 ${RETENTION_DAYS} 天的备份"
find ${BACKUP_DIR} -name "*.sql.gz" -mtime +${RETENTION_DAYS} -delete
find ${BACKUP_DIR} -name "*.tar.gz" -mtime +${RETENTION_DAYS} -delete

# 验证备份
echo "验证备份"
gunzip -t ${BACKUP_DIR}/db_${DB_NAME}_${DATE}.sql.gz && echo "备份成功"

echo "备份完成: ${DATE}"
```

#### 1.5.2 恢复脚本

```bash
#!/bin/bash
# scripts/restore.sh

set -e

if [ -z "$1" ]; then
    echo "用法: $0 <backup_file>"
    echo "示例: $0 /backups/db_flowly_20240501_120000.sql.gz"
    exit 1
fi

BACKUP_FILE=$1
DB_HOST="${DB_HOST:-db}"
DB_NAME="${DB_NAME}"
DB_USER="${DB_USER}"
DB_PASSWORD="${DB_PASSWORD}"

echo "警告: 即将恢复数据库 ${DB_NAME}"
echo "按 Ctrl+C 取消，或等待 5 秒继续..."
sleep 5

# 恢复数据库
gunzip -c ${BACKUP_FILE} | mysql \
    -h ${DB_HOST} \
    -u ${DB_USER} \
    -p${DB_PASSWORD} \
    ${DB_NAME}

echo "数据库恢复完成"
```

### 1.6 系统维护脚本

#### 1.6.1 日志清理脚本

```bash
#!/bin/bash
# scripts/cleanup.sh

set -e

# 配置
LOG_DIR="/var/log"
MAX_SIZE_MB=1000
DAYS_TO_KEEP=30

echo "开始日志清理..."

# 清理 Django 日志
find ${LOG_DIR} -name "*.log" -mtime +${DAYS_TO_KEEP} -delete

# 压缩旧日志
find ${LOG_DIR} -name "*.log" -mtime +7 ! -name "*.gz" -exec gzip {} \;

# 清理 Nginx 日志
if [ -d "/var/log/nginx" ]; then
    # 轮转日志
    /usr/sbin/logrotate -f /etc/logrotate.conf
fi

# 清理 Python 缓存
find /app -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find /app -type f -name "*.pyc" -delete

# 清理 Node 缓存
npm cache clean --force 2>/dev/null || true

echo "日志清理完成"
```

### 1.7 健康检查

#### 1.7.1 健康检查端点

```python
# Backend/core/views/health_views.py

from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from rest_framework.decorators import api_view
from rest_framework.response import Response


def health_check(request):
    """健康检查端点"""
    return JsonResponse({'status': 'healthy'})


def detailed_health_check(request):
    """详细健康检查"""
    health = {
        'status': 'healthy',
        'checks': {}
    }
    
    # 数据库检查
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        health['checks']['database'] = 'healthy'
    except Exception as e:
        health['checks']['database'] = f'unhealthy: {str(e)}'
        health['status'] = 'unhealthy'
    
    # Redis 检查
    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') == 'ok':
            health['checks']['redis'] = 'healthy'
        else:
            health['checks']['redis'] = 'unhealthy'
    except Exception as e:
        health['checks']['redis'] = f'unhealthy: {str(e)}'
        health['status'] = 'unhealthy'
    
    # Celery 检查
    try:
        from django_celery_results.models import TaskResult
        recent_count = TaskResult.objects.filter(
            date_created__gte=timezone.now() - timezone.timedelta(minutes=5)
        ).count()
        health['checks']['celery'] = 'healthy'
    except Exception as e:
        health['checks']['celery'] = f'unhealthy: {str(e)}'
        # Celery 失败不影响整体状态
        health['checks']['celery'] = 'degraded'
    
    status_code = 200 if health['status'] == 'healthy' else 503
    return JsonResponse(health, status=status_code)


def readiness_check(request):
    """就绪检查"""
    try:
        # 检查所有依赖
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        
        cache.get('health_check')
        
        return JsonResponse({'ready': True})
    except Exception as e:
        return JsonResponse({'ready': False, 'error': str(e)}, status=503)


def liveness_check(request):
    """存活检查"""
    return JsonResponse({'alive': True})
```

## 验收标准

- [ ] Docker Compose 配置完成
- [ ] 前后端 Dockerfile 编写完成
- [ ] Nginx 反向代理配置完成
- [ ] SSL 证书配置完成
- [ ] 环境变量配置规范
- [ ] Prometheus 监控配置完成
- [ ] Grafana 仪表板配置
- [ ] 告警规则配置
- [ ] 数据库备份脚本
- [ ] 日志清理脚本
- [ ] 健康检查端点

## 关键文件清单

| 文件路径 | 说明 |
|---------|------|
| `docker/docker-compose.yml` | Docker Compose 配置 |
| `docker/Dockerfile.backend` | 后端镜像 |
| `docker/Dockerfile.frontend` | 前端镜像 |
| `docker/nginx/conf.d/default.conf` | Nginx 配置 |
| `docker/prometheus/prometheus.yml` | Prometheus 配置 |
| `docker/prometheus/rules/flowly-alerts.yml` | 告警规则 |
| `scripts/backup.sh` | 备份脚本 |
| `scripts/restore.sh` | 恢复脚本 |
| `scripts/cleanup.sh` | 清理脚本 |
| `Backend/core/views/health_views.py` | 健康检查 |
