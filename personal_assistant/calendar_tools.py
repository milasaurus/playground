"""Calendar tools: create events and check availability. Stubs for Google Calendar / Outlook API calls."""

from typing import Any

from tool import Tool


class CreateCalendarEventTool(Tool):
    def __init__(self) -> None:
        super().__init__(
            name="create_calendar_event",
            description="Create a calendar event. Requires exact ISO datetime format.",
            input_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "start_time": {"type": "string", "description": 'ISO format: "2024-01-15T14:00:00"'},
                    "end_time": {"type": "string", "description": 'ISO format: "2024-01-15T15:00:00"'},
                    "attendees": {"type": "array", "items": {"type": "string"}, "description": "email addresses"},
                    "location": {"type": "string"},
                },
                "required": ["title", "start_time", "end_time", "attendees"],
            },
        )

    def run(self, params: dict[str, Any]) -> str:
        title = params["title"]
        start_time = params["start_time"]
        end_time = params["end_time"]
        attendees = params["attendees"]
        return f"Event created: {title} from {start_time} to {end_time} with {len(attendees)} attendees"


class GetAvailableTimeSlotsTool(Tool):
    def __init__(self) -> None:
        super().__init__(
            name="get_available_time_slots",
            description="Check calendar availability for given attendees on a specific date.",
            input_schema={
                "type": "object",
                "properties": {
                    "attendees": {"type": "array", "items": {"type": "string"}, "description": "email addresses"},
                    "date": {"type": "string", "description": 'ISO format: "2024-01-15"'},
                    "duration_minutes": {"type": "integer"},
                },
                "required": ["attendees", "date", "duration_minutes"],
            },
        )

    def run(self, params: dict[str, Any]) -> str:
        return str(["09:00", "14:00", "16:00"])
