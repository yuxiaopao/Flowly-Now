"""
Agent Tools for NL to Workflow.

Provides ReAct-style agent with tools for:
- Template search and retrieval
- User workflow history
- Workflow validation
- External API calls
"""

import json
import logging
from typing import Dict, Any, Optional, List, Type, Callable
from dataclasses import dataclass

from langchain_core.tools import BaseTool, tool
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain import hub
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.language_models import BaseChatModel

from workflows.models import Workflow, WorkflowNode, WorkflowTemplate, DomainTemplate
from workflows.services import WorkflowExecutionService
from .models import NLSession

logger = logging.getLogger(__name__)


# ========================
# Tool Definitions
# ========================

@tool
def search_workflow_templates(
    query: str,
    category: str = "",
    limit: int = 5
) -> str:
    """
    Search workflow templates by keyword or description.

    Args:
        query: Search query (keywords, description text)
        category: Optional category filter
        limit: Maximum number of results (default 5)

    Returns:
        JSON string with matching templates
    """
    from django.db.models import Q

    filters = Q(name__icontains=query) | Q(description__icontains=query)

    if category:
        filters &= Q(category__icontains=category)

    templates = WorkflowTemplate.objects.filter(filters)[:limit]

    results = []
    for t in templates:
        results.append({
            "id": str(t.id),
            "name": t.name,
            "description": t.description,
            "category": t.category or "",
            "nodes_count": t.nodes.count() if hasattr(t, 'nodes') else 0
        })

    return json.dumps(results, ensure_ascii=False)


@tool
def get_user_workflows(
    user_id: str,
    limit: int = 10
) -> str:
    """
    Get user's existing workflows for reference.

    Args:
        user_id: User ID
        limit: Maximum number of workflows (default 10)

    Returns:
        JSON string with user's workflows
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()

    try:
        user = User.objects.get(id=user_id)
        workflows = Workflow.objects.filter(
            owner=user,
            is_active=True
        ).order_by('-updated_at')[:limit]

        results = []
        for w in workflows:
            results.append({
                "id": str(w.id),
                "name": w.name,
                "description": w.description or "",
                "status": w.status or "draft",
                "node_count": w.nodes.count(),
                "updated_at": w.updated_at.isoformat() if w.updated_at else None
            })

        return json.dumps(results, ensure_ascii=False)

    except User.DoesNotExist:
        return json.dumps({"error": "User not found"})


@tool
def get_workflow_template_by_id(
    template_id: str
) -> str:
    """
    Get a specific workflow template by ID.

    Args:
        template_id: Template UUID

    Returns:
        JSON string with template details
    """
    try:
        template = WorkflowTemplate.objects.get(id=template_id)
        return json.dumps({
            "id": str(template.id),
            "name": template.name,
            "description": template.description,
            "category": template.category or "",
            "definition": template.definition or {}
        }, ensure_ascii=False)

    except WorkflowTemplate.DoesNotExist:
        return json.dumps({"error": "Template not found"})


@tool
def get_domain_templates(
    domain: str = "",
    limit: int = 5
) -> str:
    """
    Get domain-specific workflow templates.

    Args:
        domain: Domain name (e.g., 'customer_service', 'data_processing')
        limit: Maximum results (default 5)

    Returns:
        JSON string with domain templates
    """
    filters = {}
    if domain:
        filters['domain__icontains'] = domain

    templates = DomainTemplate.objects.filter(**filters)[:limit]

    results = []
    for t in templates:
        results.append({
            "id": str(t.id),
            "name": t.name,
            "domain": t.domain or "",
            "description": t.description,
            "use_count": t.use_count
        })

    return json.dumps(results, ensure_ascii=False)


@tool
def validate_workflow_nodes(
    workflow_json: str
) -> str:
    """
    Validate workflow node configuration.

    Args:
        workflow_json: JSON string of workflow definition

    Returns:
        Validation result as JSON string
    """
    try:
        workflow = json.loads(workflow_json)

        errors = []
        warnings = []

        # Check required fields
        if not workflow.get('name'):
            warnings.append("工作流缺少名称")

        if not workflow.get('nodes'):
            errors.append("工作流缺少节点")
            return json.dumps({"valid": False, "errors": errors, "warnings": warnings})

        # Check node types
        node_types = [n.get('type') for n in workflow['nodes']]
        if 'start' not in node_types:
            warnings.append("缺少开始节点")
        if 'end' not in node_types:
            warnings.append("缺少结束节点")

        # Check edges reference valid nodes
        node_ids = {n.get('id') for n in workflow['nodes']}
        for edge in workflow.get('edges', []):
            if edge.get('source') not in node_ids:
                errors.append(f"边引用了不存在的源节点: {edge.get('source')}")
            if edge.get('target') not in node_ids:
                errors.append(f"边引用了不存在的目标节点: {edge.get('target')}")

        return json.dumps({
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        })

    except json.JSONDecodeError as e:
        return json.dumps({"valid": False, "errors": [f"JSON解析错误: {str(e)}"]})


@tool
def get_nl_session_history(
    session_id: str,
    limit: int = 20
) -> str:
    """
    Get conversation history for a session.

    Args:
        session_id: Session UUID
        limit: Maximum messages (default 20)

    Returns:
        JSON string with conversation history
    """
    try:
        session = NLSession.objects.get(id=session_id)
        messages = session.messages[-limit:] if session.messages else []

        return json.dumps({
            "session_id": str(session.id),
            "session_name": session.name,
            "workflow_name": session.workflow_name,
            "messages": messages,
            "status": session.status
        }, ensure_ascii=False)

    except NLSession.DoesNotExist:
        return json.dumps({"error": "Session not found"})


@tool
def calculate_workflow_complexity(
    workflow_json: str
) -> str:
    """
    Calculate workflow complexity metrics.

    Args:
        workflow_json: JSON string of workflow definition

    Returns:
        Complexity analysis as JSON string
    """
    try:
        workflow = json.loads(workflow_json)
        nodes = workflow.get('nodes', [])
        edges = workflow.get('edges', [])

        # Count node types
        node_type_counts = {}
        for n in nodes:
            node_type = n.get('type', 'unknown')
            node_type_counts[node_type] = node_type_counts.get(node_type, 0) + 1

        # Calculate metrics
        node_count = len(nodes)
        edge_count = len(edges)
        density = edge_count / node_count if node_count > 0 else 0

        # Complexity score
        complexity_score = 0
        complexity_score += node_count * 1  # Base score per node
        complexity_score += edge_count * 0.5  # Edges add some complexity
        complexity_score += node_type_counts.get('llm', 0) * 3  # LLM nodes are expensive
        complexity_score += node_type_counts.get('condition', 0) * 2  # Conditions add branching

        return json.dumps({
            "node_count": node_count,
            "edge_count": edge_count,
            "node_type_counts": node_type_counts,
            "density": round(density, 2),
            "complexity_score": round(complexity_score, 1),
            "complexity_level": "low" if complexity_score < 10 else "medium" if complexity_score < 25 else "high"
        })

    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON"})


# ========================
# Tool Registry
# ========================

class WorkflowAgentTools:
    """Registry of all available tools for the workflow agent."""

    def __init__(self):
        self._tools: List[BaseTool] = [
            search_workflow_templates,
            get_user_workflows,
            get_workflow_template_by_id,
            get_domain_templates,
            validate_workflow_nodes,
            get_nl_session_history,
            calculate_workflow_complexity,
        ]

    @property
    def tools(self) -> List[BaseTool]:
        """Get all available tools."""
        return self._tools

    def get_tools_by_category(self, category: str) -> List[BaseTool]:
        """Get tools filtered by category (future enhancement)."""
        return self._tools

    def to_lc_tools(self) -> List:
        """Convert to LangChain tool format."""
        return self._tools


# ========================
# Agent Builder
# ========================

class WorkflowAgentBuilder:
    """
    Builder for creating workflow generation agents.

    Creates ReAct-style agents with tool access for enhanced
    workflow generation with context awareness.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        tools: Optional[List[BaseTool]] = None,
        max_iterations: int = 5,
        verbose: bool = True
    ):
        """
        Initialize agent builder.

        Args:
            llm: Chat model for the agent
            tools: List of tools (uses default if not provided)
            max_iterations: Max tool calling iterations
            verbose: Enable verbose output
        """
        self.llm = llm
        self.tools = tools or WorkflowAgentTools().tools
        self.max_iterations = max_iterations
        self.verbose = verbose

    def build(self) -> AgentExecutor:
        """
        Build and return an agent executor.

        Returns:
            Configured AgentExecutor instance
        """
        # Get the ReAct prompt from LangChain hub
        prompt = hub.pull("hwchase17/react")

        # Create the agent
        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )

        # Create executor
        executor = AgentExecutor.from_agent_and_tools(
            agent=agent,
            tools=self.tools,
            verbose=self.verbose,
            max_iterations=self.max_iterations,
            handle_parsing_errors=True
        )

        return executor

    def build_with_custom_prompt(
        self,
        system_prompt: str,
        tools: Optional[List[BaseTool]] = None
    ) -> AgentExecutor:
        """
        Build agent with custom system prompt.

        Args:
            system_prompt: Custom system prompt
            tools: Optional tool list override

        Returns:
            AgentExecutor with custom prompt
        """
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_react_agent(
            llm=self.llm,
            tools=tools or self.tools,
            prompt=prompt
        )

        return AgentExecutor.from_agent_and_tools(
            agent=agent,
            tools=tools or self.tools,
            verbose=self.verbose,
            max_iterations=self.max_iterations,
            handle_parsing_errors=True
        )


# ========================
# Convenience Functions
# ========================

def create_workflow_agent(
    llm: BaseChatModel,
    max_iterations: int = 5
) -> AgentExecutor:
    """
    Create a workflow generation agent.

    Args:
        llm: Chat model
        max_iterations: Max tool iterations

    Returns:
        Configured AgentExecutor
    """
    builder = WorkflowAgentBuilder(
        llm=llm,
        max_iterations=max_iterations
    )
    return builder.build()


def run_workflow_generation_with_agent(
    agent: AgentExecutor,
    description: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Run workflow generation using an agent.

    Args:
        agent: Agent executor
        description: User's workflow description
        context: Optional context dict

    Returns:
        Generation result
    """
    try:
        result = agent.invoke({
            "input": description,
            "context": json.dumps(context) if context else "{}"
        })

        return {
            "output": result.get("output"),
            "intermediate_steps": result.get("intermediate_steps", []),
            "success": True
        }

    except Exception as e:
        logger.exception(f"Agent execution failed: {e}")
        return {
            "output": None,
            "error": str(e),
            "success": False
        }
