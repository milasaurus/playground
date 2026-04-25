import json
import os
import subprocess
import pytest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tool_definitions import (
    read_file_tool, list_files_tool, edit_file_tool, run_command_tool,
    truncate_tool_output, MAX_OUTPUT_CHARS, HEAD_CHARS, TAIL_CHARS,
)


# ── ReadFileTool ─────────────────────────────────────────────────────────────

def test_read_file_returns_contents(tmp_path):
    f = tmp_path / "hello.txt"
    f.write_text("hello world")
    result = read_file_tool.run({"path": str(f)})
    assert result == "hello world"


def test_read_file_missing_file():
    with pytest.raises(FileNotFoundError):
        read_file_tool.run({"path": "/nonexistent/file.txt"})


# ── ListFilesTool ────────────────────────────────────────────────────────────

def test_list_files_returns_files(tmp_path):
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b.txt").write_text("b")
    result = json.loads(list_files_tool.run({"path": str(tmp_path)}))
    assert "a.txt" in result
    assert "b.txt" in result


def test_list_files_skips_git_dir(tmp_path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("x")
    (tmp_path / "real.txt").write_text("y")
    result = json.loads(list_files_tool.run({"path": str(tmp_path)}))
    assert "real.txt" in result
    assert not any(".git" in entry for entry in result)


def test_list_files_skips_venv(tmp_path):
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()
    (venv_dir / "pyvenv.cfg").write_text("x")
    (tmp_path / "main.py").write_text("y")
    result = json.loads(list_files_tool.run({"path": str(tmp_path)}))
    assert "main.py" in result
    assert not any("venv" in entry for entry in result)


def test_list_files_defaults_to_current_dir():
    result = json.loads(list_files_tool.run({}))
    assert isinstance(result, list)


# ── EditFileTool ─────────────────────────────────────────────────────────────

def test_edit_file_replaces_text(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello world")
    result = edit_file_tool.run({"path": str(f), "old_str": "hello", "new_str": "goodbye"})
    assert result == "OK"
    assert f.read_text() == "goodbye world"


def test_edit_file_creates_new_file(tmp_path):
    f = tmp_path / "new.txt"
    result = edit_file_tool.run({"path": str(f), "old_str": "", "new_str": "new content"})
    assert "Successfully created" in result
    assert f.read_text() == "new content"


def test_edit_file_creates_nested_dirs(tmp_path):
    f = tmp_path / "sub" / "deep" / "file.txt"
    result = edit_file_tool.run({"path": str(f), "old_str": "", "new_str": "nested"})
    assert "Successfully created" in result
    assert f.read_text() == "nested"


def test_edit_file_old_str_not_found(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello world")
    with pytest.raises(ValueError, match="old_str not found"):
        edit_file_tool.run({"path": str(f), "old_str": "missing", "new_str": "x"})


def test_edit_file_rejects_duplicate_matches(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("aaa bbb aaa")
    with pytest.raises(ValueError, match="appears multiple times"):
        edit_file_tool.run({"path": str(f), "old_str": "aaa", "new_str": "ccc"})


def test_edit_file_rejects_same_old_new(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello")
    with pytest.raises(ValueError, match="invalid input"):
        edit_file_tool.run({"path": str(f), "old_str": "hello", "new_str": "hello"})


def test_edit_file_missing_file_with_old_str():
    with pytest.raises(FileNotFoundError):
        edit_file_tool.run({"path": "/nonexistent.txt", "old_str": "x", "new_str": "y"})


def test_edit_file_rejects_empty_path():
    with pytest.raises(ValueError, match="invalid input"):
        edit_file_tool.run({"path": "", "old_str": "a", "new_str": "b"})


# ── RunCommandTool ───────────────────────────────────────────────────────────



def test_run_command_returns_stdout():
    result = run_command_tool.run({"command": "echo hello"})
    assert "hello" in result


def test_run_command_returns_stderr():
    result = run_command_tool.run({"command": "echo error >&2"})
    assert "error" in result


def test_run_command_returns_exit_code_on_failure():
    result = run_command_tool.run({"command": "exit 1"})
    assert "[exit code: 1]" in result


def test_run_command_timeout():
    with pytest.raises(subprocess.TimeoutExpired):
        run_command_tool.run({"command": "sleep 10", "timeout": 1})


def test_run_command_no_output():
    result = run_command_tool.run({"command": "true"})
    assert result == "(no output)"


# ── truncate_tool_output ─────────────────────────────────────────────────────

def test_truncate_passes_short_through():
    text = "hello world"
    assert truncate_tool_output(text) == text


def test_truncate_passes_empty_through():
    assert truncate_tool_output("") == ""


def test_truncate_passes_exact_threshold_through():
    text = "x" * MAX_OUTPUT_CHARS
    assert truncate_tool_output(text) == text


def test_truncate_cuts_just_over_threshold():
    text = "x" * (MAX_OUTPUT_CHARS + 1)
    result = truncate_tool_output(text)
    assert result != text
    assert len(result) < len(text)


def test_truncate_keeps_head_and_tail():
    head = "H" * HEAD_CHARS
    middle = "M" * 5000
    tail = "T" * TAIL_CHARS
    text = head + middle + tail
    result = truncate_tool_output(text)
    assert result.startswith(head)
    assert result.endswith(tail)


def test_truncate_marker_mentions_omitted_count():
    text = "x" * (MAX_OUTPUT_CHARS + 5000)
    result = truncate_tool_output(text)
    omitted = len(text) - HEAD_CHARS - TAIL_CHARS
    assert str(omitted) in result
    assert "omitted" in result


def test_truncate_marker_suggests_recovery():
    text = "x" * (MAX_OUTPUT_CHARS + 1000)
    result = truncate_tool_output(text)
    assert any(hint in result for hint in ("grep", "head", "tail"))


# ── truncate_tool_output: cost / accuracy guards ─────────────────────────────
# These tests defend the cost/accuracy contract — that truncation actually
# saves meaningful context (otherwise it's not worth the marker noise) and
# that what we keep at the boundaries is preserved exactly (no off-by-one
# drops of useful info next to the cut).

def test_truncate_substantially_reduces_large_inputs():
    """For inputs much larger than the threshold, output is a tiny fraction
    of the original — proving the wrapper is paying for itself in tokens."""
    huge = "x" * 100_000  # ~25x the threshold
    result = truncate_tool_output(huge)
    assert len(result) < len(huge) * 0.05  # saved at least 95% of original size


def test_truncate_marker_overhead_is_small_relative_to_savings():
    """The marker is tiny compared to what it stands in for. Otherwise the
    cure is as expensive as the disease."""
    huge = "x" * 100_000
    result = truncate_tool_output(huge)
    marker_overhead = len(result) - HEAD_CHARS - TAIL_CHARS
    omitted = len(huge) - HEAD_CHARS - TAIL_CHARS
    assert marker_overhead < omitted * 0.01  # marker is <1% of what it replaces


def test_truncate_preserves_head_and_tail_bytes_exactly():
    """No off-by-one at the boundaries. Use a varied pattern so any drift
    would be visible — `xxx...` would mask a one-char shift."""
    text = "".join(chr(65 + (i % 26)) for i in range(MAX_OUTPUT_CHARS + 5000))
    result = truncate_tool_output(text)
    assert result[:HEAD_CHARS] == text[:HEAD_CHARS]
    assert result[-TAIL_CHARS:] == text[-TAIL_CHARS:]


def test_truncate_output_is_bounded_regardless_of_input_size():
    """Output stays near HEAD + TAIL + marker_overhead no matter how big
    the input gets. Linear-in-input output growth would mean we're not
    actually capping anything."""
    BOUND = HEAD_CHARS + TAIL_CHARS + 200  # 200 chars allowance for the marker
    for size in (10_000, 100_000, 1_000_000):
        result = truncate_tool_output("x" * size)
        assert len(result) <= BOUND, (
            f"size={size} produced {len(result)} chars, exceeds bound {BOUND}"
        )
