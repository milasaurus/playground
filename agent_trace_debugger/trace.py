"""Trace data structures and a Tracer helper for capturing agent execution.

Design goals:
- One node per discrete event (user_input, decision, tool_call, observation, response).
- Parent-child via `parent_id` so the TUI can render a tree without a second pass.
- Everything JSON-serializable so traces can be saved, diffed, and replayed.
"""

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


# Node types — the TUI color-codes on these.
NODE_USER_INPUT  = "user_input"
NODE_DECISION    = "decision"
NODE_TOOL_CALL   = "tool_call"
NODE_OBSERVATION = "observation"
NODE_RESPONSE    = "response"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


@dataclass
class TraceCost:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    model: str = ""

    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read_input_tokens
            + self.cache_creation_input_tokens
        )

    def add(self, other: "TraceCost") -> None:
        self.input_tokens                += other.input_tokens
        self.output_tokens               += other.output_tokens
        self.cache_read_input_tokens     += other.cache_read_input_tokens
        self.cache_creation_input_tokens += other.cache_creation_input_tokens
        if not self.model and other.model:
            self.model = other.model


@dataclass
class TraceNode:
    id:          str
    parent_id:   Optional[str]
    type:        str
    name:        str
    timestamp:   str
    content:     str                         = ""
    reasoning:   Optional[str]               = None
    cost:        Optional[TraceCost]         = None
    duration_ms: Optional[float]             = None
    metadata:    dict[str, Any]              = field(default_factory=dict)


@dataclass
class Trace:
    id:            str
    user_question: str
    started_at:    str
    ended_at:      Optional[str]         = None
    nodes:         list[TraceNode]       = field(default_factory=list)
    total_cost:    TraceCost             = field(default_factory=TraceCost)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Trace":
        nodes = [
            TraceNode(
                **{**n, "cost": TraceCost(**n["cost"]) if n.get("cost") else None}
            )
            for n in data.get("nodes", [])
        ]
        total = TraceCost(**data["total_cost"]) if data.get("total_cost") else TraceCost()
        return cls(
            id            = data["id"],
            user_question = data["user_question"],
            started_at    = data["started_at"],
            ended_at      = data.get("ended_at"),
            nodes         = nodes,
            total_cost    = total,
        )


class Tracer:
    """Collects nodes as the agent runs.

    The agent calls `add_node(...)` at each event. `parent_id` is whatever the
    agent decides — usually the id of the Claude message that produced the child
    (for tool_call -> observation), or the root user_input (for top-level decisions).
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
        content:     str                    = "",
        parent_id:   Optional[str]          = None,
        reasoning:   Optional[str]          = None,
        cost:        Optional[TraceCost]    = None,
        duration_ms: Optional[float]        = None,
        metadata:    Optional[dict]         = None,
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


def load_trace(path: str) -> Trace:
    with open(path) as f:
        return Trace.from_dict(json.load(f))
