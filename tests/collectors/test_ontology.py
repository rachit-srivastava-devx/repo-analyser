from __future__ import annotations

import json
from pathlib import Path

from repo_analyser.collectors.ontology import (
    SUPERCLASS,
    _classify_files,
    _classify_message,
    _primary_dir,
    classify_commit,
    run_ontology,
)


class TestClassifyFiles:
    def test_empty_files_returns_none(self) -> None:
        assert _classify_files([]) is None

    def test_lockfile_alone_matches_dependency_bump(self) -> None:
        assert _classify_files(["package-lock.json"]) == ("dependency_bump", "file:dependency_bump")

    def test_mixed_files_no_single_rule_covers_all_returns_none(self) -> None:
        # one lockfile + one unrelated source file: "all files match" fails,
        # so file-evidence must not fire on a partial match.
        assert _classify_files(["package-lock.json", "src/app.py"]) is None

    def test_all_test_files_matches_test(self) -> None:
        assert _classify_files(["tests/test_foo.py", "tests/test_bar.py"])[0] == "test"

    def test_workflow_yaml_matches_ci_build(self) -> None:
        assert _classify_files([".github/workflows/ci.yml"])[0] == "ci_build"


class TestClassifyMessage:
    def test_conventional_prefix_feat(self) -> None:
        leaf, rule = _classify_message("feat: add checkout flow")
        assert leaf == "feature"
        assert rule == "prefix:feat"

    def test_conventional_prefix_with_scope(self) -> None:
        leaf, rule = _classify_message("fix(auth): handle expired token")
        assert leaf == "bug_fix"
        assert rule == "prefix:fix"

    def test_conventional_prefix_breaking_bang(self) -> None:
        leaf, _rule = _classify_message("feat!: drop legacy API")
        assert leaf == "feature"

    def test_no_prefix_falls_back_to_keyword(self) -> None:
        leaf, rule = _classify_message("Fixed crash on empty cart")
        assert leaf == "bug_fix"
        assert rule == "keyword:bug_fix"

    def test_no_prefix_no_keyword_is_other(self) -> None:
        leaf, rule = _classify_message("wip")
        assert leaf == "other"
        assert rule == "unmatched"

    def test_case_insensitive_prefix(self) -> None:
        leaf, _rule = _classify_message("FEAT: uppercase prefix")
        assert leaf == "feature"

    def test_revert_keyword(self) -> None:
        leaf, _rule = _classify_message("Reverted the checkout change")
        assert leaf == "revert"


class TestClassifyCommit:
    def test_conventional_prefix_wins_over_file_evidence(self) -> None:
        # message says feature; files look like docs. Prefix rules are
        # checked first inside _classify_message and message isn't "other",
        # so the message classification should stand.
        leaf, rule = classify_commit("feat: document the new endpoint", ["docs/api.md"])
        assert leaf == "feature"
        assert rule == "prefix:feat"

    def test_unambiguous_lockfile_wins_when_message_is_other(self) -> None:
        leaf, rule = classify_commit("wip", ["package-lock.json"])
        assert leaf == "dependency_bump"
        assert rule == "file:dependency_bump"

    def test_unambiguous_lockfile_overrides_generic_chore_message(self) -> None:
        leaf, rule = classify_commit("chore: bump", ["package-lock.json"])
        assert leaf == "dependency_bump"
        assert rule == "file:dependency_bump"

    def test_file_evidence_does_not_override_a_specific_keyword_match(self) -> None:
        # files look like ci_build, but message keyword-matches "bug_fix"
        # (more specific than the other/chore escape hatch) -- message wins.
        leaf, rule = classify_commit("fix broken deploy script", [".github/workflows/ci.yml"])
        assert leaf == "bug_fix"
        assert rule == "keyword:bug_fix"

    def test_no_files_no_prefix_no_keyword_is_other(self) -> None:
        leaf, rule = classify_commit("asdf", [])
        assert leaf == "other"
        assert rule == "unmatched"

    def test_every_leaf_has_a_superclass(self) -> None:
        # guards against a future leaf being added to LEAF_PRIORITY/rules
        # without a matching SUPERCLASS entry, which would KeyError in
        # analyze_repo at run time instead of at import time.
        from repo_analyser.collectors.ontology import FILE_RULES, KEYWORD_RULES, LEAF_PRIORITY, PREFIX_TO_LEAF
        all_leaves = set(LEAF_PRIORITY) | set(PREFIX_TO_LEAF.values()) | \
            {leaf for leaf, _ in KEYWORD_RULES} | {leaf for leaf, _ in FILE_RULES} | {"other"}
        assert all_leaves <= set(SUPERCLASS.keys())


class TestPrimaryDir:
    def test_empty_files_returns_empty_string(self) -> None:
        assert _primary_dir([]) == ""

    def test_single_file_two_segments(self) -> None:
        assert _primary_dir(["src/api/handler.py"]) == "src/api"

    def test_single_file_one_segment(self) -> None:
        assert _primary_dir(["README.md"]) == "README.md"

    def test_most_common_prefix_wins(self) -> None:
        files = ["src/api/a.py", "src/api/b.py", "src/web/c.py"]
        assert _primary_dir(files) == "src/api"

    def test_depth_parameter_respected(self) -> None:
        assert _primary_dir(["a/b/c/d.py"], depth=1) == "a"
        assert _primary_dir(["a/b/c/d.py"], depth=3) == "a/b/c"


class TestRunOntology:
    def test_writes_csv_and_summary_for_real_repo(self, git_repo: Path, tmp_path: Path) -> None:
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        csv_path = run_ontology([git_repo], out_dir)

        assert csv_path.exists()
        rows = csv_path.read_text().splitlines()
        assert len(rows) == 3  # header + 2 non-merge commits from the fixture

        summary = json.loads((out_dir / "ontology_summary.json").read_text())
        assert summary["total_non_merge_commits"] == 2
        # fixture commits are "feat: add add()" and "fix: add sub()"
        assert summary["leaf_distribution"].get("feature") == 1
        assert summary["leaf_distribution"].get("bug_fix") == 1
        assert summary["other_pct"] == 0.0

    def test_empty_repo_list_writes_zero_row_csv_not_crash(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        csv_path = run_ontology([], out_dir)
        assert csv_path.exists()
        summary = json.loads((out_dir / "ontology_summary.json").read_text())
        assert summary["total_non_merge_commits"] == 0
        assert summary["other_pct"] == 0.0  # guarded division, not a ZeroDivisionError
