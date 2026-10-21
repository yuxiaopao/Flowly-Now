"""
Multi-Agent orchestration for collaborative task solving.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List

from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor

from config.constants import DEFAULT_LLM_MODEL, DEFAULT_TEMPERATURE
from .engine import AgentEngine

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
            coro = self._run_with_coordinator(initial_task) if self.coordinator else self._run_default(initial_task)
            result = await asyncio.wait_for(coro, timeout=self.timeout_seconds)
            return result

        except asyncio.TimeoutError:
            logger.error(f"Multi-agent execution timed out after {self.timeout_seconds}s")
            return TaskResult(
                success=False,
                error=f"协作任务执行超时（超过 {self.timeout_seconds} 秒）",
                output=None
            )
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
        if not isinstance(plan, dict):
            logger.warning(f"Coordinators returned non-dict plan (type={type(plan).__name__}), skipping execution")
            return TaskResult(
                success=False,
                error=str(plan)[:200],
                output=None,
            )

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
                feedback_str = feedback if isinstance(feedback, str) else ""
                feedback_dict = feedback if isinstance(feedback, dict) else {}
                if feedback_dict.get("needs_revision"):
                    # Send back for revision
                    self.send_message(AgentMessage(
                        from_agent=self.coordinator.name,
                        to_agent=agent_name,
                        content=feedback_dict.get("message", feedback_str),
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
            "agents": list(self.agents.keys()),
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
    agent_instances = {}

    for name, config in agents.items():
        role = AgentRole(config.get("role", "executor"))
        model = config.get("model") or llm_config.get("model", DEFAULT_LLM_MODEL)
        temperature = config.get("temperature", llm_config.get("temperature", DEFAULT_TEMPERATURE))

        engine = AgentEngine(
            system_prompt=config.get("system_prompt", ""),
            model=model,
            temperature=temperature,
            tools=config.get("tools", []),
            knowledge_collection_ids=config.get("knowledge_collection_ids", []),
            user_id=llm_config.get('user_id'),
        )

        # Wrap as BaseAgent
        agent = MultiAgentWrapper(
            name=name,
            role=role,
            engine=engine,
            system_prompt=config.get("system_prompt", ""),
            model=model,
            temperature=temperature
        )
        agent_instances[name] = agent

    return MultiAgentOrchestrator(
        agents=agent_instances,
        max_iterations=llm_config.get("max_iterations", 10)
    )


_executor = ThreadPoolExecutor(max_workers=4)


def _sync_chat(engine: AgentEngine, message: str) -> Dict[str, Any]:
    """Run sync engine.chat() in a thread pool."""
    return engine.chat(message)


class MultiAgentWrapper(BaseAgent):
    """Wrapper to use AgentEngine as BaseAgent in multi-agent system."""

    def __init__(
        self,
        name: str,
        role: AgentRole,
        engine,
        system_prompt: str = "",
        model: str = DEFAULT_LLM_MODEL,
        temperature: float = DEFAULT_TEMPERATURE
    ):
        super().__init__(
            name=name,
            role=role,
            system_prompt=system_prompt,
            tools=engine.tools,
            model=model,
            temperature=temperature
        )
        self.engine = engine

    async def think(self, context: Dict[str, Any]) -> str:
        """Generate role-aware response based on context.

        - PLANNER: returns a JSON plan dict string with steps.
        - EXECUTOR: returns the refined task instruction.
        - CRITIC: returns feedback on the execution result.
        - REPORTER: returns a structured final report.
        """
        task = context.get("task", "")
        available_agents = context.get("available_agents", [])

        if self.role == AgentRole.PLANNER:
            prompt = self._build_planner_prompt(task, available_agents)
        elif self.role == AgentRole.EXECUTOR:
            plan = context.get("plan", {})
            prompt = self._build_executor_prompt(task, plan)
        elif self.role == AgentRole.CRITIC:
            execution = context.get("execution")
            prompt = self._build_critic_prompt(execution)
        elif self.role == AgentRole.REPORTER:
            all_results = context.get("all_results", {})
            prompt = self._build_reporter_prompt(all_results)
        elif self.role == AgentRole.COORDINATOR:
            prompt = self._build_coordinator_prompt(task, available_agents)
        else:
            prompt = task

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor, _sync_chat, self.engine, prompt
        )
        response = result.get("response", "") if isinstance(result, dict) else ""

        # Attempt to parse as JSON plan (for PLANNER and COORDINATOR)
        if self.role in (AgentRole.PLANNER, AgentRole.COORDINATOR):
            import json
            try:
                parsed = json.loads(response)
                if isinstance(parsed, dict):
                    return json.dumps(parsed)
            except (json.JSONDecodeError, ValueError):
                # Not valid JSON — wrap raw text in a steps plan
                return json.dumps({"steps": [{"agent": "executor", "description": response}]})

        return response

    def _build_planner_prompt(self, task: str, available_agents: List[str]) -> str:
        return (
            f"You are a planning agent. Decompose the following task into "
            f"ordered steps. Available agents: {', '.join(available_agents)}.\n\n"
            f"Task: {task}\n\n"
            f"Return ONLY a valid JSON object with a 'steps' key, each step having "
            f"'agent' (one of: {', '.join(available_agents)}) and 'description' fields.\n"
            f"Example: {{'steps': [{{'agent': 'executor', 'description': '...'}}]}}"
        )

    def _build_executor_prompt(self, task: str, plan: Dict) -> str:
        steps_text = ""
        if isinstance(plan, dict):
            steps = plan.get("steps", [])
            if steps:
                steps_text = "\n".join(
                    f"- {i+1}. {s.get('description', s)}" for i, s in enumerate(steps)
                )
        plan_section = f"Plan:\n{steps_text}\n\n" if steps_text else ""
        return (
            f"You are an executor agent. Execute the following task.\n\n"
            f"Task: {task}\n"
            f"{plan_section}"
            f"Perform the task and report your findings concisely."
        )

    def _build_critic_prompt(self, execution) -> str:
        exec_output = ""
        if hasattr(execution, "output"):
            exec_output = str(execution.output) if execution.output else ""
        elif isinstance(execution, dict):
            exec_output = str(execution.get("output", ""))
        elif execution:
            exec_output = str(execution)
        return (
            f"You are a critic agent. Review the following execution result and "
            f"determine if it meets the task requirements. "
            f"If improvements are needed, describe what should be revised.\n\n"
            f"Execution result:\n{exec_output}\n\n"
            f"Respond with either 'APPROVED' or 'NEEDS_REVISION: <reason>'."
        )

    def _build_reporter_prompt(self, all_results: Dict) -> str:
        return (
            f"You are a reporter agent. Synthesize the following results into a "
            f"clear, structured final report.\n\n"
            f"Results: {all_results}\n\n"
            f"Provide a comprehensive summary with key findings and conclusions."
        )

    def _build_coordinator_prompt(self, task: str, available_agents: List[str]) -> str:
        return (
            f"You are a coordinator agent. Break down the following task into "
            f"agent assignments. Available agents: {', '.join(available_agents)}.\n\n"
            f"Task: {task}\n\n"
            f"Return a JSON plan: {{'steps': [{{'agent': '...', 'description': '...'}}, ...]}}"
        )

    async def act(self, thought: str) -> TaskResult:
        """Execute action using the agent engine."""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                _executor, _sync_chat, self.engine, thought
            )
            return TaskResult(
                success=result.get("success", False) if isinstance(result, dict) else False,
                output=result.get("response") if isinstance(result, dict) else str(result),
                agent=self.name,
                metadata=result if isinstance(result, dict) else {}
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
