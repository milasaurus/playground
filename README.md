# Playground

A collection of projects exploring agentic workflows and prompt engineering with the Anthropic Python SDK.

## Projects

| Directory | Description |
|-----------|-------------|
| `claude_conversation_engine/` | Multi-turn chat with Claude using streaming, history tracking, and token usage reporting |
| `claude_prompt_eval/` | Evaluate system prompts by auto-generating test cases and grading with Claude-as-judge |
| `code_editing_agent/` | Terminal-based agent that gives Claude tools to read, list, and edit files |

## Getting Started

```bash
git clone https://github.com/milasaurus/playground.git
cd playground
make setup
```

Create a `.env` file in the project root with your Anthropic API key:

```bash
ANTHROPIC_API_KEY=your-api-key-here
```

## Commands

```bash
make chat               # Run the conversation engine
make prompt             # Run prompt eval
make prompt-verbose     # Run prompt eval with full response details
make coder              # Run the code-editing agent
make test               # Run all tests
```
