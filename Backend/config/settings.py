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
)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv(BASE_DIR / '.env')

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
    'users',
    'core',
    'workflows',
    'datasets',
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

# ─────────────────────────────────────────────────────────────────
# Jazzmin Admin Theme Configuration
# 美化 Django Admin 界面
# ─────────────────────────────────────────────────────────────────
JAZZMIN_SETTINGS = {
    # 顶部品牌栏
    "site_brand": "e-Flowly 管理系统",
    "site_logo": "admin/img/logo.svg",
    "site_logo_width": 40,

    # 登录页
    "login_logo": "admin/img/logo.svg",
    "login_logo_height": 60,

    # 标题与页脚
    "site_header": "e-Flowly Admin",
    "site_title": "e-Flowly 管理系统",
    "copyright": "e-Flowly © 2024-2026",

    # 顶部导航栏
    "topmenu_links": [
        {"name": "控制台", "url": "/admin/", "icon": "fas fa-cogs"},
        {"name": "API 文档", "url": "/api/docs/", "new_window": True, "icon": "fas fa-book"},
        {"name": "前台首页", "url": "/", "new_window": True, "icon": "fas fa-home"},
    ],

    # 用户菜单（右上角）
    "user_menu": {
        "title": "用户",
        "links": [
            {"name": "个人资料", "url": "/admin/auth/user/{user_id}/change/", "icon": "fas fa-user"},
            {"name": "修改密码", "url": "/admin/auth/user/{user_id}/password/", "icon": "fas fa-key"},
        ],
    },

    # 侧边栏
    "show_sidebar": True,
    "navigation_expanded": True,

    # 变更列表视图
    "order_with_respect_to": [
        "workflows.Workflow",
        "workflows.Node",
        "workflows.Edge",
    ],

    # 主题色配置
    "ui_theme": "default",
    "show_ui_builder": True,
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
        "blue": "#3498db",
        "light-blue": "#3bee17",
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

    # 自定义 CSS
    "custom_css": "admin/css/custom_admin.css",

    # 自定义 JS
    "custom_js": "admin/js/custom_admin.js",
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_colour": "navbar-info",
    "accent_colour": "accent-warning",
    "logo_colour": "navbar-dark",
    "sidebar_nav_compact_style": False,
    "sidebar_nav_flat_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_child_indent": True,
    "admin_title": "e-Flowly 管理系统",
    "welcome_sign": "欢迎使用 e-Flowly 智能工作流平台",
}

# ─────────────────────────────────────────────────────────────────
# 自定义 Admin Site 配置
# ─────────────────────────────────────────────────────────────────
ADMIN_SITE_HEADER = "e-Flowly 管理系统"
ADMIN_SITE_TITLE = "e-Flowly Admin"
ADMIN_INDEX_TITLE = "欢迎来到 e-Flowly 管理控制台"

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

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'users.User'

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
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
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
        'workflow_execute': RATE_LIMIT_WORKFLOW_EXECUTE,
    },
}

# =============================================================================
# CORS configuration
# =============================================================================
# SECURITY: CORS_ALLOWED_ORIGINS must be explicitly configured - no default fallback in production.
_CORS_ORIGINS_RAW = os.getenv('CORS_ALLOWED_ORIGINS', '')
CORS_ALLOWED_ORIGINS = [o.strip() for o in _CORS_ORIGINS_RAW.split(',') if o.strip()]
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

# OpenAI API configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')

# Anthropic API configuration
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')

# Ollama (local LLM) configuration
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen2.5-coder:7b')

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
NL_WORKFLOW_MODEL = os.getenv('NL_WORKFLOW_MODEL', 'qwen2.5-coder:7b')
NL_WORKFLOW_TEMPERATURE = float(os.getenv('NL_WORKFLOW_TEMPERATURE', '0.7'))

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
