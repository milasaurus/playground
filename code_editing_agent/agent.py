"""
Code-editing agent — a minimal terminal agent that gives Claude file-system tools.

The user chats with Claude via stdin/stdout. Claude can call three tools
(read_file, list_files, edit_file) to inspect and modify files in the working
directory. The agent loop keeps running tool calls until Claude responds with
plain text, then prompts the user again.
"""

import json
import uuid
from typing import Any, Callable, NotRequired, TypedDict

import anthropic

from observability import observe_if_active, record_span_input, session_context
from .tool_definitions import (
    Tool, ReadFileTool, ListFilesTool, EditFileTool, RunCommandTool,
    truncate_tool_output,
)


# ── Agent ─────────────────────────────────────────────────────────────────────

DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 4096

SUMMARY_MODEL = "claude-haiku-4-5-20251001"
SUMMARY_MAX_TOKENS = 1024
SUMMARY_PROMPT = (
    "Summarise this conversation in ~200 words. Preserve every file path "
    "or file reference mentioned, every decision we made, and every open "
    "todo or unfinished task. Drop chitchat and verbose tool output. "
    "Write it as a briefing the assistant can read to pick up where we "
    "left off."
)


class ToolResult(TypedDict):
    """Shape of the `tool_result` content block sent back to Claude.

    Mirrors the Anthropic API's tool_result schema. `is_error` is omitted
    on success and set to True when the tool raised or wasn't found.
    """
    type:        str
    tool_use_id: str
    content:     str
    is_error:    NotRequired[bool]


class Agent:
    """Agentic loop: prompt user -> call Claude -> execute tools -> repeat.

    Args:
        client: Anthropic API client.
        get_user_message: Callable that returns (message, ok). When ok is False
            the loop exits (e.g. on EOF or Ctrl-C).
        tools: List of tools Claude can invoke during the conversation.
        model: Model ID passed to the Anthropic API.
        max_tokens: Max tokens per API response.
    """

    def __init__(
        self,
        client: anthropic.Anthropic,
        get_user_message: Callable[[], tuple[str, bool]],
        tools: list[Tool],
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        self.client          = client
        self.get_user_message = get_user_message
        self.tools           = tools
        self.model           = model
        self.max_tokens      = max_tokens
        self.session_id      = str(uuid.uuid4())

    @observe_if_active("agent-session")
    def run(self) -> None:
        """Main loop. Alternates between user input and Claude responses.

        When Claude responds with tool_use blocks, the agent executes each tool
        and feeds results back without prompting the user. The loop only asks
        for new user input when Claude responds with text only.
        """
        with session_context(self.session_id, tags=["code-editing-agent"]):
            self._run_loop()

    def _run_loop(self) -> None:
        conversation: list[dict[str, Any]] = []
        print("\033[93m🤖 Coding Agent Ready. Ask me anything about your codebase!\033[0m")
        print("(use 'ctrl-c' to quit)\n")

        read_user_input = True
        while True:
            if read_user_input:
                print("\033[94mYou\033[0m: ", end="", flush=True)
                user_input, ok = self.get_user_message()
                if not ok:
                    break
                if user_input.strip() == "/compact":
                    self._compact_conversation(conversation)
                    continue
                conversation.append({"role": "user", "content": user_input})

            message = self._run_inference(conversation)
            conversation.append({"role": "assistant", "content": message.content})

            # Execute any tool_use blocks and send results back together.
            tool_results: list[ToolResult] = []
            for block in message.content:
                if block.type == "tool_use":
                    result = self._execute_tool(block.id, block.name, block.input)
                    tool_results.append(result)

            # stop_reason == "tool_use" means Claude wants to call more tools;
            # "end_turn" means it's done and we should prompt the user again.
            if message.stop_reason != "tool_use":
                read_user_input = True
                continue

            read_user_input = False
            conversation.append({"role": "user", "content": tool_results})

    def _run_inference(self, conversation: list[dict[str, Any]]) -> anthropic.types.Message:
        """Stream the response, printing text tokens as they arrive."""
        tool_dicts = [t.to_api_dict() for t in self.tools]
        if tool_dicts:
            tool_dicts[-1]["cache_control"] = {"type": "ephemeral"}

        printed_prefix = False

        with self.client.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            tools=tool_dicts,
            messages=conversation,
        ) as stream:
            for text in stream.text_stream:
                if not printed_prefix:
                    print("\033[93mClaude\033[0m: ", end="", flush=True)
                    printed_prefix = True
                print(text, end="", flush=True)

            if printed_prefix:
                print()

            return stream.get_final_message()

    def _compact_conversation(self, conversation: list[dict[str, Any]]) -> None:
        """Summarise `conversation` and rewrite it in place to a single user message.

        On empty conversation or any failure (API error, empty/non-text
        response), the conversation is left untouched and a short status
        line is printed.
        """
        if len(conversation) == 0:
            print("\033[93mnothing to compact — conversation is empty\033[0m")
            return

        try:
            payload = list(conversation) + [
                {"role": "user", "content": SUMMARY_PROMPT},
            ]
            response = self.client.messages.create(
                model=SUMMARY_MODEL,
                max_tokens=SUMMARY_MAX_TOKENS,
                tools=[t.to_api_dict() for t in self.tools],
                messages=payload,
            )
            summary = response.content[0].text
            n_messages = len(conversation)
            m_tokens = response.usage.output_tokens

            conversation.clear()
            conversation.append({"role": "user", "content": summary})
            print(f"\033[93mcompacted {n_messages} messages → {m_tokens} tokens\033[0m")
        except Exception as e:
            print(f"\033[93m/compact failed: {e}\033[0m")

    @observe_if_active("execute-tool")
    def _execute_tool(self, tool_id: str, name: str, input: dict[str, Any]) -> ToolResult:
        """Look up a tool by name, run it, and return a tool_result dict.

        Errors are caught and returned as error tool_results so Claude can
        see what went wrong and retry.
        """
        record_span_input({"name": name, "params": input})
        tool_def = next((t for t in self.tools if t.name == name), None)
        if tool_def is None:
            return {
                "type":        "tool_result",
                "tool_use_id": tool_id,
                "content":     "tool not found",
                "is_error":    True,
            }

        print(f"\033[92mtool\033[0m: {name}({json.dumps(input)})")
        try:
            response = truncate_tool_output(tool_def.run(input))
            return {"type": "tool_result", "tool_use_id": tool_id, "content": response}
        except Exception as e:
            return {
                "type":        "tool_result",
                "tool_use_id": tool_id,
                "content":     truncate_tool_output(str(e)),
                "is_error":    True,
            }


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    # Set up Langfuse tracing BEFORE importing the shared Anthropic client —
    # OTEL patches the SDK module, so a client built afterwards is auto-traced.
    # No-op when LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY aren't set.
    from observability import setup_langfuse, flush
    setup_langfuse()

    # Import here to avoid circular dependency and keep module importable without API key
    from client import client

    def get_user_message() -> tuple[str, bool]:
        try:
            return input(), True
        except (EOFError, KeyboardInterrupt):
            return "", False
    # add new tools here
    tools: list[Tool] = [ReadFileTool(), ListFilesTool(), EditFileTool(), RunCommandTool()]
    agent = Agent(client, get_user_message, tools)
    try:
        agent.run()
    finally:
        flush()


if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    main()
