# ── Setup ────────────────────────────────────────────────────────────────────

setup:
	python3 -m venv venv && source venv/bin/activate && pip install anthropic python-dotenv pytest textual
	$(MAKE) -C property_management_agent setup

# ── Run ──────────────────────────────────────────────────────────────────────

chat:
	source venv/bin/activate && python -m claude_conversation_engine.services.send_message

prompt:
	source venv/bin/activate && python -m claude_prompt_eval.services.evaluation

prompt-verbose:
	source venv/bin/activate && python -m claude_prompt_eval.services.evaluation --verbose

coder:
	source venv/bin/activate && python -m code_editing_agent.agent

coder-traced:
	source venv/bin/activate && python -m code_editing_agent.traced_main

debugger:
	source venv/bin/activate && python -m agent_trace_debugger.main $${Q:+"$$Q"}

# Open a saved trace in the TUI. Defaults to the most recent file in
# traces/. Override with TRACE=path/to/trace.json.
tui:
	@if [ -z "$$TRACE" ] && ! ls traces/*.json >/dev/null 2>&1; then \
		echo "no traces yet — run 'make coder-traced' first or pass TRACE=path"; \
		exit 1; \
	fi
	source venv/bin/activate && python -m agent_trace_debugger.main --load $${TRACE:-$$(ls -t traces/*.json | head -1)}

# ── Property Management Agent (uses uv, not the root venv) ──────────────────

property-agent:
	$(MAKE) -C property_management_agent run

# ── Test ─────────────────────────────────────────────────────────────────────

test:
	source venv/bin/activate && python -m pytest claude_conversation_engine/ claude_prompt_eval/ code_editing_agent/tests/ agent_trace_debugger/tests/ -v

test-chat:
	source venv/bin/activate && python -m pytest claude_conversation_engine/tests/ -v

test-eval:
	source venv/bin/activate && python -m pytest claude_prompt_eval/tests/ -v

test-coder:
	source venv/bin/activate && python -m pytest code_editing_agent/tests/ -v

test-debugger:
	source venv/bin/activate && python -m pytest agent_trace_debugger/tests/ -v

test-property-agent:
	$(MAKE) -C property_management_agent test
