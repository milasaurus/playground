# Playground

A collection of projects exploring agentic workflows with the Anthropic Python SDK.

## Projects

| Directory | Description |
|-----------|-------------|
| `claude_conversation_engine/` | Terminal chat with Claude using streaming, history tracking, and token usage reporting |
| `claude_prompt_eval/` | Auto generate test cases for a prompt, run them, and grade responses using Claude |
| `code_editing_agent/` | Terminal based agent that gives Claude tools to read, list, and edit files |
| `property_management_agent/` | Agentic tool-calling system that manages inbox, calendar, and property listings for a real estate solopreneur |
| `agent_trace_debugger/` | Auto-instrumented Claude agent + Textual TUI that captures and visualises decisions, tool calls, and observations |

## Getting Started

Dependencies are managed with [uv](https://docs.astral.sh/uv/). Install it first (`brew install uv` or see the uv docs), then:

```bash
git clone https://github.com/milasaurus/playground.git
cd playground
make setup        # uv sync — creates .venv/ and resolves uv.lock
```

`make setup` also installs `property_management_agent`'s separate uv project. The `make` targets all run through `uv run`, so you don't need to activate a venv manually.

Create a `.env` file in the project root with your Anthropic API key:

```bash
ANTHROPIC_API_KEY=your-api-key-here
```

## Commands

```bash
make chat                  # Run the conversation engine
make prompt                # Run prompt eval
make prompt-verbose        # Run prompt eval with full response details
make coder                 # Run the code-editing agent
make property-agent        # Run the property management agent
make debugger Q="..."      # Run the agent trace debugger on a question
make test                  # Run all tests
```

## AFK Mode

AFK Mode is a workflow pattern for running coding agents while you're away from your desk — in a meeting, commuting, or otherwise unavailable to supervise.

### How it works

Instead of watching every step of an agent run interactively, you hand the agent a well-defined task and let it work autonomously until it produces a reviewable result (typically a passing test suite and a diff). When you return, you review what it produced rather than what it's currently doing.

### Principles

| Principle | What it means in practice |
|---|---|
| **High bar for asking questions** | The agent makes reasonable assumptions on shallow ambiguity and documents them. It only halts for deep conflicts or missing context that would produce materially wrong work. |
| **Self-resolve where possible** | Read the code, run the tests, check existing patterns before surfacing a question. |
| **Most reversible path** | When two approaches are equally valid, prefer the one that's easier to undo. |
| **Green tests before done** | The agent runs the repo's canonical test command (`make test`) and captures pass/fail output before declaring the task complete. |
| **Halt cleanly when truly blocked** | If a required file is missing, requirements conflict, or an environment problem prevents progress, the agent stops and reports exactly what it tried and what it needs. |

### Good tasks for AFK Mode

- Adding a new feature with clear acceptance criteria
- Writing or extending tests for an existing module
- Refactoring a file to match an established pattern elsewhere in the repo
- Updating documentation to reflect recent code changes
- Fixing a well-described bug with a reproducible test case

### Less suitable tasks

- Exploratory spikes where the right direction is genuinely unknown
- Tasks that require human judgement calls mid-run (e.g. "pick whichever design you prefer" on a high-stakes interface)
- Anything requiring credentials or environment access the agent doesn't already have

### Running an AFK session in this repo

1. Launch the agent with a specific, scoped task.
2. The agent works, runs `make test`, and documents assumptions in its final response.
3. You return, read the summary, review the diff, and merge or iterate.

## Observability and Tracing

Two complementary observability surfaces are available for projects in this repo. They serve different purposes and can run independently or together.

### Local trace debugger (`agent_trace_debugger/`)

A self-contained tracer plus Textual TUI for **local debugging**. Captures decisions, tool calls, and observations as a tree of nodes, writes them to a JSON file per session, and renders them interactively in the terminal. Best when you want to step through a single agent run, inspect token-level cost, or compare prompts side by side without leaving the machine.

Used today by:
- `make coder-traced` — runs the code-editing agent under tracing and saves to `traces/<id>.json`.
- `make debugger Q="..."` — answers a single question and renders the trace inline.

No external service or credentials required — it's all local files plus a terminal UI.

### Langfuse (cloud observability)

Cloud-side tracing via [Langfuse](https://langfuse.com). Every Anthropic API call is captured as a generation with model name and token usage; multi-step flows get nested spans; sessions group multi-turn conversations. Best when you want **dashboards, filtering across many sessions, cost analytics, or shared traces with a team**.

Wiring lives in `observability.py` at the repo root and is shared by every project. Tracing is **opt-in** — if env vars are not set, projects run untraced and the helpers are no-ops.

To enable for any project:

1. Get keys from your Langfuse project: Settings → API Keys.
2. Add to `.env`:
   ```bash
   LANGFUSE_PUBLIC_KEY=pk-lf-...
   LANGFUSE_SECRET_KEY=sk-lf-...
   LANGFUSE_HOST=https://cloud.langfuse.com           # or https://us.cloud.langfuse.com
   ```
3. The project's entry point must call `setup_langfuse()` before constructing the Anthropic client, and `flush()` before exit. See `CLAUDE.md` "Observability" for the standard pattern.

Reference implementation: `code_editing_agent/agent.py` (`make coder` is Langfuse-traced when keys are set). Once enabled, traces appear in your Langfuse UI — see [Langfuse docs](https://langfuse.com/docs) for navigation.

### When to use which

| Need | Use |
|---|---|
| Step through a single run interactively | Local trace debugger |
| Compare two prompt versions on one question | Local trace debugger |
| Shared dashboard across many sessions | Langfuse |
| Cost / latency analytics over time | Langfuse |
| Filter traces by user, session, or tag | Langfuse |
| Quick local debugging with no external deps | Local trace debugger |
| Both at once on a single run | Wire both into the entry point |
