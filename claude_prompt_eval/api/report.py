from claude_prompt_eval.models import EvalResult, ScoreResult
from claude_prompt_eval.formatter import (
    format_header, format_prompts, format_test_case,
    format_result, format_rankings,
)


class EvalReport:
    """Formats eval results and scores into a readable comparison report."""

    def __init__(self, results: list[EvalResult], scores: list[ScoreResult], prompt_map: dict[str, str] = None):
        self.results = results
        self.scores = scores
        self.prompt_map = prompt_map or {}

    def _group_by_test(self) -> dict[str, list[tuple[EvalResult, ScoreResult]]]:
        score_map = {
            (s.version_name, s.test_name): s for s in self.scores
        }
        grouped: dict[str, list[tuple[EvalResult, ScoreResult]]] = {}
        for r in self.results:
            key = (r.version_name, r.test_name)
            pair = (r, score_map[key])
            grouped.setdefault(r.test_name, []).append(pair)
        return grouped

    def summary(self) -> str:
        lines = format_header()

        if self.prompt_map:
            lines.extend(format_prompts(self.prompt_map))

        for test_name, pairs in self._group_by_test().items():
            lines.extend(format_test_case(test_name, pairs[0][0].user_message))
            for result, score in pairs:
                lines.extend(format_result(result, score))

        version_scores: dict[str, list[int]] = {}
        for s in self.scores:
            version_scores.setdefault(s.version_name, []).append(s.score)
        lines.extend(format_rankings(version_scores))

        return "\n".join(lines)
