---
date: 2026-04-24
topic: agent-trace-debugger-improvements
---

# Agent Trace Debugger — Small Improvements

## The problem

The debugger shows a single agent run as a tree. That's fine for the two
things we built it for: multi-hop reasoning loops and context bloat. But
three other questions keep coming up and the trace can't answer them:

1. **Are the tools at the right level?** Does the agent waste calls on
   mechanical steps, or hit edge cases it can't handle?
2. **What mattered in this run?** Thousands of decisions is too much to
   eyeball. I need a way to mark the important ones.
3. **Did the agent read the tool output, or just guess?** When it runs
   tests and says "looks good," did it actually look?

Three small additions, one per question. Ship order: **C → A → B**
(novel piece first, then the piece I'll use every day, then the
aggregation that only pays off on multi-tool agents).

## C. Verification flag + read-back check

**Problem:** agent runs tests, says "pass," moves on — without reading
the output.

**Fix, in two parts:**

- **R10. Flag verification tools at registration.** Add an optional
  `verification: bool` (default `False`) to
  `agent_trace_debugger/services/tool_runner.py`. Simplest shape: the
  dict accepts either a plain callable or `(callable, verification=True)`.
  Pick whichever is cleanest. The flag lands on
  `metadata.verification` for each `tool_call`. Client-side tools only
  for v1 — no consumer for the server-side path yet.

- **R11. Check if the output got read.** After the run, for each
  `observation` node, set `metadata.output_referenced` to
  `true` / `false` / `null`:
  - Find the next `decision` or `response` that came after this
    observation's turn (walk `observation → tool_call → decision`, then
    look for the next sibling decision under the root).
  - If the observation is under 8 words (`ok`, `(no results)`), return
    `null` — too short to judge.
  - If the next decision mentions the tool name or reuses an 8-word
    chunk of the output, return `true`. Else `false`.

  Dumb on purpose. We iterate once we see real traces.

- **R12. Show it in the TUI.** `[V]` badge on verification tool_calls,
  `!!` next to verification observations with `output_referenced=false`.

## A. Node tagging

**Problem:** long runs have thousands of steps. No way to mark which
ones mattered.

- **R5. Tag nodes with `g` / `w` / `p`.** Good / wasted / pivotal.
  Stored in `TraceNode.metadata.tags` as a list. Independent — a node
  can be both pivotal and wasted. Press again to remove. Register as
  named Textual `Binding`s so they show up in the footer automatically.

- **R6. Show tags in the detail panel.** When empty, render
  `tags: (press g/w/p to tag)` so the feature is discoverable.

- **R7. Save.** `s` saves and stays open. `q` saves and quits. Path:
  `traces/<trace_id>.json` relative to CWD for a fresh run; overwrite
  the source file when opened via `--load`. Add `traces/` to
  `.gitignore`. On save failure, show the error in the detail panel
  and don't quit.

- **R8. Load a saved trace.** `--load PATH` opens the TUI on a saved
  trace without running an agent. Makes the positional `question`
  argument optional. Bad path or malformed JSON: print the error and
  exit before the TUI starts.

## B. Per-tool report

**Problem:** can't tell at a glance which tool is the problem.

- **R1. Aggregate per tool.** Call count, total duplicate calls, max
  consecutive duplicates, error count, avg output size, avg latency.

- **R2. What counts as a duplicate.** Same tool name + same input.
  Canonicalize input with
  `json.dumps(input, sort_keys=True, separators=(',', ':'))` so key
  order doesn't break the match.

- **R3. Show it.** A new pane below the tree in the TUI, and a block
  after the tree in `--print` mode. Aggregation lives in a pure
  function so both renderers share it.

- **R4.** Replaces the "loop detection" bullet in
  `agent_trace_debugger/improvements.md`. Loops show up as high
  max-consecutive-duplicates.

## What success looks like

From the TUI, after a run:

1. I can tag nodes and the tags survive when I `--load` the trace
   tomorrow.
2. Verification tool_calls are visible at a glance, and I can spot the
   ones the agent didn't read.
3. I can see which tool has the most consecutive duplicates, errors, or
   oversized outputs.

## What we're not building

- Fixing non-determinism. The trace shows *what*, not *why*.
- A real eval harness. Tags are just raw material.
- Tool-name auto-lift for verification. Authors flag explicitly.
- Fuzzy duplicate detection, streaming capture, multi-agent correlation.

## Existing hooks we'll use

- `TraceNode.metadata` round-trips through `Trace.to_dict` /
  `Trace.from_dict` (`agent_trace_debugger/models.py`). Tags serialize
  for free.
- `Tracer.save` and `load_trace` already exist
  (`agent_trace_debugger/services/tracer.py`, `models.py`) but aren't
  wired into `main.py`. R7 and R8 wire them in.

## Open questions for planning

- Exact layout of the tool-report pane — below the tree, overlay, or
  toggled by a key? Fit it without crowding the detail panel.
- Exact shape of the verification-flag registration API — tuple, small
  dataclass, or something else. Pick the smallest call-site diff.
