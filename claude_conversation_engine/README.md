# Claude Conversation Engine

> A shared conversation layer for building multi-turn Claude-powered products.

## Overview

The Claude Conversation Engine handles the plumbing of talking to Claude — message history, token tracking, system prompts, and an interactive chat loop — so you can focus on building your product on top of it.

## Features

### Multi-Turn Conversations

Maintains full conversation history across turns. Every message you send includes the full context of what came before, so Claude always knows what's been discussed.

### System Prompts

Control Claude's behavior per product or per message:

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
cd claude
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
from core_services.claude_conversation_engine.api.history import HistoryHandler
from core_services.claude_conversation_engine.api.messages import MessageHandler
from core_services.claude_conversation_engine.usage_tracking.tracker import UsageTracker
from core_services.claude_conversation_engine.services.send_message import run_chat

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

## Project Structure

```
claude/
  client.py                                  # Shared Anthropic client
  core_services/
    claude_conversation_engine/
      api/
        messages.py                          # MessageHandler — sends messages to Claude
        history.py                           # HistoryHandler — tracks conversation state
      services/
        send_message.py                      # Interactive chat loop (run_chat)
      usage_tracking/
        tracker.py                           # Tracks token usage per turn
      tests/                                 # 14 tests covering all of the above
  Makefile                                   # make chat, make test, make setup
```

## Testing

```bash
make test
```
