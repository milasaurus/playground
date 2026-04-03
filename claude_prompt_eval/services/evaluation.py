from client import client
from claude_prompt_eval.models import PromptVersion, EvalCase
from claude_prompt_eval.api.runner import EvalRunner
from claude_prompt_eval.api.evaluator import Evaluator
from claude_prompt_eval.api.report import EvalReport


def collect_versions():
    print("Enter two system prompts to compare.\n")
    prompt_a = input("Prompt A: ")
    print()
    prompt_b = input("Prompt B: ")
    print()
    return [
        PromptVersion(name="A", system_prompt=prompt_a),
        PromptVersion(name="B", system_prompt=prompt_b),
    ]


def collect_case():
    message = input("What should the user ask? ")
    print(f"  Added: \"{message}\"\n")
    return EvalCase(name="test_1", user_message=message)


def run_eval(versions, cases):
    print(f"\nEvaluating {len(versions)} prompt versions x {len(cases)} test cases")
    print(f"This will make {len(versions) * len(cases) * 2} API calls (generation + scoring).\n")

    print("\nRunning evaluation...")
    print(f"Generating responses... ({len(versions) * len(cases)} API calls)")
    results = EvalRunner(client).run(versions, cases)

    print(f"Scoring responses with Claude as judge... ({len(versions) * len(cases)} API calls)")
    prompt_map = {v.name: v.system_prompt for v in versions}
    scores = Evaluator(client).score(results, prompt_map)

    print("Generating report...\n")
    print(EvalReport(results, scores, prompt_map).summary())


if __name__ == "__main__":
    print("=== Prompt Eval ===")
    print("Compare different system prompts side by side.\n")

    print("STEP 1 of 2: Define your prompt versions")
    print("  Example: Answer in one sentence.")
    print("  Example: Give a thorough explanation with examples.\n")

    versions = collect_versions()

    print("STEP 2 of 2: What should the user ask?")
    print("  Example: What is a variable?")
    print("  Example: Explain how recursion works.\n")

    case = collect_case()

    run_eval(versions, [case])
