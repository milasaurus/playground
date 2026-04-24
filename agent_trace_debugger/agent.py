"""Research agent — plain Claude tool-use loop, no tracing vocabulary.

The agent calls `client.messages.create(...)` and `tool_runner.run(...)`.
Pass the raw `anthropic.Anthropic` client and a plain `ToolRunner` for an
un-traced run; pass `InstrumentedClient` / `InstrumentedToolRunner` (via
`run_traced`) to capture a full `Trace`.
"""

from typing import Any

from .instrumentation import MaxTurnsExceeded


DEFAULT_MODEL      = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 1024

SYSTEM_PROMPT = (
    "You are a concise research assistant. Only call `web_search` when you "
    "are uncertain about a specific fact or the question requires up-to-date "
    "information. For common knowledge, answer directly without calling "
    "tools. Keep responses brief."
)

TOOL_DEFS = [
    {
        "name": "web_search",
        "description": "Search the web for information on a topic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query."},
            },
            "required": ["query"],
        },
    },
]


def mock_web_search(query: str) -> str:
    """Deterministic mock so the demo is reproducible offline.

    TODO: swap for Claude's built-in web_search server tool. For now we test
    against pre-canned questions (France, Japan, Everest) so runs stay offline
    and deterministic.
    """
    q = query.lower()
    if "france" in q and "capital" in q:
        return "Paris is the capital of France. Population ~2.1M (city proper)."
    if "capital" in q and "japan" in q:
        return "Tokyo is the capital of Japan. Population ~13.9M."
    if "tallest mountain" in q or "everest" in q:
        return "Mount Everest, 8,848.86 m, on the Nepal-China border."
    return f"No high-confidence results for: '{query}'."


TOOL_IMPLS = {
    "web_search": lambda i: mock_web_search(i["query"]),
}


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
