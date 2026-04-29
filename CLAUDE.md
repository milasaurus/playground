# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
make setup              # uv sync — creates .venv/ and resolves uv.lock
make test               # Run all tests
make test-chat          # Run conversation engine tests only
make test-eval          # Run prompt eval tests only
make chat               # Run the conversation engine (interactive)
make prompt             # Run prompt eval (interactive)
make prompt-verbose     # Run prompt eval with full response details
```

Dependencies are managed with [uv](https://docs.astral.sh/uv/). The root `pyproject.toml` covers `claude_conversation_engine`, `claude_prompt_eval`, `code_editing_agent`, and `agent_trace_debugger`. `property_management_agent/` has its own pyproject and uv.lock.

Run a single test file (uv resolves the env automatically — no activation needed):
```bash
uv run python -m pytest claude_prompt_eval/tests/test_grader.py -v
```

Add a dependency to the shared projects:
```bash
uv add <package>        # writes to root pyproject.toml + uv.lock
```

## Architecture

This repo contains three independent projects that all use the Anthropic Python SDK:

### claude_conversation_engine/
Multi-turn chat with Claude using streaming responses. The conversation loop lives in `services/send_message.py`. Three core components are injected into `MessageHandler`:
- `HistoryHandler` (api/history.py) -- manages conversation message list
- `UsageTracker` (usage_tracking/tracker.py) -- records per-turn token counts
- `MessageHandler` (api/messages.py) -- wraps `client.messages.stream()`, prints tokens as they arrive

### claude_prompt_eval/
Evaluates system prompts by auto-generating test cases, running them, and grading with Claude-as-judge. Pipeline in `services/evaluation.py`:
1. `CaseGenerator` -- asks Claude to generate test questions for a given system prompt
2. `EvalRunner` -- runs all test cases against prompt versions **in parallel** (uses `AsyncAnthropic`)
3. `Grader` -- scores responses in batches of 5, then generates improvement recommendations
4. `EvalReport` + `formatter.py` -- renders the final report

Data flows through dataclasses in `models.py`: `PromptVersion` -> `EvalCase` -> `EvalResult` -> `ScoreResult` -> `GradeReport`.

### code_editing_agent/
Standalone single-file agent (`agent.py`) with its own CLAUDE.md. Not connected to the other modules. Uses a tool-use loop: Claude calls `read_file`, `list_files`, or `edit_file` tools, agent executes them and feeds results back until Claude responds with text only.

### Shared
`client.py` at the repo root creates a shared `Anthropic` client (used by conversation engine and prompt eval, but **not** by code_editing_agent which creates its own).

`observability.py` at the repo root provides shared Langfuse tracing helpers (`setup_langfuse`, `flush`, `observe_if_active`, `session_context`, `record_span_input`). Each project opts in from its own entry point — see "Observability" below.

## Observability

Projects opt into Langfuse tracing via the shared helpers in `observability.py`. The integration is optional — if `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` aren't set, the helpers are no-ops and projects run untraced.

Standard wiring pattern:

- `setup_langfuse()` early in `main()`, **before** the shared Anthropic client is imported (OTEL patches the SDK module, so any client built afterwards is auto-traced).
- `flush()` before process exit.
- `@observe_if_active(name=...)` on top-level methods (session loops, tool dispatch, pipeline stages).
- `session_context(session_id, tags=[...])` at the top of any multi-turn flow; generate `session_id` with `uuid.uuid4()`.
- `record_span_input({...})` inside `@observe_if_active` methods to set the span's input explicitly — otherwise all function args (including `self`) leak in.
- **Don't manually instrument LLM calls.** The OTEL Anthropic instrumentor captures `client.messages.*` automatically.

Reference implementation: `code_editing_agent/agent.py`. Counter-example (deliberately untraced): `code_editing_agent/traced_main.py`, which uses the local `agent_trace_debugger` TUI tracer instead.

For deeper guidance on what to capture (session_id, user_id, tags, scores, masking PII) consult the installed `langfuse` skill — don't duplicate it here.

## Code Change Philosophy

### Keep Changes Small and Focused

- One logical change per commit -- each commit should do exactly one thing
- If a task feels too large, break it into subtasks
- Prefer multiple small commits over one large commit
- Run feedback loops after each change, not at the end
- Quality over speed. Small steps compound into big progress.

### Task Prioritization

When choosing the next task, prioritize in this order:

1. **Architectural decisions and core abstractions** -- Get the foundation right
2. **Integration points between modules** -- Ensure components connect properly
3. **Unknown unknowns and spike work** -- De-risk early
4. **Standard features and implementation** -- Build on solid foundations
5. **Polish, cleanup, and quick wins** -- Save easy wins for later

## Code Quality Standards

### Write Concise Code

After writing any code file, ask yourself: "Would a senior engineer say this is overcomplicated?"

If yes, simplify.

### Avoid Over-Engineering

- Only make changes that are directly requested or clearly necessary
- Don't add features beyond what was asked
- Don't refactor code that doesn't need it
- A bug fix doesn't need surrounding code cleaned up
- A simple feature doesn't need extra configurability

### Clean Code Practices

- Don't fill files just for the sake of it
- Don't leave dead code -- if it's unused, delete it completely
- Be organized, concise, and clean in your work
- No backwards-compatibility hacks for removed code
- No `# removed` comments or re-exports for deleted items

### Task Decomposition

- Use micro tasks -- smaller the task, better the code
- Break complex work into discrete, testable units
- Each micro task should be completable in one focused session

## Project-Specific Rules

### Tech Stack

- **Runtime**: Python 3.10+
- **Package Management**: uv (root `pyproject.toml` + `uv.lock`; `property_management_agent/` has its own)
- **Testing**: pytest
- **AI SDK**: Anthropic Python SDK
- **Environment**: python-dotenv

### Code Standards

- Use 4 spaces for indentation (PEP 8)
- Use snake_case for files, functions, and variables
- Use PascalCase for classes
- Keep imports organized -- stdlib, third-party, local
- Extract magic strings into constants
- Use dependency injection -- pass dependencies into classes, don't import globals
- Use named parameters for hardcoded/literal values in function calls (e.g. `make_client(text="response")`, `MessageHandler(client, history, tracker, thinking=True)`). Positional args are fine when passing variables whose names already convey meaning.

### Boundaries -- Never Modify

- `.env` files during execution
- `.venv/` directory contents (managed by uv)
- `uv.lock` (regenerate via `uv sync` or `uv lock`, never hand-edit)

### Testing

- Write tests for new features
- Run tests before committing: `make test`
- Mock external API calls -- never hit the real Claude API in tests
- Use constants for test values -- avoid hardcoded strings in assertions

### README Maintenance

Each project has its own README. After making changes to a project, read its README and update it to reflect the current state:

- `claude_conversation_engine/README.md`
- `claude_prompt_eval/README.md` (if it exists)
- `code_editing_agent/README.md` (if it exists)

Update READMEs when changes affect: architecture, public API, configuration, project structure, commands, or features. Don't update for internal refactors that don't change the external interface.

### Commit Guidelines

- One logical change per commit
- Write descriptive commit messages
- Commit message format: `type: brief description`
  - `feat:` new feature
  - `fix:` bug fix
  - `refactor:` code restructuring
  - `docs:` documentation
  - `test:` test additions/changes
  - `chore:` maintenance tasks
