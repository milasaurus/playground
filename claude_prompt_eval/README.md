# Prompt Eval

> Score a prompt — or compare two side by side.

## Getting started

1. Set up the environment (if you haven't already):

```bash
make setup
```

2. Add your API key to `.env` in the project root:

```
ANTHROPIC_API_KEY=your-api-key-here
```

3. Run the eval:

```bash
make prompt
```

You'll be asked for:

1. **A prompt** — the instruction you want to evaluate (e.g., "Answer in one sentence.")
2. **A second prompt (optional)** — press Enter to skip, or add one to compare (e.g., "Give a thorough explanation.")

The tool auto-generates test cases, runs them against your prompts in parallel, scores responses using Claude as a judge, and gives you 3 actionable recommendations per prompt.

## Example output

```
PROMPTS EVALUATED
------------------------------------------------------------
  A: "Answer in one sentence."
  B: "Give a thorough explanation with examples."

  HOW TO IMPROVE: A
------------------------------------------------------------
    1. Add a brief code example to ground abstract explanations
    2. Specify when one sentence isn't enough for complex topics
    3. Include "if the question is vague, ask for clarification"

  HOW TO IMPROVE: B
------------------------------------------------------------
    1. Add "match explanation depth to question complexity"
    2. Cap responses at 3 paragraphs to avoid over-explaining
    3. Include formatting instructions for code examples

  RANKINGS
------------------------------------------------------------
  🥇 B — █████████░ 9/10 (avg)
  🥈 A — ███████░░░ 7/10 (avg)
```

## Verbose mode

To see the full details — every test case, Claude's response, per-test scores, strengths, and weaknesses:

```bash
make prompt-verbose
```

## Configuration

Prompt evaluation data set count is configurable in `evaluation.py`:

```python
DEFAULT_EVAL_DATASET_SIZE = 3  # change this to generate more or fewer test cases
```

## Testing

```bash
make test-eval
```
