# Docker 部署指南

本机开发的 API/Worker/Beat 启停、分项就绪检查及进程归属保护见 [本地服务生命周期](local-services.md)。该入口不会清空队列，也不会自动执行业务数据库迁移。

## 前置条件

- Docker 24+
- Docker Compose v2+
- 至少 4GB RAM

## 快速启动

### 1. 配置环境变量

```bash
cp Backend/.env.example Backend/.env
```

编辑 `Backend/.env` 文件，填写数据库凭据和 `DJANGO_SECRET_KEY`。当前 Compose 复用宿主机的
MySQL（3307）、Redis（6379）和 pgvector（5433）；这些基础服务需要先启动。

### 2. 启动所有服务

```bash
docker compose up -d
```

当前仓库的 `docker-compose.yml` 定义以下应用服务：

| 服务 | 端口 | 说明 |
|------|------|------|
| `backend` | 8000 | Django API |
| `celery` | 无宿主机端口 | 异步任务 worker |
| `frontend` | 5200 | Nginx 托管生产前端并代理 API/WebSocket |

首次启动前，在仓库根目录构建前端镜像：

```bash
docker build -f docker/Dockerfile.frontend -t flowly-now-frontend-fixed:latest .
```

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

生产使用独立的 `docker-compose.prod.yml`，不挂载后端源码；保留 API、Celery worker、Celery beat 和前端。
MySQL、Redis、pgvector、模型服务器由现有环境管理。`Backend/data`、`outputs`、`logs`、`backups`
继续使用原宿主目录；media/static 沿用原命名卷。容器之间共享训练配置、输出和模型，不会因 worker 重建丢失。

发布主机需要 Python 3.10+、Docker 和支持 `up --wait` 的 Compose v2.18+，并能拉取应用镜像。
从旧环境迁移时，Compose project name 必须与旧服务相同，才能复用原 media/static 卷；
CI 默认 `flowly-now`，可通过 `STAGING_COMPOSE_PROJECT` / `PRODUCTION_COMPOSE_PROJECT` 仓库变量配置。
同一主机上的 staging 和 production 应使用各自已有的 project name 和数据目录。

### 1. 构建镜像

```bash
docker build -f docker/Dockerfile.backend -t flowly-backend .
docker build -f docker/Dockerfile.frontend -t flowly-frontend .
```

两个 Dockerfile 都以仓库根目录为构建上下文。根 `.dockerignore` 排除本地环境变量、虚拟环境、
node_modules 和模型权重，生产前端通过构建参数传入 `VITE_API_URL` / `VITE_WS_URL`。
后端镜像与本地安装共享 `Backend/requirements.txt`；CPU wheel 版本在后端 Dockerfile 中固定，
可选本地模型扩展位于 `Backend/requirements-local-models.txt`，不会自动替换宿主机 CUDA 环境。

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

容器内部健康检查从 `ALLOWED_HOSTS` 取一个实际允许的 Host，也可在运行环境中设置 `HEALTHCHECK_HOST`。
容器和发布脚本都只接受 HTTP 2xx；重定向不会被当作健康成功。

### 4. 按本次构建 digest 发布与应用回滚

CI 仅在 `develop` 发布 staging、`main` 发布 production，沿用既有的 `ENV_STAGING` / `ENV_PRODUCTION`
及主机、账号、SSH key、部署路径和 URL secrets。两个镜像的 digest 直接来自本次 build 输出，
不会从可变的 `staging` 标签重新打包或重标记。review 后的脚本、Compose 和私有运行配置经 SCP 传到原部署目录。

手动执行同一入口时，使用本次构建的不可变镜像引用：

```bash
python3 docker/deploy_release.py \
  --backend-image "$BACKEND_IMAGE_REF" \
  --frontend-image "$FRONTEND_IMAGE_REF" \
  --env-file /path/to/runtime.env \
  --release-id "$RELEASE_ID" \
  --project-name flowly-now \
  --health-url "$HEALTH_URL"
```

`BACKEND_IMAGE_REF` / `FRONTEND_IMAGE_REF` 必须是 `仓库@sha256:完整摘要`。脚本先拉取镜像，
执行正向迁移和 collectstatic，再仅启动应用服务并检查健康。`.flowly-deploy/` 私有目录记录每版镜像、
环境文件和 Compose 副本，后续上传不会覆盖上一版快照。

首次接管已有但尚无发布记录的服务，必须同时传入旧运行环境和旧 Compose：

```bash
# 追加到上面的首次发布命令；路径应指向当前实际运行的旧配置。
--adopt-env-file /path/to/current.env --adopt-compose-file /path/to/current-compose.yml
```

CI 对应的可选仓库变量是 `STAGING_ADOPT_ENV_FILE` / `STAGING_ADOPT_COMPOSE_FILE` 和 production 同名变量。
接管时保存完整已解析的旧拓扑，将旧服务 literal image 标签替换为实际运行/缓存的 image ID，
保留旧挂载、命令和环境。没有这些信息时会在迁移前停止发布。

迁移、启动或健康检查失败，会恢复上一版应用镜像、环境和 Compose；新引入的应用 beat 等会停止。
回滚不重建旧拓扑中的数据库/Redis，不使用 `down -v` 或清理持久卷。首次无旧服务的失败只停止新应用服务。
显式应用回滚使用已记录的上一版：

```bash
python3 docker/deploy_release.py --rollback --project-name flowly-now --health-url "$HEALTH_URL"
```

数据库迁移不会自动逆转，发布迁移需兼容上一版应用；数据库数据恢复应使用对应备份流程。
不要清理当前和上一版仍需使用的本地 image ID。`.flowly-deploy/` 和临时部署包均已排除出 Git 与 Docker 上下文。

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
