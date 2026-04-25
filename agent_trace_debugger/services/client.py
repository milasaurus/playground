"""Anthropic client wrapper.

`InstrumentedClient` wraps `anthropic.Anthropic` so every `messages.create`
call emits a `decision`/`response` trace node with cost + latency, and
server-side tool activity (e.g. the built-in `web_search_20250305`) is
threaded into the trace as `tool_call` + `observation` nodes — the same
shape client-side tools produce via `InstrumentedToolRunner`.
"""

import json
import time
from typing import Any, Optional

import anthropic

from ..models import (
    NODE_DECISION,
    NODE_OBSERVATION,
    NODE_RESPONSE,
    NODE_TOOL_CALL,
    TraceCost,
)
from .tracer import TracingContext


class _InstrumentedMessages:
    """Wraps `client.messages`. Records a decision/response node per call,
    whether the agent uses `.create(...)` or the streaming `.stream(...)`.
    """

    def __init__(self, messages: Any, ctx: TracingContext):
        self._messages = messages
        self._ctx      = ctx

    def create(self, **kwargs: Any) -> Any:
        started = time.perf_counter()
        msg     = self._messages.create(**kwargs)
        elapsed = (time.perf_counter() - started) * 1000
        _record_decision_node(self._ctx, msg, elapsed)
        return msg

    def stream(self, **kwargs: Any) -> "_InstrumentedStream":
        return _InstrumentedStream(self._messages.stream(**kwargs), self._ctx)


class _InstrumentedStream:
    """Wraps `messages.stream(...)` so the final message records a decision.

    Mirrors the bits of the Anthropic stream API the existing agents use:
    the context-manager protocol, the `text_stream` iterator, and
    `get_final_message()`. The decision node is emitted when
    `get_final_message()` is called, so streamed and non-streamed runs
    produce the same trace shape.
    """

    def __init__(self, inner_cm: Any, ctx: TracingContext):
        self._cm      = inner_cm
        self._ctx     = ctx
        self._inner   = None
        self._started = None

    def __enter__(self):
        self._inner   = self._cm.__enter__()
        self._started = time.perf_counter()
        return self

    def __exit__(self, *exc):
        return self._cm.__exit__(*exc)

    @property
    def text_stream(self):
        return self._inner.text_stream

    def get_final_message(self):
        msg     = self._inner.get_final_message()
        elapsed = (time.perf_counter() - self._started) * 1000
        _record_decision_node(self._ctx, msg, elapsed)
        return msg


class InstrumentedClient:
    """Wraps `anthropic.Anthropic` so each model call emits a trace node."""

    def __init__(self, client: anthropic.Anthropic, ctx: TracingContext):
        self._client  = client
        self.messages = _InstrumentedMessages(client.messages, ctx)


def _record_decision_node(ctx: TracingContext, msg: Any, elapsed_ms: float) -> None:
    cost = TraceCost(
        input_tokens  = msg.usage.input_tokens,
        output_tokens = msg.usage.output_tokens,
        model         = msg.model,
    )
    text      = "\n".join(b.text for b in msg.content if b.type == "text").strip()
    is_final  = msg.stop_reason != "tool_use"
    node_type = NODE_RESPONSE if is_final else NODE_DECISION

    decision = ctx.tracer.add_node(
        type        = node_type,
        name        = "claude",
        content     = text or "(no text)",
        reasoning   = f"stop_reason={msg.stop_reason}",
        cost        = cost,
        duration_ms = elapsed_ms,
        parent_id   = ctx.current_user_input_id,
    )
    ctx.current_decision_id = decision.id
    _record_server_tool_blocks(ctx, msg.content, decision.id)


def _block_type(block: Any) -> Optional[str]:
    return getattr(block, "type", None)


def _record_server_tool_blocks(ctx: TracingContext, content: Any, decision_id: str) -> None:
    """Emit tool_call + observation nodes for Anthropic server-tool usage.

    Server tools (e.g. `web_search_20250305`) are resolved by Anthropic before
    the response returns — the content contains matched `server_tool_use` and
    `web_search_tool_result` blocks. We thread them into the same tool_call ->
    observation shape as client-side tools so the trace stays uniform.
    """
    uses = {b.id: b for b in content if _block_type(b) == "server_tool_use"}
    for b in content:
        if _block_type(b) != "web_search_tool_result":
            continue
        use = uses.get(getattr(b, "tool_use_id", None))
        if use is None:
            continue
        tool_call = ctx.tracer.add_node(
            type      = NODE_TOOL_CALL,
            name      = use.name,
            content   = json.dumps(use.input, indent=2),
            parent_id = decision_id,
            metadata  = {"tool_use_id": use.id, "server_tool": True},
        )
        ctx.tracer.add_node(
            type      = NODE_OBSERVATION,
            name      = use.name,
            content   = _format_web_search_content(b.content),
            parent_id = tool_call.id,
        )


def _format_web_search_content(content: Any) -> str:
    """Render a web_search_tool_result content block for the observation node."""
    if getattr(content, "error_code", None):
        return f"error: {content.error_code}"
    try:
        items = list(content)
    except TypeError:
        return str(content)
    if not items:
        return "(no results)"
    lines = [f"{len(items)} result(s):"]
    for r in items:
        title = getattr(r, "title", None) or "(untitled)"
        url   = getattr(r, "url", None)   or "(no url)"
        lines.append(f"- {title} — {url}")
    return "\n".join(lines)
