"""
Execution cache service for node execution caching based on config hash.
Enables idempotent execution and cache reuse.
"""

import copy
import hashlib
import json
import logging
from datetime import timedelta
from typing import Any, Dict, Optional

from django.utils import timezone

logger = logging.getLogger(__name__)


class ExecutionCacheService:
    """
    Node execution cache service.
    
    Uses node config hash as cache key, supporting:
    - Idempotent execution (identical config returns cached result)
    - Smart TTL (different expiration times per node type)
    - Cache statistics (hit rate, access count)
    - Manual invalidation (clear related cache on config change)
    """
    
    def __init__(self):
        self._cache_config = None  # Local cache config to reduce DB queries
    
    def _get_cache_config(self, node_type: str) -> Dict[str, Any]:
        """Get cache configuration for a node type."""
        from workflows.models import ExecutionCacheConfig
        
        if self._cache_config is None:
            configs = ExecutionCacheConfig.objects.all()
            self._cache_config = {c.node_type: c for c in configs}
        
        if node_type in self._cache_config:
            config = self._cache_config[node_type]
            return {
                'enabled': config.enabled,
                'ttl_hours': config.ttl_hours,
            }
        
        # Default configuration
        return {'enabled': True, 'ttl_hours': 24}
    
    def compute_config_hash(
        self, 
        node_config: Dict[str, Any], 
        exclude_fields: Optional[list] = None
    ) -> str:
        """
        Compute hash for node configuration.
        
        Excludes runtime fields like execution_id, retry_count, timestamp.
        
        Args:
            node_config: The node configuration dict
            exclude_fields: List of field names to exclude from hash
            
        Returns:
            SHA-256 hex hash string
        """
        exclude_fields = exclude_fields or [
            'execution_id', 'node_execution_id', 'retry_count',
            'timestamp', '_timestamp', 'request_id', 'session_id',
            'cached', 'cache_hit', 'cache_key',
        ]
        
        # Deep copy to avoid modifying original config
        config_copy = copy.deepcopy(node_config)
        
        # Remove runtime fields
        for field in exclude_fields:
            if field in config_copy:
                del config_copy[field]
        
        # Normalize JSON (sort keys)
        config_str = json.dumps(config_copy, sort_keys=True, ensure_ascii=False)
        
        # SHA-256 hash
        return hashlib.sha256(config_str.encode('utf-8')).hexdigest()
    
    def get(
        self, 
        node_config: Dict[str, Any], 
        node_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Try to get result from cache.
        
        Args:
            node_config: The node configuration
            node_type: Type of the node
            
        Returns:
            Cached output_data or None (cache miss)
        """
        config = self._get_cache_config(node_type)
        if not config['enabled']:
            logger.debug(f"Cache disabled for node type: {node_type}")
            return None
        
        config_hash = self.compute_config_hash(node_config)
        
        try:
            from workflows.models import ExecutionCache
            
            cache_entry = ExecutionCache.objects.get(
                config_hash=config_hash,
                node_type=node_type,
                is_valid=True,
            )
            
            # Check expiration
            if cache_entry.is_expired:
                cache_entry.invalidate()
                logger.debug(f"Cache expired for {node_type}@{config_hash[:8]}")
                return None
            
            # Update access statistics
            cache_entry.access_count += 1
            cache_entry.last_accessed = timezone.now()
            cache_entry.save(update_fields=['access_count', 'last_accessed'])
            
            logger.info(
                f"Cache HIT for {node_type}@{config_hash[:8]} "
                f"(hit #{cache_entry.access_count})"
            )
            return cache_entry.output_data
            
        except ExecutionCache.DoesNotExist:
            logger.debug(f"Cache MISS for {node_type}@{config_hash[:8]}")
            return None
    
    def set(
        self, 
        node_config: Dict[str, Any], 
        node_type: str, 
        output_data: Dict[str, Any]
    ) -> Optional[str]:
        """
        Store execution result to cache.
        
        Args:
            node_config: The node configuration
            node_type: Type of the node
            output_data: The execution output to cache
            
        Returns:
            config_hash or None if caching is disabled
        """
        config = self._get_cache_config(node_type)
        if not config['enabled']:
            return None
        
        config_hash = self.compute_config_hash(node_config)
        
        try:
            from workflows.models import ExecutionCache
            
            # Compute checksum for output data
            output_str = json.dumps(output_data, sort_keys=True, ensure_ascii=False)
            checksum = hashlib.sha256(output_str.encode('utf-8')).hexdigest()
            
            # Calculate expiration time
            expires_at = timezone.now() + timedelta(hours=config['ttl_hours'])
            
            cache_entry, created = ExecutionCache.objects.update_or_create(
                config_hash=config_hash,
                defaults={
                    'node_type': node_type,
                    'node_config': node_config,
                    'output_data': output_data,
                    'checksum': checksum,
                    'is_valid': True,
                    'expires_at': expires_at,
                }
            )
            
            logger.info(
                f"Cache {'SET' if created else 'UPDATE'} for "
                f"{node_type}@{config_hash[:8]}"
            )
            return config_hash
            
        except Exception as e:
            logger.error(f"Failed to set cache: {e}")
            return None
    
    def invalidate(
        self, 
        node_type: Optional[str] = None, 
        config_hash: Optional[str] = None
    ) -> int:
        """
        Manually invalidate cache entries.
        
        Args:
            node_type: Invalidate all caches for this node type
            config_hash: Invalidate specific cache entry by hash
            
        Returns:
            Number of invalidated entries
        """
        from workflows.models import ExecutionCache
        
        if config_hash:
            count = ExecutionCache.objects.filter(config_hash=config_hash).update(
                is_valid=False
            )
            logger.info(f"Invalidated cache by hash: {config_hash[:8]} ({count} entries)")
        elif node_type:
            count = ExecutionCache.objects.filter(node_type=node_type).update(
                is_valid=False
            )
            logger.info(f"Invalidated cache for node_type: {node_type} ({count} entries)")
        else:
            count = 0
            
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with total, valid, expired counts and per-node-type breakdown
        """
        from workflows.models import ExecutionCache
        from django.db.models import Count, Avg
        
        total = ExecutionCache.objects.count()
        valid = ExecutionCache.objects.filter(is_valid=True).count()
        
        # Count expired (valid but past expiration time)
        expired = ExecutionCache.objects.filter(
            is_valid=True,
            expires_at__lt=timezone.now(),
        ).count()
        
        # Stats by node type
        by_type = ExecutionCache.objects.values('node_type').annotate(
            count=Count('id'),
            avg_access=Avg('access_count'),
        ).order_by('-count')
        
        return {
            'total': total,
            'valid': valid,
            'expired': expired,
            'invalid': total - valid,
            'by_node_type': list(by_type),
            'hit_rate': self._compute_hit_rate(),
        }
    
    def _compute_hit_rate(self) -> float:
        """
        Compute cache hit rate estimate.
        
        Returns:
            Hit rate as percentage (0-100)
        """
        from workflows.models import ExecutionCache
        
        total = ExecutionCache.objects.count()
        if total == 0:
            return 0.0
        
        accessed = ExecutionCache.objects.filter(access_count__gt=0).count()
        return round(accessed / total * 100, 1)
    
    def cleanup_expired(self) -> int:
        """
        Clean up expired cache entries.
        
        Returns:
            Number of cleaned entries
        """
        from workflows.models import ExecutionCache
        
        expired = ExecutionCache.objects.filter(
            is_valid=True,
            expires_at__lt=timezone.now(),
        )
        count = expired.count()
        expired.update(is_valid=False)
        
        if count > 0:
            logger.info(f"Cleaned up {count} expired cache entries")
        
        return count
    
    def get_size_info(self) -> Dict[str, Any]:
        """
        Get cache size information.
        
        Returns:
            Dict with size metrics per node type
        """
        from workflows.models import ExecutionCache
        from django.db.models import Sum
        
        # Get total count and approximate size by type
        by_type = ExecutionCache.objects.filter(
            is_valid=True
        ).values(
            'node_type'
        ).annotate(
            count=Count('id'),
        ).order_by('-count')
        
        total = sum(item['count'] for item in by_type)
        
        return {
            'total_entries': total,
            'by_node_type': list(by_type),
        }
    
    def refresh_config_cache(self) -> None:
        """Refresh local cache config from database."""
        from workflows.models import ExecutionCacheConfig
        
        configs = ExecutionCacheConfig.objects.all()
        self._cache_config = {c.node_type: c for c in configs}
        logger.debug("Refreshed local cache config")
