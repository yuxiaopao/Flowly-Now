"""
统一异常类体系
所有业务异常从此模块导入，避免分散的 try/except Exception
"""

from rest_framework.exceptions import APIException
from rest_framework import status


class BaseAPIException(APIException):
    """所有业务异常的基类"""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = '服务器内部错误'
    default_code = 'INTERNAL_ERROR'

    def __init__(self, detail=None, code=None):
        self.detail = detail or self.default_detail
        self.code = code or self.default_code


# =============================================================================
# 工作流异常
# =============================================================================

class WorkflowNotFoundError(BaseAPIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = '工作流不存在'
    default_code = 'WORKFLOW_NOT_FOUND'


class WorkflowExecutionError(BaseAPIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = '工作流执行失败'
    default_code = 'WORKFLOW_EXECUTION_ERROR'


class WorkflowValidationError(BaseAPIException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = '工作流验证失败'
    default_code = 'WORKFLOW_VALIDATION_ERROR'


class NodeNotFoundError(BaseAPIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = '节点不存在'
    default_code = 'NODE_NOT_FOUND'


class NodeExecutionError(BaseAPIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = '节点执行失败'
    default_code = 'NODE_EXECUTION_ERROR'


# =============================================================================
# Agent 异常
# =============================================================================

class AgentNotFoundError(BaseAPIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'Agent 不存在'
    default_code = 'AGENT_NOT_FOUND'


class AgentExecutionError(BaseAPIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = 'Agent 执行失败'
    default_code = 'AGENT_EXECUTION_ERROR'


class ConversationNotFoundError(BaseAPIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = '会话不存在'
    default_code = 'CONVERSATION_NOT_FOUND'


# =============================================================================
# RAG / 向量存储异常
# =============================================================================

class VectorStoreConnectionError(BaseAPIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = '向量数据库连接失败'
    default_code = 'VECTOR_STORE_UNAVAILABLE'


class VectorStoreConfigError(BaseAPIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = '向量存储配置错误'
    default_code = 'VECTOR_STORE_CONFIG_ERROR'


class CollectionNotFoundError(BaseAPIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = '文档集合不存在'
    default_code = 'COLLECTION_NOT_FOUND'


class DocumentProcessingError(BaseAPIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = '文档处理失败'
    default_code = 'DOCUMENT_PROCESSING_ERROR'


# =============================================================================
# LLM / AI 异常
# =============================================================================

class LLMProviderNotAvailableError(BaseAPIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = '没有可用的 LLM provider'
    default_code = 'LLM_PROVIDER_UNAVAILABLE'


class LLMCallError(BaseAPIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = 'LLM 调用失败'
    default_code = 'LLM_CALL_ERROR'


class TokenLimitExceededError(BaseAPIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Token 数量超限'
    default_code = 'TOKEN_LIMIT_EXCEEDED'


class ModelNotFoundError(BaseAPIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'AI 模型不存在'
    default_code = 'MODEL_NOT_FOUND'


# =============================================================================
# 认证 / 权限异常
# =============================================================================

class TokenExpiredError(BaseAPIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = 'Token 已过期'
    default_code = 'TOKEN_EXPIRED'


class InvalidCredentialsError(BaseAPIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = '认证凭证无效'
    default_code = 'INVALID_CREDENTIALS'


# =============================================================================
# 限流异常
# =============================================================================

class RateLimitExceededError(BaseAPIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = '请求频率超限'
    default_code = 'RATE_LIMIT_EXCEEDED'


# =============================================================================
# 账单 / 订阅异常
# =============================================================================

class SubscriptionNotFoundError(BaseAPIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = '订阅不存在'
    default_code = 'SUBSCRIPTION_NOT_FOUND'


class PaymentError(BaseAPIException):
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = '支付处理失败'
    default_code = 'PAYMENT_ERROR'


class CouponInvalidError(BaseAPIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = '优惠券无效'
    default_code = 'COUPON_INVALID'


class QuotaExceededError(BaseAPIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = '配额已用尽'
    default_code = 'QUOTA_EXCEEDED'


# =============================================================================
# 数据异常
# =============================================================================

class FileUploadError(BaseAPIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = '文件上传失败'
    default_code = 'FILE_UPLOAD_ERROR'


class DataExportError(BaseAPIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = '数据导出失败'
    default_code = 'DATA_EXPORT_ERROR'


# =============================================================================
# NL Workflow 异常
# =============================================================================

class NLSessionNotFoundError(BaseAPIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'NL 会话不存在'
    default_code = 'NL_SESSION_NOT_FOUND'


class WorkflowGenerationError(BaseAPIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = '工作流生成失败'
    default_code = 'WORKFLOW_GENERATION_ERROR'


class IntentParseError(BaseAPIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = '意图解析失败'
    default_code = 'INTENT_PARSE_ERROR'


# =============================================================================
# 通用异常
# =============================================================================

class ResourceNotFoundError(BaseAPIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = '请求的资源不存在'
    default_code = 'RESOURCE_NOT_FOUND'


class ValidationError(BaseAPIException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = '数据验证失败'
    default_code = 'VALIDATION_ERROR'


class OperationTimeoutError(BaseAPIException):
    status_code = status.HTTP_504_GATEWAY_TIMEOUT
    default_detail = '操作超时'
    default_code = 'OPERATION_TIMEOUT'


# =============================================================================
# 异常处理辅助函数
# =============================================================================

def get_error_response(exc):
    """将异常转换为标准 API 响应格式"""
    return {
        'code': exc.status_code,
        'message': exc.detail,
        'error_code': exc.code,
        'data': None,
        'errors': None
    }
