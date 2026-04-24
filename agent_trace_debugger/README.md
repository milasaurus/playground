# Agent Trace Debugger

An auto-instrumented Claude agent + terminal TUI that captures every decision,
tool call, and observation into a structured trace. Built for agent observability: 
the kind of tool you wish existed the first time an agent did something weird in production.

## What it does

1. Runs a small **research agent** (Claude + mock `web_search` tool).
2. **Auto-instruments** each turn — every Claude call becomes a `decision` or
   `response` node; every `tool_use` block becomes a `tool_call` node with its
   result as a child `observation`.
3. Opens an interactive **Textual TUI** by default — expand/collapse, arrow-key
   navigation, per-node detail panel, token totals in the header. Pass
   `--print` for a colour-coded tree on stdout (pipes / non-TTY).

<img width="1083" height="554" alt="image" src="https://github.com/user-attachments/assets/73042e81-7ad1-481f-94b4-7fedccaea9cc" />

## Trace shape

```
user_input (root)
└── decision / response       (one per Claude call; response = end_turn)
    └── tool_call             (one per tool_use block)
        └── observation       (tool result)
```

Each node carries: `id`, `parent_id`, `type`, `name`, `timestamp`, `content`,
`reasoning`, `cost` (per-call tokens + model), and free-form `metadata`.

## Files

| File                 | Purpose                                                            |
| -------------------- | ------------------------------------------------------------------ |
| `trace.py`           | `Trace`, `TraceNode`, `TraceCost`, `Tracer`, JSON IO               |
| `instrumentation.py` | `InstrumentedClient`, `ToolRunner`, `run_traced`, `Agent` protocol |
| `agent.py`           | `ResearchAgent` — plain Claude tool-use loop, no trace vocabulary  |
| `tui.py`             | Textual `TraceApp` — tree + detail panel, color-coded types        |
| `main.py`            | CLI entry point                                                    |
| `tests/`             | `pytest` tests for trace structure and agent flow (mocked)         |

## Run it

From the repo root:

```bash
make setup                                   # first time only (installs textual)
make debugger Q="What's the capital of France?"
```

Or directly:

```bash
source venv/bin/activate
python -m agent_trace_debugger.main "What's the capital of France?"
```

### Flags

```bash
# Default: run agent, launch the interactive Textual TUI.
python -m agent_trace_debugger.main "Tell me about Everest."

# Print a colour-coded tree to stdout instead (non-TTY / pipes).
python -m agent_trace_debugger.main --print "..."
```

### Keybindings (TUI)

| Key | Action         |
| --- | -------------- |
| `q` | Quit           |
| `e` | Expand all     |
| `c` | Collapse all   |
| `↑↓` | Navigate tree |
| `←→` | Collapse / expand |
| `Enter` | Select node |

## Testing

```bash
make test-debugger
```

All tests use a mocked Anthropic client — they never call the real API.

## Plugging in your own agent

Any class with `run(question: str) -> str` whose constructor accepts `client`
and `tool_runner` as kwargs works:

```python
from agent_trace_debugger.instrumentation import run_traced

class MyAgent:
    def __init__(self, client, tool_runner):
        self.client = client
        self.tool_runner = tool_runner

    def run(self, question: str) -> str:
        msg = self.client.messages.create(model=..., messages=[...], tools=[...])
        # ... your loop ...
        return final_text

trace = run_traced(MyAgent, raw_client, tool_impls, "your question")
```

`run_traced` wraps the client and tool dispatcher with instrumented versions.
The agent writes plain Claude code — the trace is a side effect.

## Design notes (for future-me / interviewers)

- **Zero tracing vocabulary in agent code.** `InstrumentedClient` wraps
  `client.messages.create` and emits decision/response nodes; `InstrumentedToolRunner`
  wraps tool dispatch and emits tool_call/observation nodes. The agent only sees
  a normal Claude client and a tool runner — swap them for plain versions and
  it runs un-traced without any code change.
- **Tree via `parent_id`, not nested structs.** Keeps JSON flat, diff-friendly,
  and streamable — append-only writes would work unchanged for real-time
  capture.
- **Cost at the node level.** Aggregation is trivial (`total_cost.add`), and
  per-node cost is what you actually want when hunting the turn that burned
  your budget.
- **What's not here yet.** Streaming capture, multi-agent correlation,
  hallucination/validation checks, replay-with-diff. All fit the current
  schema — none are load-bearing for the MVP.
