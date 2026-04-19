from .base import BaseMemory


CREATE_AUDIT_TABLE = """
CREATE TABLE IF NOT EXISTS glaivio_audit (
    id              SERIAL PRIMARY KEY,
    user_id         TEXT NOT NULL,
    channel         TEXT,
    raw_message     TEXT,
    redacted_message TEXT,
    pii_redacted    BOOLEAN DEFAULT FALSE,
    skill_calls     JSONB DEFAULT '[]',
    reply           TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);
"""

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

CREATE_MISSED_CALLS_TABLE = """
CREATE TABLE IF NOT EXISTS glaivio_missed_calls (
    id          SERIAL PRIMARY KEY,
    from_number TEXT NOT NULL,
    to_number   TEXT NOT NULL,
    sent_at     TIMESTAMP DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS glaivio_missed_calls_from_idx ON glaivio_missed_calls (from_number);
"""

CREATE_SMS_CONSENT_TABLE = """
CREATE TABLE IF NOT EXISTS glaivio_sms_consent (
    id          SERIAL PRIMARY KEY,
    from_number TEXT NOT NULL,
    to_number   TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS glaivio_sms_consent_idx ON glaivio_sms_consent (from_number, to_number);
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
            cur.execute(CREATE_MISSED_CALLS_TABLE)
            cur.execute(CREATE_SMS_CONSENT_TABLE)
        conn.commit()

    def check_missed_call_rate_limit(self, from_number: str, hours: int = 24) -> bool:
        """Return True if a missed call SMS was already sent to this number within the last N hours."""
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT sent_at FROM glaivio_missed_calls
                    WHERE from_number = %s
                      AND sent_at > NOW() - INTERVAL '%s hours'
                """, (from_number, hours))
                return cur.fetchone() is not None
        except Exception as e:
            print(f"[Glaivio] Rate limit check error: {e}")
            self._conn.rollback()
            return False

    def record_missed_call(self, from_number: str, to_number: str):
        """Record that a missed call SMS was sent to this number."""
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO glaivio_missed_calls (from_number, to_number)
                    VALUES (%s, %s)
                    ON CONFLICT (from_number) DO UPDATE SET sent_at = NOW()
                """, (from_number, to_number))
            conn.commit()
        except Exception as e:
            print(f"[Glaivio] Record missed call error: {e}")
            self._conn.rollback()

    def get_sms_consent(self, from_number: str, to_number: str) -> str:
        """Return consent status: 'pending', 'consented', 'opted_out', or None (unknown)."""
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT status FROM glaivio_sms_consent
                    WHERE from_number = %s AND to_number = %s
                """, (from_number, to_number))
                row = cur.fetchone()
                return row[0] if row else None
        except Exception as e:
            print(f"[Glaivio] Consent check error: {e}")
            self._conn.rollback()
            return None

    def set_sms_consent(self, from_number: str, to_number: str, status: str):
        """Set consent status for a number. status: 'pending', 'consented', 'opted_out'."""
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO glaivio_sms_consent (from_number, to_number, status)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (from_number, to_number) DO UPDATE SET
                        status = EXCLUDED.status,
                        updated_at = NOW()
                """, (from_number, to_number, status))
            conn.commit()
        except Exception as e:
            print(f"[Glaivio] Consent update error: {e}")
            self._conn.rollback()

    def audit(self, user_id: str, channel: str, raw_message: str, redacted_message: str, pii_redacted: bool, skill_calls: list, reply: str):
        """Persist a full audit record for a conversation turn."""
        try:
            import json
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO glaivio_audit
                        (user_id, channel, raw_message, redacted_message, pii_redacted, skill_calls, reply)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (user_id, channel, raw_message, redacted_message, pii_redacted, json.dumps(skill_calls), reply))
            conn.commit()
        except Exception as e:
            print(f"[Glaivio] Audit error: {e}")
            self._conn.rollback()

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
            self._conn.rollback()

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
