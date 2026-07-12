"""
项目常量配置文件
统一管理所有硬编码的魔法数字、魔法字符串、枚举值和 URL 配置
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# =============================================================================
# Default Model Names
# =============================================================================

# Default LLM model (this is a fallback for OpenAI-compatible APIs)
# For local Ollama models, use DEFAULT_OLLAMA_MODEL
DEFAULT_LLM_MODEL = "qwen2.5-coder:7b"  # Default LLM model for OpenAI-compatible APIs
DEFAULT_OLLAMA_MODEL = "qwen2.5-coder:7b"  # Default Ollama model
DEFAULT_EMBEDDING_MODEL = "text-embedding-ada-002"  # Default embedding model
DEFAULT_OLLAMA_EMBEDDING_MODEL = "nomic-embed-text"  # Default local Ollama embedding model

# =============================================================================
# Default LLM Parameters
# =============================================================================

DEFAULT_TEMPERATURE = 0.7  # Default temperature for LLM
DEFAULT_MAX_TOKENS = 4096  # Default max tokens for general LLM calls
DEFAULT_CONTEXT_WINDOW = 10  # Default context window size

# =============================================================================
# API Providers
# =============================================================================

OPENAI_API_URL = "https://api.openai.com/v1"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1"
OPENAI_BASE_URL = "https://api.openai.com/v1"  # Default fallback
OPENWEATHER_API_URL = "https://api.openweathermap.org/data/2.5/weather"
WTIRR_API_URL = "https://wttr.in"

# =============================================================================
# Ollama Configuration
# =============================================================================

OLLAMA_BASE_URL = "http://localhost:11434"  # Default Ollama server URL
OLLAMA_HEALTH_CHECK_TIMEOUT = 5  # Ollama health check timeout in seconds
OLLAMA_CHAT_TIMEOUT = 120  # Ollama chat request timeout in seconds
OLLAMA_EMBEDDINGS_TIMEOUT = 30  # Ollama embeddings timeout in seconds
OLLAMA_CONNECT_TIMEOUT = 5  # Ollama connection timeout
OLLAMA_LIST_MODELS_TIMEOUT = 5  # Ollama list models timeout
# Context window (tokens) requested from the Ollama server for chat calls. Many local
# models default to very large context windows (e.g. 128k) which can exhaust host RAM
# when allocating the KV cache; capping this keeps local inference usable on typical dev
# machines. Override via OLLAMA_NUM_CTX env var for larger-memory hosts.
OLLAMA_NUM_CTX = 4096

# =============================================================================
# Timeout (seconds)
# =============================================================================

TOOL_TIMEOUT_DEFAULT = 30          # Default tool timeout
NODE_EXECUTION_TIMEOUT = 300       # Node execution timeout
HTTP_TOOL_TIMEOUT = 10            # HTTP tool request timeout
WEBHOOK_TIMEOUT = 10              # Webhook delivery timeout
OLLAMA_HEALTH_CHECK_TIMEOUT = 5   # Ollama health check timeout
OLLAMA_CHAT_TIMEOUT = 120         # Ollama chat request timeout
EMBEDDINGS_TIMEOUT = 30           # Ollama embeddings timeout

# =============================================================================
# Pagination
# =============================================================================

PAGE_SIZE_DEFAULT = 20
PAGE_SIZE_MAX = 100
CURSOR_PAGE_SIZE = 50
CURSOR_PAGE_SIZE_MAX = 200

# =============================================================================
# Workflow Status
# =============================================================================

class WorkflowStatus:
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

    CHOICES = [
        (DRAFT, "草稿"),
        (PUBLISHED, "已发布"),
        (ARCHIVED, "已归档"),
    ]

# =============================================================================
# Node Types
# =============================================================================

class NodeType:
    START = "start"
    END = "end"
    LLM = "llm"
    PROMPT = "prompt"
    CONDITION = "condition"
    TOOL = "tool"
    INPUT = "input"
    OUTPUT = "output"
    CODE = "code"
    LOOP = "loop"
    HTTP_REQUEST = "http_request"
    DATA_TRANSFORM = "data_transform"
    EMAIL = "email"
    WEBHOOK = "webhook"
    TEMPLATE = "template"
    VARIABLE = "variable"
    RAG = "rag"

    # Multimodal & Generation
    IMAGE_GENERATION = "image_generation"
    VIDEO_GENERATION = "video_generation"
    AUDIO_GENERATION = "audio_generation"
    SUBTITLE_GENERATION = "subtitle_generation"
    IMAGE_EDITING = "image_editing"
    VIDEO_TRANSLATION = "video_translation"
    VIDEO_UPLOAD = "video_upload"
    SUBTITLE_TRANSLATE = "subtitle_translate"
    SEGMENT_DUBBING = "segment_dubbing"
    LIP_SYNC = "lip_sync"
    SUBTITLE_BURN = "subtitle_burn"

    # ML & Training
    DATASET_UPLOAD = "dataset_upload"
    DATA_ANNOTATION = "data_annotation"
    DATA_AUGMENTATION = "data_augmentation"
    MODEL_TRAINING = "model_training"
    MODEL_EVALUATION = "model_evaluation"
    MODEL_DEPLOYMENT = "model_deployment"

    # RAG & Retrieval
    DOCUMENT_LOADER = "document_loader"
    EMBEDDING = "embedding"
    VECTOR_STORE = "vector_store"
    RETRIEVER = "retriever"
    RERANKER = "reranker"

    # Agent
    AGENT = "agent"
    PLANNER = "planner"
    EXECUTOR = "executor"
    MEMORY = "memory"

    # Data Pipeline
    FILE_READER = "file_reader"
    FILE_WRITER = "file_writer"
    WEB_SCRAPER = "web_scraper"
    CSV_TRANSFORM = "csv_transform"
    JSON_TRANSFORM = "json_transform"

    CHOICES = [
        (START, "开始"),
        (END, "结束"),
        (LLM, "大语言模型"),
        (PROMPT, "提示词"),
        (CONDITION, "条件判断"),
        (TOOL, "工具调用"),
        (INPUT, "输入"),
        (OUTPUT, "输出"),
        (CODE, "代码执行"),
        (LOOP, "循环"),
        (HTTP_REQUEST, "HTTP请求"),
        (DATA_TRANSFORM, "数据转换"),
        (EMAIL, "邮件"),
        (WEBHOOK, "Webhook"),
        (TEMPLATE, "模板"),
        (VARIABLE, "变量"),
        (RAG, "知识检索"),
        (IMAGE_GENERATION, "图像生成"),
        (VIDEO_GENERATION, "视频生成"),
        (AUDIO_GENERATION, "音频生成"),
        (SUBTITLE_GENERATION, "字幕生成"),
        (IMAGE_EDITING, "图像编辑"),
        (VIDEO_TRANSLATION, "视频翻译"),
        (VIDEO_UPLOAD, "视频上传"),
        (SUBTITLE_TRANSLATE, "字幕翻译"),
        (SEGMENT_DUBBING, "分段配音"),
        (LIP_SYNC, "口型同步"),
        (SUBTITLE_BURN, "字幕烧录"),
        (DATASET_UPLOAD, "数据集上传"),
        (DATA_ANNOTATION, "数据标注"),
        (DATA_AUGMENTATION, "数据增强"),
        (MODEL_TRAINING, "模型训练"),
        (MODEL_EVALUATION, "模型评估"),
        (MODEL_DEPLOYMENT, "模型部署"),
        (DOCUMENT_LOADER, "文档加载"),
        (EMBEDDING, "向量化"),
        (VECTOR_STORE, "向量存储"),
        (RETRIEVER, "检索器"),
        (RERANKER, "重排序"),
        (AGENT, "Agent"),
        (PLANNER, "任务规划"),
        (EXECUTOR, "任务执行"),
        (MEMORY, "记忆管理"),
        (FILE_READER, "文件读取"),
        (FILE_WRITER, "文件写入"),
        (WEB_SCRAPER, "网页爬取"),
        (CSV_TRANSFORM, "CSV转换"),
        (JSON_TRANSFORM, "JSON转换"),
    ]

# =============================================================================
# Execution Status
# =============================================================================

class ExecutionStatus:
    QUEUED = "queued"
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

    CHOICES = [
        (QUEUED, "排队中"),
        (PENDING, "等待中"),
        (RUNNING, "运行中"),
        (PAUSED, "已暂停"),
        (COMPLETED, "已完成"),
        (FAILED, "失败"),
        (CANCELLED, "已取消"),
        (TIMEOUT, "超时"),
    ]

# =============================================================================
# Execution Trigger Types
# =============================================================================

class TriggerType:
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    WEBHOOK = "webhook"
    API = "api"
    EVENT = "event"

    CHOICES = [
        (MANUAL, "手动触发"),
        (SCHEDULED, "定时任务"),
        (WEBHOOK, "Webhook"),
        (API, "API调用"),
        (EVENT, "事件触发"),
    ]

# =============================================================================
# Node Execution Status
# =============================================================================

class NodeExecutionStatus:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

    CHOICES = [
        (PENDING, "等待中"),
        (RUNNING, "运行中"),
        (COMPLETED, "已完成"),
        (FAILED, "失败"),
        (SKIPPED, "已跳过"),
    ]

# =============================================================================
# Error Handling Strategies
# =============================================================================

class ErrorHandlingStrategy:
    STOP = "stop"
    SKIP = "skip"
    RETRY = "retry"
    FALLBACK = "fallback"

    CHOICES = [
        (STOP, "停止"),
        (SKIP, "跳过"),
        (RETRY, "重试"),
        (FALLBACK, "备用值"),
    ]

# =============================================================================
# Rate Limits
# =============================================================================

RATE_LIMIT_ANON = "100/minute"
RATE_LIMIT_USER = "1000/minute"
RATE_LIMIT_WORKFLOW_EXECUTE = "10/minute"
RATE_LIMIT_NL_STREAM = "5/minute"
RATE_LIMIT_NL_PREVIEW = "10/minute"
RATE_LIMIT_NL_EDITOR_APPLY = "30/minute"
RATE_LIMIT_LOGIN = "5/minute"  # Login attempt rate limit

# =============================================================================
# Security Limits
# =============================================================================

DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB - max size for file uploads
DATA_UPLOAD_MAX_FORM_FIELD_SIZE = 10 * 1024 * 1024  # 10MB - max size for form fields
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes - Celery task time limit

# =============================================================================
# Ollama Model Prefixes (used for auto-detection)
# =============================================================================

OLLAMA_MODEL_PREFIXES = [
    'llama', 'mistral', 'codellama', 'qwen', 'phi', 'deepseek',
    'gemma', 'nomic', 'smollm', 'phi3', 'llava', 'moondream',
    'mixtral', 'neural-chat', 'wizardlm', 'orca', 'stablelm',
    'qwen2', 'qwen3', 'qwen2.5', 'aya', 'command-r',
    # Additional local model prefixes
    'vicuna', 'wizardcoder', 'codestral', 'phi4',
]

# =============================================================================
# Tenant (Team) Default Plan Limits
# =============================================================================
# Applied as the Tenant model's field defaults for newly created teams (free plan).
# A max_users of 1 would make team invitations impossible, so this must stay >= 2.

TENANT_DEFAULT_MAX_USERS = 5
TENANT_DEFAULT_MAX_WORKFLOWS = 10
TENANT_DEFAULT_MAX_EXECUTIONS_PER_MONTH = 100

# =============================================================================
# CORS Default Origins
# =============================================================================

CORS_DEFAULT_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"

# =============================================================================
# Vector Database Configuration
# =============================================================================

CHROMA_PERSIST_DIR = BASE_DIR / 'data' / 'chroma'
PINECONE_CLOUD = 'aws'
PINECONE_REGION = 'us-east-1'
EMBEDDING_BATCH_SIZE = 100

# Vector store defaults
VECTOR_STORE_DEFAULT_HOST = 'localhost'
VECTOR_STORE_DEFAULT_PORT = 6333
VECTOR_STORE_DEFAULT_PROTOCOL = 'http'
VECTOR_STORE_DEFAULT_DIMENSION = 1536
VECTOR_STORE_DEFAULT_COLLECTION = 'default'

# =============================================================================
# Vector Database Configuration
# =============================================================================

# =============================================================================
# Cache Configuration
# =============================================================================

CACHE_DEFAULT_TIMEOUT = 300  # Default cache timeout in seconds
CACHE_VIEW_TIMEOUT = 60  # View cache timeout in seconds
CACHE_QUERY_TIMEOUT = 300  # Query cache timeout in seconds
