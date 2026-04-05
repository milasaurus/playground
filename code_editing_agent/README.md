# Code-Editing Agent

This project wires up Claude with file system tools, grep, glob, and shell access to create an interactive agent that can read, search, and reason about your codebase. Claude decides which tools to call, chains them together, and maintains conversational memory across your session.

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

1. Create a new class in `tool_definitions.py` that extends `Tool`
2. Define `name`, `description`, and `input_schema` as class attributes
3. Implement the `run(params) -> str` method with your tool's logic
4. Add an instance to the tools list in `agent.py` `main()`
