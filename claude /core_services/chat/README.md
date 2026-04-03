# Chat — Core Service

A shared, reusable conversation engine powered by the Claude API. Provides multi-turn messaging, conversation history, token usage tracking, and an interactive chat loop.

This lives under `core_services/` because it is not a product itself — it is a foundational building block that products import and build on top of.

## Project Structure

```
claude/
  client.py                          # Shared Anthropic client
  core_services/                     # Reusable packages shared across products
    chat/
      api/
        messages.py                  # MessageHandler — sends messages to Claude
        history.py                   # HistoryHandler — manages conversation history
      services/
        send_message.py              # Interactive chat loop (run_chat)
      usage_tracking/
        tracker.py                   # UsageTracker — tracks token consumption per turn
      tests/
        test_messages.py             # Tests for MessageHandler
        test_history.py              # Tests for HistoryHandler
        test_send_message.py         # Tests for chat loop
```

## Setup

1. Create and activate a virtual environment:
   ```bash
   cd claude\ /
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install anthropic python-dotenv pytest
   ```

3. Create a `.env` file in the `claude /` directory with your API key:
   ```
   ANTHROPIC_API_KEY=your-api-key-here
   ```

## Usage

From the `claude /` directory, with the virtual environment activated:

```bash
python -m core_services.chat.services.send_message
```

This starts an interactive conversation with Claude. Type your messages and press Enter to send. Type `quit` to exit and see a token usage report.

### Importing into a product

```python
from client import client
from core_services.chat.api.history import HistoryHandler
from core_services.chat.api.messages import MessageHandler
from core_services.chat.usage_tracking.tracker import UsageTracker
from core_services.chat.services.send_message import run_chat

history = HistoryHandler()
tracker = UsageTracker()
handler = MessageHandler(client, history, tracker)
run_chat(handler, tracker)
```

## Running Tests

```bash
python -m pytest core_services/chat/tests/ -v
```
