"""
Tests for WorkflowExecutor.
"""

import pytest
from unittest.mock import MagicMock, patch
from workflows.services.workflow_executor import WorkflowExecutor
from workflows.services.context import ExecutionContext


class TestWorkflowExecutor:
    """Test cases for WorkflowExecutor."""

    @pytest.fixture
    def mock_workflow(self):
        """Create a mock workflow."""
        workflow = MagicMock()
        workflow.id = 1
        workflow.name = 'Test Workflow'
        workflow.edges.all.return_value = []
        workflow.nodes.all.return_value = []
        return workflow

    @pytest.fixture
    def mock_execution(self):
        """Create a mock execution."""
        execution = MagicMock()
        execution.id = 1
        execution.workflow_id = 1
        execution.status = 'pending'
        execution.input_data = {'test': 'value'}
        return execution

    def test_init(self, mock_workflow, mock_execution):
        """Test executor initialization."""
        executor = WorkflowExecutor(mock_workflow, mock_execution)
        
        assert executor.workflow == mock_workflow
        assert executor.execution == mock_execution
        assert isinstance(executor.context, ExecutionContext)
        assert executor.node_results == {}
        assert executor.graph == {}
        assert executor.node_map == {}

    def test_init_with_input_data(self, mock_workflow, mock_execution):
        """Test executor initialization with input data."""
        mock_execution.input_data = {'name': 'Alice'}
        executor = WorkflowExecutor(mock_workflow, mock_execution)
        
        assert executor.context.input_data == {'name': 'Alice'}

    def test_build_graph_empty(self, mock_workflow, mock_execution):
        """Test building graph with no edges."""
        executor = WorkflowExecutor(mock_workflow, mock_execution)
        executor.build_graph()
        
        assert executor.graph == {}
        assert executor.reverse_graph == {}

    def test_find_start_nodes_empty(self, mock_workflow, mock_execution):
        """Test finding start nodes with no nodes."""
        mock_workflow.nodes.filter.return_value = []
        executor = WorkflowExecutor(mock_workflow, mock_execution)
        executor.build_graph()
        
        start_nodes = executor.find_start_nodes()
        assert start_nodes == []

    def test_find_end_nodes_empty(self, mock_workflow, mock_execution):
        """Test finding end nodes with no nodes."""
        mock_workflow.nodes.filter.return_value = []
        executor = WorkflowExecutor(mock_workflow, mock_execution)
        executor.build_graph()
        
        end_nodes = executor.find_end_nodes()
        assert end_nodes == []

    def test_get_next_nodes(self, mock_workflow, mock_execution):
        """Test getting next nodes."""
        mock_node = MagicMock()
        mock_node.id = 1
        
        mock_workflow.nodes.all.return_value = [mock_node]
        mock_workflow.edges.all.return_value = []
        
        executor = WorkflowExecutor(mock_workflow, mock_execution)
        executor.build_graph()
        
        next_nodes = executor.get_next_nodes(mock_node)
        assert next_nodes == []


class TestWorkflowExecutorIntegration:
    """Integration tests for WorkflowExecutor."""

    @pytest.fixture
    def mock_workflow_with_nodes(self):
        """Create a mock workflow with nodes and edges."""
        # Create mock nodes
        start_node = MagicMock()
        start_node.id = 1
        start_node.node_type = 'start'
        start_node.name = 'Start'
        start_node.config = {}

        llm_node = MagicMock()
        llm_node.id = 2
        llm_node.node_type = 'llm'
        llm_node.name = 'LLM'
        llm_node.config = {'model': 'gpt-3.5-turbo'}

        end_node = MagicMock()
        end_node.id = 3
        end_node.node_type = 'end'
        end_node.name = 'End'
        end_node.config = {}

        # Create mock edges
        edge1 = MagicMock()
        edge1.source_node_id = 1
        edge1.target_node_id = 2
        edge1.source_node = start_node
        edge1.target_node = llm_node

        edge2 = MagicMock()
        edge2.source_node_id = 2
        edge2.target_node_id = 3
        edge2.source_node = llm_node
        edge2.target_node = end_node

        # Setup workflow mock
        workflow = MagicMock()
        workflow.id = 1
        workflow.name = 'Test Workflow'
        workflow.nodes.all.return_value = [start_node, llm_node, end_node]
        workflow.edges.all.return_value = [edge1, edge2]

        return workflow, start_node, llm_node, end_node

    def test_build_graph_with_edges(self, mock_workflow_with_nodes):
        """Test building graph with edges."""
        workflow, start_node, llm_node, end_node = mock_workflow_with_nodes
        
        execution = MagicMock()
        execution.id = 1
        execution.workflow_id = 1
        execution.status = 'pending'
        execution.input_data = {}
        
        executor = WorkflowExecutor(workflow, execution)
        executor.build_graph()
        
        # Check forward graph
        assert 1 in executor.graph
        assert 2 in executor.graph[1]
        assert 3 in executor.graph[2]
        
        # Check reverse graph
        assert 2 in executor.reverse_graph
        assert 1 in executor.reverse_graph[2]
        assert 3 in executor.reverse_graph[2]

    def test_find_start_nodes(self, mock_workflow_with_nodes):
        """Test finding start nodes."""
        workflow, start_node, llm_node, end_node = mock_workflow_with_nodes
        
        # Setup filter to return start node
        workflow.nodes.filter.return_value = [start_node]
        
        execution = MagicMock()
        execution.id = 1
        execution.workflow_id = 1
        execution.status = 'pending'
        execution.input_data = {}
        
        executor = WorkflowExecutor(workflow, execution)
        executor.build_graph()
        
        start_nodes = executor.find_start_nodes()
        assert len(start_nodes) == 1
        assert start_nodes[0].node_type == 'start'

    def test_get_next_nodes(self, mock_workflow_with_nodes):
        """Test getting next nodes from a node."""
        workflow, start_node, llm_node, end_node = mock_workflow_with_nodes
        
        execution = MagicMock()
        execution.id = 1
        execution.workflow_id = 1
        execution.status = 'pending'
        execution.input_data = {}
        
        executor = WorkflowExecutor(workflow, execution)
        executor.build_graph()
        
        # Get next nodes from start
        next_nodes = executor.get_next_nodes(start_node)
        assert len(next_nodes) == 1
        assert next_nodes[0].id == 2


class TestWorkflowExecutorErrorHandling:
    """Tests for WorkflowExecutor error handling."""

    @pytest.fixture
    def mock_workflow_with_error_node(self):
        """Create a mock workflow with error handling configured."""
        node = MagicMock()
        node.id = 1
        node.node_type = 'llm'
        node.name = 'LLM Node'
        node.config = {}
        node.error_handling = 'skip'
        node.max_retries = 3
        node.retry_delay = 1.0
        node.fallback_value = {'result': 'fallback'}

        workflow = MagicMock()
        workflow.id = 1
        workflow.name = 'Test Workflow'
        workflow.nodes.all.return_value = [node]
        workflow.edges.all.return_value = []

        return workflow, node

    def test_execute_node_with_skip_strategy(self, mock_workflow_with_error_node):
        """Test executing node with skip error handling."""
        workflow, node = mock_workflow_with_error_node
        
        execution = MagicMock()
        execution.id = 1
        execution.workflow_id = 1
        execution.status = 'pending'
        execution.input_data = {}
        
        executor = WorkflowExecutor(workflow, execution)
        executor.build_graph()
        
        # Mock the langchain service to raise an error
        with patch('workflows.services.workflow_executor.langchain_service') as mock_service:
            mock_service.execute_node.side_effect = Exception("API Error")
            
            # This should not raise, it should return skipped result
            # because error_handling is 'skip'
            node.error_handling = 'skip'
            result = executor.execute_node(node)
            
            assert result.get('skipped') is True

    def test_execute_node_with_fallback_strategy(self, mock_workflow_with_error_node):
        """Test executing node with fallback error handling."""
        workflow, node = mock_workflow_with_error_node
        
        execution = MagicMock()
        execution.id = 1
        execution.workflow_id = 1
        execution.status = 'pending'
        execution.input_data = {}
        
        executor = WorkflowExecutor(workflow, execution)
        executor.build_graph()
        
        # Mock the langchain service to return failure
        with patch('workflows.services.workflow_executor.langchain_service') as mock_service:
            mock_service.execute_node.return_value = {'success': False, 'error': 'API Error'}
            
            node.error_handling = 'fallback'
            node.fallback_value = {'result': 'fallback'}
            
            result = executor.execute_node(node)
            
            assert result.get('used_fallback') is True
            assert result.get('output') == {'result': 'fallback'}

    def test_execute_node_with_stop_strategy(self, mock_workflow_with_error_node):
        """Test executing node with stop error handling raises error."""
        workflow, node = mock_workflow_with_error_node
        
        execution = MagicMock()
        execution.id = 1
        execution.workflow_id = 1
        execution.status = 'pending'
        execution.input_data = {}
        
        executor = WorkflowExecutor(workflow, execution)
        executor.build_graph()
        
        # Mock the langchain service to return failure
        with patch('workflows.services.workflow_executor.langchain_service') as mock_service:
            mock_service.execute_node.return_value = {'success': False, 'error': 'API Error'}
            
            node.error_handling = 'stop'
            
            with pytest.raises(Exception):
                executor.execute_node(node)
