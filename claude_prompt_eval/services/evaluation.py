import sys
from client import client
from claude_prompt_eval.models import PromptVersion
from claude_prompt_eval.api.generator import CaseGenerator
from claude_prompt_eval.api.runner import EvalRunner
from claude_prompt_eval.api.grader import Grader
from claude_prompt_eval.api.report import EvalReport

DEFAULT_EVAL_DATASET_SIZE = 3


def collect_prompt():
    print("Enter the system prompt you want to evaluate.\n")
    print("  Example: Answer in one sentence.")
    print("  Example: Give a thorough explanation with examples.\n")
    prompt = input("Prompt: ")
    print()
    return PromptVersion(name="A", system_prompt=prompt)


def run_eval(version, cases, verbose=False):
    from claude_prompt_eval.api.grader import BATCH_SIZE
    num_cases = len(cases)
    response_calls = num_cases
    grading_calls = -(-num_cases // BATCH_SIZE)
    total_calls = 1 + response_calls + grading_calls
    case_label = "case" if num_cases == 1 else "cases"
    print(f"\nEvaluating prompt x {num_cases} test {case_label}")
    print(f"~{total_calls} API calls: 1 to generate test cases, {response_calls} for responses, {grading_calls} for grading.\n")

    print("Generating responses...")
    results = EvalRunner(client).run([version], cases)

    print("Grading responses with Claude as judge...")
    prompt_map = {version.name: version.system_prompt}
    grades = Grader(client).grade(results, prompt_map)

    print("Generating report...\n")
    print(EvalReport(results, grades, prompt_map, verbose=verbose).summary())


if __name__ == "__main__":
    print("=== Prompt Eval ===")
    print("Evaluate a system prompt and get recommendations to improve it.\n")

    print("STEP 1 of 2: Define your prompt")
    version = collect_prompt()

    print(f"STEP 2 of 2: Generating {DEFAULT_EVAL_DATASET_SIZE} test cases...")
    cases = CaseGenerator(client).generate(
        version.system_prompt,
        count=DEFAULT_EVAL_DATASET_SIZE,
    )
    print(f"  Generated {len(cases)} test cases.\n")

    for i, case in enumerate(cases, 1):
        print(f"  {i}. \"{case.user_message}\"")
    print()

    verbose = "--verbose" in sys.argv
    run_eval(version, cases, verbose=verbose)
