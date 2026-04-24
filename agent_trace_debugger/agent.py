"""Research agent — plain Claude tool-use loop, no tracing vocabulary.

The agent calls `client.messages.create(...)` and `tool_runner.run(...)`.
Pass the raw `anthropic.Anthropic` client and a plain `ToolRunner` for an
un-traced run; pass `InstrumentedClient` / `InstrumentedToolRunner` (via
`run_traced`) to capture a full `Trace`.
"""

from typing import Any

from .services.agent_runner import MaxTurnsExceeded


DEFAULT_MODEL      = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 1024

SYSTEM_PROMPT = (
    "You are a concise research assistant. Answer from your own knowledge "
    "when possible. Call `web_search` when the question requires up-to-date "
    "information (news, recent events, live data) or a specific fact you "
    "genuinely do not know. When you use search results, cite the source URL "
    "inline. Keep responses brief."
)

# Anthropic's server-side web search tool. The search runs on Anthropic's
# infrastructure; results arrive in the same response as `server_tool_use` /
# `web_search_tool_result` content blocks — no client-side implementation
# needed, and `TOOL_IMPLS` stays empty.
TOOL_DEFS = [
    {"type": "web_search_20250305", "name": "web_search", "max_uses": 5},
]

TOOL_IMPLS: dict[str, Any] = {}


class ResearchAgent:
    """Claude tool-use loop. Returns the final assistant text.

    Dependencies are injected so the same agent runs traced or un-traced:
    - `client`       — anything with `.messages.create(**kwargs)` → message
    - `tool_runner`  — anything with `.run(name, input, tool_use_id)` → str
    """

    def __init__(
        self,
        client:      Any,
        tool_runner: Any,
        model:       str = DEFAULT_MODEL,
        max_tokens:  int = DEFAULT_MAX_TOKENS,
        max_turns:   int = 10,
    ):
        self.client      = client
        self.tool_runner = tool_runner
        self.model       = model
        self.max_tokens  = max_tokens
        self.max_turns   = max_turns

    def run(self, question: str) -> str:
        conversation: list[dict[str, Any]] = [{"role": "user", "content": question}]

        for _ in range(self.max_turns):
            msg = self.client.messages.create(
                model      = self.model,
                max_tokens = self.max_tokens,
                system     = SYSTEM_PROMPT,
                tools      = TOOL_DEFS,
                messages   = conversation,
            )
            conversation.append({"role": "assistant", "content": msg.content})

            if msg.stop_reason != "tool_use":
                return "\n".join(b.text for b in msg.content if b.type == "text").strip()

            tool_results = []
            for block in msg.content:
                if block.type != "tool_use":
                    continue
                observation = self.tool_runner.run(block.name, block.input, block.id)
                tool_results.append({
                    "type":        "tool_result",
                    "tool_use_id": block.id,
                    "content":     observation,
                })
            conversation.append({"role": "user", "content": tool_results})

        raise MaxTurnsExceeded(f"hit max_turns={self.max_turns}")
