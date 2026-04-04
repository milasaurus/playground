import json
from unittest.mock import MagicMock
from claude_prompt_eval.api.generator import CaseGenerator, GENERATOR_SYSTEM_PROMPT
from claude_prompt_eval.models import USER_ROLE

PROMPT_A = "Answer in one sentence."
PROMPT_B = "Give a thorough explanation."


def make_mock_client(questions):
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content = [
        MagicMock(text=json.dumps(questions))
    ]
    return mock_client


def test_generate_returns_eval_cases():
    questions = ["What is a variable?", "Explain recursion"]
    mock_client = make_mock_client(questions)

    generator = CaseGenerator(mock_client)
    cases = generator.generate(PROMPT_A, PROMPT_B, count=2)

    assert len(cases) == 2
    assert cases[0].user_message == "What is a variable?"
    assert cases[0].name == "test_1"
    assert cases[1].user_message == "Explain recursion"
    assert cases[1].name == "test_2"


def test_generate_passes_prompts_to_claude():
    mock_client = make_mock_client(["question"])

    generator = CaseGenerator(mock_client)
    generator.generate(PROMPT_A, PROMPT_B, count=5)

    call_args = mock_client.messages.create.call_args
    assert call_args.kwargs["system"] == GENERATOR_SYSTEM_PROMPT
    content = call_args.kwargs["messages"][0]["content"]
    assert PROMPT_A in content
    assert PROMPT_B in content
    assert "5" in content


def test_generate_handles_invalid_response():
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content = [
        MagicMock(text="I can't generate questions")
    ]

    generator = CaseGenerator(mock_client)
    cases = generator.generate(PROMPT_A, PROMPT_B)

    assert cases == []
