"""
Workflow executor for running workflows.
"""

import json
import asyncio
import logging
import threading
import copy
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Optional, List, Set, Generator, Callable, Tuple
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from ..models import Workflow, Node, Edge, WorkflowExecution, NodeExecution
from .langchain_service import LangChainService
from .context import ExecutionContext
from .error_handler import ErrorHandlerRegistry, NodeErrorHandler, ErrorStrategy
from ..execution_control import (
    make_json_safe,
    write_heartbeat,
    heartbeat_interval_seconds,
)


logger = logging.getLogger(__name__)

# Finishing / media nodes that must not abort the whole short-drama film
_SOFT_FAIL_NODE_TYPES = frozenset({
    'image_generation', 'video_generation', 'audio_generation', 'image_editing',
    'subtitle_generation', 'subtitle_burn',
})

# LLM nodes used only for packaging / narration polish — soft-fail if provider flakes
_SOFT_FAIL_LLM_NAME_HINTS = ('包装', '宣发', '旁白')


def _is_soft_fail_node(node) -> bool:
    if (getattr(node, 'config', None) or {}).get('require_success') is True:
        return False
    if getattr(node, 'node_type', None) in _SOFT_FAIL_NODE_TYPES:
        return True
    if getattr(node, 'node_type', None) == 'llm':
        name = getattr(node, 'name', None) or ''
        return any(h in name for h in _SOFT_FAIL_LLM_NAME_HINTS)
    return False


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
        """Initialize executor.

        Each execution gets an isolated LangChainService so concurrent workflows
        do not share mutable client/session state.
        """
        self.workflow = workflow
        self.execution = execution
        self.langchain_service = LangChainService(
            user_id=getattr(execution, 'triggered_by_id', None)
        )
        initial_input = execution.input_data if isinstance(execution.input_data, dict) else {}
        self.context = ExecutionContext(input_data=initial_input)
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
        self._last_checkpoint_at = 0.0
        self._checkpoint_interval_sec = 20.0
        self._control_poll_every_n = 1
        self._loop_iterations = 0
        self._stop_reason: Optional[str] = None  # paused | interrupted | cancelled
        self._in_flight_nodes: Set[int] = set()
        self._last_heartbeat_at = 0.0

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

    def get_previous_nodes(self, node: Node) -> List[Node]:
        """Direct upstream nodes (incoming edges)."""
        ids = self.reverse_graph.get(node.id, []) or []
        result: List[Node] = []
        for nid in ids:
            prev = self.node_map.get(nid)
            if prev is not None:
                result.append(prev)
        return result

    def _build_node_execution_context(self, node: Node) -> Dict[str, Any]:
        """Build per-node context so parallel branches do not share last-wins vars.

        Overlay direct predecessor outputs as `_branch_upstream` (and into variables)
        so image/video templates like {image_prompt} resolve from THIS chain's pick,
        not whatever the last parallel pick wrote into the global context.
        """
        ctx = self.context.to_dict()
        variables = dict(ctx.get('variables') or {})
        branch: Dict[str, Any] = {}

        for pred in self.get_previous_nodes(node):
            out = None
            # Prefer live results from this run
            live = self.node_results.get(pred.id) or {}
            if isinstance(live, dict) and isinstance(live.get('output'), dict):
                out = live.get('output')
            if out is None:
                out = self.context.get_node_output(str(pred.id))
            if not isinstance(out, dict):
                continue
            for key, value in out.items():
                if str(key).startswith('_'):
                    continue
                if value in (None, ''):
                    continue
                branch[key] = value
                variables[key] = value

        ctx['variables'] = variables
        if branch:
            ctx['_branch_upstream'] = branch
        return ctx

    def execute_node(self, node: Node) -> Dict[str, Any]:
        """Execute a single node with error handling and timeout control."""
        self._update_node_status(node.id, 'running')

        node_exec = self._create_or_update_node_execution(node, status='running', started_at=timezone.now())

        timeout_seconds = getattr(node, 'timeout_seconds', None)
        if not timeout_seconds:
            defaults = {
                'image_generation': 900,
                'video_generation': 1800,
                'audio_generation': 300,
                'subtitle_generation': 600,
                'video_translation': 3600,
                'video_upload': 120,
                'subtitle_translate': 600,
                'segment_dubbing': 900,
                'lip_sync': 1200,
                'subtitle_burn': 600,
                'model_training': 3600,
            }
            timeout_seconds = defaults.get(node.node_type, 300)
        error_handler = ErrorHandlerRegistry.create_from_node(node)

        def _do_execute() -> Dict[str, Any]:
            node_config = node.config or {}
            if node.node_type == 'email':
                node_config = self.langchain_service._normalize_email_node_config(node_config)
            return self.langchain_service.execute_node(
                node.node_type,
                node_config,
                self._build_node_execution_context(node),
                timeout_seconds=timeout_seconds
            )

        def _progress_reporter(payload: Dict[str, Any]) -> None:
            if not node_exec:
                return
            merged = {**(node_exec.output_data or {}), **(payload or {})}
            node_exec.output_data = merged
            node_exec.save(update_fields=['output_data', 'updated_at'])
            self._update_node_status(node.id, 'running', merged)

        self.langchain_service.set_progress_reporter(_progress_reporter)
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
            handled = self.node_results.get(node.id)
            if handled and handled.get('success'):
                return handled
            raise

        except Exception as e:
            logger.warning(f"Node '{node.name}' execution error: {e}")
            self._handle_node_error(node, result if 'result' in dir() else None, node_exec, error_handler, e)
            handled = self.node_results.get(node.id)
            if handled and handled.get('success'):
                return handled
            raise
        finally:
            self.langchain_service.clear_progress_reporter()

        if result is None:
            return {
                'success': True,
                'output': {},
                'skipped': True
            }

        if node.error_handling == 'skip' and not result.get('success'):
            self._handle_node_error(node, result, node_exec, error_handler)
            return self.node_results[node.id]

        if node.error_handling == 'fallback' and not result.get('success'):
            result = {
                'success': True,
                'output': node.fallback_value if node.fallback_value is not None else {},
                'used_fallback': True
            }

        self.node_results[node.id] = result

        if result.get('success') and 'output' in result:
            self._store_node_output(node, result['output'])

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

    def _store_node_output(self, node: Node, output: Any) -> None:
        with self._context_lock:
            if isinstance(output, dict):
                for key, value in output.items():
                    if not key.startswith('_'):
                        self.context.set_var(key, value)
            else:
                self.context.set_var('last_output', output)
            self.context.set_var(f'{node.name}_output', output)
            self.context.set_node_output(str(node.id), output)

    def _complete_boundary_node(self, node: Node) -> Dict[str, Any]:
        result = {'success': True, 'output': {}}
        node_exec = self._create_or_update_node_execution(node, status='running')
        if node_exec:
            node_exec.mark_completed(output_data={})
        self.node_results[node.id] = result
        self._update_node_status(node.id, 'completed', {})
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
            fallback = node.fallback_value if node.fallback_value is not None else {}
            self.node_results[node.id] = {'success': True, 'output': fallback, 'used_fallback': True}
            self._store_node_output(node, fallback)
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

    _MEDIA_PARALLEL_TYPES = frozenset({
        'image_generation', 'video_generation', 'audio_generation', 'image_editing',
    })

    def _execute_parallel_nodes(self, nodes: List[Node]) -> List[Dict[str, Any]]:
        """Execute multiple nodes in parallel using ThreadPoolExecutor.

        Do NOT hold `_context_lock` around the full `execute_node` call — that
        previously serialized "parallel" work and made 12-shot fan-out hang on
        one slow LLM/media node.

        Media fan-out is capped (Agnes rate-limits / times out under high concurrency).
        """
        results = [(node.id, self._complete_boundary_node(node)) for node in nodes if node.node_type in ('start', 'end')]
        nodes = [node for node in nodes if node.node_type not in ('start', 'end')]
        if not nodes:
            return results
        
        def execute_one(node: Node) -> tuple:
                try:
                    result = self.execute_node(node)
                    return node.id, result
                except Exception as e:
                    return node.id, {'success': False, 'error': str(e)}

        has_media = any(n.node_type in self._MEDIA_PARALLEL_TYPES for n in nodes)
        # Agnes image/video collapses under concurrency — run media strictly serial.
        max_workers = 1 if has_media else min(len(nodes), 8)
        if has_media and len(nodes) > 1:
            # Serial with spacing to avoid provider 503 / connection resets
            for idx, node in enumerate(nodes):
                if idx:
                    time.sleep(5.0)
                results.append(execute_one(node))
            return results

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(execute_one, node): node for node in nodes}
            for future in as_completed(futures):
                try:
                    node_id, result = future.result()
                    results.append((node_id, result))
                except Exception as e:
                    node = futures[future]
                    logger.error(f"Parallel execution failed for node {node.id}: {e}")
                    results.append((node.id, {'success': False, 'error': str(e)}))

        return results

    def _is_join_node(self, node: Node) -> bool:
        name = node.name or ''
        return (
            node.node_type in {
                'merge', 'output', 'end', 'subtitle_generation', 'subtitle_burn',
                'audio_generation',
            }
            or '汇总' in name
            or '拼接' in name
            or '成片' in name
        )

    def _cascade_skip_until_join(self, node: Node) -> List[Node]:
        """Mark downstream shot-chain nodes skipped; return join nodes to re-check."""
        joins: List[Node] = []
        stack = list(self.get_next_nodes(node))
        while stack:
            nxt = stack.pop()
            if self._is_join_node(nxt):
                joins.append(nxt)
                continue
            if nxt.id in self._visited:
                # Still surface joins beyond already-skipped nodes
                stack.extend(self.get_next_nodes(nxt))
                continue
            self._visited.add(nxt.id)
            self.node_results[nxt.id] = {
                'success': True,
                'skipped': True,
                'skipped_reason': f'upstream soft-fail: {node.name}',
            }
            self._update_node_status(nxt.id, 'skipped')
            for child in self.get_next_nodes(nxt):
                if self._is_join_node(child):
                    joins.append(child)
                else:
                    stack.append(child)
        return joins

    def _handle_parallel_wave_results(
        self,
        wave: List[Node],
        parallel_results: List[tuple],
    ) -> Tuple[List[Node], List[Node]]:
        """Apply parallel results; soft-fail media nodes so partial films can continue.

        Returns (completed_nodes, join_nodes_to_check).
        """
        node_by_id = {n.id: n for n in wave}
        completed_nodes: List[Node] = []
        join_nodes: List[Node] = []
        hard_errors: List[str] = []
        for node_id, result in parallel_results:
            node = node_by_id[node_id]
            completed_nodes.append(node)
            # Ensure node_results populated when execute_one caught exceptions
            if node.id not in self.node_results and isinstance(result, dict):
                self.node_results[node.id] = result
            if result.get('success') or result.get('skipped'):
                continue
            err = result.get('error') or 'Parallel node execution failed'
            if node.node_type in self._MEDIA_PARALLEL_TYPES:
                logger.error(
                    "Soft-fail media node %s (%s): %s",
                    node.name, node.id, err,
                )
                self.node_results[node.id] = {
                    'success': True,
                    'skipped': True,
                    'skipped_reason': err,
                    'output': result.get('output') or {},
                }
                self._update_node_status(node.id, 'failed', {'error': err})
                # Keep video runnable after image soft-fail (text-to-video path)
                if node.node_type != 'image_generation':
                    join_nodes.extend(self._cascade_skip_until_join(node))
                continue
            hard_errors.append(f"{node.name}: {err}")
        if hard_errors:
            raise Exception('; '.join(hard_errors))
        return completed_nodes, join_nodes

    def _drain_ready_wave(
        self,
        seed: Node,
        queue: deque,
        queued_ids: Set[Any],
    ) -> List[Node]:
        """Pull currently-ready siblings from the queue into one parallel wave."""
        wave = [seed]
        deferred: deque = deque()
        while queue:
            candidate = queue.popleft()
            queued_ids.discard(candidate.id)
            if candidate.id in self._visited:
                continue
            if self._predecessors_ready(candidate):
                wave.append(candidate)
            else:
                deferred.append(candidate)
                queued_ids.add(candidate.id)
        queue.extend(deferred)
        return wave

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

            # 无分支标签时沿用线性连线（编辑器默认不设置 edge.label）
            if len(outgoing_edges) == 1:
                return [outgoing_edges[0].target_node]
            return [edge.target_node for edge in outgoing_edges]

        return [edge.target_node for edge in outgoing_edges]

    def _discover_loop_body_and_exit(self, loop_node: Node) -> tuple[List[Node], Optional[Node]]:
        """
        Discover loop body as the subgraph reachable from loop successors until a merge/join.
        Returns (body_nodes_in_order, exit_node).
        """
        successors = self.get_next_nodes(loop_node)
        if not successors:
            return [], None

        exit_node = None
        body_roots = []
        for node in successors:
            if node.node_type == 'merge':
                exit_node = node
            else:
                body_roots.append(node)

        if not body_roots and exit_node is None and successors:
            # Single successor: treat as body start; find merge downstream
            body_roots = [successors[0]]

        body_ids: Set[Any] = set()
        ordered: List[Node] = []
        queue = deque(body_roots)
        terminal_types = {
            'merge', 'output', 'end', 'subtitle_generation', 'subtitle_burn',
            'subtitle_translate', 'segment_dubbing',
        }
        while queue:
            node = queue.popleft()
            if node.id in body_ids:
                continue
            if node.node_type == 'merge':
                exit_node = exit_node or node
                continue
            if node.node_type in terminal_types:
                continue
            body_ids.add(node.id)
            ordered.append(node)
            for nxt in self.get_next_nodes(node):
                if nxt.node_type == 'merge':
                    exit_node = exit_node or nxt
                    continue
                if nxt.node_type in terminal_types:
                    continue
                if nxt.id not in body_ids:
                    queue.append(nxt)

        # Prefer topological-ish order along first path
        return ordered, exit_node

    def _resolve_loop_items(self, loop_node: Node) -> List[Any]:
        """Resolve iterable items for a loop node from context / config."""
        config = loop_node.config or {}
        ctx = self.context.to_dict() if self.context else {}
        # Reuse LangChain for_each resolution by calling with empty body once for items only
        items_source = config.get('items_source', 'input')
        item_variable = config.get('item_variable', 'item')
        max_iterations = int(config.get('max_iterations') or 100)
        results, count = self.langchain_service._execute_for_each_loop(
            items=config.get('items') or [],
            items_source=items_source,
            input_data=ctx,
            item_variable=item_variable,
            index_variable=config.get('index_variable', 'index'),
            max_iterations=max_iterations,
            body_nodes=[],
            continue_on_error=True,
        )
        # _execute_for_each_loop with empty body still iterates items; recover items from results
        items = [r.get('item') for r in results] if results else []
        if not items:
            # Direct resolve again for safety
            for key in ('items', 'data', 'result', 'chapters', 'shots', 'scenes'):
                candidate = ctx.get(key)
                if isinstance(candidate, list) and candidate:
                    items = candidate[:max_iterations]
                    break
            if not items:
                variables = ctx.get('variables') if isinstance(ctx.get('variables'), dict) else {}
                for key in ('items', 'data', 'result', 'chapters', 'shots', 'scenes'):
                    candidate = variables.get(key)
                    if isinstance(candidate, list) and candidate:
                        items = candidate[:max_iterations]
                        break
        # Last resort: parse LLM JSON array sitting in variables.text / text
        if not items:
            try:
                parsed = self.langchain_service.run_json_transform_node(
                    {'operation': 'parse_array', 'target_field': 'items'},
                    ctx,
                )
                output = (parsed or {}).get('output') if isinstance(parsed, dict) else None
                candidate = None
                if isinstance(output, dict):
                    candidate = output.get('items') or output.get('data')
                if isinstance(candidate, list) and candidate:
                    items = candidate[:max_iterations]
            except Exception:
                pass
        return items[:max_iterations]

    def _execute_loop_subgraph(self, loop_node: Node) -> Dict[str, Any]:
        """
        Execute loop body nodes once per item, then return aggregated loop output.
        Marks body nodes as visited so the main walker does not re-run them singly.
        """
        config = loop_node.config or {}
        item_variable = config.get('item_variable', 'item')
        index_variable = config.get('index_variable', 'index')
        max_iterations = int(config.get('max_iterations') or 100)
        continue_on_error = bool(config.get('continue_on_error', True))

        body_nodes, exit_node = self._discover_loop_body_and_exit(loop_node)
        items = self._resolve_loop_items(loop_node)

        # Fallback: still run loop node runner (may no-op body) for status parity
        if not body_nodes or not items:
            result = self.execute_node(loop_node)
            return result

        loop_results = []
        video_urls = []
        image_urls = []
        errors = []

        self._update_node_status(loop_node.id, 'running')
        loop_exec = self._create_or_update_node_execution(loop_node, status='running', started_at=timezone.now())

        for i, item in enumerate(items):
            if i >= max_iterations:
                break
            with self._context_lock:
                self.context.set_var(item_variable, item)
                self.context.set_var(index_variable, i)
                self.context.set_var('chapter', item)
                self.context.set_var('shot', item)
                if isinstance(item, dict):
                    for key, value in item.items():
                        if not str(key).startswith('_'):
                            self.context.set_var(key, value)
                    # Prefer textual fields as input for LLM/code body
                    for key in ('text', 'prompt', '情节概要', '章节标题', 'scene_description', 'description', 'content'):
                        if item.get(key):
                            self.context.set_var('input', item.get(key))
                            self.context.set_var('text', item.get(key))
                            break
                else:
                    self.context.set_var('input', item)
                    self.context.set_var('text', item)

            iteration_output = {}
            try:
                for body_node in body_nodes:
                    # Allow body nodes to re-run each iteration
                    self._visited.discard(body_node.id)
                    body_result = self.execute_node(body_node)
                    # Retry transient Agnes/network failures inside loop body
                    if (
                        not body_result.get('success')
                        and not body_result.get('skipped')
                        and body_node.node_type in ('image_generation', 'video_generation')
                    ):
                        err = str(body_result.get('error') or '')
                        if any(k in err.lower() for k in ('connection', 'timeout', 'timed out', '503', '502', '429')):
                            import time as _time
                            for attempt in range(1, 4):
                                logger.warning(
                                    'Loop body %s failed (%s), retry %s/3',
                                    body_node.name, err[:120], attempt,
                                )
                                _time.sleep(min(30, 5 * attempt))
                                self._visited.discard(body_node.id)
                                body_result = self.execute_node(body_node)
                                if body_result.get('success') or body_result.get('skipped'):
                                    break
                                err = str(body_result.get('error') or '')
                    if not body_result.get('success') and not body_result.get('skipped'):
                        raise Exception(body_result.get('error', f'Loop body failed: {body_node.name}'))
                    out = body_result.get('output') or {}
                    iteration_output[str(body_node.id)] = out
                    # Relay body output → next body node as `input`/`text`
                    # (code/image nodes often read the generic `input` slot)
                    with self._context_lock:
                        if isinstance(out, dict):
                            for key, value in out.items():
                                if not str(key).startswith('_') and value not in (None, ''):
                                    self.context.set_var(key, value)
                            relay = (
                                out.get('text')
                                or out.get('content')
                                or out.get('prompt')
                                or out.get('image_prompt')
                                or out.get('scene_description')
                                or out
                            )
                            self.context.set_var('input', relay)
                            if isinstance(relay, (str, dict, list)):
                                self.context.set_var('text', relay if not isinstance(relay, dict) else (
                                    relay.get('text') or relay.get('image_prompt') or relay.get('scene_description') or json.dumps(relay, ensure_ascii=False)
                                ))
                            self.context.set_var('last_output', out)
                        elif out not in (None, ''):
                            self.context.set_var('input', out)
                            self.context.set_var('text', out)
                            self.context.set_var('last_output', out)
                    if isinstance(out, dict):
                        if out.get('video_url'):
                            video_urls.append(out['video_url'])
                        images = out.get('images')
                        if isinstance(images, list) and images:
                            url = images[0].get('url') if isinstance(images[0], dict) else None
                            if url:
                                image_urls.append(url)
                loop_results.append({
                    'item': item,
                    'index': i,
                    'success': True,
                    'output': iteration_output,
                    'video_url': next(
                        (
                            (iteration_output[str(n.id)] or {}).get('video_url')
                            for n in reversed(body_nodes)
                            if isinstance(iteration_output.get(str(n.id)), dict)
                            and iteration_output[str(n.id)].get('video_url')
                        ),
                        None,
                    ),
                })
            except Exception as exc:
                errors.append({'index': i, 'error': str(exc)})
                loop_results.append({'item': item, 'index': i, 'success': False, 'error': str(exc)})
                if not continue_on_error:
                    raise

        # Mark body consumed so main BFS does not execute them as single-pass
        for body_node in body_nodes:
            self._visited.add(body_node.id)

        output = {
            'count': len(loop_results),
            'iterations': len(loop_results),
            'results': loop_results,
            'loop_result': loop_results,
            'items': loop_results,
            'video_urls': video_urls,
            'images': [{'url': u} for u in image_urls],
            'max_iterations': max_iterations,
            'errors': errors or None,
        }
        if video_urls:
            output['video_url'] = video_urls[-1]

        result = {'success': True, 'output': output}
        self.node_results[loop_node.id] = result
        with self._context_lock:
            for key, value in output.items():
                if not str(key).startswith('_'):
                    self.context.set_var(key, value)
            self.context.set_var(f'{loop_node.name}_output', output)
            self.context.set_node_output(str(loop_node.id), output)

        self._update_node_status(loop_node.id, 'completed', output)
        if loop_exec:
            loop_exec.mark_completed(output_data=output)
        self._broadcast_node_update(loop_node, result)
        return result

    def _predecessors_ready(self, node: Node) -> bool:
        """True when all inbound dependencies have been visited (completed)."""
        deps = self.reverse_graph.get(node.id, [])
        return all(dep_id in self._visited for dep_id in deps)

    def _enqueue_ready_successors(
        self,
        queue: deque,
        nodes: List[Node],
        *,
        queued_ids: Set[Any],
    ) -> None:
        """Enqueue successors whose predecessors are all completed."""
        for node in nodes:
            for successor in self.get_next_nodes(node):
                if successor.id in self._visited or successor.id in queued_ids:
                    continue
                if not self._predecessors_ready(successor):
                    continue
                queue.append(successor)
                queued_ids.add(successor.id)

    def _serialize_node_results(self) -> Dict[str, Any]:
        """JSON-safe node_results (keys as strings)."""
        out = {}
        for nid, result in self.node_results.items():
            try:
                out[str(nid)] = copy.deepcopy(result)
            except Exception:
                out[str(nid)] = result
        return out

    @staticmethod
    def _node_id_key(nid: Any) -> Any:
        """Preserve UUID/str/int node ids without forcing int()."""
        if nid is None:
            return nid
        if isinstance(nid, int):
            return nid
        # UUID objects
        if hasattr(nid, 'hex') and not isinstance(nid, (str, bytes)):
            return nid
        s = str(nid)
        # numeric string → int (legacy)
        if s.isdigit():
            try:
                return int(s)
            except (TypeError, ValueError):
                return s
        return s

    @staticmethod
    def _deserialize_node_results(raw: Optional[Dict[str, Any]]) -> Dict[Any, Dict[str, Any]]:
        if not raw:
            return {}
        restored: Dict[Any, Dict[str, Any]] = {}
        for k, v in raw.items():
            restored[WorkflowExecutor._node_id_key(k)] = v
        return restored

    def _build_context_snapshot(
        self,
        queue: Optional[deque] = None,
        queued_ids: Optional[Set[Any]] = None,
        reason: str = 'progress',
    ) -> Dict[str, Any]:
        return make_json_safe({
            'visited': [str(x) for x in self._visited],
            'node_results': self._serialize_node_results(),
            'context_data': self.context.to_dict(),
            'execution_order': list(self._execution_order),
            'queue_node_ids': [str(n.id) for n in (queue or [])],
            'queued_ids': [str(x) for x in (queued_ids or set())],
            'reason': reason,
            'saved_at': timezone.now().isoformat(),
            'execution_id': str(self.execution.id),
        })

    def _maybe_heartbeat(self) -> None:
        now = time.time()
        if (now - self._last_heartbeat_at) < heartbeat_interval_seconds():
            return
        try:
            write_heartbeat(self.execution, extra={
                'visited_count': len(self._visited),
                'in_flight': [str(x) for x in self._in_flight_nodes],
            })
            self._last_heartbeat_at = now
        except Exception as e:
            logger.debug('Heartbeat failed: %s', e)

    def _persist_checkpoint(
        self,
        queue: Optional[deque] = None,
        queued_ids: Optional[Set[Any]] = None,
        reason: str = 'progress',
        force: bool = False,
    ) -> Dict[str, Any]:
        """Save resume snapshot (+ optional checkpoint history). Isolated per execution."""
        now = time.time()
        if not force and (now - self._last_checkpoint_at) < self._checkpoint_interval_sec:
            return self.execution.context_snapshot or {}

        # Incomplete in-flight nodes must re-run on resume
        visited_for_snap = set(self._visited) - set(self._in_flight_nodes)

        snapshot = {
            'visited': [str(x) for x in visited_for_snap],
            'node_results': {
                str(k): v for k, v in self._serialize_node_results().items()
                if self._node_id_key(k) in visited_for_snap or (
                    isinstance(v, dict) and (v.get('success') or v.get('skipped'))
                )
            },
            'context_data': self.context.to_dict(),
            'execution_order': list(self._execution_order),
            'queue_node_ids': [str(n.id) for n in (queue or [])] + [
                str(x) for x in self._in_flight_nodes
            ],
            'queued_ids': [str(x) for x in (queued_ids or set())],
            'in_flight_node_ids': [str(x) for x in self._in_flight_nodes],
            'reason': reason,
            'saved_at': timezone.now().isoformat(),
            'execution_id': str(self.execution.id),
        }
        snapshot = make_json_safe(snapshot)
        self.execution.context_snapshot = snapshot
        completed = len(visited_for_snap)
        total = max(len(self.node_map) or 1, 1)
        self.execution.executed_nodes = completed
        self.execution.progress = min(99, int(100 * completed / total))
        self.execution.save(update_fields=[
            'context_snapshot', 'executed_nodes', 'progress',
        ])
        self._last_checkpoint_at = now

        try:
            from ..checkpointing import WorkflowCheckpointManager
            mgr = WorkflowCheckpointManager(self.execution)
            mgr.create_checkpoint(
                current_node_id=str(self.execution.current_node_id)
                if self.execution.current_node_id else None,
                completed_nodes=[str(x) for x in visited_for_snap],
                context_data=snapshot.get('context_data') or {},
                node_results=snapshot.get('node_results') or {},
            )
        except Exception as e:
            logger.debug("Checkpoint history save skipped: %s", e)

        return snapshot

    def _restore_from_snapshot(self, snapshot: Optional[Dict[str, Any]] = None) -> None:
        """Restore visited / results / context from context_snapshot or checkpoint."""
        snap = snapshot if snapshot is not None else (self.execution.get_context_snapshot() or {})
        if not snap.get('visited') and not snap.get('node_results'):
            try:
                from ..checkpointing import load_checkpoint
                cp = load_checkpoint(self.execution)
                if cp:
                    snap = {
                        'visited': [str(x) for x in (cp.completed_node_ids or [])],
                        'node_results': cp.node_results or {},
                        'context_data': cp.context_data or {},
                        'queue_node_ids': [],
                    }
            except Exception as e:
                logger.warning("Failed loading checkpoint for resume: %s", e)

        self._visited = set()
        for x in snap.get('visited') or []:
            try:
                # Match node_map keys (UUID or int)
                key = self._node_id_key(x)
                if key in self.node_map:
                    self._visited.add(key)
                else:
                    # try UUID string match against node_map
                    matched = False
                    for nid in self.node_map:
                        if str(nid) == str(x):
                            self._visited.add(nid)
                            matched = True
                            break
                    if not matched:
                        self._visited.add(key)
            except Exception:
                continue

        self.node_results = self._deserialize_node_results(snap.get('node_results'))
        context_data = snap.get('context_data') or {}
        if isinstance(context_data, dict):
            self.context = ExecutionContext(
                input_data=context_data.get('input_data') or {}
            )
            self.context.variables = context_data.get('variables') or {}
            self.context.node_outputs = context_data.get('node_outputs') or {}
            if context_data.get('metadata'):
                self.context.metadata = context_data.get('metadata') or {}
        self._execution_order = list(snap.get('execution_order') or [])

    def _rebuild_queue_from_snapshot(
        self,
        snapshot: Optional[Dict[str, Any]] = None,
    ) -> Tuple[deque, Set[Any]]:
        """Rebuild ready queue after resume."""
        snap = snapshot if snapshot is not None else (self.execution.get_context_snapshot() or {})
        queue: deque = deque()
        queued_ids: Set[Any] = set()

        saved_queue = snap.get('queue_node_ids') or []
        for nid in saved_queue:
            try:
                nid_key = self._node_id_key(nid)
            except Exception:
                continue
            node = self.node_map.get(nid_key)
            if not node:
                for cand_id, cand in self.node_map.items():
                    if str(cand_id) == str(nid):
                        node = cand
                        nid_key = cand_id
                        break
            if not node or nid_key in self._visited or nid_key in queued_ids:
                continue
            if self._predecessors_ready(node):
                queue.append(node)
                queued_ids.add(nid_key)

        if not queue:
            for node in self.node_map.values():
                if node.id in self._visited or node.id in queued_ids:
                    continue
                if self._predecessors_ready(node):
                    queue.append(node)
                    queued_ids.add(node.id)

        return queue, queued_ids

    def _refresh_control_from_db(self) -> str:
        """
        Poll DB for cooperative pause/cancel requested via API.
        Returns current status. Does not block the Celery worker on pause —
        caller should checkpoint and exit so other workflows can run.
        """
        try:
            self.execution.refresh_from_db(fields=['status'])
        except Exception as e:
            logger.warning("Control poll failed for %s: %s", self.execution.id, e)
            return getattr(self.execution, 'status', 'running')

        status = self.execution.status
        if status == 'cancelled':
            self._cancelled = True
            self._paused = False
            self._pause_event.set()
            self._stop_reason = 'cancelled'
        elif status == 'paused':
            self._paused = True
            self._stop_reason = 'paused'
        return status

    def _should_stop_cooperatively(self) -> bool:
        """True when API requested pause/cancel — exit loop after checkpoint."""
        if self._cancelled:
            return True
        status = self._refresh_control_from_db()
        return status in ('paused', 'cancelled') or self._paused

    def _stop_for_control(
        self,
        queue: deque,
        queued_ids: Set[Any],
        status: str,
        message: Optional[str] = None,
    ) -> WorkflowExecution:
        """Persist checkpoint and leave execution in paused/interrupted/cancelled."""
        snapshot = self._persist_checkpoint(
            queue, queued_ids, reason=status, force=True
        )
        self.execution.refresh_from_db()
        if status == 'cancelled' or self.execution.status == 'cancelled':
            self.execution.status = 'cancelled'
            self.execution.completed_at = timezone.now()
            self.execution.context_snapshot = snapshot
            self.execution.save(update_fields=[
                'status', 'completed_at', 'context_snapshot',
            ])
            self._broadcast_execution_event('execution_cancelled', {
                'execution_id': str(self.execution.id),
                'status': 'cancelled',
            })
        elif status == 'interrupted':
            self.execution.mark_interrupted(
                error_message=message or 'Execution interrupted',
                context_snapshot=snapshot,
            )
            self._broadcast_execution_event('execution_interrupted', {
                'execution_id': str(self.execution.id),
                'status': 'interrupted',
                'message': message,
                'context_snapshot': snapshot,
            })
        else:
            self.execution.status = 'paused'
            self.execution.paused_at = timezone.now()
            self.execution.context_snapshot = snapshot
            self.execution.save(update_fields=[
                'status', 'paused_at', 'context_snapshot',
            ])
            self._broadcast_execution_event('execution_paused', {
                'execution_id': str(self.execution.id),
                'status': 'paused',
                'context_snapshot': snapshot,
            })
        self._stop_reason = status
        return self.execution

    def interrupt(self, message: str = 'Soft time limit / worker interrupt') -> WorkflowExecution:
        """Save checkpoint and mark interrupted (resumable)."""
        return self._stop_for_control(
            deque(), set(self._visited), 'interrupted', message=message
        )

    def execute(self, resume: bool = False) -> WorkflowExecution:
        """Execute the entire workflow (synchronous).

        resume=True restores context_snapshot and continues unfinished nodes.
        Cooperative pause/cancel polls DB between waves and exits the worker
        so other workflow tasks are not blocked.
        """
        if not resume:
            self.execution.status = 'running'
            if not self.execution.started_at:
                self.execution.started_at = timezone.now()
            self.execution.save(update_fields=['status', 'started_at'])
        else:
            self.execution.status = 'running'
            self.execution.paused_at = None
            self.execution.save(update_fields=['status', 'paused_at'])

        self._broadcast_execution_start()
        self._cancelled = False
        self._paused = False
        self._stop_reason = None

        try:
            from .workflow_validation import validate_workflow
            preflight = validate_workflow(self.workflow, self.execution.input_data or {}, self.langchain_service)
            if not preflight['valid']:
                raise ValueError('工作流执行前检查未通过：' + '；'.join(preflight['errors']))
            self.build_graph()

            if resume:
                self._restore_from_snapshot()
                self.context.set_metadata('user_id', self.execution.triggered_by_id)
                self.context.set_metadata('workflow_id', str(self.workflow.id))
                self.context.set_metadata('execution_id', str(self.execution.id))
                queue, queued_ids = self._rebuild_queue_from_snapshot()
                logger.info(
                    "Resuming execution %s: visited=%s queue=%s",
                    self.execution.id, len(self._visited), len(queue),
                )
            else:
                if isinstance(self.execution.input_data, dict):
                    self.context = ExecutionContext(input_data=self.execution.input_data)
                else:
                    self.context = ExecutionContext(input_data={})
                self.context.set_metadata('user_id', self.execution.triggered_by_id)
                self.context.set_metadata('workflow_id', str(self.workflow.id))
                self.context.set_metadata('execution_id', str(self.execution.id))

                start_nodes = self.find_start_nodes()

                if not start_nodes:
                    start_nodes = [
                        node for node in self.workflow.nodes.all()
                        if node.id not in self.reverse_graph or not self.reverse_graph[node.id]
                    ]

                self._visited = set()
                queue = deque(start_nodes)
                queued_ids = {n.id for n in start_nodes}

            while queue and not self._cancelled:
                self._loop_iterations += 1
                self._maybe_heartbeat()
                if self._should_stop_cooperatively():
                    stop_status = 'cancelled' if self._cancelled else 'paused'
                    return self._stop_for_control(queue, queued_ids, stop_status)

                # Periodic progress checkpoint (crash / soft-timeout recovery)
                if self._loop_iterations % 3 == 0:
                    self._persist_checkpoint(queue, queued_ids, reason='progress')

                current_node = queue.popleft()
                queued_ids.discard(current_node.id)

                if current_node.id in self._visited:
                    continue

                # Fan-in: wait until all predecessors finished (e.g. output after 3 burns)
                if not self._predecessors_ready(current_node):
                    continue

                # Batch all currently-ready queued nodes with this one (12 shot chains)
                wave = (
                    self._drain_ready_wave(current_node, queue, queued_ids)
                    if self._parallel_enabled
                    else [current_node]
                )

                # Media chains: only take ONE media node per wave so each completed
                # keyframe can immediately enqueue its video (instead of waiting for
                # all 12 images to finish first).
                media_in_wave = [n for n in wave if n.node_type in self._MEDIA_PARALLEL_TYPES]
                if len(media_in_wave) > 1:
                    keep = media_in_wave[0]
                    defer = [n for n in wave if n.id != keep.id]
                    wave = [keep]
                    for n in reversed(defer):
                        queue.appendleft(n)
                        queued_ids.add(n.id)

                if len(wave) > 1:
                    # Mark visited before launch so successors aren't double-queued mid-flight
                    for n in wave:
                        self._visited.add(n.id)
                        self._in_flight_nodes.add(n.id)
                    try:
                        parallel_results = self._execute_parallel_nodes(wave)
                    finally:
                        for n in wave:
                            self._in_flight_nodes.discard(n.id)
                    completed_nodes, join_nodes = self._handle_parallel_wave_results(
                        wave, parallel_results
                    )
                    ok_nodes = []
                    for n in completed_nodes:
                        res = self.node_results.get(n.id) or {}
                        if res.get('success') or res.get('skipped') or n.node_type in ('start', 'end'):
                            ok_nodes.append(n)
                    self._enqueue_ready_successors(queue, ok_nodes, queued_ids=queued_ids)
                    for join in join_nodes:
                        if join.id in self._visited or join.id in queued_ids:
                            continue
                        if self._predecessors_ready(join):
                            queue.append(join)
                            queued_ids.add(join.id)
                    self._persist_checkpoint(queue, queued_ids, reason='wave')
                    continue

                self._visited.add(current_node.id)
                self._in_flight_nodes.add(current_node.id)

                try:
                    if current_node.node_type in ['start', 'end']:
                        self._complete_boundary_node(current_node)
                    elif current_node.node_type == 'loop':
                        result = self._execute_loop_subgraph(current_node)
                        if not result.get('success') and not result.get('skipped'):
                            raise Exception(result.get('error', 'Loop execution failed'))
                    elif current_node.node_type not in ['start', 'end']:
                        result = self.execute_node(current_node)

                        if not result.get('success') and not result.get('skipped'):
                            if _is_soft_fail_node(current_node):
                                err = result.get('error') or 'Node execution failed'
                                logger.error(
                                    "Soft-fail node %s (%s): %s",
                                    current_node.name, current_node.id, err,
                                )
                                # Keep fan-in unblocked: treat as skipped-success for deps
                                self.node_results[current_node.id] = {
                                    'success': True,
                                    'skipped': True,
                                    'skipped_reason': err,
                                    'output': result.get('output') or {},
                                }
                                self._update_node_status(
                                    current_node.id, 'failed', {'error': err}
                                )
                                # Image soft-fail: still run downstream video as text-to-video.
                                # Video soft-fail: cascade-skip rest of shot chain until join.
                                if current_node.node_type == 'image_generation':
                                    join_nodes = []
                                else:
                                    join_nodes = self._cascade_skip_until_join(current_node)
                                self._enqueue_ready_successors(
                                    queue, [current_node], queued_ids=queued_ids
                                )
                                for join in join_nodes:
                                    if join.id in self._visited or join.id in queued_ids:
                                        continue
                                    if self._predecessors_ready(join):
                                        queue.append(join)
                                        queued_ids.add(join.id)
                                continue
                            raise Exception(result.get('error', 'Node execution failed'))
                finally:
                    self._in_flight_nodes.discard(current_node.id)

                next_nodes = self.get_next_nodes(current_node)
                # After loop subgraph, skip body successors that are already visited;
                # continue from merge/join and other unvisited exits.
                if current_node.node_type == 'loop':
                    _, exit_node = self._discover_loop_body_and_exit(current_node)
                    next_nodes = [n for n in next_nodes if n.id not in self._visited]
                    if exit_node and exit_node.id not in self._visited:
                        if exit_node not in next_nodes:
                            next_nodes.append(exit_node)
                    # Explicitly enqueue loop exit (merge) — graph successors of loop
                    # are body-only, so _enqueue_ready_successors(loop) would miss merge.
                    for nxt in next_nodes:
                        if nxt.id in self._visited or nxt.id in queued_ids:
                            continue
                        if not self._predecessors_ready(nxt):
                            continue
                        queue.append(nxt)
                        queued_ids.add(nxt.id)
                    continue

                # Fan-out: run ready siblings in parallel, then enqueue THEIR successors
                if self._parallel_enabled and len(next_nodes) > 1:
                    parallel_nodes = [
                        n for n in next_nodes
                        if n.id not in self._visited and self._predecessors_ready(n)
                    ]
                    if len(parallel_nodes) > 1:
                        for n in parallel_nodes:
                            self._visited.add(n.id)
                            self._in_flight_nodes.add(n.id)
                        try:
                            parallel_results = self._execute_parallel_nodes(parallel_nodes)
                        finally:
                            for n in parallel_nodes:
                                self._in_flight_nodes.discard(n.id)
                        completed_nodes, join_nodes = self._handle_parallel_wave_results(
                            parallel_nodes, parallel_results
                        )
                        ok_nodes = [
                            n for n in completed_nodes
                            if (self.node_results.get(n.id) or {}).get('success')
                            or (self.node_results.get(n.id) or {}).get('skipped')
                            or n.node_type in ('start', 'end')
                        ]
                        self._enqueue_ready_successors(queue, ok_nodes, queued_ids=queued_ids)
                        for join in join_nodes:
                            if join.id in self._visited or join.id in queued_ids:
                                continue
                            if self._predecessors_ready(join):
                                queue.append(join)
                                queued_ids.add(join.id)
                        continue

                self._enqueue_ready_successors(queue, [current_node], queued_ids=queued_ids)

            if self._cancelled or self.execution.status == 'cancelled':
                return self._stop_for_control(queue, queued_ids, 'cancelled')

            self._finalize_execution('completed')
            return self.execution

        except Exception as e:
            # SoftTimeLimitExceeded may be raised from Celery inside node calls
            from celery.exceptions import SoftTimeLimitExceeded
            if isinstance(e, SoftTimeLimitExceeded):
                logger.warning("SoftTimeLimitExceeded on execution %s", self.execution.id)
                try:
                    return self._stop_for_control(
                        deque(), set(), 'interrupted',
                        message='Execution soft time limit exceeded — resumable from checkpoint',
                    )
                except Exception:
                    pass
            logger.exception(f"Workflow execution failed: {e}")
            try:
                self._persist_checkpoint(reason='failure', force=True)
            except Exception:
                pass
            self._finalize_execution('failed', error_message=str(e))
            return self.execution

    def pause(self) -> None:
        """Local pause request (prefer API → DB status=paused for cross-process)."""
        self._paused = True
        self._stop_reason = 'paused'
        self.execution.status = 'paused'
        self.execution.paused_at = timezone.now()
        self.execution.context_snapshot = self._build_context_snapshot(reason='pause')
        self.execution.save(update_fields=['status', 'paused_at', 'context_snapshot'])
        self._broadcast_execution_event('execution_paused', {
            'execution_id': self.execution.id,
            'context_snapshot': self.execution.context_snapshot
        })

    def resume(self) -> WorkflowExecution:
        """Resume a paused/interrupted workflow execution in-process."""
        if self.execution.status not in ('paused', 'interrupted', 'running'):
            raise ValueError("Execution is not resumable")

        return self.execute(resume=True)

    def cancel(self) -> None:
        """Cancel the workflow execution (cooperative)."""
        self._cancelled = True
        self._paused = False
        self._stop_reason = 'cancelled'
        self._pause_event.set()

    def _finalize_execution(self, status: str, error_message: str = None) -> None:
        """Finalize workflow execution."""
        # Never clobber cooperative control states
        try:
            self.execution.refresh_from_db(fields=['status'])
            if self.execution.status in ('paused', 'interrupted', 'cancelled') and status == 'completed':
                return
        except Exception:
            pass

        self.execution.status = status
        self.execution.executed_nodes = len(self._visited)
        if status == 'completed':
            self.execution.progress = 100
        self.execution.output_data = self.context.to_dict()
        self.execution.completed_at = timezone.now()
        if error_message:
            self.execution.error_message = error_message
        if self.execution.started_at:
            self.execution.duration_ms = int(
                (self.execution.completed_at - self.execution.started_at).total_seconds() * 1000
            )
        # Persist final snapshot so retry_failed / resume can keep successes
        try:
            self.execution.context_snapshot = self._build_context_snapshot(reason=status)
        except Exception as snap_err:
            logger.debug('Final snapshot skipped: %s', snap_err)
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
            from .workflow_validation import validate_workflow
            preflight = validate_workflow(self.workflow, self.execution.input_data or {}, self.langchain_service)
            if not preflight['valid']:
                raise ValueError('工作流执行前检查未通过：' + '；'.join(preflight['errors']))
            self.build_graph()

            if isinstance(self.execution.input_data, dict):
                self.context = ExecutionContext(input_data=self.execution.input_data)
            else:
                self.context = ExecutionContext(input_data={})
            self.context.set_metadata('user_id', self.execution.triggered_by_id)
            self.context.set_metadata('workflow_id', str(self.workflow.id))
            self.context.set_metadata('execution_id', str(self.execution.id))

            start_nodes = self.find_start_nodes()

            if not start_nodes:
                start_nodes = [
                    node for node in self.workflow.nodes.all()
                    if node.id not in self.reverse_graph or not self.reverse_graph[node.id]
                ]

            self._visited: Set[int] = set()
            queue = deque(start_nodes)
            queued_ids: Set[Any] = {n.id for n in start_nodes}

            while queue and not self._cancelled:
                if self._should_stop_cooperatively():
                    stop_status = 'cancelled' if self._cancelled else 'paused'
                    self._stop_for_control(queue, queued_ids, stop_status)
                    yield {
                        'type': 'execution_paused' if stop_status == 'paused' else 'execution_cancelled',
                        'execution_id': self.execution.id,
                        'status': stop_status,
                        'context_snapshot': self.execution.context_snapshot,
                    }
                    return

                current_node = queue.popleft()
                queued_ids.discard(current_node.id)

                if current_node.id in self._visited:
                    continue

                if not self._predecessors_ready(current_node):
                    continue

                self._visited.add(current_node.id)

                if current_node.node_type in ['start', 'end']:
                    self._complete_boundary_node(current_node)
                    yield {
                        'type': 'node_complete',
                        'node_id': current_node.id,
                        'node_name': current_node.name,
                        'status': 'completed',
                        'output': {},
                    }
                elif current_node.node_type == 'loop':
                    yield {
                        'type': 'node_start',
                        'node_id': current_node.id,
                        'node_name': current_node.name,
                        'node_type': current_node.node_type
                    }
                    try:
                        result = self._execute_loop_subgraph(current_node)
                    except Exception as e:
                        result = {'success': False, 'error': str(e)}
                    yield {
                        'type': 'node_complete',
                        'node_id': current_node.id,
                        'node_name': current_node.name,
                        'status': 'completed' if result.get('success') else 'failed',
                        'output': result.get('output'),
                        'error': result.get('error'),
                    }
                    if not result.get('success') and not result.get('skipped'):
                        raise Exception(result.get('error', 'Loop execution failed'))
                elif current_node.node_type not in ['start', 'end']:
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

                if current_node.node_type == 'loop':
                    _, exit_node = self._discover_loop_body_and_exit(current_node)
                    next_nodes = [
                        n for n in self.get_next_nodes(current_node)
                        if n.id not in self._visited
                    ]
                    if exit_node and exit_node.id not in self._visited and exit_node not in next_nodes:
                        next_nodes.append(exit_node)
                    for nxt in next_nodes:
                        if nxt.id in self._visited or nxt.id in queued_ids:
                            continue
                        if not self._predecessors_ready(nxt):
                            continue
                        queue.append(nxt)
                        queued_ids.add(nxt.id)
                else:
                    self._enqueue_ready_successors(queue, [current_node], queued_ids=queued_ids)

            self._finalize_execution('completed')

            yield {
                'type': 'execution_complete',
                'execution_id': self.execution.id,
                'status': 'completed',
                'output_data': self.context.to_dict()
            }

        except Exception as e:
            logger.exception(f"Workflow execution failed: {e}")
            self._finalize_execution('failed', error_message=str(e))

            yield {
                'type': 'execution_error',
                'execution_id': self.execution.id,
                'status': 'failed',
                'error': str(e)
            }

    def _resolve_node_label(self, node: Optional[Node]) -> str:
        """Human-readable node label for execution snapshots."""
        if not node:
            return ''
        config = node.config if isinstance(node.config, dict) else {}
        label = config.get('label')
        if isinstance(label, str) and label.strip():
            return label.strip()
        if node.name and str(node.name).strip():
            return str(node.name).strip()
        display = node.get_node_type_display()
        return display if display else str(node.node_type)

    def _update_node_status(
        self,
        node_id: int,
        status: str,
        output: Any = None,
        error: str = None,
        node: Optional[Node] = None,
    ) -> None:
        """Update node status in execution record."""
        node_status = self.execution.node_status or {}
        existing = node_status.get(str(node_id), {})
        if not isinstance(existing, dict):
            existing = {'status': existing} if existing else {}

        safe_output = self._json_safe(output) if output is not None else existing.get('output')
        resolved_node = node or self.node_map.get(node_id)

        entry = {
            'status': status,
            'output': safe_output,
            'error': error if error is not None else existing.get('error'),
            'updated_at': timezone.now().isoformat(),
        }

        if resolved_node:
            entry['node_name'] = self._resolve_node_label(resolved_node)
            entry['node_type'] = resolved_node.node_type
            entry['node_type_display'] = resolved_node.get_node_type_display()
        else:
            for key in ('node_name', 'node_type', 'node_type_display'):
                if existing.get(key) is not None:
                    entry[key] = existing[key]

        node_status[str(node_id)] = entry
        self.execution.node_status = node_status
        self.execution.save(update_fields=['node_status'])

    @staticmethod
    def _json_safe(value: Any) -> Any:
        """Strip circular refs / non-JSON values before persisting node output."""
        try:
            return json.loads(json.dumps(value, default=str, ensure_ascii=False))
        except (TypeError, ValueError):
            return str(value)

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
