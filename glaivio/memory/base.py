from abc import ABC, abstractmethod


class BaseMemory(ABC):
    """Base class for Glaivio memory backends."""

    @abstractmethod
    def get_checkpointer(self):
        """Return a Langgraph-compatible checkpointer."""
        ...
