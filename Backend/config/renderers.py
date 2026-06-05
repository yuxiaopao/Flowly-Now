"""
DRF 统一响应渲染器
将所有 API 响应包装为统一格式：
成功: { code: 200, message: "success", data: {...} }
错误: { code: 4xx/5xx, message: "错误描述", data: null, errors: {...} }
"""

from rest_framework.renderers import JSONRenderer


class UnifiedJSONRenderer(JSONRenderer):
    """
    统一 JSON 响应渲染器
    自动将 DRF 视图返回的数据包装为标准格式
    """

    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get('response') if renderer_context else None

        if response is None:
            return super().render(data, accepted_media_type, renderer_context)

        status_code = response.status_code

        # 如果数据已经是统一格式（由异常处理器包装过），直接渲染
        if isinstance(data, dict) and 'code' in data and ('error_message' in data or 'message' in data):
            # 规范化：将 error_message 统一为 message
            if 'error_message' in data and 'message' not in data:
                data['message'] = data.pop('error_message')
            elif 'error_message' in data:
                data.pop('error_message')
            return super().render(data, accepted_media_type, renderer_context)

        # 成功响应（2xx）
        if 200 <= status_code < 300:
            wrapped = {
                'code': status_code,
                'message': 'success',
                'data': data
            }
        else:
            # 错误响应（未被异常处理器捕获的情况）
            message = '请求失败'
            errors = None

            if isinstance(data, dict):
                message = (
                    data.get('detail')
                    or data.get('message')
                    or data.get('error')
                    or '请求失败'
                )
                errors = data.get('errors')
            elif isinstance(data, str):
                message = data

            wrapped = {
                'code': status_code,
                'message': message,
                'data': None,
                'errors': errors
            }

        return super().render(wrapped, accepted_media_type, renderer_context)
