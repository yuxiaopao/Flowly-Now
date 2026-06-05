"""
DRF 分页器
提供统一的分页响应格式
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from config.constants import PAGE_SIZE_DEFAULT, PAGE_SIZE_MAX, CURSOR_PAGE_SIZE, CURSOR_PAGE_SIZE_MAX


class StandardResultsSetPagination(PageNumberPagination):
    """
    标准结果集分页器
    
    请求示例: GET /api/v1/workflows/?page=1&page_size=20
    
    响应格式:
    {
        "code": 200,
        "data": {
            "count": 100,
            "next": "http://api/v1/workflows/?page=2",
            "previous": null,
            "results": [...]
        },
        "message": "操作成功"
    }
    """
    
    page_size = PAGE_SIZE_DEFAULT
    page_size_query_param = 'page_size'
    max_page_size = PAGE_SIZE_MAX
    
    def get_paginated_response(self, data):
        """返回统一格式的分页响应"""
        return Response({
            'code': 200,
            'data': {
                'count': self.page.paginator.count,
                'total_pages': self.page.paginator.num_pages,
                'current_page': self.page.number,
                'page_size': self.get_page_size(self.request),
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
                'results': data
            },
            'message': '操作成功'
        })
    
    def get_paginated_response_schema(self, schema):
        """返回分页响应的 schema"""
        return {
            'type': 'object',
            'properties': {
                'code': {
                    'type': 'integer',
                    'example': 200
                },
                'data': {
                    'type': 'object',
                    'properties': {
                        'count': {
                            'type': 'integer',
                            'description': '总记录数'
                        },
                        'total_pages': {
                            'type': 'integer',
                            'description': '总页数'
                        },
                        'current_page': {
                            'type': 'integer',
                            'description': '当前页码'
                        },
                        'page_size': {
                            'type': 'integer',
                            'description': '每页记录数'
                        },
                        'next': {
                            'type': 'string',
                            'nullable': True,
                            'description': '下一页 URL'
                        },
                        'previous': {
                            'type': 'string',
                            'nullable': True,
                            'description': '上一页 URL'
                        },
                        'results': schema
                    }
                },
                'message': {
                    'type': 'string',
                    'example': '操作成功'
                }
            }
        }


class CursorPagination:
    """
    基于游标的分页器（用于大数据量场景）

    响应格式:
    {
        "code": 200,
        "data": {
            "next_cursor": "abc123",
            "has_more": true,
            "results": [...]
        },
        "message": "操作成功"
    }
    """

    page_size = CURSOR_PAGE_SIZE
    cursor_query_param = 'cursor'
    ordering_param = 'ordering'
    page_size_query_param = 'page_size'
    max_page_size = CURSOR_PAGE_SIZE_MAX

    def paginate_queryset(self, queryset, request, view=None):
        """分页查询"""
        from django.db.models import F

        self.page_size = min(
            int(request.query_params.get(self.page_size_query_param, self.page_size)),
            self.max_page_size
        )

        cursor = request.query_params.get(self.cursor_query_param)
        ordering = request.query_params.get(self.ordering_param, '-created_at')

        queryset = queryset.order_by(ordering)

        if cursor:
            try:
                cursor_data = cursor.split(':')
                if len(cursor_data) >= 2:
                    cursor_pk = int(cursor_data[0])
                    cursor_value = cursor_data[1]
                    cursor_order = 'lt' if '-' not in ordering else 'gt'

                    field = ordering.lstrip('-')
                    filter_kwargs = {
                        f'{field}__{"lt" if cursor_order == "lt" else "gt"}': cursor_value,
                    }

                    if cursor_order == 'lt':
                        filter_kwargs['pk__lt'] = cursor_pk
                    else:
                        filter_kwargs['pk__gt'] = cursor_pk

                    queryset = queryset.filter(**filter_kwargs)
            except (ValueError, IndexError):
                pass

        results = list(queryset[:self.page_size + 1])

        if len(results) > self.page_size:
            results = results[:self.page_size]
            has_more = True
            last = results[-1]
            next_cursor = f"{last.pk}:{getattr(last, ordering.lstrip('-'), last.pk)}"
        else:
            has_more = False
            next_cursor = None

        return results, has_more, next_cursor

    def get_paginated_response(self, data, has_more=False, next_cursor=None):
        """返回游标分页响应"""
        return Response({
            'code': 200,
            'data': {
                'next_cursor': next_cursor,
                'has_more': has_more,
                'page_size': self.page_size,
                'results': data
            },
            'message': '操作成功'
        })
