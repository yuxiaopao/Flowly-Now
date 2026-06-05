# Docker 部署指南

## 前置条件

- Docker 24+
- Docker Compose v2+
- 至少 4GB RAM

## 快速启动

### 1. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填写所有必填配置项（带 `⚠️` 标记）。

### 2. 启动所有服务

```bash
docker compose up -d
```

这将启动以下服务：

| 服务 | 端口 | 说明 |
|------|------|------|
| `db` | 3306 | MySQL 主数据库 |
| `pgvector` | 5432 | PostgreSQL 向量数据库 |
| `redis` | 6379 | Redis 缓存和消息队列 |
| `backend` | 8000 | Django API |
| `frontend` | 5173 | Vue 前端 (开发模式) |
| `nginx` | 80 | 反向代理 |

### 3. 初始化数据库

```bash
# 运行迁移
docker compose exec backend python manage.py migrate

# 创建管理员账户
docker compose exec backend python manage.py createsuperuser

# 收集静态文件
docker compose exec backend python manage.py collectstatic --noinput
```

## 服务管理

### 查看日志

```bash
# 所有服务
docker compose logs -f

# 单个服务
docker compose logs -f backend
docker compose logs -f frontend
```

### 重启服务

```bash
docker compose restart backend
```

### 停止服务

```bash
docker compose down
```

### 重新构建

```bash
docker compose up -d --build
```

## 生产部署

### 1. 构建镜像

```bash
docker build -f docker/Dockerfile.backend -t flowly-backend .
docker build -f docker/Dockerfile.frontend -t flowly-frontend .
```

### 2. 生产环境变量

生产环境必须设置以下环境变量：

```bash
# 必填
DJANGO_SECRET_KEY=<使用 secrets.token_urlsafe(50) 生成>
DEBUG=false
ALLOWED_HOSTS=<你的域名>
CORS_ALLOWED_ORIGINS=<前端域名>
DB_PASSWORD=<强密码>
PG_PASSWORD=<强密码>

# 可选
CELERY_WORKERS=4
REDIS_MAX_CONNECTIONS=100
```

### 3. 健康检查

```bash
curl http://localhost:8000/api/health/
```

预期响应：
```json
{
  "status": "healthy",
  "service": "flowly-backend",
  "version": "1.0.0"
}
```

## Docker Compose 配置说明

| 服务 | 镜像 | 资源限制 |
|------|------|----------|
| backend | 自定义 | 2CPU, 2GB RAM |
| frontend | 自定义 | 1CPU, 512MB RAM |
| db | mysql:8.0 | 1CPU, 1GB RAM |
| pgvector | pgvector/pgvector:pg16 | 1CPU, 1GB RAM |
| redis | redis:7 | 256MB RAM |
| nginx | nginx:latest | 256MB RAM |

## 故障排除

### 数据库连接问题

```bash
# 检查数据库日志
docker compose logs db

# 手动运行迁移
docker compose exec backend python manage.py migrate --force
```

### 前端无法连接后端

检查 `nginx` 配置确保代理正确转发 `/api/` 请求到 `backend:8000`。

### 清理所有数据

```bash
docker compose down -v  # 删除所有卷（会丢失数据）
docker compose up -d
```
