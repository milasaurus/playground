"""Orchestration: wires the instrumentation layer around any agent.

`run_traced(agent_factory, raw_client, tool_impls, question)`:
  1. builds a `TracingContext` (holds the Tracer + root user_input node),
  2. wraps the raw client and a plain `ToolRunner` with instrumented versions,
  3. constructs the agent with those wrappers,
  4. runs it, and returns the finished `Trace`.

Agents that go through `run_traced` need no tracing vocabulary — they see a
normal client and tool runner, trace capture is a side effect.
"""

from typing import Callable, Protocol

import anthropic

from ..models import NODE_RESPONSE, Trace
from .client import InstrumentedClient
from .tool_runner import InstrumentedToolRunner, ToolImpls, ToolRunner
from .tracer import TracingContext


class MaxTurnsExceeded(RuntimeError):
    """Raised by an agent that hits its turn budget without a final response."""


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
    ctx    = TracingContext.start(question)
    client = InstrumentedClient(raw_client, ctx)
    runner = InstrumentedToolRunner(ToolRunner(tool_impls), ctx)
    agent  = agent_factory(client=client, tool_runner=runner)

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
