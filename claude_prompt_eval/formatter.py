from claude_prompt_eval.models import EvalResult, ScoreResult, GradeReport

SEPARATOR = "=" * 60
DIVIDER = "-" * 60


def score_bar(score: int) -> str:
    filled = "█" * score
    empty = "░" * (10 - score)
    return f"{filled}{empty} {score}/10"


def format_header() -> list[str]:
    return ["", SEPARATOR, "  PROMPT EVALUATION REPORT", SEPARATOR]


def format_prompts(prompt_map: dict[str, str]) -> list[str]:
    lines = ["", "  PROMPTS EVALUATED", DIVIDER]
    for name, prompt in prompt_map.items():
        lines.append(f"  {name}: \"{prompt}\"")
    lines.append("")
    return lines


def format_result(result: EvalResult, score: ScoreResult) -> list[str]:
    lines = [
        "",
        f"  >> {result.version_name}",
        f"     Score: {score_bar(score.score)}",
        f"     Tokens: {result.input_tokens} in / {result.output_tokens} out",
        "",
        f"     Response:",
    ]
    for line in result.response.split("\n"):
        lines.append(f"       {line}")
    lines.extend([
        "",
        f"     What worked:",
        f"       {score.strengths}",
        "",
        f"     What didn't:",
        f"       {score.weaknesses}",
        "",
        f"  {DIVIDER}",
    ])
    return lines


def format_recommendations(grade: GradeReport) -> list[str]:
    lines = [
        "",
        f"  HOW TO IMPROVE: {grade.version_name}",
        DIVIDER,
    ]
    for i, rec in enumerate(grade.recommendations, 1):
        lines.append(f"    {i}. {rec}")
    lines.append("")
    return lines


def format_test_case(test_name: str, user_message: str) -> list[str]:
    return ["", f"  Test: {test_name}", f"  User message: \"{user_message}\"", DIVIDER]


def format_rankings(version_scores: dict[str, list[int]]) -> list[str]:
    ranked = sorted(
        version_scores.items(),
        key=lambda x: sum(x[1]) / len(x[1]),
        reverse=True,
    )
    lines = ["", "  RANKINGS", DIVIDER]
    for i, (name, scores) in enumerate(ranked, 1):
        avg = sum(scores) / len(scores)
        medal = ["🥇", "🥈", "🥉"][i - 1] if i <= 3 else f"  {i}."
        lines.append(f"  {medal} {name} — {score_bar(int(round(avg)))} (avg)")
    lines.extend(["", SEPARATOR])
    return lines
