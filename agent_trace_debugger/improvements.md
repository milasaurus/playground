# Improvements — next steps for Agent Trace Debugger

This tool exists to debug a single agent after it did something weird. The
failure modes worth engineering against are **multi-hop reasoning gone
sideways** and **context window pressure**. Improvements below are organised
from biggest-initiative to smallest-tactical; everything is scoped to those
two problems plus a few questions the current trace can't yet answer.

## Three headline initiatives

Ordered **B → A → C** (lowest-risk-first). Each ships as an independent
commit.

### B. Per-tool usage report

*Question it answers: are the tools we give the agent at the right
abstraction level?*

- [ ] After a run, compute per-tool aggregates over `tool_call` and
  `observation` nodes: call count, duplicate-input count, error count,
  average observation size, average tool latency.
- [ ] Treat two calls as duplicates when the same tool name is called with
  byte-identical `input` after JSON canonicalisation (`sort_keys=True,
  separators=(',', ':')`) in the same run. Exact match only; fuzzy match is
  out of scope.
- [ ] Surface the report in both output modes: a new footer panel in the
  TUI, and a block printed after the tree in `--print` mode.
- [ ] Subsumes the earlier "loop detection" item — duplicate-input count is
  the loop signal.

### A. Node annotation

*Question it answers: when a run spans thousands of nodes, which ones were
pivotal and which were wasted?*

- [ ] Let the user tag the selected node in the TUI as `good`, `wasted`, or
  `pivotal` via dedicated keybindings. Store tags on
  `TraceNode.metadata.tags` as a list. Toggling an applied tag removes it.
- [ ] Show current tags for the selected node in the detail panel.
- [ ] Persist annotations — save the annotated trace back to disk on exit
  (format: existing trace JSON, no schema change).
- [ ] Support loading a saved trace into the TUI without running an agent,
  so annotations work on any prior run (including other agents wired
  through `run_traced`).
- [ ] Auto-save every fresh run's trace under a predictable path so
  annotations can be added later.

### C. Verification category + read-back heuristic

*Question it answers: did the agent actually read the verification tool's
output before claiming success?*

- [ ] Tool registration accepts an optional `category` per tool
  (`verification` / `exploration` / `mutation`; default `exploration`).
  Category is written to `metadata.category` on `tool_call` nodes.
- [ ] Post-run, compute `metadata.output_referenced` on each `observation`:
  a boolean for whether any ≥20-token substring of the observation appears
  in the next `decision`/`response` from the same turn. Paraphrase-level
  references are accepted false negatives — cheap substring match, no model
  call.
- [ ] Surface in the TUI: category as a badge on `tool_call` nodes (colour
  *and* a single-letter label — `[V]`, `[E]`, `[M]` — so signal survives
  monochrome / colour-blind terminals). `output_referenced=false` on a
  `verification` observation gets a non-colour warning marker.
- [ ] Per-tool report (B) gains a per-category breakdown so "verification
  calls with unread outputs" is a single scannable number.

## Tactical improvements

Smaller items that fit the current schema and don't need new initiatives.

### Multi-hop reasoning
- [ ] **Thinking blocks as trace nodes.** When extended thinking is on,
  Claude's reasoning between tool calls is where loops and drift live.
  Capture each thinking block as a child of its decision.

### Context window pressure
- [ ] **Running token total in the header / detail panel.** Show how close
  we are to the model's context limit, not just the current turn's cost.
- [ ] **Cache hit/miss surfaced in the TUI.** `cache_read_input_tokens` and
  `cache_creation_input_tokens` are already on `TraceCost`; just render
  them. Note: `ResearchAgent` doesn't use prompt caching today (no
  `cache_control`), so these counters are zero until caching is enabled
  here or an agent that uses it is plugged in.

### Real errors
- [ ] **Keep tracebacks on tool errors.** Today a tool exception becomes
  `"error: ..."` and we lose the stack. Store the full traceback in
  `metadata`.
- [ ] **Render web_search result bodies, not just title + URL.** Current
  observation is `"N result(s): - title — url"`. For debugging a multi-hop
  chain we want the snippet Claude actually read.

## Scope boundaries

What this tool is **not** trying to do, even as it grows:

- **Not fixing non-determinism.** Still shows *what* the model did, not
  *why* it chose to do it.
- **Not a full eval harness.** Annotations (A) create raw material for
  judges; training or running a judge is a separate project.
- **Not reshaping the monorepo for agents.** C detects symptoms of weak
  self-verification; making `make test` fast, commands unambiguous, and
  failures loud is different work.
- **Not fuzzy duplicate detection.** B is exact-match only.
- **Not streaming capture.** Writes still happen end-of-run.
- **Not multi-agent correlation.** Still one trace per run.

## Key decisions carried forward

- **Annotations live on `TraceNode.metadata`, not a new top-level field.**
  Keeps the JSON schema stable and lets future tag types land without
  migration.
- **Read-back heuristic is lossy on purpose.** Substring check is cheap,
  no model call, explicit false-negative mode.
- **Category default is `exploration`.** Existing agents don't need to
  change; only agents that care about verification pay the cost.
- **Cheapest next step: thinking blocks + the B report.** Both are
  schema-compatible, both address the "agent got stuck in its own head"
  scenario this tool is named for, and the B report replaces the
  loop-detection bullet that used to be a separate line item.

## Outstanding questions

Deferred to planning:

- [Affects B] Where in the TUI layout does the per-tool report go — a new
  bottom panel, an overlay toggled by a key, or appended to the detail
  panel when the root node is selected?
- [Affects A] Save-on-exit vs explicit save keybinding vs both. Trade-off
  is data loss on crash vs surprise writes to the trace file.
- [Affects A] Save path convention for auto-saved traces —
  `traces/<trace_id>.json` at repo root, or under a user cache dir?
  Affects `.gitignore`.
- [Affects C] Token counting for the 20-token threshold — reuse
  tiktoken-style counting or a cheap whitespace split? Accuracy here is
  not critical; cost and deps are.
- [Affects C] Cleanest way to pass categories alongside impls — a second
  `tool_categories: dict[str, str]`, a tagged value type, or a
  `ToolSpec` dataclass — given the existing `ToolImpls` alias. Pick the
  option requiring the fewest call-site changes.
