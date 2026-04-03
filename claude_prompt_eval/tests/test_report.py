from claude_prompt_eval.models import EvalResult, ScoreResult
from claude_prompt_eval.api.report import EvalReport


def make_eval_result(version_name="v1", test_name="greeting"):
    return EvalResult(
        version_name=version_name,
        test_name=test_name,
        user_message="Hello",
        response="Hi there!",
        input_tokens=10,
        output_tokens=5,
    )


def make_score_result(version_name="v1", test_name="greeting", score=8):
    return ScoreResult(
        version_name=version_name,
        test_name=test_name,
        score=score,
        strengths="Clear response.",
        weaknesses="Could be warmer.",
        recommendation="Add a greeting.",
    )


def test_summary_contains_test_name():
    results = [make_eval_result()]
    scores = [make_score_result()]
    report = EvalReport(results, scores)

    output = report.summary()

    assert "Test: greeting" in output


def test_summary_contains_score():
    results = [make_eval_result()]
    scores = [make_score_result(score=9)]
    report = EvalReport(results, scores)

    output = report.summary()

    assert "9/10" in output


def test_summary_contains_recommendation():
    results = [make_eval_result()]
    scores = [make_score_result()]
    report = EvalReport(results, scores)

    output = report.summary()

    assert "Add a greeting." in output


def test_summary_ranks_versions():
    results = [
        make_eval_result(version_name="v1"),
        make_eval_result(version_name="v2"),
    ]
    scores = [
        make_score_result(version_name="v1", score=6),
        make_score_result(version_name="v2", score=9),
    ]
    report = EvalReport(results, scores)

    output = report.summary()

    v2_pos = output.index("v2")
    v1_pos = output.index("v1")
    # v2 should appear first in rankings section
    rankings_start = output.index("RANKINGS")
    v2_rank = output.index("v2", rankings_start)
    v1_rank = output.index("v1", rankings_start)
    assert v2_rank < v1_rank
