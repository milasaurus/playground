from anthropic import Anthropic
from chatbot.api.history import HistoryHandler, USER_ROLE, ASSISTANT_ROLE
from chatbot.usage_tracking.tracker import UsageTracker


class MessageHandler:
    """Wraps the Anthropic messages API for multi-turn conversations."""

    def __init__(self, client: Anthropic, history: HistoryHandler, tracker: UsageTracker, model: str = "claude-haiku-4-5-20251001", max_tokens: int = 1024):
        self.client = client
        self.history = history
        self.tracker = tracker
        self.model = model
        self.max_tokens = max_tokens

    def send(self, content: str) -> str:
        self.history.add(USER_ROLE, content)

        message = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=self.history.get_messages()
        )

        self.tracker.record(message.usage.input_tokens, message.usage.output_tokens)

        response_text = message.content[0].text
        self.history.add(ASSISTANT_ROLE, response_text)

        return response_text
