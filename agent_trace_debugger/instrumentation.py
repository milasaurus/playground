"""Instrumentation layer: wraps a Claude client and tool dispatcher with tracing.

An agent written against these wrappers emits a full `Trace` as a side effect
of doing plain Claude tool-use work. The agent itself has no tracing vocabulary
— it just calls `client.messages.create(...)` and `tool_runner.run(...)`.

Wiring lives in `run_traced`, which:
  1. builds a `TracingContext` (holds the Tracer + root user_input node),
  2. wraps the raw client and a plain `ToolRunner` with instrumented versions,
  3. constructs the agent with those wrappers,
  4. runs it, and returns the finished `Trace`.
"""

import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional, Protocol

import anthropic

from .trace import (
    NODE_DECISION,
    NODE_OBSERVATION,
    NODE_RESPONSE,
    NODE_TOOL_CALL,
    NODE_USER_INPUT,
    Trace,
    TraceCost,
    TraceNode,
    Tracer,
)


class MaxTurnsExceeded(RuntimeError):
    """Raised by an agent that hits its turn budget without a final response."""


@dataclass
class TracingContext:
    """Request-scoped tracer state.

    Tracks the root user_input and the most recently recorded decision so that
    tool_call nodes can hang off the correct parent.
    """
    tracer:              Tracer
    root:                TraceNode
    current_decision_id: Optional[str] = None

    @classmethod
    def start(cls, question: str) -> "TracingContext":
        tracer = Tracer(question)
        root   = tracer.add_node(NODE_USER_INPUT, "user", question)
        return cls(tracer=tracer, root=root)

    def finish(self) -> Trace:
        return self.tracer.end()


class _InstrumentedMessages:
    """Wraps `client.messages`. Records a decision or response node per create()."""

    def __init__(self, messages: Any, ctx: TracingContext):
        self._messages = messages
        self._ctx      = ctx

    def create(self, **kwargs: Any) -> Any:
        started = time.perf_counter()
        msg     = self._messages.create(**kwargs)
        elapsed = (time.perf_counter() - started) * 1000

        cost = TraceCost(
            input_tokens  = msg.usage.input_tokens,
            output_tokens = msg.usage.output_tokens,
            model         = msg.model,
        )
        text      = "\n".join(b.text for b in msg.content if b.type == "text").strip()
        is_final  = msg.stop_reason != "tool_use"
        node_type = NODE_RESPONSE if is_final else NODE_DECISION

        decision = self._ctx.tracer.add_node(
            type        = node_type,
            name        = "claude",
            content     = text or "(no text)",
            reasoning   = f"stop_reason={msg.stop_reason}",
            cost        = cost,
            duration_ms = elapsed,
            parent_id   = self._ctx.root.id,
        )
        self._ctx.current_decision_id = decision.id
        return msg


class InstrumentedClient:
    """Wraps `anthropic.Anthropic` so each model call emits a trace node."""

    def __init__(self, client: anthropic.Anthropic, ctx: TracingContext):
        self._client   = client
        self.messages  = _InstrumentedMessages(client.messages, ctx)


ToolImpls = dict[str, Callable[[dict[str, Any]], str]]


class ToolRunner:
    """Plain tool dispatcher: looks up by name and executes.

    Returns a string observation (or an error string if the tool is missing or
    raises). No tracing — swap for `InstrumentedToolRunner` to record nodes.
    """

    def __init__(self, impls: ToolImpls):
        self.impls = impls

    def run(self, name: str, input: dict[str, Any], tool_use_id: str) -> str:
        impl = self.impls.get(name)
        if impl is None:
            return f"error: unknown tool '{name}'"
        try:
            return impl(input)
        except Exception as e:
            return f"error: {e}"


class InstrumentedToolRunner:
    """Wraps a `ToolRunner`, recording tool_call + observation nodes per run()."""

    def __init__(self, inner: ToolRunner, ctx: TracingContext):
        self.inner = inner
        self.ctx   = ctx

    def run(self, name: str, input: dict[str, Any], tool_use_id: str) -> str:
        tool_call = self.ctx.tracer.add_node(
            type      = NODE_TOOL_CALL,
            name      = name,
            content   = json.dumps(input, indent=2),
            parent_id = self.ctx.current_decision_id,
            metadata  = {"tool_use_id": tool_use_id},
        )
        started     = time.perf_counter()
        observation = self.inner.run(name, input, tool_use_id)
        elapsed     = (time.perf_counter() - started) * 1000
        self.ctx.tracer.add_node(
            type        = NODE_OBSERVATION,
            name        = name,
            content     = observation,
            parent_id   = tool_call.id,
            duration_ms = elapsed,
        )
        return observation


class Agent(Protocol):
    """Any object with `run(question) -> str` works in `run_traced`.

    Constructor must accept `client` and `tool_runner` as keyword arguments.
    Tracing is a side effect of calling the instrumented deps — agents stay
    free of trace vocabulary.
    """

    def run(self, question: str) -> str: ...


AgentFactory = Callable[..., Agent]


def run_traced(
    agent_factory: AgentFactory,
    raw_client:    anthropic.Anthropic,
    tool_impls:    ToolImpls,
    question:      str,
) -> Trace:
    """Run an agent under instrumentation and return the captured trace.

    `agent_factory` is anything callable with (client=..., tool_runner=...) —
    pass the agent class directly if its constructor takes only those two, or
    a lambda if you need to bind other config (model, max_turns, ...).
    """
    ctx     = TracingContext.start(question)
    client  = InstrumentedClient(raw_client, ctx)
    runner  = InstrumentedToolRunner(ToolRunner(tool_impls), ctx)
    agent   = agent_factory(client=client, tool_runner=runner)

    try:
        agent.run(question)
    except MaxTurnsExceeded as e:
        ctx.tracer.add_node(
            type      = NODE_RESPONSE,
            name      = "claude",
            content   = f"(stopped: {e})",
            parent_id = ctx.root.id,
        )

    return ctx.finish()
