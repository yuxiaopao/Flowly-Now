# 本地开发指南

## 环境要求

| 软件 | 版本 | 说明 |
|------|------|------|
| Python | 3.12+ | 推荐使用 pyenv 或 conda |
| Node.js | 20+ | 前端构建 |
| MySQL | 8.0+ | 主数据库 (端口 3306) |
| PostgreSQL | 16+ | 向量数据库 (端口 5432) |
| Redis | 7+ | 缓存和消息队列 |

## 快速启动

### 1. 克隆项目

```bash
git clone <repo-url>
cd Flowly-now
```

### 2. 环境变量配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env，填入必要配置
# 必须配置: DJANGO_SECRET_KEY, DB_PASSWORD, PG_PASSWORD
```

### 3. 后端启动

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 数据库迁移
cd Backend
python manage.py migrate

# 运行开发服务器
python manage.py runserver
```

### 4. 前端启动

```bash
cd Frontend
npm install
npm run dev
```

### 5. Redis 启动 (可选，用于异步任务)

```bash
# macOS
brew services start redis

# Ubuntu
sudo systemctl start redis-server

# Windows (使用 Docker)
docker run -d -p 6379:6379 redis:7
```

## 开发模式

### 前端热重载

前端使用 Vite 开发服务器，支持热模块替换 (HMR)。

```
http://localhost:5173
```

### 后端热重载

Django 开发服务器已开启 auto-reload，修改 Python 代码会自动重启。

### 数据库

```bash
# 创建超级用户
python manage.py createsuperuser

# 访问 Django Admin
# http://localhost:8000/admin/
```

## 常见问题

### 1. 数据库连接失败

确保 MySQL 服务运行中，且 `.env` 中 `DB_HOST` 和 `DB_PORT` 配置正确。

### 2. 依赖安装失败

```bash
# mysqlclient 依赖
# Ubuntu/Debian:
sudo apt install python3-dev default-libmysqlclient-dev pkg-config

# macOS:
brew install mysql-client
export PATH="/opt/homebrew/opt/mysql-client/bin:$PATH"
```

### 3. 前端构建失败

```bash
cd Frontend
rm -rf node_modules package-lock.json
npm install
```
