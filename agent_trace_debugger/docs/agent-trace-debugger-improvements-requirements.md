---
date: 2026-04-24
topic: agent-trace-debugger-improvements
---

# Agent Trace Debugger — Small Improvements for Abstraction, Signal, and Verification

## Problem Frame

The debugger today captures single-agent runs as a tree of decision / tool_call /
observation nodes and renders them in a Textual TUI. That covers the original
scope (multi-hop reasoning + context window pressure) but it doesn't yet produce
data that helps answer three recurring agent-development questions:

1. **Tool abstraction level.** Are the tools we give the agent at the right
   level? Too low and it wastes calls on mechanical steps; too high and it
   can't handle edge cases.
2. **Dense signal from long trajectories.** When a run spans thousands of
   decisions, how do we attribute outcomes back to specific reasoning steps and
   bootstrap a judge we trust?
3. **Agent self-verification.** Did the agent actually read the output of the
   tests / typechecker / other verification tool before claiming success?

Scope for this brainstorm is three small, surgical additions to the existing
debugger — one per problem. None are meant to fully solve their problem; each
gives durable data we can act on.

## Requirements

**B. Per-tool usage report (Tool abstraction)**

- R1. After a run, compute per-tool aggregates over the trace's `tool_call`
  and `observation` nodes: call count, duplicate-input count, error count,
  average observation size (bytes or chars), average tool latency.
- R2. Treat two calls as duplicates when the same tool name is called with
  byte-identical `input` (after JSON canonicalization) within the same run.
  Canonicalize with `json.dumps(input, sort_keys=True, separators=(',', ':'))`
  so key-order differences don't defeat the equality check. Exact match is
  enough for v1; fuzzy match is out of scope.
- R3. Surface the report in both output modes: a new footer panel in the
  TUI, and a block printed after the tree in `--print` mode.
- R4. Subsume the "loop detection" bullet in
  `agent_trace_debugger/plan.md:14` — duplicate-input count is the loop signal.

**A. Node annotation (Dense signal from long trajectories)**

- R5. In the TUI, the selected node can be tagged as `good`, `wasted`, or
  `pivotal` via dedicated keybindings. Tags are stored in
  `TraceNode.metadata.tags` as a list of strings. Toggling a key that's
  already applied removes it.
- R6. The detail panel shows current tags for the selected node.
- R7. Annotations persist: the TUI saves the annotated trace back to disk on
  exit (or on an explicit save keybinding). Format is the existing trace JSON.
- R8. The CLI supports loading a saved trace into the TUI without running an
  agent, so annotations work on any previously-captured run (including from
  other agents wired through `run_traced`).
- R9. `main.py` auto-saves every fresh run's trace to disk under a predictable
  path so annotations can be added later. Path convention chosen in planning.

**C. Verification category + read-back heuristic (Self-verification)**

- R10. Tool registration accepts an optional `category` per tool, one of
  `verification`, `exploration`, or `mutation` (default: `exploration`).
  The category is written into `metadata.category` on `tool_call` nodes.
- R11. Post-run, for each `observation` node compute a boolean
  `metadata.output_referenced` by checking whether any ≥20-token substring
  of the observation appears in the next `decision` or `response` node
  produced by the same agent turn. Paraphrase-level references will be
  false negatives — this is accepted.
- R12. The TUI surfaces both signals: category is shown as a badge on
  `tool_call` nodes (colour *and* a single-letter label — `[V]`, `[E]`,
  `[M]` — so the signal survives monochrome terminals and colour-blind
  users); `output_referenced=false` on a `verification` observation is
  rendered with a non-colour warning marker (e.g. `!!` or a Unicode warn
  glyph).
- R13. The report from R1 gains a per-category breakdown so
  "verification calls with unread outputs" is a single, scannable number.

## Success Criteria

- After running an agent once, I can answer these three questions from the
  TUI alone, without reading the raw trace JSON:
  1. Which tool is the top candidate for changing abstraction level, and why
     (duplicate-input count, oversized observations, or high error rate)?
  2. Which nodes in this run were pivotal vs wasted (because I tagged them),
     and do those tags survive if I reopen the saved trace tomorrow?
  3. Did the agent read the verification tool's output before its next
     decision, or not?
- The `ResearchAgent` run keeps working unchanged. Existing tests pass.
  No tool needs to declare a category for the old behaviour to hold.
- A trace loaded from disk renders identically to a fresh run, plus whatever
  annotations are stored in it.

## Scope Boundaries

- **Not fixing non-determinism.** The debugger still shows *what* the model
  did, not *why* it chose to do it. Unchanged from the current README.
- **Not a full eval harness.** R5–R9 create raw material for judges; actually
  training or running a judge is a separate project.
- **Not reshaping the monorepo for agents.** R10–R13 detect symptoms of
  weak self-verification. Making `make test` fast, commands unambiguous,
  and failures loud is a different piece of work.
- **Not fuzzy duplicate detection.** R2 is exact-match only.
- **Not streaming capture.** Writes still happen end-of-run. Real-time
  capture remains on the "not here yet" list in the README.
- **Not multi-agent correlation.** Still one trace per run.

## Key Decisions

- **Three commits, ordered B → A → C.** Lowest risk first (pure aggregation,
  no schema change), then TUI interaction + persistence, then the mildly
  invasive tool-registration change. Each commit ships independently.
- **Annotations live on `TraceNode.metadata`, not a new top-level field.**
  Keeps the JSON schema stable and lets future tag types land without
  migration.
- **Read-back heuristic is lossy on purpose.** A substring check is cheap,
  requires no model call, and its false-negative mode (paraphrase) is
  explicit. A smarter check would buy marginal accuracy at real cost.
- **Category default is `exploration`.** Existing `ResearchAgent` tools
  don't need to change to keep working; only agents that care about
  verification pay the cost of categorising.

## Dependencies / Assumptions

- The current trace JSON is already annotation-friendly: `TraceNode.metadata`
  is a free-form dict and round-trips through `Trace.to_dict` /
  `Trace.from_dict`. Verified in `agent_trace_debugger/models.py`.
- `Tracer.save` and `load_trace` already exist (in
  `agent_trace_debugger/services/tracer.py` and
  `agent_trace_debugger/models.py` respectively) but are not wired into
  `main.py` — R8 and R9 activate them.
- Tool registration is currently `tool_impls: dict[str, Callable]` in
  `agent_trace_debugger/services/tool_runner.py`. R10 extends the contract;
  backwards compatibility is required (plain callables keep working).
- Plugged-in agents going through `run_traced` benefit from all three
  features automatically, since instrumentation is centralised.

## Outstanding Questions

### Resolve Before Planning

(none — all product decisions are made)

### Deferred to Planning

- [Affects R3][Technical] Where in the TUI layout does the per-tool report
  go — a new bottom panel, an overlay toggled by a key, or appended to the
  detail panel when the root node is selected?
- [Affects R7][Technical] Save-on-exit vs explicit save keybinding vs both.
  Trade-off is data loss on crash vs surprise writes to the trace file.
- [Affects R9][Technical] Save path convention for auto-saved traces —
  `traces/<trace_id>.json` at repo root, or under a user cache dir? Affects
  `.gitignore`.
- [Affects R11][Technical] Token counting for the 20-token threshold —
  reuse tiktoken-style counting or a cheap whitespace split? Accuracy here
  is not critical; cost and deps are.
- [Affects R10][Needs research] Is there a cleanest way to pass categories
  alongside impls — a second dict `tool_categories: dict[str, str]`, or a
  tagged value type, or a small `ToolSpec` dataclass — given the existing
  `ToolImpls` alias? Planning should pick the one that requires the fewest
  call-site changes in `agent_trace_debugger/agent.py` and any future
  pluggable agents.

## Next Steps

-> `/ce:plan` for structured implementation planning
