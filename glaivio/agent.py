import datetime
from langchain_core.messages import HumanMessage, BaseMessage
from langchain_core.language_models import BaseChatModel
from langgraph.prebuilt import create_react_agent

from .memory.in_memory import InMemory


def _trim_messages(messages: list[BaseMessage], max_messages: int) -> list[BaseMessage]:
    """Keep only the last N messages to control context size."""
    if max_messages and len(messages) > max_messages:
        return messages[-max_messages:]
    return messages


def _resolve_llm(model: str) -> BaseChatModel:
    """Resolve a model string to a Langchain LLM instance."""
    if model.startswith("claude"):
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model, max_tokens=256)
    elif model.startswith("gemini"):
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model)
    elif model.startswith("gpt") or model.startswith("o1") or model.startswith("o3"):
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model)
    elif model.startswith("ollama/"):
        from langchain_ollama import ChatOllama
        return ChatOllama(model=model.removeprefix("ollama/"))
    else:
        raise ValueError(
            f"Unknown model '{model}'. "
            "Prefix with 'claude-', 'gemini-', 'gpt-', or 'ollama/' to specify the provider."
        )


class Agent:
    """
    The core Glaivio agent.

    Usage:
        agent = Agent(
            instructions="You are a helpful operator.",
            skills=[book_appointment, check_availability],
        )
        agent.run(channel="whatsapp")
    """

    def __init__(
        self,
        instructions: str,
        skills: list = None,
        model: str = "claude-haiku-4-5-20251001",
        memory=None,
        privacy: bool = False,
        inject_date: bool = True,
        knowledge=None,
        max_messages: int = 20,
        on_confusion=None,
        learn_from_feedback: bool = False,
    ):
        self.instructions = instructions
        self.skills = skills or []
        self.model_name = model
        self.memory = memory or InMemory()
        self.privacy = privacy
        self.inject_date = inject_date
        self.knowledge = knowledge
        self.max_messages = max_messages
        self.on_confusion = on_confusion
        self.learn_from_feedback = learn_from_feedback
        self._sessions: dict[str, any] = {}
        self._paused: set[str] = set()
        self._last_reply: dict[str, str] = {}  # track last reply per user
        self._knowledge_tool = None
        self._learner = None

        if self.learn_from_feedback:
            from .learning.feedback import FeedbackLearner
            self._learner = FeedbackLearner()

        # attach agent to handoff so it can access learner + sessions
        if self.on_confusion:
            self.on_confusion.attach(self)

        # build knowledge retriever once at startup
        if self.knowledge:
            self._knowledge_tool = self.knowledge.build_retriever()

    def _build_system(self) -> str:
        """Build the system prompt including any learned corrections."""
        system = ""
        if self._learner:
            system += self._learner.as_prompt_prefix()
        system += self.instructions
        if self.inject_date:
            system += f"\nToday is {datetime.date.today().strftime('%Y-%m-%d, %A')}."
        return system

    def _get_session(self, user_id: str):
        """Get or create a per-user agent session."""
        if user_id not in self._sessions:
            llm = _resolve_llm(self.model_name)
            checkpointer = self.memory.get_checkpointer()
            system = self._build_system()
            # combine skills + knowledge retriever
            all_tools = list(self.skills)
            if self._knowledge_tool:
                all_tools.append(self._knowledge_tool)

            self._sessions[user_id] = create_react_agent(
                model=llm,
                tools=all_tools,
                checkpointer=checkpointer,
                prompt=system,
            )
        return self._sessions[user_id]

    def reply(self, user_id: str, message: str) -> str:
        """Send a message and get a response. Used by channels internally."""

        # if handed off to human, hold until reset
        if user_id in self._paused:
            return "You're already connected with our team. They'll be in touch shortly."

        # redact PII before sending to LLM
        if self.privacy:
            from .privacy.redact import redact
            message = redact(message)

        session = self._get_session(user_id)
        config = {"configurable": {"thread_id": user_id}}
        result = session.invoke(
            {"messages": [HumanMessage(content=message)]},
            config=config,
        )
        messages = result["messages"]
        trimmed = _trim_messages(messages, self.max_messages)
        reply = trimmed[-1].content

        # check if agent signalled confusion
        if self.on_confusion and self._is_confused(reply):
            self._paused.add(user_id)
            return self.on_confusion.trigger(user_id, message)

        # detect user correction and learn from it
        if self._learner and self._learner.is_correction(message):
            last_reply = self._last_reply.get(user_id, "")
            if last_reply:
                self._learner.extract_and_store(message, last_reply, self.model_name)
                # rebuild session so corrections apply immediately
                self._sessions.pop(user_id, None)

        # store this reply for next turn
        self._last_reply[user_id] = reply

        return reply

    def _is_confused(self, reply: str) -> bool:
        """Detect if the agent is confused and needs human help."""
        confusion_signals = [
            "i'm not sure",
            "i don't know",
            "i cannot help",
            "i can't help",
            "please call us",
            "contact the office",
            "speak to someone",
            "i'm unable to",
            "i am unable to",
        ]
        reply_lower = reply.lower()
        return any(signal in reply_lower for signal in confusion_signals)

    def operator_reply(self, message: str) -> str | None:
        """
        Process an inbound message from the operator.
        Handles 'learned:' and 'resume:' commands.
        Returns a response to send back to the operator, or None.
        """
        if self.on_confusion:
            return self.on_confusion.process_operator_message(message)
        return None

    def reset(self, user_id: str):
        """Clear conversation history for a user."""
        self._sessions.pop(user_id, None)
        self._paused.discard(user_id)
        self._last_reply.pop(user_id, None)

    def run(self, channel: str = "web", **kwargs):
        """Start the agent on a channel."""
        from .channels import get_channel
        ch = get_channel(channel)
        ch.start(self, **kwargs)
