"""Entry point: run the research agent and display the trace, OR open a
saved trace from disk.

Default output is the interactive Textual TUI. Pass `--print` for a
colour-coded tree on stdout instead (useful in pipes / non-TTY contexts).

Usage:
    python -m agent_trace_debugger.main "What's the capital of France?"
    python -m agent_trace_debugger.main --print "..."
    python -m agent_trace_debugger.main --load traces/run.json
"""

import argparse
import os
import sys

# Allow running directly: `python agent_trace_debugger/main.py ...`
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from client import client
from agent_trace_debugger.agent import TOOL_IMPLS, ResearchAgent
from agent_trace_debugger.models import load_trace
from agent_trace_debugger.services.agent_runner import run_traced
from agent_trace_debugger.tui import print_trace, run_tui


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Agent Trace Debugger")
    p.add_argument("question", nargs="?",
                   help="Question to ask the research agent. Required unless --load is used.")
    p.add_argument("--load",   help="Open a saved trace JSON from this path instead of running the agent.")
    p.add_argument("--print",  dest="print_tree", action="store_true",
                   help="Print a colour-coded tree to stdout instead of launching the TUI.")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    if args.load:
        trace = load_trace(args.load)
        print(f"▶ loaded {args.load}: {len(trace.nodes)} nodes, "
              f"{trace.total_cost.total_tokens()} tokens\n")
    else:
        if not args.question:
            print("error: question is required unless --load is used", file=sys.stderr)
            sys.exit(2)
        print(f"▶ running agent: {args.question!r}")
        trace = run_traced(ResearchAgent, client, TOOL_IMPLS, args.question)
        print(f"✓ captured {len(trace.nodes)} nodes, "
              f"{trace.total_cost.total_tokens()} tokens\n")

    if args.print_tree:
        print_trace(trace)
    else:
        run_tui(trace)


if __name__ == "__main__":
    main()
