# Claude Conversation Engine

> A shared conversation layer for building multi-turn Claude-powered products.

## Overview

The Claude Conversation Engine handles the plumbing of talking to Claude — message history, token tracking, system prompts, and an interactive chat loop — so you can focus on building your product on top of it.

## Features

### Multi-Turn Conversations

Maintains full conversation history across turns. Every message you send includes the full context of what came before, so Claude always knows what's been discussed.

### Streaming Responses

Responses stream in real-time, printing character-by-character as Claude generates them using `client.messages.stream()`.

### System Prompts

Control Claude's behavior per conversation or per message:

```python
# Set a personality for the whole conversation
handler = MessageHandler(client, history, tracker, system_prompt="You are a patient eng mentor.")

# Override for a single message
handler.send("Translate hello", system_prompt="You are a Spanish translator.")
```

A default system prompt is included that guides Claude to help users work through problems rather than giving answers directly.

### Token Usage Tracking

Tracks input and output tokens per turn. Print a full usage report at any time:

```
Token Usage Report
========================================
Turn 1: 15 in / 8 out / 23 total
Turn 2: 30 in / 12 out / 42 total
========================================
Total: 45 in / 20 out / 65 total across 2 turns
```

### Interactive Chat Loop

A ready-to-use terminal chat loop with quit support. Type messages, get responses, type `quit` to exit.

## Getting Started

### Prerequisites

- Python 3.10+
- An Anthropic API key

### Installation

1. Clone the repository and set up your environment:

```bash
make setup
```

2. Set up environment variables:

```bash
# .env
ANTHROPIC_API_KEY=your-api-key-here
```

3. Start chatting:

```bash
make chat
```

## Usage

### Quick start — interactive chat

```bash
make chat
```

### Build your own product

```python
from client import client
from claude_conversation_engine.api.history import HistoryHandler
from claude_conversation_engine.api.messages import MessageHandler
from claude_conversation_engine.usage_tracking.tracker import UsageTracker
from claude_conversation_engine.services.send_message import run_chat

history = HistoryHandler()
tracker = UsageTracker()
handler = MessageHandler(client, history, tracker)

# Use the built-in chat loop
run_chat(handler, tracker)

# Or build your own flow
response = handler.send("What is Python?")
print(response)
print(tracker.report())
```

## Architecture

```
claude_conversation_engine/
  api/
    messages.py                    # MessageHandler — sends messages to Claude via streaming
    history.py                     # HistoryHandler — tracks conversation state
  services/
    send_message.py                # Interactive chat loop (run_chat)
  usage_tracking/
    tracker.py                     # Tracks token usage per turn
  tests/                           # Tests covering all components
```

### Component Dependencies

```
Client (Anthropic instance from client.py at repo root)
  |
  v
MessageHandler
  ├── HistoryHandler (stores conversation messages)
  ├── UsageTracker (records token usage)
  └── client.messages.stream() (Anthropic API)

run_chat()
  ├── MessageHandler.send()
  └── UsageTracker.report()
```

### Key Classes

| Class | File | Purpose |
|-------|------|---------|
| `HistoryHandler` | `api/history.py` | Manages conversation message list. Returns defensive copies. |
| `MessageHandler` | `api/messages.py` | Wraps `client.messages.stream()`, manages multi-turn context, tracks tokens. |
| `UsageTracker` | `usage_tracking/tracker.py` | Records per-turn token counts, generates formatted reports. |
| `run_chat()` | `services/send_message.py` | Interactive terminal loop with configurable I/O for testing. |

### Configuration

| Setting | Default | Override |
|---------|---------|----------|
| Model | `claude-haiku-4-5-20251001` | `MessageHandler(model=...)` |
| Max tokens | `1024` | `MessageHandler(max_tokens=...)` |
| System prompt | Guidance-focused default | Constructor or per-message via `send(system_prompt=...)` |

## Testing

```bash
make test-chat    # Run conversation engine tests only
make test         # Run all tests across the repo
```

14 tests covering history management, message handling, streaming, token tracking, system prompt overrides, and the interactive chat loop.
