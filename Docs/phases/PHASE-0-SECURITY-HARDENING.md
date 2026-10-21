# Phase 0: 安全加固详细方案

> 文档版本: 1.0  
> 创建日期: 2026-06-03  
> 适用范围: Flowly-now 全栈项目 (Django + Vue 3)

---

## 一、安全问题清单（优先级 P0）

### 1.1 [P0-CRITICAL] SECRET_KEY 硬编码风险

**现状**:
```python
# Backend/config/settings.py 第22行
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-flowly-dev-key-change-in-production')
```

**风险**: 
- 当前生产环境 fallback 到不安全的默认值 `django-insecure-flowly-dev-key-change-in-production`
- 若环境变量未正确配置，攻击者可利用此密钥伪造会话、CSRF token
- 风险等级: **严重 (Critical)**

**整改方案**:
1. **移除不安全的 fallback**:
   - 修改 `settings.py` 第22行，删除默认值 fallback
   - 使 `DJANGO_SECRET_KEY` 成为必需环境变量

2. **更新 .env.example** (第10行):
   ```
   # 修改前
   SECRET_KEY=your-secret-key-here-change-in-production
   
   # 修改后
   DJANGO_SECRET_KEY=your-super-secret-key-generate-with-python-secrets
   ```

3. **添加启动验证** - 在 `settings.py` 底部添加:
   ```python
   # 安全检查: 确保生产环境必须设置 SECRET_KEY
   if not DEBUG:
       secret_key = os.getenv('DJANGO_SECRET_KEY')
       if not secret_key or 'change-in-production' in secret_key.lower():
           raise ValueError(
               "DJANGO_SECRET_KEY must be set and not contain default values in production!"
           )
   ```

4. **Docker Compose 安全强化**:
   - `docker-compose.yml` 第75行使用 `DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}` 
   - 确保 `.env` 文件包含强密钥（至少50字符随机字符串）
   - 添加注释警告禁止使用默认值

**涉及文件**:
- `Backend/config/settings.py` (第22行)
- `.env.example` (第10行)
- `docker-compose.yml` (第75行)

**验收标准**:
- [ ] 生产环境启动时若 `DJANGO_SECRET_KEY` 未设置或包含 "insecure"/"change-in-production" 则抛出异常
- [ ] `.env.example` 中的 SECRET_KEY 示例为占位符，不含实际密钥
- [ ] `docker-compose.yml` 中的 backend 服务正确引用环境变量

---

### 1.2 [P0-HIGH] DEBUG 模式默认开启

**现状**:
```python
# Backend/config/settings.py 第25行
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')
```

**风险**:
- 默认 `DEBUG=True` 会泄露详细错误堆栈、数据库查询信息
- 生产环境误部署将导致敏感信息泄露
- 风险等级: **高 (High)**

**整改方案**:
1. 修改默认值:
   ```python
   # 修改前
   DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')
   
   # 修改后
   DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')
   ```

2. 在 `.env.example` 中明确标注:
   ```
   # 生产环境必须设置为 false
   DEBUG=false
   ```

3. 添加生产环境强制检查 (settings.py):
   ```python
   if not DEBUG:
       # 禁用 Django 调试面板和详细错误
       import django.views.debug
       debug.technical_500_response = lambda *a, **kw: None
   ```

**涉及文件**:
- `Backend/config/settings.py` (第25行)
- `.env.example`

**验收标准**:
- [ ] 默认 `DEBUG=False`
- [ ] 生产环境部署文档明确说明必须设置 `DEBUG=false`

---

### 1.3 [P0-HIGH] 数据库密码弱默认配置

**现状**:
```yaml
# docker-compose.yml 第31-34行 (MySQL)
MYSQL_ROOT_PASSWORD: <local-database-password>
MYSQL_PASSWORD: flowly_password

# .env.example 第15行
DB_PASSWORD=<local-database-password>
```

**风险**:
- 使用常见弱密码 `<local-database-password>`, `flowly_password`
- 若容器端口暴露，攻击者可直连数据库
- 风险等级: **高 (High)**

**整改方案**:
1. **docker-compose.yml**:
   - 移除硬编码密码，改用环境变量
   - 添加安全警告注释

2. **.env.example**:
   ```bash
   # 修改前
   DB_PASSWORD=<local-database-password>
   
   # 修改后
   DB_PASSWORD=<your-strong-database-password-min-16-chars>
   ```

3. **PostgreSQL (pgvector) 密码** (docker-compose.yml 第11行):
   ```yaml
   POSTGRES_PASSWORD: ${PG_PASSWORD:-change-me-in-production}
   ```

**涉及文件**:
- `docker-compose.yml` (第11, 31-34行)
- `.env.example` (第15, 23行)

**验收标准**:
- [ ] 所有数据库密码改为必需环境变量
- [ ] `.env.example` 不包含任何真实密码
- [ ] 部署文档包含密码生成指南

---

### 1.4 [P0-HIGH] CORS 配置过于宽松

**现状**:
```python
# Backend/config/settings.py 第313-316行
CORS_ALLOWED_ORIGINS = os.getenv(
    'CORS_ALLOWED_ORIGINS',
    CORS_DEFAULT_ORIGINS
).split(',')
```

```python
# Backend/config/constants.py (推断)
CORS_DEFAULT_ORIGINS = 'localhost,127.0.0.1'  # 默认允许本地开发
```

**风险**:
- 若环境变量未设置，`CORS_ALLOWED_ORIGINS` 为 `'localhost,127.0.0.1'`
- 生产环境若未配置 CORS，浏览器同源策略可能阻止正常请求
- 或配置为 `*` 导致任意域可访问 API
- 风险等级: **高 (High)**

**整改方案**:
1. **添加 CORS 验证** (settings.py):
   ```python
   CORS_ALLOWED_ORIGINS = os.getenv(
       'CORS_ALLOWED_ORIGINS',
       ''
   ).split(',')
   
   # 生产环境必须明确配置 CORS
   if not DEBUG and not CORS_ALLOWED_ORIGINS:
       raise ValueError(
           "CORS_ALLOWED_ORIGINS must be set in production!"
       )
   
   # 过滤空字符串
   CORS_ALLOWED_ORIGINS = [o.strip() for o in CORS_ALLOWED_ORIGINS if o.strip()]
   ```

2. **禁用 CORS_ALLOW_CREDENTIALS 与通配符** (settings.py 第318行):
   ```python
   CORS_ALLOW_CREDENTIALS = True  # 保持，但需确保 ORIGINS 严格配置
   ```

3. **添加预检请求优化**:
   ```python
   CORS_PREFLIGHT_MAX_AGE = 3600  # 缓存预检请求1小时
   ```

4. **更新 .env.example**:
   ```
   # 生产环境示例
   CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
   ```

**涉及文件**:
- `Backend/config/settings.py` (第313-327行)
- `.env.example` (第29行)

**验收标准**:
- [ ] 生产环境未配置 CORS_ORIGINS 时启动失败
- [ ] `CORS_ALLOWED_ORIGINS` 不包含 `*` 或空值

---

### 1.5 [P1-MEDIUM] 公开端点权限配置

**现状** (已分析全部 views.py):

| 模块 | 端点 | 当前权限 | 风险 |
|------|------|----------|------|
| `core/views/health_views.py` | `/api/health/`, `/api/ping/` | `AllowAny` | 低 - 健康检查 |
| `dataset_recommend/views.py` | `/api/datasets/recommend/` | `AllowAny` | 中 - 公开数据 |
| `templates/views.py` | `/api/templates/`, `/api/categories/` | `AllowAny` | 低 - 模板浏览 |
| `marketplace/views.py` | `/api/marketplace/` | `AllowAny` | 中 - 市场数据 |
| `users/views.py` | `/register/`, `/login/`, `/password-reset/` | `AllowAny` | 低 - 认证端点 |
| `integrations/views.py` | Webhook 回调 | `AllowAny` | **高 - 需验证签名** |

**风险评估**:
- 大部分 `AllowAny` 是合理的公开端点
- Webhook 端点缺少签名验证机制
- 风险等级: **中 (Medium)**

**整改方案**:
1. **Webhook 签名验证** (integrations/views.py):
   ```python
   @permission_classes([AllowAny])  # Webhook 需要公开访问
   class WebhookView(APIView):
       def post(self, request):
           # 验证 Webhook 签名
           signature = request.headers.get('X-Webhook-Signature')
           if not verify_webhook_signature(request.data, signature):
               return Response({'error': 'Invalid signature'}, status=401)
           # 处理 webhook...
   ```

2. **添加 IP 白名单** (可选):
   ```python
   # settings.py
   WEBHOOK_ALLOWED_IPS = os.getenv('WEBHOOK_ALLOWED_IPS', '').split(',')
   ```

**涉及文件**:
- `Backend/integrations/views.py` (第140行)

**验收标准**:
- [ ] Webhook 端点实现签名验证
- [ ] 公开端点无敏感数据泄露

---

### 1.6 [P1-MEDIUM] Serializer 输入验证缺失

**现状** (分析 `Backend/workflows/serializers.py`):

| Serializer | 问题字段 | 当前状态 | 风险 |
|------------|----------|----------|------|
| `WorkflowCreateSerializer` | `name` | 无 `max_length` | 中 - 可输入超长字符串 |
| `WorkflowCreateSerializer` | `description` | 无长度限制 | 中 - DoS 风险 |
| `WorkflowCreateSerializer` | `tags` | `default=list` | 中 - 数组大小无限制 |
| `WorkflowCreateSerializer` | `config` | `default=dict` | 中 - JSON 大小无限制 |
| `NodeCreateSerializer` | `name` | 无 `max_length` | 中 |
| `NodeCreateSerializer` | `description` | 无长度限制 | 中 |
| `EdgeCreateSerializer` | `label` | 无长度限制 | 低 |
| `WorkflowExecutionSerializer` | `input_data` | `JSONField` 无限制 | **高 - DoS** |
| `WorkflowExecutionSerializer` | `output_data` | `JSONField` 无限制 | **高 - DoS** |
| `APICredentialSerializer` | `credential_data` | `write_only=True` ✓ | 低 |
| `VariableSerializer` | `default_value` | 无长度限制 | 中 |

**风险分析**:
- 攻击者可提交超大 JSON payload 导致内存耗尽
- 超长字符串可触发数据库索引问题
- 风险等级: **中 (Medium)**

**整改方案**:
1. **WorkflowCreateSerializer**:
   ```python
   class WorkflowCreateSerializer(serializers.ModelSerializer):
       nodes = serializers.JSONField(required=False, default=list)
       edges = serializers.JSONField(required=False, default=list)
       
       class Meta:
           model = Workflow
           fields = ['id', 'name', 'description', ...]
       
       def validate_name(self, value):
           if len(value) > 200:
               raise serializers.ValidationError("名称不能超过200字符")
           return value.strip()
       
       def validate_description(self, value):
           if value and len(value) > 5000:
               raise serializers.ValidationError("描述不能超过5000字符")
           return value
       
       def validate_nodes(self, value):
           if value and len(str(value)) > 1024 * 1024:  # 1MB
               raise serializers.ValidationError("节点数据过大")
           if value and len(value) > 500:
               raise serializers.ValidationError("节点数量不能超过500")
           return value
   ```

2. **WorkflowExecuteSerializer** (高优先级):
   ```python
   class WorkflowExecuteSerializer(serializers.Serializer):
       input_data = serializers.JSONField(default=dict)
       MAX_INPUT_SIZE = 100 * 1024  # 100KB
       
       def validate_input_data(self, value):
           if value and len(str(value)) > self.MAX_INPUT_SIZE:
               raise serializers.ValidationError(
                   f"输入数据不能超过 {self.MAX_INPUT_SIZE // 1024}KB"
               )
           return value
   ```

3. **全局请求大小限制** (settings.py):
   ```python
   # Data Upload Limits
   DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
   DATA_UPLOAD_MAX_FORM_FIELD_SIZE = 10 * 1024 * 1024  # 10MB
   ```

**涉及文件**:
- `Backend/workflows/serializers.py` (多处)
- `Backend/config/settings.py`

**验收标准**:
- [ ] 所有字符串字段有 `max_length` 限制
- [ ] JSONField 有大小限制
- [ ] `DATA_UPLOAD_MAX_MEMORY_SIZE` 已配置

---

### 1.7 [P2-LOW] 审计日志事件不完整

**现状** (分析 `Backend/workflows/models.py` 第1253-1364行):

| 事件类型 | 当前状态 | 缺失项 |
|----------|----------|--------|
| `create` | ✓ 已支持 | - |
| `update` | ✓ 已支持 | - |
| `delete` | ✓ 已支持 | - |
| `execute` | ✓ 已支持 | - |
| `login` | ⚠ 需集成 | 需在 auth 流程中调用 |
| `logout` | ⚠ 需集成 | 需在 auth 流程中调用 |
| `login_failure` | ✗ 未实现 | 需记录失败登录 |
| `access` | ✗ 未实现 | 需记录数据访问 |
| `export` | ✗ 未实现 | 需记录导出操作 |
| `share` | ✗ 未实现 | 需记录分享操作 |
| `permission_change` | ✗ 未实现 | 需记录权限变更 |
| `credential_access` | ✗ 未实现 | 需记录敏感凭证访问 |

**AuditLog 模型分析**:
```python
# Backend/workflows/models.py 第1253行
class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('create', '创建'),
        ('update', '更新'),
        ('delete', '删除'),
        ('execute', '执行'),
        ('login', '登录'),
        ('logout', '登出'),
        ('access', '访问'),
        ('export', '导出'),
        ('import', '导入'),
        ('share', '分享'),
        ('revoke', '撤销'),
    ]
```

**缺失功能**:
1. **登录失败日志** - `LoginView` 未记录失败尝试
2. **数据访问日志** - 敏感数据读取时未记录
3. **凭证访问日志** - API 凭证使用/查看时未记录

**整改方案**:
1. **添加登录失败日志** (`users/views.py`):
   ```python
   class LoginView(APIView):
       permission_classes = [AllowAny]
       
       def post(self, request):
           serializer = LoginSerializer(data=request.data, ...)
           if not serializer.is_valid():
               # 记录登录失败
               AuditLog.log(
                   user=None,
                   action='login_failure',
                   resource_type='user',
                   request=request,
                   status='failure',
                   error_message=str(serializer.errors)
               )
               return Response(serializer.errors, status=401)
           # ... 成功登录处理
   ```

2. **添加中间件自动日志** (`Backend/config/middleware.py`):
   ```python
   class AuditLogMiddleware:
       def __init__(self, get_response):
           self.get_response = get_response
       
       def __call__(self, request):
           response = self.get_response(request)
           
           # 仅记录敏感路径
           if request.path.startswith('/api/'):
               if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
                   self._log_action(request, response)
           
           return response
       
       def _log_action(self, request, response):
           # 从 response 获取被修改的资源信息
           # 调用 AuditLog.log()
   ```

3. **扩展 ACTION_CHOICES** (models.py):
   ```python
   ACTION_CHOICES = [
       # ... 现有选项
       ('login_failure', '登录失败'),      # 新增
       ('credential_access', '凭证访问'),   # 新增
       ('permission_change', '权限变更'),  # 新增
       ('api_call', 'API调用'),            # 新增
   ]
   ```

**涉及文件**:
- `Backend/users/views.py`
- `Backend/workflows/models.py`
- 新建 `Backend/config/middleware.py`

**验收标准**:
- [ ] 登录失败事件已记录
- [ ] 登录成功事件已记录
- [ ] 敏感操作有审计日志
- [ ] 审计日志不可篡改

---

### 1.8 [P2-LOW] API 限流配置需强化

**现状** (settings.py 第301-309行):
```python
'DEFAULT_THROTTLE_RATES': {
    'anon': RATE_LIMIT_ANON,        # 来自 constants.py
    'user': RATE_LIMIT_USER,
    'workflow_execute': RATE_LIMIT_WORKFLOW_EXECUTE,
}
```

**问题**:
- 需要确认 constants.py 中的限流值
- 生产环境可能需要更严格的限流
- 缺少登录尝试限流

**整改方案**:
1. **添加登录限流**:
   ```python
   # settings.py
   REST_FRAMEWORK = {
       # ...
       'DEFAULT_THROTTLE_CLASSES': [
           'rest_framework.throttling.AnonRateThrottle',
           'rest_framework.throttling.UserRateThrottle',
           'workflows.throttling.WorkflowExecuteThrottle',  # 已有
       ],
       'DEFAULT_THROTTLE_RATES': {
           'anon': '60/minute',        # 匿名用户 60次/分钟
           'user': '300/minute',       # 认证用户 300次/分钟
           'login': '5/minute',        # 登录尝试 5次/分钟 (新增)
           'workflow_execute': '30/hour',
       },
   }
   ```

2. **应用登录限流** (`users/views.py`):
   ```python
   from rest_framework.throttling import ScopedRateThrottle
   
   class LoginView(APIView):
       permission_classes = [AllowAny]
       throttle_classes = [ScopedRateThrottle]
       throttle_scope = 'login'  # 5/minute
   ```

**涉及文件**:
- `Backend/config/settings.py`
- `Backend/users/views.py`

**验收标准**:
- [ ] 登录端点有独立限流
- [ ] 限流值在 .env 中可配置

---

## 二、执行检查清单

### Phase 0 完成标准

| 序号 | 检查项 | 状态 | 备注 |
|------|--------|------|------|
| 1 | SECRET_KEY 必须从环境变量读取，无默认值 | ⬜ | |
| 2 | DEBUG 默认值为 False | ⬜ | |
| 3 | 数据库密码使用强密码占位符 | ⬜ | |
| 4 | CORS 在生产环境必须配置 | ⬜ | |
| 5 | 所有 Serializer 有输入长度验证 | ⬜ | |
| 6 | 登录失败事件记录到审计日志 | ⬜ | |
| 7 | API 限流覆盖所有端点 | ⬜ | |
| 8 | .env.example 不包含真实密码 | ⬜ | |
| 9 | 生产部署文档包含安全配置指南 | ⬜ | |
| 10 | 所有硬编码密钥已移除 | ⬜ | |

---

## 三、代码变更示例

### 3.1 settings.py 安全强化

```python
# === SECRET_KEY 安全配置 (第22行) ===
# 修改前:
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-flowly-dev-key-change-in-production')

# 修改后:
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-dev-only-do-not-use-in-production'
    else:
        raise ValueError("DJANGO_SECRET_KEY environment variable must be set in production!")

# === DEBUG 默认值修改 (第25行) ===
# 修改前:
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')

# 修改后:
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')

# === CORS 配置强化 (第313-316行) ===
# 修改前:
CORS_ALLOWED_ORIGINS = os.getenv(
    'CORS_ALLOWED_ORIGINS',
    CORS_DEFAULT_ORIGINS
).split(',')

# 修改后:
_cors_origins = os.getenv('CORS_ALLOWED_ORIGINS', '')
if not _cors_origins and not DEBUG:
    raise ValueError("CORS_ALLOWED_ORIGINS must be set in production!")
CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_origins.split(',') if o.strip()]
CORS_ALLOW_CREDENTIALS = True
CORS_PREFLIGHT_MAX_AGE = 3600

# === 添加请求大小限制 ===
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_FORM_FIELD_SIZE = 10 * 1024 * 1024  # 10MB
```

### 3.2 .env.example 安全更新

```bash
# === 应用配置 ===
APP_NAME=Flowly
APP_ENV=development
# ⚠️ 生产环境必须设置为 false
DEBUG=false

# ⚠️ 必填: 使用 python -c "import secrets; print(secrets.token_urlsafe(50))" 生成
DJANGO_SECRET_KEY=your-super-secret-key-generate-with-secrets-module

# === 主数据库配置 (MySQL) ===
# ⚠️ 必填: 使用强密码，最少16字符
DB_NAME=flowly_db
DB_USER=root
DB_PASSWORD=<your-strong-password-min-16-chars>
DB_HOST=localhost
DB_PORT=3307

# === 向量数据库配置 (PostgreSQL) ===
# ⚠️ 必填
PG_NAME=flowly_vector
PG_USER=flowly
PG_PASSWORD=<your-strong-pg-password>
PG_HOST=localhost
PG_PORT=5432

# === CORS 配置 ===
# ⚠️ 生产环境必填，逗号分隔多个域名
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# === API 限流配置 (可选) ===
RATE_LIMIT_ANON=60/minute
RATE_LIMIT_USER=300/minute
RATE_LIMIT_WORKFLOW_EXECUTE=30/hour
```

### 3.3 docker-compose.yml 安全更新

```yaml
services:
  db:
    image: mysql:8.0
    environment:
      # ⚠️ 生产环境必须在 .env 中设置
      MYSQL_ROOT_PASSWORD: ${DB_ROOT_PASSWORD:?DB_ROOT_PASSWORD must be set}
      MYSQL_DATABASE: ${DB_NAME:-flowly_db}
      MYSQL_USER: ${DB_USER:-flowly}
      # 使用占位符密码，生产环境必须替换
      MYSQL_PASSWORD: ${DB_PASSWORD:-change-me-in-production}

  pgvector:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: ${PG_USER:-flowly}
      # ⚠️ 生产环境必须在 .env 中设置
      POSTGRES_PASSWORD: ${PG_PASSWORD:?PG_PASSWORD must be set}
      POSTGRES_DB: ${PG_NAME:-flowly_vector}
```

---

## 四、后续 Phase 计划参考

| Phase | 内容 | 优先级 |
|-------|------|--------|
| Phase 1 | 用户认证与授权强化 | P0 |
| Phase 2 | API 网关安全 | P1 |
| Phase 3 | 数据加密与脱敏 | P1 |
| Phase 4 | 安全监控与告警 | P2 |
| Phase 5 | 渗透测试与漏洞修复 | P2 |

---

## 五、参考资料

- [Django Security Documentation](https://docs.djangoproject.com/en/stable/topics/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [DRF Security Best Practices](https://www.django-rest-framework.org/topics/security/)
- [CORS Best Practices](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
