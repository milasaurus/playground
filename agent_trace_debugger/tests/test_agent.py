import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from agent_trace_debugger.agent import TOOL_IMPLS, ResearchAgent, mock_web_search
from agent_trace_debugger.instrumentation import run_traced
from agent_trace_debugger.trace import (
    NODE_DECISION,
    NODE_OBSERVATION,
    NODE_RESPONSE,
    NODE_TOOL_CALL,
    NODE_USER_INPUT,
)


MODEL = "mock-model"


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


def test_tool_use_flow_records_call_and_observation():
    client = make_client(
        message(
            [
                text_block("Let me search."),
                tool_use_block("web_search", {"query": "capital of France"}),
            ],
            stop_reason="tool_use",
        ),
        message([text_block("Paris.")], stop_reason="end_turn"),
    )
    trace = run_traced(ResearchAgent, client, TOOL_IMPLS, "What is the capital of France?")

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

    assert tool_call.name == "web_search"
    assert "france" in observation.content.lower()
    assert trace.total_cost.input_tokens == 10  # 5 + 5


def test_agent_stops_at_max_turns():
    # Agent keeps wanting to use tools forever.
    responses = [
        message(
            [tool_use_block("web_search", {"query": f"q{i}"}, id=f"tu_{i}")],
            stop_reason="tool_use",
        )
        for i in range(10)
    ]
    client = make_client(*responses)
    trace  = run_traced(
        agent_factory = lambda client, tool_runner: ResearchAgent(client, tool_runner, max_turns=3),
        raw_client    = client,
        tool_impls    = TOOL_IMPLS,
        question      = "loopy question",
    )

    # Should have hit max_turns and added a synthetic response note.
    assert any(n.type == NODE_RESPONSE and "max_turns" in n.content for n in trace.nodes)


def test_agent_run_returns_final_text_without_tracing():
    """ResearchAgent works with plain (un-instrumented) deps and returns text."""
    from agent_trace_debugger.instrumentation import ToolRunner

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
                text_block("searching"),
                tool_use_block("web_search", {"query": "capital of France"}),
            ],
            stop_reason="tool_use",
        ),
        message([text_block("Paris.")], stop_reason="end_turn"),
    )
    trace = run_traced(ResearchAgent, client, TOOL_IMPLS, "q?")

    by_type = {n.type: n for n in trace.nodes}
    # Model calls get latency.
    assert by_type[NODE_DECISION].duration_ms is not None
    assert by_type[NODE_DECISION].duration_ms >= 0
    assert by_type[NODE_RESPONSE].duration_ms is not None
    # Tool execution latency lands on the observation node.
    assert by_type[NODE_OBSERVATION].duration_ms is not None
    assert by_type[NODE_OBSERVATION].duration_ms >= 0
    # Request-side nodes don't carry latency.
    assert by_type[NODE_USER_INPUT].duration_ms is None
    assert by_type[NODE_TOOL_CALL].duration_ms is None


def test_mock_web_search_deterministic():
    assert "Paris" in mock_web_search("capital of France")
    assert "Tokyo" in mock_web_search("capital of Japan")
    assert "Everest" in mock_web_search("tallest mountain")
    assert "No high-confidence" in mock_web_search("something obscure")
