"""
Retry decorator with exponential backoff for workflow execution.

Provides configurable retry logic for transient errors including:
- Network errors (ConnectionError, TimeoutError)
- Rate limiting (429 Too Many Requests)
- Service unavailability
"""

import time
import functools
import logging
from typing import Callable, Any, Dict, Type, Tuple, Optional

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """API rate limit exceeded."""
    pass


class ServiceUnavailableError(Exception):
    """Service temporarily unavailable."""
    pass


# Default retry configurations: (max_retries, initial_delay_seconds)
RETRY_CONFIGS: Dict[Type[Exception], Tuple[int, float]] = {
    ConnectionError: (3, 2.0),
    TimeoutError: (3, 5.0),
    RateLimitError: (5, 10.0),
}


def with_retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    retriable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
):
    """
    Decorator that retries a function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts.
        initial_delay: Initial delay between retries in seconds.
        max_delay: Maximum delay between retries in seconds.
        exponential_base: Base for exponential backoff calculation.
        retriable_exceptions: Tuple of exception types to retry on.
                             If None, uses the default RETRY_CONFIGS mapping.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            config = retriable_exceptions or tuple(RETRY_CONFIGS.keys())
            last_exception = None
            delay = initial_delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except config as e:
                    last_exception = e

                    # Check per-exception-type retry limits
                    type_max_retries, type_delay = RETRY_CONFIGS.get(type(e), (max_retries, delay))
                    if attempt >= type_max_retries:
                        logger.error(
                            f"{func.__name__} failed after {attempt + 1} attempts "
                            f"({type(e).__name__}): {e}"
                        )
                        raise

                    if attempt >= max_retries:
                        logger.error(
                            f"{func.__name__} failed after {max_retries + 1} attempts: {e}"
                        )
                        raise

                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1}/{max_retries + 1} failed "
                        f"({type(e).__name__}): {e}. Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    delay = min(delay * exponential_base, max_delay)

                except Exception as e:
                    # Non-retriable exception, raise immediately
                    logger.error(f"{func.__name__} non-retriable error ({type(e).__name__}): {e}")
                    raise

            if last_exception:
                raise last_exception

        return wrapper
    return decorator


def is_retriable_error(error: Exception, node_type: str = None) -> bool:
    """
    Determine if an error is retriable based on its type and message.

    Args:
        error: The exception to evaluate.
        node_type: Optional node type for context-specific logic.

    Returns:
        True if the error should trigger a retry.
    """
    # Network-related errors
    if isinstance(error, (ConnectionError, TimeoutError)):
        return True

    # Explicit retryable error types
    if isinstance(error, (RateLimitError, ServiceUnavailableError)):
        return True

    # Check error message for retryable patterns
    error_str = str(error).lower()

    retriable_keywords = [
        'rate limit', '429', 'too many requests', 'quota exceeded',
        'throttle', 'service unavailable', '503', '502', '504',
        'connection refused', 'connection reset', 'timeout',
        'temporarily unavailable', 'try again', 'please retry',
        'capacity', 'overloaded', 'maintenance',
    ]

    if any(keyword in error_str for keyword in retriable_keywords):
        return True

    return False


def calculate_retry_delay(
    attempt: int,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
) -> float:
    """
    Calculate retry delay with exponential backoff and optional jitter.

    Args:
        attempt: Current retry attempt number (0-indexed).
        initial_delay: Base delay in seconds.
        max_delay: Maximum delay cap.
        exponential_base: Exponential growth base.
        jitter: Whether to add random jitter (0-25% of delay).

    Returns:
        Calculated delay in seconds.
    """
    import random

    delay = min(initial_delay * (exponential_base ** attempt), max_delay)

    if jitter:
        jitter_amount = delay * random.uniform(0, 0.25)
        delay += jitter_amount

    return delay
