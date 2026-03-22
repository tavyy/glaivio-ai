import os


# Magic prefix the operator uses to teach the agent
LEARN_PREFIX = "learned:"
RESUME_PREFIX = "resume:"


class HumanHandoff:
    """
    Pauses the agent and notifies a human when the agent can't handle a situation.

    Usage:
        from glaivio.handoff import handoff_to_human

        agent = Agent(
            instructions="You are a helpful assistant.",
            on_confusion=handoff_to_human(
                notify="whatsapp:+447911111111",
                learn=True,
            ),
        )

    When triggered, the agent:
    1. Sends a WhatsApp/SMS alert to the notify number with conversation context
    2. Tells the user a human will be in touch
    3. Pauses the session

    The operator can then:
    - Text "learned: when user asks X, say Y" → agent stores the lesson
    - Text "resume: +447911111111" → agent unpauses that user's session
    """

    def __init__(self, notify: str, learn: bool = False):
        self.notify = notify
        self.learn = learn
        self._agent = None  # set by Agent after init

    def attach(self, agent):
        """Attach to the parent agent so we can access learner and sessions."""
        self._agent = agent

    def trigger(self, user_id: str, last_message: str, conversation_summary: str = ""):
        """Send alert to human and return a holding message for the user."""
        self._notify_human(user_id, last_message, conversation_summary)
        return "I'm going to connect you with a member of our team who can help. They'll be in touch shortly."

    def _notify_human(self, user_id: str, last_message: str, conversation_summary: str):
        """Send a WhatsApp or SMS alert via Twilio."""
        sid = os.getenv("TWILIO_ACCOUNT_SID")
        token = os.getenv("TWILIO_AUTH_TOKEN")
        from_number = os.getenv("TWILIO_WHATSAPP_NUMBER") or os.getenv("TWILIO_NUMBER")

        body = f"[Agent handoff]\nUser: {user_id}\nLast message: {last_message}"
        if conversation_summary:
            body += f"\nContext: {conversation_summary}"
        if self.learn:
            body += f"\n\nTo teach me: reply 'learned: <rule>'\nTo resume: reply 'resume: {user_id}'"

        if not all([sid, token, from_number]):
            print(f"\n[HANDOFF] {body}")
            return

        try:
            from twilio.rest import Client
            client = Client(sid, token)
            client.messages.create(to=self.notify, from_=from_number, body=body)
        except Exception as e:
            print(f"[HANDOFF] Failed to notify human: {e}")

    def process_operator_message(self, message: str) -> str | None:
        """
        Process an inbound message from the operator.
        Returns a response string if handled, None if not a handoff command.
        """
        message_stripped = message.strip()
        lower = message_stripped.lower()

        # "learned: when user asks X, say Y"
        if lower.startswith(LEARN_PREFIX):
            rule = message_stripped[len(LEARN_PREFIX):].strip()
            if rule and self._agent and self._agent._learner:
                self._agent._learner._corrections.append(rule)
                self._agent._learner._save()
                # rebuild all sessions so correction applies immediately
                self._agent._sessions.clear()
                print(f"[HANDOFF] Learned: {rule}")
                return f"Got it. I'll remember: {rule}"
            return "Learning is not enabled on this agent."

        # "resume: +447911111111"
        if lower.startswith(RESUME_PREFIX):
            user_id = message_stripped[len(RESUME_PREFIX):].strip()
            if self._agent:
                self._agent._paused.discard(user_id)
                self._agent._sessions.pop(user_id, None)
                print(f"[HANDOFF] Resumed session for {user_id}")
                return f"Session resumed for {user_id}. I'll take it from here."
            return None

        return None


def handoff_to_human(notify: str, learn: bool = False) -> HumanHandoff:
    """
    Create a human handoff handler.

    Args:
        notify: Phone number to alert. Use 'whatsapp:+44...' for WhatsApp or '+44...' for SMS.
        learn:  If True, the operator can teach the agent by replying 'learned: <rule>'
    """
    return HumanHandoff(notify=notify, learn=learn)
