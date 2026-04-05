# Playground

A collection of projects exploring agentic workflows and prompt engineering with the Anthropic Python SDK.

## Projects

| Directory | Description |
|-----------|-------------|
| `claude_conversation_engine/` | Terminal chat with Claude using streaming, history tracking, and token usage reporting |
| `claude_prompt_eval/` | Evaluate prompts by auto generating user message cases and prompt grading with Claude |
| `code-editing-agent/` | Terminal coding agent that gives Claude tools to read, list, and edit files |

## Setup

```bash
make setup
```

## Commands

```bash
make chat               # Run the conversation engine
make prompt             # Run prompt eval
make prompt-verbose     # Run prompt eval with full response details
make coder              # Run the code-editing agent
make test               # Run all tests
```
