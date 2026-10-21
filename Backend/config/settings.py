"""
Django settings for Flowly project.
"""

import re
from pathlib import Path
import os
from dotenv import load_dotenv

from config.constants import (
    PAGE_SIZE_DEFAULT, PAGE_SIZE_MAX, CURSOR_PAGE_SIZE, CURSOR_PAGE_SIZE_MAX,
    RATE_LIMIT_ANON, RATE_LIMIT_USER, RATE_LIMIT_WORKFLOW_EXECUTE,
    RATE_LIMIT_LOGIN,
    CELERY_TASK_TIME_LIMIT,
    DATA_UPLOAD_MAX_MEMORY_SIZE,
    DATA_UPLOAD_MAX_FORM_FIELD_SIZE,
    OLLAMA_NUM_CTX as DEFAULT_OLLAMA_NUM_CTX,
    DEFAULT_OLLAMA_EMBEDDING_MODEL,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_LLM_MODEL,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
)
from admin.constants import (
    PLATFORM_ADMIN_COPYRIGHT,
    PLATFORM_ADMIN_HEADER,
    PLATFORM_ADMIN_INDEX_TITLE,
    PLATFORM_ADMIN_PANEL_TITLE,
    PLATFORM_ADMIN_TITLE,
    PLATFORM_ADMIN_WELCOME_SIGN,
)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv(BASE_DIR / '.env')

# Explicit hostnames only, for operator-approved self-hosted integration endpoints.
INTEGRATIONS_HTTP_PROXY = os.getenv('INTEGRATIONS_HTTP_PROXY', '').strip()
INTEGRATIONS_ALLOWED_PRIVATE_HOSTS = tuple(
    host.strip().lower() for host in os.getenv('INTEGRATIONS_ALLOWED_PRIVATE_HOSTS', '').split(',') if host.strip()
)

# =============================================================================
# SECURITY WARNING: keep the secret key used in production secret!
# =============================================================================
# SECURITY: SECRET_KEY must be set via DJANGO_SECRET_KEY environment variable.
# No insecure default fallback - production MUST provide a real key.
_DJANGO_SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', '')
if _DJANGO_SECRET_KEY:
    SECRET_KEY = _DJANGO_SECRET_KEY
else:
    if os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes'):
        SECRET_KEY = 'django-insecure-dev-only-do-not-use-in-production'
    else:
        raise ValueError(
            "DJANGO_SECRET_KEY environment variable must be set in production! "
            "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(50))\""
        )

# =============================================================================
# SECURITY WARNING: don't run with debug turned on in production!
# =============================================================================
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')

# SECURITY: Enforce DEBUG=False in production
if not DEBUG:
    import django.views.debug
    django.views.debug.technical_500_response = lambda *a, **kw: None

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')
ALLOWED_HOSTS = [h.strip() for h in ALLOWED_HOSTS if h.strip()]
# SECURITY: Require explicit ALLOWED_HOSTS in production
if not DEBUG and not ALLOWED_HOSTS:
    raise ValueError("ALLOWED_HOSTS must be set in production!")

# ─── Admin / Session 安全（Django Admin 独立入口 :8000/admin/） ───
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 86400 if DEBUG else 28800  # 生产环境 Admin 会话 8 小时
SESSION_SAVE_EVERY_REQUEST = not DEBUG
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# =============================================================================
# Data Upload Security Limits
# =============================================================================
DATA_UPLOAD_MAX_MEMORY_SIZE = DATA_UPLOAD_MAX_MEMORY_SIZE
DATA_UPLOAD_MAX_FORM_FIELD_SIZE = DATA_UPLOAD_MAX_FORM_FIELD_SIZE
FILE_UPLOAD_MAX_HANDLERS = 100

# Application definition
INSTALLED_APPS = [
    'daphne',
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'channels',
    'drf_spectacular',
    # Local apps
    'datasets',   # must be before core/augmentation due to cross-app FK lazy refs
    'users',
    'core',
    'workflows',
    'agents',
    'nl_to_workflow',
    'prompts',
    'tenants',
    'monitoring',
    'rag',
    'gateway',
    'billing',
    'integrations',
    'branding',
    'marketplace',
    'templates',
    'admin',
    'dataset_recommend',
    'annotations',
    'augmentation',
    'training',
    'website_generator',
    'evaluation',
    'features',
    'codegraph',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'admin.context_processors.flowly_admin',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME', 'flowly'),
        'USER': os.getenv('DB_USER', 'root'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

# 用户端 Frontend URL（Admin 外链、模板 {{ frontend_url }}）
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5200').rstrip('/')
# 对外暴露的后端 API 根地址（Webhook/SSE/前端运行时配置）
PUBLIC_API_BASE_URL = os.getenv('PUBLIC_API_BASE_URL', 'http://127.0.0.1:8000').rstrip('/')
# WebSocket 根地址（空则 runtime_config 从 PUBLIC_API_BASE_URL 推导）
PUBLIC_WS_URL = os.getenv('PUBLIC_WS_URL', '').strip()
LOGIN_URL = '/admin/login/'
LOGIN_REDIRECT_URL = '/admin/'

# ─────────────────────────────────────────────────────────────────
# Jazzmin Admin Theme Configuration
# 美化 Django Admin 界面
# ─────────────────────────────────────────────────────────────────
JAZZMIN_SETTINGS = {
    # 顶部品牌栏
    "site_brand": PLATFORM_ADMIN_TITLE,
    "site_logo": "admin/img/logo.png",
    "site_logo_width": 120,
    "site_logo_classes": "brand-image elevation-3",

    # 登录页
    "login_logo": "admin/img/logo.png",
    "login_logo_height": 72,
    "site_icon": "admin/img/logo.png",

    # 标题与页脚
    "site_header": PLATFORM_ADMIN_HEADER,
    "site_title": PLATFORM_ADMIN_TITLE,
    "copyright": PLATFORM_ADMIN_COPYRIGHT,

    # 顶部导航栏（Flowly Tab 栏已承担主导航，此处仅保留外链）
    "topmenu_links": [
        {"name": "API 文档", "url": "/api/docs/", "new_window": True, "icon": "fas fa-book"},
        {"name": "用户端", "url": f"{FRONTEND_URL}/", "new_window": True, "icon": "fas fa-external-link-alt"},
    ],

    # 侧边栏自定义链接（Tab 已覆盖的入口不再重复；仅保留配置中心快捷链）
    "custom_links": {
        "admin": [{
            "name": "平台配置中心",
            "url": "/admin/flowly/settings/",
            "icon": "fas fa-cogs",
            "permissions": ["auth.view_user"],
        }],
    },

    # 模型图标
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.group": "fas fa-users",
        "workflows": "fas fa-project-diagram",
        "workflows.workflow": "fas fa-sitemap",
        "workflows.workflowexecution": "fas fa-play-circle",
        "workflows.node": "fas fa-circle-nodes",
        "workflows.edge": "fas fa-link",
        "gateway": "fas fa-brain",
        "gateway.modelprovider": "fas fa-cloud",
        "gateway.aimodel": "fas fa-microchip",
        "agents": "fas fa-robot",
        "agents.agent": "fas fa-robot",
        "users": "fas fa-user-shield",
        "users.user": "fas fa-user",
        "admin": "fas fa-cogs",
        "admin.systemsetting": "fas fa-sliders-h",
        "core": "fas fa-database",
        "datasets": "fas fa-table",
        "tenants": "fas fa-building",
    },

    # 用户菜单（右上角）
    "user_menu": {
        "title": "用户",
        "links": [
            {"name": "个人资料", "url": "/admin/auth/user/{user_id}/change/", "icon": "fas fa-user"},
            {"name": "修改密码", "url": "/admin/auth/user/{user_id}/password/", "icon": "fas fa-key"},
        ],
    },

    # 侧边栏（False = 按应用分组，可独立展开/收起子菜单）
    "show_sidebar": True,
    "navigation_expanded": False,

    # 变更列表视图
    "order_with_respect_to": [
        "workflows",
        "workflows.Workflow",
        "workflows.WorkflowExecution",
        "workflows.Node",
        "workflows.Edge",
        "agents",
        "agents.Agent",
        "users",
        "admin",
        "gateway",
        "features",
        "auth",
        "tenants",
        "datasets",
    ],

    # 主题色配置
    "ui_theme": "default",
    "show_ui_builder": False,
    "use_htmx": True,

    # 隐藏默认链接
    "hide_default_admin_menu": False,

    # 快捷方式
    "related_modal_active": True,
    "use_i18n": True,

    # 变更历史
    "changeform_format": "collapsed",
    "changeform_format_overrides": {
        "workflows.Workflow": "horizontal_table",
        "workflows.WorkflowExecution": "stacked",
    },

    # 颜色主题（可选）
    "colours": {
        "favourite": "#e74c3c",
        "maroon": "#e74c3c",
        "purple": "#9b59b6",
        "orange": "#f39c12",
        "blue": "#1d4ed8",
        "light-blue": "#2563eb",
        "green": "#27ae60",
        "red": "#c0392b",
        "dark-blue": "#2c3e50",
    },

    # 按钮样式
    "button_classes": {
        "primary": "btn-outline-primary",
        "secondary": "btn-outline-secondary",
        "info": "btn-outline-info",
        "success": "btn-outline-success",
        "warning": "btn-outline-warning",
        "danger": "btn-outline-danger",
    },

    # 自定义 CSS（tokens 通过 custom_admin @import 引入）
    "custom_css": "admin/css/custom_admin.css",

    # 自定义 JS
    "custom_js": "admin/js/custom_admin.js",
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_colour": "navbar-white",
    "accent_colour": "accent-primary",
    "logo_colour": "navbar-dark",
    "sidebar_nav_compact_style": False,
    "sidebar_nav_flat_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_child_indent": True,
    "admin_title": PLATFORM_ADMIN_TITLE,
    "welcome_sign": PLATFORM_ADMIN_WELCOME_SIGN,
}

# ─────────────────────────────────────────────────────────────────
# 自定义 Admin Site 配置
# ─────────────────────────────────────────────────────────────────
ADMIN_SITE_HEADER = PLATFORM_ADMIN_TITLE
ADMIN_SITE_TITLE = PLATFORM_ADMIN_HEADER
ADMIN_INDEX_TITLE = PLATFORM_ADMIN_INDEX_TITLE

# ─────────────────────────────────────────────────────────────────
# 静态文件
# ─────────────────────────────────────────────────────────────────
STATICFILES_DIRS = [
    BASE_DIR / 'static',
    BASE_DIR / 'admin_static',  # Jazzmin 自定义静态资源目录
]

# Jazzmin 默认会从 jazzmin 包的 static/jazzmin 目录提供资源


# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_PUBLIC_BASE_URL = os.getenv(
    'MEDIA_PUBLIC_BASE_URL',
    os.getenv('PUBLIC_API_BASE_URL', 'http://127.0.0.1:8000'),
).rstrip('/')

# Video translation / FFmpeg
FFMPEG_BINARY = os.getenv('FFMPEG_BINARY', 'ffmpeg')
FFPROBE_BINARY = os.getenv('FFPROBE_BINARY', 'ffprobe')
VIDEO_TRANSLATION_MAX_DURATION_SEC = int(os.getenv('VIDEO_TRANSLATION_MAX_DURATION_SEC', '300'))
VIDEO_TRANSLATION_MAX_FILE_MB = int(os.getenv('VIDEO_TRANSLATION_MAX_FILE_MB', '200'))
VIDEO_TRANSLATION_ASR_PROVIDER = os.getenv('VIDEO_TRANSLATION_ASR_PROVIDER', 'local_whisper').strip()
VIDEO_TRANSLATION_TTS_PROVIDER = os.getenv('VIDEO_TRANSLATION_TTS_PROVIDER', 'pyttsx3').strip()
VIDEO_TRANSLATION_LIP_SYNC_PROVIDER = os.getenv('VIDEO_TRANSLATION_LIP_SYNC_PROVIDER', 'ffmpeg').strip()
WHISPER_MODEL_SIZE = os.getenv('WHISPER_MODEL_SIZE', 'base').strip()
WHISPER_DEVICE = os.getenv('WHISPER_DEVICE', 'cpu').strip()
WHISPER_COMPUTE_TYPE = os.getenv('WHISPER_COMPUTE_TYPE', 'int8').strip()

# System backup output directory (admin panel data backup)
BACKUP_DIR = os.getenv('BACKUP_DIR', str(BASE_DIR / 'backups'))

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'users.User'
AUTH_ACCESS_TOKEN_SECONDS = int(os.getenv('AUTH_ACCESS_TOKEN_SECONDS', 86400))
AUTH_REFRESH_TOKEN_SECONDS = int(os.getenv('AUTH_REFRESH_TOKEN_SECONDS', 604800))
PASSWORD_RESET_TIMEOUT = int(os.getenv('PASSWORD_RESET_TIMEOUT', 86400))

# REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'users.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'config.pagination.StandardResultsSetPagination',
    'PAGE_SIZE': PAGE_SIZE_DEFAULT,
    'DEFAULT_RENDERER_CLASSES': [
        'config.renderers.UnifiedJSONRenderer',
    ],
    'EXCEPTION_HANDLER': 'config.exception_handlers.custom_exception_handler',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': RATE_LIMIT_ANON,
        'user': RATE_LIMIT_USER,
        'login': RATE_LIMIT_LOGIN,
        'password_reset': os.getenv('RATE_LIMIT_PASSWORD_RESET', '10/hour'),
        'workflow_execute': RATE_LIMIT_WORKFLOW_EXECUTE,
    },
}

# =============================================================================
# CORS configuration
# =============================================================================
# SECURITY: CORS_ALLOWED_ORIGINS must be explicitly configured - no default fallback in production.
_CORS_ORIGINS_RAW = os.getenv('CORS_ALLOWED_ORIGINS', '')
CORS_ALLOWED_ORIGINS = [o.strip() for o in _CORS_ORIGINS_RAW.split(',') if o.strip()]
# Development defaults when CORS_ALLOWED_ORIGINS is not configured
if DEBUG and not CORS_ALLOWED_ORIGINS:
    CORS_ALLOWED_ORIGINS = [
        'http://localhost:5200',
        'http://127.0.0.1:5200',
        'http://localhost:5173',
        'http://127.0.0.1:5173',
    ]
# SECURITY: Require explicit CORS origins in production
if not DEBUG and not CORS_ALLOWED_ORIGINS:
    raise ValueError(
        "CORS_ALLOWED_ORIGINS must be explicitly set in production! "
        "Example: CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com"
    )
# SECURITY: Reject wildcard origins in production
if not DEBUG and any('*' in origin for origin in CORS_ALLOWED_ORIGINS):
    raise ValueError("Wildcard CORS origin (*) is not allowed in production!")

CORS_ALLOW_CREDENTIALS = True
CORS_PREFLIGHT_MAX_AGE = 3600  # Cache preflight requests for 1 hour

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Channels configuration
try:
    import redis as redis_module
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [(os.getenv('REDIS_HOST', 'localhost'), os.getenv('REDIS_PORT', 6379))],
            },
        },
    }
except ImportError:
    CHANNEL_LAYERS = {}

# Celery configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = CELERY_TASK_TIME_LIMIT  # from config.constants
# Concurrent workflows: prefer prefork/threads with -c N (NOT --pool=solo).
# Prefetch=1 + acks_late keeps one task per slot and requeues on worker loss.
CELERY_WORKER_PREFETCH_MULTIPLIER = int(os.getenv('CELERY_WORKER_PREFETCH_MULTIPLIER', '1'))
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_CONCURRENCY = int(os.getenv('CELERY_WORKER_CONCURRENCY', '2'))

# Workflow execution control
WORKFLOW_MAX_CONCURRENT_PER_WORKFLOW = int(os.getenv('WORKFLOW_MAX_CONCURRENT_PER_WORKFLOW', '3'))
WORKFLOW_STALE_RUNNING_MINUTES = int(os.getenv('WORKFLOW_STALE_RUNNING_MINUTES', '45'))
WORKFLOW_HEARTBEAT_INTERVAL_SEC = float(os.getenv('WORKFLOW_HEARTBEAT_INTERVAL_SEC', '15'))

# Optional Celery Beat schedule (enable beat process to activate)
CELERY_BEAT_SCHEDULE = {
    'recover-stale-workflow-executions': {
        'task': 'workflows.tasks.recover_stale_executions_task',
        'schedule': 300.0,  # every 5 minutes
    },
}

# Redis cache (optional)
try:
    import django_redis
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': os.getenv('REDIS_CACHE_URL', 'redis://localhost:6379/1'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            }
        }
    }
except ImportError:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }

# OpenAI API configuration (also used for Volcengine Ark / Doubao OpenAI-compatible API)
OPENAI_API_KEY = (
    os.getenv('OPENAI_API_KEY')
    or os.getenv('VOLCENGINE_API_KEY')
    or os.getenv('ARK_API_KEY')
    or ''
).strip()
OPENAI_BASE_URL = (
    os.getenv('OPENAI_BASE_URL') or 'https://api.openai.com/v1'
).strip().rstrip('/')

# Anthropic API configuration
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')

# 阿里云百炼 DashScope 配置（多模态：文生图/文生视频/语音合成/语音识别 + LLM 兼容模式）
# DASHSCOPE_API_KEY 同时用于 REST 服务端点与 OpenAI 兼容端点鉴权
DASHSCOPE_API_KEY = os.getenv('DASHSCOPE_API_KEY', '').strip()
# DashScope 原生 REST API 根地址（文生图/文生视频/语音合成/语音识别等 AIGC 服务）
DASHSCOPE_BASE_URL = (
    os.getenv('DASHSCOPE_BASE_URL') or 'https://dashscope.aliyuncs.com/api/v1'
).strip().rstrip('/')
# DashScope OpenAI 兼容模式地址（用于 LLM 对话节点接入通义千问系列模型）
DASHSCOPE_COMPATIBLE_BASE_URL = (
    os.getenv('DASHSCOPE_COMPATIBLE_BASE_URL') or 'https://dashscope.aliyuncs.com/compatible-mode/v1'
).strip().rstrip('/')

# Agnes AI 多模态 API Hub（OpenAI 兼容：LLM / 文生图 / 文生视频）
AGNES_API_KEY = os.getenv('AGNES_API_KEY', '').strip()
AGNES_BASE_URL = (
    os.getenv('AGNES_BASE_URL') or 'https://apihub.agnes-ai.com/v1'
).strip().rstrip('/')

# Ollama (local LLM) configuration
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', DEFAULT_OLLAMA_MODEL)
DEFAULT_LLM_MODEL = os.getenv('DEFAULT_LLM_MODEL', DEFAULT_LLM_MODEL)
DEFAULT_EMBEDDING_MODEL = os.getenv('DEFAULT_EMBEDDING_MODEL', DEFAULT_EMBEDDING_MODEL)
DEFAULT_TEMPERATURE = float(os.getenv('DEFAULT_TEMPERATURE', str(DEFAULT_TEMPERATURE)))
DEFAULT_MAX_TOKENS = int(os.getenv('DEFAULT_MAX_TOKENS', str(DEFAULT_MAX_TOKENS)))
# Chat context window (tokens) requested from Ollama; capped by default to avoid
# exhausting host RAM with large-context models (see config/constants.py OLLAMA_NUM_CTX).
OLLAMA_NUM_CTX = int(os.getenv('OLLAMA_NUM_CTX', str(DEFAULT_OLLAMA_NUM_CTX)))
# Local embedding model served by Ollama, used as a RAG fallback when no OpenAI-compatible
# embeddings API key is configured (see rag/services.py EmbeddingService).
OLLAMA_EMBEDDING_MODEL = os.getenv('OLLAMA_EMBEDDING_MODEL', DEFAULT_OLLAMA_EMBEDDING_MODEL)

# RAG limits and optional separate embedding/chat endpoints. Secrets stay server-side.
from rag.constants import (
    DEFAULT_MAX_FILE_BYTES, DEFAULT_MAX_TEXT_CHARS, DEFAULT_MAX_QUERY_CHARS,
    DEFAULT_CONTEXT_CHARS, DEFAULT_REQUEST_TIMEOUT, DEFAULT_EMBEDDING_BATCH_SIZE,
    DEFAULT_CANDIDATE_LIMIT, DEFAULT_PROCESSING_LEASE_SECONDS,
)
RAG_MAX_FILE_BYTES = int(os.getenv('RAG_MAX_FILE_BYTES', str(DEFAULT_MAX_FILE_BYTES)))
RAG_MAX_TEXT_CHARS = int(os.getenv('RAG_MAX_TEXT_CHARS', str(DEFAULT_MAX_TEXT_CHARS)))
RAG_MAX_QUERY_CHARS = int(os.getenv('RAG_MAX_QUERY_CHARS', str(DEFAULT_MAX_QUERY_CHARS)))
RAG_CONTEXT_CHARS = int(os.getenv('RAG_CONTEXT_CHARS', str(DEFAULT_CONTEXT_CHARS)))
RAG_REQUEST_TIMEOUT = int(os.getenv('RAG_REQUEST_TIMEOUT', str(DEFAULT_REQUEST_TIMEOUT)))
RAG_PROCESSING_LEASE_SECONDS = int(os.getenv('RAG_PROCESSING_LEASE_SECONDS', str(DEFAULT_PROCESSING_LEASE_SECONDS)))
RAG_EMBEDDING_BATCH_SIZE = int(os.getenv('RAG_EMBEDDING_BATCH_SIZE', str(DEFAULT_EMBEDDING_BATCH_SIZE)))
RAG_CANDIDATE_LIMIT = int(os.getenv('RAG_CANDIDATE_LIMIT', str(DEFAULT_CANDIDATE_LIMIT)))
RAG_EMBEDDING_API_KEY = os.getenv('RAG_EMBEDDING_API_KEY', '').strip()
RAG_EMBEDDING_BASE_URL = os.getenv('RAG_EMBEDDING_BASE_URL', '').strip()
RAG_CHAT_MODEL = os.getenv('RAG_CHAT_MODEL', '').strip()
RAG_CHAT_API_KEY = os.getenv('RAG_CHAT_API_KEY', '').strip()
RAG_CHAT_BASE_URL = os.getenv('RAG_CHAT_BASE_URL', '').strip()
RAG_PINECONE_CLOUD = os.getenv('RAG_PINECONE_CLOUD', 'aws')
RAG_PINECONE_REGION = os.getenv('RAG_PINECONE_REGION', 'us-east-1')
RAG_WEAVIATE_GRPC_PORT = int(os.getenv('RAG_WEAVIATE_GRPC_PORT', '50051'))

# Z-Image-Turbo (local image generation) configuration
ZIMAGE_MODEL_ID = os.getenv('ZIMAGE_MODEL_ID', 'Tongyi-MAI/Z-Image-Turbo')
ZIMAGE_DEVICE = os.getenv('ZIMAGE_DEVICE', 'cuda')
ZIMAGE_DTYPE = os.getenv('ZIMAGE_DTYPE', 'auto')
ZIMAGE_ENABLE_CPU_OFFLOAD = os.getenv('ZIMAGE_ENABLE_CPU_OFFLOAD', 'true').lower() in ('true', '1', 'yes')
ZIMAGE_NUM_INFERENCE_STEPS = int(os.getenv('ZIMAGE_NUM_INFERENCE_STEPS', '9'))
ZIMAGE_GUIDANCE_SCALE = float(os.getenv('ZIMAGE_GUIDANCE_SCALE', '0.0'))
ZIMAGE_DEFAULT_WIDTH = int(os.getenv('ZIMAGE_DEFAULT_WIDTH', '1024'))
ZIMAGE_DEFAULT_HEIGHT = int(os.getenv('ZIMAGE_DEFAULT_HEIGHT', '1024'))

# NL-to-Workflow configuration
_NL_MODEL_DEFAULT = (
    os.getenv('NL_WORKFLOW_MODEL')
    or ('agnes-2.0-flash' if os.getenv('AGNES_API_KEY') else DEFAULT_OLLAMA_MODEL)
)
NL_WORKFLOW_MODEL = _NL_MODEL_DEFAULT
NL_WORKFLOW_TEMPERATURE = float(os.getenv('NL_WORKFLOW_TEMPERATURE', '0.7'))
# Pre-generation chat: lower token cap for faster first-token / completion
NL_CHAT_MAX_TOKENS = int(os.getenv('NL_CHAT_MAX_TOKENS', '512'))
NL_EDITOR_MAX_TOKENS = int(os.getenv('NL_EDITOR_MAX_TOKENS', '2048'))
NL_GENERATE_MAX_TOKENS = int(os.getenv('NL_GENERATE_MAX_TOKENS', '4096'))
# AI-first: LLM designs workflows. Domain graph templates are offline-only.
# NL_WORKFLOW_USE_TEMPLATES=true → force template builders (dev/offline).
# NL_WORKFLOW_TEMPLATE_FALLBACK=true → allow template after LLM failure (default off).
NL_WORKFLOW_USE_TEMPLATES = os.getenv('NL_WORKFLOW_USE_TEMPLATES', 'false').lower() in ('true', '1', 'yes')
NL_WORKFLOW_TEMPLATE_FALLBACK = os.getenv('NL_WORKFLOW_TEMPLATE_FALLBACK', 'false').lower() in ('true', '1', 'yes')
NL_WORKFLOW_GENERATE_RETRIES = int(os.getenv('NL_WORKFLOW_GENERATE_RETRIES', '2'))
NL_WORKFLOW_USE_LLM_INTENT = os.getenv('NL_WORKFLOW_USE_LLM_INTENT', 'true').lower() in ('true', '1', 'yes')
# P2: agent tool retrieval + async + chat summary
NL_WORKFLOW_USE_AGENT_CONTEXT = os.getenv('NL_WORKFLOW_USE_AGENT_CONTEXT', 'true').lower() in ('true', '1', 'yes')
NL_WORKFLOW_ASYNC_GENERATE = os.getenv('NL_WORKFLOW_ASYNC_GENERATE', 'false').lower() in ('true', '1', 'yes')
NL_WORKFLOW_USE_HUB_REACT_PROMPT = os.getenv('NL_WORKFLOW_USE_HUB_REACT_PROMPT', 'false').lower() in ('true', '1', 'yes')
# Soft RAG over imported n8n open-source workflows (training corpus for 语创)
NL_WORKFLOW_USE_N8N_CORPUS = os.getenv('NL_WORKFLOW_USE_N8N_CORPUS', 'true').lower() in ('true', '1', 'yes')
NL_WORKFLOW_N8N_CORPUS_LIMIT = int(os.getenv('NL_WORKFLOW_N8N_CORPUS_LIMIT', '3') or 3)
NL_WORKFLOW_N8N_CORPUS_PATH = os.getenv('NL_WORKFLOW_N8N_CORPUS_PATH', '')
NL_CHAT_SUMMARY_THRESHOLD = int(os.getenv('NL_CHAT_SUMMARY_THRESHOLD', '12'))
NL_CHAT_USE_SUMMARY = os.getenv('NL_CHAT_USE_SUMMARY', 'true').lower() in ('true', '1', 'yes')
# Project Agent / profiler: prefer LLM enrichment when any provider is configured
SITE_AGENT_PREFER_LLM = os.getenv('SITE_AGENT_PREFER_LLM', 'true').lower() in ('true', '1', 'yes')
SITE_AGENT_MODEL = os.getenv('SITE_AGENT_MODEL', '')  # empty → NL_WORKFLOW_MODEL

# ─────────────────────────────────────────────────────────────────
# Email (SMTP) Configuration
# These serve as FALLBACK defaults when a workflow's email node
# does not provide its own SMTP configuration.
# ─────────────────────────────────────────────────────────────────
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587') or 587)
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'true').lower() in ('true', '1', 'yes')
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', '') or 'noreply@flowly.local'
# Django's SMTP backend blocks indefinitely by default (EMAIL_TIMEOUT=None) if the
# SMTP server is unreachable (e.g. outbound port 25/465/587 blocked by the network),
# which would hang the invite-email HTTP request. Cap it so failures surface quickly.
EMAIL_TIMEOUT = int(os.getenv('EMAIL_TIMEOUT', '10'))

# No SMTP server configured (e.g. local dev) → fall back to the console backend
# so outgoing emails (password reset, team invitations, ...) are still visible
# in the server log instead of silently failing or raising exceptions.
EMAIL_BACKEND = os.getenv(
    'EMAIL_BACKEND',
    'django.core.mail.backends.smtp.EmailBackend' if EMAIL_HOST
    else 'django.core.mail.backends.console.EmailBackend'
)

# ─────────────────────────────────────────────────────────────────
# LangSmith Tracing Configuration
# For observability and debugging LLM calls
# Install: pip install langsmith
# ─────────────────────────────────────────────────────────────────
LANGCHAIN_TRACING_V2 = os.getenv('LANGCHAIN_TRACING_V2', 'false').lower() == 'true'
LANGSMITH_API_KEY = os.getenv('LANGSMITH_API_KEY', '')
LANGSMITH_PROJECT = os.getenv('LANGSMITH_PROJECT', 'flowly-default')
LANGSMITH_ENDPOINT = os.getenv('LANGSMITH_ENDPOINT', 'https://api.smith.langchain.com')
LANGSMITH_TIMEOUT = int(os.getenv('LANGSMITH_TIMEOUT', '60'))
LANGSMITH_RETRY_ATTEMPTS = int(os.getenv('LANGSMITH_RETRY_ATTEMPTS', '3'))
LANGSMITH_VERBOSE = os.getenv('LANGSMITH_VERBOSE', 'false').lower() == 'true'

# Set environment variables for LangChain
if LANGSMITH_API_KEY:
    import os
    os.environ.setdefault('LANGCHAIN_TRACING_V2', 'true')
    os.environ.setdefault('LANGCHAIN_API_KEY', LANGSMITH_API_KEY)
    os.environ.setdefault('LANGCHAIN_PROJECT', LANGSMITH_PROJECT)
    os.environ.setdefault('LANGCHAIN_ENDPOINT', LANGSMITH_ENDPOINT)

# ========== Docker Sandbox Configuration ==========
DOCKER_ENABLED = os.getenv('DOCKER_ENABLED', 'auto')  # 'true', 'false', or 'auto'
DOCKER_CODE_IMAGE = os.getenv('DOCKER_CODE_IMAGE', 'python:3.12-slim')
DOCKER_MEMORY_LIMIT = int(os.getenv('DOCKER_MEMORY_LIMIT', '256'))  # MB
DOCKER_CPU_LIMIT = float(os.getenv('DOCKER_CPU_LIMIT', '0.5'))
DOCKER_TIMEOUT = int(os.getenv('DOCKER_TIMEOUT', '60'))  # seconds
DOCKER_POOL_SIZE = int(os.getenv('DOCKER_POOL_SIZE', '3'))

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        # HTTP client INFO/DEBUG logs include complete webhook and Bot token URLs.
        'httpx': {'level': 'WARNING'},
        'httpcore': {'level': 'WARNING'},
        'django': {
            'handlers': ['console', 'file'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'celery': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'workflows.debug': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
