# ── Setup ────────────────────────────────────────────────────────────────────

setup:
	uv sync
	$(MAKE) -C property_management_agent setup

# ── Run ──────────────────────────────────────────────────────────────────────

chat:
	uv run python -m claude_conversation_engine.services.send_message

prompt:
	uv run python -m claude_prompt_eval.services.evaluation

prompt-verbose:
	uv run python -m claude_prompt_eval.services.evaluation --verbose

coder:
	uv run python -m code_editing_agent.agent

coder-traced:
	uv run python -m code_editing_agent.traced_main

debugger:
	uv run python -m agent_trace_debugger.main $${Q:+"$$Q"}

# Open a saved trace in the TUI. Defaults to the most recent file in
# traces/. Override with TRACE=path/to/trace.json.
tui:
	@if [ -z "$$TRACE" ] && ! ls traces/*.json >/dev/null 2>&1; then \
		echo "no traces yet — run 'make coder-traced' first or pass TRACE=path"; \
		exit 1; \
	fi
	uv run python -m agent_trace_debugger.main --load $${TRACE:-$$(ls -t traces/*.json | head -1)}

# ── Property Management Agent (its own pyproject + uv.lock) ─────────────────

property-agent:
	$(MAKE) -C property_management_agent run

# ── Test ─────────────────────────────────────────────────────────────────────

test:
	uv run python -m pytest claude_conversation_engine/ claude_prompt_eval/ code_editing_agent/tests/ agent_trace_debugger/tests/ -v

test-chat:
	uv run python -m pytest claude_conversation_engine/tests/ -v

test-eval:
	uv run python -m pytest claude_prompt_eval/tests/ -v

test-coder:
	uv run python -m pytest code_editing_agent/tests/ -v

test-debugger:
	uv run python -m pytest agent_trace_debugger/tests/ -v

test-property-agent:
	$(MAKE) -C property_management_agent test
