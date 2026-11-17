"""Shared execution errors used by orchestration and domain node modules."""


class WorkflowExecutionError(Exception):
    """Base exception for workflow execution errors."""
    def __init__(self, message: str, error_type: str = 'execution'):
        self.message = message
        self.error_type = error_type
        super().__init__(message)


class LocalImageModelError(WorkflowExecutionError):
    """Raised when a local image generation model cannot be loaded or executed."""
    def __init__(self, message: str):
        super().__init__(message, 'local_image_model')
