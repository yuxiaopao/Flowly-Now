"""
Workflow executor for running workflows.
"""

import json
import asyncio
import logging
import threading
import copy
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Optional, List, Set, Generator, Callable
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from ..models import Workflow, Node, Edge, WorkflowExecution, NodeExecution
from .langchain_service import langchain_service, LangChainService
from .context import ExecutionContext
from .error_handler import ErrorHandlerRegistry, NodeErrorHandler, ErrorStrategy


logger = logging.getLogger(__name__)


class ExecutionTimeoutError(Exception):
    """Raised when node execution exceeds timeout."""
    pass


class WorkflowExecutor:
    """
    Executor for running workflows.
    
    Supports:
    - Topological execution order
    - Multiple node types
    - Parallel node execution (when dependencies allow)
    - Error handling with retry/skip/fallback/stop strategies
    - Node execution timeout control
    - Pause/resume capability with context snapshots
    - WebSocket real-time updates
    - Execution context for variable management
    """

    def __init__(self, workflow: Workflow, execution: WorkflowExecution, parallel_enabled: bool = True):
        """Initialize executor."""
        self.workflow = workflow
        self.execution = execution
        self.langchain_service = (
            LangChainService(user_id=execution.triggered_by_id)
            if getattr(execution, 'triggered_by_id', None)
            else langchain_service
        )
        self.context = ExecutionContext()
        self.node_results: Dict[int, Dict[str, Any]] = {}
        self.graph: Dict[int, List[int]] = defaultdict(list)
        self.reverse_graph: Dict[int, List[int]] = defaultdict(list)
        self.node_map: Dict[int, Node] = {}
        self._streaming = False
        self._parallel_enabled = parallel_enabled
        self._context_lock = threading.RLock()
        self._cancelled = False
        self._paused = False
        self._pause_event = threading.Event()
        self._visited: Set[int] = set()
        self._pending_nodes: Dict[int, Node] = {}
        self._execution_order: List[int] = []
        self._node_executions: Dict[int, NodeExecution] = {}

    def build_graph(self) -> None:
        """Build adjacency lists from edges."""
        edges = list(self.workflow.edges.select_related('source_node', 'target_node').all())
        for edge in edges:
            self.graph[edge.source_node_id].append(edge.target_node_id)
            self.reverse_graph[edge.target_node_id].append(edge.source_node_id)
            self.node_map[edge.source_node_id] = edge.source_node
            self.node_map[edge.target_node_id] = edge.target_node

        all_nodes = list(self.workflow.nodes.all())
        for node in all_nodes:
            if node.id not in self.node_map:
                self.node_map[node.id] = node

    def find_start_nodes(self) -> List[Node]:
        """Find all start nodes (no incoming edges)."""
        all_nodes = list(self.workflow.nodes.all())
        start_node_ids = [
            node.id for node in all_nodes
            if node.id not in self.reverse_graph or not self.reverse_graph[node.id]
        ]
        return [node for node in all_nodes if node.id in start_node_ids and node.node_type == 'start']

    def find_end_nodes(self) -> List[Node]:
        """Find all end nodes (no outgoing edges)."""
        all_nodes = list(self.workflow.nodes.all())
        end_node_ids = [
            node.id for node in all_nodes
            if node.id not in self.graph or not self.graph[node.id]
        ]
        return [node for node in all_nodes if node.id in end_node_ids and node.node_type == 'end']

    def _create_or_update_node_execution(self, node: Node, status: str = 'running', **kwargs) -> NodeExecution:
        """Create or update NodeExecution record."""
        try:
            node_exec, created = NodeExecution.objects.get_or_create(
                execution=self.execution,
                node=node,
                defaults={
                    'node_version': node.version,
                    'status': status,
                    'input_data': self.context.to_dict(),
                }
            )
            if not created:
                node_exec.status = status
                node_exec.retry_count = kwargs.get('retry_count', node_exec.retry_count)
                node_exec.error_message = kwargs.get('error_message', node_exec.error_message)
                if 'output_data' in kwargs:
                    node_exec.output_data = kwargs['output_data']
                if 'started_at' in kwargs:
                    node_exec.started_at = kwargs['started_at']
                if 'completed_at' in kwargs:
                    node_exec.completed_at = kwargs['completed_at']
                node_exec.save()
            self._node_executions[node.id] = node_exec
            return node_exec
        except Exception as e:
            logger.warning(f"Failed to create/update NodeExecution for node {node.id}: {e}")
            return None

    def _execute_node_with_timeout(
        self,
        node: Node,
        timeout_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """Execute a node with optional timeout control."""
        error_handler = ErrorHandlerRegistry.create_from_node(node)

        def _do_execute():
            return self.langchain_service.execute_node(
                node.node_type,
                node.config,
                self.context.to_dict(),
                timeout_seconds=timeout_seconds
            )

        try:
            if timeout_seconds:
                import signal

                def timeout_handler(signum, frame):
                    raise ExecutionTimeoutError(f"Node '{node.name}' execution timed out after {timeout_seconds}s")

                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(timeout_seconds)
                try:
                    result = _do_execute()
                finally:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)
            else:
                result = _do_execute()

        except ExecutionTimeoutError as e:
            raise e
        except Exception as e:
            result = error_handler.handle(e, _do_execute)

        return result

    def execute_node(self, node: Node) -> Dict[str, Any]:
        """Execute a single node with error handling and timeout control."""
        self._update_node_status(node.id, 'running')

        node_exec = self._create_or_update_node_execution(node, status='running', started_at=timezone.now())

        timeout_seconds = getattr(node, 'timeout_seconds', None) or 300
        error_handler = ErrorHandlerRegistry.create_from_node(node)

        def _do_execute() -> Dict[str, Any]:
            return langchain_service.execute_node(
                node.node_type,
                node.config,
                self.context.to_dict(),
                timeout_seconds=timeout_seconds
            )

        try:
            result = _do_execute()
        except ExecutionTimeoutError as e:
            logger.warning(f"Node '{node.name}' timed out after {timeout_seconds}s")
            result = {
                'success': False,
                'error': str(e),
                'error_type': 'timeout'
            }
            self._handle_node_error(node, result, node_exec, error_handler)
            raise

        except Exception as e:
            logger.warning(f"Node '{node.name}' execution error: {e}")
            self._handle_node_error(node, result if 'result' in dir() else None, node_exec, error_handler, e)
            raise

        if result is None:
            return {
                'success': True,
                'output': {},
                'skipped': True
            }

        if node.error_handling == 'fallback' and not result.get('success'):
            result = {
                'success': True,
                'output': node.fallback_value or {},
                'used_fallback': True
            }

        self.node_results[node.id] = result

        if result.get('success') and result.get('output'):
            output = result['output']
            with self._context_lock:
                if isinstance(output, dict):
                    for key, value in output.items():
                        if not key.startswith('_'):
                            self.context.set_var(key, value)
                else:
                    self.context.set_var('last_output', output)
                self.context.set_var(f'{node.name}_output', output)
                self.context.set_node_output(str(node.id), output)

        if result.get('success'):
            self._update_node_status(node.id, 'completed', result.get('output'))
            if node_exec:
                node_exec.mark_completed(output_data=result.get('output'))
        else:
            self._update_node_status(node.id, 'failed', error=result.get('error'))
            if node_exec:
                node_exec.mark_failed(error_message=result.get('error', 'Unknown error'))

        self._broadcast_node_update(node, result)
        return result

    def _handle_node_error(
        self,
        node: Node,
        result: Optional[Dict[str, Any]],
        node_exec: Optional[NodeExecution],
        error_handler: NodeErrorHandler,
        error: Optional[Exception] = None
    ) -> None:
        """Handle node execution error with appropriate strategy."""
        error_msg = str(error) if error else result.get('error', 'Unknown error') if result else 'Unknown error'

        if node_exec:
            node_exec.retry_count += 1

        if node.error_handling == 'retry':
            if node_exec and node_exec.retry_count < node.max_retries:
                logger.info(f"Retrying node '{node.name}' (attempt {node_exec.retry_count + 1}/{node.max_retries})")
                import time
                time.sleep(node.retry_delay_seconds)
                try:
                    self.execute_node(node)
                    return
                except Exception as retry_error:
                    error_msg = str(retry_error)

        if node.error_handling == 'skip':
            logger.info(f"Skipping node '{node.name}' due to error")
            self.node_results[node.id] = {'success': True, 'skipped': True, 'skipped_reason': error_msg}
            self._update_node_status(node.id, 'skipped')
            if node_exec:
                node_exec.mark_skipped()
            return

        if node.error_handling == 'fallback':
            logger.info(f"Using fallback value for node '{node.name}'")
            fallback = node.fallback_value or {}
            self.node_results[node.id] = {'success': True, 'output': fallback, 'used_fallback': True}
            self._update_node_status(node.id, 'completed', fallback)
            if node_exec:
                node_exec.mark_completed(output_data=fallback)
            return

        self.node_results[node.id] = {'success': False, 'error': error_msg}
        self._update_node_status(node.id, 'failed', error=error_msg)
        if node_exec:
            node_exec.mark_failed(error_message=error_msg)
        self._broadcast_error(node, error_msg)

    def _find_parallel_ready_nodes(self, visited: Set[int], in_progress: Set[int]) -> List[List[Node]]:
        """Find groups of nodes that can be executed in parallel."""
        all_nodes = list(self.workflow.nodes.all())
        ready_groups = []
        
        for node in all_nodes:
            if node.id in visited or node.id in in_progress:
                continue

            deps = self.reverse_graph.get(node.id, [])
            if not deps or all(d in visited for d in deps):
                ready_groups.append(node)

        if not ready_groups:
            return []
        
        if not self._parallel_enabled or len(ready_groups) <= 1:
            return [[ready_groups[0]]] if ready_groups else []

        return [ready_groups]

    def _execute_parallel_nodes(self, nodes: List[Node]) -> List[Dict[str, Any]]:
        """Execute multiple nodes in parallel using ThreadPoolExecutor."""
        results = []
        threads = []
        
        def execute_with_lock(node: Node) -> tuple:
            with self._context_lock:
                if node.node_type in ['start', 'end']:
                    return node.id, {'success': True, 'output': {}}
                try:
                    result = self.execute_node(node)
                    return node.id, result
                except Exception as e:
                    return node.id, {'success': False, 'error': str(e)}

        with ThreadPoolExecutor(max_workers=min(len(nodes), 10)) as executor:
            futures = {executor.submit(execute_with_lock, node): node for node in nodes}
            for future in as_completed(futures):
                try:
                    node_id, result = future.result()
                    results.append((node_id, result))
                except Exception as e:
                    node = futures[future]
                    logger.error(f"Parallel execution failed for node {node.id}: {e}")
                    results.append((node.id, {'success': False, 'error': str(e)}))

        return results

    def get_next_nodes(self, current_node: Node) -> List[Node]:
        """Get next nodes based on execution result."""
        outgoing_edges = list(current_node.outgoing_edges.all())

        if not outgoing_edges:
            return []

        if current_node.node_type == 'condition':
            result = self.node_results.get(current_node.id, {})
            branch = result.get('branch', 'default')

            for edge in outgoing_edges:
                if edge.label == branch:
                    return [edge.target_node]

            for edge in outgoing_edges:
                if edge.label == 'default':
                    return [edge.target_node]

            return []

        return [edge.target_node for edge in outgoing_edges]

    def execute(self) -> WorkflowExecution:
        """Execute the entire workflow (synchronous)."""
        self.execution.status = 'running'
        self.execution.started_at = timezone.now()
        self.execution.save()

        self._broadcast_execution_start()

        try:
            self.build_graph()

            if isinstance(self.execution.input_data, dict):
                self.context = ExecutionContext(input_data=self.execution.input_data)
            else:
                self.context = ExecutionContext(input_data={})

            start_nodes = self.find_start_nodes()

            if not start_nodes:
                start_nodes = [
                    node for node in self.workflow.nodes.all()
                    if node.id not in self.reverse_graph or not self.reverse_graph[node.id]
                ]

            self._visited: Set[int] = set()
            queue = deque(start_nodes)

            while queue and not self._cancelled:
                if self._paused:
                    self._pause_event.wait()
                    self._pause_event.clear()

                current_node = queue.popleft()

                if current_node.id in self._visited:
                    continue

                self._visited.add(current_node.id)

                if current_node.node_type not in ['start', 'end']:
                    result = self.execute_node(current_node)

                    if not result.get('success') and not result.get('skipped'):
                        raise Exception(result.get('error', 'Node execution failed'))

                next_nodes = self.get_next_nodes(current_node)

                for next_node in next_nodes:
                    if next_node.id not in self._visited:
                        queue.append(next_node)

                if self._parallel_enabled and len(next_nodes) > 1:
                    parallel_nodes = [n for n in next_nodes if n.id not in self._visited]
                    if len(parallel_nodes) > 1:
                        parallel_results = self._execute_parallel_nodes(parallel_nodes)
                        for node_id, result in parallel_results:
                            self._visited.add(node_id)
                            if not result.get('success') and not result.get('skipped'):
                                raise Exception(result.get('error', 'Parallel node execution failed'))

            self._finalize_execution('completed')
            return self.execution

        except Exception as e:
            logger.exception(f"Workflow execution failed: {e}")
            self._finalize_execution('failed', error_message=str(e))
            return self.execution

    def pause(self) -> None:
        """Pause the workflow execution."""
        self._paused = True
        self.execution.status = 'paused'
        self.execution.paused_at = timezone.now()
        self.execution.context_snapshot = {
            'visited': list(self._visited),
            'node_results': self.node_results,
            'context_data': self.context.to_dict(),
            'paused_at': timezone.now().isoformat(),
            'execution_order': self._execution_order,
        }
        self.execution.save(update_fields=['status', 'paused_at', 'context_snapshot'])
        self._broadcast_execution_event('execution_paused', {
            'execution_id': self.execution.id,
            'context_snapshot': self.execution.context_snapshot
        })

    def resume(self) -> WorkflowExecution:
        """Resume a paused workflow execution."""
        if self.execution.status != 'paused':
            raise ValueError("Execution is not paused")

        snapshot = self.execution.get_context_snapshot()
        if snapshot:
            self._visited = set(snapshot.get('visited', []))
            self.node_results = snapshot.get('node_results', {})
            context_data = snapshot.get('context_data', {})
            self.context = ExecutionContext(input_data=context_data.get('input_data', {}))
            self.context.variables = context_data.get('variables', {})
            self.context.node_outputs = context_data.get('node_outputs', {})
            self._execution_order = snapshot.get('execution_order', [])

        self.execution.status = 'running'
        self.execution.paused_at = None
        self.execution.save(update_fields=['status', 'paused_at'])

        self._paused = False
        self._pause_event.set()

        return self.execute()

    def cancel(self) -> None:
        """Cancel the workflow execution."""
        self._cancelled = True
        self._paused = False
        self._pause_event.set()

    def _finalize_execution(self, status: str, error_message: str = None) -> None:
        """Finalize workflow execution."""
        self.execution.status = status
        self.execution.output_data = self.context.to_dict()
        self.execution.completed_at = timezone.now()
        if error_message:
            self.execution.error_message = error_message
        if self.execution.started_at:
            self.execution.duration_ms = int(
                (self.execution.completed_at - self.execution.started_at).total_seconds() * 1000
            )
        self.execution.save()

        if status == 'completed':
            self._broadcast_execution_complete()
        else:
            self._broadcast_execution_error(error_message or 'Unknown error')

    def stream_execute(self) -> Generator[Dict[str, Any], None, None]:
        """Execute workflow with streaming output (generator)."""
        self._streaming = True
        self.execution.status = 'running'
        self.execution.started_at = timezone.now()
        self.execution.save()

        yield {
            'type': 'execution_start',
            'execution_id': self.execution.id,
            'workflow_id': self.workflow.id,
            'status': 'running'
        }

        try:
            self.build_graph()

            if isinstance(self.execution.input_data, dict):
                self.context = ExecutionContext(input_data=self.execution.input_data)
            else:
                self.context = ExecutionContext(input_data={})

            start_nodes = self.find_start_nodes()

            if not start_nodes:
                start_nodes = [
                    node for node in self.workflow.nodes.all()
                    if node.id not in self.reverse_graph or not self.reverse_graph[node.id]
                ]

            self._visited: Set[int] = set()
            queue = deque(start_nodes)

            while queue and not self._cancelled:
                if self._paused:
                    yield {
                        'type': 'execution_paused',
                        'execution_id': self.execution.id,
                        'context_snapshot': {
                            'visited': list(self._visited),
                            'node_results': self.node_results,
                            'context_data': self.context.to_dict(),
                        }
                    }
                    self._pause_event.wait()
                    self._pause_event.clear()

                current_node = queue.popleft()

                if current_node.id in self._visited:
                    continue

                self._visited.add(current_node.id)

                if current_node.node_type not in ['start', 'end']:
                    yield {
                        'type': 'node_start',
                        'node_id': current_node.id,
                        'node_name': current_node.name,
                        'node_type': current_node.node_type
                    }

                    try:
                        result = self.execute_node(current_node)
                    except Exception as e:
                        result = {'success': False, 'error': str(e)}

                    yield {
                        'type': 'node_complete',
                        'node_id': current_node.id,
                        'node_name': current_node.name,
                        'status': 'completed' if result.get('success') else 'failed',
                        'output': result.get('output'),
                        'error': result.get('error'),
                        'skipped': result.get('skipped', False)
                    }

                    if result.get('success') and isinstance(result.get('output'), dict):
                        output_data = result['output']
                        if 'text' in output_data:
                            yield {
                                'type': 'stream_output',
                                'node_id': current_node.id,
                                'text': output_data['text'],
                                'partial': True
                            }

                    if not result.get('success') and not result.get('skipped'):
                        raise Exception(result.get('error', 'Node execution failed'))

                next_nodes = self.get_next_nodes(current_node)

                for next_node in next_nodes:
                    if next_node.id not in self._visited:
                        queue.append(next_node)

            self.execution.status = 'completed'
            self.execution.output_data = self.context.to_dict()
            self.execution.completed_at = timezone.now()
            self.execution.save()

            yield {
                'type': 'execution_complete',
                'execution_id': self.execution.id,
                'status': 'completed',
                'output_data': self.context.to_dict()
            }

        except Exception as e:
            logger.exception(f"Workflow execution failed: {e}")
            self.execution.status = 'failed'
            self.execution.error_message = str(e)
            self.execution.completed_at = timezone.now()
            self.execution.save()

            yield {
                'type': 'execution_error',
                'execution_id': self.execution.id,
                'status': 'failed',
                'error': str(e)
            }

    def _update_node_status(
        self,
        node_id: int,
        status: str,
        output: Any = None,
        error: str = None
    ) -> None:
        """Update node status in execution record."""
        node_status = self.execution.node_status or {}
        existing = node_status.get(str(node_id), {})
        node_status[str(node_id)] = {
            'status': status,
            'output': output or existing.get('output'),
            'error': error or existing.get('error'),
            'updated_at': timezone.now().isoformat()
        }
        self.execution.node_status = node_status
        self.execution.save(update_fields=['node_status'])

    def _broadcast_execution_start(self) -> None:
        """Broadcast execution start via WebSocket."""
        self._broadcast('execution_start', {
            'execution_id': self.execution.id,
            'workflow_id': self.workflow.id,
            'status': 'running'
        })

    def _broadcast_node_update(self, node: Node, result: Dict[str, Any]) -> None:
        """Broadcast node update via WebSocket."""
        self._broadcast('execution_node_complete', {
            'execution_id': self.execution.id,
            'node_id': node.id,
            'node_name': node.name,
            'status': 'completed' if result.get('success') else 'failed',
            'output': result.get('output'),
            'error': result.get('error')
        })

    def _broadcast_execution_complete(self) -> None:
        """Broadcast execution complete via WebSocket."""
        self._broadcast('execution_complete', {
            'execution_id': self.execution.id,
            'workflow_id': self.workflow.id,
            'status': 'completed',
            'output': self.context.to_dict()
        })

    def _broadcast_execution_error(self, error: str) -> None:
        """Broadcast execution error via WebSocket."""
        self._broadcast('execution_error', {
            'execution_id': self.execution.id,
            'workflow_id': self.workflow.id,
            'status': 'failed',
            'error': error
        })

    def _broadcast_error(self, node: Node, error: str) -> None:
        """Broadcast node error via WebSocket."""
        self._broadcast('execution_node_error', {
            'execution_id': self.execution.id,
            'node_id': node.id,
            'node_name': node.name,
            'error': error
        })

    def _broadcast_execution_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Broadcast execution event via WebSocket."""
        self._broadcast(event_type, data)

    def _broadcast(self, event_type: str, data: Dict[str, Any]) -> None:
        """Broadcast message via channel layer."""
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f'execution_{self.execution.id}',
                    {
                        'type': event_type,
                        'data': data
                    }
                )
        except Exception:
            pass
