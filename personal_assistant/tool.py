"""Base Tool class for all agent tools. Subclasses define their schema and implement run()."""

from abc import ABC, abstractmethod
from typing import Any

from anthropic.types import ToolParam


class Tool(ABC):
    def __init__(self, name: str, description: str, input_schema: dict[str, Any]) -> None:
        self.name = name
        self.description = description
        self.input_schema = input_schema

    def to_api_dict(self) -> ToolParam:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }

    @abstractmethod
    def run(self, params: dict[str, Any]) -> str:
        """Execute the tool and return a string the agent sees as tool output."""
