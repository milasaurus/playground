import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agent import Agent
from tool_definitions import Tool


TOOL_ID = "tool_123"
TOOL_NAME = "echo"
TOOL_RESPONSE = "echoed"


class EchoTool(Tool):
    """Test tool that returns a fixed string."""
    name = TOOL_NAME
    description = "echoes input"
    input_schema = {"type": "object", "properties": {}}

    def run(self, params: dict) -> str:
        return TOOL_RESPONSE


class FailingTool(Tool):
    """Test tool that always raises."""
    name = "fail"
    description = "fails"
    input_schema = {"type": "object", "properties": {}}

    def run(self, params: dict) -> str:
        raise RuntimeError("boom")


def make_text_block(text):
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def make_tool_use_block(name=TOOL_NAME, tool_id=TOOL_ID, tool_input=None):
    block = MagicMock()
    block.type = "tool_use"
    block.name = name
    block.id = tool_id
    block.input = tool_input or {}
    return block


# ── _execute_tool ────────────────────────────────────────────────────────────

class TestExecuteTool:
    def setup_method(self):
        self.client = MagicMock()
        self.agent = Agent(self.client, lambda: ("", False), [EchoTool()])

    def test_executes_known_tool(self):
        result = self.agent._execute_tool(TOOL_ID, TOOL_NAME, {})
        assert result["content"] == TOOL_RESPONSE
        assert result["tool_use_id"] == TOOL_ID
        assert "is_error" not in result

    def test_returns_error_for_unknown_tool(self):
        result = self.agent._execute_tool(TOOL_ID, "nonexistent", {})
        assert result["is_error"] is True
        assert result["content"] == "tool not found"

    def test_returns_error_on_tool_exception(self):
        agent = Agent(self.client, lambda: ("", False), [FailingTool()])
        result = agent._execute_tool(TOOL_ID, "fail", {})
        assert result["is_error"] is True
        assert "boom" in result["content"]


# ── run loop ─────────────────────────────────────────────────────────────────

class TestRunLoop:
    def test_exits_on_user_quit(self, capsys):
        client = MagicMock()
        agent = Agent(client, lambda: ("", False), [])
        agent.run()
        output = capsys.readouterr().out
        assert "ctrl-c" in output

    def test_text_response_prints_and_prompts_again(self, capsys):
        client = MagicMock()
        message = MagicMock()
        message.content = [make_text_block("hi there")]
        client.messages.create.return_value = message

        call_count = 0
        def get_message():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "hello", True
            return "", False

        agent = Agent(client, get_message, [])
        agent.run()
        output = capsys.readouterr().out
        assert "hi there" in output

    def test_tool_use_executes_and_continues(self, capsys):
        client = MagicMock()
        tool_message = MagicMock()
        tool_message.content = [make_tool_use_block()]

        text_message = MagicMock()
        text_message.content = [make_text_block("done")]

        client.messages.create.side_effect = [tool_message, text_message]

        call_count = 0
        def get_message():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "do something", True
            return "", False

        agent = Agent(client, get_message, [EchoTool()])
        agent.run()
        output = capsys.readouterr().out
        assert TOOL_NAME in output
        assert "done" in output
