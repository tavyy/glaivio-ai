from .base import BaseMemory


class PostgresMemory(BaseMemory):
    """
    PostgreSQL-backed memory. Conversation history persists across restarts.

    Usage:
        from glaivio.memory import PostgresMemory

        agent = Agent(
            instructions="You are a helpful assistant.",
            memory=PostgresMemory(url="postgresql://user:pass@localhost/mydb"),
        )

    Requires:
        pip install langgraph-checkpoint-postgres
    """

    def __init__(self, url: str):
        self.url = url

    def get_checkpointer(self):
        try:
            from langgraph.checkpoint.postgres import PostgresSaver
        except ImportError:
            raise ImportError(
                "PostgresMemory requires langgraph-checkpoint-postgres.\n"
                "Install it with: pip install langgraph-checkpoint-postgres"
            )

        saver = PostgresSaver.from_conn_string(self.url)
        saver.setup()  # creates tables if they don't exist
        return saver
