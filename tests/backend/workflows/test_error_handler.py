"""
Tests for NodeErrorHandler.
"""

import pytest
from unittest.mock import MagicMock
from workflows.services.error_handler import (
    NodeErrorHandler,
    ErrorStrategy,
    RetryConfig,
    ErrorHandlerRegistry
)


class TestNodeErrorHandler:
    """Test cases for NodeErrorHandler."""

    def test_init_stop_strategy(self):
        """Test initialization with stop strategy."""
        handler = NodeErrorHandler(strategy='stop')
        assert handler.strategy == ErrorStrategy.STOP

    def test_init_skip_strategy(self):
        """Test initialization with skip strategy."""
        handler = NodeErrorHandler(strategy='skip')
        assert handler.strategy == ErrorStrategy.SKIP

    def test_init_retry_strategy(self):
        """Test initialization with retry strategy."""
        handler = NodeErrorHandler(strategy='retry')
        assert handler.strategy == ErrorStrategy.RETRY

    def test_init_fallback_strategy(self):
        """Test initialization with fallback strategy."""
        handler = NodeErrorHandler(strategy='fallback')
        assert handler.strategy == ErrorStrategy.FALLBACK

    def test_init_with_config(self):
        """Test initialization with config."""
        config = {
            'max_retries': 5,
            'retry_delay': 2.0,
            'exponential_backoff': False
        }
        handler = NodeErrorHandler(strategy='retry', config=config)
        assert handler.retry_config.max_retries == 5
        assert handler.retry_config.retry_delay == 2.0
        assert handler.retry_config.exponential_backoff is False

    def test_handle_stop_strategy(self):
        """Test stop strategy raises error."""
        handler = NodeErrorHandler(strategy='stop')
        error = Exception("Test error")
        
        with pytest.raises(Exception) as exc_info:
            handler.handle(error, lambda: (_ for _ in ()).throw(error))
        
        assert str(exc_info.value) == "Test error"

    def test_handle_skip_strategy(self):
        """Test skip strategy returns None."""
        handler = NodeErrorHandler(strategy='skip')
        error = Exception("Test error")
        
        result = handler.handle(error, lambda: None)
        assert result is None

    def test_handle_retry_strategy_success(self):
        """Test retry strategy succeeds on first try."""
        handler = NodeErrorHandler(strategy='retry', config={'max_retries': 3})
        call_count = 0
        
        def executor():
            nonlocal call_count
            call_count += 1
            return 'success'
        
        result = handler.handle(Exception("error"), executor)
        assert result == 'success'
        assert call_count == 1

    def test_handle_retry_strategy_failure(self):
        """Test retry strategy eventually fails."""
        handler = NodeErrorHandler(
            strategy='retry',
            config={'max_retries': 2, 'retry_delay': 0.01}
        )
        call_count = 0
        
        def executor():
            nonlocal call_count
            call_count += 1
            raise Exception("Test error")
        
        with pytest.raises(Exception) as exc_info:
            handler.handle(Exception("Test error"), executor)
        
        assert str(exc_info.value) == "Test error"
        assert call_count == 3  # initial + 2 retries

    def test_handle_fallback_strategy(self):
        """Test fallback strategy returns fallback value."""
        handler = NodeErrorHandler(
            strategy='fallback',
            config={'fallback_value': 'fallback_result'}
        )
        error = Exception("Test error")
        
        result = handler.handle(error, lambda: None)
        assert result == 'fallback_result'

    def test_handle_fallback_strategy_with_default(self):
        """Test fallback strategy with default fallback value."""
        handler = NodeErrorHandler(strategy='fallback')
        error = Exception("Test error")
        
        result = handler.handle(error, lambda: None)
        assert result is None

    def test_repr(self):
        """Test string representation."""
        handler = NodeErrorHandler(strategy='stop')
        assert 'stop' in repr(handler)


class TestRetryConfig:
    """Test cases for RetryConfig."""

    def test_default_values(self):
        """Test default values."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.retry_delay == 1.0
        assert config.exponential_backoff is True
        assert config.max_delay == 60.0

    def test_custom_values(self):
        """Test custom values."""
        config = RetryConfig(
            max_retries=10,
            retry_delay=5.0,
            exponential_backoff=False,
            max_delay=120.0
        )
        assert config.max_retries == 10
        assert config.retry_delay == 5.0
        assert config.exponential_backoff is False
        assert config.max_delay == 120.0


class TestErrorHandlerRegistry:
    """Test cases for ErrorHandlerRegistry."""

    def test_register_and_get(self):
        """Test registering and getting handlers."""
        handler = NodeErrorHandler(strategy='stop')
        ErrorHandlerRegistry.register('custom_handler', handler)
        
        retrieved = ErrorHandlerRegistry.get('custom_handler')
        assert retrieved is handler

    def test_get_nonexistent(self):
        """Test getting non-existent handler."""
        result = ErrorHandlerRegistry.get('nonexistent')
        assert result is None

    def test_create(self):
        """Test creating handler from config."""
        config = {
            'error_handling': 'skip',
            'max_retries': 5
        }
        handler = ErrorHandlerRegistry.create(config)
        assert handler.strategy == ErrorStrategy.SKIP
        assert handler.retry_config.max_retries == 5

    def test_set_and_get_default(self):
        """Test setting and getting default strategy."""
        original = ErrorHandlerRegistry._default_strategy
        ErrorHandlerRegistry.set_default('skip')
        assert ErrorHandlerRegistry._default_strategy == 'skip'
        
        default_handler = ErrorHandlerRegistry.get_default()
        assert default_handler.strategy == ErrorStrategy.SKIP
        
        # Restore original
        ErrorHandlerRegistry._default_strategy = original

    def test_create_from_node(self):
        """Test creating handler from node-like object."""
        node = MagicMock(spec=['error_handling', 'max_retries', 'retry_delay', 'fallback_value'])
        node.error_handling = 'retry'
        node.max_retries = 10
        node.retry_delay = 5.0
        node.fallback_value = {'default': 'value'}
        
        handler = ErrorHandlerRegistry.create_from_node(node)
        assert handler.strategy == ErrorStrategy.RETRY
        assert handler.retry_config.max_retries == 10
        assert handler.retry_config.retry_delay == 5.0
        assert handler.fallback_value == {'default': 'value'}

    def test_create_from_node_with_defaults(self):
        """Test creating handler from node with default values."""
        node = MagicMock(spec=['error_handling'])  # Only has error_handling
        node.error_handling = 'stop'
        
        handler = ErrorHandlerRegistry.create_from_node(node)
        assert handler.strategy == ErrorStrategy.STOP
        assert handler.retry_config.max_retries == 3  # default
