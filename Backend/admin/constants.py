"""
Admin app constants - default system settings and module definitions.
"""

# ─── 平台品牌（管理后台与用户端统一，禁止硬编码 e-Flowly） ───
PLATFORM_SITE_NAME = 'Flowly'
PLATFORM_SITE_TAGLINE = 'AI Agent 工作流编排平台'
PLATFORM_ADMIN_TITLE = 'Flowly 管理系统'
PLATFORM_ADMIN_HEADER = 'Flowly Admin'
PLATFORM_ADMIN_PANEL_TITLE = 'Flowly 管理后台'
PLATFORM_ADMIN_INDEX_TITLE = '欢迎来到 Flowly 管理控制台'
PLATFORM_ADMIN_COPYRIGHT = 'Flowly © 2024-2026'
PLATFORM_ADMIN_WELCOME_SIGN = '欢迎使用 Flowly 智能工作流平台'
PLATFORM_ADMIN_WELCOME_DESC = '欢迎使用 Flowly 智能工作流管理平台'

# 管理端静态 Logo
PLATFORM_ADMIN_LOGO = 'admin/img/logo.png'          # 侧栏/登录（深色背景上的主 Logo）
PLATFORM_ADMIN_LOGO_WHITE = 'admin/img/logow.png'   # 欢迎页 Hero（浅色图形）


def get_time_greeting(dt=None):
    """根据本地时区返回时段问候语。"""
    from django.utils import timezone

    local = timezone.localtime(dt or timezone.now())
    hour = local.hour
    if 5 <= hour < 12:
        return '早上好'
    if 12 <= hour < 18:
        return '下午好'
    return '晚上好'

# ─── 系统设置默认值 ───
DEFAULT_SYSTEM_SETTINGS = {
    # 1. 通用设置
    'site_name': 'Flowly',
    'site_description': 'AI Agent 工作流编排平台',
    'site_logo': '/static/admin/img/logo.png',
    'site_favicon': '',
    'contact_email': '',
    'contact_phone': '',
    'support_url': '',
    'footer_text': '',
    'default_locale': 'zh-CN',
    'default_timezone': 'Asia/Shanghai',
    # 2. 登录条款（开关）
    'require_terms_on_register': True,
    'require_terms_on_login': False,
    # 3. 功能开关（全局默认，细粒度见 SystemFeature）
    'enable_marketplace': True,
    'enable_nl_workflow': True,
    'enable_api_docs': True,
    # 4. 安全与认证
    'allow_registration': True,
    'email_verification': False,
    'password_min_length': 8,
    'password_require_uppercase': True,
    'password_require_lowercase': True,
    'password_require_digit': True,
    'password_require_special': False,
    'max_login_attempts': 5,
    'lockout_duration_minutes': 30,
    'session_timeout_minutes': 1440,
    'jwt_expiry_hours': 24,
    'require_2fa_for_admin': False,
    # 5. 用户默认值
    'default_role': 'user',
    'default_tenant_id': None,
    'default_execution_limit': 1000,
    'default_notification_enabled': True,
    # 6. 网关服务（全局默认）
    'gateway_default_rate_limit': 60,
    'gateway_enable_service_discovery': True,
    'gateway_request_timeout_seconds': 120,
    'gateway_enable_api_logging': True,
    # 7. 支付设置（全局）
    'payment_default_currency': 'CNY',
    'payment_enable_refunds': True,
    'payment_refund_window_days': 30,
    # 8. 邮件设置
    'smtp_host': '',
    'smtp_port': 587,
    'smtp_user': '',
    'smtp_password': '',
    'from_email': '',
    'from_name': 'Flowly',
    'use_tls': True,
    'email_queue_enabled': True,
    'email_retry_count': 3,
    # 9. 数据备份
    'backup_schedule_cron': '0 3 * * *',
    'backup_retention_days': 30,
    'backup_auto_enabled': False,
    'backup_include_media': True,
    # API 配置（保留兼容）
    'rate_limit_per_minute': 60,
    'max_tokens': 4096,
    'execution_timeout': 300,
    'enable_api_logging': True,
    'enable_cost_tracking': True,
}

# 模块 → 设置键映射
SETTING_MODULE_KEYS = {
    'general': [
        'site_name', 'site_description', 'site_logo', 'site_favicon',
        'contact_email', 'contact_phone', 'support_url', 'footer_text',
        'default_locale', 'default_timezone',
    ],
    'terms': [
        'require_terms_on_register', 'require_terms_on_login',
    ],
    'features': [
        'enable_marketplace', 'enable_nl_workflow', 'enable_api_docs',
    ],
    'security': [
        'allow_registration', 'email_verification',
        'password_min_length', 'password_require_uppercase',
        'password_require_lowercase', 'password_require_digit',
        'password_require_special', 'max_login_attempts',
        'lockout_duration_minutes', 'session_timeout_minutes',
        'jwt_expiry_hours', 'require_2fa_for_admin',
    ],
    'user_defaults': [
        'default_role', 'default_tenant_id', 'default_execution_limit',
        'default_notification_enabled',
    ],
    'gateway': [
        'gateway_default_rate_limit', 'gateway_enable_service_discovery',
        'gateway_request_timeout_seconds', 'gateway_enable_api_logging',
        'rate_limit_per_minute', 'max_tokens', 'execution_timeout',
        'enable_api_logging', 'enable_cost_tracking',
    ],
    'payment': [
        'payment_default_currency', 'payment_enable_refunds',
        'payment_refund_window_days',
    ],
    'email': [
        'smtp_host', 'smtp_port', 'smtp_user', 'smtp_password',
        'from_email', 'from_name', 'use_tls',
        'email_queue_enabled', 'email_retry_count',
    ],
    'backup': [
        'backup_schedule_cron', 'backup_retention_days',
        'backup_auto_enabled', 'backup_include_media',
    ],
}

SETTING_MODULE_LABELS = {
    'general': '通用设置',
    'terms': '登录条款',
    'features': '功能可见性规则',
    'security': '安全与认证',
    'user_defaults': '用户默认值',
    'gateway': '网关服务',
    'payment': '支付设置',
    'email': '邮件设置',
    'backup': '数据备份',
}

SETTING_FIELD_LABELS = {
    'site_name': '网站名称',
    'site_description': '网站描述',
    'site_logo': 'Logo URL',
    'site_favicon': 'Favicon URL',
    'contact_email': '联系邮箱',
    'contact_phone': '联系电话',
    'support_url': '支持链接',
    'footer_text': '页脚文案',
    'default_locale': '默认语言',
    'default_timezone': '默认时区',
    'require_terms_on_register': '注册需确认条款',
    'require_terms_on_login': '登录需确认条款',
    'enable_marketplace': '启用模板市场',
    'enable_nl_workflow': '启用自然语言工作流',
    'enable_api_docs': '启用 API 文档',
    'allow_registration': '允许注册',
    'email_verification': '邮箱验证',
    'password_min_length': '密码最小长度',
    'password_require_uppercase': '需大写字母',
    'password_require_lowercase': '需小写字母',
    'password_require_digit': '需数字',
    'password_require_special': '需特殊字符',
    'max_login_attempts': '最大登录失败次数',
    'lockout_duration_minutes': '锁定时长(分钟)',
    'session_timeout_minutes': '会话超时(分钟)',
    'jwt_expiry_hours': 'JWT 过期(小时)',
    'require_2fa_for_admin': '管理员需双因素认证',
    'default_role': '默认角色',
    'default_tenant_id': '默认租户 ID',
    'default_execution_limit': '默认执行限额',
    'default_notification_enabled': '默认开启通知',
    'gateway_default_rate_limit': '默认限流(次/分)',
    'gateway_enable_service_discovery': '启用服务发现',
    'gateway_request_timeout_seconds': '请求超时(秒)',
    'gateway_enable_api_logging': '启用网关日志',
    'payment_default_currency': '默认货币',
    'payment_enable_refunds': '允许退款',
    'payment_refund_window_days': '退款窗口(天)',
    'smtp_host': 'SMTP 主机',
    'smtp_port': 'SMTP 端口',
    'smtp_user': 'SMTP 用户名',
    'smtp_password': 'SMTP 密码',
    'from_email': '发件邮箱',
    'from_name': '发件人名称',
    'use_tls': '启用 TLS',
    'email_queue_enabled': '启用邮件队列',
    'email_retry_count': '重试次数',
    'backup_schedule_cron': '备份计划(Cron)',
    'backup_retention_days': '保留天数',
    'backup_auto_enabled': '自动备份',
    'backup_include_media': '包含媒体文件',
    'rate_limit_per_minute': 'API 限流(次/分)',
    'max_tokens': '最大 Token',
    'execution_timeout': '执行超时(秒)',
    'enable_api_logging': 'API 日志',
    'enable_cost_tracking': '成本追踪',
}

BOOLEAN_SETTING_KEYS = {
    key for key, value in DEFAULT_SYSTEM_SETTINGS.items() if isinstance(value, bool)
}

INTEGER_SETTING_KEYS = {
    key for key, value in DEFAULT_SYSTEM_SETTINGS.items()
    if isinstance(value, int) and not isinstance(value, bool)
}

# 备份类型
BACKUP_TYPE_FULL = 'full'
BACKUP_TYPE_DATABASE = 'database'
BACKUP_TYPE_FILES = 'files'
BACKUP_TYPES = (BACKUP_TYPE_FULL, BACKUP_TYPE_DATABASE, BACKUP_TYPE_FILES)

BACKUP_DUMPDATA_EXCLUDES = (
    'contenttypes',
    'auth.permission',
    'sessions',
    'admin.logentry',
)

USER_ROLE_CHOICES = ('admin', 'developer', 'user')

PUBLIC_CONFIG_CACHE_KEY = 'flowly:public_site_config'
PUBLIC_CONFIG_CACHE_TTL = 60

# Flowly 自定义面板 — 顶部浏览器式 Tab 导航
FLOWLY_ADMIN_TABS = [
    {'id': 'welcome', 'label': '欢迎', 'url': '/admin/', 'icon': 'fas fa-home'},
    {'id': 'dashboard', 'label': '控制台', 'url': '/admin/flowly/', 'icon': 'fas fa-chart-line'},
    {'id': 'settings', 'label': '配置中心', 'url': '/admin/flowly/settings/', 'icon': 'fas fa-cogs'},
    {'id': 'features', 'label': '功能开关', 'url': '/admin/flowly/features/', 'icon': 'fas fa-sliders-h'},
    {'id': 'ai_models', 'label': 'AI 模型', 'url': '/admin/flowly/ai-models/', 'icon': 'fas fa-brain'},
    {'id': 'audit', 'label': '审计', 'url': '/admin/flowly/audit/', 'icon': 'fas fa-shield-alt'},
    {'id': 'system', 'label': '系统', 'url': '/admin/flowly/system/', 'icon': 'fas fa-server'},
]
