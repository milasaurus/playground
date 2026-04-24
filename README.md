# Playground

A collection of projects exploring agentic workflows with the Anthropic Python SDK.

## Projects

| Directory | Description |
|-----------|-------------|
| `claude_conversation_engine/` | Terminal chat with Claude using streaming, history tracking, and token usage reporting |
| `claude_prompt_eval/` | Auto generate test cases for a prompt, run them, and grade responses using Claude |
| `code_editing_agent/` | Terminal based agent that gives Claude tools to read, list, and edit files |
| `property_management_agent/` | Agentic tool-calling system that manages inbox, calendar, and property listings for a real estate solopreneur |
| `agent_trace_debugger/` | Auto-instrumented Claude agent + Textual TUI that captures and visualises decisions, tool calls, and observations |

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
make chat                  # Run the conversation engine
make prompt                # Run prompt eval
make prompt-verbose        # Run prompt eval with full response details
make coder                 # Run the code-editing agent
make property-agent        # Run the property management agent
make debugger Q="..."      # Run the agent trace debugger on a question
make test                  # Run all tests
```
