"""
Workflow Checkpointing for Pause/Resume Execution.

Provides persistent checkpoint storage for:
- Saving execution state at checkpoints
- Resuming from interrupted execution
- Recovery from crashes
"""

import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
from django.utils import timezone

from workflows.models import WorkflowExecution, NodeExecution

logger = logging.getLogger(__name__)


@dataclass
class CheckpointData:
    """Snapshot of workflow execution state."""
    execution_id: str
    workflow_id: str
    workflow_version: int
    current_node_id: Optional[str]
    completed_node_ids: List[str]
    skipped_node_ids: List[str]
    errored_node_ids: List[str]
    context_data: Dict[str, Any]
    node_results: Dict[str, Dict[str, Any]]
    timestamp: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CheckpointData":
        return cls(**data)


class CheckpointStorage:
    """
    Storage backend for workflow checkpoints.

    Uses Django model storage with JSON field.
    """

    @staticmethod
    def save_checkpoint(
        execution: WorkflowExecution,
        checkpoint: CheckpointData
    ) -> bool:
        """
        Save a checkpoint for an execution.

        Args:
            execution: WorkflowExecution model instance
            checkpoint: Checkpoint data to save

        Returns:
            True if saved successfully
        """
        try:
            # Store in execution's metadata
            checkpoints = execution.metadata.get('checkpoints', [])
            checkpoints.append(checkpoint.to_dict())

            # Keep only last 10 checkpoints
            checkpoints = checkpoints[-10:]

            execution.metadata = {
                **execution.metadata,
                'checkpoints': checkpoints,
                'last_checkpoint': checkpoint.to_dict(),
                'last_checkpoint_at': timezone.now().isoformat()
            }
            execution.save(update_fields=['metadata'])
            return True

        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            return False

    @staticmethod
    def load_latest_checkpoint(
        execution: WorkflowExecution
    ) -> Optional[CheckpointData]:
        """
        Load the most recent checkpoint.

        Args:
            execution: WorkflowExecution model instance

        Returns:
            CheckpointData or None if no checkpoint exists
        """
        try:
            metadata = execution.metadata or {}
            checkpoint_dict = metadata.get('last_checkpoint')
            if checkpoint_dict:
                return CheckpointData.from_dict(checkpoint_dict)
            return None

        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None

    @staticmethod
    def load_checkpoint_by_index(
        execution: WorkflowExecution,
        index: int
    ) -> Optional[CheckpointData]:
        """
        Load a specific checkpoint by index.

        Args:
            execution: WorkflowExecution model instance
            index: Checkpoint index (0 = oldest)

        Returns:
            CheckpointData or None
        """
        try:
            checkpoints = execution.metadata.get('checkpoints', [])
            if 0 <= index < len(checkpoints):
                return CheckpointData.from_dict(checkpoints[index])
            return None

        except Exception as e:
            logger.error(f"Failed to load checkpoint {index}: {e}")
            return None

    @staticmethod
    def list_checkpoints(
        execution: WorkflowExecution
    ) -> List[Dict[str, Any]]:
        """
        List all checkpoints for an execution.

        Args:
            execution: WorkflowExecution model instance

        Returns:
            List of checkpoint summaries
        """
        try:
            checkpoints = execution.metadata.get('checkpoints', [])
            return [
                {
                    'index': i,
                    'timestamp': cp.get('timestamp'),
                    'current_node_id': cp.get('current_node_id'),
                    'completed_count': len(cp.get('completed_node_ids', [])),
                    'has_errors': len(cp.get('errored_node_ids', [])) > 0
                }
                for i, cp in enumerate(checkpoints)
            ]

        except Exception as e:
            logger.error(f"Failed to list checkpoints: {e}")
            return []

    @staticmethod
    def clear_checkpoints(execution: WorkflowExecution) -> bool:
        """Clear all checkpoints for an execution."""
        try:
            metadata = execution.metadata or {}
            metadata.pop('checkpoints', None)
            metadata.pop('last_checkpoint', None)
            metadata.pop('last_checkpoint_at', None)
            execution.metadata = metadata
            execution.save(update_fields=['metadata'])
            return True

        except Exception as e:
            logger.error(f"Failed to clear checkpoints: {e}")
            return False


class WorkflowCheckpointManager:
    """
    Manager for workflow execution checkpointing.

    Handles:
    - Creating checkpoints during execution
    - Saving execution state
    - Resuming from checkpoints
    """

    def __init__(self, execution: WorkflowExecution):
        self.execution = execution
        self.storage = CheckpointStorage()

    def create_checkpoint(
        self,
        current_node_id: Optional[str],
        completed_nodes: List[str],
        context_data: Dict[str, Any],
        node_results: Dict[str, Dict[str, Any]],
        skipped_nodes: Optional[List[str]] = None,
        errored_nodes: Optional[List[str]] = None
    ) -> bool:
        """
        Create a checkpoint of current execution state.

        Args:
            current_node_id: Currently executing node
            completed_nodes: List of completed node IDs
            context_data: Execution context
            node_results: Results from completed nodes
            skipped_nodes: List of skipped node IDs
            errored_nodes: List of errored node IDs

        Returns:
            True if checkpoint created successfully
        """
        checkpoint = CheckpointData(
            execution_id=str(self.execution.id),
            workflow_id=str(self.execution.workflow_id),
            workflow_version=self.execution.workflow.version,
            current_node_id=current_node_id,
            completed_node_ids=completed_nodes,
            skipped_node_ids=skipped_nodes or [],
            errored_node_ids=errored_nodes or [],
            context_data=context_data,
            node_results=node_results,
            timestamp=timezone.now().isoformat(),
            metadata={
                'execution_status': self.execution.status,
                'created_by': 'checkpoint_manager'
            }
        )

        return self.storage.save_checkpoint(self.execution, checkpoint)

    def can_resume(self) -> bool:
        """
        Check if execution can be resumed.

        Returns:
            True if there is a checkpoint and execution is resumable
        """
        if self.execution.status not in ('running', 'paused'):
            return False

        checkpoint = self.storage.load_latest_checkpoint(self.execution)
        return checkpoint is not None

    def get_resume_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information needed to resume execution.

        Returns:
            Dict with resume information or None
        """
        checkpoint = self.storage.load_latest_checkpoint(self.execution)
        if not checkpoint:
            return None

        return {
            'execution_id': str(self.execution.id),
            'workflow_id': checkpoint.workflow_id,
            'workflow_version': checkpoint.workflow_version,
            'current_node_id': checkpoint.current_node_id,
            'completed_node_ids': checkpoint.completed_node_ids,
            'skipped_node_ids': checkpoint.skipped_node_ids,
            'errored_node_ids': checkpoint.errored_node_ids,
            'context_data': checkpoint.context_data,
            'node_results': checkpoint.node_results,
            'checkpoint_timestamp': checkpoint.timestamp
        }

    def save_execution_state(
        self,
        current_node_id: str,
        context_data: Dict[str, Any],
        node_results: Dict[str, Dict[str, Any]],
        status: str
    ) -> bool:
        """
        Save current execution state (wrapper for checkpointing).

        Args:
            current_node_id: Currently executing node
            context_data: Execution context
            node_results: Results from all nodes
            status: Current execution status

        Returns:
            True if saved successfully
        """
        # Determine node states
        completed = []
        skipped = []
        errored = []

        for node_id, result in node_results.items():
            status = result.get('status', 'unknown')
            if status == 'success':
                completed.append(node_id)
            elif status == 'skipped':
                skipped.append(node_id)
            elif status == 'error':
                errored.append(node_id)

        return self.create_checkpoint(
            current_node_id=current_node_id,
            completed_nodes=completed,
            context_data=context_data,
            node_results=node_results,
            skipped_nodes=skipped,
            errored_nodes=errored
        )


class ExecutionResumer:
    """
    Handles resuming execution from checkpoints.
    """

    def __init__(self, execution: WorkflowExecution):
        self.execution = execution
        self.checkpoint_manager = WorkflowCheckpointManager(execution)

    def prepare_resume(self) -> Optional[Dict[str, Any]]:
        """
        Prepare execution for resumption.

        Returns:
            Resume configuration or None
        """
        if not self.checkpoint_manager.can_resume():
            return None

        resume_info = self.checkpoint_manager.get_resume_info()
        if not resume_info:
            return None

        # Update execution status
        self.execution.status = 'running'
        self.execution.metadata = {
            **self.execution.metadata,
            'resumed_from_checkpoint': True,
            'resume_at': timezone.now().isoformat()
        }
        self.execution.save(update_fields=['status', 'metadata', 'updated_at'])

        return resume_info

    def mark_resumption_complete(
        self,
        success: bool,
        final_output: Any = None
    ) -> None:
        """
        Mark resumption as complete.

        Args:
            success: Whether resume succeeded
            final_output: Final output from resumed execution
        """
        if success:
            self.execution.status = 'completed'
            self.execution.output = final_output
        else:
            self.execution.status = 'failed'

        self.execution.metadata = {
            **self.execution.metadata,
            'resumption_completed': True,
            'resumption_success': success,
            'completed_at': timezone.now().isoformat()
        }
        self.execution.save()


# Convenience functions

def create_checkpoint(execution: WorkflowExecution, **kwargs) -> bool:
    """Create a checkpoint for an execution."""
    manager = WorkflowCheckpointManager(execution)
    return manager.create_checkpoint(**kwargs)


def load_checkpoint(execution: WorkflowExecution) -> Optional[CheckpointData]:
    """Load latest checkpoint for an execution."""
    storage = CheckpointStorage()
    return storage.load_latest_checkpoint(execution)


def can_resume_execution(execution: WorkflowExecution) -> bool:
    """Check if an execution can be resumed."""
    manager = WorkflowCheckpointManager(execution)
    return manager.can_resume()


def resume_execution(execution: WorkflowExecution) -> Optional[Dict[str, Any]]:
    """Prepare an execution for resumption."""
    resumer = ExecutionResumer(execution)
    return resumer.prepare_resume()
