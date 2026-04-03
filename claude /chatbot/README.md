# Chatbot

A multi-turn chatbot powered by the Claude API with conversation history and token usage tracking.

## Project Structure

```
chatbot/
  api/
    messages.py         # MessageHandler — sends messages to Claude
    history.py          # HistoryHandler — manages conversation history
  services/
    send_message.py     # Entry point to run the chatbot
  usage_tracking/
    tracker.py          # UsageTracker — tracks token consumption per turn
  tests/
    test_messages.py    # Tests for MessageHandler
    test_history.py     # Tests for HistoryHandler
    test_send_message.py # Tests for chat loop
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
python -m chatbot.services.send_message
```

This starts an interactive conversation with Claude. Type your messages and press Enter to send. Type `quit` to exit and see a token usage report.

## Running Tests

```bash
python -m pytest chatbot/tests/ -v
```
