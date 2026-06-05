"""
节点错误处理 - 支持多种错误处理策略
"""

import time
import logging
from typing import Any, Dict, Callable, Optional, List
from dataclasses import dataclass, field
from enum import Enum


logger = logging.getLogger(__name__)


class ErrorStrategy(Enum):
    """
    错误处理策略枚举
    """
    STOP = 'stop'           # 停止执行，抛出异常
    SKIP = 'skip'           # 跳过当前节点，继续执行下一个
    RETRY = 'retry'         # 重试指定次数
    FALLBACK = 'fallback'   # 使用备用值


@dataclass
class RetryConfig:
    """
    重试配置
    
    Attributes:
        max_retries: 最大重试次数
        retry_delay: 初始重试延迟（秒）
        exponential_backoff: 是否使用指数退避
        max_delay: 最大延迟（秒）
        retry_on: 重试特定异常类型列表
    """
    max_retries: int = 3
    retry_delay: float = 1.0
    exponential_backoff: bool = True
    max_delay: float = 60.0
    retry_on: List[type] = field(default_factory=lambda: [Exception])


class NodeErrorHandler:
    """
    节点错误处理器
    
    支持四种错误处理策略：
    1. STOP - 立即停止执行
    2. SKIP - 跳过当前节点，继续执行
    3. RETRY - 按照配置重试
    4. FALLBACK - 使用备用值
    """
    
    def __init__(
        self,
        strategy: str = 'stop',
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化错误处理器
        
        Args:
            strategy: 错误处理策略 ('stop', 'skip', 'retry', 'fallback')
            config: 配置字典
        """
        self.strategy = ErrorStrategy(strategy)
        self.config = config or {}
        
        # 解析重试配置
        self.retry_config = RetryConfig(
            max_retries=self.config.get('max_retries', 3),
            retry_delay=float(self.config.get('retry_delay', 1.0)),
            exponential_backoff=self.config.get('exponential_backoff', True),
            max_delay=float(self.config.get('max_delay', 60.0))
        )
        
        # 备用值
        self.fallback_value = self.config.get('fallback_value')
        
        self._logger = logger
    
    def handle(
        self,
        error: Exception,
        executor_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        处理错误
        
        Args:
            error: 发生的异常
            executor_func: 需要执行的函数
            *args: 函数位置参数
            **kwargs: 函数关键字参数
            
        Returns:
            执行结果或备用值
        """
        # 记录错误日志
        self._logger.warning(f"节点执行错误 [{self.strategy.value}]: {error}")
        
        if self.strategy == ErrorStrategy.STOP:
            raise error
        
        elif self.strategy == ErrorStrategy.SKIP:
            self._logger.info("策略: 跳过当前节点")
            return None
        
        elif self.strategy == ErrorStrategy.RETRY:
            return self._retry_execute(executor_func, *args, **kwargs)
        
        elif self.strategy == ErrorStrategy.FALLBACK:
            self._logger.info(f"策略: 使用备用值 {self.fallback_value}")
            return self.fallback_value
        
        # 默认抛出原始错误
        raise error
    
    def _retry_execute(
        self,
        executor_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        带重试的执行
        
        Args:
            executor_func: 需要执行的函数
            *args: 函数位置参数
            **kwargs: 函数关键字参数
            
        Returns:
            执行结果
            
        Raises:
            Exception: 所有重试都失败后抛出最后一个异常
        """
        last_error = None
        delay = self.retry_config.retry_delay
        
        for attempt in range(self.retry_config.max_retries + 1):
            try:
                result = executor_func(*args, **kwargs)
                
                if attempt > 0:
                    self._logger.info(f"重试成功 (尝试 {attempt + 1})")
                
                return result
                
            except Exception as e:
                last_error = e
                
                # 检查是否应该重试这个异常类型
                should_retry = any(
                    isinstance(e, exc_type)
                    for exc_type in self.retry_config.retry_on
                )
                
                if not should_retry:
                    self._logger.warning(f"异常类型 {type(e).__name__} 不支持重试")
                    raise e
                
                self._logger.warning(
                    f"执行失败 (尝试 {attempt + 1}/{self.retry_config.max_retries + 1}): {e}"
                )
                
                if attempt < self.retry_config.max_retries:
                    # 等待后再重试
                    time.sleep(delay)
                    
                    # 指数退避
                    if self.retry_config.exponential_backoff:
                        delay = min(
                            delay * 2,
                            self.retry_config.max_delay
                        )
                else:
                    self._logger.error(
                        f"重试次数耗尽，最大尝试 {self.retry_config.max_retries + 1} 次"
                    )
        
        # 所有重试都失败
        raise last_error
    
    def __repr__(self) -> str:
        return f"NodeErrorHandler(strategy={self.strategy.value})"


class ErrorHandlerRegistry:
    """
    错误处理器注册表
    
    提供全局的错误处理器管理和配置。
    """
    
    _handlers: Dict[str, NodeErrorHandler] = {}
    _default_strategy: str = 'stop'
    
    @classmethod
    def register(
        cls,
        name: str,
        handler: NodeErrorHandler
    ) -> None:
        """
        注册处理器
        
        Args:
            name: 处理器名称
            handler: 错误处理器实例
        """
        cls._handlers[name] = handler
    
    @classmethod
    def get(cls, name: str) -> Optional[NodeErrorHandler]:
        """
        获取处理器
        
        Args:
            name: 处理器名称
            
        Returns:
            错误处理器或 None
        """
        return cls._handlers.get(name)
    
    @classmethod
    def create(cls, config: Dict[str, Any]) -> NodeErrorHandler:
        """
        根据配置创建处理器
        
        Args:
            config: 配置字典
            
        Returns:
            NodeErrorHandler 实例
        """
        strategy = config.get('error_handling', 'stop')
        return NodeErrorHandler(strategy=strategy, config=config)
    
    @classmethod
    def set_default(cls, strategy: str) -> None:
        """
        设置默认策略
        
        Args:
            strategy: 策略名称
        """
        cls._default_strategy = strategy
    
    @classmethod
    def get_default(cls) -> NodeErrorHandler:
        """
        获取默认处理器
        
        Returns:
            默认错误处理器
        """
        return NodeErrorHandler(strategy=cls._default_strategy)
    
    @classmethod
    def create_from_node(cls, node) -> NodeErrorHandler:
        """
        从节点配置创建处理器
        
        Args:
            node: Node 实例
            
        Returns:
            NodeErrorHandler 实例
        """
        config = {
            'error_handling': getattr(node, 'error_handling', 'stop'),
            'max_retries': getattr(node, 'max_retries', 3),
            'retry_delay': getattr(node, 'retry_delay_seconds', getattr(node, 'retry_delay', 1.0)),
            'fallback_value': getattr(node, 'fallback_value', None)
        }
        return cls.create(config)


def handle_node_error(
    strategy: str,
    config: Dict[str, Any],
    error: Exception,
    executor_func: Callable,
    *args,
    **kwargs
) -> Any:
    """
    便捷函数：处理节点错误
    
    Args:
        strategy: 错误处理策略
        config: 节点配置
        error: 发生的异常
        executor_func: 执行函数
        *args, **kwargs: 函数参数
        
    Returns:
        执行结果或备用值
    """
    handler = NodeErrorHandler(strategy=strategy, config=config)
    return handler.handle(error, executor_func, *args, **kwargs)
