"""
Custom exceptions and exception handlers.
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


class FlowlyException(Exception):
    """Base exception for Flowly."""

    def __init__(self, message: str, code: str = None, details: dict = None):
        self.message = message
        self.code = code or 'error'
        self.details = details or {}
        super().__init__(message)


class AuthenticationError(FlowlyException):
    """Authentication related errors."""

    def __init__(self, message: str = 'Authentication failed', **kwargs):
        super().__init__(message, code='auth_error', **kwargs)


class AuthorizationError(FlowlyException):
    """Authorization related errors."""

    def __init__(self, message: str = 'Permission denied', **kwargs):
        super().__init__(message, code='authz_error', **kwargs)


class ValidationError(FlowlyException):
    """Validation related errors."""

    def __init__(self, message: str = 'Validation failed', **kwargs):
        super().__init__(message, code='validation_error', **kwargs)


class NotFoundError(FlowlyException):
    """Resource not found errors."""

    def __init__(self, message: str = 'Resource not found', **kwargs):
        super().__init__(message, code='not_found', **kwargs)


class RateLimitError(FlowlyException):
    """Rate limit exceeded errors."""

    def __init__(self, message: str = 'Rate limit exceeded', **kwargs):
        super().__init__(message, code='rate_limit', **kwargs)


class ExternalServiceError(FlowlyException):
    """External service errors."""

    def __init__(self, message: str = 'External service error', **kwargs):
        super().__init__(message, code='external_error', **kwargs)


class WorkflowExecutionError(FlowlyException):
    """Workflow execution errors."""

    def __init__(self, message: str = 'Workflow execution failed', **kwargs):
        super().__init__(message, code='workflow_error', **kwargs)


class AgentError(FlowlyException):
    """AI Agent errors."""

    def __init__(self, message: str = 'Agent execution failed', **kwargs):
        super().__init__(message, code='agent_error', **kwargs)


def custom_exception_handler(exc, context):
    """
    Custom exception handler for consistent error responses.
    """
    # Handle custom Flowly exceptions
    if isinstance(exc, FlowlyException):
        return Response({
            'error': True,
            'code': exc.code,
            'message': exc.message,
            'details': exc.details
        }, status=status.HTTP_400_BAD_REQUEST)

    # Call REST framework's default exception handler
    response = exception_handler(exc, context)

    if response is not None:
        error_data = {
            'error': True,
            'code': get_error_code(response.status_code),
            'message': get_error_message(response.data),
            'details': response.data if isinstance(response.data, dict) else {'detail': response.data}
        }
        response.data = error_data
    else:
        # Handle unexpected exceptions
        logger.error('Unhandled exception: %s', exc, exc_info=True)
        error_data = {
            'error': True,
            'code': 'internal_error',
            'message': '服务器内部错误',
            'details': {}
        }
        response = Response(error_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return response


def get_error_code(status_code: int) -> str:
    """Get error code from status code."""
    codes = {
        400: 'bad_request',
        401: 'unauthorized',
        403: 'forbidden',
        404: 'not_found',
        405: 'method_not_allowed',
        409: 'conflict',
        422: 'unprocessable_entity',
        429: 'rate_limit',
        500: 'internal_error',
        502: 'bad_gateway',
        503: 'service_unavailable',
    }
    return codes.get(status_code, 'error')


def get_error_message(data) -> str:
    """Extract error message from response data."""
    if isinstance(data, str):
        return data

    if isinstance(data, dict):
        if 'detail' in data:
            return str(data['detail'])

        for key, value in data.items():
            if isinstance(value, list) and value:
                return f"{key}: {value[0]}"
            elif isinstance(value, str):
                return f"{key}: {value}"

    if isinstance(data, list) and data:
        return str(data[0])

    return '请求处理失败'
