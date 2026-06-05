"""
Multi-Agent orchestration for collaborative task solving.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List

from dataclasses import dataclass, field
from enum import Enum

from config.constants import DEFAULT_LLM_MODEL, DEFAULT_TEMPERATURE

logger = logging.getLogger(__name__)


class AgentRole(Enum):
    """Roles for multi-agent collaboration."""
    PLANNER = "planner"        # Decomposes tasks, creates plans
    EXECUTOR = "executor"       # Executes tasks, calls tools
    CRITIC = "critic"          # Reviews outputs, provides feedback
    REPORTER = "reporter"       # Synthesizes results, generates reports
    COORDINATOR = "coordinator" # Orchestrates other agents


@dataclass
class AgentMessage:
    """Message between agents."""
    from_agent: str
    to_agent: str
    content: str
    message_type: str = "text"  # text, plan, result, feedback, coordination
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    """Result from a task execution."""
    success: bool
    output: Any = None
    error: str = None
    agent: str = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent:
    """Base class for multi-agent system agents."""

    def __init__(
        self,
        name: str,
        role: AgentRole,
        system_prompt: str,
        model: str = DEFAULT_LLM_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        tools: List[str] = None
    ):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.model = model
        self.temperature = temperature
        self.tools = tools or []
        self._llm = None

    async def think(self, context: Dict[str, Any]) -> str:
        """Process input and generate thought/response."""
        raise NotImplementedError

    async def act(self, thought: str) -> TaskResult:
        """Execute an action based on thought."""
        raise NotImplementedError

    async def reflect(self, result: TaskResult) -> str:
        """Reflect on the result and provide feedback."""
        raise NotImplementedError


class MultiAgentOrchestrator:
    """
    Orchestrator for multi-agent collaboration.
    Manages communication and coordination between agents.
    """

    def __init__(
        self,
        agents: Dict[str, BaseAgent],
        coordinator: Optional[BaseAgent] = None,
        max_iterations: int = 10,
        timeout_seconds: int = 300
    ):
        self.agents = agents
        self.coordinator = coordinator
        self.max_iterations = max_iterations
        self.timeout_seconds = timeout_seconds

        # Message queue for agent communication
        self.message_queue: List[AgentMessage] = []
        self.shared_context: Dict[str, Any] = {}

        # Execution state
        self.is_running = False
        self.iteration_count = 0

    def add_agent(self, agent: BaseAgent):
        """Add an agent to the orchestration."""
        self.agents[agent.name] = agent

    def remove_agent(self, name: str):
        """Remove an agent from the orchestration."""
        if name in self.agents:
            del self.agents[name]

    def send_message(self, message: AgentMessage):
        """Send a message between agents."""
        self.message_queue.append(message)
        logger.debug(f"Message sent: {message.from_agent} -> {message.to_agent}")

    def get_messages_for(self, agent_name: str) -> List[AgentMessage]:
        """Get all messages for a specific agent."""
        return [m for m in self.message_queue if m.to_agent == agent_name]

    def clear_messages_for(self, agent_name: str):
        """Clear messages for a specific agent after processing."""
        self.message_queue = [
            m for m in self.message_queue if m.to_agent != agent_name
        ]

    async def run(self, initial_task: str) -> TaskResult:
        """
        Run the multi-agent collaboration to complete a task.

        Args:
            initial_task: The initial task description

        Returns:
            TaskResult with the final outcome
        """
        self.is_running = True
        self.iteration_count = 0
        self.shared_context = {
            "task": initial_task,
            "history": [],
            "results": {}
        }

        try:
            # Initialize with coordinator or default orchestration
            if self.coordinator:
                result = await self._run_with_coordinator(initial_task)
            else:
                result = await self._run_default(initial_task)

            return result

        except Exception as e:
            logger.error(f"Multi-agent execution failed: {e}")
            return TaskResult(
                success=False,
                error=str(e),
                output=None
            )
        finally:
            self.is_running = False

    async def _run_with_coordinator(self, task: str) -> TaskResult:
        """Run with a coordinator agent managing the workflow."""
        # Coordinator creates the plan
        plan = await self.coordinator.think({
            "task": task,
            "available_agents": list(self.agents.keys()),
            "context": self.shared_context
        })

        self.shared_context["plan"] = plan
        self.send_message(AgentMessage(
            from_agent=self.coordinator.name,
            to_agent="broadcast",
            content=plan,
            message_type="plan"
        ))

        # Execute plan
        for step in plan.get("steps", []):
            agent_name = step.get("agent")
            if agent_name not in self.agents:
                continue

            agent = self.agents[agent_name]
            agent_context = {
                **self.shared_context,
                "current_step": step
            }

            # Agent thinks
            thought = await agent.think(agent_context)

            # Agent acts
            result = await agent.act(thought)
            self.shared_context["results"][agent.name] = result

            # Coordinator reviews
            if self.coordinator:
                feedback = await self.coordinator.reflect(result)
                if feedback.get("needs_revision"):
                    # Send back for revision
                    self.send_message(AgentMessage(
                        from_agent=self.coordinator.name,
                        to_agent=agent_name,
                        content=feedback.get("message", ""),
                        message_type="feedback"
                    ))

        # Generate final report
        if self.coordinator.role == AgentRole.REPORTER:
            final_result = await self.coordinator.think({
                "task": "generate_report",
                "context": self.shared_context
            })
        else:
            final_result = TaskResult(
                success=True,
                output=self.shared_context["results"]
            )

        return final_result

    async def _run_default(self, task: str) -> TaskResult:
        """Run with default orchestration pattern (planner -> executor -> critic)."""
        results = {}

        # Phase 1: Planning
        if "planner" in self.agents:
            planner = self.agents["planner"]
            plan = await planner.think({
                "task": task,
                "context": self.shared_context
            })
            results["plan"] = plan
            self.shared_context["plan"] = plan

        # Phase 2: Execution
        if "executor" in self.agents:
            executor = self.agents["executor"]
            execution_result = await executor.think({
                "task": task,
                "plan": results.get("plan", {}),
                "context": self.shared_context
            })
            results["execution"] = await executor.act(execution_result)

        # Phase 3: Review
        if "critic" in self.agents:
            critic = self.agents["critic"]
            review = await critic.think({
                "task": task,
                "execution": results.get("execution"),
                "context": self.shared_context
            })
            results["review"] = review

        # Phase 4: Report
        if "reporter" in self.agents:
            reporter = self.agents["reporter"]
            report = await reporter.think({
                "task": task,
                "all_results": results,
                "context": self.shared_context
            })
            results["report"] = report

        return TaskResult(
            success=True,
            output=results,
            metadata=self.shared_context
        )

    def get_status(self) -> Dict[str, Any]:
        """Get current orchestration status."""
        return {
            "is_running": self.is_running,
            "iteration_count": self.iteration_count,
            "agents": [a.name for a in self.agents.values()],
            "messages_pending": len(self.message_queue),
            "context_keys": list(self.shared_context.keys())
        }


class SequentialPipeline:
    """
    Simple sequential pipeline for running agents one after another.
    """

    def __init__(self, agents: List[BaseAgent]):
        self.agents = agents

    async def run(self, initial_input: Any) -> Any:
        """Run agents sequentially, passing output to next agent."""
        current_input = initial_input
        results = []

        for agent in self.agents:
            # Agent thinks
            thought = await agent.think({
                "input": current_input,
                "previous_results": results
            })

            # Agent acts
            result = await agent.act(thought)
            results.append({
                "agent": agent.name,
                "thought": thought,
                "result": result
            })

            if result.success:
                current_input = result.output
            else:
                return result  # Stop on first failure

        return TaskResult(
            success=True,
            output=current_input,
            metadata={"all_results": results}
        )


class ParallelExecutor:
    """
    Execute multiple agents in parallel and aggregate results.
    """

    def __init__(self, agents: List[BaseAgent], aggregation_strategy: str = "merge"):
        """
        Args:
            agents: List of agents to execute in parallel
            aggregation_strategy: How to combine results - "merge", "vote", "concat"
        """
        self.agents = agents
        self.aggregation_strategy = aggregation_strategy

    async def run(self, task: str) -> TaskResult:
        """Execute all agents in parallel and aggregate results."""
        async def run_agent(agent: BaseAgent):
            try:
                thought = await agent.think({"task": task})
                result = await agent.act(thought)
                return result
            except Exception as e:
                return TaskResult(
                    success=False,
                    error=str(e),
                    agent=agent.name
                )

        # Run all agents concurrently
        tasks = [run_agent(agent) for agent in self.agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results based on strategy
        aggregated = self._aggregate_results(results)

        return aggregated

    def _aggregate_results(self, results: List) -> TaskResult:
        """Aggregate multiple agent results."""
        successful = [r for r in results if isinstance(r, TaskResult) and r.success]

        if not successful:
            errors = [r.error if isinstance(r, TaskResult) else str(r) for r in results]
            return TaskResult(
                success=False,
                error=f"All agents failed: {errors}"
            )

        if self.aggregation_strategy == "merge":
            merged = {}
            for r in successful:
                if isinstance(r.output, dict):
                    merged.update(r.output)
                else:
                    merged[r.agent] = r.output
            return TaskResult(success=True, output=merged)

        elif self.aggregation_strategy == "concat":
            combined = "\n---\n".join([
                str(r.output) for r in successful if r.output
            ])
            return TaskResult(success=True, output=combined)

        else:  # first_success
            return successful[0]


# LangChain Integration
def create_multi_agent_chain(
    agents: Dict[str, Dict[str, Any]],
    llm_config: Dict[str, Any]
) -> MultiAgentOrchestrator:
    """
    Create a multi-agent orchestrator from configuration.

    Args:
        agents: Dict of agent configs with name, role, system_prompt, tools
        llm_config: LLM configuration (model, api_key, etc.)
    """
    from .engine import AgentEngine

    agent_instances = {}

    for name, config in agents.items():
        role = AgentRole(config.get("role", "executor"))

        # Create agent engine
        engine = AgentEngine(
            system_prompt=config.get("system_prompt", ""),
            model=llm_config.get("model", DEFAULT_LLM_MODEL),
            temperature=llm_config.get("temperature", DEFAULT_TEMPERATURE),
            tools=config.get("tools", [])
        )

        # Wrap as BaseAgent
        agent = MultiAgentWrapper(
            name=name,
            role=role,
            engine=engine
        )
        agent_instances[name] = agent

    return MultiAgentOrchestrator(
        agents=agent_instances,
        max_iterations=llm_config.get("max_iterations", 10)
    )


class MultiAgentWrapper(BaseAgent):
    """Wrapper to use AgentEngine as BaseAgent in multi-agent system."""

    def __init__(
        self,
        name: str,
        role: AgentRole,
        engine,
        system_prompt: str = ""
    ):
        super().__init__(
            name=name,
            role=role,
            system_prompt=system_prompt,
            tools=engine.tools
        )
        self.engine = engine

    async def think(self, context: Dict[str, Any]) -> str:
        """Generate thought/action based on context."""
        task = context.get("task", "")
        return task

    async def act(self, thought: str) -> TaskResult:
        """Execute action using the agent engine."""
        try:
            result = self.engine.chat(thought)
            return TaskResult(
                success=result.get("success", False),
                output=result.get("response"),
                agent=self.name,
                metadata=result
            )
        except Exception as e:
            return TaskResult(
                success=False,
                error=str(e),
                agent=self.name
            )

    async def reflect(self, result: TaskResult) -> str:
        """Provide reflection on result."""
        if result.success:
            return f"Task completed successfully by {self.name}"
        else:
            return f"Task failed: {result.error}"
