---
title: "feat: /compact slash command for mid-session conversation reset"
type: feat
status: active
date: 2026-04-26
deepened: 2026-04-26
origin: code_editing_agent/docs/code-editing-agent-long-context-requirements.md
---

# feat: `/compact` slash command for mid-session conversation reset

## Overview

Add a user-typed `/compact` command that summarises the conversation so
far via one Claude call, then rewrites the conversation list to a single
user message containing the summary. Implements **L2** from the
requirements doc. The original turns are dropped; the agent keeps
running in the same terminal with a much smaller working context.

## Problem Frame

Once a session is long, today's only option is quit and start over —
losing every decision, file path, and open todo. The agent already
truncates large tool results (L1 plan, completed), but that only caps
*per-call* output; it doesn't help with cumulative growth across many
turns. `/compact` gives the user a manual one-shot reset that keeps
the high-signal context (file refs, decisions, open todos) and drops
the bulk. (See origin: `code_editing_agent/docs/code-editing-agent-long-context-requirements.md`.)

## Requirements Trace

- R1 (origin L2). Typing `/compact` at the prompt summarises the
  conversation so far and replaces it with the summary.
- R2 (origin L2). Summary is one Claude call asking for ~200 words,
  preserving file references, decisions made, and open todos.
- R3 (origin L2). After compaction the conversation is rewritten to
  `[system prompt (if any)] + [summary as a single user message]` —
  original turns are dropped.
- R4 (origin L2). A short confirmation prints: `compacted N messages → M tokens`. *(Origin doc's literal wording is "N turns"; we use "messages" because `len(conversation)` includes synthetic tool-result entries that the user didn't type, so "turns" would mismatch the user's mental model — see decision below.)*
- R5 (origin "What we're not building"). Manual only — no auto-compaction,
  no thresholds, no `/clear`.
- R6 (origin success criteria). Setup is unchanged — `make coder`
  still just works. No new dependencies.

## Scope Boundaries

- Manual command only. No auto-trigger on token count, turn count, or
  any other signal.
- One slash command (`/compact`). No general slash-command dispatcher
  framework — that's overkill for one command.
- Strict match: only the literal token `/compact` (after `.strip()`)
  triggers compaction. Anything else flows through to Claude as a
  normal message. No arguments, no aliases.
- No system prompt is introduced by this work. The agent currently has
  no system prompt (see `code_editing_agent/CLAUDE.md` "What to work on
  next"). The rewritten conversation is just `[summary as a single
  user message]`. If a system prompt is added later, it lives outside
  the conversation list (passed via `system=` to the API), so this
  plan is forward-compatible.
- No persistence — the summary lives only in memory for the current run.
- No undo of compaction. Once compacted, original turns are gone.

## Context & Research

### Relevant Code and Patterns

- `code_editing_agent/agent.py` — `Agent.run()` is the input loop.
  User input is read at line 80 (`self.get_user_message()`) and
  appended to `conversation` at line 83. The slash command check
  belongs between those two points. The `conversation` list is local
  to `run()`, so the compact handler needs a reference to it (pass it
  in as a parameter).
- `code_editing_agent/agent.py` — `Agent._run_inference` (line 104)
  uses `self.client.messages.stream(...)` for the streaming chat
  loop. The summarisation call is one-shot and we don't want to print
  the summary token-by-token, so use the simpler non-streaming
  `self.client.messages.create(...)` instead. The Anthropic SDK
  exposes `.usage.output_tokens` on the response, which gives us the
  `M tokens` for the confirmation line.
- `code_editing_agent/agent.py` — `DEFAULT_MODEL` and
  `DEFAULT_MAX_TOKENS` already exist as module-level constants. Add
  the summary prompt and a max-tokens-for-summary constant alongside.
- `code_editing_agent/tests/test_agent.py` — uses `MagicMock` for the
  client and a fake `get_user_message` callable. Pattern to follow
  for the compact tests: mock `client.messages.create` to return a
  `Message`-shaped object with `.content` and `.usage`.

### Institutional Learnings

- None applicable — `docs/solutions/` does not exist in this repo yet.

### External References

- None needed. The Anthropic Python SDK's `messages.create` and the
  `Message.usage` field are already used implicitly through
  `messages.stream` (`stream.get_final_message()` returns the same
  `Message` shape).

## Key Technical Decisions

- **Strict equality match (`user_input.strip() == "/compact"`).**
  Simplest, least surprising. Anything more permissive (prefix match,
  command parser) is ceremony for one command. If a user pastes
  `/compact me please`, that goes to Claude as a normal message —
  acceptable.
- **Detection in `Agent.run()` between `get_user_message()` and the
  conversation append.** That's the natural seam: we already have the
  raw input there, and we haven't polluted the conversation yet. On
  match, call `_compact_conversation(conversation)` and `continue` to
  re-prompt without an inference call.
- **Compact lives as a method on `Agent` (`_compact_conversation`).**
  It needs `self.client` and the conversation list (passed in by
  `run()`). A free function would require threading the client
  through. Method is the right shape.
- **Use a cheaper model for the summarisation call: `SUMMARY_MODEL = "claude-haiku-4-5-20251001"`.**
  Reusing `self.model` would run Opus on a low-difficulty task —
  reading the user's own conversation back to themselves at top-tier
  rates. Haiku is well-suited for summarisation and dramatically
  cheaper. We hardcode it as a separate module-level constant
  alongside `DEFAULT_MODEL` so the choice is explicit and easy to
  change later. This is the only place in the agent that uses a
  non-default model.
- **Non-streaming `client.messages.create(...)` for the summarisation
  call.** We don't want to print the summary live, and we want
  `.usage.output_tokens` for the confirmation line. Streaming would
  add complexity for no user benefit. The one-shot call returns a
  `Message` with the same shape as `stream.get_final_message()`.
- **Pass `tools=` on the summarisation call (same list
  `_run_inference` builds).** The conversation accumulated up to this
  point contains `tool_use` and `tool_result` blocks from prior turns,
  and the Anthropic API rejects requests whose `messages` contain
  `tool_use` blocks without a matching `tools=` declaration. We don't
  expect Claude to invoke a tool on a summarisation prompt, but the
  declaration must be present or the API call fails on exactly the
  long, tool-heavy sessions `/compact` is meant for. Reuse the same
  `[t.to_api_dict() for t in self.tools]` shape as `_run_inference`,
  without `cache_control` (this is a one-shot call).
- **Mutate the conversation list in place: `conversation.clear()` then
  `conversation.append({"role": "user", "content": <summary>})`.**
  The list is owned by `run()`. Passing it into the compact method
  and mutating it keeps the loop's reference valid. Don't return a
  new list — the caller would have to rebind, easy to get wrong.
- **`N messages` in the confirmation = `len(conversation)` before clearing.**
  Each entry in `conversation` is one API message (user, assistant,
  or synthetic tool-result). We label this "messages" rather than
  "turns" (origin doc's word) because each tool round produces a
  synthetic `{role: user, content: tool_results}` entry the user did
  not type — counting those as "turns" would surprise readers (a
  3-exchange session with 2-3 tool rounds each would print "12
  turns"). "Messages" matches what's actually being counted.
- **`M tokens` in the confirmation = `response.usage.output_tokens`.**
  This is the size of the new summary in tokens — the post-compaction
  conversation's resident weight. Reading the line as "your conversation
  now costs M tokens going forward" is the intended meaning. Don't
  try to compute saved tokens or pre-compaction totals — that requires
  a separate `count_tokens` call and adds noise.
- **Summary prompt is a module-level constant (`SUMMARY_PROMPT`).**
  Easy to tweak, lives next to the other constants. Required
  substrings (asserted by tests) are spelled out in Unit 1's
  approach.
- **On summarisation API error or unparseable response, leave the
  conversation untouched and print an error line.** Don't
  half-compact. The user can retry or keep going. The same
  try/except covers both the API call and the content-block
  extraction (see Unit 1).
- **Empty-conversation guard: if `len(conversation) == 0`, print a
  short status line and skip the API call.** Avoids a wasted call
  and a confusing summary of nothing. Exact prose left to the
  implementer (see Open Questions / Deferred to Implementation).

## Open Questions

### Resolved During Planning

- Where does dispatch live? → In `Agent.run()` directly, before the
  conversation append. No dispatcher framework.
- Streaming or non-streaming for the summary call? → Non-streaming.
- Where does the summary go? → Replace `conversation` in place with
  one user message containing the summary text.
- What does the confirmation count? → `len(conversation)` before
  clearing, labelled "messages" (not "turns" — see Key Technical
  Decisions).
- How to count `M tokens`? → `response.usage.output_tokens`.
- Should the summary be printed to the user at compaction time? →
  No, just the confirmation line (per origin doc). The summary
  surfaces naturally in subsequent turns if relevant.
- What model does the summarisation call use? → `SUMMARY_MODEL`
  (Haiku 4.5), not `self.model`. Cheaper and well-suited for the
  task.
- Does `tools=` need to be passed on the summary call? → Yes, the
  payload contains `tool_use` blocks from prior turns and the API
  rejects requests without matching `tools=`.

### Deferred to Implementation

- Exact wording of the summary prompt — must contain the four
  required substrings (`200 words`, `file`, `decision`, `todo`,
  case-insensitive); other prose is the implementer's call.
- Exact wording of the empty-conversation status line and the API
  error line — short and clear, prose left to the implementer.

## Implementation Units

- [ ] **Unit 1: Add `_compact_conversation` method on `Agent`**

**Goal:** A method that takes the current conversation list, asks
Claude to summarise it, mutates the list in place to a single user
message containing the summary, and prints a confirmation. On error
or empty conversation, leaves the list untouched.

**Requirements:** R1, R2, R3, R4, R6.

**Dependencies:** None.

**Files:**
- Modify: `code_editing_agent/agent.py` (add method, add module-level
  constants `SUMMARY_PROMPT`, `SUMMARY_MODEL`, `SUMMARY_MAX_TOKENS`)
- Test: `code_editing_agent/tests/test_agent.py` (new test class for
  `_compact_conversation`)

**Approach:**
- Add `SUMMARY_PROMPT: str` near `DEFAULT_MODEL` — a single-paragraph
  instruction. The prompt's wording is left to the implementer, but
  it MUST contain the substrings (case-insensitive) `200 words`,
  `file`, `decision`, and `todo` so the contract is testable and so
  the model receives all four pieces of guidance. Tests assert these
  substrings are present in the request payload (see Test scenarios).
- Add `SUMMARY_MODEL = "claude-haiku-4-5-20251001"` next to
  `DEFAULT_MODEL`.
- Add `SUMMARY_MAX_TOKENS = 1024` (~200 words headroom).
- Method signature: `_compact_conversation(self, conversation: list[dict[str, Any]]) -> None`.
- Behaviour:
  - If `len(conversation) == 0`: print a short empty-conversation
    status line (exact prose left to implementer), return without an
    API call.
  - Build a one-shot **request payload** (separate from
    `conversation` itself): take a copy of the existing conversation
    and append a final `{role: "user", content: SUMMARY_PROMPT}`
    message. The `conversation` list is mutated only after the
    response returns — "original turns are dropped" refers to the
    post-compaction conversation state, not to the summarisation
    request input.
  - Call `self.client.messages.create(model=SUMMARY_MODEL, max_tokens=SUMMARY_MAX_TOKENS, tools=[t.to_api_dict() for t in self.tools], messages=<payload>)`.
    `tools=` is required because the payload contains `tool_use`
    blocks from earlier turns (see Key Technical Decisions).
  - Extract the summary text from `response.content[0].text`. A
    text-only response is expected because the prompt is a
    summarisation task; if `content` is empty or the first block is
    a `tool_use`, the extraction raises — that's fine, the
    surrounding try/except handles it.
  - Capture `n_messages = len(conversation)` before mutation.
  - Capture `m_tokens = response.usage.output_tokens`.
  - `conversation.clear()`; `conversation.append({"role": "user", "content": <summary>})`.
  - Print: `compacted {n_messages} messages → {m_tokens} tokens`.
- Wrap the entire flow — API call **and** content extraction — in a
  single try/except. On any exception, print a short error line
  (exact prose left to implementer) and return without mutating the
  conversation.

**Patterns to follow:**
- Module-level constants like `DEFAULT_MODEL`, `DEFAULT_MAX_TOKENS`
  in `code_editing_agent/agent.py`.
- ANSI colour usage from `Agent.run()` (yellow for agent messages,
  green for tool calls). The compact confirmation is an agent-side
  status line — yellow fits.
- Test mocking style from `code_editing_agent/tests/test_agent.py`:
  `MagicMock()` client, fake message objects with `.content` and
  `.usage`.

**Test scenarios:**
- Happy path: 4-message conversation + fake client returning a
  summary message → conversation is mutated to a single user message
  whose content equals the summary text.
- Happy path: same 4-message conversation → confirmation printed
  contains both the original message count (`4`) and the output
  token count from the fake response. Assert via substring match
  (e.g. `"4"` and the token count appear in the printed line) — do
  not pin the exact prose.
- Edge case: empty conversation → no API call made
  (`client.messages.create.assert_not_called()`), conversation
  remains empty, a short empty-conversation status line is printed
  (substring assertion only — don't pin exact wording, which is
  deferred to the implementer).
- Error path: client raises an exception → conversation length and
  contents unchanged, *something* is printed to stderr/stdout
  (substring assertion only). No traceback bubbles up.
- Error path: client returns a Message whose `content` is empty
  (`[]`) → conversation length and contents unchanged, an error
  line printed. (Verifies the try/except covers extraction, not
  just the API call.)
- Integration: API call payload — assert that the `messages`
  argument passed to `client.messages.create` (a) starts with the
  original conversation messages and (b) ends with a final
  user-role message whose content contains the four required
  substrings (case-insensitive): `200 words`, `file`, `decision`,
  `todo`. This pins the SUMMARY_PROMPT contract without pinning its
  exact wording.
- Integration: API call uses cheaper model — assert that the
  `model` argument passed to `client.messages.create` is
  `SUMMARY_MODEL`, not `DEFAULT_MODEL`.
- Integration: API call declares tools — assert that the `tools`
  argument passed to `client.messages.create` is non-empty (the
  conversation contains `tool_use` blocks, so this is required for
  the call to succeed).

**Verification:**
- `python -m pytest code_editing_agent/tests/test_agent.py -v` passes,
  including the new compact tests.

- [ ] **Unit 2: Detect `/compact` in the input loop and dispatch**

**Goal:** When the user types `/compact` at the prompt, the input
loop calls `_compact_conversation` instead of treating it as a normal
message, then re-prompts.

**Requirements:** R1, R5.

**Dependencies:** Unit 1.

**Files:**
- Modify: `code_editing_agent/agent.py` (insert dispatch in
  `Agent.run()` between input read and conversation append)
- Test: `code_editing_agent/tests/test_agent.py` (extend
  `TestRunLoop`)

**Approach:**
- After `user_input, ok = self.get_user_message()` and the `if not ok:
  break` guard, add: `if user_input.strip() == "/compact": self._compact_conversation(conversation); continue`.
- The `continue` skips the conversation-append and the inference
  call, returning to the top of the loop where `read_user_input` is
  still `True` so the user is re-prompted.
- No other changes to `run()`. The existing flow for normal messages
  is untouched.

**Patterns to follow:**
- Existing input-loop test pattern in `TestRunLoop` — fake
  `get_user_message` callable that returns a queued sequence of
  `(text, ok)` pairs, then drains.

**Test scenarios:**
- Integration: user types `/compact` first, then sends a normal
  message → `_compact_conversation` is called once with the
  conversation list (use a spy/patch on the method); after compact,
  the loop accepts a follow-up message and proceeds to inference.
- Integration: user types `/compact ` (trailing whitespace) →
  treated as compact (`.strip()` covers this).
- Integration: user types `compact` (without slash) → flows through
  to inference as a normal message; `_compact_conversation` is not
  called.
- Integration: user types `/compact me please` → flows through as a
  normal message (strict equality); `_compact_conversation` is not
  called.

**Verification:**
- `python -m pytest code_editing_agent/tests/test_agent.py -v` passes.
- `make test` (from repo root) passes.
- Smoke check: `make coder`, exchange a few messages with the agent
  including a `read_file` call, then type `/compact`. Expect to see
  the confirmation line `compacted N messages → M tokens` and to be
  re-prompted. Send a follow-up message that references something
  from before compaction (e.g. "what file did we just read?") —
  expect Claude's reply to be coherent based on the summary.

- [ ] **Unit 3: Update README to document `/compact`**

**Goal:** Users and future contributors discover the command from the
project README. CLAUDE.md says: "Update READMEs when changes affect…
commands, or features."

**Requirements:** R1.

**Dependencies:** Unit 2 (so docs match shipped behaviour).

**Files:**
- Modify: `code_editing_agent/README.md` (add a short "Slash
  commands" section near "Long-context handling")

**Approach:**
- One short section: name the command, what it does, the
  confirmation format, and the manual-only stance (no auto-compaction,
  no `/clear`).
- Mention that the original turns are dropped — make the trade-off
  clear so users don't expect undo.
- Keep the section under ~10 lines. The README is intentionally
  compact.

**Patterns to follow:**
- Tone and length of the existing "Long-context handling" section in
  the same README.

**Test scenarios:**
- Test expectation: none — documentation change with no behavioural
  surface.

**Verification:**
- README renders correctly; the new section sits naturally next to
  "Long-context handling" and "Adding a tool".

## System-Wide Impact

- **Interaction graph:** Only `Agent.run()` and a new
  `Agent._compact_conversation` method are touched. No tool
  implementations, no `_run_inference`, no `_execute_tool`. The
  `truncate_tool_output` wrapper from L1 (defined in
  `code_editing_agent/tool_definitions.py`, imported by
  `agent.py`, applied at the dispatch site in `_execute_tool`)
  keeps doing its job unchanged. See sibling plan
  `code_editing_agent/docs/truncate-tool-output-plan.md`.
- **Error propagation:** Summarisation API failures are caught inside
  `_compact_conversation` and surfaced as a printed error; they do
  not bubble out and do not break the run loop. Aligns with the
  existing pattern of `_execute_tool` catching and reporting errors.
- **State lifecycle risks:** `conversation` is mutated in place — the
  reference held by `run()` stays valid. No partial-write risk
  because mutation is atomic relative to the loop (single thread, no
  yields).
- **API surface parity:** None — the agent has no other entry points
  that would need a parallel command. `traced_main.py` reuses the
  same `Agent` class, so it gets `/compact` for free.
- **Integration coverage:** The end-to-end test in `TestRunLoop`
  drives the actual loop with a fake client, so it proves the
  dispatch path and the conversation mutation together.
- **Unchanged invariants:**
  - `Tool` ABC and all four tool implementations are untouched.
  - `_execute_tool` and `_run_inference` are untouched.
  - The L1 truncation wrapper still applies to every tool call.
  - The agent has no system prompt before this change and still has
    none after.

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| Summary loses information the user actually needs (e.g. drops a critical file path or todo). | The summary prompt explicitly asks for file references, decisions, and open todos. Smoke-test the recovery — after `/compact`, ask a follow-up that requires that info. If recovery fails repeatedly, iterate the prompt wording before considering this shipped. |
| User runs `/compact` immediately after a tool call that left the conversation in a `tool_use` waiting state. | Not possible by construction. The `/compact` check sits in the `read_user_input` branch of `run()`, which only runs when `read_user_input` is `True` — i.e. when the previous turn ended with `end_turn`, not `tool_use`. |
| The summarisation call itself fails (rate limit, network). | Caught and surfaced as a printed error; conversation left intact so the user can retry or keep going. No half-state. |
| `/compact` is typed accidentally and the user wanted to send the literal text. | Strict equality match means only the bare token triggers compaction. Anything with arguments or surrounding text passes through to Claude. The dropped turns are still gone if they did mean to compact — accept this as the cost of a manual reset. |
| Token count in the confirmation is slightly off (only counts the summary, not the saved input). | Acceptable. The number is informational. The honest meaning — "the conversation now costs roughly M tokens going forward" — is what users care about. |

## Sources & References

- **Origin document:** `code_editing_agent/docs/code-editing-agent-long-context-requirements.md`
- **Sibling plan (L1, completed):** `code_editing_agent/docs/truncate-tool-output-plan.md`
- **Agent loop:** `code_editing_agent/agent.py` (`Agent.run`, `Agent._run_inference`, `Agent._execute_tool`)
- **Test patterns:** `code_editing_agent/tests/test_agent.py` (`TestExecuteTool`, `TestRunLoop`)
- **Project conventions:** `code_editing_agent/CLAUDE.md`, `CLAUDE.md` (repo root)
