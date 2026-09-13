from __future__ import annotations

from repo_analyser.collectors.debt_markers.markers import MARKER_TYPES, find_markers_in_text
from repo_analyser.core.util import repo_root


def test_empty_text_yields_nothing() -> None:
    assert find_markers_in_text("") == []


def test_no_markers_present() -> None:
    assert find_markers_in_text("def add(a, b):\n    return a + b\n") == []


def test_all_five_marker_types_recognized_with_hash_prefix() -> None:
    text = "\n".join(f"# {marker}: something" for marker in MARKER_TYPES)
    found = find_markers_in_text(text)
    assert [t for _lineno, t in found] == list(MARKER_TYPES)


def test_slash_slash_prefix_matches() -> None:
    assert find_markers_in_text("// TODO: fix this later\n") == [(1, "TODO")]


def test_block_comment_open_and_continuation_prefixes_match() -> None:
    text = "/* TODO: opening line */\n * FIXME: continuation line\n"
    assert find_markers_in_text(text) == [(1, "TODO"), (2, "FIXME")]


def test_sql_style_double_dash_prefix_matches() -> None:
    assert find_markers_in_text("-- TODO: backfill this column\n") == [(1, "TODO")]


def test_html_comment_prefix_matches() -> None:
    assert find_markers_in_text("<!-- TODO: revisit markup -->\n") == [(1, "TODO")]


def test_todolist_identifier_is_not_a_bare_todo_match() -> None:
    """Word-boundary requirement: TODO is a real word inside a comment,
    TODOLIST is a different, unrelated identifier -- even with a comment
    prefix present, TODOLIST must not be counted as a TODO marker."""
    assert find_markers_in_text("# TODOLIST = fetch_list()\n") == []


def test_debugging_is_not_a_bare_bug_match() -> None:
    """Same word-boundary rule, the other direction: BUG has no boundary
    before it inside DEBUGGING (preceded by a word character, 'E')."""
    assert find_markers_in_text("# DEBUGGING in progress, see logs\n") == []


def test_marker_text_inside_a_string_literal_is_not_matched() -> None:
    """The line doesn't start with a recognized comment prefix -- this is
    ordinary business logic printing text that happens to contain the word
    TODO, not a tracked debt marker."""
    assert find_markers_in_text('print("TODO: send confirmation email")\n') == []


def test_lowercase_marker_token_is_not_matched_case_sensitive() -> None:
    assert find_markers_in_text("# todo: this should not count\n") == []


def test_multiple_distinct_markers_on_one_line_each_count() -> None:
    assert find_markers_in_text("# TODO: x, FIXME: y\n") == [(1, "TODO"), (1, "FIXME")]


def test_same_marker_twice_on_one_line_counts_twice() -> None:
    assert find_markers_in_text("# TODO: a, TODO: b\n") == [(1, "TODO"), (1, "TODO")]


def test_marker_reported_with_one_indexed_line_number() -> None:
    text = "line one\nline two\n# HACK: on the third line\n"
    assert find_markers_in_text(text) == [(3, "HACK")]


def test_marker_inside_a_triple_quoted_python_string_is_not_matched() -> None:
    """Regression for the multi-line string false positive: the comment-
    prefix regex, applied per physical line with no notion of "currently
    inside an open string", used to flag this line even though it is
    string *data*, not a real comment -- because it happens to start with
    `#` once the surrounding triple-quote is stripped away. filename=
    "banner.py" is required to opt into the Python triple-quote tracker."""
    text = (
        'BANNER = """\n'
        "# TODO: this is literal string DATA, not a real comment\n"
        "some other line\n"
        '"""\n'
    )
    assert find_markers_in_text(text, filename="banner.py") == []


def test_marker_inside_triple_quoted_string_still_matches_without_a_py_filename() -> None:
    """The triple-quote suppression is opt-in via `filename` ending in
    `.py` -- without it (unknown language), behavior is unchanged from
    before this fix: a comment-prefixed line still matches."""
    text = 'BANNER = """\n# TODO: still counted, no .py filename given\n"""\n'
    assert find_markers_in_text(text) == [(2, "TODO")]


def test_marker_on_a_real_comment_line_after_a_closed_triple_quoted_string_still_matches() -> None:
    """The triple-quote tracker must not over-suppress: once the string
    closes, an ordinary real comment afterwards is still a real marker."""
    text = 'BANNER = """\nignored data\n"""\n# TODO: this one is real\n'
    assert find_markers_in_text(text, filename="banner.py") == [(4, "TODO")]


def test_aggregate_module_source_itself_has_no_self_flagged_debt_markers() -> None:
    """Regression: aggregate.py's own docstring/comments used to discuss
    the concept of a "TODO/FIXME" marker using those literal, bare words
    inside a real `#`-prefixed comment -- which this same collector then
    flagged as 2 "real" findings when scanning its own source tree,
    directly contradicting a builder's claimed "0 markers, self-checked"
    report. The comment was reworded to discuss the concept without using
    the bare marker tokens; this pins that down against silent regression
    by scanning the actual file on disk, not a hand-copied excerpt."""
    aggregate_path = repo_root() / "src/repo_analyser/collectors/debt_markers/aggregate.py"
    text = aggregate_path.read_text(encoding="utf-8")
    assert find_markers_in_text(text, filename=str(aggregate_path)) == []
