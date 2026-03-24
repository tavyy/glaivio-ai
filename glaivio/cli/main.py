import os
import sys
import importlib
import subprocess
from pathlib import Path
import click


@click.group()
def cli():
    """Glaivio — the opinionated framework for AI-native apps."""
    pass


# ── glaivio new <name> ────────────────────────────────────────────────────────

@cli.command()
@click.argument("name")
def new(name):
    """Scaffold a new Glaivio project."""
    root = Path(name)

    if root.exists():
        click.echo(f"Error: directory '{name}' already exists.")
        sys.exit(1)

    click.echo(f"Creating {name}/...")

    # create folders
    (root / "skills").mkdir(parents=True)
    (root / "knowledge").mkdir(parents=True)
    (root / "prompts").mkdir(parents=True)
    click.echo("  ✓ skills/")
    click.echo("  ✓ knowledge/")
    click.echo("  ✓ prompts/")

    # prompts/system.md
    (root / "prompts" / "system.md").write_text('''\
You are a helpful assistant.

Keep replies concise and friendly.
''')
    click.echo("  ✓ prompts/system.md")

    # agent.py
    (root / "agent.py").write_text(f'''\
from glaivio import Agent, skill
from dotenv import load_dotenv

load_dotenv()

# Import your skills
from skills.example import hello

agent = Agent(
    instructions="prompts/system.md",
    skills=[hello],
)

if __name__ == "__main__":
    agent.run()
''')
    click.echo("  ✓ agent.py")

    # skills/__init__.py
    (root / "skills" / "__init__.py").write_text("")

    # skills/example.py
    (root / "skills" / "example.py").write_text('''\
from glaivio import skill


@skill
def hello(name: str) -> str:
    """Say hello to someone by name."""
    return f"Hello, {name}!"
''')
    click.echo("  ✓ skills/example.py")

    # .env.example
    (root / ".env.example").write_text('''\
ANTHROPIC_API_KEY=your_key_here

# Optional — only needed for specific channels
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_NUMBER=
TWILIO_WHATSAPP_NUMBER=

# Optional — switch channels
GLAIVIO_CHANNEL=web
''')
    click.echo("  ✓ .env.example")

    # .gitignore
    (root / ".gitignore").write_text('''\
.env
__pycache__/
*.pyc
.venv/
''')
    click.echo("  ✓ .gitignore")

    # requirements.txt
    (root / "requirements.txt").write_text('''\
glaivio-ai
python-dotenv
''')
    click.echo("  ✓ requirements.txt")

    click.echo(f"""
✓ {name}/ ready

Next steps:
  cd {name}
  cp .env.example .env        # add your ANTHROPIC_API_KEY
  pip install -r requirements.txt
  glaivio run
""")


# ── glaivio migrate ───────────────────────────────────────────────────────────

@cli.command()
@click.option("--database-url", default=None, help="Postgres connection URL. Falls back to DATABASE_URL env var.")
def migrate(database_url):
    """Run database migrations. Must be run before starting the agent with Postgres memory."""
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path.cwd() / ".env", override=True)

    url = database_url or os.getenv("DATABASE_URL")
    if not url:
        click.echo("Error: no database URL provided. Set DATABASE_URL in .env or pass --database-url.")
        sys.exit(1)

    click.echo("Running Glaivio migrations...")

    # create the database if it doesn't exist
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        from urllib.parse import urlparse

        parsed = urlparse(url)
        dbname = parsed.path.lstrip("/")
        server_url = url.replace(f"/{dbname}", "/postgres")

        conn = psycopg2.connect(server_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
            if not cur.fetchone():
                cur.execute(f'CREATE DATABASE "{dbname}"')
                click.echo(f"  ✓ Created database '{dbname}'")
            else:
                click.echo(f"  ✓ Database '{dbname}' already exists")
        conn.close()
    except Exception as e:
        click.echo(f"  ✗ Could not create database: {e}")
        sys.exit(1)

    try:
        from langgraph.checkpoint.postgres import PostgresSaver
        with PostgresSaver.from_conn_string(url) as saver:
            saver.setup()
        click.echo("  ✓ Langgraph checkpoint tables")
    except ImportError:
        click.echo("  ✗ Langgraph checkpoint tables skipped (install glaivio-ai[postgres])")
    except Exception as e:
        click.echo(f"  ✗ Langgraph checkpoint tables failed: {e}")
        sys.exit(1)

    try:
        import psycopg2
        from glaivio.memory.postgres import CREATE_SESSIONS_TABLE
        conn = psycopg2.connect(url)
        with conn.cursor() as cur:
            cur.execute(CREATE_SESSIONS_TABLE)
        conn.commit()
        conn.close()
        click.echo("  ✓ glaivio_sessions table")
    except Exception as e:
        click.echo(f"  ✗ glaivio_sessions table failed: {e}")
        sys.exit(1)

    click.echo("\n✓ Migrations complete.")


# ── glaivio run ───────────────────────────────────────────────────────────────

@cli.command()
@click.option("--channel", default=None, help="Channel to run on: web, whatsapp, sms")
@click.option("--port", default=8000, help="Port to run on")
def run(channel, port):
    """Start the agent. Reads GLAIVIO_CHANNEL from .env if --channel not set."""
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path.cwd() / ".env", override=True)

    # ensure project directory is on sys.path so skills/ and other local modules import correctly
    if str(Path.cwd()) not in sys.path:
        sys.path.insert(0, str(Path.cwd()))

    resolved_channel = channel or os.getenv("GLAIVIO_CHANNEL", "web")

    click.echo(f"Starting Glaivio agent on channel: {resolved_channel}")

    # load agent.py from current directory
    agent_path = Path("agent.py")
    if not agent_path.exists():
        click.echo("Error: agent.py not found. Are you in a Glaivio project directory?")
        sys.exit(1)

    spec = importlib.util.spec_from_file_location("agent", agent_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "agent"):
        click.echo("Error: agent.py must define an 'agent' variable.")
        sys.exit(1)

    module.agent.run(channel=resolved_channel, port=port)


# ── glaivio generate skill <Name> ─────────────────────────────────────────────

@cli.group()
def generate():
    """Generate boilerplate files."""
    pass


@generate.command()
@click.argument("name")
def skill(name):
    """Generate a new skill file. Example: glaivio generate skill BookAppointment"""
    # convert CamelCase to snake_case for filename
    snake = _to_snake(name)
    path = Path("skills") / f"{snake}.py"

    if not Path("skills").exists():
        click.echo("Error: skills/ directory not found. Are you in a Glaivio project?")
        sys.exit(1)

    if path.exists():
        click.echo(f"Error: {path} already exists.")
        sys.exit(1)

    path.write_text(f'''\
from glaivio import skill


@skill
def {snake}() -> str:
    """{name} skill. Describe what this skill does so the agent knows when to use it."""
    # TODO: implement
    return ""
''')

    click.echo(f"✓ Created {path}")
    click.echo(f"  Add '{snake}' to your agent's skills list in agent.py")


# ── glaivio test ─────────────────────────────────────────────────────────────

@cli.command()
def test():
    """Run evaluations against your agent."""
    import glob
    from dotenv import load_dotenv
    load_dotenv()

    agent_path = Path("agent.py")
    if not agent_path.exists():
        click.echo("Error: agent.py not found. Are you in a Glaivio project directory?")
        sys.exit(1)

    # load agent
    spec = importlib.util.spec_from_file_location("agent", agent_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "agent"):
        click.echo("Error: agent.py must define an 'agent' variable.")
        sys.exit(1)

    # load all test files
    test_files = glob.glob("tests/**/*.py", recursive=True) + glob.glob("tests/*.py")
    if not test_files:
        click.echo("No test files found. Create a tests/ folder with @eval decorated functions.")
        sys.exit(1)

    for test_file in test_files:
        spec = importlib.util.spec_from_file_location("tests", test_file)
        test_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(test_module)

    click.echo(f"Running evals...\n")
    from glaivio.testing.eval import run_evals
    success = run_evals(module.agent)
    sys.exit(0 if success else 1)


def _to_snake(name: str) -> str:
    """Convert CamelCase to snake_case."""
    import re
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


# ── glaivio deploy ────────────────────────────────────────────────────────────

@cli.command()
@click.option("--target", default="railway", type=click.Choice(["railway", "render", "fly"]), help="Deployment target")
def deploy(target):
    """Generate deployment files for your agent."""
    agent_path = Path("agent.py")
    if not agent_path.exists():
        click.echo("Error: agent.py not found. Are you in a Glaivio project directory?")
        sys.exit(1)

    _write_dockerfile()
    _write_docker_compose()

    if target == "railway":
        _write_railway_config()
        click.echo("""
✓ Generated deployment files:
  Dockerfile
  docker-compose.yml
  railway.toml

Deploy to Railway:
  1. Install Railway CLI:  npm install -g @railway/cli
  2. Login:               railway login
  3. Deploy:              railway up

Your agent will be live at a Railway-provided URL.
Set your env vars in the Railway dashboard after deploying.
""")
    elif target == "render":
        _write_render_config()
        click.echo("""
✓ Generated deployment files:
  Dockerfile
  docker-compose.yml
  render.yaml

Deploy to Render:
  1. Push this repo to GitHub
  2. Go to render.com → New → Web Service
  3. Connect your repo
  4. Render will detect render.yaml automatically

Set your env vars in the Render dashboard.
""")
    elif target == "fly":
        _write_fly_config()
        click.echo("""
✓ Generated deployment files:
  Dockerfile
  docker-compose.yml
  fly.toml

Deploy to Fly.io:
  1. Install Fly CLI:  curl -L https://fly.io/install.sh | sh
  2. Login:           fly auth login
  3. Launch:          fly launch
  4. Deploy:          fly deploy

Set your secrets:  fly secrets set ANTHROPIC_API_KEY=your_key
""")


def _write_dockerfile():
    Path("Dockerfile").write_text('''\
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["glaivio", "run"]
''')


def _write_docker_compose():
    Path("docker-compose.yml").write_text('''\
version: "3.9"

services:
  agent:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    restart: unless-stopped
''')


def _write_railway_config():
    Path("railway.toml").write_text('''\
[build]
builder = "dockerfile"

[deploy]
startCommand = "glaivio run"
healthcheckPath = "/health"
restartPolicyType = "on_failure"
''')


def _write_render_config():
    Path("render.yaml").write_text('''\
services:
  - type: web
    name: glaivio-agent
    runtime: docker
    plan: starter
    healthCheckPath: /health
    envVars:
      - key: ANTHROPIC_API_KEY
        sync: false
      - key: GLAIVIO_CHANNEL
        value: web
''')


def _write_fly_config():
    Path("fly.toml").write_text('''\
app = "glaivio-agent"
primary_region = "lhr"

[build]

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true

[[vm]]
  memory = "512mb"
  cpu_kind = "shared"
  cpus = 1
''')
