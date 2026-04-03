USER_ROLE = "user"
ASSISTANT_ROLE = "assistant"


class HistoryHandler:
    """Manages the conversation history between the user and Claude."""

    def __init__(self):
        self.conversation: list[dict] = []

    def add(self, role: str, content: str):
        self.conversation.append({"role": role, "content": content})

    def get_messages(self) -> list[dict]:
        return list(self.conversation)

    def clear(self):
        self.conversation.clear()
