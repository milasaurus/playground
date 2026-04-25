from unittest.mock import MagicMock, AsyncMock
from claude_prompt_eval.models import (
    PromptVersion, EvalCase, USER_ROLE, DEFAULT_MODEL, DEFAULT_MAX_TOKENS
)
from claude_prompt_eval.api.runner import EvalRunner

TEST_VERSION_NAME = "v1"
TEST_SYSTEM_PROMPT = "You are helpful."
TEST_CASE_NAME = "greeting"
TEST_USER_MESSAGE = "Hello"
TEST_RESPONSE = "Hi there!"
TEST_INPUT_TOKENS = 10
TEST_OUTPUT_TOKENS = 5


def make_mock_response(text=TEST_RESPONSE, input_tokens=TEST_INPUT_TOKENS, output_tokens=TEST_OUTPUT_TOKENS):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=text)]
    mock_response.usage.input_tokens = input_tokens
    mock_response.usage.output_tokens = output_tokens
    return mock_response


def make_mock_client():
    mock_client = MagicMock()
    mock_client.api_key = "test-key"
    return mock_client


def make_runner_with_async_mock(responses=None):
    mock_client = make_mock_client()
    runner = EvalRunner(mock_client)
    mock_async = MagicMock()
    if responses:
        mock_async.messages.create = AsyncMock(side_effect=responses)
    else:
        mock_async.messages.create = AsyncMock(return_value=make_mock_response())
    runner.async_client = mock_async
    return runner, mock_async


def test_run_single_version_single_case():
    runner, _ = make_runner_with_async_mock()

    versions = [PromptVersion(name=TEST_VERSION_NAME, system_prompt=TEST_SYSTEM_PROMPT)]
    cases = [EvalCase(name=TEST_CASE_NAME, user_message=TEST_USER_MESSAGE)]

    results = runner.run(versions, cases)

    assert len(results) == 1
    assert results[0].version_name == TEST_VERSION_NAME
    assert results[0].test_name == TEST_CASE_NAME
    assert results[0].response == TEST_RESPONSE
    assert results[0].input_tokens == TEST_INPUT_TOKENS
    assert results[0].output_tokens == TEST_OUTPUT_TOKENS


def test_run_multiple_versions():
    runner, _ = make_runner_with_async_mock()

    versions = [
        PromptVersion(name="v1", system_prompt="Be concise."),
        PromptVersion(name="v2", system_prompt="Be detailed."),
    ]
    cases = [EvalCase(name=TEST_CASE_NAME, user_message=TEST_USER_MESSAGE)]

    results = runner.run(versions, cases)

    assert len(results) == 2
    version_names = {r.version_name for r in results}
    assert version_names == {"v1", "v2"}


def test_run_multiple_cases():
    runner, _ = make_runner_with_async_mock()

    versions = [PromptVersion(name=TEST_VERSION_NAME, system_prompt=TEST_SYSTEM_PROMPT)]
    cases = [
        EvalCase(name="greeting", user_message="Hello"),
        EvalCase(name="question", user_message="What is Python?"),
    ]

    results = runner.run(versions, cases)

    assert len(results) == 2
    test_names = {r.test_name for r in results}
    assert test_names == {"greeting", "question"}


def test_run_passes_correct_params_to_api():
    runner, mock_async = make_runner_with_async_mock()

    version = PromptVersion(name=TEST_VERSION_NAME, system_prompt=TEST_SYSTEM_PROMPT)
    case = EvalCase(name=TEST_CASE_NAME, user_message=TEST_USER_MESSAGE)

    runner.run([version], [case])

    mock_async.messages.create.assert_called_once_with(
        model=DEFAULT_MODEL,
        max_tokens=DEFAULT_MAX_TOKENS,
        system=TEST_SYSTEM_PROMPT,
        messages=[{"role": USER_ROLE, "content": TEST_USER_MESSAGE}],
    )


def test_run_executes_in_parallel():
    runner, mock_async = make_runner_with_async_mock()

    versions = [PromptVersion(name="v1", system_prompt="Be helpful.")]
    cases = [EvalCase(name=f"test_{i}", user_message=f"Q{i}") for i in range(5)]

    results = runner.run(versions, cases)

    assert len(results) == 5
    assert mock_async.messages.create.call_count == 5
