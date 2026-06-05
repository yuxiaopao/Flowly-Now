"""
Pydantic models for structured workflow generation.
Used by LangChain Output Parser for type-safe JSON parsing.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class NodeConfig(BaseModel):
    """Configuration for workflow nodes."""
    model_config = {"extra": "allow"}  # Allow additional fields


class WorkflowNode(BaseModel):
    """A single node in the workflow graph."""
    id: str = Field(description="Unique node ID (e.g., node_1, node_2)")
    type: str = Field(
        description="Node type: start/end/input/llm/condition/tool/code/output"
    )
    name: str = Field(description="Display name for the node")
    position: Dict[str, int] = Field(
        description="Canvas coordinates {x: number, y: number}"
    )
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Node-specific configuration"
    )

    @field_validator('position')
    @classmethod
    def validate_position(cls, v: Dict[str, int]) -> Dict[str, int]:
        if 'x' not in v or 'y' not in v:
            raise ValueError("Position must have 'x' and 'y' coordinates")
        return v

    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        valid_types = {
            'start', 'end', 'input', 'llm', 'condition',
            'tool', 'code', 'output', 'http', 'email', 'webhook', 'prompt'
        }
        # Allow unknown types but warn
        return v


class WorkflowEdge(BaseModel):
    """A connection between two nodes."""
    id: str = Field(description="Unique edge ID (e.g., edge_1, edge_2)")
    source: str = Field(description="Source node ID")
    target: str = Field(description="Target node ID")
    label: str = Field(
        default="",
        description="Edge label (e.g., condition branch name)"
    )


class WorkflowSchema(BaseModel):
    """Complete workflow structure."""
    name: str = Field(description="Workflow name (concise and meaningful)")
    description: str = Field(description="Workflow description (1-2 sentences)")
    nodes: List[WorkflowNode] = Field(
        description="List of workflow nodes"
    )
    edges: List[WorkflowEdge] = Field(
        description="List of connections between nodes"
    )

    @field_validator('nodes')
    @classmethod
    def validate_nodes(cls, v: List[WorkflowNode]) -> List[WorkflowNode]:
        if not v:
            raise ValueError("Workflow must have at least one node")
        return v

    @field_validator('edges')
    @classmethod
    def validate_edges(cls, v: List[WorkflowEdge], info) -> List[WorkflowEdge]:
        # Validate that edge references exist in nodes
        if 'nodes' in info.data:
            node_ids = {node.id for node in info.data['nodes']}
            for edge in v:
                if edge.source not in node_ids:
                    raise ValueError(
                        f"Edge '{edge.id}' references non-existent source node '{edge.source}'"
                    )
                if edge.target not in node_ids:
                    raise ValueError(
                        f"Edge '{edge.id}' references non-existent target node '{edge.target}'"
                    )
        return v


class WorkflowModificationSchema(BaseModel):
    """Schema for workflow modification responses (same as workflow)."""
    name: Optional[str] = Field(
        default=None,
        description="Updated workflow name"
    )
    description: Optional[str] = Field(
        default=None,
        description="Updated workflow description"
    )
    nodes: Optional[List[WorkflowNode]] = Field(
        default=None,
        description="Updated list of workflow nodes"
    )
    edges: Optional[List[WorkflowEdge]] = Field(
        default=None,
        description="Updated list of connections"
    )


class ValidationResult(BaseModel):
    """Validation result for workflow."""
    valid: bool = Field(description="Whether the workflow is valid")
    errors: List[str] = Field(
        default_factory=list,
        description="List of validation errors"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="List of validation warnings"
    )


class WorkflowWithValidation(BaseModel):
    """Workflow with validation result."""
    name: str
    description: str
    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]
    validation: ValidationResult = Field(default_factory=ValidationResult)
    estimated_cost: Optional[float] = Field(default=None)
