# Code-Editing Agent

This project wires up Claude with file system tools, grep, glob, and shell access to create an interactive agent that can read, search, and reason about your codebase. Claude decides which tools to call, chains them together, and maintains conversational memory across your session.

## Usage

From the repo root:

```bash
make coder
```

## Architecture

- `agent.py` -- Agent class and entry point
- `tool_definitions.py` -- `Tool` base class and implementations (`ReadFileTool`, `ListFilesTool`, `EditFileTool`, `RunCommandTool`)
- `tests/` -- pytest tests for tools and agent loop

## Tools

| Tool | Description |
|------|-------------|
| `read_file` | Reads and returns a file's contents |
| `list_files` | Walks a directory and returns file/folder names (skips `.git`, `venv`, etc.) |
| `edit_file` | String-replaces in a file; creates it if new |
| `run_command` | Executes a shell command and returns stdout/stderr (30s timeout) |

## Long-context handling

Tool results are capped and truncated before they enter the conversation.
For a coding agent, tool output (`read_file`, `run_command`, `list_files`)
is the single biggest source of context growth — a 1,000-line file or a
verbose `pytest` run can easily eclipse everything else in a session.
Capping is a one-place change in the tool wrapper that keeps every tool
honest.

Benefits:

- **Bounded context growth.** No matter how big a file or command output
  is, a single call can't blow up the conversation.
- **Predictable cost.** Sessions stay roughly linear in turns instead of
  spiking on a single bad call.
- **One pathological call doesn't kill the run.** `find /` or
  `cat huge.log` truncate gracefully instead of failing the turn.
- **The agent learns to narrow its queries.** The truncation marker
  tells it what got cut and how to fetch the rest, so it asks for line
  ranges or pipes through `head` next time.

## Slash commands

| Command | Effect |
|---------|--------|
| `/compact` | Summarises the conversation so far (one Haiku call) and replaces it with a single user message containing that summary. The original turns are dropped — there's no undo. Prints `compacted N messages → M tokens` on success. Use it mid-session when context has grown large; the agent keeps running in the same terminal. |

Manual only. There is no auto-compaction, no token-threshold trigger, and no `/clear` — `/compact` on an empty conversation is a no-op, and to truly start over, just restart the process.

## Adding a tool

1. Subclass `Tool` in `tool_definitions.py` and implement `run(self, params: dict) -> str`
2. Instantiate it and add to the tools list in `agent.py` `main()`
