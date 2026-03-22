from langgraph.checkpoint.memory import MemorySaver
from .base import BaseMemory


class InMemory(BaseMemory):
    """
    Default in-memory backend. Fast, zero config.
    Conversation history is lost when the process restarts.
    """

    def get_checkpointer(self):
        return MemorySaver()
