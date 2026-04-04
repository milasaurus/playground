import sys
from client import client
from claude_prompt_eval.models import PromptVersion
from claude_prompt_eval.api.generator import CaseGenerator
from claude_prompt_eval.api.runner import EvalRunner
from claude_prompt_eval.api.grader import Grader
from claude_prompt_eval.api.report import EvalReport

DEFAULT_EVAL_DATASET_SIZE = 3


def collect_versions():
    print("Enter a system prompt to evaluate.\n")
    prompt_a = input("Prompt A: ")
    print()
    prompt_b = input("Prompt B (optional — press Enter to skip): ")
    print()
    versions = [PromptVersion(name="A", system_prompt=prompt_a)]
    if prompt_b:
        versions.append(PromptVersion(name="B", system_prompt=prompt_b))
    return versions


def run_eval(versions, cases, verbose=False):
    from claude_prompt_eval.api.grader import BATCH_SIZE
    num_versions = len(versions)
    num_cases = len(cases)
    response_calls = num_versions * num_cases
    grading_calls = num_versions * -(-num_cases // BATCH_SIZE)
    total_calls = 1 + response_calls + grading_calls
    version_label = "version" if num_versions == 1 else "versions"
    case_label = "case" if num_cases == 1 else "cases"
    print(f"\nEvaluating {num_versions} prompt {version_label} x {num_cases} test {case_label}")
    print(f"~{total_calls} API calls: 1 to generate test cases, {response_calls} for responses, {grading_calls} for grading.\n")

    print("Generating responses...")
    results = EvalRunner(client).run(versions, cases)

    print("Grading responses with Claude as judge...")
    prompt_map = {v.name: v.system_prompt for v in versions}
    grades = Grader(client).grade(results, prompt_map)

    print("Generating report...\n")
    print(EvalReport(results, grades, prompt_map, verbose=verbose).summary())


if __name__ == "__main__":
    print("=== Prompt Eval ===")
    print("Evaluate a system prompt — or compare two side by side.\n")

    print("STEP 1 of 2: Define your prompt versions")
    print("  Example: Answer in one sentence.")
    print("  Example: Give a thorough explanation with examples.\n")

    versions = collect_versions()

    print(f"STEP 2 of 2: Generating {DEFAULT_EVAL_DATASET_SIZE} test cases...")
    generator = CaseGenerator(client)
    prompt_b = versions[1].system_prompt if len(versions) > 1 else ""
    cases = generator.generate(
        versions[0].system_prompt,
        prompt_b,
        count=DEFAULT_EVAL_DATASET_SIZE,
    )
    print(f"  Generated {len(cases)} test cases.\n")

    for i, case in enumerate(cases, 1):
        print(f"  {i}. \"{case.user_message}\"")
    print()

    verbose = "--verbose" in sys.argv
    run_eval(versions, cases, verbose=verbose)
