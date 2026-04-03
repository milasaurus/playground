from unittest.mock import MagicMock
from chatbot.api.messages import MessageHandler, USER_ROLE

DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
DEFAULT_MAX_TOKENS = 1024
CUSTOM_MODEL = "claude-haiku-4-5-20251001"
CUSTOM_MAX_TOKENS = 512


def test_send_returns_response_text():
    content = "Hello, Claudette!"
    expected = "Hello! How can I help you?"
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content = [
        MagicMock(text=expected)
    ]

    handler = MessageHandler(mock_client)
    result = handler.send(content)

    assert result == expected
    mock_client.messages.create.assert_called_once_with(
        model=DEFAULT_MODEL,
        max_tokens=DEFAULT_MAX_TOKENS,
        messages=[{"role": USER_ROLE, "content": content}]
    )


def test_send_with_custom_model_and_max_tokens():
    content = "Hi"
    expected = "Response"
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content = [
        MagicMock(text=expected)
    ]

    handler = MessageHandler(mock_client)
    result = handler.send(content, model=CUSTOM_MODEL, max_tokens=CUSTOM_MAX_TOKENS)

    assert result == expected
    mock_client.messages.create.assert_called_once_with(
        model=CUSTOM_MODEL,
        max_tokens=CUSTOM_MAX_TOKENS,
        messages=[{"role": USER_ROLE, "content": content}]
    )
