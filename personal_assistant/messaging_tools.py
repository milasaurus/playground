"""Messaging tools: send emails. Stub for SendGrid / Gmail API calls."""

import json
from typing import Any

from tool import Tool


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
            name="report_result",
            description="Report the final result of your work. You MUST call this tool to complete your task.",
            input_schema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["success", "failed"]},
                    "recipients": {"type": "array", "items": {"type": "string"}},
                    "subject": {"type": "string"},
                    "body_summary": {"type": "string"},
                    "error": {"type": "string"},
                },
                "required": ["status"],
            },
        )

    def run(self, params: dict[str, Any]) -> str:
        return json.dumps(params)
