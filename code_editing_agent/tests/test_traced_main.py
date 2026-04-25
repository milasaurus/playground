"""Integration tests for traced_main.py — the interactive traced flow.

Drives a fake user-input function and a mock streaming client through the
existing `Agent` to simulate a session, then asserts the trace structure.
"""

import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent_trace_debugger.models import (
    NODE_DECISION,
    NODE_OBSERVATION,
    NODE_RESPONSE,
    NODE_TOOL_CALL,
    NODE_USER_INPUT,
)
from agent_trace_debugger.services.client import InstrumentedClient
from agent_trace_debugger.services.tracer import TracingContext

from agent import Agent
from tool_definitions import Tool
from traced_main import _TracingTool


# ── fixtures ─────────────────────────────────────────────────────────────────

class StubTool(Tool):
    def __init__(self, name, payload):
        super().__init__(
            name         = name,
            description  = "returns a fixed payload",
            input_schema = {"type": "object", "properties": {}},
        )
        self._payload = payload

    def run(self, params: dict) -> str:
        return self._payload


def text_block(text):
    b = MagicMock()
    b.type = "text"
    b.text = text
    return b


def tool_use_block(name, tool_id="tu_1", tool_input=None):
    b = MagicMock()
    b.type  = "tool_use"
    b.name  = name
    b.id    = tool_id
    b.input = tool_input or {}
    return b


def make_message(content, stop_reason, input_tokens=5, output_tokens=3):
    m = MagicMock()
    m.content              = content
    m.stop_reason          = stop_reason
    m.model                = "mock-model"
    m.usage.input_tokens   = input_tokens
    m.usage.output_tokens  = output_tokens
    return m


def make_stream(message_obj):
    """Mock context manager that mimics anthropic.messages.stream(...)."""
    s = MagicMock()
    s.text_stream            = iter([])
    s.get_final_message.return_value = message_obj
    s.__enter__              = lambda self: s
    s.__exit__               = lambda self, *args: None
    return s


# ── tests ────────────────────────────────────────────────────────────────────

def test_tracing_tool_records_call_and_observation():
    ctx = TracingContext.start_session()
    ctx.current_decision_id = "decision_1"  # any non-empty id

    wrapped = _TracingTool(StubTool("echo", "hello"), ctx)
    result  = wrapped.run({"msg": "hi"})

    assert result == "hello"
    types = [n.type for n in ctx.tracer.trace.nodes]
    assert NODE_TOOL_CALL   in types
    assert NODE_OBSERVATION in types

    obs = next(n for n in ctx.tracer.trace.nodes if n.type == NODE_OBSERVATION)
    assert obs.content == "hello"


def test_interactive_session_records_full_round_with_correct_parents():
    """One user prompt → decision → tool_call → observation → response.
    Decision must parent to the prompt (not the placeholder root)."""
    ctx = TracingContext.start_session()
    raw_client = MagicMock()
    raw_client.messages.stream.side_effect = [
        make_stream(make_message(
            [text_block("calling echo"), tool_use_block("echo", tool_input={"msg": "hi"})],
            stop_reason="tool_use",
        )),
        make_stream(make_message([text_block("done")], stop_reason="end_turn")),
    ]
    inst_client = InstrumentedClient(raw_client, ctx)
    tools       = [_TracingTool(StubTool("echo", "echoed!"), ctx)]

    prompts = iter([("read agent.py", True), ("", False)])
    def get_user_message():
        msg, ok = next(prompts)
        if ok:
            ctx.start_new_user_input(msg)
        return msg, ok

    Agent(inst_client, get_user_message, tools).run()

    nodes       = ctx.tracer.trace.nodes
    placeholder = nodes[0]
    prompt      = nodes[1]
    decision    = next(n for n in nodes if n.type == NODE_DECISION)
    response    = next(n for n in nodes if n.type == NODE_RESPONSE)

    assert prompt.type        == NODE_USER_INPUT
    assert prompt.parent_id   == placeholder.id
    assert decision.parent_id == prompt.id     # not placeholder.id
    assert response.parent_id == prompt.id


def test_two_prompts_create_two_branches_under_root():
    """Each user prompt becomes a sibling user_input under the placeholder
    root. Decisions for each prompt parent to that prompt's user_input."""
    ctx = TracingContext.start_session()
    raw_client = MagicMock()
    raw_client.messages.stream.side_effect = [
        make_stream(make_message([text_block("first answer")],  stop_reason="end_turn")),
        make_stream(make_message([text_block("second answer")], stop_reason="end_turn")),
    ]
    inst_client = InstrumentedClient(raw_client, ctx)

    prompts = iter([("first prompt", True), ("second prompt", True), ("", False)])
    def get_user_message():
        msg, ok = next(prompts)
        if ok:
            ctx.start_new_user_input(msg)
        return msg, ok

    Agent(inst_client, get_user_message, []).run()

    user_inputs = [n for n in ctx.tracer.trace.nodes if n.type == NODE_USER_INPUT]
    assert len(user_inputs) == 3  # placeholder + 2 prompts

    placeholder, p1, p2 = user_inputs
    assert p1.parent_id == placeholder.id
    assert p2.parent_id == placeholder.id

    responses = [n for n in ctx.tracer.trace.nodes if n.type == NODE_RESPONSE]
    assert len(responses) == 2
    assert responses[0].parent_id == p1.id
    assert responses[1].parent_id == p2.id
