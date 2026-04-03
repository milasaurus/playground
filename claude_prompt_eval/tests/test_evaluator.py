import json
from unittest.mock import MagicMock
from claude_prompt_eval.models import EvalResult, USER_ROLE
from claude_prompt_eval.api.evaluator import Evaluator, JUDGE_SYSTEM_PROMPT

TEST_VERSION = "v1"
TEST_CASE = "greeting"
TEST_USER_MESSAGE = "Hello"
TEST_RESPONSE = "Hi there!"
TEST_SYSTEM_PROMPT = "You are helpful."
TEST_SCORE = 8
TEST_STRENGTHS = "Clear and friendly."
TEST_WEAKNESSES = "Could be more detailed."
TEST_RECOMMENDATION = "Add a follow-up question."


def make_judge_response():
    return json.dumps({
        "score": TEST_SCORE,
        "strengths": TEST_STRENGTHS,
        "weaknesses": TEST_WEAKNESSES,
        "recommendation": TEST_RECOMMENDATION,
    })


def make_mock_client(judge_response=None):
    mock_client = MagicMock()
    response_text = judge_response or make_judge_response()
    mock_client.messages.create.return_value.content = [MagicMock(text=response_text)]
    return mock_client


def make_eval_result():
    return EvalResult(
        version_name=TEST_VERSION,
        test_name=TEST_CASE,
        user_message=TEST_USER_MESSAGE,
        response=TEST_RESPONSE,
        input_tokens=10,
        output_tokens=5,
    )


def test_score_returns_score_result():
    mock_client = make_mock_client()
    evaluator = Evaluator(mock_client)
    result = make_eval_result()
    system_prompts = {TEST_VERSION: TEST_SYSTEM_PROMPT}

    scores = evaluator.score([result], system_prompts)

    assert len(scores) == 1
    assert scores[0].version_name == TEST_VERSION
    assert scores[0].test_name == TEST_CASE
    assert scores[0].score == TEST_SCORE
    assert scores[0].strengths == TEST_STRENGTHS
    assert scores[0].weaknesses == TEST_WEAKNESSES
    assert scores[0].recommendation == TEST_RECOMMENDATION


def test_score_passes_correct_params_to_judge():
    mock_client = make_mock_client()
    evaluator = Evaluator(mock_client)
    result = make_eval_result()
    system_prompts = {TEST_VERSION: TEST_SYSTEM_PROMPT}

    evaluator.score([result], system_prompts)

    call_args = mock_client.messages.create.call_args
    assert call_args.kwargs["system"] == JUDGE_SYSTEM_PROMPT
    assert call_args.kwargs["messages"][0]["role"] == USER_ROLE
    assert TEST_SYSTEM_PROMPT in call_args.kwargs["messages"][0]["content"]
    assert TEST_USER_MESSAGE in call_args.kwargs["messages"][0]["content"]
    assert TEST_RESPONSE in call_args.kwargs["messages"][0]["content"]


def test_score_multiple_results():
    mock_client = make_mock_client()
    evaluator = Evaluator(mock_client)
    results = [make_eval_result(), make_eval_result()]
    system_prompts = {TEST_VERSION: TEST_SYSTEM_PROMPT}

    scores = evaluator.score(results, system_prompts)

    assert len(scores) == 2
    assert mock_client.messages.create.call_count == 2
