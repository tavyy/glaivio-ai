import yaml
from pathlib import Path
from .agent import Agent


class MultiAgent:
    """
    Routes inbound messages to the correct Agent based on the Twilio 'To' number.
    One deployment, multiple clients.

    Usage:
        from glaivio import MultiAgent

        agent = MultiAgent(
            config="clients.yaml",
            skills=[book_appointment, check_availability],
            memory=PostgresMemory(url=os.getenv("DATABASE_URL")),
            learn_from_feedback=True,
            privacy=True,
        )

        agent.run(channel="whatsapp")

    clients.yaml:
        "whatsapp:+447911111111":
          name: bright-smile
          instructions: prompts/bright-smile.md

        "whatsapp:+447922222222":
          name: leeds-dental
          instructions: prompts/leeds-dental.md
    """

    def __init__(self, config: str = "clients.yaml", skills: list = None, **agent_kwargs):
        self._config_path = Path(config)
        self._skills = skills or []
        self._agent_kwargs = agent_kwargs
        self._agents: dict[str, Agent] = {}
        self._load()

    def _load(self):
        clients = yaml.safe_load(self._config_path.read_text())
        for number, cfg in clients.items():
            name = cfg.get("name", number)
            instructions = cfg.get("instructions", "You are a helpful assistant.")
            whatsapp_number = cfg.get("whatsapp_number")
            if whatsapp_number:
                wa_number = whatsapp_number.replace("+", "").replace(" ", "")
                wa_link = f"https://wa.me/{wa_number}"
                instructions += f"\n\nIf the customer says yes to WhatsApp, send them this link to start a chat: {wa_link}"
            self._agents[number] = Agent(
                instructions=instructions,
                name=name,
                skills=self._skills,
                **self._agent_kwargs,
            )
            print(f"[Glaivio] Loaded client: {name} ({number})")

    def resolve(self, to: str) -> Agent:
        """Return the agent for the given Twilio 'To' number."""
        if to not in self._agents:
            raise ValueError(f"No client configured for '{to}'. Check clients.yaml.")
        return self._agents[to]

    def run(self, channel: str = "whatsapp", **kwargs):
        """Start the multi-client agent on a channel."""
        for agent in self._agents.values():
            agent._current_channel = channel
        from .channels import get_channel
        ch = get_channel(channel)
        ch.start(self, **kwargs)
