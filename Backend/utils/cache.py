"""
Caching utilities for performance optimization.
"""

import hashlib
import json
import logging
from typing import Any, Callable, Optional, Union
from functools import wraps
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


class CacheKeys:
    """Cache key generators."""

    @staticmethod
    def workflow(workflow_id: int) -> str:
        return f"workflow:{workflow_id}"

    @staticmethod
    def agent(agent_id: int) -> str:
        return f"agent:{agent_id}"

    @staticmethod
    def user(user_id: int) -> str:
        return f"user:{user_id}"

    @staticmethod
    def tenant(tenant_id: int) -> str:
        return f"tenant:{tenant_id}"

    @staticmethod
    def workflow_run(run_id: int) -> str:
        return f"workflow_run:{run_id}"

    @staticmethod
    def dashboard(user_id: int) -> str:
        return f"dashboard:{user_id}"

    @staticmethod
    def model_list() -> str:
        return "model_list"

    @staticmethod
    def provider_list() -> str:
        return "provider_list"


def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """Generate a cache key from prefix and arguments."""
    key_parts = [prefix]
    for arg in args:
        key_parts.append(str(arg))
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}:{v}")
    return ":".join(key_parts)


def md5_key(*args, **kwargs) -> str:
    """Generate MD5 hash as cache key."""
    key_string = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
    return hashlib.md5(key_string.encode()).hexdigest()


class CacheManager:
    """Centralized cache management."""

    DEFAULT_TIMEOUT = 300  # 5 minutes

    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        """Get value from cache."""
        try:
            return cache.get(key, default)
        except Exception as e:
            logger.error(f"Cache get error for {key}: {e}")
            return default

    @staticmethod
    def set(key: str, value: Any, timeout: int = None) -> bool:
        """Set value in cache."""
        try:
            cache.set(key, value, timeout or CacheManager.DEFAULT_TIMEOUT)
            return True
        except Exception as e:
            logger.error(f"Cache set error for {key}: {e}")
            return False

    @staticmethod
    def delete(key: str) -> bool:
        """Delete key from cache."""
        try:
            cache.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error for {key}: {e}")
            return False

    @staticmethod
    def get_or_set(key: str, callable_func: Callable, timeout: int = None) -> Any:
        """Get from cache or set if not exists."""
        value = CacheManager.get(key)
        if value is None:
            value = callable_func()
            CacheManager.set(key, value, timeout)
        return value

    @staticmethod
    def invalidate(key: str) -> bool:
        """Invalidate cache key."""
        return CacheManager.delete(key)

    @staticmethod
    def invalidate_pattern(pattern: str) -> int:
        """Invalidate all keys matching pattern."""
        try:
            from django.core.cache import caches
            count = 0
            for cache_alias in caches:
                c = caches[cache_alias]
                if hasattr(c, 'delete_pattern'):
                    c.delete_pattern(pattern)
                    count += 1
            return count
        except Exception as e:
            logger.error(f"Cache invalidate pattern error: {e}")
            return 0


def cached(
    timeout: int = 300,
    key_prefix: str = "",
    unless: Callable = None,
    force_key: str = None
):
    """Decorator to cache function results."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check unless condition
            if unless and unless(*args, **kwargs):
                return func(*args, **kwargs)

            # Generate cache key
            if force_key:
                cache_key = force_key
            else:
                key_parts = [key_prefix or func.__module__, func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)

            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result

            # Execute function
            result = func(*args, **kwargs)

            # Cache result
            try:
                cache.set(cache_key, result, timeout)
            except Exception as e:
                logger.error(f"Failed to cache result: {e}")

            return result
        return wrapper
    return decorator


def cache_view(timeout: int = 60, key_prefix: str = "view"):
    """Decorator to cache view responses."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # Generate cache key based on request
            cache_key = f"{key_prefix}:{request.path}"
            if request.user.is_authenticated:
                cache_key += f":user:{request.user.id}"

            # Check cache
            cached_response = cache.get(cache_key)
            if cached_response is not None:
                return cached_response

            # Execute view
            response = func(request, *args, **kwargs)

            # Cache response
            try:
                cache.set(cache_key, response, timeout)
            except Exception as e:
                logger.error(f"Failed to cache view: {e}")

            return response
        return wrapper
    return decorator


class RedisCache:
    """Redis-specific cache operations."""

    @staticmethod
    def exists(key: str) -> bool:
        """Check if key exists."""
        try:
            return cache.get(f"exists:{key}") is not None
        except Exception:
            return False

    @staticmethod
    def increment(key: str, delta: int = 1) -> Optional[int]:
        """Increment counter."""
        try:
            return cache.incr(key, delta)
        except Exception as e:
            logger.error(f"Cache increment error: {e}")
            return None

    @staticmethod
    def decrement(key: str, delta: int = 1) -> Optional[int]:
        """Decrement counter."""
        try:
            return cache.decr(key, delta)
        except Exception as e:
            logger.error(f"Cache decrement error: {e}")
            return None

    @staticmethod
    def ttl(key: str) -> Optional[int]:
        """Get time-to-live for key."""
        try:
            from django.core.cache import cache as default_cache
            if hasattr(default_cache, 'ttl'):
                return default_cache.ttl(key)
        except Exception:
            pass
        return None
