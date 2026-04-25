---
date: 2026-04-25
topic: code-editing-agent-long-context
---

# Code-Editing Agent — Long-Context Improvements

## The problem

The agent works fine for short sessions and gets unwieldy fast. Two
specific reasons:

1. **Tool results are huge and stick around.** A 1,000-line `read_file`
   or a verbose `pytest` run dumps everything into the conversation,
   and it stays there for the rest of the session. One bad call can
   blow the budget.
2. **There's no way to clean up a long conversation mid-session.** Once
   the chat is heavy, your only option is to quit and start over,
   losing all context.

Two small additions handle both.

## L1. Cap and truncate large tool results

Wrap every tool's output before it goes back into the conversation. If
the result exceeds a threshold (e.g. 4,000 chars), keep the first
~2,000 and last ~1,000 chars and replace the middle with a marker:

```
[... 847 lines omitted. Re-run with a narrower query — e.g.
`grep -n PATTERN file.py`, `head -100`, or a smaller offset/limit. ...]
```

Why head + tail: errors and structure usually surface at the top of a
file or command output; summaries usually surface at the bottom. The
marker is the load-bearing piece — it tells the agent both that
content was cut *and* what action recovers it. The agent's normal
response is to re-run with a narrower query.

One change in `code_editing_agent/tool_definitions.py`. Affects every
tool through the wrapper, no per-tool patches.

## L2. `/compact` slash command

A user-typed command that summarises the conversation so far and
restarts the chat with the summary as context.

How it works:

- User types `/compact` at the prompt.
- The agent makes one Claude call: "summarise this conversation in
  ~200 words, preserving file references, decisions made, and any
  open todos."
- The conversation is rewritten to: `[system prompt] + [summary as a
  single user message]`. The original turns are dropped.
- A short confirmation prints: `compacted N turns → M tokens`.

Why `/compact` and not auto-compaction: auto needs thresholds, a
trigger policy, and a recovery story when summarisation goes wrong.
Manual is a one-line dispatch and the user is in control. The agent
doesn't decide when context gets reset — you do.

This goes in `code_editing_agent/agent.py` near the input loop.

## What success looks like

- I can `read_file` a 2,000-line file or run `pytest -v` without the
  next ten turns paying for it.
- After a long session, I can type `/compact` and keep going in the
  same terminal instead of quitting.
- Setup is unchanged — `make coder` still just works.

## What we're not building

- Auto-compaction at a threshold.
- Persistent sessions across runs.
- Cost tracking, budget alarms, or token counters.
- Per-tool truncation rules — one wrapper for all.
- A `/clear` command (use `/compact` or restart).
- Retroactive truncation of already-stored tool results.

## Next

-> `/ce:plan` if you want a structured plan; otherwise just ship it.
