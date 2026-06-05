"""
Django 错误处理器
将 404、405、500 等错误转换为 JSON 响应
"""

import logging
from django.http import JsonResponse
from django.views import defaults

logger = logging.getLogger(__name__)


def handler400(request, exception):
    """
    400 Bad Request - 错误请求
    """
    logger.warning(f"400 Error: {exception} - Path: {request.path}")
    
    return JsonResponse({
        'code': 400,
        'data': None,
        'message': '请求格式错误或参数无效',
        'error': str(exception) if hasattr(exception, '__str__') else 'Bad Request'
    }, status=400)


def handler403(request, exception):
    """
    403 Forbidden - 权限不足
    """
    logger.warning(f"403 Error: {exception} - Path: {request.path} - User: {getattr(request, 'user', 'Anonymous')}")
    
    return JsonResponse({
        'code': 403,
        'data': None,
        'message': '权限不足，无法访问此资源',
        'error': str(exception) if hasattr(exception, '__str__') else 'Forbidden'
    }, status=403)


def handler404(request, exception):
    """
    404 Not Found - 资源不存在
    """
    logger.info(f"404 Error: Path: {request.path}")
    
    return JsonResponse({
        'code': 404,
        'data': None,
        'message': f'路由不存在: {request.path}',
        'error': 'Not Found'
    }, status=404)


def handler405(request, exception):
    """
    405 Method Not Allowed - 请求方法不支持
    """
    logger.warning(f"405 Error: Method {request.method} not allowed for {request.path}")
    
    return JsonResponse({
        'code': 405,
        'data': None,
        'message': f'请求方法 {request.method} 不支持此端点',
        'error': 'Method Not Allowed'
    }, status=405)


def handler500(request):
    """
    500 Internal Server Error - 服务器内部错误
    """
    logger.exception(f"500 Error: Path: {request.path} - User: {getattr(request, 'user', 'Anonymous')}")
    
    return JsonResponse({
        'code': 500,
        'data': None,
        'message': '服务器内部错误，请稍后重试',
        'error': 'Internal Server Error'
    }, status=500)


def csrf_failure(request, reason=""):
    """
    CSRF 验证失败
    """
    return JsonResponse({
        'code': 403,
        'data': None,
        'message': 'CSRF 验证失败，请刷新页面后重试',
        'error': 'CSRF Failed'
    }, status=403)
