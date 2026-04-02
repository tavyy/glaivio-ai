from .base import BaseMemory


CREATE_CONTACTS_TABLE = """
CREATE TABLE IF NOT EXISTS glaivio_contacts (
    id         SERIAL PRIMARY KEY,
    user_id    TEXT UNIQUE NOT NULL,
    name       TEXT,
    metadata   JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
"""

CREATE_SESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS glaivio_sessions (
    id            SERIAL PRIMARY KEY,
    user_id       TEXT NOT NULL,
    channel       TEXT,
    started_at    TIMESTAMP DEFAULT NOW(),
    last_seen     TIMESTAMP DEFAULT NOW(),
    message_count INT DEFAULT 0,
    tokens_used   INT DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS glaivio_sessions_user_id_idx ON glaivio_sessions (user_id);
"""

UPSERT_SESSION = """
INSERT INTO glaivio_sessions (user_id, channel, last_seen, message_count, tokens_used)
VALUES (%(user_id)s, %(channel)s, NOW(), 1, %(tokens_used)s)
ON CONFLICT (user_id) DO UPDATE SET
    last_seen     = NOW(),
    message_count = glaivio_sessions.message_count + 1,
    tokens_used   = glaivio_sessions.tokens_used + %(tokens_used)s;
"""


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
        pip install glaivio-ai[postgres]
    """

    def __init__(self, url: str):
        self.url = url
        self._checkpointer = None
        self._conn = None

    def _get_conn(self):
        import psycopg2
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(self.url)
        return self._conn

    def setup(self):
        """Create Glaivio's own tables if they don't exist."""
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(CREATE_SESSIONS_TABLE)
        conn.commit()

    def track(self, user_id: str, channel: str = None, tokens_used: int = 0):
        """Update session metadata after each turn."""
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute(UPSERT_SESSION, {
                    "user_id": user_id,
                    "channel": channel,
                    "tokens_used": tokens_used,
                })
            conn.commit()
        except Exception as e:
            print(f"[Glaivio] Session tracking error: {e}")

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
            import psycopg
            conn = psycopg.connect(self.url, autocommit=True)
            saver = PostgresSaver(conn)
            saver.setup()
            self._checkpointer = saver
            print("[Glaivio] Postgres memory connected.")
            return self._checkpointer
        except Exception as e:
            raise ConnectionError(
                f"[Glaivio] Failed to connect to Postgres: {e}\n"
                f"Check your DATABASE_URL and that Postgres is running."
            )
