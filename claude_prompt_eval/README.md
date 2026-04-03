# Prompt Eval

> Compare two system prompts and find out which one is better.

## Quick start

```bash
make prompt
```

You'll be asked for:

1. **Two system prompts** — the instructions you want to compare (e.g., "Answer in one sentence." vs "Give a thorough explanation.")
2. **A user message** — a question to test both prompts against (e.g., "What is a variable?")

The tool runs both prompts, scores them 1-10 using Claude as a judge, and tells you what to improve.

## Example output

```
PROMPTS EVALUATED
------------------------------------------------------------
  A: "Answer in one sentence."
  B: "Give a thorough explanation with examples."

  >> A
     Score: ███████░░░ 7/10

     What worked:
       Direct and clear.

     How to improve:
       Add "include a one-line code example" to the prompt.

  >> B
     Score: █████████░ 9/10

     What worked:
       Thorough with a practical example.

     How to improve:
       Add "match explanation depth to question complexity."

  RANKINGS
------------------------------------------------------------
  🥇 B — █████████░ 9/10 (avg)
  🥈 A — ███████░░░ 7/10 (avg)
```

## Testing

```bash
make test-eval
```
