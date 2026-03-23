# Glaivio

**The opinionated framework for AI-native apps.**

No UI. No forms. No buttons. Just a brain, skills, and a channel.

```python
from glaivio import Agent, skill

@skill
def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    return f"Sunny, 22°C in {city}"

agent = Agent(
    instructions="prompts/system.md",
    skills=[get_weather],
)

agent.run(channel="whatsapp")
```

That's it. Your agent is live on WhatsApp.

---

## Why Glaivio?

Every developer building an AI agent today faces the same problems:

- Which LLM? How do I swap between them?
- How do I give it memory across conversations?
- How do I connect it to WhatsApp or SMS?
- How do I give it tools without breaking everything?
- How do I deploy it?
- How do I test it when I change the prompt?

There are no standard answers. Every team solves these differently, from scratch, every time.

Langchain and similar SDKs give you the primitives — but you still wire everything together yourself. It's powerful and flexible, but it's not a framework. It's Lego with no instructions.

**Glaivio makes the decisions for you.**

One way to define skills. One way to add memory. One way to connect channels. One command to deploy. Convention over configuration — the same philosophy that made Rails dominate web development for a decade.

```
Web era     → Rails      (2004)  — one way to build web apps
Frontend    → Next.js    (2016)  — one way to build React apps
Agent era   → Glaivio    (2026)  — one way to build AI-native apps
```

If you want full control and flexibility — use Langchain. If you want to ship in hours not weeks — use Glaivio.

---

## Install

```bash
pip install glaivio
```

---

## Quickstart

```bash
glaivio new my-app
cd my-app
cp .env.example .env   # add your ANTHROPIC_API_KEY
glaivio run
```

This scaffolds:

```
my-app/
├── prompts/
│   └── system.md       ← write your agent's instructions here
├── skills/
│   └── example.py
├── knowledge/
├── agent.py
├── .env.example
└── requirements.txt
```

Open `http://localhost:8000` — your agent is running.

---

## Core Concepts

### Prompts

Write your agent's instructions in plain markdown — no string literals in code:

```
prompts/
└── system.md
```

Point your agent at it:

```python
agent = Agent(
    instructions="prompts/system.md",
    ...
)
```

Glaivio loads it automatically. Edit the prompt without touching `agent.py`.

---

### Skills

Skills are what your agent can do. Define them with `@skill`:

```python
from glaivio import skill

@skill
def book_appointment(name: str, date: str, time: str) -> str:
    """Book an appointment. date: YYYY-MM-DD, time: HH:MM."""
    # your logic here — call an API, write to a DB, anything
    return "Booked successfully"
```

The docstring is what the agent reads to decide when to use the skill. Write it clearly.

Skills that need to identify the current user can use `user_id` — Glaivio injects it automatically into every session:

```python
@skill
def book_appointment(name: str, user_phone: str, date: str, time: str) -> str:
    """Book an appointment. user_phone: use the current user's ID from context."""
    ...
```

No closures. No wiring. It just works.

---

### Agent

```python
from glaivio import Agent

agent = Agent(
    instructions="prompts/system.md",
    skills=[book_appointment, check_availability],
    model="claude-haiku-4-5-20251001",   # or "gpt-4o", "gemini-2.0-flash", "ollama/llama3"
    max_messages=20,                      # context window per session
)
```

---

### Channels

Run your agent on any channel:

```python
agent.run(channel="web")        # browser chat UI + REST API
agent.run(channel="whatsapp")   # Twilio WhatsApp webhook
agent.run(channel="sms")        # Twilio SMS webhook
```

Or set it in `.env`:
```
GLAIVIO_CHANNEL=whatsapp
```

Then just run:
```bash
glaivio run
```

---

### Memory

```python
from glaivio.memory import PostgresMemory

agent = Agent(
    instructions="prompts/system.md",
    memory=PostgresMemory(url="postgresql://user:pass@localhost/mydb"),
)
```

Default is in-memory (zero config). Switch to Postgres for production — conversation history survives restarts.

```bash
pip install glaivio[postgres]
```

---

### Knowledge

Drop files in and the agent searches them automatically:

```python
from glaivio.knowledge import Knowledge

agent = Agent(
    instructions="prompts/system.md",
    knowledge=Knowledge(["./faqs.md", "./pricing.pdf", "./policies.txt"]),
)
```

Supports `.txt`, `.md`, `.pdf`. No configuration needed.

```bash
pip install glaivio[knowledge]
```

---

### Human Handoff

When the agent can't handle something, escalate to a human:

```python
from glaivio.handoff import handoff_to_human

agent = Agent(
    instructions="prompts/system.md",
    on_confusion=handoff_to_human(notify="whatsapp:+447911111111"),
)
```

The agent detects confusion, notifies your team via WhatsApp/SMS, and holds the conversation until a human takes over.

---

### Privacy

Automatically redact PII before it reaches the LLM:

```python
agent = Agent(
    instructions="prompts/system.md",
    privacy=True,  # redacts phone numbers, emails, NHS numbers, NI numbers
)
```

---

### Learning from Feedback

The agent learns from user corrections automatically:

```python
agent = Agent(
    instructions="prompts/system.md",
    skills=[book_appointment],
    learn_from_feedback=True,
)
```

When a user says *"that's wrong, I said Tuesday not Wednesday"* — the agent extracts the correction, stores it, and applies it to all future conversations:

```
[Learned from past conversations]
- Always book the exact day the user specifies, never the next day
- When user says Tuesday, confirm Tuesday before booking
```

Corrections persist in `.glaivio/corrections.json`. The agent gets smarter over time without any manual prompt editing.

---

### Structured Extraction

Extract structured data from natural language — no prompt writing:

```python
from pydantic import BaseModel
from glaivio import extract

class BookingRequest(BaseModel):
    name: str
    date: str   # YYYY-MM-DD
    time: str   # HH:MM
    reason: str = "Appointment"

booking = extract(BookingRequest, from_message="I need Tuesday 10am, I'm John Smith")
# → BookingRequest(name="John Smith", date="2026-03-25", time="10:00", reason="Appointment")
```

---

## CLI

```bash
glaivio new my-app                      # scaffold a project
glaivio run                             # start the agent
glaivio run --channel whatsapp          # start on a specific channel
glaivio generate skill BookAppointment  # generate a skill stub
glaivio test                            # run evaluations
glaivio deploy                          # generate Railway deployment files
glaivio deploy --target render          # generate Render deployment files
glaivio deploy --target fly             # generate Fly.io deployment files
```

---

## Evaluations

Test your agent like you test your code:

```python
# tests/test_booking.py
from glaivio.testing import eval, EvalCase

@eval
def test_booking(agent):
    return [
        EvalCase("I want Tuesday 10am", "booked", "basic booking"),
        EvalCase("Cancel my appointment", "cancelled", "cancellation"),
        EvalCase("Do you accept BUPA?", "bupa", "insurance FAQ"),
    ]
```

```bash
glaivio test
# → 3/3 passed ✅
```

Change your instructions and run again — regressions are caught automatically.

---

## Supported Models

| Prefix | Provider | Example |
|--------|----------|---------|
| `claude-` | Anthropic | `claude-haiku-4-5-20251001` |
| `gpt-` | OpenAI | `gpt-4o` |
| `gemini-` | Google | `gemini-2.0-flash` |
| `ollama/` | Local (Ollama) | `ollama/llama3` |

---

## Deploy

```bash
glaivio deploy
```

Generates a `Dockerfile`, `docker-compose.yml`, and `railway.toml`.

```bash
railway login
railway up
```

Done. Your agent is live.

---

## Reference App

A fully autonomous WhatsApp dental receptionist — books appointments, checks availability, and handles patient conversations 24/7. Built in 20 lines:

```python
from dotenv import load_dotenv
load_dotenv()

from glaivio import Agent
from glaivio.handoff import handoff_to_human
from glaivio.knowledge import Knowledge
from skills.check_availability import check_availability
from skills.book_appointment import book_appointment
from skills.cancel_appointment import cancel_appointment

agent = Agent(
    instructions="prompts/system.md",
    skills=[check_availability, book_appointment, cancel_appointment],
    knowledge=Knowledge(["./faqs.md"]),
    on_confusion=handoff_to_human(notify="whatsapp:+447911111111", learn=True),
    learn_from_feedback=True,
    privacy=True,
)

agent.run(channel="whatsapp")
```

---

## License

MIT
