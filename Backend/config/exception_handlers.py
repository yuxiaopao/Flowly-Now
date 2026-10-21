"""
DRF 全局异常处理器
提供统一的错误响应格式
"""

import logging
from django_ratelimit.exceptions import Ratelimited
from rest_framework.views import exception_handler
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import (
    ValidationError, AuthenticationFailed, NotAuthenticated,
    PermissionDenied, NotFound, MethodNotAllowed,
    Throttled, UnsupportedMediaType, ParseError
)

logger = logging.getLogger(__name__)


class APIResponse:
    """标准 API 响应格式"""
    
    @staticmethod
    def success(data=None, message='操作成功', code=status.HTTP_200_OK):
        """成功响应"""
        return {
            'code': code,
            'data': data,
            'message': message
        }
    
    @staticmethod
    def error(error_message, code=status.HTTP_400_BAD_REQUEST, errors=None):
        """错误响应"""
        return {
            'code': code,
            'error_message': error_message,
            'errors': errors
        }


def custom_exception_handler(exc, context):
    """
    自定义全局异常处理
    
    所有 DRF 异常都会被此函数处理，返回统一格式的 JSON 响应。
    格式: {code, data, message, errors}
    """
    if isinstance(exc, Ratelimited):
        return Response({
            'code': status.HTTP_429_TOO_MANY_REQUESTS,
            'message': '请求过于频繁，请稍后再试',
            'data': None,
            'errors': None,
        }, status=status.HTTP_429_TOO_MANY_REQUESTS)

    response = exception_handler(exc, context)
    request = context.get('request')

    if response is not None:
        custom_response_data = {
            'code': response.status_code,
            'message': get_error_message(response.data),
            'data': None,
            'errors': None
        }
        
        if isinstance(response.data, dict):
            field_errors = {}
            for key, value in response.data.items():
                if isinstance(value, list):
                    field_errors[key] = value
                elif isinstance(value, dict):
                    field_errors[key] = flatten_errors(value)
                    
            if field_errors:
                custom_response_data['errors'] = field_errors
        
        elif isinstance(response.data, list):
            custom_response_data['errors'] = response.data
        
        if isinstance(exc, ValidationError):
            custom_response_data['message'] = '数据验证失败'
            custom_response_data['code'] = status.HTTP_422_UNPROCESSABLE_ENTITY
        elif isinstance(exc, AuthenticationFailed):
            custom_response_data['message'] = '认证失败，请检查凭证'
        elif isinstance(exc, NotAuthenticated):
            custom_response_data['message'] = '请先登录'
        elif isinstance(exc, PermissionDenied):
            custom_response_data['message'] = '权限不足，无法执行此操作'
        elif isinstance(exc, NotFound):
            custom_response_data['message'] = '请求的资源不存在'
        elif isinstance(exc, MethodNotAllowed):
            custom_response_data['message'] = f'不支持 {request.method} 请求方法'
        elif isinstance(exc, Throttled):
            custom_response_data['message'] = '请求过于频繁，请稍后再试'
        elif isinstance(exc, (UnsupportedMediaType, ParseError)):
            custom_response_data['message'] = '不支持的媒体类型或解析失败'
        
        response.data = custom_response_data

    else:
        view = context.get('view')
        logger.exception(f"Unhandled exception in {view}: {exc}")

        response = Response(
            {
                'code': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': '服务器内部错误',
                'data': None,
                'errors': None
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        return response

    log_exception(exc, response, request)
    return response


def get_error_message(data):
    """
    从响应数据中提取错误消息
    """
    if data is None:
        return '未知错误'
    
    if isinstance(data, str):
        return data
    
    if isinstance(data, list):
        if data:
            return '; '.join(str(item) for item in data)
        return '请求处理失败'
    
    if isinstance(data, dict):
        for field in ('detail', 'message', 'error', 'non_field_errors'):
            if field in data:
                value = data[field]
                if isinstance(value, str):
                    return value
                elif isinstance(value, list) and value:
                    return str(value[0])
        
        for key, value in data.items():
            if isinstance(value, list) and value:
                return f'{key}: {value[0]}'
            elif isinstance(value, str):
                return f'{key}: {value}'
    
    return '请求处理失败'


def flatten_errors(errors, prefix=''):
    """
    扁平化嵌套的错误字典
    """
    result = []
    for key, value in errors.items():
        field_name = f'{prefix}.{key}' if prefix else key
        if isinstance(value, dict):
            result.extend(flatten_errors(value, field_name))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    result.extend(flatten_errors(item, field_name))
                else:
                    result.append(f'{field_name}: {item}')
        else:
            result.append(f'{field_name}: {value}')
    return result


def log_exception(exc, response, request):
    """
    记录异常日志
    """
    if request is None:
        return

    log_data = {
        'method': request.method,
        'path': request.path,
        'user': str(request.user) if hasattr(request, 'user') else 'Anonymous',
        'status_code': response.status_code,
        'error_message': str(exc)
    }

    if hasattr(response, 'data') and isinstance(response.data, dict) and response.data.get('errors'):
        log_data['errors'] = response.data['errors']
    
    status_code = log_data['status_code']
    if status_code >= 500:
        logger.error('Server Error', extra=log_data)
    elif status_code >= 400:
        logger.warning('Client Error', extra=log_data)
    else:
        logger.info('Request completed', extra=log_data)
