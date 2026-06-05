"""
Parallel Execution Service for Workflows.

Provides parallel execution capabilities for workflow branches using:
- asyncio for concurrent execution
- Celery tasks for distributed execution
- Redis for result aggregation
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict

from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class BranchResult:
    """Result from a parallel branch execution."""
    branch_id: str
    node_results: Dict[str, Any]
    status: str  # success, error, timeout
    duration_ms: float
    error: Optional[str] = None


@dataclass
class ParallelExecutionConfig:
    """Configuration for parallel execution."""
    max_workers: int = 4
    timeout_seconds: int = 300
    fail_fast: bool = False  # Stop if any branch fails
    aggregate_results: bool = True  # Merge results from branches


class BranchExecutor:
    """
    Executor for a single branch of nodes.

    Executes nodes sequentially within a branch.
    """

    def __init__(self, branch_id: str, node_ids: List[str]):
        self.branch_id = branch_id
        self.node_ids = node_ids
        self.results: Dict[str, Any] = {}
        self.context: Dict[str, Any] = {}

    async def execute(
        self,
        workflow_nodes: Dict[str, Dict],
        langchain_service,
        timeout: int = 300
    ) -> BranchResult:
        """
        Execute all nodes in the branch.

        Args:
            workflow_nodes: Map of node_id -> node definition
            langchain_service: Service for executing nodes
            timeout: Timeout for entire branch

        Returns:
            BranchResult with execution outcomes
        """
        start_time = time.time()
        status = "success"

        try:
            for node_id in self.node_ids:
                node = workflow_nodes.get(node_id)
                if not node:
                    logger.warning(f"Node {node_id} not found in branch {self.branch_id}")
                    continue

                # Execute node
                result = await asyncio.wait_for(
                    self._execute_node(node, langchain_service),
                    timeout=timeout
                )

                self.results[node_id] = result
                self.context[f"node_{node_id}_output"] = result

                # Check for errors
                if isinstance(result, dict) and not result.get('success', True):
                    status = "error"
                    break

        except asyncio.TimeoutError:
            status = "timeout"
            logger.warning(f"Branch {self.branch_id} timed out after {timeout}s")

        except Exception as e:
            status = "error"
            logger.exception(f"Branch {self.branch_id} execution error: {e}")

        duration_ms = (time.time() - start_time) * 1000

        return BranchResult(
            branch_id=self.branch_id,
            node_results=self.results,
            status=status,
            duration_ms=duration_ms,
            error=None if status == "success" else str(e) if status == "error" else "Timeout"
        )

    async def _execute_node(self, node: Dict, langchain_service) -> Any:
        """Execute a single node."""
        # Import here to avoid circular imports
        from .services.langchain_service import langchain_service as lc_service

        return await lc_service.execute_node_async(
            node_type=node.get('type', 'llm'),
            config=node.get('config', {}),
            context=self.context
        )


class ParallelExecutionEngine:
    """
    Engine for executing parallel branches in a workflow.

    Finds parallel branches in the workflow graph and executes
    them concurrently.
    """

    def __init__(
        self,
        workflow_definition: Dict[str, Any],
        config: Optional[ParallelExecutionConfig] = None
    ):
        self.workflow_definition = workflow_definition
        self.nodes = workflow_definition.get('nodes', [])
        self.edges = workflow_definition.get('edges', [])
        self.config = config or ParallelExecutionConfig()

        # Build lookup maps
        self.node_map = {n['id']: n for n in self.nodes}
        self.adjacency = self._build_adjacency()
        self.reverse_adjacency = self._build_reverse_adjacency()

    def _build_adjacency(self) -> Dict[str, List[str]]:
        """Build forward adjacency list."""
        adj = defaultdict(list)
        for edge in self.edges:
            adj[edge['source']].append(edge['target'])
        return dict(adj)

    def _build_reverse_adjacency(self) -> Dict[str, List[str]]:
        """Build reverse adjacency list."""
        rev = defaultdict(list)
        for edge in self.edges:
            rev[edge['target']].append(edge['source'])
        return dict(rev)

    def find_parallel_branches(
        self,
        split_node_id: str
    ) -> List[List[str]]:
        """
        Find all parallel branches starting from a split node.

        A split node is one that has multiple outgoing edges.

        Args:
            split_node_id: The node where branches split

        Returns:
            List of branch paths, each path is a list of node IDs
        """
        if not self.adjacency.get(split_node_id):
            return []

        branches = []

        def find_paths(
            current: str,
            visited: set,
            path: List[str]
        ) -> None:
            """Recursively find all paths from current node."""
            if current in visited:
                return

            path.append(current)

            # Check if this is an end node or merge point
            next_nodes = self.adjacency.get(current, [])

            if not next_nodes:
                # End of path
                branches.append(path.copy())
            elif len(next_nodes) > 1:
                # Another split point - branch from here
                for next_node in next_nodes:
                    find_paths(next_node, visited.copy(), path.copy())
            else:
                # Single path continuation
                find_paths(next_nodes[0], visited, path)

            path.pop()

        # Start from each outgoing edge
        for next_node in self.adjacency.get(split_node_id, []):
            find_paths(next_node, {split_node_id}, [])

        return branches

    def find_merge_points(
        self,
        branches: List[List[str]]
    ) -> List[str]:
        """
        Find nodes where parallel branches merge back.

        Args:
            branches: List of branch paths

        Returns:
            List of merge point node IDs
        """
        if not branches:
            return []

        # Find nodes that appear in multiple branches (merge points)
        node_count: Dict[str, int] = defaultdict(int)
        for branch in branches:
            for node_id in branch:
                node_count[node_id] += 1

        # A merge point is where multiple branches converge
        # (node appears in multiple branches but isn't the split point)
        merge_points = [
            node_id for node_id, count in node_count.items()
            if count > 1
        ]

        return merge_points

    async def execute_parallel(
        self,
        split_node_id: str,
        initial_context: Dict[str, Any],
        langchain_service
    ) -> Dict[str, Any]:
        """
        Execute parallel branches starting from split_node_id.

        Args:
            split_node_id: The node where execution splits
            initial_context: Context data before split
            langchain_service: Service for executing nodes

        Returns:
            Dict with branch results and aggregated output
        """
        # Find branches
        branches = self.find_parallel_branches(split_node_id)

        if len(branches) <= 1:
            # No parallel execution needed
            return {
                'parallel': False,
                'branches': [],
                'results': {},
                'aggregated': initial_context
            }

        logger.info(f"Executing {len(branches)} parallel branches from {split_node_id}")

        # Execute branches in parallel
        executors = [
            BranchExecutor(f"branch_{i}", branch)
            for i, branch in enumerate(branches)
        ]

        # Run with concurrency limit
        semaphore = asyncio.Semaphore(self.config.max_workers)

        async def execute_with_limit(executor: BranchExecutor) -> BranchResult:
            async with semaphore:
                return await executor.execute(
                    self.node_map,
                    langchain_service,
                    timeout=self.config.timeout_seconds
                )

        # Execute all branches
        branch_results = await asyncio.gather(
            *[execute_with_limit(ex) for ex in executors],
            return_exceptions=True
        )

        # Process results
        results = {}
        success_count = 0
        error_results = []

        for i, result in enumerate(branch_results):
            if isinstance(result, Exception):
                results[f"branch_{i}"] = BranchResult(
                    branch_id=f"branch_{i}",
                    node_results={},
                    status="error",
                    duration_ms=0,
                    error=str(result)
                )
                error_results.append(result)
            else:
                results[result.branch_id] = result
                if result.status == "success":
                    success_count += 1

        # Aggregate results
        aggregated = self._aggregate_results(results, initial_context) if self.config.aggregate_results else {}

        return {
            'parallel': True,
            'branch_count': len(branches),
            'success_count': success_count,
            'failed': len(branches) - success_count,
            'results': results,
            'aggregated': aggregated,
            'merge_points': self.find_merge_points(branches),
            'fail_fast_triggered': self.config.fail_fast and error_results
        }

    def _aggregate_results(
        self,
        results: Dict[str, BranchResult],
        initial_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Aggregate results from all branches."""
        aggregated = initial_context.copy()

        # Merge all branch outputs
        for branch_id, result in results.items():
            if result.status == "success":
                aggregated[f"branch_{branch_id}_output"] = result.node_results

                # Also flatten top-level outputs
                for node_id, node_result in result.node_results.items():
                    aggregated[f"node_{node_id}_output"] = node_result

        return aggregated


class ParallelExecutionManager:
    """
    High-level manager for parallel execution in workflows.

    Integrates with Django models and provides Celery task support.
    """

    @staticmethod
    def should_parallelize(workflow_definition: Dict[str, Any]) -> bool:
        """
        Determine if workflow should use parallel execution.

        Args:
            workflow_definition: Workflow nodes and edges

        Returns:
            True if workflow has parallelizable branches
        """
        edges = workflow_definition.get('edges', [])
        nodes = workflow_definition.get('nodes', [])

        # Count outgoing edges per node
        out_degree: Dict[str, int] = defaultdict(int)
        for edge in edges:
            out_degree[edge['source']] += 1

        # Parallel if any node has >1 outgoing edges
        return any(count > 1 for count in out_degree.values())

    @staticmethod
    def find_parallelization_points(
        workflow_definition: Dict[str, Any]
    ) -> List[str]:
        """
        Find nodes where parallel execution should occur.

        Args:
            workflow_definition: Workflow nodes and edges

        Returns:
            List of node IDs suitable for parallel execution
        """
        edges = workflow_definition.get('edges', [])

        # Find nodes with multiple outgoing edges
        out_degree: Dict[str, int] = defaultdict(int)
        for edge in edges:
            out_degree[edge['source']] += 1

        return [
            node_id for node_id, degree in out_degree.items()
            if degree > 1
        ]


# Synchronous wrapper for Celery tasks
def execute_parallel_branches_sync(
    workflow_definition: Dict[str, Any],
    split_node_id: str,
    initial_context: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Synchronous wrapper for parallel execution.

    For use in Celery tasks.
    """
    parallel_config = ParallelExecutionConfig(
        max_workers=config.get('max_workers', 4) if config else 4,
        timeout_seconds=config.get('timeout_seconds', 300) if config else 300,
        fail_fast=config.get('fail_fast', False) if config else False,
        aggregate_results=config.get('aggregate_results', True) if config else True
    )

    engine = ParallelExecutionEngine(workflow_definition, parallel_config)

    # Get langchain service
    from .services.langchain_service import langchain_service

    return asyncio.run(engine.execute_parallel(
        split_node_id,
        initial_context,
        langchain_service
    ))
