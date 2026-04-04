import asyncio
from anthropic import Anthropic, AsyncAnthropic
from claude_prompt_eval.models import (
    PromptVersion, EvalCase, EvalResult, USER_ROLE
)


class EvalRunner:
    """Runs test cases against prompt versions in parallel."""

    def __init__(self, client: Anthropic):
        self.client = client
        self.async_client = AsyncAnthropic(api_key=client.api_key)

    def run(
        self,
        versions: list[PromptVersion],
        test_cases: list[EvalCase],
    ) -> list[EvalResult]:
        return asyncio.run(self._run_all(versions, test_cases))

    async def _run_all(
        self,
        versions: list[PromptVersion],
        test_cases: list[EvalCase],
    ) -> list[EvalResult]:
        tasks = [
            self._run_single(version, test_case)
            for version in versions
            for test_case in test_cases
        ]
        return await asyncio.gather(*tasks)

    async def _run_single(self, version: PromptVersion, test_case: EvalCase) -> EvalResult:
        message = await self.async_client.messages.create(
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
