"""Tool definitions and implementations for the code-editing agent.

Each tool subclasses Tool (an ABC) and implements run(). The Agent calls
to_api_dict() to get the schema for the Anthropic API, and run() to
execute the tool locally.

Adding a new tool:
    1. Subclass Tool and implement run(params: dict) -> str.
    2. Instantiate it and append to the tools list in agent.py main().
"""

import json
import os
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

from anthropic.types import ToolParam


class Tool(ABC):
    """Base class for tools that Claude can invoke during a conversation.

    Subclasses must implement run() and provide name, description, and
    input_schema in their __init__.
    """

    def __init__(self, name: str, description: str, input_schema: dict):
        self.name = name
        self.description = description
        self.input_schema = input_schema

    def to_api_dict(self) -> ToolParam:
        """Return the dict the Anthropic API expects for tool definitions."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }

    @abstractmethod
    def run(self, params: dict) -> str:
        """Execute the tool and return a string result."""


# ── read_file ────────────────────────────────────────────────────────────────

class ReadFileTool(Tool):
    def __init__(self):
        super().__init__(
            name="read_file",
            description=(
                "Read the contents of a given relative file path. "
                "Use this when you want to see what's inside a file. "
                "Do not use this with directory names."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative path of a file in the working directory.",
                    }
                },
                "required": ["path"],
            },
        )

    def run(self, params: dict) -> str:
        path = params.get("path", "")
        with open(path, "r") as f:
            return f.read()


read_file_tool = ReadFileTool()


# ── list_files ───────────────────────────────────────────────────────────────

SKIP_DIRS = {".git", "node_modules", "venv", "__pycache__", ".venv"}


class ListFilesTool(Tool):
    def __init__(self):
        super().__init__(
            name="list_files",
            description=(
                "List files and directories at a given path. "
                "If no path is provided, lists files in the current directory."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "Optional relative path to list files from. "
                            "Defaults to current directory if not provided."
                        ),
                    }
                },
                "required": [],
            },
        )

    def run(self, params: dict) -> str:
        dir_path = params.get("path", ".") or "."
        result = []
        for entry in sorted(Path(dir_path).rglob("*")):
            if any(part in SKIP_DIRS for part in entry.parts):
                continue
            rel = entry.relative_to(dir_path)
            result.append(str(rel) + ("/" if entry.is_dir() else ""))
        return json.dumps(result)


list_files_tool = ListFilesTool()


# ── edit_file ────────────────────────────────────────────────────────────────

def _create_new_file(file_path: str, content: str) -> str:
    dir_name = os.path.dirname(file_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with open(file_path, "w") as f:
        f.write(content)
    return f"Successfully created file {file_path}"


class EditFileTool(Tool):
    def __init__(self):
        super().__init__(
            name="edit_file",
            description=(
                "Make edits to a text file.\n\n"
                "Replaces 'old_str' with 'new_str' in the given file. "
                "'old_str' and 'new_str' MUST be different from each other.\n\n"
                "If the file specified with path doesn't exist, it will be created."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "path":    {"type": "string", "description": "The path to the file"},
                    "old_str": {"type": "string", "description": "Text to search for — must match exactly and appear only once"},
                    "new_str": {"type": "string", "description": "Text to replace old_str with"},
                },
                "required": ["path", "old_str", "new_str"],
            },
        )

    def run(self, params: dict) -> str:
        path    = params.get("path", "")
        old_str = params.get("old_str", "")
        new_str = params.get("new_str", "")

        if not path or old_str == new_str:
            raise ValueError("invalid input parameters")

        if not os.path.exists(path):
            if old_str == "":
                return _create_new_file(path, new_str)
            raise FileNotFoundError(f"{path} does not exist")

        with open(path, "r") as f:
            content = f.read()

        if old_str and old_str not in content:
            raise ValueError("old_str not found in file")

        if old_str and content.count(old_str) > 1:
            raise ValueError("old_str appears multiple times in file — be more specific")

        new_content = content.replace(old_str, new_str, 1)

        with open(path, "w") as f:
            f.write(new_content)

        return "OK"


edit_file_tool = EditFileTool()


# ── run_command ──────────────────────────────────────────────────────────────

DEFAULT_TIMEOUT_SECONDS = 30


class RunCommandTool(Tool):
    def __init__(self):
        super().__init__(
            name="run_command",
            description=(
                "Run a shell command and return its stdout and stderr. "
                "Use this to run tests, install dependencies, or execute scripts. "
                "Commands time out after 30 seconds by default."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute.",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Optional timeout in seconds. Defaults to 30.",
                    },
                },
                "required": ["command"],
            },
        )

    def run(self, params: dict) -> str:
        command = params.get("command", "")
        timeout = params.get("timeout", DEFAULT_TIMEOUT_SECONDS)

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += result.stderr
        if result.returncode != 0:
            output += f"\n[exit code: {result.returncode}]"
        return output or "(no output)"


run_command_tool = RunCommandTool()
