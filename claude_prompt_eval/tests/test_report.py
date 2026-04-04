from claude_prompt_eval.models import EvalResult, ScoreResult, GradeReport
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
    )


def make_grade(version_name="v1", test_name="greeting", score=8):
    score_result = make_score_result(version_name=version_name, test_name=test_name, score=score)
    return GradeReport(
        version_name=version_name,
        avg_score=float(score),
        num_cases=1,
        scores=[score_result],
        recommendations=["Add a greeting.", "Use a warmer tone.", "Ask a follow-up."],
    )


def test_default_hides_test_details():
    results = [make_eval_result()]
    grades = [make_grade()]
    report = EvalReport(results, grades)

    output = report.summary()

    assert "Test: greeting" not in output
    assert "Hi there!" not in output


def test_verbose_shows_test_details():
    results = [make_eval_result()]
    grades = [make_grade()]
    report = EvalReport(results, grades, verbose=True)

    output = report.summary()

    assert "Test: greeting" in output
    assert "Hi there!" in output
    assert "9/10" not in output


def test_summary_contains_score_in_rankings():
    results = [make_eval_result()]
    grades = [make_grade(score=9)]
    report = EvalReport(results, grades)

    output = report.summary()

    assert "9/10" in output


def test_summary_contains_recommendation():
    results = [make_eval_result()]
    grades = [make_grade()]
    report = EvalReport(results, grades)

    output = report.summary()

    assert "Add a greeting." in output


def test_summary_ranks_versions():
    results = [
        make_eval_result(version_name="v1"),
        make_eval_result(version_name="v2"),
    ]
    grades = [
        make_grade(version_name="v1", score=6),
        make_grade(version_name="v2", score=9),
    ]
    report = EvalReport(results, grades)

    output = report.summary()

    rankings_start = output.index("RANKINGS")
    v2_rank = output.index("v2", rankings_start)
    v1_rank = output.index("v1", rankings_start)
    assert v2_rank < v1_rank
