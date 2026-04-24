"""Tool dispatch + tracing wrapper.

`ToolRunner` is a plain dispatcher: given a name, look up the implementation
and execute it. `InstrumentedToolRunner` wraps a `ToolRunner` and records
`tool_call` + `observation` nodes with execution latency.

Agents call `.run(name, input, tool_use_id)` on whichever runner they're
handed; the trace is a side effect when the instrumented variant is used.
"""

import json
import time
from typing import Any, Callable

from ..models import NODE_OBSERVATION, NODE_TOOL_CALL
from .tracer import TracingContext


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
