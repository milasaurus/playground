# Code-Editing Agent

A terminal-based AI agent built with the Anthropic Python SDK. Chat with Claude in the terminal while giving it tools to read, list, and edit files in your working directory.

## Usage

From the repo root:

```bash
make coder
```

## Architecture

- `agent.py` -- Agent class and entry point
- `tool_definitions.py` -- `Tool` base class and implementations (`ReadFileTool`, `ListFilesTool`, `EditFileTool`)
- `tests/` -- pytest tests for tools and agent loop

## Tools

| Tool | Description |
|------|-------------|
| `read_file` | Reads and returns a file's contents |
| `list_files` | Walks a directory and returns file/folder names (skips `.git`, `venv`, etc.) |
| `edit_file` | String-replaces in a file; creates it if new |

## Adding a tool

Subclass `Tool` in `tool_definitions.py`, implement `run(params) -> str`, and add an instance to the tools list in `agent.py` `main()`.
