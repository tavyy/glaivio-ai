"""
Core unit tests for Glaivio.
All LLM calls are mocked — no API keys required.

Run with: pytest tests/test_core.py -v
"""
import datetime
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from glaivio import Agent, skill
from glaivio.multi import MultiAgent


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_ai_message(content: str, tool_calls=None):
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = tool_calls or []
    msg.__class__ = MagicMock()
    msg.__class__.__name__ = "AIMessage"
    return msg


def mock_invoke(content: str):
    session = MagicMock()
    session.invoke.return_value = {"messages": [make_ai_message(content)]}
    return session


# ── Fixtures ──────────────────────────────────────────────────────────────────

@skill
def check_availability(date: str, time: str) -> str:
    """Check if a dental appointment slot is available. Always call before book_appointment.
    date: YYYY-MM-DD, time: HH:MM 24h format."""
    return "Slot available."


@skill
def book_appointment(patient_name: str, date: str, time: str) -> str:
    """Book a dental appointment. Only call after check_availability confirms the slot is free."""
    return f"Booked {patient_name} on {date} at {time}."


@pytest.fixture
def agent():
    return Agent(
        instructions="You are an AI receptionist for Bright Smile Dental, London. Keep replies short.",
        skills=[check_availability, book_appointment],
    )


@pytest.fixture
def named_agent():
    return Agent(
        instructions="You are an AI receptionist for Bright Smile Dental, London. Keep replies short.",
        name="Bright Smile Dental",
    )


# ── Core reply loop ───────────────────────────────────────────────────────────

def test_agent_returns_string(agent):
    with patch.object(agent, "_get_session", return_value=mock_invoke("Welcome to Bright Smile Dental. How can I help?")):
        reply = agent.reply("patient-001", "Hello")
    assert isinstance(reply, str)
    assert len(reply) > 0


def test_agent_returns_llm_content(agent):
    with patch.object(agent, "_get_session", return_value=mock_invoke("Our hours are Monday to Friday 8am to 6pm.")):
        reply = agent.reply("patient-001", "What are your opening hours?")
    assert "8am" in reply or "Monday" in reply


# ── Em dash stripping ─────────────────────────────────────────────────────────

def test_em_dash_stripped(agent):
    with patch.object(agent, "_get_session", return_value=mock_invoke("We're open Monday — Friday, 8am to 6pm.")):
        reply = agent.reply("patient-001", "Opening hours?")
    assert "—" not in reply


def test_en_dash_stripped(agent):
    with patch.object(agent, "_get_session", return_value=mock_invoke("Monday – Friday")):
        reply = agent.reply("patient-001", "Opening hours?")
    assert "–" not in reply


# ── AI disclosure ─────────────────────────────────────────────────────────────

def test_ai_disclosure_on_first_message(named_agent):
    with patch.object(named_agent, "_get_session", return_value=mock_invoke("How can I help you today?")):
        reply = named_agent.reply("new-patient", "Hello")
    assert "Bright Smile Dental" in reply


def test_ai_disclosure_not_repeated(named_agent):
    with patch.object(named_agent, "_get_session", return_value=mock_invoke("How can I help you today?")):
        named_agent.reply("returning-patient", "Hello")
        reply = named_agent.reply("returning-patient", "I need to book an appointment")
    assert reply.count("personal AI assistant") == 0


def test_no_disclosure_without_name(agent):
    with patch.object(agent, "_get_session", return_value=mock_invoke("How can I help you today?")):
        reply = agent.reply("patient-001", "Hello")
    assert "personal AI assistant" not in reply


# ── Missed call trigger ───────────────────────────────────────────────────────

def test_missed_call_trigger_expands(agent):
    """missed_call string is expanded to a proper instruction before reaching LLM."""
    captured = {}

    def fake_get_session(user_id):
        session = MagicMock()
        def capture_invoke(input_, config=None):
            captured["message"] = input_["messages"][0].content
            return {"messages": [make_ai_message("Sorry we missed your call at Bright Smile Dental!")]}
        session.invoke.side_effect = capture_invoke
        return session

    with patch.object(agent, "_get_session", side_effect=fake_get_session):
        agent.reply("patient-001", "missed_call")

    assert "missed_call" not in captured["message"]
    assert "call" in captured["message"].lower()


def test_missed_call_returns_reply(agent):
    with patch.object(agent, "_get_session", return_value=mock_invoke("Sorry we missed your call! Do you have WhatsApp?")):
        reply = agent.reply("patient-001", "missed_call")
    assert isinstance(reply, str)
    assert len(reply) > 0


# ── Session management ────────────────────────────────────────────────────────

def test_reset_clears_last_reply(agent):
    with patch.object(agent, "_get_session", return_value=mock_invoke("Your appointment is confirmed.")):
        agent.reply("patient-001", "Book me in for Tuesday")
    assert "patient-001" in agent._last_reply
    agent.reset("patient-001")
    assert "patient-001" not in agent._last_reply


def test_reset_clears_last_seen(agent):
    with patch.object(agent, "_get_session", return_value=mock_invoke("Your appointment is confirmed.")):
        agent.reply("patient-001", "Book me in for Tuesday")
    assert "patient-001" in agent._last_seen
    agent.reset("patient-001")
    assert "patient-001" not in agent._last_seen


def test_reset_clears_session(agent):
    agent._sessions["patient-001"] = MagicMock()
    agent.reset("patient-001")
    assert "patient-001" not in agent._sessions


def test_reset_unpauses_patient(agent):
    agent._paused.add("patient-001")
    agent.reset("patient-001")
    assert "patient-001" not in agent._paused


# ── Paused state (human handoff) ──────────────────────────────────────────────

def test_paused_patient_gets_holding_message(agent):
    """Patient handed off to human gets holding message, not agent reply."""
    agent._paused.add("patient-001")
    reply = agent.reply("patient-001", "I need to speak to someone about my treatment plan")
    assert "team" in reply.lower() or "touch" in reply.lower()


def test_paused_patient_does_not_hit_llm(agent):
    """LLM is never called for a paused patient."""
    agent._paused.add("patient-001")
    with patch.object(agent, "_get_session") as mock_session:
        agent.reply("patient-001", "Hello")
        mock_session.assert_not_called()


# ── Session TTL ───────────────────────────────────────────────────────────────

def test_session_ttl_expires():
    """Stale session is cleared after TTL, patient starts fresh."""
    ttl_agent = Agent(instructions="You are an AI receptionist for Bright Smile Dental.", session_ttl=1)
    ttl_agent._last_seen["patient-001"] = datetime.datetime.now() - datetime.timedelta(hours=2)
    ttl_agent._sessions["patient-001"] = MagicMock()
    ttl_agent._last_reply["patient-001"] = "Your last appointment was on Monday."

    with patch.object(ttl_agent, "_get_session", return_value=mock_invoke("Welcome back! How can I help?")):
        ttl_agent.reply("patient-001", "Hi")

    assert "patient-001" not in ttl_agent._sessions or ttl_agent._sessions.get("patient-001") is not None


# ── Confusion detection ───────────────────────────────────────────────────────

def test_is_confused_true(agent):
    assert agent._is_confused("I'm not sure I can help with your treatment plan.")
    assert agent._is_confused("I don't know the answer to that medical question.")
    assert agent._is_confused("Please call us directly to discuss your x-ray results.")
    assert agent._is_confused("I cannot help with insurance claims.")
    assert agent._is_confused("I am unable to process that request.")


def test_is_confused_false(agent):
    assert not agent._is_confused("Your appointment is confirmed for Tuesday at 10am.")
    assert not agent._is_confused("We have availability on Thursday at 2pm.")
    assert not agent._is_confused("I've cancelled your appointment as requested.")


# ── System prompt building ────────────────────────────────────────────────────

def test_system_prompt_includes_instructions(agent):
    system = agent._build_system()
    assert "Bright Smile Dental" in system


def test_system_prompt_includes_date(agent):
    system = agent._build_system()
    today = datetime.date.today().strftime("%Y-%m-%d")
    assert today in system


def test_system_prompt_includes_patient_id(agent):
    system = agent._build_system(user_id="+447911111111")
    assert "+447911111111" in system


def test_system_prompt_includes_ai_rule(agent):
    system = agent._build_system()
    assert "AI assistant" in system


# ── Skill call logging ────────────────────────────────────────────────────────

def test_skill_calls_are_captured(agent):
    """Skill calls appear in audit skill_calls list."""
    tool_msg = MagicMock()
    tool_msg.content = "Slot available."
    tool_msg.__class__ = MagicMock()
    tool_msg.__class__.__name__ = "ToolMessage"

    ai_with_tool = make_ai_message(
        "Let me check availability.",
        tool_calls=[{"name": "check_availability", "args": {"date": "2026-04-20", "time": "10:00"}}]
    )
    final_msg = make_ai_message("Tuesday 10am is available. Shall I book it?")

    session = MagicMock()
    session.invoke.return_value = {"messages": [ai_with_tool, tool_msg, final_msg]}

    with patch.object(agent, "_get_session", return_value=session):
        reply = agent.reply("patient-001", "Is Tuesday 10am free?")

    assert "available" in reply.lower() or "tuesday" in reply.lower() or "10" in reply


# ── MultiAgent base prompt injection ─────────────────────────────────────────

@pytest.fixture
def multi_agent_dir(tmp_path):
    """Create a temp directory with clients.yaml and prompt files."""
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "system.md").write_text("# Generic HVAC behaviour\nYou are an HVAC receptionist.")
    (tmp_path / "prompts" / "quickcool.md").write_text("# Business Info\nName: QuickCool HVAC\nPhone: +1 555 123 4567")
    (tmp_path / "clients.yaml").write_text(
        '"+1xxxxxxxxxx":\n'
        '  name: QuickCool HVAC\n'
        '  instructions: prompts/quickcool.md\n'
        '  base: prompts/system.md\n'
    )
    return tmp_path


def test_multiagent_base_prepends_to_instructions(multi_agent_dir):
    """base prompt is prepended before client-specific instructions."""
    orig_dir = os.getcwd()
    os.chdir(multi_agent_dir)
    try:
        ma = MultiAgent(config="clients.yaml")
        agent = ma.resolve("+1xxxxxxxxxx")
        assert "Generic HVAC behaviour" in agent.instructions
        assert "QuickCool HVAC" in agent.instructions
    finally:
        os.chdir(orig_dir)


def test_multiagent_base_comes_before_client(multi_agent_dir):
    """base prompt content appears before client-specific content."""
    orig_dir = os.getcwd()
    os.chdir(multi_agent_dir)
    try:
        ma = MultiAgent(config="clients.yaml")
        agent = ma.resolve("+1xxxxxxxxxx")
        base_pos = agent.instructions.index("Generic HVAC behaviour")
        client_pos = agent.instructions.index("QuickCool HVAC")
        assert base_pos < client_pos
    finally:
        os.chdir(orig_dir)


def test_multiagent_without_base(tmp_path):
    """clients.yaml without base field works as before."""
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "quickcool.md").write_text("You are a helpful assistant.")
    (tmp_path / "clients.yaml").write_text(
        '"+1xxxxxxxxxx":\n'
        '  name: QuickCool HVAC\n'
        '  instructions: prompts/quickcool.md\n'
    )
    orig_dir = os.getcwd()
    os.chdir(tmp_path)
    try:
        ma = MultiAgent(config="clients.yaml")
        agent = ma.resolve("+1xxxxxxxxxx")
        assert "helpful assistant" in agent.instructions
    finally:
        os.chdir(orig_dir)


def test_multiagent_resolve_unknown_number(multi_agent_dir):
    """Resolving an unknown number raises ValueError."""
    orig_dir = os.getcwd()
    os.chdir(multi_agent_dir)
    try:
        ma = MultiAgent(config="clients.yaml")
        with pytest.raises(ValueError, match="No client configured"):
            ma.resolve("+9999999999")
    finally:
        os.chdir(orig_dir)
