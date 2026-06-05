"""
LangSmith integration for observability and tracing.

Provides:
- LangChain callback handler for tracing
- Token usage tracking
- Latency monitoring
- Cost estimation
"""

import logging
import time
import functools
from typing import Any, Dict, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import contextmanager

from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class LangSmithConfig:
    """LangSmith configuration."""
    api_key: str = ''
    project_name: str = 'flowly-default'
    endpoint: str = 'https://api.smith.langchain.com'
    timeout: int = 60
    retry_attempts: int = 3
    verbose: bool = False

    @classmethod
    def from_settings(cls) -> 'LangSmithConfig':
        """Create config from Django settings."""
        return cls(
            api_key=getattr(settings, 'LANGSMITH_API_KEY', ''),
            project_name=getattr(settings, 'LANGSMITH_PROJECT', 'flowly-default'),
            endpoint=getattr(settings, 'LANGSMITH_ENDPOINT', 'https://api.smith.langchain.com'),
            timeout=getattr(settings, 'LANGSMITH_TIMEOUT', 60),
            retry_attempts=getattr(settings, 'LANGSMITH_RETRY_ATTEMPTS', 3),
            verbose=getattr(settings, 'LANGSMITH_VERBOSE', False),
        )


@dataclass
class TraceRecord:
    """Record of a single LLM call for tracing."""
    trace_id: str
    run_id: str
    name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None
    
    # Request info
    model: str = ''
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    # Cost info
    input_cost: float = 0.0
    output_cost: float = 0.0
    total_cost: float = 0.0
    
    # Metadata
    user_id: Optional[int] = None
    workflow_id: Optional[str] = None
    execution_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/export."""
        return {
            'trace_id': self.trace_id,
            'run_id': self.run_id,
            'name': self.name,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_ms': self.duration_ms,
            'success': self.success,
            'error': self.error,
            'model': self.model,
            'prompt_tokens': self.prompt_tokens,
            'completion_tokens': self.completion_tokens,
            'total_tokens': self.total_tokens,
            'input_cost': self.input_cost,
            'output_cost': self.output_cost,
            'total_cost': self.total_cost,
            'user_id': self.user_id,
            'workflow_id': self.workflow_id,
            'execution_id': self.execution_id,
            'metadata': self.metadata,
        }


class CostEstimator:
    """Estimate LLM API costs based on token usage."""
    
    # Default pricing per 1M tokens (USD)
    DEFAULT_PRICING = {
        'gpt-4': {'input': 30.0, 'output': 60.0},
        'gpt-4-turbo': {'input': 10.0, 'output': 30.0},
        'gpt-3.5-turbo': {'input': 0.5, 'output': 1.5},
        'claude-3-opus': {'input': 15.0, 'output': 75.0},
        'claude-3-sonnet': {'input': 3.0, 'output': 15.0},
        'claude-3-haiku': {'input': 0.25, 'output': 1.25},
        'default': {'input': 1.0, 'output': 2.0},
    }
    
    def __init__(self, custom_pricing: Optional[Dict[str, Dict[str, float]]] = None):
        self.pricing = {**self.DEFAULT_PRICING}
        if custom_pricing:
            self.pricing.update(custom_pricing)
    
    def estimate_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> Dict[str, float]:
        """
        Estimate cost for a given model and token usage.
        
        Returns dict with input_cost, output_cost, and total_cost.
        """
        model_lower = model.lower()
        
        # Find matching pricing tier
        pricing = self.DEFAULT_PRICING['default']
        for tier, rates in self.pricing.items():
            if tier != 'default' and tier in model_lower:
                pricing = rates
                break
        
        input_cost = (prompt_tokens / 1_000_000) * pricing['input']
        output_cost = (completion_tokens / 1_000_000) * pricing['output']
        
        return {
            'input_cost': round(input_cost, 6),
            'output_cost': round(output_cost, 6),
            'total_cost': round(input_cost + output_cost, 6),
        }


class TokenTracker:
    """Track token usage across multiple calls."""
    
    def __init__(self):
        self.total_prompt_tokens: int = 0
        self.total_completion_tokens: int = 0
        self.total_tokens: int = 0
        self.total_cost: float = 0.0
        self.call_count: int = 0
        self.cost_estimator = CostEstimator()
    
    def record(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> Dict[str, Any]:
        """Record token usage for a single call."""
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_tokens += prompt_tokens + completion_tokens
        self.call_count += 1
        
        costs = self.cost_estimator.estimate_cost(model, prompt_tokens, completion_tokens)
        self.total_cost += costs['total_cost']
        
        return costs
    
    def get_stats(self) -> Dict[str, Any]:
        """Get aggregated token statistics."""
        return {
            'total_prompt_tokens': self.total_prompt_tokens,
            'total_completion_tokens': self.total_completion_tokens,
            'total_tokens': self.total_tokens,
            'total_cost_usd': round(self.total_cost, 6),
            'call_count': self.call_count,
            'avg_tokens_per_call': round(self.total_tokens / self.call_count, 2) if self.call_count > 0 else 0,
        }
    
    def reset(self):
        """Reset all counters."""
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        self.call_count = 0


# Global token tracker instance
_global_token_tracker = TokenTracker()


def get_token_tracker() -> TokenTracker:
    """Get the global token tracker instance."""
    return _global_token_tracker


class LangSmithCallback:
    """
    LangChain callback handler for LangSmith tracing.
    
    Provides:
    - Full call chain tracing
    - Token usage tracking
    - Latency monitoring
    - Cost estimation
    
    Usage:
        from langchain.callbacks import LangChainCallbackHandler
        
        callback = LangChainCallbackHandler(
            project_name="flowly-production",
            user_id=request.user.id,
            workflow_id=workflow.id,
        )
        
        result = chain.invoke(inputs, config={"callbacks": [callback]})
    """
    
    def __init__(
        self,
        project_name: Optional[str] = None,
        api_key: Optional[str] = None,
        trace_id: Optional[str] = None,
        run_id: Optional[str] = None,
        user_id: Optional[int] = None,
        workflow_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        streaming: bool = False,
    ):
        self.config = LangSmithConfig.from_settings()
        self.project_name = project_name or self.config.project_name
        
        self.trace_id = trace_id or self._generate_id()
        self.run_id = run_id or self._generate_id()
        self.user_id = user_id
        self.workflow_id = workflow_id
        self.execution_id = execution_id
        self.metadata = metadata or {}
        self.tags = tags or []
        self.streaming = streaming
        
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.duration_ms: float = 0.0
        self.success: bool = True
        self.error: Optional[str] = None
        
        # Token tracking
        self.prompt_tokens: int = 0
        self.completion_tokens: int = 0
        self.total_tokens: int = 0
        
        # Call chain
        self.child_spans: List['LangSmithCallback'] = []
        self.parent_callback: Optional['LangSmithCallback'] = None
        
        # Cost tracking
        self.cost_estimator = CostEstimator()
        self.input_cost: float = 0.0
        self.output_cost: float = 0.0
        self.total_cost: float = 0.0
        
        # LangChain-specific attributes
        self.llm_output: Optional[Dict[str, Any]] = None
        
        # Check if LangSmith is configured
        self.enabled = bool(self.config.api_key)
    
    def _generate_id(self) -> str:
        """Generate a unique ID for tracing."""
        import uuid
        return str(uuid.uuid4())
    
    def _calculate_duration(self) -> float:
        """Calculate duration in milliseconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return 0.0
    
    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs
    ) -> List[str]:
        """Called when LLM starts processing."""
        if not self.enabled:
            return prompts
        
        self.start_time = datetime.now()
        
        # Extract model name
        if 'name' in serialized:
            self.metadata['model'] = serialized['name']
        elif 'id' in serialized:
            self.metadata['model'] = serialized['id']
        
        self.metadata['prompts_count'] = len(prompts)
        
        if self.config.verbose:
            logger.debug(f"[LangSmith] LLM Start: {self.run_id}, prompts: {len(prompts)}")
        
        return prompts
    
    def on_llm_new_token(
        self,
        token: str,
        **kwargs
    ) -> None:
        """Called for each new token in streaming mode."""
        if self.streaming and self.config.verbose:
            logger.debug(f"[LangSmith] Token: {token[:50]}...")
    
    def on_llm_end(
        self,
        response,
        **kwargs
    ) -> None:
        """Called when LLM finishes processing."""
        if not self.enabled:
            return
        
        self.end_time = datetime.now()
        self.duration_ms = self._calculate_duration()
        
        # Extract token usage from response
        try:
            if hasattr(response, 'llm_output') and response.llm_output:
                self.llm_output = response.llm_output
                
                # OpenAI format
                if 'token_usage' in response.llm_output:
                    usage = response.llm_output['token_usage']
                    self.prompt_tokens = usage.get('prompt_tokens', 0)
                    self.completion_tokens = usage.get('completion_tokens', 0)
                    self.total_tokens = usage.get('total_tokens', 0)
                
                # Calculate costs
                model = self.metadata.get('model', 'default')
                costs = self.cost_estimator.estimate_cost(
                    model,
                    self.prompt_tokens,
                    self.completion_tokens
                )
                self.input_cost = costs['input_cost']
                self.output_cost = costs['output_cost']
                self.total_cost = costs['total_cost']
                
                # Update global tracker
                get_token_tracker().record(model, self.prompt_tokens, self.completion_tokens)
        
        except Exception as e:
            logger.warning(f"[LangSmith] Failed to extract token usage: {e}")
        
        if self.config.verbose:
            logger.debug(
                f"[LangSmith] LLM End: {self.run_id}, "
                f"tokens: {self.total_tokens}, cost: ${self.total_cost:.6f}"
            )
    
    def on_llm_error(
        self,
        error: Exception,
        **kwargs
    ) -> None:
        """Called when LLM encounters an error."""
        self.end_time = datetime.now()
        self.duration_ms = self._calculate_duration()
        self.success = False
        self.error = str(error)
        
        if self.config.verbose:
            logger.warning(f"[LangSmith] LLM Error: {self.run_id}, error: {error}")
    
    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Called when a chain starts execution."""
        if not self.enabled:
            return inputs
        
        self.start_time = datetime.now()
        
        if 'name' in serialized:
            self.metadata['chain_name'] = serialized['name']
        
        self.metadata['inputs_keys'] = list(inputs.keys()) if inputs else []
        
        if self.config.verbose:
            logger.debug(f"[LangSmith] Chain Start: {self.run_id}")
        
        return inputs
    
    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        **kwargs
    ) -> None:
        """Called when a chain finishes execution."""
        if not self.enabled:
            return
        
        self.end_time = datetime.now()
        self.duration_ms = self._calculate_duration()
        
        self.metadata['outputs_keys'] = list(outputs.keys()) if outputs else []
        
        if self.config.verbose:
            logger.debug(f"[LangSmith] Chain End: {self.run_id}, duration: {self.duration_ms}ms")
    
    def on_chain_error(
        self,
        error: Exception,
        **kwargs
    ) -> None:
        """Called when a chain encounters an error."""
        self.end_time = datetime.now()
        self.duration_ms = self._calculate_duration()
        self.success = False
        self.error = str(error)
        
        if self.config.verbose:
            logger.warning(f"[LangSmith] Chain Error: {self.run_id}, error: {error}")
    
    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Called when a tool starts execution."""
        if not self.enabled:
            return inputs
        
        self.start_time = datetime.now()
        
        if 'name' in serialized:
            self.metadata['tool_name'] = serialized['name']
        
        if self.config.verbose:
            logger.debug(f"[LangSmith] Tool Start: {self.run_id}")
        
        return inputs
    
    def on_tool_end(
        self,
        output: str,
        **kwargs
    ) -> None:
        """Called when a tool finishes execution."""
        if not self.enabled:
            return
        
        self.end_time = datetime.now()
        self.duration_ms = self._calculate_duration()
        
        if self.config.verbose:
            logger.debug(f"[LangSmith] Tool End: {self.run_id}, output length: {len(str(output))}")
    
    def on_tool_error(
        self,
        error: Exception,
        **kwargs
    ) -> None:
        """Called when a tool encounters an error."""
        self.end_time = datetime.now()
        self.duration_ms = self._calculate_duration()
        self.success = False
        self.error = str(error)
    
    def to_trace_record(self) -> TraceRecord:
        """Convert to a TraceRecord for storage."""
        return TraceRecord(
            trace_id=self.trace_id,
            run_id=self.run_id,
            name=self.metadata.get('chain_name', self.metadata.get('tool_name', 'unknown')),
            start_time=self.start_time,
            end_time=self.end_time,
            duration_ms=self.duration_ms,
            success=self.success,
            error=self.error,
            model=self.metadata.get('model', ''),
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            total_tokens=self.total_tokens,
            input_cost=self.input_cost,
            output_cost=self.output_cost,
            total_cost=self.total_cost,
            user_id=self.user_id,
            workflow_id=self.workflow_id,
            execution_id=self.execution_id,
            metadata=self.metadata,
        )
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the trace."""
        return {
            'trace_id': self.trace_id,
            'run_id': self.run_id,
            'success': self.success,
            'duration_ms': self.duration_ms,
            'tokens': {
                'prompt': self.prompt_tokens,
                'completion': self.completion_tokens,
                'total': self.total_tokens,
            },
            'cost': {
                'input': self.input_cost,
                'output': self.output_cost,
                'total': self.total_cost,
            },
            'error': self.error,
            'metadata': self.metadata,
        }


@contextmanager
def langsmith_trace(
    name: str,
    project_name: Optional[str] = None,
    user_id: Optional[int] = None,
    workflow_id: Optional[str] = None,
    execution_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
):
    """
    Context manager for creating a LangSmith trace.
    
    Usage:
        with langsmith_trace("workflow_execution", workflow_id="wf-123") as trace:
            # Do work
            result = execute_workflow()
            trace.metadata['result'] = 'success'
    """
    callback = LangSmithCallback(
        project_name=project_name,
        user_id=user_id,
        workflow_id=workflow_id,
        execution_id=execution_id,
        metadata=metadata,
        tags=tags,
    )
    
    callback.start_time = datetime.now()
    callback.metadata['name'] = name
    
    try:
        yield callback
    except Exception as e:
        callback.success = False
        callback.error = str(e)
        raise
    finally:
        callback.end_time = datetime.now()
        callback.duration_ms = callback._calculate_duration()


def traced_llm_call(
    model: str,
    prompt: str,
    project_name: Optional[str] = None,
    user_id: Optional[int] = None,
    workflow_id: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Execute an LLM call with LangSmith tracing.
    
    Returns the LLM response along with trace metadata.
    """
    callback = LangSmithCallback(
        project_name=project_name,
        user_id=user_id,
        workflow_id=workflow_id,
    )
    
    # This would be integrated with the actual LLM call
    # For now, returns the callback for integration
    return {
        'callback': callback,
        'model': model,
        'prompt': prompt,
        'kwargs': kwargs,
    }


class TracingMiddleware:
    """
    Django middleware for adding LangSmith tracing to all requests.
    
    Add to MIDDLEWARE in settings.py:
        'workflows.services.langsmith_callback.TracingMiddleware',
    """
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
        self.config = LangSmithConfig.from_settings()
        self.enabled = bool(self.config.api_key)
    
    def __call__(self, request):
        if not self.enabled:
            return self.get_response(request)
        
        # Add trace ID to request for downstream use
        import uuid
        trace_id = str(uuid.uuid4())
        request.langsmith_trace_id = trace_id
        
        start_time = time.time()
        
        response = self.get_response(request)
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Log request trace
        if self.config.verbose or request.path.startswith('/api/'):
            logger.info(
                f"[LangSmith] Request: {request.method} {request.path} "
                f"status={response.status_code} duration={duration_ms:.2f}ms "
                f"trace_id={trace_id}"
            )
        
        # Add trace ID to response headers
        response['X-Trace-ID'] = trace_id
        
        return response


def setup_langsmith():
    """
    Set up LangSmith environment variables and tracing.
    
    Call this during application startup if LangSmith is configured.
    """
    config = LangSmithConfig.from_settings()
    
    if not config.api_key:
        logger.info("LangSmith API key not configured, tracing disabled")
        return
    
    # Set environment variables for LangChain tracing
    import os
    os.environ['LANGCHAIN_TRACING_V2'] = 'true'
    os.environ['LANGCHAIN_API_KEY'] = config.api_key
    os.environ['LANGCHAIN_PROJECT'] = config.project_name
    os.environ['LANGCHAIN_ENDPOINT'] = config.endpoint
    
    logger.info(f"LangSmith tracing enabled for project: {config.project_name}")
