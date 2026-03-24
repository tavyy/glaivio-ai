# Contributing to Glaivio

Thanks for your interest in contributing. Glaivio is early and contributions are very welcome.

## Setup

```bash
git clone https://github.com/tavyy/glaivio.git
cd glaivio
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[postgres,knowledge,openai,gemini,ollama]"
```

Copy `.env.example` and add your API key:

```bash
cp .env.example .env
# add ANTHROPIC_API_KEY
```

## Project structure

```
glaivio/
├── glaivio/
│   ├── agent.py          # core Agent class
│   ├── skill.py          # @skill decorator
│   ├── schema.py         # structured extraction
│   ├── channels/         # web, whatsapp, sms
│   ├── memory/           # in-memory and Postgres backends
│   ├── handoff/          # human handoff
│   ├── learning/         # feedback learning
│   ├── privacy/          # PII redaction
│   ├── knowledge/        # RAG / knowledge base
│   ├── testing/          # eval framework
│   └── cli/              # glaivio CLI commands
├── pyproject.toml
└── README.md
```

## Making changes

1. Fork the repo
2. Create a branch: `git checkout -b my-feature`
3. Make your changes
4. Test manually by building a small agent against your local version: `pip install -e .`
5. Open a pull request with a clear description of what you changed and why

## What we need help with

- More channel integrations (Telegram, email, Slack)
- Built-in skills library (`glaivio.skills.google_calendar`, `glaivio.skills.stripe`, etc.)
- Better error handling and retries
- Token usage tracking
- More LLM providers
- Tests

## Commit style

Keep commits small and focused. Use plain English:

```
Add Telegram channel
Fix Postgres reconnect on idle timeout
Update README — add Telegram example
```

## Questions

Open an issue or start a discussion on GitHub.
