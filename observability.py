"""Shared Langfuse observability for any project in this repo.

When `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are present in
the environment AND `setup_langfuse()` was called for this process,
this module instruments the Anthropic SDK via OpenTelemetry so every
`client.messages.*` call is captured as a Langfuse generation
(model name and token usage automatic).

Importing the module does nothing on its own. Tracing is opt-in
per entry point — call `setup_langfuse()` early in `main()`, before
constructing any Anthropic client. Without that call, the helpers
below are no-ops and the wrapped functions run unchanged. This lets
the same code support traced and untraced execution paths in the
same repo without conditionals scattered through call sites.

Standard pattern for an entry point that wants Langfuse tracing:

    from observability import (
        setup_langfuse, flush, observe_if_active,
        record_span_input, session_context,
    )

    def main():
        setup_langfuse()                    # before importing the client
        from client import client
        ...
        try:
            run_app()
        finally:
            flush()                         # before process exit

    @observe_if_active("my-pipeline")
    def run_pipeline(user_id: str, session_id: str):
        with session_context(session_id, tags=["my-feature"]):
            record_span_input({"user_id": user_id})
            ...

Without `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` in the
environment, the gating means projects still run normally — no
Langfuse calls and no warnings beyond Langfuse's own startup logs.
"""

import os
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable

from dotenv import load_dotenv


_setup_called = False


def langfuse_enabled() -> bool:
    """True iff both Langfuse env vars are set."""
    load_dotenv()
    return bool(os.environ.get("LANGFUSE_PUBLIC_KEY")) and bool(
        os.environ.get("LANGFUSE_SECRET_KEY")
    )


def is_active() -> bool:
    """True iff `setup_langfuse()` ran successfully in this process."""
    return _setup_called


def setup_langfuse() -> None:
    """Instrument the Anthropic SDK via OpenTelemetry. Idempotent.

    Must be called before any `Anthropic()` client is constructed —
    OTEL patches the SDK module, so a client built afterwards is
    automatically traced. No-op when env vars are missing.
    """
    global _setup_called
    if _setup_called:
        return
    if not langfuse_enabled():
        return

    from opentelemetry.instrumentation.anthropic import AnthropicInstrumentor

    AnthropicInstrumentor().instrument()
    _setup_called = True


def flush() -> None:
    """Flush any pending Langfuse spans. Call before process exit."""
    if not _setup_called:
        return

    from langfuse import get_client

    get_client().flush()


def observe_if_active(name: str) -> Callable:
    """Decorator: wrap with Langfuse `@observe` only when setup ran.

    When `setup_langfuse()` has NOT been called in this process, this
    is a no-op and the wrapped function executes normally. This keeps
    untraced entry points and tests from emitting half-traces — parent
    spans without Anthropic generation children.
    """
    def decorator(fn: Callable) -> Callable:
        from langfuse import observe
        observed_fn = observe(name=name)(fn)

        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if is_active():
                return observed_fn(*args, **kwargs)
            return fn(*args, **kwargs)

        return wrapper

    return decorator


@contextmanager
def session_context(session_id: str, tags: list[str] | None = None):
    """Attach `session_id` and `tags` to the current span. No-op when inactive."""
    if not is_active():
        yield
        return

    from langfuse import get_client, propagate_attributes

    get_client().update_current_span(input={"session_id": session_id})
    with propagate_attributes(
        session_id=session_id,
        tags=tags or [],
    ):
        yield


def record_span_input(payload: dict[str, Any]) -> None:
    """Set the `input` of the current span. No-op when inactive."""
    if not is_active():
        return

    from langfuse import get_client

    get_client().update_current_span(input=payload)
