"""Messaging tools: send emails. Stub for SendGrid / Gmail API calls."""

import json
from typing import Any

from tool import Tool, COMPLETION_TOOL_NAME
from schemas import EmailAgentOutput


class SendEmailTool(Tool):
    def __init__(self) -> None:
        super().__init__(
            name="send_email",
            description="Send an email. Requires properly formatted addresses.",
            input_schema={
                "type": "object",
                "properties": {
                    "to": {"type": "array", "items": {"type": "string"}, "description": "email addresses"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                    "cc": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["to", "subject", "body"],
            },
        )

    def run(self, params: dict[str, Any]) -> str:
        to = params["to"]
        subject = params["subject"]
        return f"Email sent to {', '.join(to)} - Subject: {subject}"


class ReportEmailResultTool(Tool):
    def __init__(self) -> None:
        super().__init__(
            name=COMPLETION_TOOL_NAME,
            description="Report the final result of your work. You MUST call this tool to complete your task.",
            input_schema=EmailAgentOutput.model_json_schema(),
        )

    def run(self, params: dict[str, Any]) -> str:
        # Never called — the agent loop intercepts report_result before invoking run().
        # Exists only to satisfy the Tool ABC.
        return json.dumps(params)
