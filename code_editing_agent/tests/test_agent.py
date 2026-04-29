from unittest.mock import MagicMock

from code_editing_agent.agent import Agent, SUMMARY_MODEL
from code_editing_agent.tool_definitions import Tool, MAX_OUTPUT_CHARS


TOOL_ID = "tool_123"
TOOL_NAME = "echo"
TOOL_RESPONSE = "echoed"


class EchoTool(Tool):
    def __init__(self):
        super().__init__(
            name=TOOL_NAME,
            description="echoes input",
            input_schema={"type": "object", "properties": {}},
        )

    def run(self, params: dict) -> str:
        return TOOL_RESPONSE


class FailingTool(Tool):
    def __init__(self):
        super().__init__(
            name="fail",
            description="fails",
            input_schema={"type": "object", "properties": {}},
        )

    def run(self, params: dict) -> str:
        raise RuntimeError("boom")


class LongOutputTool(Tool):
    def __init__(self, payload: str):
        super().__init__(
            name="long",
            description="returns a long string",
            input_schema={"type": "object", "properties": {}},
        )
        self._payload = payload

    def run(self, params: dict) -> str:
        return self._payload


echo_tool = EchoTool()
failing_tool = FailingTool()


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


def make_stream(message, text_chunks=None):
    """Create a mock stream context manager that yields text_chunks and returns message."""
    stream = MagicMock()
    stream.text_stream = iter(text_chunks or [])
    stream.get_final_message.return_value = message
    stream.__enter__ = lambda self: stream
    stream.__exit__ = lambda self, *args: None
    return stream


# ── _execute_tool ────────────────────────────────────────────────────────────

class TestExecuteTool:
    def setup_method(self):
        self.client = MagicMock()
        self.agent = Agent(self.client, lambda: ("", False), [echo_tool])

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
        agent = Agent(self.client, lambda: ("", False), [failing_tool])
        result = agent._execute_tool(TOOL_ID, "fail", {})
        assert result["is_error"] is True
        assert "boom" in result["content"]

    def test_long_tool_output_is_truncated(self):
        long_tool = LongOutputTool("x" * (MAX_OUTPUT_CHARS + 5000))
        agent = Agent(self.client, lambda: ("", False), [long_tool])
        result = agent._execute_tool(TOOL_ID, "long", {})
        assert len(result["content"]) < MAX_OUTPUT_CHARS + 5000
        assert "omitted" in result["content"]
        assert "is_error" not in result

    def test_short_tool_output_is_unchanged(self):
        result = self.agent._execute_tool(TOOL_ID, TOOL_NAME, {})
        assert result["content"] == TOOL_RESPONSE


# ── _compact_conversation ────────────────────────────────────────────────────

def make_summary_response(text="summary text", output_tokens=42):
    """Build a fake messages.create() response with .content[0].text and .usage."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.content = [block]
    response.usage.output_tokens = output_tokens
    return response


SAMPLE_CONVERSATION = [
    {"role": "user", "content": "read agent.py"},
    {"role": "assistant", "content": "ok"},
    {"role": "user", "content": "now edit it"},
    {"role": "assistant", "content": "done"},
]


class TestCompactConversation:
    def setup_method(self):
        self.client = MagicMock()
        self.agent = Agent(self.client, lambda: ("", False), [echo_tool])

    def test_replaces_conversation_with_single_summary_message(self):
        self.client.messages.create.return_value = make_summary_response(text="THE SUMMARY")
        conversation = list(SAMPLE_CONVERSATION)

        self.agent._compact_conversation(conversation)

        assert len(conversation) == 1
        assert conversation[0]["role"] == "user"
        assert conversation[0]["content"] == "THE SUMMARY"

    def test_confirmation_includes_message_count_and_token_count(self, capsys):
        self.client.messages.create.return_value = make_summary_response(output_tokens=99)
        conversation = list(SAMPLE_CONVERSATION)

        self.agent._compact_conversation(conversation)

        out = capsys.readouterr().out
        assert "4" in out
        assert "99" in out

    def test_empty_conversation_skips_api_call(self, capsys):
        conversation: list = []

        self.agent._compact_conversation(conversation)

        self.client.messages.create.assert_not_called()
        assert conversation == []
        assert capsys.readouterr().out  # something was printed

    def test_api_error_leaves_conversation_intact(self, capsys):
        self.client.messages.create.side_effect = RuntimeError("network down")
        conversation = list(SAMPLE_CONVERSATION)

        self.agent._compact_conversation(conversation)

        assert conversation == SAMPLE_CONVERSATION
        assert capsys.readouterr().out  # error line printed

    def test_empty_response_content_leaves_conversation_intact(self, capsys):
        bad_response = MagicMock()
        bad_response.content = []
        bad_response.usage.output_tokens = 0
        self.client.messages.create.return_value = bad_response
        conversation = list(SAMPLE_CONVERSATION)

        self.agent._compact_conversation(conversation)

        assert conversation == SAMPLE_CONVERSATION
        assert capsys.readouterr().out

    def test_payload_starts_with_original_messages_and_appends_prompt(self):
        self.client.messages.create.return_value = make_summary_response()
        conversation = list(SAMPLE_CONVERSATION)

        self.agent._compact_conversation(conversation)

        kwargs = self.client.messages.create.call_args.kwargs
        sent = kwargs["messages"]
        assert sent[: len(SAMPLE_CONVERSATION)] == SAMPLE_CONVERSATION
        assert sent[-1]["role"] == "user"
        prompt_text = sent[-1]["content"].lower()
        for needle in ("200 words", "file", "decision", "todo"):
            assert needle in prompt_text

    def test_uses_summary_model_not_default(self):
        self.client.messages.create.return_value = make_summary_response()
        conversation = list(SAMPLE_CONVERSATION)

        self.agent._compact_conversation(conversation)

        kwargs = self.client.messages.create.call_args.kwargs
        assert kwargs["model"] == SUMMARY_MODEL

    def test_declares_tools_on_summary_call(self):
        self.client.messages.create.return_value = make_summary_response()
        conversation = list(SAMPLE_CONVERSATION)

        self.agent._compact_conversation(conversation)

        kwargs = self.client.messages.create.call_args.kwargs
        assert kwargs["tools"]  # non-empty


# ── run loop ─────────────────────────────────────────────────────────────────

class TestRunLoop:
    def test_exits_on_user_quit(self, capsys):
        client = MagicMock()
        agent = Agent(client, lambda: ("", False), [])
        agent.run()
        output = capsys.readouterr().out
        assert "Coding Agent Ready" in output

    def test_text_response_prints_and_prompts_again(self, capsys):
        client = MagicMock()
        message = MagicMock()
        message.content = [make_text_block("hi there")]
        message.stop_reason = "end_turn"
        client.messages.stream.return_value = make_stream(message, text_chunks=["hi ", "there"])

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
        tool_message.stop_reason = "tool_use"

        text_message = MagicMock()
        text_message.content = [make_text_block("done")]
        text_message.stop_reason = "end_turn"

        client.messages.stream.side_effect = [
            make_stream(tool_message),
            make_stream(text_message, text_chunks=["done"]),
        ]

        call_count = 0
        def get_message():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "do something", True
            return "", False

        agent = Agent(client, get_message, [echo_tool])
        agent.run()
        output = capsys.readouterr().out
        assert TOOL_NAME in output
        assert "done" in output

    def test_multiple_tool_calls_in_single_response(self, capsys):
        """Claude returns two tool_use blocks in one response; both execute."""
        client = MagicMock()
        tool_message = MagicMock()
        tool_message.content = [
            make_tool_use_block(tool_id="tool_1"),
            make_tool_use_block(tool_id="tool_2"),
        ]
        tool_message.stop_reason = "tool_use"

        text_message = MagicMock()
        text_message.content = [make_text_block("both done")]
        text_message.stop_reason = "end_turn"

        client.messages.stream.side_effect = [
            make_stream(tool_message),
            make_stream(text_message, text_chunks=["both done"]),
        ]

        call_count = 0
        def get_message():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "do two things", True
            return "", False

        agent = Agent(client, get_message, [echo_tool])
        agent.run()

        # Both tool results sent back in one message (second-to-last, before assistant)
        second_call_args = client.messages.stream.call_args_list[1]
        tool_result_msg = second_call_args.kwargs["messages"][-2]
        assert tool_result_msg["role"] == "user"
        assert len(tool_result_msg["content"]) == 2
        assert tool_result_msg["content"][0]["tool_use_id"] == "tool_1"
        assert tool_result_msg["content"][1]["tool_use_id"] == "tool_2"

    def test_consecutive_tool_use_stop_reasons(self, capsys):
        """Claude calls a tool, sees the result, then calls another tool."""
        client = MagicMock()

        first_tool = MagicMock()
        first_tool.content = [make_tool_use_block(tool_id="tool_1")]
        first_tool.stop_reason = "tool_use"

        second_tool = MagicMock()
        second_tool.content = [make_tool_use_block(tool_id="tool_2")]
        second_tool.stop_reason = "tool_use"

        final_text = MagicMock()
        final_text.content = [make_text_block("all done")]
        final_text.stop_reason = "end_turn"

        client.messages.stream.side_effect = [
            make_stream(first_tool),
            make_stream(second_tool),
            make_stream(final_text, text_chunks=["all done"]),
        ]

        call_count = 0
        def get_message():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "multi step task", True
            return "", False

        agent = Agent(client, get_message, [echo_tool])
        agent.run()

        # Three API calls: first tool, second tool, final text
        assert client.messages.stream.call_count == 3
        output = capsys.readouterr().out
        assert "all done" in output

    def test_slash_compact_dispatches_and_skips_inference(self, capsys):
        """User types /compact → _compact_conversation is called, no inference happens."""
        client = MagicMock()
        # Stub the summary call so _compact_conversation actually runs end-to-end.
        client.messages.create.return_value = make_summary_response(text="summary")

        # After /compact, the user quits. No streaming inference should occur.
        call_count = 0
        def get_message():
            nonlocal call_count
            call_count += 1
            # Seed the conversation with one normal exchange before /compact,
            # otherwise the empty-conversation guard short-circuits.
            if call_count == 1:
                return "hello", True
            if call_count == 2:
                return "/compact", True
            return "", False

        # Set up the first inference (normal exchange) and the post-compact quit.
        text_message = MagicMock()
        text_message.content = [make_text_block("hi")]
        text_message.stop_reason = "end_turn"
        client.messages.stream.return_value = make_stream(text_message, text_chunks=["hi"])

        agent = Agent(client, get_message, [echo_tool])
        agent.run()

        # The summary call happened exactly once; only the pre-compact inference streamed.
        assert client.messages.create.call_count == 1
        assert client.messages.stream.call_count == 1

    def test_compact_with_trailing_whitespace_triggers(self, capsys):
        client = MagicMock()
        client.messages.create.return_value = make_summary_response()

        # Need a non-empty conversation, so prime with one user turn first.
        text_message = MagicMock()
        text_message.content = [make_text_block("ok")]
        text_message.stop_reason = "end_turn"
        client.messages.stream.return_value = make_stream(text_message, text_chunks=["ok"])

        call_count = 0
        def get_message():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "first", True
            if call_count == 2:
                return "/compact   ", True
            return "", False

        agent = Agent(client, get_message, [echo_tool])
        agent.run()

        assert client.messages.create.call_count == 1

    def test_compact_without_slash_passes_through(self):
        """Bare 'compact' is a normal message; no summary call."""
        client = MagicMock()
        text_message = MagicMock()
        text_message.content = [make_text_block("ok")]
        text_message.stop_reason = "end_turn"
        client.messages.stream.return_value = make_stream(text_message, text_chunks=["ok"])

        call_count = 0
        def get_message():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "compact", True
            return "", False

        agent = Agent(client, get_message, [])
        agent.run()

        client.messages.create.assert_not_called()
        assert client.messages.stream.call_count == 1

    def test_compact_with_args_passes_through(self):
        """'/compact me please' is not the bare token, so it flows through."""
        client = MagicMock()
        text_message = MagicMock()
        text_message.content = [make_text_block("ok")]
        text_message.stop_reason = "end_turn"
        client.messages.stream.return_value = make_stream(text_message, text_chunks=["ok"])

        call_count = 0
        def get_message():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "/compact me please", True
            return "", False

        agent = Agent(client, get_message, [])
        agent.run()

        client.messages.create.assert_not_called()
        assert client.messages.stream.call_count == 1

    def test_end_turn_without_tools_prompts_user(self, capsys):
        """stop_reason='end_turn' with no tool calls prompts for user input."""
        client = MagicMock()
        message = MagicMock()
        message.content = [make_text_block("just text")]
        message.stop_reason = "end_turn"
        client.messages.stream.return_value = make_stream(message, text_chunks=["just text"])

        call_count = 0
        def get_message():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "hello", True
            return "", False

        agent = Agent(client, get_message, [])
        agent.run()

        # Only one API call -- no tool loop
        assert client.messages.stream.call_count == 1
