import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from agent_trace_debugger.models import (
    NODE_DECISION,
    NODE_OBSERVATION,
    NODE_TOOL_CALL,
    NODE_USER_INPUT,
    Trace,
    TraceCost,
    load_trace,
)
from agent_trace_debugger.services.tracer import Tracer


USER_Q = "What is the capital of France?"


def test_tracer_builds_parent_child_chain():
    t    = Tracer(USER_Q)
    root = t.add_node(NODE_USER_INPUT, "user", USER_Q)
    dec  = t.add_node(NODE_DECISION, "claude", "calling search", parent_id=root.id)
    call = t.add_node(NODE_TOOL_CALL, "web_search", "{\"query\":\"france\"}", parent_id=dec.id)
    obs  = t.add_node(NODE_OBSERVATION, "web_search", "Paris", parent_id=call.id)

    trace = t.end()
    assert trace.user_question == USER_Q
    assert len(trace.nodes) == 4
    assert trace.ended_at is not None
    assert root.parent_id is None
    assert obs.parent_id == call.id
    assert call.parent_id == dec.id


def test_tracer_sums_costs():
    t = Tracer(USER_Q)
    t.add_node(NODE_DECISION, "claude", "", cost=TraceCost(input_tokens=10, output_tokens=5, model="m"))
    t.add_node(NODE_DECISION, "claude", "", cost=TraceCost(input_tokens=3,  output_tokens=7, model="m"))
    trace = t.end()
    assert trace.total_cost.input_tokens  == 13
    assert trace.total_cost.output_tokens == 12
    assert trace.total_cost.total_tokens() == 25
    assert trace.total_cost.model == "m"


def test_trace_json_round_trip(tmp_path):
    t = Tracer(USER_Q)
    root = t.add_node(NODE_USER_INPUT, "user", USER_Q)
    t.add_node(NODE_DECISION, "claude", "answer",
               parent_id=root.id,
               cost=TraceCost(input_tokens=1, output_tokens=2, model="m"),
               duration_ms=123.4,
               metadata={"k": "v"})
    t.end()

    path = tmp_path / "trace.json"
    t.save(str(path))

    loaded = load_trace(str(path))
    assert isinstance(loaded, Trace)
    assert loaded.user_question == USER_Q
    assert len(loaded.nodes) == 2
    assert loaded.nodes[1].metadata == {"k": "v"}
    assert loaded.nodes[1].cost.input_tokens == 1
    assert loaded.nodes[1].duration_ms == 123.4
    assert loaded.total_cost.total_tokens() == 3


def test_trace_to_dict_is_json_serializable():
    t = Tracer(USER_Q)
    t.add_node(NODE_USER_INPUT, "user", USER_Q)
    trace = t.end()
    # Should not raise.
    json.dumps(trace.to_dict())


# ── TracingContext: interactive session helpers ──────────────────────────────

from agent_trace_debugger.services.tracer import TracingContext


def test_start_sets_current_user_input_to_root():
    ctx = TracingContext.start("hi")
    assert ctx.current_user_input_id == ctx.root.id


def test_start_session_uses_placeholder_root():
    ctx = TracingContext.start_session()
    assert ctx.root.type == NODE_USER_INPUT
    assert ctx.root.content == "(interactive session)"
    assert ctx.current_user_input_id == ctx.root.id


def test_start_new_user_input_adds_child_and_updates_current():
    ctx = TracingContext.start_session()
    first  = ctx.start_new_user_input("read agent.py")
    second = ctx.start_new_user_input("now refactor")

    assert first.parent_id  == ctx.root.id
    assert second.parent_id == ctx.root.id
    assert ctx.current_user_input_id == second.id  # tracks the most recent
