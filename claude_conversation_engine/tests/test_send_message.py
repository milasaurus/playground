from unittest.mock import MagicMock, patch
from claude_conversation_engine.api.messages import MessageHandler
from claude_conversation_engine.usage_tracking.tracker import UsageTracker
from claude_conversation_engine.services.send_message import run_chat, EXIT_COMMAND


def make_mock_handler(responses):
    mock_handler = MagicMock(spec=MessageHandler)
    mock_handler.send.side_effect = responses
    return mock_handler


@patch("builtins.print")
def test_quit_exits_immediately(mock_print):
    mock_handler = make_mock_handler([])
    tracker = UsageTracker()
    inputs = iter([EXIT_COMMAND])
    output = []

    run_chat(mock_handler, tracker, input_fn=lambda _: next(inputs), print_fn=output.append)

    mock_handler.send.assert_not_called()


@patch("builtins.print")
def test_single_message_then_quit(mock_print):
    expected = "Hi there!"
    mock_handler = make_mock_handler([expected])
    tracker = UsageTracker()
    inputs = iter(["Hello", EXIT_COMMAND])
    output = []

    run_chat(mock_handler, tracker, input_fn=lambda _: next(inputs), print_fn=output.append)

    mock_handler.send.assert_called_once_with("Hello")
    assert f"(Type '{EXIT_COMMAND}' to exit)" in output


@patch("builtins.print")
def test_multi_turn_then_quit(mock_print):
    first_expected = "Python is a language."
    second_expected = "It's used for many things."
    mock_handler = make_mock_handler([first_expected, second_expected])
    tracker = UsageTracker()
    inputs = iter(["What is Python?", "What is it used for?", EXIT_COMMAND])
    output = []

    run_chat(mock_handler, tracker, input_fn=lambda _: next(inputs), print_fn=output.append)

    assert mock_handler.send.call_count == 2
