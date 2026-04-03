from unittest.mock import MagicMock
from core_services.chat.api.history import HistoryHandler, USER_ROLE, ASSISTANT_ROLE
from core_services.chat.api.messages import MessageHandler, DEFAULT_MODEL, DEFAULT_SYSTEM_PROMPT
from core_services.chat.usage_tracking.tracker import UsageTracker

DEFAULT_MAX_TOKENS = 1024
CUSTOM_MODEL = "claude-haiku-4-5-20251001"
CUSTOM_MAX_TOKENS = 512
CUSTOM_SYSTEM_PROMPT = "You are a math tutor."


def make_mock_client(text, input_tokens=10, output_tokens=5):
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content = [MagicMock(text=text)]
    mock_client.messages.create.return_value.usage.input_tokens = input_tokens
    mock_client.messages.create.return_value.usage.output_tokens = output_tokens
    return mock_client


def test_send_returns_response_text():
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


def test_send_with_custom_model_and_max_tokens():
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


def test_multi_turn_conversation():
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

    # Second turn — mock a new response
    mock_client.messages.create.return_value.content = [MagicMock(text=second_expected)]
    mock_client.messages.create.return_value.usage.input_tokens = 30
    mock_client.messages.create.return_value.usage.output_tokens = 12
    second_result = handler.send(second_content)
    assert second_result == second_expected

    # Verify the full conversation history is maintained
    assert history.get_messages() == [
        {"role": USER_ROLE, "content": first_content},
        {"role": ASSISTANT_ROLE, "content": first_expected},
        {"role": USER_ROLE, "content": second_content},
        {"role": ASSISTANT_ROLE, "content": second_expected},
    ]

    assert mock_client.messages.create.call_count == 2


def test_send_tracks_token_usage():
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


def test_send_uses_default_system_prompt():
    content = "Help me"
    expected = "What do you need help with?"
    mock_client = make_mock_client(expected)

    history = HistoryHandler()
    tracker = UsageTracker()
    handler = MessageHandler(mock_client, history, tracker)
    handler.send(content)

    mock_client.messages.create.assert_called_once_with(
        model=DEFAULT_MODEL,
        max_tokens=DEFAULT_MAX_TOKENS,
        system=DEFAULT_SYSTEM_PROMPT,
        messages=[{"role": USER_ROLE, "content": content}]
    )


def test_send_with_custom_system_prompt_in_init():
    content = "What is 2+2?"
    expected = "Think about counting."
    mock_client = make_mock_client(expected)

    history = HistoryHandler()
    tracker = UsageTracker()
    handler = MessageHandler(mock_client, history, tracker, system_prompt=CUSTOM_SYSTEM_PROMPT)
    handler.send(content)

    mock_client.messages.create.assert_called_once_with(
        model=DEFAULT_MODEL,
        max_tokens=DEFAULT_MAX_TOKENS,
        system=CUSTOM_SYSTEM_PROMPT,
        messages=[{"role": USER_ROLE, "content": content}]
    )


def test_send_with_system_prompt_override():
    content = "Translate hello"
    expected = "Hola"
    override_prompt = "You are a translator."
    mock_client = make_mock_client(expected)

    history = HistoryHandler()
    tracker = UsageTracker()
    handler = MessageHandler(mock_client, history, tracker)
    handler.send(content, system_prompt=override_prompt)

    mock_client.messages.create.assert_called_once_with(
        model=DEFAULT_MODEL,
        max_tokens=DEFAULT_MAX_TOKENS,
        system=override_prompt,
        messages=[{"role": USER_ROLE, "content": content}]
    )
