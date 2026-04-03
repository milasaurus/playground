from unittest.mock import MagicMock
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


def make_mock_client(text=TEST_RESPONSE, input_tokens=TEST_INPUT_TOKENS, output_tokens=TEST_OUTPUT_TOKENS):
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content = [MagicMock(text=text)]
    mock_client.messages.create.return_value.usage.input_tokens = input_tokens
    mock_client.messages.create.return_value.usage.output_tokens = output_tokens
    return mock_client


def test_run_single_version_single_case():
    mock_client = make_mock_client()
    runner = EvalRunner(mock_client)

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
    mock_client = make_mock_client()
    runner = EvalRunner(mock_client)

    versions = [
        PromptVersion(name="v1", system_prompt="Be concise."),
        PromptVersion(name="v2", system_prompt="Be detailed."),
    ]
    cases = [EvalCase(name=TEST_CASE_NAME, user_message=TEST_USER_MESSAGE)]

    results = runner.run(versions, cases)

    assert len(results) == 2
    assert results[0].version_name == "v1"
    assert results[1].version_name == "v2"


def test_run_multiple_cases():
    mock_client = make_mock_client()
    runner = EvalRunner(mock_client)

    versions = [PromptVersion(name=TEST_VERSION_NAME, system_prompt=TEST_SYSTEM_PROMPT)]
    cases = [
        EvalCase(name="greeting", user_message="Hello"),
        EvalCase(name="question", user_message="What is Python?"),
    ]

    results = runner.run(versions, cases)

    assert len(results) == 2
    assert results[0].test_name == "greeting"
    assert results[1].test_name == "question"


def test_run_passes_correct_params_to_api():
    mock_client = make_mock_client()
    runner = EvalRunner(mock_client)

    version = PromptVersion(name=TEST_VERSION_NAME, system_prompt=TEST_SYSTEM_PROMPT)
    case = EvalCase(name=TEST_CASE_NAME, user_message=TEST_USER_MESSAGE)

    runner.run([version], [case])

    mock_client.messages.create.assert_called_once_with(
        model=DEFAULT_MODEL,
        max_tokens=DEFAULT_MAX_TOKENS,
        system=TEST_SYSTEM_PROMPT,
        messages=[{"role": USER_ROLE, "content": TEST_USER_MESSAGE}],
    )
