"""Active trace builder + request-scoped context.

`Tracer` is the append-only collector agents (and the instrumentation layer)
call to record events. `TracingContext` holds per-run state: the tracer, the
root `user_input` node, and a pointer to the most recent decision so tool
nodes hang off the right parent.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from ..models import NODE_USER_INPUT, Trace, TraceCost, TraceNode


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return uuid4().hex[:8]


class Tracer:
    """Collects nodes as the agent runs.

    Callers invoke `add_node(...)` at each event. `parent_id` is whatever the
    caller decides — usually the id of the Claude message that produced the
    child (tool_call -> observation), or the root user_input for top-level
    decisions.
    """

    def __init__(self, user_question: str):
        self.trace = Trace(
            id            = _new_id(),
            user_question = user_question,
            started_at    = _now(),
        )

    def add_node(
        self,
        type:        str,
        name:        str,
        content:     str                 = "",
        parent_id:   Optional[str]       = None,
        reasoning:   Optional[str]       = None,
        cost:        Optional[TraceCost] = None,
        duration_ms: Optional[float]     = None,
        metadata:    Optional[dict]      = None,
    ) -> TraceNode:
        node = TraceNode(
            id          = _new_id(),
            parent_id   = parent_id,
            type        = type,
            name        = name,
            timestamp   = _now(),
            content     = content,
            reasoning   = reasoning,
            cost        = cost,
            duration_ms = duration_ms,
            metadata    = metadata or {},
        )
        self.trace.nodes.append(node)
        if cost is not None:
            self.trace.total_cost.add(cost)
        return node

    def end(self) -> Trace:
        self.trace.ended_at = _now()
        return self.trace

    def save(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump(self.trace.to_dict(), f, indent=2)


@dataclass
class TracingContext:
    """Request-scoped tracer state.

    Tracks three handles into the trace:
    - `root` — the trace's root user_input node.
    - `current_user_input_id` — the most recent user_input. Decisions hang
      off this so multi-prompt sessions render cleanly under the right
      branch. For single-shot runs (`start(question)`) it equals `root.id`,
      so the existing behaviour is unchanged.
    - `current_decision_id` — the most recent decision. tool_call nodes
      hang off this.
    """
    tracer:                Tracer
    root:                  TraceNode
    current_decision_id:   Optional[str] = None
    current_user_input_id: Optional[str] = None

    @classmethod
    def start(cls, question: str) -> "TracingContext":
        tracer = Tracer(question)
        root   = tracer.add_node(NODE_USER_INPUT, "user", question)
        return cls(tracer=tracer, root=root, current_user_input_id=root.id)

    @classmethod
    def start_session(cls, placeholder: str = "(interactive session)") -> "TracingContext":
        """Like `start` but for sessions where prompts arrive over time.

        Creates a placeholder root user_input so the trace has a top-level
        anchor. Add real prompts with `start_new_user_input(content)` as
        they arrive — each becomes a child of the placeholder root, and
        decisions attach to the most recent prompt.
        """
        tracer = Tracer(placeholder)
        root   = tracer.add_node(NODE_USER_INPUT, "session", placeholder)
        return cls(tracer=tracer, root=root, current_user_input_id=root.id)

    def start_new_user_input(self, content: str) -> TraceNode:
        """Record a new user prompt and make it the parent for subsequent decisions."""
        node = self.tracer.add_node(NODE_USER_INPUT, "user", content, parent_id=self.root.id)
        self.current_user_input_id = node.id
        return node

    def finish(self) -> Trace:
        return self.tracer.end()
