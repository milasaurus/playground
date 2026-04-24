# Plan — next steps for Agent Trace Debugger

This tool exists to debug a single agent after it did something weird. The
real failure modes we care about are **multi-hop reasoning gone sideways**
and **context window pressure**. Everything below is scoped to those.

## Multi-hop reasoning

- [ ] **Thinking blocks as trace nodes.** When extended thinking is on,
  Claude's reasoning between tool calls is where loops and drift live. Capture
  each thinking block as a child of its decision so the "why" is visible next
  to the "what".
- [ ] **Loop detection.** Flag when the agent calls the same tool with near-
  identical input N turns in a row. This is the #1 symptom of a stuck agent
  and is trivial to spot once you're already tracking tool_call nodes.

## Context window pressure

- [ ] **Running token total in the header / detail panel.** Show how close
  we are to the model's context limit, not just the current turn's cost. An
  agent that quietly grows its conversation until it gets truncated is a real
  failure mode the trace today doesn't surface.
- [ ] **Cache hit/miss surfaced in the TUI.** `cache_read_input_tokens` and
  `cache_creation_input_tokens` are already on `TraceCost`; just render them.
  A cache silently stopping hitting is the usual way costs explode.
  **Note:** `ResearchAgent` doesn't use prompt caching yet (no `cache_control`
  on the system prompt or tool defs), so these counters are zero today. This
  item only pays off once caching is enabled here — or when an agent that
  does use it gets plugged in via the `Agent` protocol.

## Real errors

- [ ] **Keep tracebacks on tool errors.** Today a tool exception becomes the
  string `"error: ..."` and we lose the stack. Store the full traceback in
  `metadata` so the detail panel can show it.

## Cheapest next step

**Thinking blocks + loop detection.** Both target the multi-hop use case, both
fit the current schema as new node types or a second pass over the trace, and
together they cover the "agent got stuck in its own head" scenario this tool
is named for.
