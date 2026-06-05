"""
Performance optimization utilities for the backend.
"""

from functools import wraps
from django.core.cache import cache
from django.db.models import Count, Q
import hashlib
import json
import time


def cache_key(*args, **kwargs):
    """Generate a cache key from arguments."""
    key_data = {
        'args': args,
        'kwargs': sorted(kwargs.items())
    }
    key_str = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(key_str.encode()).hexdigest()


def cached_view(timeout=300, prefix='view'):
    """
    Cache decorator for view responses.

    Usage:
        @cached_view(timeout=600, prefix='workflows')
        def get_workflows(request):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # Generate cache key
            key_parts = [
                prefix,
                func.__name__,
                request.user.id if request.user.is_authenticated else 'anonymous',
                request.path,
                json.dumps(dict(request.GET), sort_keys=True)
            ]
            cache_key_str = ':'.join(str(k) for k in key_parts)
            cache_key_hash = hashlib.md5(cache_key_str.encode()).hexdigest()

            # Try to get from cache
            result = cache.get(cache_key_hash)
            if result is not None:
                return result

            # Execute view
            result = func(request, *args, **kwargs)

            # Cache the result (only cache successful responses)
            if hasattr(result, 'status_code') and result.status_code == 200:
                cache.set(cache_key_hash, result, timeout)

            return result
        return wrapper
    return decorator


def cache_query(timeout=300):
    """
    Cache decorator for database queries.

    Usage:
        @cache_query(timeout=600)
        def get_popular_workflows():
            return Workflow.objects.annotate(execution_count=Count('executions')).order_by('-execution_count')[:10]
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key = f"query:{func.__name__}:{cache_key(*args, **kwargs)}"

            result = cache.get(key)
            if result is not None:
                return result

            result = func(*args, **kwargs)
            cache.set(key, result, timeout)
            return result
        return wrapper
    return decorator


def invalidate_cache(pattern='*'):
    """
    Invalidate cache entries matching a pattern.

    Note: This is a simple implementation. For production,
    consider using django-cache-memoize or Redis patterns.
    """
    if pattern == '*':
        cache.clear()
    # For pattern-based invalidation, you would need to track
    # cache keys or use Redis SCAN command


class QueryCounter:
    """Context manager to count database queries."""

    def __init__(self):
        self.count = 0
        self.queries = []

    def __enter__(self):
        from django.db import connection
        self._connection = connection
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def optimize_queryset(queryset):
    """
    Apply common optimizations to a queryset.

    - select_related for ForeignKey
    - prefetch_related for ManyToMany and reverse FK
    """
    from django.db.models import Prefetch

    # Get model
    model = queryset.model

    # Get related fields
    related_fields = [
        f.name for f in model._meta.get_fields()
        if f.many_to_one and f.name != 'ptr'
    ]

    # Get reverse relations
    reverse_relations = [
        f.name for f in model._meta.get_fields()
        if f.one_to_many
    ]

    # Apply select_related
    if related_fields:
        queryset = queryset.select_related(*related_fields)

    # Return without prefetch_related by default (may cause N+1 in some cases)
    return queryset


def paginate_queryset(queryset, page=1, page_size=20, max_page_size=100):
    """
    Manual pagination for views that need more control.

    Returns (paginated_queryset, total_count, total_pages, has_next, has_prev)
    """
    page = max(1, page)
    page_size = min(max(1, page_size), max_page_size)

    total = queryset.count()
    total_pages = (total + page_size - 1) // page_size

    offset = (page - 1) * page_size
    items = list(queryset[offset:offset + page_size])

    return items, total, total_pages, page < total_pages, page > 1
