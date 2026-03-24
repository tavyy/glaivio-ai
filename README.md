# Glaivio

**The opinionated framework for AI-native apps.**

Rails did it for web apps. Next.js did it for React. Glaivio does it for AI agents.

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

## How it works

Glaivio gives every AI-native app the same anatomy:

```
                    ┌──────────────────────┐
                    │   prompts/system.md  │  ← who the agent is
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │     🧠  LLM          │  ← the brain
                    │  Claude/GPT/Gemini   │    decides what to do
                    └──────────┬───────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
┌───────▼────────┐  ┌──────────▼──────────┐  ┌───────▼────────┐
│  @skill        │  │  @skill             │  │  @skill        │  ← the arms
│  search_db()   │  │  send_email()       │  │  book_slot()   │    what it can do
└───────┬────────┘  └──────────┬──────────┘  └───────┬────────┘
        │                      │                      │
        └──────────────────────▼──────────────────────┘
                               │
                    ┌──────────▼───────────┐
                    │  📱 WhatsApp/SMS/Web  │  ← the mouth
                    └──────────┬───────────┘    talks to users
                               │
                    ┌──────────▼───────────┐       ┌──────────────────────┐
                    │        User          │       │   👤 Human operator  │
                    │  "that's wrong,      ├──────►│   notified when      │
                    │   I meant X not Y"   │ stuck │   agent is confused  │
                    └──────────┬───────────┘       │                      │
                               │ correction        │  replies "learned:   │
                    ┌──────────▼───────────┐       │   always confirm X"  │
                    │  💡 Self-improvement  │◄──────┘                     │
                    │  agent gets smarter  │                              │
                    │  with every mistake  │                              │
                    └──────────────────────┘
```

One framework. One way to build. Every AI-native app follows the same pattern.

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

## Prerequisites

- Python 3.10+
- An [Anthropic API key](https://console.anthropic.com/) — Glaivio uses Claude by default
- For WhatsApp/SMS: a [Twilio account](https://twilio.com) with a WhatsApp-enabled number
- For Postgres memory: a running Postgres instance

---

## Install

```bash
pip install glaivio-ai
```

---

## Quickstart

Here's a real example — an AI receptionist that books appointments over WhatsApp.

**1. Scaffold**

```bash
glaivio new my-receptionist
cd my-receptionist
cp .env.example .env   # add your ANTHROPIC_API_KEY
```

**2. Write your prompt** — `prompts/system.md`

```markdown
You are an AI receptionist for Bright Smile Dental.

Your job is to help patients via WhatsApp. Keep replies SHORT — this is a text message.
Max 2 sentences. Never use bullet points or markdown.

Practice info:
- Address: 123 High Street, London
- Hours: Mon-Fri 8am-6pm, Sat 9am-2pm

When booking: ask for name, date and time. Always call check_availability first.
If the slot is taken, offer the alternatives the tool returns.
When rescheduling: cancel the old appointment first, then book the new one.
If medical or urgent, tell them to call the office directly.
```

**3. Generate your skills**

```bash
glaivio generate skill CheckAvailability
glaivio generate skill BookAppointment
glaivio generate skill CancelAppointment
```

Fill in the logic — skills are just functions:

```python
# skills/check_availability.py
from glaivio import skill

@skill
def check_availability(date: str, time: str) -> str:
    """Check if a time slot is available. Always call before book_appointment.
    date: YYYY-MM-DD, time: HH:MM 24h format."""
    # call your calendar API here
    return "Available"
```

```python
# skills/book_appointment.py
from glaivio import skill

@skill
def book_appointment(patient_name: str, patient_phone: str, date: str, time: str) -> str:
    """Book an appointment. Only call after check_availability confirms the slot is free.
    patient_phone: use the current user's ID from context.
    date: YYYY-MM-DD, time: HH:MM 24h format."""
    # call your calendar API here
    return f"Booked {patient_name} on {date} at {time}"
```

```python
# skills/cancel_appointment.py
from glaivio import skill

@skill
def cancel_appointment(patient_phone: str, date: str) -> str:
    """Cancel an existing appointment on a given date.
    patient_phone: use the current user's ID from context.
    date: YYYY-MM-DD format."""
    # call your calendar API here
    return f"Cancelled appointment on {date}"
```

**4. Wire it up** — `agent.py`

```python
from dotenv import load_dotenv
load_dotenv()

from glaivio import Agent
from skills.check_availability import check_availability
from skills.book_appointment import book_appointment
from skills.cancel_appointment import cancel_appointment

agent = Agent(
    instructions="prompts/system.md",
    skills=[check_availability, book_appointment, cancel_appointment],
    learn_from_feedback=True,
    privacy=True,
)

if __name__ == "__main__":
    agent.run(channel="whatsapp")
```

**5. Run it**

```bash
glaivio run --channel whatsapp
```

For local testing, expose your server with [ngrok](https://ngrok.com):

```bash
ngrok http 8000
```

Then in your [Twilio WhatsApp sandbox](https://console.twilio.com), set the webhook URL to:
```
https://<your-ngrok-id>.ngrok.io/webhook/whatsapp
```

Add to your `.env`:
```
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```

Send a WhatsApp message to your Twilio number. Your agent replies.

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

By default Glaivio uses in-memory storage — zero config, works immediately. Conversation history is lost when the server restarts.

For production, switch to Postgres — history survives restarts, works across multiple instances.

**1. Add your database URL to `.env`:**
```
DATABASE_URL=postgresql://user:pass@localhost/mydb
```

**2. Run migrations once** (creates Langgraph checkpoint tables + Glaivio's own session table):
```bash
glaivio migrate
```

Output:
```
Running Glaivio migrations...
  ✓ Database 'mydb' already exists
  ✓ Langgraph checkpoint tables
  ✓ glaivio_sessions table

✓ Migrations complete.
```

**3. Use `PostgresMemory` in your agent:**
```python
import os
from glaivio import Agent
from glaivio.memory import PostgresMemory

agent = Agent(
    instructions="prompts/system.md",
    memory=PostgresMemory(url=os.getenv("DATABASE_URL")),
)
```

Glaivio creates and maintains two sets of tables:
- **Langgraph checkpoint tables** — full message history per user, keyed by their ID
- **`glaivio_sessions`** — your own table tracking `user_id`, `channel`, `message_count`, `tokens_used`, `last_seen`

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
pip install glaivio-ai[knowledge]
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
glaivio migrate                         # run database migrations (Postgres only)
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

## Roadmap

**v0.2 — Memory & persistence** ✅
- [x] Postgres memory — conversation history survives restarts
- [x] One-command database setup — tables created automatically, no manual SQL
- [x] Session tracking — per-user metadata (channel, message count, last seen)
- [x] Instructions in markdown — prompts live in files, not code
- [x] User ID injection — skills always know who they're talking to
- [x] Self-improvement — agent learns from user corrections automatically
- [x] Human handoff — escalate to operator when confused, operator teaches agent

**v0.3 — Observability**
- [ ] Token usage tracking per session, per user, per channel
- [ ] Cost dashboard — see exactly what each conversation costs
- [ ] Structured logs — every message, skill call, and result in one place
- [ ] Twilio webhook signature verification

**v0.4 — Human handover (full loop)**
- [ ] Improved confusion detection — smarter signals beyond keyword matching
- [ ] Full handover UI — operator sees full conversation history before taking over
- [ ] Handover analytics — how often does the agent get stuck, on what topics
- [ ] Automatic resume after operator resolves the conversation

**v0.5 — Self-learning**
- [ ] Feedback learning v2 — agent detects corrections across more signals
- [ ] Rule conflict resolution — when two learned rules contradict each other
- [ ] Learning dashboard — see what the agent has learned, edit or remove rules

**v0.6 — Conscious / unconscious memory**
- [ ] Two-tier memory system inspired by how humans think:
  - **Conscious** — recent conversation, active context (already in v0.2)
  - **Unconscious** — long-term facts about the user, retrieved semantically when relevant
- [ ] User profile store — agent remembers preferences, past interactions, stated facts
- [ ] Smart context injection — only pull in what's relevant to the current message
- [ ] Memory decay — old facts fade unless reinforced

**v0.7 — Skills library**
- [ ] Built-in skills for common integrations — calendars, payments, CRMs, messaging
- [ ] Import skills from community marketplaces — one line to add a pre-built skill

**v1.0 — Glaivio Cloud**
- [ ] One command deploy to the cloud
- [ ] Hosted memory, observability, and token dashboard out of the box
- [ ] No infrastructure to manage

---

Have an idea or want to contribute? [Open an issue](https://github.com/tavyy/glaivio/issues) or read the [contributing guide](CONTRIBUTING.md).

---

## License

MIT
