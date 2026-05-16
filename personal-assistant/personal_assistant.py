"""
Personal assistant: a supervisor agent that delegates to specialised sub-agents for calendar
scheduling and email. The supervisor sees only high-level tools (schedule_event, message_email);
the low-level API tools are hidden inside each sub-agent.
"""

from typing import Any
import anthropic

from tool import Tool
from calendar_tools import CreateCalendarEventTool, GetAvailableTimeSlotsTool
from messaging_tools import SendEmailTool
from agent_prompts import CALENDAR_AGENT_PROMPT, EMAIL_AGENT_PROMPT, SUPERVISOR_PROMPT

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-6"


# --- Agent ---

class Agent:
    def __init__(self, system_prompt: str, tools: list[Tool]) -> None:
        self.system_prompt = system_prompt
        self.tools = {t.name: t for t in tools}
        self.tool_defs = [t.to_api_dict() for t in tools]
        self.messages: list[dict] = []

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

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = self.tools[block.name].run(block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

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
        return self.agent.run(params["request"])


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
        return self.agent.run(params["request"])


# --- Sub-agents ---

# Handles scheduling requests: parses natural language dates, checks availability, and creates events.
calendar_agent = Agent(
    system_prompt=CALENDAR_AGENT_PROMPT,
    tools=[CreateCalendarEventTool(), GetAvailableTimeSlotsTool()],
)

# Handles email requests: composes and sends professional emails from natural language instructions.
email_agent = Agent(
    system_prompt=EMAIL_AGENT_PROMPT,
    tools=[SendEmailTool()],
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
    result = supervisor.run(query)
    print(f"Response: {result}")
