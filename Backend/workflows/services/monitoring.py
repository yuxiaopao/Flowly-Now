"""
Enhanced monitoring and observability utilities for the backend.

Provides:
- Prometheus metrics collection
- Structured JSON logging
- Execution statistics tracking
- Health check endpoints
- Performance profiling
"""

import logging
import time
import json
import threading
import traceback
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, Optional, List, Callable
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from contextlib import contextmanager

from django.conf import settings
from django.utils import timezone
from django.db.models import Q, F, Count, Avg, Sum, Max, Min
from django.utils.module_loading import import_string

from Backend.utils.helpers import get_client_ip

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
# Prometheus Metrics
# ─────────────────────────────────────────────────────────────────

class PrometheusMetrics:
    """
    Prometheus metrics collector for workflow and API monitoring.
    
    Provides counters, gauges, histograms, and summaries.
    Metrics are exposed via /metrics endpoint.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init_metrics()
        return cls._instance
    
    def _init_metrics(self):
        """Initialize metric storage."""
        self._counters: Dict[str, float] = defaultdict(float)
        self._counters_labels: Dict[str, Dict[tuple, float]] = defaultdict(lambda: defaultdict(float))
        self._gauges: Dict[str, float] = defaultdict(float)
        self._gauges_labels: Dict[str, Dict[tuple, float]] = defaultdict(lambda: defaultdict(float))
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._histograms_labels: Dict[str, Dict[tuple, List[float]]] = defaultdict(lambda: defaultdict(list))
        self._summaries: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {'count': 0, 'sum': 0, 'total': 0}
        )
        self._summaries_labels: Dict[str, Dict[tuple, Dict[str, float]]] = defaultdict(
            lambda: defaultdict(lambda: {'count': 0, 'sum': 0})
        )
        self._histogram_buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        self._reset_interval = 60  # seconds
        self._last_reset = time.time()
    
    # ─────────────────────────────────────────────────────────────
    # Counters
    # ─────────────────────────────────────────────────────────────
    
    def counter_inc(self, name: str, value: float = 1, **labels):
        """Increment a counter metric."""
        self._counters[name] += value
        if labels:
            key = tuple(sorted(labels.items()))
            self._counters_labels[name][key] += value
    
    def counter_get(self, name: str, **labels) -> float:
        """Get counter value."""
        if labels:
            key = tuple(sorted(labels.items()))
            return self._counters_labels[name].get(key, 0)
        return self._counters[name]
    
    # ─────────────────────────────────────────────────────────────
    # Gauges
    # ─────────────────────────────────────────────────────────────
    
    def gauge_set(self, name: str, value: float, **labels):
        """Set a gauge value."""
        self._gauges[name] = value
        if labels:
            key = tuple(sorted(labels.items()))
            self._gauges_labels[name][key] = value
    
    def gauge_inc(self, name: str, value: float = 1, **labels):
        """Increment a gauge."""
        if labels:
            key = tuple(sorted(labels.items()))
            self._gauges_labels[name][key] += value
        else:
            self._gauges[name] += value
    
    def gauge_dec(self, name: str, value: float = 1, **labels):
        """Decrement a gauge."""
        if labels:
            key = tuple(sorted(labels.items()))
            self._gauges_labels[name][key] -= value
        else:
            self._gauges[name] -= value
    
    def gauge_get(self, name: str, **labels) -> float:
        """Get gauge value."""
        if labels:
            key = tuple(sorted(labels.items()))
            return self._gauges_labels[name].get(key, 0)
        return self._gauges[name]
    
    # ─────────────────────────────────────────────────────────────
    # Histograms
    # ─────────────────────────────────────────────────────────────
    
    def histogram_observe(self, name: str, value: float, **labels):
        """Observe a value for histogram."""
        self._histograms[name].append(value)
        if labels:
            key = tuple(sorted(labels.items()))
            self._histograms_labels[name][key].append(value)
    
    def histogram_get_stats(self, name: str, **labels) -> Dict[str, float]:
        """Get histogram statistics."""
        if labels:
            key = tuple(sorted(labels.items()))
            values = self._histograms_labels[name].get(key, [])
        else:
            values = self._histograms[name]
        
        if not values:
            return {}
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        return {
            'count': n,
            'sum': sum(values),
            'mean': sum(values) / n,
            'min': sorted_values[0],
            'max': sorted_values[-1],
            'p50': sorted_values[int(n * 0.5)],
            'p90': sorted_values[int(n * 0.9)],
            'p95': sorted_values[int(n * 0.95)],
            'p99': sorted_values[int(n * 0.99)],
        }
    
    # ─────────────────────────────────────────────────────────────
    # Summaries
    # ─────────────────────────────────────────────────────────────
    
    def summary_observe(self, name: str, value: float, **labels):
        """Observe a value for summary."""
        self._summaries[name]['count'] += 1
        self._summaries[name]['sum'] += value
        self._summaries[name]['total'] += value
        
        if labels:
            key = tuple(sorted(labels.items()))
            s = self._summaries_labels[name][key]
            s['count'] += 1
            s['sum'] += value
    
    def summary_get(self, name: str, **labels) -> Dict[str, float]:
        """Get summary statistics."""
        if labels:
            key = tuple(sorted(labels.items()))
            s = self._summaries_labels[name].get(key, {})
        else:
            s = self._summaries[name]
        
        if not s or s['count'] == 0:
            return {}
        
        return {
            'count': s['count'],
            'sum': s['sum'],
            'mean': s['sum'] / s['count'],
        }
    
    # ─────────────────────────────────────────────────────────────
    # Metric Helpers
    # ─────────────────────────────────────────────────────────────
    
    def record_request(self, method: str, path: str, status: int, duration: float):
        """Record an HTTP request metric."""
        self.counter_inc('http_requests_total', method=method, path=path, status=str(status))
        self.histogram_observe('http_request_duration_seconds', duration, method=method, path=path)
        self.gauge_inc('http_requests_in_progress', method=method, path=path)
        self.gauge_dec('http_requests_in_progress', method=method, path=path)
    
    def record_workflow_execution(self, workflow_id: str, status: str, duration: float):
        """Record workflow execution metric."""
        self.counter_inc('workflow_executions_total', workflow_id=workflow_id, status=status)
        self.histogram_observe('workflow_execution_duration_seconds', duration, workflow_id=workflow_id)
        self.counter_inc('workflow_executions_by_status', status=status)
    
    def record_llm_call(self, model: str, tokens: int, duration: float, success: bool):
        """Record LLM API call metric."""
        self.counter_inc('llm_calls_total', model=model, success=str(success))
        self.histogram_observe('llm_call_duration_seconds', duration, model=model)
        self.counter_inc('llm_tokens_total', tokens, model=model)
    
    def record_sandbox_execution(self, sandbox_type: str, status: str, duration: float):
        """Record sandbox execution metric."""
        self.counter_inc('sandbox_executions_total', sandbox_type=sandbox_type, status=status)
        self.histogram_observe('sandbox_execution_duration_seconds', duration, sandbox_type=sandbox_type)
    
    # ─────────────────────────────────────────────────────────────
    # Prometheus Format Export
    # ─────────────────────────────────────────────────────────────
    
    def to_prometheus_text(self) -> str:
        """Export metrics in Prometheus text format."""
        lines = []
        
        # Counters
        for name, value in sorted(self._counters.items()):
            lines.append(f'# TYPE {name} counter')
            lines.append(f'{name} {value}')
        
        for name, label_values in sorted(self._counters_labels.items()):
            for labels, value in label_values.items():
                label_str = ','.join(f'{k}="{v}"' for k, v in labels)
                lines.append(f'# TYPE {name} counter')
                lines.append(f'{name}{{{label_str}}} {value}')
        
        # Gauges
        for name, value in sorted(self._gauges.items()):
            lines.append(f'# TYPE {name} gauge')
            lines.append(f'{name} {value}')
        
        for name, label_values in sorted(self._gauges_labels.items()):
            for labels, value in label_values.items():
                label_str = ','.join(f'{k}="{v}"' for k, v in labels)
                lines.append(f'# TYPE {name} gauge')
                lines.append(f'{name}{{{label_str}}} {value}')
        
        # Histograms
        for name, values in sorted(self._histograms.items()):
            if values:
                sorted_values = sorted(values)
                n = len(sorted_values)
                total = sum(values)
                
                lines.append(f'# TYPE {name} histogram')
                lines.append(f'{name}_count {n}')
                lines.append(f'{name}_sum {total}')
                
                for bucket in self._histogram_buckets:
                    bucket_count = sum(1 for v in sorted_values if v <= bucket)
                    lines.append(f'{name}_bucket{{le="{bucket}"}} {bucket_count}')
                lines.append(f'{name}_bucket{{le="+Inf"}} {n}')
        
        # Summaries
        for name, stats in sorted(self._summaries.items()):
            if stats['count'] > 0:
                lines.append(f'# TYPE {name} summary')
                lines.append(f'{name}_count {stats["count"]}')
                lines.append(f'{name}_sum {stats["sum"]}')
        
        return '\n'.join(lines) + '\n'
    
    def reset(self):
        """Reset all metrics (for testing or periodic reset)."""
        self._init_metrics()
        self._last_reset = time.time()
    
    def get_all_metrics(self) -> Dict:
        """Get all metrics as dictionary."""
        return {
            'counters': dict(self._counters),
            'gauges': dict(self._gauges),
            'histograms': {k: self.histogram_get_stats(k) for k in self._histograms},
            'summaries': {k: dict(v) for k, v in self._summaries.items()},
        }


# Global metrics instance
metrics = PrometheusMetrics()


def get_metrics() -> PrometheusMetrics:
    """Get the global Prometheus metrics instance."""
    return metrics


# ─────────────────────────────────────────────────────────────────
# Structured Logging
# ─────────────────────────────────────────────────────────────────

class StructuredLogger:
    """
    Structured JSON logger for consistent log formatting.
    
    Provides context-aware logging with automatic field enrichment.
    """
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._context: Dict[str, Any] = {}
    
    def set_context(self, **kwargs):
        """Set context fields for all subsequent logs."""
        self._context.update(kwargs)
    
    def clear_context(self):
        """Clear context fields."""
        self._context = {}
    
    def _build_record(self, level: str, message: str, **extra) -> Dict[str, Any]:
        """Build structured log record."""
        record = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': level,
            'message': message,
            'logger': self.logger.name,
            **self._context,
            **extra,
        }
        return record
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        record = self._build_record('DEBUG', message, **kwargs)
        self.logger.debug(json.dumps(record))
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        record = self._build_record('INFO', message, **kwargs)
        self.logger.info(json.dumps(record))
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        record = self._build_record('WARNING', message, **kwargs)
        self.logger.warning(json.dumps(record))
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        record = self._build_record('ERROR', message, **kwargs)
        self.logger.error(json.dumps(record))
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        record = self._build_record('CRITICAL', message, **kwargs)
        self.logger.critical(json.dumps(record))


def get_structured_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance."""
    return StructuredLogger(name)


# ─────────────────────────────────────────────────────────────────
# Execution Metrics
# ─────────────────────────────────────────────────────────────────

@dataclass
class ExecutionRecord:
    """Record of a workflow execution for metrics."""
    execution_id: str
    workflow_id: str
    user_id: Optional[int]
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str = 'running'
    duration_ms: int = 0
    node_count: int = 0
    success_count: int = 0
    error_count: int = 0
    token_usage: int = 0
    error_type: Optional[str] = None
    error_message: Optional[str] = None


class ExecutionMetrics:
    """
    Enhanced workflow execution metrics tracking.
    
    Tracks:
    - Execution counts and rates
    - Duration distributions
    - Success/failure rates
    - Token usage
    - Error patterns
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        self._executions: Dict[str, ExecutionRecord] = {}
        self._execution_history: List[ExecutionRecord] = []
        self._max_history = 10000
    
    def start_execution(
        self,
        execution_id: str,
        workflow_id: str,
        user_id: Optional[int] = None
    ) -> ExecutionRecord:
        """Record start of execution."""
        record = ExecutionRecord(
            execution_id=execution_id,
            workflow_id=workflow_id,
            user_id=user_id,
            started_at=datetime.utcnow(),
        )
        
        with self._lock:
            self._executions[execution_id] = record
        
        # Update Prometheus metrics
        metrics.gauge_inc('workflow_executions_in_progress')
        metrics.counter_inc('workflow_executions_started', workflow_id=workflow_id)
        
        return record
    
    def complete_execution(
        self,
        execution_id: str,
        status: str = 'completed',
        node_count: int = 0,
        success_count: int = 0,
        error_count: int = 0,
        token_usage: int = 0,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        """Record completion of execution."""
        with self._lock:
            if execution_id not in self._executions:
                logger.warning(f"Execution {execution_id} not found")
                return
            
            record = self._executions[execution_id]
            record.completed_at = datetime.utcnow()
            record.status = status
            record.duration_ms = int((record.completed_at - record.started_at).total_seconds() * 1000)
            record.node_count = node_count
            record.success_count = success_count
            record.error_count = error_count
            record.token_usage = token_usage
            record.error_type = error_type
            record.error_message = error_message
            
            # Move to history
            self._execution_history.append(record)
            del self._executions[execution_id]
            
            # Trim history
            if len(self._execution_history) > self._max_history:
                self._execution_history = self._execution_history[-self._max_history:]
        
        # Update Prometheus metrics
        metrics.gauge_dec('workflow_executions_in_progress')
        metrics.histogram_observe('workflow_execution_duration_ms', record.duration_ms)
        metrics.counter_inc('workflow_executions_completed', status=status)
        
        if token_usage > 0:
            metrics.counter_inc('workflow_tokens_total', token_usage)
    
    def record_node_execution(
        self,
        execution_id: str,
        node_id: str,
        status: str,
        duration_ms: int,
    ):
        """Record individual node execution."""
        metrics.histogram_observe('workflow_node_execution_duration_ms', duration_ms)
        metrics.counter_inc('workflow_node_executions', status=status)
    
    def get_execution_stats(
        self,
        workflow_id: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get execution statistics."""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        with self._lock:
            records = [
                r for r in self._execution_history
                if r.started_at >= since
                and (workflow_id is None or r.workflow_id == workflow_id)
            ]
        
        if not records:
            return {
                'total_executions': 0,
                'successful': 0,
                'failed': 0,
                'avg_duration_ms': 0,
                'total_tokens': 0,
            }
        
        completed = [r for r in records if r.status == 'completed']
        failed = [r for r in records if r.status == 'failed']
        
        durations = [r.duration_ms for r in records if r.duration_ms > 0]
        
        return {
            'total_executions': len(records),
            'successful': len(completed),
            'failed': len(failed),
            'success_rate': len(completed) / len(records) if records else 0,
            'avg_duration_ms': sum(durations) / len(durations) if durations else 0,
            'p50_duration_ms': sorted(durations)[len(durations) // 2] if durations else 0,
            'p95_duration_ms': sorted(durations)[int(len(durations) * 0.95)] if durations else 0,
            'p99_duration_ms': sorted(durations)[int(len(durations) * 0.99)] if durations else 0,
            'total_tokens': sum(r.token_usage for r in records),
            'total_nodes': sum(r.node_count for r in records),
            'period_hours': hours,
        }
    
    def get_error_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get error statistics."""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        with self._lock:
            errors = [
                r for r in self._execution_history
                if r.started_at >= since and r.status == 'failed'
            ]
        
        error_counts: Dict[str, int] = defaultdict(int)
        for r in errors:
            if r.error_type:
                error_counts[r.error_type] += 1
        
        return {
            'total_errors': len(errors),
            'error_types': dict(error_counts),
            'most_common': sorted(error_counts.items(), key=lambda x: -x[1])[:10],
            'period_hours': hours,
        }


# Global execution metrics
_execution_metrics: Optional[ExecutionMetrics] = None
_metrics_lock = threading.Lock()


def get_execution_metrics() -> ExecutionMetrics:
    """Get the global execution metrics instance."""
    global _execution_metrics
    if _execution_metrics is None:
        with _metrics_lock:
            if _execution_metrics is None:
                _execution_metrics = ExecutionMetrics()
    return _execution_metrics


# ─────────────────────────────────────────────────────────────────
# Request Logger (Enhanced)
# ─────────────────────────────────────────────────────────────────

class RequestLogger:
    """Enhanced API request logger with structured logging."""
    
    _structured_logger = get_structured_logger('api.requests')
    
    @classmethod
    def log_request(cls, request, response=None, duration: float = None):
        """Log an API request with structured format."""
        log_data = {
            'method': request.method,
            'path': request.path,
            'query': dict(request.GET),
            'user': request.user.username if hasattr(request, 'user') and request.user.is_authenticated else 'anonymous',
            'ip': get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
        }
        
        if response:
            log_data['status_code'] = response.status_code
        
        if duration is not None:
            log_data['duration_ms'] = round(duration * 1000, 2)
        
        # Record Prometheus metrics
        if response:
            metrics.record_request(request.method, request.path, response.status_code, duration or 0)
        
        # Log with appropriate level
        if response and response.status_code >= 500:
            cls._structured_logger.error('API request failed', **log_data)
        elif response and response.status_code >= 400:
            cls._structured_logger.warning('API request client error', **log_data)
        else:
            cls._structured_logger.info('API request', **log_data)
    
    @classmethod
    def log_error(cls, request, error: Exception, duration: float = None):
        """Log an API error."""
        log_data = {
            'method': request.method,
            'path': request.path,
            'user': request.user.username if hasattr(request, 'user') and request.user.is_authenticated else 'anonymous',
            'error': str(error),
            'error_type': type(error).__name__,
            'traceback': traceback.format_exc(),
        }
        
        if duration is not None:
            log_data['duration_ms'] = round(duration * 1000, 2)
        
        metrics.counter_inc('api_errors_total', error_type=type(error).__name__)
        cls._structured_logger.error('API error', **log_data)


# ─────────────────────────────────────────────────────────────────
# Decorators
# ─────────────────────────────────────────────────────────────────

def timing_decorator(func: Callable) -> Callable:
    """Decorator to measure and record function execution time."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start
            
            metrics.histogram_observe(
                f'function_duration_seconds',
                duration,
                function=func.__module__ + '.' + func.__name__
            )
            
            return result
        except Exception as e:
            duration = time.time() - start
            metrics.counter_inc('function_errors_total', function=func.__module__ + '.' + func.__name__)
            raise
    return wrapper


def track_execution(func: Callable) -> Callable:
    """Decorator to track workflow execution metrics."""
    @wraps(func)
    def wrapper(execution_id: str = None, workflow_id: str = None, user_id: int = None, *args, **kwargs):
        metrics_instance = get_execution_metrics()
        
        if execution_id:
            record = metrics_instance.start_execution(execution_id, workflow_id, user_id)
        
        start = time.time()
        try:
            result = func(*args, **kwargs)
            
            if execution_id:
                metrics_instance.complete_execution(
                    execution_id,
                    status='completed',
                )
            
            return result
        except Exception as e:
            if execution_id:
                metrics_instance.complete_execution(
                    execution_id,
                    status='failed',
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
            raise
    return wrapper


@contextmanager
def log_execution(operation: str, **context):
    """Context manager for logging execution with duration."""
    structured = get_structured_logger('execution')
    structured.set_context(operation=operation, **context)
    
    start = time.time()
    structured.info(f'Started {operation}')
    
    try:
        yield
        duration = time.time() - start
        structured.info(f'Completed {operation}', duration_ms=round(duration * 1000, 2))
    except Exception as e:
        duration = time.time() - start
        structured.error(f'Failed {operation}', duration_ms=round(duration * 1000, 2), error=str(e))
        raise


# ─────────────────────────────────────────────────────────────────
# Health Checks
# ─────────────────────────────────────────────────────────────────

class HealthCheck:
    """Health check utilities for monitoring."""
    
    @staticmethod
    def check_database() -> Dict[str, Any]:
        """Check database connectivity."""
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
            return {'status': 'healthy', 'message': 'Database connection OK'}
        except Exception as e:
            return {'status': 'unhealthy', 'message': str(e)}
    
    @staticmethod
    def check_redis() -> Dict[str, Any]:
        """Check Redis connectivity."""
        try:
            from django.core.cache import cache
            cache.set('health_check', 'ok', 10)
            if cache.get('health_check') == 'ok':
                return {'status': 'healthy', 'message': 'Redis connection OK'}
            return {'status': 'unhealthy', 'message': 'Redis read/write failed'}
        except Exception as e:
            return {'status': 'unhealthy', 'message': str(e)}
    
    @staticmethod
    def check_ollama() -> Dict[str, Any]:
        """Check Ollama connectivity."""
        try:
            import requests
            base_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
            response = requests.get(f'{base_url}/api/tags', timeout=5)
            if response.status_code == 200:
                return {'status': 'healthy', 'message': 'Ollama connection OK'}
            return {'status': 'unhealthy', 'message': f'Ollama returned {response.status_code}'}
        except Exception as e:
            return {'status': 'unhealthy', 'message': str(e)}
    
    @classmethod
    def run_all_checks(cls) -> Dict[str, Any]:
        """Run all health checks."""
        checks = {
            'database': cls.check_database(),
            'redis': cls.check_redis(),
            'ollama': cls.check_ollama(),
        }
        
        overall_status = 'healthy' if all(
            c['status'] == 'healthy' for c in checks.values()
        ) else 'unhealthy'
        
        return {
            'status': overall_status,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'checks': checks,
            'metrics': metrics.get_all_metrics(),
        }


# ─────────────────────────────────────────────────────────────────
# Performance Profiling
# ─────────────────────────────────────────────────────────────────

class PerformanceProfiler:
    """Simple performance profiler for identifying bottlenecks."""
    
    def __init__(self):
        self._profiles: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def record(self, operation: str, duration: float):
        """Record an operation duration."""
        with self._lock:
            self._profiles[operation].append(duration)
            
            # Keep only last 1000 records
            if len(self._profiles[operation]) > 1000:
                self._profiles[operation] = self._profiles[operation][-1000:]
    
    def get_stats(self, operation: str) -> Optional[Dict[str, float]]:
        """Get statistics for an operation."""
        with self._lock:
            durations = self._profiles.get(operation)
        
        if not durations:
            return None
        
        sorted_durations = sorted(durations)
        n = len(sorted_durations)
        
        return {
            'count': n,
            'mean': sum(durations) / n,
            'min': sorted_durations[0],
            'max': sorted_durations[-1],
            'p50': sorted_durations[n // 2],
            'p95': sorted_durations[int(n * 0.95)],
            'p99': sorted_durations[int(n * 0.99)],
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all operations."""
        return {
            op: self.get_stats(op)
            for op in self._profiles
        }


# Global profiler
_profiler = PerformanceProfiler()


def get_profiler() -> PerformanceProfiler:
    """Get the global performance profiler."""
    return _profiler


@contextmanager
def profile(operation: str):
    """Context manager for profiling code blocks."""
    start = time.time()
    try:
        yield
    finally:
        duration = time.time() - start
        _profiler.record(operation, duration)
        metrics.histogram_observe('profiler_duration_seconds', duration, operation=operation)


# ─────────────────────────────────────────────────────────────────
# Backward Compatibility Re-exports
# ─────────────────────────────────────────────────────────────────

# Keep old class names for backward compatibility
ExecutionMetricsLegacy = ExecutionMetrics
RequestLoggerLegacy = RequestLogger
ErrorTracker = ErrorTracker
UsageTracker = UsageTracker


class ErrorTracker:
    """Track and categorize errors (enhanced version)."""
    
    _structured_logger = get_structured_logger('errors')
    
    @classmethod
    def track_error(cls, error_type: str, error_message: str, context: Dict = None):
        """Track an error for analytics."""
        metrics.counter_inc('errors_total', error_type=error_type)
        
        cls._structured_logger.error(
            'Tracked error',
            error_type=error_type,
            message=error_message,
            context=context,
        )
    
    @classmethod
    def get_error_stats(cls, start_date=None, end_date=None) -> Dict:
        """Get error statistics for a time period."""
        return get_execution_metrics().get_error_stats()


class UsageTracker:
    """Track platform usage (enhanced version)."""
    
    _structured_logger = get_structured_logger('usage')
    
    @classmethod
    def track_event(cls, event_type: str, user_id: int = None, metadata: Dict = None):
        """Track a usage event."""
        metrics.counter_inc('usage_events_total', event_type=event_type)
        
        cls._structured_logger.info(
            'Usage event',
            event_type=event_type,
            user_id=user_id,
            metadata=metadata,
        )
    
    @classmethod
    def get_usage_summary(cls, time_period: str = 'day') -> Dict:
        """Get usage summary for a time period."""
        hours_map = {'hour': 1, 'day': 24, 'week': 168, 'month': 720}
        hours = hours_map.get(time_period, 24)
        
        return get_execution_metrics().get_execution_stats(hours=hours)
