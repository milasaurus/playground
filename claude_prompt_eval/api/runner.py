from anthropic import Anthropic
from claude_prompt_eval.models import (
    PromptVersion, EvalCase, EvalResult, USER_ROLE
)


class EvalRunner:
    """Runs test cases against prompt versions and collects results."""

    def __init__(self, client: Anthropic):
        self.client = client

    def run(
        self,
        versions: list[PromptVersion],
        test_cases: list[EvalCase],
    ) -> list[EvalResult]:
        results = []
        for version in versions:
            for test_case in test_cases:
                result = self._run_single(version, test_case)
                results.append(result)
        return results

    def _run_single(self, version: PromptVersion, test_case: EvalCase) -> EvalResult:
        message = self.client.messages.create(
            model=version.model,
            max_tokens=version.max_tokens,
            system=version.system_prompt,
            messages=[{"role": USER_ROLE, "content": test_case.user_message}],
        )
        return EvalResult(
            version_name=version.name,
            test_name=test_case.name,
            user_message=test_case.user_message,
            response=message.content[0].text,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
        )
