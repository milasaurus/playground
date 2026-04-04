from claude_prompt_eval.models import EvalResult, GradeReport
from claude_prompt_eval.formatter import (
    format_header, format_prompts, format_test_case,
    format_result, format_recommendations, format_rankings,
)


class EvalReport:
    """Formats grade reports into a readable comparison."""

    def __init__(self, results: list[EvalResult], grades: list[GradeReport], prompt_map: dict[str, str] = None, verbose: bool = False):
        self.results = results
        self.grades = grades
        self.prompt_map = prompt_map or {}
        self.verbose = verbose

    def _group_by_test(self):
        all_scores = {}
        for grade in self.grades:
            for s in grade.scores:
                all_scores[(s.version_name, s.test_name)] = s

        grouped = {}
        for r in self.results:
            key = (r.version_name, r.test_name)
            pair = (r, all_scores[key])
            grouped.setdefault(r.test_name, []).append(pair)
        return grouped

    def summary(self) -> str:
        lines = format_header()

        if self.prompt_map:
            lines.extend(format_prompts(self.prompt_map))

        if self.verbose:
            for test_name, pairs in self._group_by_test().items():
                lines.extend(format_test_case(test_name, pairs[0][0].user_message))
                for result, score in pairs:
                    lines.extend(format_result(result, score))

        for grade in self.grades:
            lines.extend(format_recommendations(grade))

        version_scores = {
            g.version_name: [s.score for s in g.scores]
            for g in self.grades
        }
        lines.extend(format_rankings(version_scores))

        return "\n".join(lines)
