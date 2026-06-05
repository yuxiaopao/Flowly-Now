"""
Enhanced agent debugger service with step-through execution support.
"""

import json
import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class DebugState(str, Enum):
    """Debugger states."""
    IDLE = 'idle'
    RUNNING = 'running'
    PAUSED = 'paused'
    STEP_OVER = 'step_over'
    STEP_INTO = 'step_into'
    STEP_OUT = 'step_out'
    BREAKPOINT = 'breakpoint'
    COMPLETED = 'completed'
    ERROR = 'error'
    TERMINATED = 'terminated'


class StepType(str, Enum):
    """Step types for debugging."""
    START = 'start'
    THOUGHT = 'thought'
    ACTION = 'action'
    OBSERVATION = 'observation'
    TOOL_CALL = 'tool_call'
    TOOL_RESULT = 'tool_result'
    LLM_CALL = 'llm_call'
    LLM_RESPONSE = 'llm_response'
    CONDITION = 'condition'
    LOOP_START = 'loop_start'
    LOOP_END = 'loop_end'
    BRANCH = 'branch'
    STATE_CHANGE = 'state_change'
    END = 'end'


@dataclass
class Breakpoint:
    """Breakpoint definition."""
    id: str
    node_id: str
    node_type: str
    condition: Optional[str] = None
    enabled: bool = True
    hit_count: int = 0
    created_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            from django.utils import timezone
            self.created_at = str(timezone.now())


@dataclass
class DebugStep:
    """Single step in the debug execution."""
    step_id: str
    step_number: int
    step_type: StepType
    timestamp: str

    # Content
    thought: Optional[str] = None
    action: Optional[str] = None
    observation: Optional[str] = None
    tool_name: Optional[str] = None
    tool_input: Optional[Dict] = None
    tool_output: Optional[Any] = None
    llm_prompt: Optional[str] = None
    llm_response: Optional[str] = None
    condition: Optional[str] = None
    condition_result: Optional[bool] = None

    # State
    state_snapshot: Optional[Dict] = None
    variables: Optional[Dict] = None
    node_id: Optional[str] = None
    node_name: Optional[str] = None

    # Breakpoint info
    hit_breakpoint: bool = False
    breakpoint_id: Optional[str] = None

    # Execution info
    duration_ms: Optional[int] = None
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'step_id': self.step_id,
            'step_number': self.step_number,
            'step_type': self.step_type.value,
            'timestamp': self.timestamp,
            'thought': self.thought,
            'action': self.action,
            'observation': self.observation,
            'tool_name': self.tool_name,
            'tool_input': self.tool_input,
            'tool_output': self.tool_output,
            'llm_prompt': self.llm_prompt,
            'llm_response': self.llm_response,
            'condition': self.condition,
            'condition_result': self.condition_result,
            'state_snapshot': self.state_snapshot,
            'variables': self.variables,
            'node_id': self.node_id,
            'node_name': self.node_name,
            'hit_breakpoint': self.hit_breakpoint,
            'breakpoint_id': self.breakpoint_id,
            'duration_ms': self.duration_ms,
            'error': self.error,
            'warnings': self.warnings
        }


@dataclass
class DebugSession:
    """Debug session state."""
    session_id: str
    agent_id: int
    state: DebugState = DebugState.IDLE
    steps: List[DebugStep] = field(default_factory=list)
    breakpoints: List[Breakpoint] = field(default_factory=list)
    current_step: int = 0
    variables: Dict = field(default_factory=dict)
    state_history: List[Dict] = field(default_factory=list)

    # Execution info
    input_data: Optional[Dict] = None
    started_at: Optional[str] = None
    paused_at: Optional[str] = None
    completed_at: Optional[str] = None
    total_duration_ms: int = 0

    # Error tracking
    error: Optional[str] = None
    error_step: Optional[int] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'session_id': self.session_id,
            'agent_id': self.agent_id,
            'state': self.state.value,
            'current_step': self.current_step,
            'total_steps': len(self.steps),
            'variables': self.variables,
            'started_at': self.started_at,
            'paused_at': self.paused_at,
            'completed_at': self.completed_at,
            'total_duration_ms': self.total_duration_ms,
            'error': self.error,
            'error_step': self.error_step,
            'breakpoints': [bp.__dict__ for bp in self.breakpoints]
        }


class AgentDebugger:
    """
    Enhanced agent debugger with step-through execution.
    """

    def __init__(self, agent_id: int):
        self.agent_id = agent_id
        self.sessions: Dict[str, DebugSession] = {}
        self._step_counter = 0

    def create_session(self, session_id: str, input_data: Dict = None) -> DebugSession:
        """Create a new debug session."""
        session = DebugSession(
            session_id=session_id,
            agent_id=self.agent_id,
            state=DebugState.IDLE,
            input_data=input_data or {}
        )
        self.sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[DebugSession]:
        """Get an existing session."""
        return self.sessions.get(session_id)

    def delete_session(self, session_id: str):
        """Delete a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]

    def add_breakpoint(
        self,
        session_id: str,
        node_id: str,
        node_type: str,
        condition: str = None
    ) -> Optional[Breakpoint]:
        """Add a breakpoint to a session."""
        session = self.get_session(session_id)
        if not session:
            return None

        bp_id = f"bp_{len(session.breakpoints) + 1}"
        breakpoint = Breakpoint(
            id=bp_id,
            node_id=node_id,
            node_type=node_type,
            condition=condition
        )
        session.breakpoints.append(breakpoint)
        return breakpoint

    def remove_breakpoint(self, session_id: str, breakpoint_id: str) -> bool:
        """Remove a breakpoint."""
        session = self.get_session(session_id)
        if not session:
            return False

        session.breakpoints = [
            bp for bp in session.breakpoints if bp.id != breakpoint_id
        ]
        return True

    def toggle_breakpoint(self, session_id: str, breakpoint_id: str) -> bool:
        """Toggle a breakpoint enabled/disabled."""
        session = self.get_session(session_id)
        if not session:
            return False

        for bp in session.breakpoints:
            if bp.id == breakpoint_id:
                bp.enabled = not bp.enabled
                return True
        return False

    def check_breakpoint(self, session: DebugSession, node_id: str, node_type: str) -> Optional[Breakpoint]:
        """Check if a breakpoint should be hit."""
        for bp in session.breakpoints:
            if bp.enabled and bp.node_id == node_id and bp.node_type == node_type:
                bp.hit_count += 1
                return bp
        return None

    def start_execution(self, session_id: str) -> bool:
        """Start or resume debug execution."""
        session = self.get_session(session_id)
        if not session:
            return False

        if session.state == DebugState.IDLE:
            session.started_at = str(timezone.now())
            session.state = DebugState.RUNNING
        elif session.state == DebugState.PAUSED:
            session.state = DebugState.RUNNING

        return True

    def pause_execution(self, session_id: str) -> bool:
        """Pause debug execution."""
        session = self.get_session(session_id)
        if not session:
            return False

        session.state = DebugState.PAUSED
        session.paused_at = str(timezone.now())
        return True

    def step_over(self, session_id: str) -> bool:
        """Step over the current execution."""
        session = self.get_session(session_id)
        if not session or session.state != DebugState.PAUSED:
            return False

        session.state = DebugState.STEP_OVER
        return True

    def step_into(self, session_id: str) -> bool:
        """Step into the current execution."""
        session = self.get_session(session_id)
        if not session or session.state != DebugState.PAUSED:
            return False

        session.state = DebugState.STEP_INTO
        return True

    def step_out(self, session_id: str) -> bool:
        """Step out of the current execution."""
        session = self.get_session(session_id)
        if not session or session.state != DebugState.PAUSED:
            return False

        session.state = DebugState.STEP_OUT
        return True

    def terminate_execution(self, session_id: str) -> bool:
        """Terminate the debug execution."""
        session = self.get_session(session_id)
        if not session:
            return False

        session.state = DebugState.TERMINATED
        session.completed_at = str(timezone.now())
        return True

    def record_step(self, session_id: str, step_data: Dict) -> Optional[DebugStep]:
        """Record a debug step."""
        session = self.get_session(session_id)
        if not session:
            return None

        self._step_counter += 1
        step = DebugStep(
            step_id=f"step_{self._step_counter}",
            step_number=len(session.steps) + 1,
            step_type=StepType(step_data.get('step_type', 'state_change')),
            timestamp=step_data.get('timestamp', str(timezone.now())),
            thought=step_data.get('thought'),
            action=step_data.get('action'),
            observation=step_data.get('observation'),
            tool_name=step_data.get('tool_name'),
            tool_input=step_data.get('tool_input'),
            tool_output=step_data.get('tool_output'),
            llm_prompt=step_data.get('llm_prompt'),
            llm_response=step_data.get('llm_response'),
            condition=step_data.get('condition'),
            condition_result=step_data.get('condition_result'),
            state_snapshot=step_data.get('state_snapshot'),
            variables=step_data.get('variables', session.variables.copy()),
            node_id=step_data.get('node_id'),
            node_name=step_data.get('node_name'),
            duration_ms=step_data.get('duration_ms'),
            error=step_data.get('error'),
            warnings=step_data.get('warnings', [])
        )

        session.steps.append(step)
        session.current_step = len(session.steps)

        # Update variables
        if step.variables:
            session.variables.update(step.variables)

        # Save state snapshot
        if step.state_snapshot:
            session.state_history.append(step.state_snapshot)

        return step

    def get_current_step(self, session_id: str) -> Optional[DebugStep]:
        """Get the current step."""
        session = self.get_session(session_id)
        if not session or not session.steps:
            return None
        return session.steps[-1]

    def get_step_range(
        self,
        session_id: str,
        start: int,
        end: int
    ) -> List[DebugStep]:
        """Get a range of steps."""
        session = self.get_session(session_id)
        if not session:
            return []
        return session.steps[start:end]

    def complete_execution(self, session_id: str):
        """Mark execution as completed."""
        session = self.get_session(session_id)
        if not session:
            return

        session.state = DebugState.COMPLETED
        session.completed_at = str(timezone.now())

        if session.started_at:
            from datetime import datetime
            start = datetime.fromisoformat(session.started_at)
            end = datetime.fromisoformat(session.completed_at)
            session.total_duration_ms = int((end - start).total_seconds() * 1000)

    def set_error(self, session_id: str, error: str):
        """Set an error state."""
        session = self.get_session(session_id)
        if not session:
            return

        session.state = DebugState.ERROR
        session.error = error
        session.error_step = session.current_step

    def get_execution_trace(self, session_id: str) -> List[Dict]:
        """Get the full execution trace."""
        session = self.get_session(session_id)
        if not session:
            return []

        return [step.to_dict() for step in session.steps]

    def get_variable_history(self, session_id: str) -> List[Dict]:
        """Get variable history."""
        session = self.get_session(session_id)
        if not session:
            return []

        history = []
        for step in session.steps:
            if step.variables:
                history.append({
                    'step': step.step_number,
                    'variables': step.variables,
                    'timestamp': step.timestamp
                })
        return history


# Global debugger instance
_debuggers: Dict[int, AgentDebugger] = {}


def get_debugger(agent_id: int) -> AgentDebugger:
    """Get or create a debugger for an agent."""
    if agent_id not in _debuggers:
        _debuggers[agent_id] = AgentDebugger(agent_id)
    return _debuggers[agent_id]


def cleanup_debugger(agent_id: int):
    """Clean up a debugger."""
    if agent_id in _debuggers:
        del _debuggers[agent_id]
