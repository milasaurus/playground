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

## AFK Mode

AFK Mode lets you hand a task to the coding agent and walk away — no supervision required. The agent works autonomously, resolves ambiguity on its own, runs the test suite, and leaves a written summary for you to review when you return.

### How it works

- **High autonomy** — the agent reads code, runs commands, makes edits, and self-corrects without asking for confirmation on every step.
- **Low interruption** — it only escalates when genuinely blocked (conflicting requirements, missing secrets, destructive operations with no safe default). Shallow ambiguity (naming, style, library choice) is resolved independently with a note in the final summary.
- **Test-gated** — before declaring work done the agent runs `make test` and reports pass/fail. If tests fail it attempts to fix them; unresolved failures are listed explicitly.
- **Documented handoff** — the final response summarises what was done, what assumptions were made, and any follow-ups the engineer may want to address.

### Enabling AFK Mode

AFK Mode is a prompt-level instruction — no code changes or environment variables are needed.

1. **Open a Claude session** (claude.ai/code or the API).
2. **Paste the AFK Mode system prompt** at the start of your conversation (or configure it as the system prompt in your API call):

   > *You are a coding agent operating in AFK Mode. [full AFK Mode instructions…]*

3. **Give your task** as the first human message, then step away. Claude will work through the task, run `make test`, and post a final summary.

#### Quick-start via the API

```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-opus-4-5",
    max_tokens=8096,
    system=(
        "You are a coding agent operating in AFK Mode. "
        "Work autonomously, resolve shallow ambiguity independently, "
        "run the repo's test suite before finishing, and post a plain-text "
        "summary of what you did, what you assumed, and any follow-ups."
    ),
    messages=[
        {"role": "user", "content": "Refactor the retry logic in code_editing_agent/agent.py and make sure all tests pass."}
    ],
)
print(response.content[0].text)
```

#### Via `claude.ai/code`

1. Go to **claude.ai/code** and open (or create) a project.
2. In **Project instructions**, paste the AFK Mode system prompt.
3. Type your task in the chat and close the tab — the agent will keep working.

### When to use AFK Mode vs. interactive mode

| Situation | Recommended mode |
|---|---|
| Well-defined task you can describe in a sentence or two | AFK Mode |
| You need to review design decisions as they're made | Interactive |
| Running the test suite validates the outcome automatically | AFK Mode |
| The task requires frequent back-and-forth clarification | Interactive |
| You're away from your desk or on a small screen | AFK Mode |
| Exploratory / research work where direction may shift | Interactive |
