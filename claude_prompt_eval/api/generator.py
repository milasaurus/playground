import json
import re
from anthropic import Anthropic
from claude_prompt_eval.models import EvalCase, USER_ROLE, DEFAULT_MODEL, DEFAULT_MAX_TOKENS

GENERATOR_SYSTEM_PROMPT = """You are a prompt testing expert. Given two system prompts, generate test questions that a real user would ask.

The questions should:
- Cover a wide range of difficulty (simple, moderate, complex)
- Include edge cases (vague questions, off-topic, follow-ups)
- Reveal differences between the two prompts

CRITICAL: You must return EXACTLY the number of questions requested. No more, no less.

Respond ONLY with a JSON array of strings. No other text.
Example for 3 questions: ["What is a variable?", "Explain recursion", "I don't understand"]"""


class CaseGenerator:
    """Generates test cases using Claude based on the prompts being evaluated."""

    def __init__(
        self,
        client: Anthropic,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS
    ):
        self.client = client
        self.model = model
        self.max_tokens = max_tokens

    def generate(self, prompt_a: str, prompt_b: str, count: int = 3) -> list[EvalCase]:
        message = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=GENERATOR_SYSTEM_PROMPT,
            messages=[{
                "role": USER_ROLE,
                "content": (
                    f"Generate exactly {count} test questions (no more, no less) for these two system prompts:\n\n"
                    f"Prompt A: {prompt_a}\n\n"
                    f"Prompt B: {prompt_b}"
                ),
            }],
        )

        raw = message.content[0].text
        json_match = re.search(r'\[[\s\S]*\]', raw)
        if not json_match:
            return []

        questions = json.loads(json_match.group())[:count]

        return [
            EvalCase(name=f"test_{i + 1}", user_message=q)
            for i, q in enumerate(questions)
        ]
