from __future__ import annotations

from repo_analyser.collectors.debt_markers.markers import MARKER_TYPES, find_markers_in_text


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
