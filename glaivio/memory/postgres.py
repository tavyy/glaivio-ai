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
        self._checkpointer = None

    def get_checkpointer(self):
        if self._checkpointer is not None:
            return self._checkpointer

        try:
            from langgraph.checkpoint.postgres import PostgresSaver
        except ImportError:
            raise ImportError(
                "PostgresMemory requires langgraph-checkpoint-postgres.\n"
                "Install it with: pip install glaivio-ai[postgres]"
            )

        try:
            saver = PostgresSaver.from_conn_string(self.url)
            saver.setup()  # creates tables if they don't exist
            self._checkpointer = saver
            print(f"[Glaivio] Postgres memory connected.")
            return self._checkpointer
        except Exception as e:
            raise ConnectionError(
                f"[Glaivio] Failed to connect to Postgres: {e}\n"
                f"Check your DATABASE_URL and that Postgres is running."
            )
