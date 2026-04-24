import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from agent_trace_debugger.agent import TOOL_IMPLS, ResearchAgent
from agent_trace_debugger.models import (
    NODE_DECISION,
    NODE_OBSERVATION,
    NODE_RESPONSE,
    NODE_TOOL_CALL,
    NODE_USER_INPUT,
)
from agent_trace_debugger.services.agent_runner import run_traced
from agent_trace_debugger.services.tool_runner import ToolRunner


MODEL = "mock-model"

# Tests that exercise the client-side tool instrumentation path use this echo
# tool instead of `web_search` — the real agent's `web_search` is a server-side
# Anthropic tool (handled inside the response content), not a client-dispatched
# one, so `TOOL_IMPLS` is empty in production.
TEST_TOOL_IMPLS = {"echo": lambda i: f"echo: {i.get('msg', '')}"}


def text_block(text):
    b = MagicMock()
    b.type = "text"
    b.text = text
    return b


def tool_use_block(name, input, id="tu_1"):
    b = MagicMock()
    b.type  = "tool_use"
    b.name  = name
    b.id    = id
    b.input = input
    return b


def server_tool_use_block(name, input, id="stu_1"):
    b = MagicMock()
    b.type  = "server_tool_use"
    b.name  = name
    b.id    = id
    b.input = input
    return b


def web_search_result_block(tool_use_id, results):
    """results: list of MagicMocks with .title and .url, or an error MagicMock with .error_code."""
    b = MagicMock()
    b.type        = "web_search_tool_result"
    b.tool_use_id = tool_use_id
    b.content     = results
    return b


def search_result(title, url):
    r = MagicMock()
    r.title = title
    r.url   = url
    return r


def message(content, stop_reason, input_tokens=5, output_tokens=3):
    m = MagicMock()
    m.content     = content
    m.stop_reason = stop_reason
    m.model       = MODEL
    m.usage.input_tokens  = input_tokens
    m.usage.output_tokens = output_tokens
    return m


def make_client(*responses):
    """Mock Anthropic client whose .messages.create returns responses in order."""
    client = MagicMock()
    client.messages.create.side_effect = list(responses)
    return client


def test_direct_answer_produces_root_and_response():
    client = make_client(
        message([text_block("Paris.")], stop_reason="end_turn")
    )
    trace = run_traced(ResearchAgent, client, TOOL_IMPLS, "What is the capital of France?")

    types = [n.type for n in trace.nodes]
    assert types == [NODE_USER_INPUT, NODE_RESPONSE]
    assert trace.nodes[1].content == "Paris."
    assert trace.total_cost.input_tokens  == 5
    assert trace.total_cost.output_tokens == 3


def test_client_tool_flow_records_call_and_observation():
    client = make_client(
        message(
            [
                text_block("using echo"),
                tool_use_block("echo", {"msg": "hi"}),
            ],
            stop_reason="tool_use",
        ),
        message([text_block("done")], stop_reason="end_turn"),
    )
    trace = run_traced(ResearchAgent, client, TEST_TOOL_IMPLS, "q")

    types = [n.type for n in trace.nodes]
    assert types == [
        NODE_USER_INPUT,
        NODE_DECISION,
        NODE_TOOL_CALL,
        NODE_OBSERVATION,
        NODE_RESPONSE,
    ]

    root, decision, tool_call, observation, response = trace.nodes
    assert decision.parent_id    == root.id
    assert tool_call.parent_id   == decision.id
    assert observation.parent_id == tool_call.id
    assert response.parent_id    == root.id
    assert observation.content   == "echo: hi"


def test_server_web_search_is_instrumented_into_trace():
    """Anthropic's server web_search resolves in-response; the trace should
    still record a tool_call + observation under the decision."""
    stu = server_tool_use_block("web_search", {"query": "current AI news"}, id="stu_42")
    result = web_search_result_block(
        tool_use_id = "stu_42",
        results     = [
            search_result("Anthropic ships something", "https://example.com/a"),
            search_result("Second result",            "https://example.com/b"),
        ],
    )
    client = make_client(
        message(
            [stu, result, text_block("Summary of the news...")],
            stop_reason="end_turn",
        )
    )
    trace = run_traced(ResearchAgent, client, TOOL_IMPLS, "what's new?")

    types = [n.type for n in trace.nodes]
    assert types == [NODE_USER_INPUT, NODE_RESPONSE, NODE_TOOL_CALL, NODE_OBSERVATION]

    _, response, tool_call, observation = trace.nodes
    assert tool_call.parent_id          == response.id
    assert observation.parent_id        == tool_call.id
    assert tool_call.name               == "web_search"
    assert tool_call.metadata["server_tool"] is True
    assert "2 result(s)" in observation.content
    assert "https://example.com/a" in observation.content


def test_server_web_search_error_rendered_in_observation():
    stu   = server_tool_use_block("web_search", {"query": "x"}, id="stu_9")
    error = MagicMock()
    error.error_code = "max_uses_exceeded"
    result = web_search_result_block(tool_use_id="stu_9", results=error)
    client = make_client(
        message([stu, result, text_block("couldn't search")], stop_reason="end_turn")
    )
    trace = run_traced(ResearchAgent, client, TOOL_IMPLS, "q")

    observation = next(n for n in trace.nodes if n.type == NODE_OBSERVATION)
    assert observation.content == "error: max_uses_exceeded"


def test_agent_stops_at_max_turns():
    responses = [
        message(
            [tool_use_block("echo", {"msg": f"q{i}"}, id=f"tu_{i}")],
            stop_reason="tool_use",
        )
        for i in range(10)
    ]
    client = make_client(*responses)
    trace  = run_traced(
        agent_factory = lambda client, tool_runner: ResearchAgent(client, tool_runner, max_turns=3),
        raw_client    = client,
        tool_impls    = TEST_TOOL_IMPLS,
        question      = "loopy question",
    )

    assert any(n.type == NODE_RESPONSE and "max_turns" in n.content for n in trace.nodes)


def test_agent_run_returns_final_text_without_tracing():
    client = make_client(
        message([text_block("Paris.")], stop_reason="end_turn")
    )
    agent  = ResearchAgent(client, ToolRunner(TOOL_IMPLS))
    answer = agent.run("What is the capital of France?")

    assert answer == "Paris."


def test_latency_recorded_on_decision_and_observation():
    client = make_client(
        message(
            [
                text_block("using echo"),
                tool_use_block("echo", {"msg": "hi"}),
            ],
            stop_reason="tool_use",
        ),
        message([text_block("done")], stop_reason="end_turn"),
    )
    trace = run_traced(ResearchAgent, client, TEST_TOOL_IMPLS, "q?")

    by_type = {n.type: n for n in trace.nodes}
    assert by_type[NODE_DECISION].duration_ms is not None
    assert by_type[NODE_DECISION].duration_ms >= 0
    assert by_type[NODE_RESPONSE].duration_ms is not None
    assert by_type[NODE_OBSERVATION].duration_ms is not None
    assert by_type[NODE_OBSERVATION].duration_ms >= 0
    assert by_type[NODE_USER_INPUT].duration_ms is None
    assert by_type[NODE_TOOL_CALL].duration_ms is None
