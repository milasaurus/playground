# ── Setup ────────────────────────────────────────────────────────────────────

setup:
	python3 -m venv venv && source venv/bin/activate && pip install anthropic python-dotenv pytest
	$(MAKE) -C property_management_agent setup

# ── Run ──────────────────────────────────────────────────────────────────────

chat:
	source venv/bin/activate && python -m claude_conversation_engine.services.send_message

prompt:
	source venv/bin/activate && python -m claude_prompt_eval.services.evaluation

prompt-verbose:
	source venv/bin/activate && python -m claude_prompt_eval.services.evaluation --verbose

coder:
	source venv/bin/activate && python code_editing_agent/agent.py

# ── Property Management Agent (uses uv, not the root venv) ──────────────────

property-agent:
	$(MAKE) -C property_management_agent run

# ── Test ─────────────────────────────────────────────────────────────────────

test:
	source venv/bin/activate && python -m pytest claude_conversation_engine/ claude_prompt_eval/ code_editing_agent/tests/ -v

test-chat:
	source venv/bin/activate && python -m pytest claude_conversation_engine/tests/ -v

test-eval:
	source venv/bin/activate && python -m pytest claude_prompt_eval/tests/ -v

test-coder:
	source venv/bin/activate && python -m pytest code_editing_agent/tests/ -v

test-property-agent:
	$(MAKE) -C property_management_agent test
