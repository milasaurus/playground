"""Run the interactive code-editing agent under tracing.

Behaves like `make coder` but captures every decision, tool call, and
observation as a trace. Type prompts as normal at the `You:` prompt;
press Ctrl-D when done. The session's trace is saved to disk on exit.

Usage:
    python code_editing_agent/traced_main.py
    python code_editing_agent/traced_main.py --no-cap
    python code_editing_agent/traced_main.py --save traces/run.json
    python code_editing_agent/traced_main.py --print

Open a saved trace later with the trace debugger:
    python agent_trace_debugger/main.py --load traces/<id>.json
"""

import argparse
import json
import os
import sys
import time
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from client import client
from agent_trace_debugger.models import NODE_OBSERVATION, NODE_TOOL_CALL
from agent_trace_debugger.services.client import InstrumentedClient
from agent_trace_debugger.services.tracer import TracingContext
from agent_trace_debugger.tui import print_trace

from agent import Agent
import tool_definitions as td
from tool_definitions import (
    Tool, ReadFileTool, ListFilesTool, EditFileTool, RunCommandTool,
)


class _TracingTool(Tool):
    """Wraps a Tool so each invocation records tool_call + observation nodes.

    Mirrors the inner tool's API surface (name, description, schema) so
    Claude sees an identical tool. Truncation is applied here too — the
    trace observation matches what the model actually sees.
    """

    def __init__(self, inner: Tool, ctx: TracingContext):
        super().__init__(
            name         = inner.name,
            description  = inner.description,
            input_schema = inner.input_schema,
        )
        self._inner = inner
        self._ctx   = ctx

    def run(self, params: dict) -> str:
        tool_call = self._ctx.tracer.add_node(
            type      = NODE_TOOL_CALL,
            name      = self.name,
            content   = json.dumps(params, indent=2),
            parent_id = self._ctx.current_decision_id,
        )
        started = time.perf_counter()
        try:
            observation = td.truncate_tool_output(self._inner.run(params))
        except Exception as e:
            elapsed = (time.perf_counter() - started) * 1000
            self._ctx.tracer.add_node(
                type        = NODE_OBSERVATION,
                name        = self.name,
                content     = f"error: {e}",
                parent_id   = tool_call.id,
                duration_ms = elapsed,
            )
            raise
        elapsed = (time.perf_counter() - started) * 1000
        self._ctx.tracer.add_node(
            type        = NODE_OBSERVATION,
            name        = self.name,
            content     = observation,
            parent_id   = tool_call.id,
            duration_ms = elapsed,
        )
        return observation


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Interactive code-editing agent under tracing.")
    p.add_argument("--save",   help="Save trace JSON to this path. Defaults to traces/<trace_id>.json.")
    p.add_argument("--print",  dest="print_tree", action="store_true",
                   help="Print a colour-coded tree to stdout after the session.")
    p.add_argument("--no-cap", action="store_true",
                   help="Disable tool-output truncation for this session.")
    return p.parse_args()


def make_get_user_message(ctx: TracingContext):
    """Read a prompt from stdin and record it as a new user_input node."""
    def get_user_message() -> tuple[str, bool]:
        try:
            msg = input()
        except (EOFError, KeyboardInterrupt):
            return "", False
        ctx.start_new_user_input(msg)
        return msg, True
    return get_user_message


def main() -> None:
    args = parse_args()

    if args.no_cap:
        td.MAX_OUTPUT_CHARS = 10**9

    ctx                 = TracingContext.start_session()
    instrumented_client = InstrumentedClient(client, ctx)
    raw_tools           = [ReadFileTool(), ListFilesTool(), EditFileTool(), RunCommandTool()]
    traced_tools        = [_TracingTool(t, ctx) for t in raw_tools]

    agent = Agent(instrumented_client, make_get_user_message(ctx), traced_tools)
    agent.run()

    trace     = ctx.finish()
    save_path = args.save or os.path.join("traces", f"{trace.id}.json")
    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
    with open(save_path, "w") as f:
        json.dump(trace.to_dict(), f, indent=2)
    print(f"\n✓ {len(trace.nodes)} nodes, {trace.total_cost.total_tokens()} tokens — saved → {save_path}")

    if args.print_tree:
        print()
        print_trace(trace)


if __name__ == "__main__":
    main()
