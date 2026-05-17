"""
Personal assistant: a supervisor agent that delegates to specialised sub-agents for calendar
scheduling and email. The supervisor sees only high-level tools (schedule_event, message_email);
the low-level API tools are hidden inside each sub-agent.
"""

import json
import os
import sys
from typing import Any
import anthropic
from pydantic import ValidationError

# Import shared observability from playground root. Must run before client construction
# so the OTEL instrumentation patches the Anthropic SDK in time.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from observability import setup_langfuse, flush

from tool import Tool, COMPLETION_TOOL_NAME
from calendar_tools import CreateCalendarEventTool, GetAvailableTimeSlotsTool, ReportCalendarResultTool
from messaging_tools import SendEmailTool, ReportEmailResultTool
from agent_prompts import CALENDAR_AGENT_PROMPT, EMAIL_AGENT_PROMPT, SUPERVISOR_PROMPT
from schemas import CalendarAgentOutput, EmailAgentOutput

setup_langfuse()
client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-6"


# --- Agent ---

COMPLETION_TOOL = COMPLETION_TOOL_NAME


class Agent:
    def __init__(self, system_prompt: str, tools: list[Tool]) -> None:
        self.system_prompt = system_prompt
        self.tools = {t.name: t for t in tools}
        self.tool_defs = [t.to_api_dict() for t in tools]
        self.messages: list[dict] = []
        self.state: dict[str, dict] = {}

    def _set_state(self, tool_name: str, status: str, result: str | None = None) -> None:
        self.state[tool_name] = {"status": status, "result": result}
        suffix = f": {result[:80]}..." if result and len(result) > 80 else f": {result}" if result else ""
        print(f"[{tool_name}] {status}{suffix}")

    def run(self, user_message: str) -> str:
        self.messages.append({"role": "user", "content": user_message})

        while True:
            response = client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=self.system_prompt,
                tools=self.tool_defs,
                messages=self.messages,
            )
            self.messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                return next(b.text for b in response.content if b.type == "text")

            # Separate completion tool from regular tools so regular calls are
            # never silently dropped if both appear in the same response.
            tool_results = []
            completion_block = None

            for block in response.content:
                if block.type != "tool_use":
                    continue
                if block.name == COMPLETION_TOOL:
                    completion_block = block
                    continue

                self._set_state(block.name, "in_progress")
                try:
                    result = self.tools[block.name].run(block.input)
                    self._set_state(block.name, "completed", result)
                except Exception as e:
                    result = f"error: {e}"
                    self._set_state(block.name, "failed", result)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

            if completion_block is not None:
                self._set_state(COMPLETION_TOOL, "completed", json.dumps(completion_block.input))
                return json.dumps(completion_block.input)

            self.messages.append({"role": "user", "content": tool_results})


# --- Sub-agent wrapper tools ---

class ScheduleEventTool(Tool):
    def __init__(self, agent: Agent) -> None:
        self.agent = agent
        super().__init__(
            name="schedule_event",
            description=(
                "Use this to create calendar events or check availability. "
                "Accepts natural language requests — handles date/time parsing, availability checking, and event creation. "
                "Returns confirmation of what was scheduled, or an explanation if no suitable slot was found. "
                "Example: 'meeting with design team next Tuesday at 2pm for 1 hour'."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "request": {"type": "string"},
                },
                "required": ["request"],
            },
        )

    def run(self, params: dict[str, Any]) -> str:
        raw = self.agent.run(params["request"])
        try:
            output = CalendarAgentOutput.model_validate_json(raw)
        except (ValidationError, json.JSONDecodeError):
            return json.dumps({"status": "failed", "error": f"malformed response: {raw[:200]}"})
        return output.model_dump_json()


class MessageEmailTool(Tool):
    def __init__(self, agent: Agent) -> None:
        self.agent = agent
        super().__init__(
            name="message_email",
            description=(
                "Use this to send emails. "
                "Accepts natural language requests — handles recipient extraction, subject generation, and email composition. "
                "Returns confirmation of what was sent. "
                "Example: 'send the design team a reminder about reviewing the new mockups'."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "request": {"type": "string"},
                },
                "required": ["request"],
            },
        )

    def run(self, params: dict[str, Any]) -> str:
        raw = self.agent.run(params["request"])
        try:
            output = EmailAgentOutput.model_validate_json(raw)
        except (ValidationError, json.JSONDecodeError):
            return json.dumps({"status": "failed", "error": f"malformed response: {raw[:200]}"})
        return output.model_dump_json()


# --- Sub-agents ---

# Handles scheduling requests: parses natural language dates, checks availability, and creates events.
calendar_agent = Agent(
    system_prompt=CALENDAR_AGENT_PROMPT,
    tools=[CreateCalendarEventTool(), GetAvailableTimeSlotsTool(), ReportCalendarResultTool()],
)

# Handles email requests: composes and sends professional emails from natural language instructions.
email_agent = Agent(
    system_prompt=EMAIL_AGENT_PROMPT,
    tools=[SendEmailTool(), ReportEmailResultTool()],
)


# --- Supervisor ---

supervisor = Agent(
    system_prompt=SUPERVISOR_PROMPT,
    tools=[ScheduleEventTool(calendar_agent), MessageEmailTool(email_agent)],
)


# --- Main ---

if __name__ == "__main__":
    query = (
        "Schedule a 1-hour meeting with the design team on 2026-05-19 at 2pm. "
        "Attendees: alice@design.com, bob@design.com. "
        "Then send them an email reminder about reviewing the new mockups."
    )
    print(f"Query: {query}\n")
    try:
        result = supervisor.run(query)
        print(f"Response: {result}")
    finally:
        flush()
