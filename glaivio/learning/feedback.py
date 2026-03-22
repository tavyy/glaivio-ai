import json
import os
from pathlib import Path


# Signals that the user is correcting the agent
CORRECTION_SIGNALS = [
    "that's wrong",
    "thats wrong",
    "that is wrong",
    "no i said",
    "no, i said",
    "not right",
    "you misunderstood",
    "i meant",
    "i said",
    "that's incorrect",
    "thats incorrect",
    "that is incorrect",
    "you got it wrong",
    "wrong day",
    "wrong time",
    "wrong date",
    "not what i asked",
    "that's not what i",
    "no that's",
    "no thats",
]


class FeedbackLearner:
    """
    Stores corrections from users and injects them into future conversations.

    When a user says "that's wrong, I said Tuesday" — the agent extracts
    the correction and applies it to all future conversations.

    Usage:
        agent = Agent(
            instructions="You are a helpful assistant.",
            learn_from_feedback=True,
        )
    """

    def __init__(self, storage_path: str = ".glaivio/corrections.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._corrections: list[str] = self._load()

    def _load(self) -> list[str]:
        if self.storage_path.exists():
            try:
                return json.loads(self.storage_path.read_text())
            except Exception:
                return []
        return []

    def _save(self):
        self.storage_path.write_text(json.dumps(self._corrections, indent=2))

    def is_correction(self, message: str) -> bool:
        """Check if the user message is a correction."""
        message_lower = message.lower()
        return any(signal in message_lower for signal in CORRECTION_SIGNALS)

    def extract_and_store(self, user_message: str, last_agent_reply: str, model: str = "claude-haiku-4-5-20251001"):
        """
        Use LLM to extract a correction rule from the user's feedback
        and store it for future use.
        """
        try:
            from langchain_anthropic import ChatAnthropic
            llm = ChatAnthropic(model=model, max_tokens=128)

            prompt = f"""A user corrected an AI agent. Extract a concise rule the agent should follow in future.

Agent said: {last_agent_reply}
User corrected: {user_message}

Write ONE short rule (max 20 words) starting with "Always" or "Never" or "When".
Only output the rule, nothing else."""

            correction = llm.invoke(prompt).content.strip()

            if correction and correction not in self._corrections:
                self._corrections.append(correction)
                self._save()
                print(f"[Glaivio] Learned: {correction}")

        except Exception as e:
            print(f"[Glaivio] Could not extract correction: {e}")

    def as_prompt_prefix(self) -> str:
        """Return corrections formatted as a system prompt prefix."""
        if not self._corrections:
            return ""
        rules = "\n".join(f"- {c}" for c in self._corrections)
        return f"[Learned from past conversations]\n{rules}\n\n"

    def clear(self):
        """Clear all stored corrections."""
        self._corrections = []
        self._save()
