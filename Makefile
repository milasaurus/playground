chat:
	source venv/bin/activate && python -m claude_conversation_engine.services.send_message

prompt:
	source venv/bin/activate && python -m claude_prompt_eval.services.evaluation

prompt-verbose:
	source venv/bin/activate && python -m claude_prompt_eval.services.evaluation --verbose

test:
	source venv/bin/activate && python -m pytest claude_conversation_engine/ claude_prompt_eval/ -v

test-chat:
	source venv/bin/activate && python -m pytest core_services/claude_conversation_engine/tests/ -v

test-eval:
	source venv/bin/activate && python -m pytest claude_prompt_eval/tests/ -v

setup:
	python3 -m venv venv && source venv/bin/activate && pip install anthropic python-dotenv pytest
