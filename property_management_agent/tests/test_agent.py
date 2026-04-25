"""Tests for the Agent class — verifies the agentic loop, tool execution,
thinking block filtering, and conversation history management.

All tests mock the Anthropic client so no API calls are made."""

from unittest.mock import MagicMock, patch
from types import SimpleNamespace

from agent import Agent
from tools.base import Tool


# ── Helpers ──────────────────────────────────────────────────────────────────


class FakeTool(Tool):
    """A simple tool that echoes its input as a string."""

    def __init__(self, name="echo", description="Echo input"):
        super().__init__(
            name=name,
            description=description,
            input_schema={
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        )

    def run(self, params: dict) -> str:
        return params.get("text", "")


class FailingTool(Tool):
    """A tool that always raises an exception."""

    def __init__(self):
        super().__init__(
            name="fail",
            description="Always fails",
            input_schema={"type": "object", "properties": {}, "required": []},
        )

    def run(self, params: dict) -> str:
        raise RuntimeError("something broke")


def _text_block(text):
    return SimpleNamespace(type="text", text=text)


def _thinking_block(thinking):
    return SimpleNamespace(type="thinking", thinking=thinking)


def _tool_use_block(id, name, input):
    return SimpleNamespace(type="tool_use", id=id, name=name, input=input)


def _make_response(content, stop_reason="end_turn"):
    return SimpleNamespace(content=content, stop_reason=stop_reason)


def _mock_stream(response):
    """Create a mock stream context manager that returns a response."""
    stream = MagicMock()
    stream.get_final_message.return_value = response
    stream.__enter__ = MagicMock(return_value=stream)
    stream.__exit__ = MagicMock(return_value=False)
    return stream


# ── Tests ────────────────────────────────────────────────────────────────────


class TestAgentInit:
    def test_caches_tool_definitions(self):
        client = MagicMock()
        tool = FakeTool()
        agent = Agent(client, [tool])

        assert len(agent._tool_defs_cache) == 1
        assert agent._tool_defs_cache[0]["name"] == "echo"

    def test_starts_with_empty_history(self):
        client = MagicMock()
        agent = Agent(client, [])

        assert agent.messages == []


class TestAgentRun:
    def test_returns_text_response(self):
        """When Claude responds with text only, run() returns that text."""
        client = MagicMock()
        response = _make_response([_text_block("Hello!")])
        client.messages.stream.return_value = _mock_stream(response)

        agent = Agent(client, [])
        result = agent.run("Hi")

        assert result == "Hello!"

    def test_appends_user_message_to_history(self):
        client = MagicMock()
        response = _make_response([_text_block("Reply")])
        client.messages.stream.return_value = _mock_stream(response)

        agent = Agent(client, [])
        agent.run("Test message")

        assert agent.messages[0] == {"role": "user", "content": "Test message"}

    def test_appends_assistant_response_to_history(self):
        client = MagicMock()
        text_block = _text_block("Reply")
        response = _make_response([text_block])
        client.messages.stream.return_value = _mock_stream(response)

        agent = Agent(client, [])
        agent.run("Hi")

        assert agent.messages[1]["role"] == "assistant"
        assert agent.messages[1]["content"] == [text_block]

    def test_strips_thinking_blocks_from_history(self):
        """Thinking blocks are ephemeral — the API rejects them in later
        requests. Verify they're filtered out of self.messages."""
        client = MagicMock()
        thinking = _thinking_block("Let me think...")
        text = _text_block("Done thinking")
        response = _make_response([thinking, text])
        client.messages.stream.return_value = _mock_stream(response)

        agent = Agent(client, [])
        agent.run("Think about this")

        assistant_content = agent.messages[1]["content"]
        types = [block.type for block in assistant_content]
        assert "thinking" not in types
        assert "text" in types

    def test_multi_turn_preserves_history(self):
        """Each call to run() adds to the same conversation history."""
        client = MagicMock()

        response1 = _make_response([_text_block("First reply")])
        response2 = _make_response([_text_block("Second reply")])
        client.messages.stream.side_effect = [
            _mock_stream(response1),
            _mock_stream(response2),
        ]

        agent = Agent(client, [])
        agent.run("First message")
        agent.run("Second message")

        # Should have: user1, assistant1, user2, assistant2
        assert len(agent.messages) == 4
        assert agent.messages[2] == {"role": "user", "content": "Second message"}


class TestAgentToolExecution:
    def test_executes_tool_and_sends_result_back(self):
        """When Claude requests a tool call, the agent executes it and
        feeds the result back, then returns Claude's final text."""
        client = MagicMock()
        tool = FakeTool()

        # First response: Claude calls the echo tool
        tool_response = _make_response(
            [_tool_use_block("call-1", "echo", {"text": "echoed"})],
            stop_reason="tool_use",
        )
        # Second response: Claude replies with text
        text_response = _make_response([_text_block("Got: echoed")])

        client.messages.stream.side_effect = [
            _mock_stream(tool_response),
            _mock_stream(text_response),
        ]

        agent = Agent(client, [tool])
        result = agent.run("Echo this")

        assert result == "Got: echoed"

    def test_tool_results_appended_to_history(self):
        """After executing tools, the results should appear in
        self.messages as a user message with tool_result dicts."""
        client = MagicMock()
        tool = FakeTool()

        tool_response = _make_response(
            [_tool_use_block("call-1", "echo", {"text": "test"})],
            stop_reason="tool_use",
        )
        text_response = _make_response([_text_block("Done")])

        client.messages.stream.side_effect = [
            _mock_stream(tool_response),
            _mock_stream(text_response),
        ]

        agent = Agent(client, [tool])
        agent.run("Do it")

        # Find the tool result message in history
        tool_result_msg = agent.messages[2]  # user, assistant(tool_use), user(tool_result)
        assert tool_result_msg["role"] == "user"
        assert tool_result_msg["content"][0]["type"] == "tool_result"
        assert tool_result_msg["content"][0]["content"] == "test"

    def test_unknown_tool_returns_error(self):
        """If Claude calls a tool that doesn't exist, the agent returns
        an error tool_result so Claude can see what went wrong."""
        client = MagicMock()

        tool_response = _make_response(
            [_tool_use_block("call-1", "nonexistent", {})],
            stop_reason="tool_use",
        )
        text_response = _make_response([_text_block("Sorry")])

        client.messages.stream.side_effect = [
            _mock_stream(tool_response),
            _mock_stream(text_response),
        ]

        agent = Agent(client, [])
        agent.run("Call something")

        tool_result_msg = agent.messages[2]
        assert tool_result_msg["content"][0]["is_error"] is True
        assert "not found" in tool_result_msg["content"][0]["content"]

    def test_tool_exception_returns_error_result(self):
        """If a tool raises an exception, the agent catches it and returns
        the error as a tool_result rather than crashing."""
        client = MagicMock()
        tool = FailingTool()

        tool_response = _make_response(
            [_tool_use_block("call-1", "fail", {})],
            stop_reason="tool_use",
        )
        text_response = _make_response([_text_block("I see the error")])

        client.messages.stream.side_effect = [
            _mock_stream(tool_response),
            _mock_stream(text_response),
        ]

        agent = Agent(client, [tool])
        result = agent.run("Break it")

        tool_result_msg = agent.messages[2]
        assert tool_result_msg["content"][0]["is_error"] is True
        assert "something broke" in tool_result_msg["content"][0]["content"]
        assert result == "I see the error"

    def test_max_tool_calls_stops_execution(self):
        """If total tool calls exceed MAX_TOOL_CALLS, the agent stops
        executing tools and returns early."""
        client = MagicMock()
        tool = FakeTool()

        # Each response calls 3 tools — after 3 iterations that's 9,
        # which exceeds a limit of 8. The agent should stop mid-iteration.
        tool_response = _make_response(
            [
                _tool_use_block("call-a", "echo", {"text": "1"}),
                _tool_use_block("call-b", "echo", {"text": "2"}),
                _tool_use_block("call-c", "echo", {"text": "3"}),
            ],
            stop_reason="tool_use",
        )
        client.messages.stream.return_value = _mock_stream(tool_response)

        agent = Agent(client, [tool])

        with patch("agent.MAX_TOOL_CALLS", 8), patch("agent.MAX_ITERATIONS", 10):
            result = agent.run("Do many things")

        # 3 iterations fully executed (9 calls attempted, but the 9th
        # triggers the limit), so the API was called 3 times
        assert client.messages.stream.call_count == 3
        assert result == ""

    def test_max_iterations_returns_last_response(self):
        """If the agent hits MAX_ITERATIONS without Claude stopping tool use,
        it returns whatever text it can extract from the last response."""
        client = MagicMock()
        tool = FakeTool()

        # Claude keeps calling tools forever
        tool_response = _make_response(
            [_tool_use_block("call-1", "echo", {"text": "loop"})],
            stop_reason="tool_use",
        )
        client.messages.stream.return_value = _mock_stream(tool_response)

        agent = Agent(client, [tool])

        with patch("agent.MAX_ITERATIONS", 2):
            result = agent.run("Loop forever")

        # Should return empty string since the last response has no text block
        assert result == ""
        # Should have called the API exactly MAX_ITERATIONS times
        assert client.messages.stream.call_count == 2


class TestExtractText:
    def test_extracts_text_from_mixed_content(self):
        client = MagicMock()
        agent = Agent(client, [])

        response = _make_response([
            _tool_use_block("id", "name", {}),
            _text_block("The actual text"),
        ])

        assert agent._extract_text(response) == "The actual text"

    def test_returns_empty_when_no_text(self):
        client = MagicMock()
        agent = Agent(client, [])

        response = _make_response([_tool_use_block("id", "name", {})])

        assert agent._extract_text(response) == ""
