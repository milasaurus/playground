"""Tests for the Router class in claude_conversation_engine.api.router.

Coverage:
- Registered routes are dispatched to the correct handler.
- Unregistered routes (any method/path combination) return HTTP 404
  with a JSON body describing what was not found (the missing-route handler).
- add_route() and the @route decorator both work.
- The request dict passed to a handler carries method, path, and body.
- 404 is returned regardless of HTTP verb (GET, POST, DELETE, …).
- A path registered under one verb does *not* match a different verb.
"""

import pytest

from claude_conversation_engine.api.router import Router


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_handler(status: int = 200, payload: dict | None = None):
    """Return a simple handler that always responds with *status* and *payload*."""
    response_body = payload or {"ok": True}

    def handler(request):
        return {"status": status, "body": response_body}

    return handler


# ── Route registration ────────────────────────────────────────────────────────

class TestRouteRegistration:
    def test_add_route_registers_handler(self):
        router = Router()
        handler = _make_handler()
        router.add_route("GET", "/ping", handler)

        response = router.dispatch("GET", "/ping")
        assert response["status"] == 200

    def test_decorator_registers_handler(self):
        router = Router()

        @router.route("GET", "/health")
        def health(request):
            return {"status": 200, "body": {"status": "ok"}}

        response = router.dispatch("GET", "/health")
        assert response["status"] == 200
        assert response["body"]["status"] == "ok"

    def test_multiple_routes_dispatched_independently(self):
        router = Router()
        router.add_route("GET", "/a", _make_handler(200, {"route": "a"}))
        router.add_route("GET", "/b", _make_handler(200, {"route": "b"}))

        assert router.dispatch("GET", "/a")["body"]["route"] == "a"
        assert router.dispatch("GET", "/b")["body"]["route"] == "b"

    def test_same_path_different_methods(self):
        router = Router()
        router.add_route("GET",  "/items", _make_handler(200, {"verb": "get"}))
        router.add_route("POST", "/items", _make_handler(201, {"verb": "post"}))

        assert router.dispatch("GET",  "/items")["status"] == 200
        assert router.dispatch("POST", "/items")["status"] == 201

    def test_method_is_case_insensitive_on_registration(self):
        router = Router()
        router.add_route("get", "/lower", _make_handler(200))

        # Dispatching with uppercase should still hit the handler
        response = router.dispatch("GET", "/lower")
        assert response["status"] == 200

    def test_method_is_case_insensitive_on_dispatch(self):
        router = Router()
        router.add_route("GET", "/mixed", _make_handler(200))

        response = router.dispatch("get", "/mixed")
        assert response["status"] == 200


# ── 404 missing-route handler ─────────────────────────────────────────────────

class TestMissingRoute404:
    """The core feature: any unregistered (method, path) pair must return 404."""

    def test_unknown_path_returns_404(self):
        router = Router()
        response = router.dispatch("GET", "/does-not-exist")
        assert response["status"] == 404

    def test_404_body_contains_error_key(self):
        router = Router()
        response = router.dispatch("GET", "/ghost")
        assert response["body"]["error"] == "not_found"

    def test_404_body_mentions_method_and_path(self):
        router = Router()
        response = router.dispatch("GET", "/missing")
        message = response["body"]["message"]
        assert "GET" in message
        assert "/missing" in message

    def test_404_content_type_header_is_json(self):
        router = Router()
        response = router.dispatch("GET", "/no-route")
        assert response["headers"]["Content-Type"] == "application/json"

    def test_post_to_unregistered_path_returns_404(self):
        router = Router()
        response = router.dispatch("POST", "/unknown-endpoint")
        assert response["status"] == 404

    def test_delete_to_unregistered_path_returns_404(self):
        router = Router()
        response = router.dispatch("DELETE", "/unknown-resource/42")
        assert response["status"] == 404

    def test_put_to_unregistered_path_returns_404(self):
        router = Router()
        response = router.dispatch("PUT", "/unregistered")
        assert response["status"] == 404

    def test_patch_to_unregistered_path_returns_404(self):
        router = Router()
        response = router.dispatch("PATCH", "/unregistered")
        assert response["status"] == 404

    def test_wrong_verb_for_registered_path_returns_404(self):
        """GET /items is registered; DELETE /items must still return 404."""
        router = Router()
        router.add_route("GET", "/items", _make_handler(200))

        response = router.dispatch("DELETE", "/items")
        assert response["status"] == 404

    def test_registered_path_prefix_does_not_match_longer_path(self):
        """/users is registered; /users/99 must not accidentally match."""
        router = Router()
        router.add_route("GET", "/users", _make_handler(200))

        response = router.dispatch("GET", "/users/99")
        assert response["status"] == 404

    def test_empty_router_always_returns_404(self):
        router = Router()
        for path in ["/", "/api", "/api/v1/messages", "/favicon.ico"]:
            response = router.dispatch("GET", path)
            assert response["status"] == 404, f"expected 404 for GET {path}"

    def test_root_path_unregistered_returns_404(self):
        router = Router()
        response = router.dispatch("GET", "/")
        assert response["status"] == 404

    def test_404_message_reflects_actual_method_used(self):
        router = Router()
        response = router.dispatch("DELETE", "/vanished")
        assert "DELETE" in response["body"]["message"]
        assert "/vanished" in response["body"]["message"]


# ── Request dict forwarded to handler ─────────────────────────────────────────

class TestRequestDict:
    def test_handler_receives_method_and_path(self):
        router = Router()
        received = {}

        def capture(request):
            received.update(request)
            return {"status": 200, "body": {}}

        router.add_route("POST", "/capture", capture)
        router.dispatch("POST", "/capture")

        assert received["method"] == "POST"
        assert received["path"] == "/capture"

    def test_handler_receives_body_when_provided(self):
        router = Router()
        received = {}

        def capture(request):
            received.update(request)
            return {"status": 201, "body": {}}

        router.add_route("POST", "/with-body", capture)
        payload = {"text": "hello"}
        router.dispatch("POST", "/with-body", body=payload)

        assert received["body"] == payload

    def test_handler_receives_no_body_key_when_omitted(self):
        router = Router()
        received = {}

        def capture(request):
            received.update(request)
            return {"status": 200, "body": {}}

        router.add_route("GET", "/no-body", capture)
        router.dispatch("GET", "/no-body")

        assert "body" not in received
