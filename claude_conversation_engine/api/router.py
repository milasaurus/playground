"""Lightweight HTTP router for the conversation engine API.

Registers handlers by (method, path) pairs and dispatches incoming requests.
Unregistered routes receive a 404 JSON response — the missing-route handler —
so callers always get a well-formed response regardless of the path requested.

Usage::

    router = Router()

    @router.route("GET", "/messages")
    def list_messages(request):
        return {"status": 200, "body": {"messages": []}}

    response = router.dispatch("GET", "/messages")   # → registered handler
    response = router.dispatch("GET", "/unknown")    # → 404 not-found response
"""

from __future__ import annotations

import json
from typing import Any, Callable


# Shape of every response returned by a handler or the 404 fallback.
# Keys: status (int), body (dict), headers (dict, optional).
Response = dict[str, Any]


class Router:
    """Maps (HTTP method, path) pairs to callable handlers.

    Handlers receive a ``request`` dict with at least the keys ``method``
    and ``path``, and must return a :class:`Response` dict.

    Any (method, path) combination that has not been registered is answered
    by the built-in :meth:`_not_found` handler, which returns HTTP 404.
    """

    def __init__(self) -> None:
        # Keyed by (METHOD_UPPERCASE, "/path")
        self._routes: dict[tuple[str, str], Callable[[dict], Response]] = {}

    # ── Registration ──────────────────────────────────────────────────────────

    def route(self, method: str, path: str) -> Callable:
        """Decorator that registers *handler* for the given method + path pair.

        Args:
            method: HTTP verb (case-insensitive, e.g. ``"GET"``).
            path:   URL path starting with ``/`` (e.g. ``"/messages"``).

        Returns:
            A decorator that registers the wrapped callable and returns it
            unchanged so it can still be called directly in tests.
        """
        def decorator(handler: Callable[[dict], Response]) -> Callable[[dict], Response]:
            self._routes[(method.upper(), path)] = handler
            return handler
        return decorator

    def add_route(self, method: str, path: str, handler: Callable[[dict], Response]) -> None:
        """Imperative alternative to the :meth:`route` decorator.

        Args:
            method:  HTTP verb (case-insensitive).
            path:    URL path starting with ``/``.
            handler: Callable that accepts a request dict and returns a Response.
        """
        self._routes[(method.upper(), path)] = handler

    # ── Dispatch ──────────────────────────────────────────────────────────────

    def dispatch(self, method: str, path: str, body: Any = None) -> Response:
        """Look up and call the handler registered for *method* + *path*.

        If no handler is registered the built-in 404 handler is called instead.

        Args:
            method: HTTP verb (case-insensitive).
            path:   URL path to look up.
            body:   Optional parsed request body passed into the request dict.

        Returns:
            A Response dict with at least a ``status`` key.
        """
        key = (method.upper(), path)
        handler = self._routes.get(key, self._not_found)
        request: dict[str, Any] = {"method": method.upper(), "path": path}
        if body is not None:
            request["body"] = body
        return handler(request)

    # ── Built-in handlers ─────────────────────────────────────────────────────

    @staticmethod
    def _not_found(request: dict) -> Response:
        """Default 404 handler for routes that have not been registered.

        Returns a JSON-serialisable response body that tells callers which
        method and path were not found, making debugging straightforward.
        """
        return {
            "status": 404,
            "body": {
                "error": "not_found",
                "message": (
                    f"No route registered for "
                    f"{request['method']} {request['path']}"
                ),
            },
            "headers": {"Content-Type": "application/json"},
        }
