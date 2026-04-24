"""Trace display — Rich tree for stdout and Textual TUI for interactive use."""

from collections import defaultdict

from rich.console import Console
from rich.markup import escape
from rich.tree import Tree as RichTree
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Footer, Static, Tree

from .trace import Trace, TraceNode


# Color per node type — keep in sync with trace.NODE_* constants.
TYPE_COLORS = {
    "user_input":  "white",
    "decision":    "blue",
    "tool_call":   "yellow",
    "observation": "green",
    "response":    "cyan",
}


def _preview(text: str, limit: int = 60) -> str:
    text = text.replace("\n", " ").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _fmt_duration(ms: float) -> str:
    return f"{ms/1000:.2f}s" if ms >= 1000 else f"{ms:.0f}ms"


def _node_label(node: TraceNode) -> str:
    color  = TYPE_COLORS.get(node.type, "white")
    tokens = node.cost.total_tokens() if node.cost else 0
    tokstr = f" [dim]({tokens} tok)[/dim]" if tokens else ""
    latstr = f" [dim]({_fmt_duration(node.duration_ms)})[/dim]" if node.duration_ms else ""
    return (
        f"[{color}]{node.type}[/{color}] "
        f"[bold]{escape(node.name)}[/bold]{tokstr}{latstr} "
        f"[dim]{escape(_preview(node.content))}[/dim]"
    )


class TraceApp(App):
    CSS = """
    Screen { layout: vertical; }
    #topbar { height: 3; padding: 0 1; background: $panel; color: $text; border: round $primary; }
    #body   { height: 1fr; }
    #tree   { width: 50%; border: round $primary; }
    #detail-wrap { width: 50%; border: round $secondary; padding: 1; }
    """

    BINDINGS = [
        Binding("q",      "quit",          "Quit"),
        Binding("e",      "expand_all",    "Expand all"),
        Binding("c",      "collapse_all",  "Collapse all"),
        Binding("r",      "reset",         "Reset"),
    ]

    def __init__(self, trace: Trace):
        super().__init__()
        self.trace = trace
        self._detail: Static | None = None

    def compose(self) -> ComposeResult:
        yield Static(self._header_text(), id="topbar")
        with Horizontal(id="body"):
            yield Tree(f"Trace {self.trace.id}", id="tree")
            with VerticalScroll(id="detail-wrap"):
                yield Static("Select a node to view details.", id="detail")
        yield Footer()

    def on_mount(self) -> None:
        tree = self.query_one(Tree)
        self._detail = self.query_one("#detail", Static)
        self._populate(tree)
        tree.root.expand_all()
        tree.focus()

    def _header_text(self) -> str:
        c = self.trace.total_cost
        return (
            f"[bold]Q:[/bold] {escape(_preview(self.trace.user_question, 80))}\n"
            f"[bold]tokens[/bold] in={c.input_tokens} out={c.output_tokens} "
            f"cache_r={c.cache_read_input_tokens} cache_w={c.cache_creation_input_tokens} "
            f"[bold]total={c.total_tokens()}[/bold] · [dim]model={escape(c.model or '?')}[/dim]"
        )

    def _populate(self, tree: Tree) -> None:
        children_of: dict[str | None, list[TraceNode]] = defaultdict(list)
        for n in self.trace.nodes:
            children_of[n.parent_id].append(n)

        def walk(parent_tree_node, node: TraceNode) -> None:
            child = parent_tree_node.add(_node_label(node), data=node)
            for kid in children_of.get(node.id, []):
                walk(child, kid)
            child.expand()

        for root_node in children_of.get(None, []):
            walk(tree.root, root_node)

    # Textual fires NodeSelected when the user presses enter / clicks.
    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        node: TraceNode | None = event.node.data
        if node is None or self._detail is None:
            return
        self._detail.update(self._format_detail(node))

    # Also update on mere highlighting so arrow-key navigation feels live.
    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        node: TraceNode | None = event.node.data
        if node is None or self._detail is None:
            return
        self._detail.update(self._format_detail(node))

    def _format_detail(self, node: TraceNode) -> str:
        color = TYPE_COLORS.get(node.type, "white")
        lines = [
            f"[{color}][bold]{node.type.upper()}[/bold] · {escape(node.name)}[/{color}]",
            f"[dim]id={node.id}  parent={node.parent_id}  ts={node.timestamp}[/dim]",
        ]
        if node.cost:
            lines.append(
                f"[bold]tokens[/bold]  in={node.cost.input_tokens}  "
                f"out={node.cost.output_tokens}  model={escape(node.cost.model)}"
            )
        if node.duration_ms is not None:
            lines.append(f"[bold]latency[/bold]  {_fmt_duration(node.duration_ms)}")
        if node.reasoning:
            lines.append(f"[bold]reasoning[/bold]  {escape(node.reasoning)}")
        if node.metadata:
            lines.append(f"[bold]metadata[/bold]  {escape(str(node.metadata))}")
        lines += ["", "[bold]content[/bold]", escape(node.content) or "[dim](empty)[/dim]"]
        return "\n".join(lines)

    def action_expand_all(self) -> None:
        self.query_one(Tree).root.expand_all()

    def action_collapse_all(self) -> None:
        self.query_one(Tree).root.collapse_all()
        self.query_one(Tree).root.expand()

    def action_reset(self) -> None:
        tree = self.query_one(Tree)
        tree.root.expand_all()


def run_tui(trace: Trace) -> None:
    TraceApp(trace).run()


def print_trace(trace: Trace, console: Console | None = None) -> None:
    """Render the trace as a colour-coded Rich tree to stdout and return.

    This is the non-interactive counterpart to `run_tui`. It needs no TTY, so
    it works in pipes, CI, and sandboxed environments.
    """
    console = console or Console()
    c = trace.total_cost

    console.print(f"[bold]Q:[/bold] {escape(trace.user_question)}")
    console.print(
        f"[bold]tokens[/bold]  in={c.input_tokens}  out={c.output_tokens}  "
        f"cache_r={c.cache_read_input_tokens}  cache_w={c.cache_creation_input_tokens}  "
        f"[bold]total={c.total_tokens()}[/bold]  [dim]model={escape(c.model or '?')}[/dim]"
    )
    console.print()

    children_of: dict[str | None, list[TraceNode]] = defaultdict(list)
    for n in trace.nodes:
        children_of[n.parent_id].append(n)

    rich_tree = RichTree(f"[dim]Trace {trace.id}[/dim]")

    def walk(parent_rnode, node: TraceNode) -> None:
        sub = parent_rnode.add(_node_label(node))
        for kid in children_of.get(node.id, []):
            walk(sub, kid)

    for root in children_of.get(None, []):
        walk(rich_tree, root)

    console.print(rich_tree)
