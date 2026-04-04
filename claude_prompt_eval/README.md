# Prompt Eval

> Score a system prompt and get recommendations to improve it.

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

You'll be asked for a system prompt — the instruction you want to evaluate (e.g., "Answer in one sentence.").

The tool auto-generates test cases, runs them against your prompt in parallel, scores responses using Claude as a judge, and gives you 3 actionable recommendations.

## Example output

```
PROMPT EVALUATED
------------------------------------------------------------
  A: "Answer in one sentence."

  HOW TO IMPROVE: A
------------------------------------------------------------
    1. Add a brief code example to ground abstract explanations
    2. Specify when one sentence isn't enough for complex topics
    3. Include "if the question is vague, ask for clarification"

  SCORE
------------------------------------------------------------
  🥇 A — ███████░░░ 7/10 (avg)
```

## Verbose mode

To see the full details — every test case, Claude's response, per-test scores, strengths, and weaknesses:

```bash
make prompt-verbose
```

## Configuration

Evaluation dataset size is configurable in `evaluation.py`:

```python
DEFAULT_EVAL_DATASET_SIZE = 3  # change this to generate more or fewer test cases
```

## Testing

```bash
make test-eval
```
