"""
Conversation Memory System for NL to Workflow.

Provides persistent, resumable conversation context using LangChain's
memory components with Django model storage.
"""

import logging
from typing import Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.chat_history import BaseChatMessageHistory

from .models import NLSession

logger = logging.getLogger(__name__)


@dataclass
class MessageRecord:
    """A single message in the conversation history."""
    role: str  # "human" or "ai"
    content: str
    timestamp: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "MessageRecord":
        return cls(
            role=data.get("role", "human"),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", "")
        )


class DjangoChatMessageHistory(BaseChatMessageHistory):
    """
    Chat message history stored in Django NLSession model.

    This provides persistent storage for conversation history,
    allowing users to resume conversations across sessions.
    """

    def __init__(self, session_id: str):
        """
        Initialize with a session ID.

        Args:
            session_id: The NLSession primary key or UUID
        """
        self.session_id = session_id
        self._messages: List[MessageRecord] = []
        self._loaded = False

    def _ensure_loaded(self):
        """Lazy load messages from database."""
        if self._loaded:
            return

        try:
            session = NLSession.objects.get(id=self.session_id)
            # JSONField returns a Python list directly — do NOT json.loads
            if session.messages:
                for m in session.messages:
                    self._messages.append(MessageRecord.from_dict(m))
        except NLSession.DoesNotExist:
            self._messages = []

        self._loaded = True

    @property
    def messages(self) -> List[BaseMessage]:
        """Get messages as LangChain message objects."""
        self._ensure_loaded()
        result = []
        for msg in self._messages:
            if msg.role == "human":
                result.append(HumanMessage(content=msg.content))
            else:
                result.append(AIMessage(content=msg.content))
        return result

    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the history."""
        self._ensure_loaded()

        role = "human" if isinstance(message, HumanMessage) else "ai"
        self._messages.append(MessageRecord(
            role=role,
            content=message.content,
            timestamp=datetime.now().isoformat()
        ))

        self._save()

    def add_messages(self, messages: List[BaseMessage]) -> None:
        """Add multiple messages."""
        for message in messages:
            self.add_message(message)

    def clear(self) -> None:
        """Clear all messages."""
        self._messages = []
        self._save()

    def _save(self):
        """Persist messages to database."""
        try:
            session = NLSession.objects.get(id=self.session_id)
            # JSONField stores Python objects directly — do NOT json.dumps
            session.messages = [m.to_dict() for m in self._messages]
            session.save(update_fields=['messages'])
        except NLSession.DoesNotExist:
            logger.warning(f"Session {self.session_id} not found for saving")
        except Exception as e:
            logger.error(f"Failed to save messages: {e}")

    async def aadd_messages(self, messages: List[BaseMessage]) -> None:
        """Async add messages."""
        self.add_messages(messages)

    async def aclear(self) -> None:
        """Async clear messages."""
        self.clear()


class ConversationMemoryManager:
    """
    Manages conversation memory with summary capabilities.

    Uses ConversationSummaryMemory to condense long conversations
    and prevent token limit issues.
    """

    def __init__(
        self,
        session_id: str,
        llm=None,
        max_token_limit: int = 4000,
        summary_threshold: int = 10
    ):
        """
        Initialize memory manager.

        Args:
            session_id: The conversation session ID
            llm: LLM for generating summaries
            max_token_limit: Maximum tokens before summarization
            summary_threshold: Number of messages before summarization
        """
        self.session_id = session_id
        self.max_token_limit = max_token_limit
        self.summary_threshold = summary_threshold

        # Create chat history storage
        self.chat_history = DjangoChatMessageHistory(session_id)

        # Create memory components
        if llm:
            self.memory = ConversationSummaryMemory(
                llm=llm,
                chat_memory=self.chat_history,
                max_token_limit=max_token_limit,
                return_messages=True
            )
        else:
            self.memory = ConversationBufferMemory(
                chat_memory=self.chat_history,
                max_token_limit=max_token_limit,
                return_messages=True,
                output_key="output",
                input_key="input"
            )

    def load_memory_variables(self, input_variables: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Load memory variables for a chain.

        Args:
            input_variables: Optional variables to include

        Returns:
            Dict with memory context
        """
        memory_variables = self.memory.load_memory_variables(input_variables or {})

        # Add session metadata
        memory_variables["session_id"] = self.session_id
        memory_variables["chat_history"] = self.chat_history.messages

        return memory_variables

    def save_context(
        self,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any]
    ) -> None:
        """
        Save context after a chain execution.

        Args:
            inputs: Input variables
            outputs: Output variables
        """
        self.memory.save_context(inputs, outputs)

    def get_conversation_summary(self) -> str:
        """
        Get a summary of the conversation.

        Returns:
            Summary string
        """
        if hasattr(self.memory, 'predict_new_summary'):
            # Get the most recent messages
            messages = self.chat_history.messages[-6:]  # Last 6 messages
            if messages:
                summary = self.memory.predict_new_summary(messages, "")
                return summary
        return ""

    def clear_memory(self) -> None:
        """Clear all conversation memory."""
        self.memory.clear()
        self.chat_history.clear()

    def get_recent_messages(self, count: int = 10) -> List[Dict[str, str]]:
        """
        Get recent messages.

        Args:
            count: Number of recent messages to return

        Returns:
            List of message dicts
        """
        messages = self.chat_history.messages
        recent = messages[-count:] if len(messages) > count else messages

        return [
            {
                "role": "human" if isinstance(m, HumanMessage) else "ai",
                "content": m.content
            }
            for m in recent
        ]


class SessionMemoryPool:
    """
    Pool of memory managers for efficient session management.

    Caches memory managers to avoid repeated database queries.
    """

    _pool: Dict[str, ConversationMemoryManager] = {}
    _llm_provider = None

    @classmethod
    def configure(cls, llm_provider):
        """Configure the LLM provider for summaries."""
        cls._llm_provider = llm_provider

    @classmethod
    def get_memory_manager(
        cls,
        session_id: str,
        llm=None
    ) -> ConversationMemoryManager:
        """
        Get or create a memory manager for a session.

        Args:
            session_id: The session ID
            llm: Optional LLM override

        Returns:
            ConversationMemoryManager instance
        """
        if session_id not in cls._pool:
            llm = llm or cls._llm_provider
            cls._pool[session_id] = ConversationMemoryManager(
                session_id=session_id,
                llm=llm
            )
        return cls._pool[session_id]

    @classmethod
    def clear_session(cls, session_id: str) -> None:
        """Clear a specific session from the pool."""
        if session_id in cls._pool:
            cls._pool[session_id].clear_memory()
            del cls._pool[session_id]

    @classmethod
    def clear_all(cls) -> None:
        """Clear all sessions from the pool."""
        for manager in cls._pool.values():
            manager.clear_memory()
        cls._pool.clear()


def get_memory_manager(
    session_id: str,
    llm=None
) -> ConversationMemoryManager:
    """
    Convenience function to get a memory manager.

    Args:
        session_id: The session ID
        llm: Optional LLM

    Returns:
        ConversationMemoryManager instance
    """
    return SessionMemoryPool.get_memory_manager(session_id, llm)


def format_chat_history_for_prompt(
    session_id: str,
    max_messages: int = 20
) -> str:
    """
    Format chat history as a string for prompt injection.

    Args:
        session_id: The session ID
        max_messages: Maximum number of messages to include

    Returns:
        Formatted history string
    """
    try:
        session = NLSession.objects.get(id=session_id)
        # JSONField returns a Python list directly — do NOT json.loads
        if not session.messages:
            return ""
        # session.messages is already a Python list
        messages = session.messages
        recent = messages[-max_messages:] if len(messages) > max_messages else messages

        lines = []
        for msg in recent:
            role = "用户" if msg["role"] == "human" else "助手"
            lines.append(f"{role}: {msg['content']}")

        return "\n".join(lines)

    except NLSession.DoesNotExist:
        return ""


def build_conversation_messages(
    session_id: str,
    current_input: str
) -> List[Dict[str, str]]:
    """
    Build a message list for LLM with conversation history.

    Args:
        session_id: The session ID
        current_input: The current user input

    Returns:
        List of message dicts for LLM
    """
    messages = []

    # Get recent history
    history = format_chat_history_for_prompt(session_id)
    if history:
        # Parse history and add as messages
        lines = history.split("\n")
        for line in lines:
            if ": " in line:
                role_part, content = line.split(": ", 1)
                role = "user" if "用户" in role_part else "assistant"
                messages.append({"role": role, "content": content})

    # Add current input
    messages.append({"role": "user", "content": current_input})

    return messages
