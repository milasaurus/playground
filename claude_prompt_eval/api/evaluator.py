import json
import re
from anthropic import Anthropic
from claude_prompt_eval.models import (
    EvalResult, ScoreResult, USER_ROLE, DEFAULT_MODEL, DEFAULT_MAX_TOKENS
)

JUDGE_SYSTEM_PROMPT = """You are an expert prompt evaluator. You will be given:
- A system prompt that was used
- A user message that was sent
- The response that was generated

Score the response from 1-10 based on:
- Relevance: Does it address the user's message?
- Quality: Is it well-structured and clear?
- Prompt adherence: Does it follow the system prompt's instructions?

Respond ONLY with valid JSON in this exact format:
{
    "score": <1-10>,
    "strengths": "<what the response did well>",
    "weaknesses": "<where the response fell short>",
    "recommendation": "<specific suggestion to improve the system prompt>"
}"""


class Evaluator:
    """Uses Claude as a judge to score responses and recommend prompt iterations."""

    def __init__(
        self,
        client: Anthropic,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS
    ):
        self.client = client
        self.model = model
        self.max_tokens = max_tokens

    def score(
        self,
        results: list[EvalResult],
        system_prompts: dict[str, str],
    ) -> list[ScoreResult]:
        """Score each result using Claude as a judge.

        Args:
            results: The eval results to score.
            system_prompts: Map of version_name to the system prompt used.
        """
        scored = []
        for result in results:
            score_result = self._score_single(result, system_prompts[result.version_name])
            scored.append(score_result)
        return scored

    def _score_single(self, result: EvalResult, system_prompt: str) -> ScoreResult:
        judge_input = (
            f"System prompt used:\n{system_prompt}\n\n"
            f"User message:\n{result.user_message}\n\n"
            f"Response:\n{result.response}"
        )

        message = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=JUDGE_SYSTEM_PROMPT,
            messages=[{"role": USER_ROLE, "content": judge_input}],
        )

        raw = message.content[0].text
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if not json_match:
            return ScoreResult(
                version_name=result.version_name,
                test_name=result.test_name,
                score=0,
                strengths="",
                weaknesses="",
                recommendation=f"Judge returned invalid response: {raw[:200]}",
            )

        parsed = json.loads(json_match.group())

        return ScoreResult(
            version_name=result.version_name,
            test_name=result.test_name,
            score=parsed["score"],
            strengths=parsed["strengths"],
            weaknesses=parsed["weaknesses"],
            recommendation=parsed["recommendation"],
        )
