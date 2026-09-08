"""Direct tests against hand-written diff text, per the task's explicit
instruction to get range extraction right and test it directly -- this
is what future line-filtering modules (e.g. lint_diff.py) depend on."""
from __future__ import annotations

from repo_analyser.pr_review.hunks import _parse_added_ranges


class TestParseAddedRanges:
    def test_new_file_single_hunk(self) -> None:
        text = (
            "diff --git a/new_file.txt b/new_file.txt\n"
            "new file mode 100644\n"
            "index 0000000..1111111\n"
            "--- /dev/null\n"
            "+++ b/new_file.txt\n"
            "@@ -0,0 +1,3 @@\n"
            "+line1\n"
            "+line2\n"
            "+line3\n"
        )
        assert _parse_added_ranges(text) == {"new_file.txt": [(1, 3)]}

    def test_modified_file_multiple_hunks_including_single_line_omitted_count(self) -> None:
        # git omits the ",count" suffix when a hunk's count is exactly 1
        # (verified empirically: "@@ -5 +5 @@", not "@@ -5,1 +5,1 @@").
        text = (
            "diff --git a/modified.txt b/modified.txt\n"
            "index 2222222..3333333 100644\n"
            "--- a/modified.txt\n"
            "+++ b/modified.txt\n"
            "@@ -5 +5 @@ some context\n"
            "-old\n"
            "+new\n"
            "@@ -10,0 +11,2 @@\n"
            "+added1\n"
            "+added2\n"
        )
        assert _parse_added_ranges(text) == {"modified.txt": [(5, 5), (11, 12)]}

    def test_pure_deletion_hunk_contributes_no_added_range(self) -> None:
        text = (
            "diff --git a/deleted.txt b/deleted.txt\n"
            "deleted file mode 100644\n"
            "index 4444444..0000000\n"
            "--- a/deleted.txt\n"
            "+++ /dev/null\n"
            "@@ -1,2 +0,0 @@\n"
            "-gone1\n"
            "-gone2\n"
        )
        assert _parse_added_ranges(text).get("deleted.txt", []) == []

    def test_binary_file_has_no_hunks(self) -> None:
        text = (
            "diff --git a/image.png b/image.png\n"
            "new file mode 100644\n"
            "index 5555555..6666666\n"
            "Binary files /dev/null and b/image.png differ\n"
        )
        assert _parse_added_ranges(text).get("image.png", []) == []

    def test_pure_rename_no_content_change_has_no_hunks(self) -> None:
        text = (
            "diff --git a/old_name.txt b/new_name.txt\n"
            "similarity index 100%\n"
            "rename from old_name.txt\n"
            "rename to new_name.txt\n"
        )
        assert _parse_added_ranges(text).get("new_name.txt", []) == []

    def test_multiple_files_in_one_combined_stream(self) -> None:
        text = (
            "diff --git a/new_file.txt b/new_file.txt\n"
            "new file mode 100644\n"
            "index 0000000..1111111\n"
            "--- /dev/null\n"
            "+++ b/new_file.txt\n"
            "@@ -0,0 +1,3 @@\n"
            "+line1\n"
            "+line2\n"
            "+line3\n"
            "diff --git a/old_name.txt b/new_name.txt\n"
            "similarity index 100%\n"
            "rename from old_name.txt\n"
            "rename to new_name.txt\n"
        )
        result = _parse_added_ranges(text)
        assert result["new_file.txt"] == [(1, 3)]
        assert result["new_name.txt"] == []

    def test_empty_input(self) -> None:
        assert _parse_added_ranges("") == {}
