"""
Graph Cache - 多级缓存策略
支持内存缓存和 Redis 缓存，按文件修改时间失效
"""

import json
import os
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from functools import wraps
import hashlib

from .parser import CodeStructure
from .analyzer import AnalysisResult


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: float
    updated_at: float
    version: str
    file_mtimes: Dict[str, float]  # 关联文件的修改时间

    def is_valid(self, current_mtimes: Dict[str, float] = None) -> bool:
        """检查缓存是否仍然有效"""
        if current_mtimes is None:
            return True
        # 如果任何关联文件被修改，缓存失效
        for path, mtime in self.file_mtimes.items():
            if path not in current_mtimes or current_mtimes[path] != mtime:
                return False
        return True

    def to_dict(self) -> dict:
        return {
            'key': self.key,
            'value': self.value,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'version': self.version,
            'file_mtimes': self.file_mtimes,
        }


class MemoryCache:
    """
    内存缓存 (L1)
    线程安全，使用 LRU 策略
    """

    def __init__(self, max_size: int = 100, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []  # LRU 顺序
        self._lock = threading.RLock()

    def get(self, key: str, current_mtimes: Dict[str, float] = None) -> Optional[Any]:
        """获取缓存"""
        with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]

            # 检查 TTL
            if time.time() - entry.created_at > self.ttl:
                del self._cache[key]
                self._access_order.remove(key)
                return None

            # 检查文件修改时间
            if not entry.is_valid(current_mtimes):
                del self._cache[key]
                self._access_order.remove(key)
                return None

            # 更新访问顺序 (LRU)
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)

            return entry.value

    def set(self, key: str, value: Any, file_mtimes: Dict[str, float] = None):
        """设置缓存"""
        with self._lock:
            # LRU 淘汰
            if len(self._cache) >= self.max_size and key not in self._cache:
                oldest = self._access_order.pop(0)
                del self._cache[oldest]

            now = time.time()
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                updated_at=now,
                version=self._compute_version(value),
                file_mtimes=file_mtimes or {},
            )
            self._cache[key] = entry

            if key not in self._access_order:
                self._access_order.append(key)

    def delete(self, key: str):
        """删除缓存"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._access_order.remove(key)

    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()

    def _compute_version(self, value: Any) -> str:
        """计算值的版本哈希"""
        serialized = json.dumps(value, sort_keys=True, default=str)
        return hashlib.md5(serialized.encode()).hexdigest()[:12]

    def get_stats(self) -> dict:
        """获取缓存统计"""
        with self._lock:
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'ttl': self.ttl,
            }


class RedisCache:
    """
    Redis 缓存 (L2)
    用于分布式环境下的缓存共享
    """

    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._enabled = redis_client is not None
        self._prefix = 'codegraph:cache:'
        self._default_ttl = 3600 * 24  # 24 小时

    def get(self, key: str, current_mtimes: Dict[str, float] = None) -> Optional[Any]:
        """获取缓存"""
        if not self._enabled:
            return None

        try:
            cache_key = f"{self._prefix}{key}"
            data = self._redis.get(cache_key)
            if not data:
                return None

            entry_data = json.loads(data)
            entry = CacheEntry(**entry_data)

            # 检查文件修改时间
            if not entry.is_valid(current_mtimes):
                self.delete(key)
                return None

            return entry.value
        except Exception:
            return None

    def set(self, key: str, value: Any, file_mtimes: Dict[str, float] = None, ttl: int = None):
        """设置缓存"""
        if not self._enabled:
            return

        try:
            cache_key = f"{self._prefix}{key}"
            now = time.time()

            entry = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                updated_at=now,
                version=self._compute_version(value),
                file_mtimes=file_mtimes or {},
            )

            self._redis.setex(
                cache_key,
                ttl or self._default_ttl,
                json.dumps(entry.to_dict(), default=str),
            )
        except Exception:
            pass

    def delete(self, key: str):
        """删除缓存"""
        if not self._enabled:
            return

        try:
            self._redis.delete(f"{self._prefix}{key}")
        except Exception:
            pass

    def clear(self):
        """清空所有缓存"""
        if not self._enabled:
            return

        try:
            keys = self._redis.keys(f"{self._prefix}*")
            if keys:
                self._redis.delete(*keys)
        except Exception:
            pass

    def _compute_version(self, value: Any) -> str:
        """计算值的版本哈希"""
        serialized = json.dumps(value, sort_keys=True, default=str)
        return hashlib.md5(serialized.encode()).hexdigest()[:12]


class GraphCache:
    """
    多级缓存管理器
    L1: MemoryCache (进程内)
    L2: RedisCache (分布式)
    """

    def __init__(self, redis_client=None, memory_size: int = 100, memory_ttl: int = 3600):
        self._memory = MemoryCache(max_size=memory_size, ttl=memory_ttl)
        self._redis = RedisCache(redis_client)

    def get(self, key: str, current_mtimes: Dict[str, float] = None) -> Optional[Any]:
        """获取缓存，先查内存，再查 Redis"""
        # L1 内存缓存
        value = self._memory.get(key, current_mtimes)
        if value is not None:
            return value

        # L2 Redis 缓存
        value = self._redis.get(key, current_mtimes)
        if value is not None:
            # 回填内存缓存
            self._memory.set(key, value, current_mtimes)
            return value

        return None

    def set(self, key: str, value: Any, file_mtimes: Dict[str, float] = None, ttl: int = None):
        """设置缓存，同时写入内存和 Redis"""
        self._memory.set(key, value, file_mtimes)
        self._redis.set(key, value, file_mtimes, ttl)

    def delete(self, key: str):
        """删除缓存"""
        self._memory.delete(key)
        self._redis.delete(key)

    def invalidate_project(self, project_id: int):
        """失效项目相关的所有缓存"""
        key = f"project:{project_id}"
        self._memory.delete(key)
        self._redis.delete(key)

    def clear(self):
        """清空所有缓存"""
        self._memory.clear()
        self._redis.clear()

    def get_stats(self) -> dict:
        """获取缓存统计"""
        return {
            'memory': self._memory.get_stats(),
            'redis_enabled': self._redis._enabled,
        }


class ProjectCache:
    """
    项目级别的缓存管理
    提供项目结构的缓存和失效策略
    """

    def __init__(self, cache: GraphCache):
        self._cache = cache

    def get_structure(self, project_id: int, project_path: str) -> Optional[CodeStructure]:
        """获取项目结构缓存"""
        key = f"structure:{project_id}"
        data = self._cache.get(key)
        if not data or os.path.realpath(data['root_path']) != os.path.realpath(project_path):
            return None
        return CodeStructure.from_dict(data)

    def set_structure(self, project_id: int, structure: CodeStructure):
        """设置项目结构缓存"""
        key = f"structure:{project_id}"
        # 收集所有文件的修改时间
        file_mtimes = {}
        for node in structure.nodes:
            full_path = os.path.join(structure.root_path, node.path)
            if os.path.exists(full_path):
                file_mtimes[full_path] = os.path.getmtime(full_path)

        self._cache.set(key, structure.to_dict(), file_mtimes)

    def get_analysis(self, project_id: int) -> Optional[AnalysisResult]:
        """获取分析结果缓存"""
        key = f"analysis:{project_id}"
        data = self._cache.get(key)
        if data:
            return AnalysisResult(**data)
        return None

    def set_analysis(self, project_id: int, analysis: AnalysisResult):
        """设置分析结果缓存"""
        key = f"analysis:{project_id}"
        self._cache.set(key, analysis.to_dict())

    def invalidate(self, project_id: int):
        """失效项目缓存"""
        self._cache.delete(f"structure:{project_id}")
        self._cache.delete(f"analysis:{project_id}")
        self._cache.delete(f"modules:{project_id}")

    def invalidate_file(self, project_id: int, file_path: str):
        """失效单个文件相关的缓存"""
        # 简单策略：文件变化时失效整个项目
        self.invalidate(project_id)


def cached(cache: GraphCache, key_func=None):
    """
    缓存装饰器
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存 key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # 默认使用函数名和参数生成 key
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)

            # 尝试获取缓存
            result = cache.get(cache_key)
            if result is not None:
                return result

            # 执行函数
            result = func(*args, **kwargs)

            # 设置缓存
            if result is not None:
                cache.set(cache_key, result)

            return result
        return wrapper
    return decorator
