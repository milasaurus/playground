"""Pydantic output schemas for each sub-agent.

These define the structured JSON contract each sub-agent must return.
The supervisor reads explicit fields from these rather than parsing prose.
"""

from typing import Literal
from pydantic import BaseModel


class CalendarAgentOutput(BaseModel):
    status: Literal["success", "unavailable", "failed"]
    event_title: str | None = None
    date: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    attendees: list[str] = []
    error: str | None = None


class EmailAgentOutput(BaseModel):
    status: Literal["success", "failed"]
    recipients: list[str] = []
    subject: str | None = None
    body_summary: str | None = None
    error: str | None = None
