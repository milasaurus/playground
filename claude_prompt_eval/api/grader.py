import json
import re
from anthropic import Anthropic
from claude_prompt_eval.models import (
    EvalResult, ScoreResult, GradeReport, USER_ROLE, DEFAULT_MODEL
)

BATCH_SIZE = 5

JUDGE_SYSTEM_PROMPT = """You are an expert prompt evaluator. You will be given a batch of responses to score.

For each response, score it from 1-10 based on:
- Relevance: Does it address the user's message?
- Quality: Is it well-structured and clear?
- Prompt adherence: Does it follow the system prompt's instructions?

Respond ONLY with a JSON array. Each item must have this format:
[
    {
        "test_name": "<the test name>",
        "score": <1-10>,
        "strengths": "<what the response did well>",
        "weaknesses": "<where the response fell short>"
    }
]"""

RECOMMENDATIONS_SYSTEM_PROMPT = """You are an expert prompt engineer. You will be given:
- A system prompt
- A summary of strengths and weaknesses from multiple test cases

Based on the patterns across ALL test cases, provide exactly 3 specific, actionable recommendations to improve the system prompt.

Respond ONLY with a JSON array of 3 strings. No other text.
Example: ["Add explicit formatting instructions", "Include a constraint on response length", "Specify the target audience"]"""


class Grader:
    """Scores responses in batches using Claude as a judge and averages across all test cases."""

    def __init__(
        self,
        client: Anthropic,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 4096
    ):
        self.client = client
        self.model = model
        self.max_tokens = max_tokens

    def grade(
        self,
        results: list[EvalResult],
        system_prompts: dict[str, str],
    ) -> list[GradeReport]:
        """Grade results in batches and return averaged reports per version."""
        by_version: dict[str, list[EvalResult]] = {}
        for r in results:
            by_version.setdefault(r.version_name, []).append(r)

        all_scores: list[ScoreResult] = []
        for version_name, version_results in by_version.items():
            prompt = system_prompts[version_name]
            for i in range(0, len(version_results), BATCH_SIZE):
                batch = version_results[i:i + BATCH_SIZE]
                scores = self._grade_batch(batch, prompt)
                all_scores.extend(scores)

        version_scores: dict[str, list[ScoreResult]] = {}
        for s in all_scores:
            version_scores.setdefault(s.version_name, []).append(s)

        reports = []
        for version_name, scores in version_scores.items():
            avg = sum(s.score for s in scores) / len(scores)
            recommendations = self._recommend(system_prompts[version_name], scores)
            reports.append(GradeReport(
                version_name=version_name,
                avg_score=round(avg, 1),
                num_cases=len(scores),
                scores=scores,
                recommendations=recommendations,
            ))

        return sorted(reports, key=lambda r: r.avg_score, reverse=True)

    def _grade_batch(self, results: list[EvalResult], system_prompt: str) -> list[ScoreResult]:
        entries = []
        for r in results:
            entries.append(
                f"Test: {r.test_name}\n"
                f"User message: {r.user_message}\n"
                f"Response: {r.response}"
            )

        judge_input = (
            f"System prompt used:\n{system_prompt}\n\n"
            f"Score each of the following {len(results)} responses:\n\n"
            + "\n---\n".join(entries)
        )

        message = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=JUDGE_SYSTEM_PROMPT,
            messages=[{"role": USER_ROLE, "content": judge_input}],
        )

        raw = message.content[0].text
        json_match = re.search(r'\[[\s\S]*\]', raw)
        if not json_match:
            return [
                ScoreResult(
                    version_name=r.version_name,
                    test_name=r.test_name,
                    score=0,
                    strengths="",
                    weaknesses="",
                )
                for r in results
            ]

        parsed = json.loads(json_match.group())

        scores = []
        for i, r in enumerate(results):
            entry = parsed[i] if i < len(parsed) else {}
            scores.append(ScoreResult(
                version_name=r.version_name,
                test_name=r.test_name,
                score=entry.get("score", 0),
                strengths=entry.get("strengths", ""),
                weaknesses=entry.get("weaknesses", ""),
            ))

        return scores

    def _recommend(self, system_prompt: str, scores: list[ScoreResult]) -> list[str]:
        feedback = []
        for s in scores:
            feedback.append(f"- Strengths: {s.strengths}\n  Weaknesses: {s.weaknesses}")

        message = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=RECOMMENDATIONS_SYSTEM_PROMPT,
            messages=[{
                "role": USER_ROLE,
                "content": (
                    f"System prompt:\n{system_prompt}\n\n"
                    f"Feedback from {len(scores)} test cases:\n" + "\n".join(feedback)
                ),
            }],
        )

        raw = message.content[0].text
        json_match = re.search(r'\[[\s\S]*\]', raw)
        if not json_match:
            return ["Could not generate recommendations."]

        return json.loads(json_match.group())[:3]
