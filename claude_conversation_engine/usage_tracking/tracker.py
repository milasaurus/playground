class UsageTracker:
    """Tracks token usage across a conversation."""

    def __init__(self):
        self.turns: list[dict] = []

    def record(self, input_tokens: int, output_tokens: int):
        self.turns.append({
            "turn": len(self.turns) + 1,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        })

    def get_total(self) -> dict:
        total_input = sum(t["input_tokens"] for t in self.turns)
        total_output = sum(t["output_tokens"] for t in self.turns)
        return {
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "num_turns": len(self.turns),
        }

    def get_turns(self) -> list[dict]:
        return list(self.turns)

    def report(self) -> str:
        lines = ["Token Usage Report", "=" * 40]
        for turn in self.turns:
            lines.append(
                f"Turn {turn['turn']}: "
                f"{turn['input_tokens']} in / {turn['output_tokens']} out / "
                f"{turn['total_tokens']} total"
            )
        totals = self.get_total()
        lines.append("=" * 40)
        lines.append(
            f"Total: {totals['total_input_tokens']} in / "
            f"{totals['total_output_tokens']} out / "
            f"{totals['total_tokens']} total across {totals['num_turns']} turns"
        )
        return "\n".join(lines)
