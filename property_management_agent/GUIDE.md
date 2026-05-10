# Testing Guide

## Setup

### Option 1 — UV (recommended)

    make setup

This runs `uv sync` to create a virtual environment and install dependencies.

### Option 2 — pip (if you don't have UV installed)

Ensure you are using **Python 3.14 or later**, then create and activate a virtual environment manually:

```bash
python3 --version          # confirm 3.14+
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Once the environment is active, replace every `make` target's underlying `uv run` call with a direct `python` invocation:

| Task | UV (make) | pip alternative |
|---|---|---|
| Seed databases | `make seed` | `python seed_data.py` |
| Start the CLI | `make run` | `python seed_data.py && python main.py` |
| Run tests | `make test` | `python -m pytest tests/ -v` |

> **Note:** `requirements.txt` is generated from `pyproject.toml` and is the pip-compatible source of truth for dependencies.

### API key

You'll need an `ANTHROPIC_API_KEY` environment variable set:

    export ANTHROPIC_API_KEY=sk-ant-...

## Interactive CLI

Start the agent (seeds databases automatically):

    make run

To seed databases without starting the CLI:

    make seed

Seeding creates 15 listings, 12 calendar events, and 20 inbox messages.

### Example prompts to try

**Listings queries:**

```
You: What 2 bedroom apartments do you have available below $3000?
You: Show me all listings
You: Create a listing for a 3BR house at 500 Elm Street for $3200/month with 2 bathrooms
You: Delete the listing at 500 Elm Street
```

**Calendar queries:**

```
You: What's my schedule for tomorrow?
You: Schedule a viewing at 123 Oak Street tomorrow at 4 PM with tenant@example.com
You: Move my 4 PM appointment tomorrow to 5 PM
You: Cancel the showing with sarah.jones@example.com
```

**Inbox queries:**

```
You: Show me all my emails
You: Send an email to tenant@example.com with subject "Lease Renewal" saying their lease is up next month
You: Search my inbox for emails about maintenance
You: What did priya.patel@example.com ask about?
```

**Multi-step requests (tests the tool chaining):**

```
You: Find all 2BR apartments under $3000 and send the list to customer@example.com
You: Check if I have any showings tomorrow and list the addresses
```

### Multi-turn conversation

The agent remembers prior context within a session:

```
You: What listings do I have?
Agent: [lists all properties]

You: Delete the one on Oak Street
Agent: [finds and deletes it — knows "the one" from prior turn]
```

## Running tests

    make test          # All tests (unit + e2e, requires API key)

## Agent limits

The agent has two safety limits to prevent runaway loops:

- **Depth limit (`MAX_ITERATIONS=4`):** Maximum LLM call -> tool use cycles per request
- **Tool call limit (`MAX_TOOL_CALLS=8`):** Maximum total tool executions per request

If either limit is hit, the agent returns whatever response it has so far. These limits mean it won't handle overly complex compound requests like "adjust all listings, reschedule all showings, and notify everyone."

## Notes

- The agent uses `claude-haiku-4-5` with extended thinking enabled
- Databases are SQLite files created in the working directory (`inbox.db`, `calendar.db`, `listings.db`)
- Test databases use separate files (`test_*.db`) and are wiped between runs
- Seed data includes realistic contacts — use those emails in prompts for best results
