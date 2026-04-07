from unittest.mock import MagicMock, patch
from claude_conversation_engine.api.history import HistoryHandler, USER_ROLE, ASSISTANT_ROLE
from claude_conversation_engine.api.messages import (
    MessageHandler, DEFAULT_MODEL, DEFAULT_SYSTEM_PROMPT,
    DEFAULT_MAX_TOKENS, DEFAULT_THINKING_BUDGET,
)
from claude_conversation_engine.usage_tracking.tracker import UsageTracker

CUSTOM_MODEL = "claude-haiku-4-5-20251001"
CUSTOM_MAX_TOKENS = 512
CUSTOM_SYSTEM_PROMPT = "You are a math tutor."


def make_mock_client(text, input_tokens=10, output_tokens=5, content_blocks=None):
    mock_client = MagicMock()
    mock_stream = MagicMock()
    mock_stream.text_stream = list(text)
    mock_stream.get_final_message.return_value.usage.input_tokens = input_tokens
    mock_stream.get_final_message.return_value.usage.output_tokens = output_tokens
    if content_blocks is not None:
        mock_stream.get_final_message.return_value.content = content_blocks
    mock_client.messages.stream.return_value.__enter__ = MagicMock(return_value=mock_stream)
    mock_client.messages.stream.return_value.__exit__ = MagicMock(return_value=False)
    return mock_client


@patch("builtins.print")
def test_send_returns_response_text(mock_print):
    content = "Hello, Claudette!"
    expected = "Hello! How can I help you?"
    mock_client = make_mock_client(expected)

    history = HistoryHandler()
    tracker = UsageTracker()
    handler = MessageHandler(mock_client, history, tracker)
    result = handler.send(content)

    assert result == expected
    assert history.get_messages() == [
        {"role": USER_ROLE, "content": content},
        {"role": ASSISTANT_ROLE, "content": expected},
    ]


@patch("builtins.print")
def test_send_with_custom_model_and_max_tokens(mock_print):
    content = "Hi"
    expected = "Response"
    mock_client = make_mock_client(expected)

    history = HistoryHandler()
    tracker = UsageTracker()
    handler = MessageHandler(mock_client, history, tracker, model=CUSTOM_MODEL, max_tokens=CUSTOM_MAX_TOKENS)
    result = handler.send(content)

    assert result == expected
    assert history.get_messages() == [
        {"role": USER_ROLE, "content": content},
        {"role": ASSISTANT_ROLE, "content": expected},
    ]


@patch("builtins.print")
def test_multi_turn_conversation(mock_print):
    first_content = "What is Python?"
    first_expected = "Python is a programming language."
    second_content = "What is it used for?"
    second_expected = "It's used for web dev, data science, and more."

    mock_client = make_mock_client(first_expected, input_tokens=15, output_tokens=8)

    history = HistoryHandler()
    tracker = UsageTracker()
    handler = MessageHandler(mock_client, history, tracker)

    # First turn
    first_result = handler.send(first_content)
    assert first_result == first_expected

    # Second turn — update mock for new response
    mock_stream = mock_client.messages.stream.return_value.__enter__.return_value
    mock_stream.text_stream = list(second_expected)
    mock_stream.get_final_message.return_value.usage.input_tokens = 30
    mock_stream.get_final_message.return_value.usage.output_tokens = 12
    second_result = handler.send(second_content)
    assert second_result == second_expected

    # Verify the full conversation history is maintained
    assert history.get_messages() == [
        {"role": USER_ROLE, "content": first_content},
        {"role": ASSISTANT_ROLE, "content": first_expected},
        {"role": USER_ROLE, "content": second_content},
        {"role": ASSISTANT_ROLE, "content": second_expected},
    ]

    assert mock_client.messages.stream.call_count == 2


@patch("builtins.print")
def test_send_tracks_token_usage(mock_print):
    content = "Hello"
    expected = "Hi there!"
    input_tokens = 20
    output_tokens = 10
    mock_client = make_mock_client(expected, input_tokens, output_tokens)

    history = HistoryHandler()
    tracker = UsageTracker()
    handler = MessageHandler(mock_client, history, tracker)
    handler.send(content)

    totals = tracker.get_total()
    assert totals["total_input_tokens"] == input_tokens
    assert totals["total_output_tokens"] == output_tokens
    assert totals["total_tokens"] == input_tokens + output_tokens
    assert totals["num_turns"] == 1


@patch("builtins.print")
def test_send_uses_default_system_prompt(mock_print):
    content = "Help me"
    expected = "What do you need help with?"
    mock_client = make_mock_client(expected)

    history = HistoryHandler()
    tracker = UsageTracker()
    handler = MessageHandler(mock_client, history, tracker)
    handler.send(content)

    mock_client.messages.stream.assert_called_once_with(
        model=DEFAULT_MODEL,
        max_tokens=DEFAULT_MAX_TOKENS,
        system=DEFAULT_SYSTEM_PROMPT,
        messages=[{"role": USER_ROLE, "content": content}],
    )


@patch("builtins.print")
def test_send_with_custom_system_prompt_in_init(mock_print):
    content = "What is 2+2?"
    expected = "Think about counting."
    mock_client = make_mock_client(expected)

    history = HistoryHandler()
    tracker = UsageTracker()
    handler = MessageHandler(mock_client, history, tracker, system_prompt=CUSTOM_SYSTEM_PROMPT)
    handler.send(content)

    mock_client.messages.stream.assert_called_once_with(
        model=DEFAULT_MODEL,
        max_tokens=DEFAULT_MAX_TOKENS,
        system=CUSTOM_SYSTEM_PROMPT,
        messages=[{"role": USER_ROLE, "content": content}],
    )


@patch("builtins.print")
def test_send_with_system_prompt_override(mock_print):
    content = "Translate hello"
    expected = "Hola"
    override_prompt = "You are a translator."
    mock_client = make_mock_client(expected)

    history = HistoryHandler()
    tracker = UsageTracker()
    handler = MessageHandler(mock_client, history, tracker)
    handler.send(content, system_prompt=override_prompt)

    mock_client.messages.stream.assert_called_once_with(
        model=DEFAULT_MODEL,
        max_tokens=DEFAULT_MAX_TOKENS,
        system=override_prompt,
        messages=[{"role": USER_ROLE, "content": content}],
    )


@patch("builtins.print")
def test_send_with_thinking_enabled(mock_print):
    content = "Explain recursion"
    expected = "Recursion is when a function calls itself."

    thinking_block = MagicMock()
    thinking_block.type = "thinking"
    thinking_block.model_dump.return_value = {
        "type": "thinking",
        "thinking": "Let me think about this...",
        "signature": "sig123",
    }
    text_block = MagicMock()
    text_block.type = "text"
    text_block.model_dump.return_value = {
        "type": "text",
        "text": expected,
    }

    mock_client = make_mock_client(
        expected,
        content_blocks=[thinking_block, text_block],
    )

    history = HistoryHandler()
    tracker = UsageTracker()
    handler = MessageHandler(mock_client, history, tracker, thinking=True)
    result = handler.send(content)

    assert result == expected
    mock_client.messages.stream.assert_called_once_with(
        model=DEFAULT_MODEL,
        max_tokens=DEFAULT_MAX_TOKENS,
        system=DEFAULT_SYSTEM_PROMPT,
        messages=[{"role": USER_ROLE, "content": content}],
        thinking={
            "type": "enabled",
            "budget_tokens": DEFAULT_THINKING_BUDGET,
        },
    )


@patch("builtins.print")
def test_thinking_stores_content_blocks_in_history(mock_print):
    content = "Hello"
    expected = "Hi there!"

    thinking_block = MagicMock()
    thinking_block.type = "thinking"
    thinking_block.model_dump.return_value = {
        "type": "thinking",
        "thinking": "Simple greeting.",
        "signature": "sig456",
    }
    text_block = MagicMock()
    text_block.type = "text"
    text_block.model_dump.return_value = {
        "type": "text",
        "text": expected,
    }

    mock_client = make_mock_client(
        expected,
        content_blocks=[thinking_block, text_block],
    )

    history = HistoryHandler()
    tracker = UsageTracker()
    handler = MessageHandler(mock_client, history, tracker, thinking=True)
    handler.send(content)

    messages = history.get_messages()
    assert messages[0] == {"role": USER_ROLE, "content": content}
    assert messages[1] == {
        "role": ASSISTANT_ROLE,
        "content": [
            {"type": "thinking", "thinking": "Simple greeting.", "signature": "sig456"},
            {"type": "text", "text": expected},
        ],
    }


@patch("builtins.print")
def test_thinking_with_custom_budget(mock_print):
    content = "Hi"
    expected = "Hello!"
    custom_budget = 2048

    mock_client = make_mock_client(expected, content_blocks=[])

    history = HistoryHandler()
    tracker = UsageTracker()
    handler = MessageHandler(
        mock_client, history, tracker,
        thinking=True, thinking_budget=custom_budget,
    )
    handler.send(content)

    call_kwargs = mock_client.messages.stream.call_args.kwargs
    assert call_kwargs["thinking"] == {
        "type": "enabled",
        "budget_tokens": custom_budget,
    }


@patch("builtins.print")
def test_thinking_disabled_by_default(mock_print):
    content = "Hi"
    expected = "Hello!"
    mock_client = make_mock_client(expected)

    history = HistoryHandler()
    tracker = UsageTracker()
    handler = MessageHandler(mock_client, history, tracker)
    handler.send(content)

    call_kwargs = mock_client.messages.stream.call_args.kwargs
    assert "thinking" not in call_kwargs
