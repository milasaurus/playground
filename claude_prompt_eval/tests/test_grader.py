import json
from unittest.mock import MagicMock
from claude_prompt_eval.models import EvalResult
from claude_prompt_eval.api.grader import Grader, JUDGE_SYSTEM_PROMPT


def mock_response(text):
    return MagicMock(content=[MagicMock(text=text)])


def eval_result(version="v1", test_name="test_1"):
    return EvalResult(
        version_name=version, test_name=test_name,
        user_message="Hello", response="Hi there!",
        input_tokens=0, output_tokens=0,
    )


RECS = json.dumps(["Rec 1", "Rec 2", "Rec 3"])


def test_grade_returns_score_and_recommendations():
    result = eval_result()
    scores_json = json.dumps([{"test_name": "test_1", "score": 8, "strengths": "Good", "weaknesses": "Short"}])

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [
        mock_response(scores_json),
        mock_response(RECS),
    ]

    grades = Grader(mock_client).grade([result], {"v1": "Be helpful."})

    assert len(grades) == 1
    assert grades[0].version_name == "v1"
    assert grades[0].avg_score == 8
    assert grades[0].num_cases == 1
    assert grades[0].scores[0].score == 8
    assert grades[0].recommendations == ["Rec 1", "Rec 2", "Rec 3"]


def test_grade_sends_prompt_and_response_to_judge():
    result = eval_result()
    scores_json = json.dumps([{"test_name": "test_1", "score": 5, "strengths": "", "weaknesses": ""}])

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [
        mock_response(scores_json),
        mock_response(RECS),
    ]

    Grader(mock_client).grade([result], {"v1": "Be helpful."})

    call_args = mock_client.messages.create.call_args_list[0]
    assert call_args.kwargs["system"] == JUDGE_SYSTEM_PROMPT
    content = call_args.kwargs["messages"][0]["content"]
    assert "Be helpful." in content
    assert "Hello" in content
    assert "Hi there!" in content


def test_grade_averages_scores():
    results = [eval_result(test_name="t1"), eval_result(test_name="t2")]
    scores_json = json.dumps([
        {"test_name": "t1", "score": 6, "strengths": "", "weaknesses": ""},
        {"test_name": "t2", "score": 10, "strengths": "", "weaknesses": ""},
    ])

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [
        mock_response(scores_json),
        mock_response(RECS),
    ]

    grades = Grader(mock_client).grade(results, {"v1": "Be helpful."})

    assert grades[0].avg_score == 8.0
    assert grades[0].num_cases == 2


def test_grade_batches_at_5():
    results = [eval_result(test_name=f"t{i}") for i in range(7)]
    scores_json = json.dumps([
        {"test_name": f"t{i}", "score": 7, "strengths": "", "weaknesses": ""}
        for i in range(7)
    ])

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [
        mock_response(scores_json),  # batch 1 (5 results)
        mock_response(scores_json),  # batch 2 (2 results)
        mock_response(RECS),         # recommendations
    ]

    Grader(mock_client).grade(results, {"v1": "Be helpful."})

    assert mock_client.messages.create.call_count == 3


def test_grade_ranks_higher_score_first():
    result_a = eval_result(version="A")
    result_b = eval_result(version="B")

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [
        mock_response(json.dumps([{"test_name": "test_1", "score": 6, "strengths": "", "weaknesses": ""}])),
        mock_response(json.dumps([{"test_name": "test_1", "score": 9, "strengths": "", "weaknesses": ""}])),
        mock_response(RECS),
        mock_response(RECS),
    ]

    grades = Grader(mock_client).grade([result_a, result_b], {"A": "Concise.", "B": "Detailed."})

    assert grades[0].version_name == "B"
    assert grades[1].version_name == "A"
