"""
Tests for ExecutionContext.
"""

import pytest
from datetime import datetime
from workflows.services.context import ExecutionContext


class TestExecutionContext:
    """Test cases for ExecutionContext."""

    def test_init(self):
        """Test initialization."""
        ctx = ExecutionContext()
        assert ctx.input_data == {}
        assert ctx.variables == {}
        assert ctx.node_outputs == {}
        assert ctx.metadata == {}
        assert ctx.started_at is not None
        assert ctx.ended_at is None

    def test_init_with_data(self):
        """Test initialization with data."""
        input_data = {'name': 'test'}
        ctx = ExecutionContext(input_data=input_data)
        assert ctx.input_data == input_data

    def test_set_and_get_var(self):
        """Test setting and getting variables."""
        ctx = ExecutionContext()
        ctx.set_var('name', 'Alice')
        assert ctx.get_var('name') == 'Alice'
        assert ctx.get_var('nonexistent', 'default') == 'default'

    def test_get_var_priority(self):
        """Test variable priority: variables > input_data."""
        ctx = ExecutionContext(
            input_data={'name': 'input_name'},
            variables={'name': 'var_name'}
        )
        assert ctx.get_var('name') == 'var_name'

    def test_get_var_from_input_data(self):
        """Test getting variable from input_data when not in variables."""
        ctx = ExecutionContext(input_data={'name': 'input_name'})
        assert ctx.get_var('name') == 'input_name'

    def test_has_var(self):
        """Test has_var method."""
        ctx = ExecutionContext()
        ctx.set_var('name', 'Alice')
        assert ctx.has_var('name') is True
        assert ctx.has_var('nonexistent') is False

    def test_set_and_get_node_output(self):
        """Test setting and getting node outputs."""
        ctx = ExecutionContext()
        ctx.set_node_output('node1', {'result': 'success'})
        assert ctx.get_node_output('node1') == {'result': 'success'}
        assert ctx.get_node_output('nonexistent') is None
        assert ctx.get_node_output('nonexistent', 'default') == 'default'

    def test_interpolate_simple(self):
        """Test simple variable interpolation."""
        ctx = ExecutionContext()
        ctx.set_var('name', 'Alice')
        result = ctx.interpolate('Hello {{name}}!')
        assert result == 'Hello Alice!'

    def test_interpolate_multiple(self):
        """Test multiple variable interpolation."""
        ctx = ExecutionContext()
        ctx.set_var('first', 'Hello')
        ctx.set_var('second', 'World')
        result = ctx.interpolate('{{first}} {{second}}!')
        assert result == 'Hello World!'

    def test_interpolate_missing_var(self):
        """Test interpolation with missing variable."""
        ctx = ExecutionContext()
        result = ctx.interpolate('Hello {{name}}!')
        assert result == 'Hello {{name}}!'

    def test_interpolate_nested(self):
        """Test nested value interpolation."""
        ctx = ExecutionContext()
        ctx.set_var('user.name', 'Alice')
        ctx.set_var('user', {'name': 'Alice'})
        result = ctx.interpolate('Hello {{user.name}}!')
        assert result == 'Hello Alice!'

    def test_interpolate_dict(self):
        """Test dictionary interpolation."""
        ctx = ExecutionContext()
        ctx.set_var('name', 'Alice')
        data = {
            'greeting': 'Hello {{name}}!',
            'template': '{{name}} is here'
        }
        result = ctx.interpolate_dict(data)
        assert result['greeting'] == 'Hello Alice!'
        assert result['template'] == 'Alice is here'

    def test_interpolate_list(self):
        """Test list interpolation."""
        ctx = ExecutionContext()
        ctx.set_var('item', 'apple')
        data = ['I like {{item}}', 'Another {{item}}']
        result = ctx.interpolate_dict({'list': data})
        assert result['list'] == ['I like apple', 'Another apple']

    def test_metadata(self):
        """Test metadata methods."""
        ctx = ExecutionContext()
        ctx.set_metadata('key1', 'value1')
        assert ctx.get_metadata('key1') == 'value1'
        assert ctx.get_metadata('nonexistent', 'default') == 'default'

    def test_mark_end(self):
        """Test marking execution end."""
        ctx = ExecutionContext()
        assert ctx.ended_at is None
        ctx.mark_end()
        assert ctx.ended_at is not None

    def test_duration(self):
        """Test duration calculation."""
        ctx = ExecutionContext()
        assert ctx.duration is None
        ctx.mark_end()
        assert ctx.duration is not None
        assert ctx.duration >= 0

    def test_to_dict(self):
        """Test converting to dictionary."""
        ctx = ExecutionContext(input_data={'input': 'value'})
        ctx.set_var('var1', 'value1')
        ctx.set_metadata('meta1', 'meta_value')
        ctx.mark_end()
        
        result = ctx.to_dict()
        assert 'input_data' in result
        assert 'variables' in result
        assert 'metadata' in result
        assert 'started_at' in result
        assert 'ended_at' in result
        assert 'duration' in result

    def test_get_all_outputs(self):
        """Test getting all outputs."""
        ctx = ExecutionContext()
        ctx.set_var('var1', 'value1')
        result = ctx.get_all_outputs()
        assert 'var1' in result
        assert result['var1'] == 'value1'

    def test_clone(self):
        """Test cloning context."""
        ctx = ExecutionContext(input_data={'input': 'value'})
        ctx.set_var('var1', 'value1')
        
        cloned = ctx.clone()
        assert cloned.input_data == ctx.input_data
        assert cloned.variables == ctx.variables
        assert cloned.variables is not ctx.variables  # Different object

    def test_auto_extract_variables_from_node_output(self):
        """Test that setting node output auto-extracts variables."""
        ctx = ExecutionContext()
        ctx.set_node_output('node1', {'extracted_var': 'extracted_value'})
        
        # Variable should be extracted
        assert ctx.get_var('extracted_var') == 'extracted_value'
        
        # Original output should still be stored
        assert ctx.get_node_output('node1') == {'extracted_var': 'extracted_value'}
