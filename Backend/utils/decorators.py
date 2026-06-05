"""
Common decorators for views and functions.
"""

import functools
import time
import logging
from typing import Callable, Any
from django.http import JsonResponse
from django.core.cache import cache

logger = logging.getLogger(__name__)


def timing_decorator(func: Callable) -> Callable:
    """Decorator to measure function execution time."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        logger.debug(f"{func.__name__} took {duration:.3f}s")
        return result
    return wrapper


def cache_result(timeout: int = 300, key_prefix: str = ""):
    """Decorator to cache function results."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
            cache_key = cache_key.replace(" ", "").replace("\n", "")

            # Try to get from cache
            cached = cache.get(cache_key)
            if cached is not None:
                return cached

            # Call function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            return result
        return wrapper
    return decorator


def rate_limit(max_calls: int = 60, period: int = 60):
    """Decorator to rate limit function calls."""
    def decorator(func: Callable) -> Callable:
        cache_key = f"rate_limit:{func.__name__}"

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            calls = cache.get(cache_key, 0)
            if calls >= max_calls:
                return JsonResponse({
                    'error': 'Rate limit exceeded',
                    'retry_after': period
                }, status=429)

            cache.set(cache_key, calls + 1, period)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def retry(max_attempts: int = 3, delay: float = 1.0, exceptions: tuple = (Exception,)):
    """Decorator to retry function on failure."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        raise
                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt + 1}/{max_attempts}): {e}"
                    )
                    time.sleep(delay * (attempt + 1))
        return wrapper
    return decorator


def require_authentication(func: Callable) -> Callable:
    """Decorator to require authentication."""
    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {'error': 'Authentication required'},
                status=401
            )
        return func(request, *args, **kwargs)
    return wrapper


def log_api_call(func: Callable) -> Callable:
    """Decorator to log API calls."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        logger.info(f"API call: {func.__name__}")

        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(f"API call {func.__name__} completed in {duration:.3f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"API call {func.__name__} failed after {duration:.3f}s: {e}"
            )
            raise
    return wrapper


class classproperty:
    """Descriptor for class-level properties."""

    def __init__(self, func):
        self.func = func

    def __get__(self, obj, objtype=None):
        return self.func(objtype)
