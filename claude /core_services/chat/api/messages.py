from anthropic import Anthropic
from core_services.chat.api.history import HistoryHandler, USER_ROLE, ASSISTANT_ROLE
from core_services.chat.usage_tracking.tracker import UsageTracker


DEFAULT_MODEL = "claude-haiku-4-5-20251001"

DEFAULT_SYSTEM_PROMPT = """Give the user guidance on how to solve their problem.
Do not provide the answer directly.
Instead, ask questions and provide hints that help the user
arrive at the solution on their own."""


class MessageHandler:
    """Wraps the Anthropic messages API for multi-turn conversations."""

    def __init__(
        self,
        client: Anthropic,
        history: HistoryHandler,
        tracker: UsageTracker,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 1024
    ):
        self.client = client
        self.history = history
        self.tracker = tracker
        self.system_prompt = system_prompt
        self.model = model
        self.max_tokens = max_tokens

    def send(self, content: str, system_prompt: str = None) -> str:
        self.history.add(USER_ROLE, content)

        message = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_prompt if system_prompt is not None else self.system_prompt,
            messages=self.history.get_messages()
        )

        self.tracker.record(message.usage.input_tokens, message.usage.output_tokens)

        response_text = message.content[0].text
        self.history.add(ASSISTANT_ROLE, response_text)

        return response_text
