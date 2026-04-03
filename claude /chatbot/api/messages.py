from anthropic import Anthropic

USER_ROLE = "user"


class MessageHandler:
    def __init__(self, client: Anthropic):
        self.client = client

    def send(self, content: str, model: str = "claude-sonnet-4-5-20250929", max_tokens: int = 1024) -> str:
        message = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": USER_ROLE, "content": content}
            ]
        )
        return message.content[0].text
