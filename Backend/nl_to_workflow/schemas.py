"""
Pydantic models for structured workflow generation.
Used by LangChain Output Parser for type-safe JSON parsing.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator


class NodeConfig(BaseModel):
    """Configuration for workflow nodes."""
    model_config = {"extra": "allow"}  # Allow additional fields


class WorkflowNode(BaseModel):
    """A single node in the workflow graph."""
    id: str = Field(description="Unique node ID (e.g., node_1, node_2)")
    type: str = Field(
        description="Node type: start/end/input/llm/condition/tool/code/output"
    )
    name: str = Field(
        default="",
        description="Display name for the node",
    )
    position: Dict[str, Any] = Field(
        default_factory=lambda: {"x": 100, "y": 150},
        description="Canvas coordinates {x: number, y: number}",
    )
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Node-specific configuration",
    )

    @field_validator("name", mode="before")
    @classmethod
    def coerce_name(cls, v, info):
        if isinstance(v, str) and v.strip():
            return v.strip()
        node_type = ""
        if info.data and isinstance(info.data, dict):
            node_type = str(info.data.get("type") or "")
        defaults = {
            "start": "开始",
            "end": "结束",
            "input": "输入",
            "output": "输出",
            "llm": "大语言模型",
            "code": "代码执行",
            "loop": "循环",
            "image_generation": "图像生成",
            "video_generation": "视频生成",
            "subtitle_generation": "字幕生成",
            "merge": "合并",
            "json_transform": "数据转换",
        }
        return defaults.get(node_type, node_type or "Node")

    @field_validator("position", mode="before")
    @classmethod
    def coerce_position(cls, v):
        if not isinstance(v, dict):
            return {"x": 100, "y": 150}
        out = dict(v)
        out.setdefault("x", 100)
        out.setdefault("y", 150)
        return out

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        return v


class WorkflowEdge(BaseModel):
    """A connection between two nodes."""
    id: str = Field(description="Unique edge ID (e.g., edge_1, edge_2)")
    source: str = Field(description="Source node ID")
    target: str = Field(description="Target node ID")
    label: str = Field(
        default="",
        description="Edge label (e.g., condition branch name)",
    )


class WorkflowSchema(BaseModel):
    """Complete workflow structure."""
    name: str = Field(description="Workflow name (concise and meaningful)")
    description: str = Field(
        default="",
        description="Workflow description (1-2 sentences)",
    )
    nodes: List[WorkflowNode] = Field(
        description="List of workflow nodes",
    )
    edges: List[WorkflowEdge] = Field(
        default_factory=list,
        description="List of connections between nodes",
    )

    @field_validator("nodes")
    @classmethod
    def validate_nodes(cls, v: List[WorkflowNode]) -> List[WorkflowNode]:
        if not v:
            raise ValueError("Workflow must have at least one node")
        return v

    @field_validator("edges", mode="before")
    @classmethod
    def coerce_edges(cls, v):
        return [] if v is None else v

    @model_validator(mode="after")
    def auto_chain_edges_if_missing(self):
        """If LLM omitted edges, chain nodes in listed order so graph is usable."""
        if self.edges:
            return self
        nodes = self.nodes or []
        if len(nodes) < 2:
            return self
        chained = []
        for i in range(len(nodes) - 1):
            chained.append(
                WorkflowEdge(
                    id=f"edge_{i + 1}",
                    source=nodes[i].id,
                    target=nodes[i + 1].id,
                    label="",
                )
            )
        self.edges = chained
        return self

    @field_validator("edges")
    @classmethod
    def validate_edges(cls, v: List[WorkflowEdge], info) -> List[WorkflowEdge]:
        # Soft-validate references: drop invalid edges instead of failing whole parse
        if "nodes" not in info.data:
            return v or []
        node_ids = {node.id for node in info.data["nodes"]}
        kept = []
        for edge in v or []:
            if edge.source in node_ids and edge.target in node_ids:
                kept.append(edge)
        return kept


class WorkflowModificationSchema(BaseModel):
    """Schema for workflow modification responses (same as workflow)."""
    name: Optional[str] = Field(
        default=None,
        description="Updated workflow name",
    )
    description: Optional[str] = Field(
        default=None,
        description="Updated workflow description",
    )
    nodes: Optional[List[WorkflowNode]] = Field(
        default=None,
        description="Updated list of workflow nodes",
    )
    edges: Optional[List[WorkflowEdge]] = Field(
        default=None,
        description="Updated list of connections",
    )


class ValidationResult(BaseModel):
    """Validation result for workflow."""
    valid: bool = Field(description="Whether the workflow is valid")
    errors: List[str] = Field(
        default_factory=list,
        description="List of validation errors",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="List of validation warnings",
    )


class WorkflowWithValidation(BaseModel):
    """Workflow with validation result."""
    name: str
    description: str
    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]
    validation: ValidationResult = Field(default_factory=ValidationResult)
    estimated_cost: Optional[float] = Field(default=None)
