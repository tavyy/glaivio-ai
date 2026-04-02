# Glaivio

**The framework for building AI agents you can actually trust in production.**

Not just agents that demo well — agents that remember users, recover from mistakes, escalate when stuck, and get smarter over time.

[![PyPI version](https://img.shields.io/pypi/v/glaivio-ai)](https://pypi.org/project/glaivio-ai/)
[![Python](https://img.shields.io/pypi/pyversions/glaivio-ai)](https://pypi.org/project/glaivio-ai/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub stars](https://img.shields.io/github/stars/tavyy/glaivio-ai?style=social)](https://github.com/tavyy/glaivio-ai)

⭐ If this saves you time, [give it a star](https://github.com/tavyy/glaivio-ai) — it helps other developers find it.

Rails did it for web apps. Next.js did it for React. Glaivio does it for AI agents.

```python
from glaivio import Agent, skill

@skill
def book_appointment(patient_name: str, patient_phone: str, date: str, time: str) -> str:
    """Book an appointment. patient_phone: use the current user's ID from context."""
    # call your calendar API here
    return f"Booked {patient_name} on {date} at {time}"

agent = Agent(
    instructions="prompts/system.md",
    skills=[book_appointment],
    learn_from_feedback=True,
    privacy=True,
)

agent.run(channel="whatsapp")
```

That's it. Your agent is live on WhatsApp — with memory, PII redaction, and self-improvement.


https://github.com/user-attachments/assets/e28e1a8c-95e9-4dcc-9cc6-930b7ba6a1be


---

## Install

```bash
pip install glaivio-ai
```

**Optional extras:**

```bash
pip install "glaivio-ai[privacy]"    # PII redaction & re-hydration (Presidio)
pip install "glaivio-ai[gmail]"      # Gmail channel support
pip install "glaivio-ai[knowledge]"  # RAG / knowledge base (ChromaDB)
pip install "glaivio-ai[openai]"     # OpenAI / GPT model support
pip install "glaivio-ai[gemini]"     # Google Gemini model support
pip install "glaivio-ai[ollama]"     # Local models via Ollama
```

---

## What ships out of the box

**Persistent memory** — conversation history survives restarts. Zero config in development, one line to switch to Postgres in production.

**Self-improvement** — when a user corrects the agent, it stores the lesson and applies it to all future conversations. No prompt editing required.

**Human handoff** — when the agent is stuck, it notifies a human operator and holds the conversation until they take over.

**PII redaction** — sensitive identifiers are redacted before reaching the LLM and re-hydrated in the reply, so users still get personalised responses.

**Multi-channel** — the same agent runs on WhatsApp or Gmail. Each channel can have its own prompt — formal for email, concise for WhatsApp.

**Multi-model** — Claude, GPT, Gemini, or local models via Ollama. Swap with one param.

---

## Why Glaivio?

An **AI agent** is an LLM that can take actions, remember things, and talk to users through a channel. Building one from scratch means solving the same problems every time:

- Which LLM? How do I swap between them?
- How do I give it memory across conversations?
- How do I connect it to WhatsApp or email?
- How do I pass the user's identity into a tool call?
- How do I redact sensitive data before it hits the LLM?
- How do I escalate to a human when it gets stuck?
- How do I deploy it?

There are no standard answers. Every team solves these differently, from scratch, every time.

LangChain gives you the primitives — a way to call LLMs, define tools, chain them together. But you still wire everything else yourself. It's powerful, but it's not a framework. It's Lego with no instructions.

**Glaivio makes the decisions for you.**

| | LangChain | Glaivio |
|---|---|---|
| Define a tool | ✅ | ✅ |
| Swap LLM providers | ✅ | ✅ |
| Memory across sessions | You build it | Built in |
| WhatsApp / Gmail channels | You build it | Built in |
| User ID in every skill | You build it | Built in |
| PII redaction | You build it | One flag |
| Human handoff | You build it | One line |
| Agent self-improvement | You build it | One flag |
| Deployment | You figure it out | One command |

```
Web era     → Rails      (2004)  — one way to build web apps
Frontend    → Next.js    (2016)  — one way to build React apps
Agent era   → Glaivio    (2026)  — one way to build AI agents
```

Convention over configuration — the same philosophy that made Rails dominate web development for a decade. If you want full control — use LangChain. If you want to ship in hours not weeks — use Glaivio.

---

## How it works

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
                    │  📱 WhatsApp / Gmail  │  ← the mouth
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

---

## Quickstart

```bash
pip install glaivio-ai
glaivio new my-agent
cd my-agent
cp .env.example .env   # add your ANTHROPIC_API_KEY
glaivio run
```

Your agent is running. Open `prompts/system.md` to change its instructions. Open `skills/example.py` to add capabilities.

For a full real-world example — an AI receptionist that books appointments over WhatsApp — see the [full quickstart](#full-quickstart) below.

---

## Prerequisites

- Python 3.10+
- An API key for your chosen LLM:
  - **Anthropic Claude** (default) — `ANTHROPIC_API_KEY` from [console.anthropic.com](https://console.anthropic.com/)
  - **OpenAI GPT** — `OPENAI_API_KEY`, install with `pip install glaivio-ai[openai]`
  - **Google Gemini** — `GOOGLE_API_KEY`, install with `pip install glaivio-ai[gemini]`
  - **Ollama** (local, free) — no API key needed, install with `pip install glaivio-ai[ollama]`
- For WhatsApp: a [Twilio account](https://twilio.com) with a WhatsApp-enabled number
- For Gmail: a Google Cloud project with the Gmail API enabled

---

## Full Quickstart

An AI receptionist that books appointments over WhatsApp.

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

When booking: ask for name, date and time. Always call check_availability first.
If the slot is taken, offer the alternatives the tool returns.
If medical or urgent, tell them to call the office directly.
```

**3. Define your skills**

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

**4. Wire it up** — `agent.py`

```python
from dotenv import load_dotenv
load_dotenv()

from glaivio import Agent
from skills.check_availability import check_availability
from skills.book_appointment import book_appointment

agent = Agent(
    instructions="prompts/system.md",
    skills=[check_availability, book_appointment],
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

For local testing, expose your server with [ngrok](https://ngrok.com) and point your [Twilio WhatsApp sandbox](https://console.twilio.com) webhook at:
```
https://<your-ngrok-id>.ngrok.io/webhook/whatsapp
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

Skills always know who they're talking to — Glaivio injects the current user's ID automatically:

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

#### WhatsApp

Add to `.env`:
```
ANTHROPIC_API_KEY=your_key
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```

Run:
```bash
glaivio run --channel whatsapp
```

For local testing, expose your server with [ngrok](https://ngrok.com):
```bash
ngrok http 8000
```

Then set the webhook URL in your [Twilio WhatsApp sandbox](https://console.twilio.com):
```
https://<your-ngrok-id>.ngrok.io/webhook/whatsapp
```

---

#### Gmail

Install the extra dependency:
```bash
pip install glaivio-ai[gmail]
```

Set up a Google Cloud project, enable the Gmail API, and download your OAuth `credentials.json`. Add to `.env`:
```
GMAIL_CREDENTIALS_FILE=credentials.json
GMAIL_POLL_INTERVAL=30
GMAIL_TARGET_EMAIL=support@yourcompany.com  # optional — filter by recipient address
```

Run:
```bash
glaivio run --channel gmail
```

The first run opens a browser for OAuth. After that the token is cached and it runs silently. The agent uses LLM classification to decide which emails to handle — it reads its own instructions to determine what's relevant.

---

#### Channel-specific prompts

Each channel can have its own prompt. If `prompts/gmail.md` exists, Glaivio appends it to your base instructions automatically:

```
prompts/
├── system.md     ← shared instructions (who the agent is)
├── whatsapp.md   ← short replies, no markdown
└── gmail.md      ← formal tone, full sentences, sign-off
```

Or set the default channel in `.env`:
```
GLAIVIO_CHANNEL=whatsapp
```

---

### Memory

Zero config by default — conversation history lives in memory, works immediately.

For production, switch to Postgres:

```python
import os
from glaivio import Agent
from glaivio.memory import PostgresMemory

agent = Agent(
    instructions="prompts/system.md",
    memory=PostgresMemory(url=os.getenv("DATABASE_URL")),
)
```

Add `DATABASE_URL` to your `.env` and run `glaivio migrate` once to create the tables. History now survives restarts and works across multiple instances.

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

Supports `.txt`, `.md`, `.pdf`. Requires `pip install glaivio-ai[knowledge]`.

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

The agent detects confusion, notifies your team via WhatsApp, and holds the conversation until a human takes over.

---

### Privacy

Glaivio uses a **redact & re-hydrate** workflow powered by [Microsoft Presidio](https://microsoft.github.io/presidio/):

1. **Redact** — sensitive identifiers (NHS numbers, NI numbers, DOBs, emails) are replaced with placeholders before the message reaches the LLM
2. **Process** — the LLM sees `[NHS_NUMBER_1]` instead of real data
3. **Re-hydrate** — placeholders are swapped back in the LLM's reply before it reaches the user

Names and phone numbers are intentionally **not** redacted so booking skills work correctly.

```python
agent = Agent(
    instructions="prompts/system.md",
    privacy=True,
)
```

```bash
pip install "glaivio-ai[privacy]"
```

You'll see exactly what's happening in your logs:

```
[Glaivio] 🔒 Redacted: 'AB123456C' → '[NI_NUMBER_1]'
[Glaivio] 🔒 Sending to LLM: my NI number is [NI_NUMBER_1]
[Glaivio] 🔓 Restored: '[NI_NUMBER_1]' → 'AB123456C'
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

When a user says *"that's wrong, I said Tuesday not Wednesday"* — the agent extracts the correction, stores it, and applies it to all future conversations. No prompt editing required.

---

### Multi-language

Glaivio agents work in any language — just write your prompts in the language you want the agent to respond in.

```markdown
<!-- prompts/system.md -->
Eres un asistente para una clínica dental en Madrid.
Responde siempre en español, de forma concisa y amable.
```

No configuration needed. The agent responds in whatever language the prompt is written in — Spanish, French, Romanian, Arabic, anything.

For channel-specific tone in a different language, write `prompts/whatsapp.md` or `prompts/gmail.md` in the same language as your system prompt.

---

### Structured Extraction

Extract structured data from natural language:

```python
from pydantic import BaseModel
from glaivio import extract

class BookingRequest(BaseModel):
    name: str
    date: str   # YYYY-MM-DD
    time: str   # HH:MM

booking = extract(BookingRequest, from_message="I need Tuesday 10am, I'm John Smith")
# → BookingRequest(name="John Smith", date="2026-03-25", time="10:00")
```

---

## Supported Models

| Prefix | Provider | Example |
|--------|----------|---------|
| `claude-` | Anthropic | `claude-haiku-4-5-20251001` |
| `gpt-` | OpenAI | `gpt-4o` |
| `gemini-` | Google | `gemini-2.0-flash` |
| `ollama/` | Local (Ollama) | `ollama/llama3` |

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

## Roadmap

**v0.2 — Memory & persistence** ✅
- [x] Postgres memory — conversation history survives restarts
- [x] One-command database setup — tables created automatically, no manual SQL
- [x] Session tracking — per-user metadata (channel, message count, last seen)
- [x] Instructions in markdown — prompts live in files, not code
- [x] User ID injection — skills always know who they're talking to
- [x] Self-improvement — agent learns from user corrections automatically
- [x] Human handoff — escalate to operator when confused, operator teaches agent
- [x] Gmail channel — polls inbox, LLM classification, replies in-thread
- [x] Channel-specific prompts — different tone per channel, zero config

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

⭐ If you find this useful, a star goes a long way — it helps more developers find the project.

Have an idea or want to contribute? [Open an issue](https://github.com/tavyy/glaivio-ai/issues) or read the [contributing guide](CONTRIBUTING.md).

---

## License

MIT
