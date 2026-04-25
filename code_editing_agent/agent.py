"""
Code-editing agent — a minimal terminal agent that gives Claude file-system tools.

The user chats with Claude via stdin/stdout. Claude can call three tools
(read_file, list_files, edit_file) to inspect and modify files in the working
directory. The agent loop keeps running tool calls until Claude responds with
plain text, then prompts the user again.
"""

import json
from typing import Callable

import anthropic

from .tool_definitions import (
    Tool, ReadFileTool, ListFilesTool, EditFileTool, RunCommandTool,
    truncate_tool_output,
)


# ── Agent ─────────────────────────────────────────────────────────────────────

DEFAULT_MODEL = "claude-opus-4-5"
DEFAULT_MAX_TOKENS = 4096


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
    ):
        self.client          = client
        self.get_user_message = get_user_message
        self.tools           = tools
        self.model           = model
        self.max_tokens      = max_tokens

    def run(self):
        """Main loop. Alternates between user input and Claude responses.

        When Claude responds with tool_use blocks, the agent executes each tool
        and feeds results back without prompting the user. The loop only asks
        for new user input when Claude responds with text only.
        """
        conversation = []
        print("\033[93m🤖 Coding Agent Ready. Ask me anything about your codebase!\033[0m")
        print("(use 'ctrl-c' to quit)\n")

        read_user_input = True
        while True:
            if read_user_input:
                print("\033[94mYou\033[0m: ", end="", flush=True)
                user_input, ok = self.get_user_message()
                if not ok:
                    break
                conversation.append({"role": "user", "content": user_input})

            message = self._run_inference(conversation)
            conversation.append({"role": "assistant", "content": message.content})

            # Execute any tool_use blocks and send results back together.
            tool_results = []
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

    def _run_inference(self, conversation: list) -> anthropic.types.Message:
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
                    print(f"\033[93mClaude\033[0m: ", end="", flush=True)
                    printed_prefix = True
                print(text, end="", flush=True)

            if printed_prefix:
                print()

            return stream.get_final_message()

    def _execute_tool(self, tool_id: str, name: str, input: dict) -> dict:
        """Look up a tool by name, run it, and return a tool_result dict.

        Errors are caught and returned as error tool_results so Claude can
        see what went wrong and retry.
        """
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

def main():
    # Import here to avoid circular dependency and keep module importable without API key
    from client import client

    def get_user_message() -> tuple[str, bool]:
        try:
            return input(), True
        except (EOFError, KeyboardInterrupt):
            return "", False
    # add new tools here
    tools = [ReadFileTool(), ListFilesTool(), EditFileTool(), RunCommandTool()]
    agent = Agent(client, get_user_message, tools)
    agent.run()


if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    main()
