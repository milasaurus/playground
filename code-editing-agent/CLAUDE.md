# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
make coder                     # Run the agent (from repo root)
make test                      # Run all tests
```

Run agent tests only:
```bash
source venv/bin/activate && python -m pytest code-editing-agent/tests/ -v
```

## Architecture

Python code-editing agent built with the Anthropic Python SDK. Learning project: understand how agents work by building one from scratch.

### File structure

- `agent.py` -- Agent class and entry point
- `tool_definitions.py` -- Tool base class and tool implementations
- `tests/` -- pytest tests for tools and agent loop

### Agent loop (agent.py)

1. Read user input from stdin
2. Append to conversation history
3. Call `client.messages.create()` with tools
4. If response contains `tool_use` blocks, execute each tool and send results back
5. Repeat until Claude responds with text only (no more tool calls)
6. Print response, prompt for next user input

### Key classes

- `Tool` (tool_definitions.py) -- abstract base class; subclasses define `name`, `description`, `input_schema`, and implement `run(params) -> str`
- `ReadFileTool`, `ListFilesTool`, `EditFileTool` -- concrete tool implementations
- `Agent` (agent.py) -- holds client, tools, and conversation loop logic; model and max_tokens are configurable

### Adding a new tool

1. Subclass `Tool` in `tool_definitions.py`
2. Define `name`, `description`, `input_schema` as class attributes
3. Implement `run(params) -> str`
4. Add an instance to the tools list in `main()`

## Conventions

- Uses shared Anthropic client from repo root `client.py`
- Errors in tool execution are caught and returned as error `tool_result` blocks
- ANSI colour codes: blue = You, yellow = Claude, green = tool calls
- Default model: `claude-opus-4-5` with `max_tokens=4096` (configurable)

## What to work on next

- Add a system prompt to give the agent a persona / set of instructions
- Add more tools: `run_command`, `search_files` (grep), `web_fetch`
- Streaming responses so long outputs print progressively
- Token usage tracking / context window management
