---
title: "feat: cap and truncate large tool results"
type: feat
status: completed
date: 2026-04-25
origin: code_editing_agent/docs/code-editing-agent-long-context-requirements.md
---

# feat: cap and truncate large tool results

## Overview

Wrap every tool's output before it goes into the conversation. If the
result exceeds a threshold, keep the head and tail and replace the
middle with a marker that tells the agent both that content was cut
and how to recover the rest. Implements **L1** from the requirements
doc.

## Problem Frame

Tool output is the single biggest source of context growth in this
agent — a 1,000-line `read_file` or a verbose `pytest` run dumps
everything into the conversation, and it stays there for the rest of
the session. Today there's no cap, so one bad call can blow the
budget. (See origin: `code_editing_agent/docs/code-editing-agent-long-context-requirements.md`.)

## Requirements Trace

- R1 (origin L1). Tool results above a threshold are truncated to
  head + marker + tail before being added to the conversation.
- R2 (origin success criteria). The agent can `read_file` a
  2,000-line file or run `pytest -v` without the next ten turns paying
  for it.
- R3 (origin success criteria). Setup is unchanged — `make coder`
  still just works. No new dependencies.

## Scope Boundaries

- One wrapper applied at the dispatch site — no per-tool truncation
  rules.
- No retroactive truncation of already-stored tool results.
- No per-tool overrides or knobs in v1 (single threshold for all
  tools).
- Errors caught in `_execute_tool` flow through the same wrapper. No
  separate error-truncation path.

## Context & Research

### Relevant Code and Patterns

- `code_editing_agent/agent.py` — `Agent._execute_tool` at line 119
  is the central dispatch site. It calls `tool_def.run(input)`,
  catches exceptions, and wraps the string result into a `tool_result`
  dict. This is the only place we need to touch.
- `code_editing_agent/tool_definitions.py` — `Tool` ABC plus four
  implementations (`ReadFileTool`, `ListFilesTool`, `EditFileTool`,
  `RunCommandTool`). Each `run(params: dict) -> str`. We don't change
  any of them.
- `code_editing_agent/tests/test_tools.py` — pytest, function-style.
  Direct `tool.run({...})` calls and plain assertions. Pattern to
  follow for truncation tests.
- `code_editing_agent/tests/test_agent.py` — uses a fake client and
  fake tools to exercise `Agent.run()`. Pattern to follow for the
  end-to-end truncation test.

### Institutional Learnings

- None applicable from `docs/solutions/`.

## Key Technical Decisions

- **Wrap at the dispatch site, not in the `Tool` base class.** A
  single change in `Agent._execute_tool` covers every tool — current
  and future — without subclasses needing to know about truncation.
- **Threshold = 4,000 chars; head = 2,000; tail = 1,000.** Carried
  from the requirements doc. Roughly fits a typical 1k-token budget
  per tool result. Constants live as module-level names so they can
  be tweaked in one place.
- **Marker contains: `(a)` "content was omitted" signal, `(b)`
  approximate omitted byte/line count, `(c)` concrete recovery hints
  (`grep`, `head`, `offset/limit`).** All three jobs the marker has
  to do — see the README's "Long-context handling" section for the
  rationale. Exact wording is left to the implementer; the contract
  is the three pieces.
- **Helper lives in `code_editing_agent/tool_definitions.py` as a
  module-level function.** It's about tool output, the file's already
  imported by `agent.py`, and adding a new module just for this is
  ceremony.
- **Pure function, no state.** `truncate_tool_output(text: str) ->
  str`. Easy to unit-test, no globals besides the size constants.

## Open Questions

### Resolved During Planning

- Where does the wrapper live? → `Agent._execute_tool` in
  `agent.py`, calling a helper in `tool_definitions.py`.
- Per-tool override? → Not in v1.
- Should errors also pass through truncation? → Yes, by virtue of
  living at the dispatch site. No separate path needed.

### Deferred to Implementation

- Exact marker text — specify the three required pieces, let the
  implementer write the prose.

## Implementation Units

- [x] **Unit 1: Add `truncate_tool_output` helper**

**Goal:** A pure function that takes a string and returns either the
original (if short) or `head + marker + tail` (if long).

**Requirements:** R1, R3.

**Dependencies:** None.

**Files:**
- Modify: `code_editing_agent/tool_definitions.py` (add helper +
  three module-level constants near the top of the file)
- Test: `code_editing_agent/tests/test_tools.py` (add a new section
  with truncation tests)

**Approach:**
- Define `MAX_OUTPUT_CHARS = 4000`, `HEAD_CHARS = 2000`,
  `TAIL_CHARS = 1000` as module-level constants.
- Define `truncate_tool_output(text: str) -> str` that:
  - Returns `text` unchanged when `len(text) <= MAX_OUTPUT_CHARS`.
  - Otherwise returns `text[:HEAD_CHARS] + marker + text[-TAIL_CHARS:]`
    where the marker is a short bracketed string containing the
    omitted character count and at least one recovery hint
    (`grep`, `head`, or `offset/limit`).
- No mutation of the input, no logging, no side effects.

**Patterns to follow:**
- Module-level constants like `SKIP_DIRS` and `DEFAULT_TIMEOUT_SECONDS`
  in `code_editing_agent/tool_definitions.py`.
- Test style from `code_editing_agent/tests/test_tools.py` — direct
  function calls, plain assertions, one behaviour per test.

**Test scenarios:**
- Happy path: short string (length below threshold) → returned
  unchanged.
- Happy path: empty string → returned unchanged.
- Edge case: string of length exactly equal to `MAX_OUTPUT_CHARS` →
  returned unchanged (boundary).
- Edge case: string of length `MAX_OUTPUT_CHARS + 1` → truncated;
  result length is roughly `HEAD_CHARS + len(marker) + TAIL_CHARS`,
  not the original length.
- Happy path: long string → result starts with the first `HEAD_CHARS`
  of input and ends with the last `TAIL_CHARS` of input.
- Happy path: long string → marker is present in the result and
  contains the omitted character count (substring assertion is fine
  — don't pin exact wording).
- Happy path: long string → marker mentions at least one recovery
  hint (`grep`, `head`, or `offset` — substring assertion).

**Verification:**
- `python -m pytest code_editing_agent/tests/test_tools.py -v` passes,
  including the new truncation tests.

- [x] **Unit 2: Apply the wrapper in `Agent._execute_tool`**

**Goal:** Every tool result that reaches the conversation passes
through `truncate_tool_output`, so the cap is enforced uniformly.

**Requirements:** R1, R2.

**Dependencies:** Unit 1.

**Files:**
- Modify: `code_editing_agent/agent.py` (import the helper, apply it
  in `_execute_tool`)
- Test: `code_editing_agent/tests/test_agent.py` (add one
  end-to-end test confirming a long tool response gets truncated)

**Approach:**
- Import `truncate_tool_output` from `tool_definitions` in
  `code_editing_agent/agent.py`.
- In `Agent._execute_tool` (currently `code_editing_agent/agent.py`
  around line 119), wrap the string `response` from
  `tool_def.run(input)` with `truncate_tool_output(...)` before
  putting it into the `tool_result` dict.
- Apply the same wrap to the error-path string `str(e)` in the
  `except Exception` branch — uniform behaviour, no special-casing.

**Patterns to follow:**
- The existing import block in `agent.py` already pulls names from
  `tool_definitions`. Add `truncate_tool_output` to that import.
- Existing `_execute_tool` test pattern in
  `code_editing_agent/tests/test_agent.py` — fake tools that return
  controlled strings, fake client whose responses queue tool calls.

**Test scenarios:**
- Integration: a fake tool returning a string longer than
  `MAX_OUTPUT_CHARS` → the resulting `tool_result` `content` length is
  shorter than the input and contains the truncation marker.
- Integration: a fake tool returning a short string → the resulting
  `tool_result` `content` is unchanged.
- Integration: a tool that raises an exception with a normal-length
  message → `tool_result` `content` is the message verbatim and
  `is_error` is `True` (regression test — existing behaviour
  preserved).

**Verification:**
- `python -m pytest code_editing_agent/tests/test_agent.py -v` passes,
  including the new truncation test.
- `make test` (from repo root) passes.
- Smoke check: `make coder`, ask the agent to `read_file` a long file
  in the repo (e.g. `code_editing_agent/agent.py`) — observe the
  marker in the agent's response or in trace output, confirm the
  agent can still answer follow-up questions about the file.

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| Marker wording is unclear and the agent doesn't recover. | Tests assert the marker contains a recovery hint. Validate via smoke test that the agent actually calls `grep`/`head`/narrower `read_file` after seeing it. If not, iterate on the marker text. |
| Truncating an error message breaks debugging. | Errors are usually short (`str(e)` of a caught exception). The wrapper is a no-op on short strings, so this only kicks in for pathologically long error text — acceptable for v1. |
| Threshold is wrong for real workloads. | Constants are module-level and easy to tweak in one place. Treat 4,000 chars as a starting point and adjust based on observed traces. |

## Sources & References

- **Origin document:** `code_editing_agent/docs/code-editing-agent-long-context-requirements.md`
- **README rationale:** `code_editing_agent/README.md` ("Long-context handling" section).
- **Dispatch site:** `code_editing_agent/agent.py` `_execute_tool`.
- **Tool implementations:** `code_editing_agent/tool_definitions.py`.
