import json
import os
import psycopg2
from ..skill import skill


def _conn():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


@skill
def get_contact(user_id: str) -> str:
    """
    Look up a contact by user ID (e.g. WhatsApp number).
    Returns their name and any stored metadata (last visit, notes, preferences, etc).
    Call this at the start of every conversation to personalise the interaction.
    """
    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT name, metadata FROM glaivio_contacts WHERE user_id = %s",
                    (user_id,),
                )
                row = cur.fetchone()

        if not row:
            return "Contact not found. This is a new contact."

        name, metadata = row
        parts = []
        if name:
            parts.append(f"Name: {name}")
        if metadata:
            for key, value in metadata.items():
                parts.append(f"{key.replace('_', ' ').title()}: {value}")
        return ", ".join(parts) if parts else "Contact found but no details stored."

    except Exception as e:
        return f"Could not retrieve contact: {e}"


@skill
def update_contact(user_id: str, name: str = None, metadata: str = None) -> str:
    """
    Create or update a contact. Pass name and/or metadata as a JSON string.
    Example metadata: '{"last_visit": "2026-03-01", "notes": "Needs follow-up"}'
    Call this when you learn new information about a contact.
    """
    try:
        meta = json.loads(metadata) if metadata else {}
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO glaivio_contacts (user_id, name, metadata, updated_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (user_id) DO UPDATE SET
                        name       = COALESCE(%s, glaivio_contacts.name),
                        metadata   = glaivio_contacts.metadata || %s,
                        updated_at = NOW()
                """, (user_id, name, json.dumps(meta), name, json.dumps(meta)))
            conn.commit()
        return f"Contact updated: {name or user_id}"

    except Exception as e:
        return f"Could not update contact: {e}"
