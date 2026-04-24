"""Trace data structures.

Pure data — no behaviour beyond JSON round-trip and a tiny cost aggregator.
Everything here is JSON-serialisable so traces can be saved, diffed, and
replayed. See `services.tracer.Tracer` for the active builder.
"""

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Optional


# Node types — the TUI color-codes on these.
NODE_USER_INPUT  = "user_input"
NODE_DECISION    = "decision"
NODE_TOOL_CALL   = "tool_call"
NODE_OBSERVATION = "observation"
NODE_RESPONSE    = "response"


@dataclass
class TraceCost:
    """Per-call token accounting for a single message."""
    input_tokens:                int = 0    # prompt tokens sent to Claude this call
    output_tokens:               int = 0    # tokens Claude generated in the response
    cache_read_input_tokens:     int = 0    # prompt tokens served from Anthropic's prompt cache (~90% cheaper)
    cache_creation_input_tokens: int = 0    # prompt tokens written to the cache on first use (~25% more expensive)
    model:                       str = ""   # model id that produced this response (e.g. "claude-sonnet-4-6")

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
    """One event in the trace tree.

    Everything the agent does — receiving the question, every Claude call,
    every tool invocation, every tool result — lands as a `TraceNode`. Nodes
    form a tree via `parent_id`; the TUI and stdout renderer walk that tree
    to display the run.
    """
    id:          str                                     # short hex id, unique within the trace
    parent_id:   Optional[str]                           # id of the parent node; None for the root user_input
    type:        str                                     # one of the NODE_* constants above
    name:        str                                     # human-readable label ("claude", tool name, "user", ...)
    timestamp:   str                                     # ISO-8601 UTC timestamp when the node was recorded
    content:     str                 = ""                # the payload (question text, tool input JSON, observation body, final answer)
    reasoning:   Optional[str]       = None              # model-call metadata like `stop_reason=tool_use`
    cost:        Optional[TraceCost] = None              # token accounting — only set on decision/response nodes
    duration_ms: Optional[float]     = None              # wall-clock latency of the work this node represents (model call or tool exec)
    metadata:    dict[str, Any]      = field(default_factory=dict)  # free-form extras (tool_use_id, server_tool flag, future annotation tags, ...)


@dataclass
class Trace:
    """Complete record of a single agent run.

    The nodes list is flat and append-only — the tree structure lives in
    each node's `parent_id`. Serialises to JSON via `to_dict` / `from_dict`
    and round-trips through `Tracer.save` and `load_trace`.
    """
    id:            str                                                 # short hex id for this run
    user_question: str                                                 # the original question that kicked off the run
    started_at:    str                                                 # ISO-8601 UTC when the tracer was created
    ended_at:      Optional[str]   = None                              # ISO-8601 UTC when Tracer.end() was called; None if the run crashed
    nodes:         list[TraceNode] = field(default_factory=list)       # every event in order of emission (not traversal order)
    total_cost:    TraceCost       = field(default_factory=TraceCost)  # running sum of every node's cost, maintained by Tracer.add_node

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


def load_trace(path: str) -> Trace:
    with open(path) as f:
        return Trace.from_dict(json.load(f))
