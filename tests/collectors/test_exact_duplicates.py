from __future__ import annotations

import json
from pathlib import Path

from repo_analyser.collectors.exact_duplicates import run_exact_duplicates


def _write(repo: Path, rel_path: str, content: str) -> None:
    p = repo / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


class TestRunExactDuplicates:
    def test_identical_file_across_two_repos_is_reported(self, tmp_path: Path) -> None:
        repo_a = tmp_path / "repo-a"
        repo_b = tmp_path / "repo-b"
        _write(repo_a, "src/util.ts", "export const x = 1;\n")
        _write(repo_b, "src/util.ts", "export const x = 1;\n")
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        run_exact_duplicates([repo_a, repo_b], out_dir)
        rows = (out_dir / "exact_duplicate_files.csv").read_text().splitlines()
        assert len(rows) == 2  # header + 1 group
        assert "repo-a" in rows[1] and "repo-b" in rows[1]

        summary = json.loads((out_dir / "exact_duplicate_summary.json").read_text())
        assert summary["cross_repo_identical_groups"] == 1
        assert summary["max_repo_count_for_one_file"] == 2

    def test_same_repo_duplicate_is_not_cross_repo(self, tmp_path: Path) -> None:
        repo_a = tmp_path / "repo-a"
        _write(repo_a, "src/a.ts", "shared content\n")
        _write(repo_a, "src/b.ts", "shared content\n")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run_exact_duplicates([repo_a], out_dir)
        summary = json.loads((out_dir / "exact_duplicate_summary.json").read_text())
        assert summary["cross_repo_identical_groups"] == 0

    def test_different_content_is_not_a_duplicate(self, tmp_path: Path) -> None:
        repo_a = tmp_path / "repo-a"
        repo_b = tmp_path / "repo-b"
        _write(repo_a, "src/util.ts", "export const x = 1;\n")
        _write(repo_b, "src/util.ts", "export const x = 2;\n")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run_exact_duplicates([repo_a, repo_b], out_dir)
        summary = json.loads((out_dir / "exact_duplicate_summary.json").read_text())
        assert summary["cross_repo_identical_groups"] == 0

    def test_lockfiles_are_excluded(self, tmp_path: Path) -> None:
        repo_a = tmp_path / "repo-a"
        repo_b = tmp_path / "repo-b"
        _write(repo_a, "package-lock.json", '{"lockfileVersion": 3}')
        _write(repo_b, "package-lock.json", '{"lockfileVersion": 3}')
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run_exact_duplicates([repo_a, repo_b], out_dir)
        summary = json.loads((out_dir / "exact_duplicate_summary.json").read_text())
        assert summary["cross_repo_identical_groups"] == 0

    def test_rust_target_and_venv_dirs_are_excluded(self, tmp_path: Path) -> None:
        # regression test: EXCLUDE_DIRS used to be its own list here,
        # independently drifted from core.lang.EXCLUDE_DIR_PARTS, missing
        # target/vendor/venv/.venv/__pycache__.
        repo_a = tmp_path / "repo-a"
        repo_b = tmp_path / "repo-b"
        _write(repo_a, "target/debug/identical.rs", "identical\n")
        _write(repo_b, "target/debug/identical.rs", "identical\n")
        _write(repo_a, ".venv/lib/identical.py", "identical\n")
        _write(repo_b, ".venv/lib/identical.py", "identical\n")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run_exact_duplicates([repo_a, repo_b], out_dir)
        summary = json.loads((out_dir / "exact_duplicate_summary.json").read_text())
        assert summary["cross_repo_identical_groups"] == 0

    def test_node_modules_is_excluded(self, tmp_path: Path) -> None:
        repo_a = tmp_path / "repo-a"
        repo_b = tmp_path / "repo-b"
        _write(repo_a, "node_modules/pkg/index.js", "identical\n")
        _write(repo_b, "node_modules/pkg/index.js", "identical\n")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run_exact_duplicates([repo_a, repo_b], out_dir)
        summary = json.loads((out_dir / "exact_duplicate_summary.json").read_text())
        assert summary["cross_repo_identical_groups"] == 0

    def test_unrecognized_extension_is_excluded(self, tmp_path: Path) -> None:
        repo_a = tmp_path / "repo-a"
        repo_b = tmp_path / "repo-b"
        _write(repo_a, "notes.txt", "identical\n")
        _write(repo_b, "notes.txt", "identical\n")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run_exact_duplicates([repo_a, repo_b], out_dir)
        summary = json.loads((out_dir / "exact_duplicate_summary.json").read_text())
        assert summary["cross_repo_identical_groups"] == 0

    def test_empty_file_is_excluded(self, tmp_path: Path) -> None:
        repo_a = tmp_path / "repo-a"
        repo_b = tmp_path / "repo-b"
        _write(repo_a, "empty.py", "")
        _write(repo_b, "empty.py", "")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run_exact_duplicates([repo_a, repo_b], out_dir)
        summary = json.loads((out_dir / "exact_duplicate_summary.json").read_text())
        assert summary["cross_repo_identical_groups"] == 0

    def test_no_repos_writes_valid_empty_output_not_crash(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        out_path = run_exact_duplicates([], out_dir)
        assert out_path.read_text().splitlines() == [
            "sha256,repo_count,instance_count,relative_paths,repos"
        ]
        summary = json.loads((out_dir / "exact_duplicate_summary.json").read_text())
        assert summary["cross_repo_identical_groups"] == 0
        assert summary["max_repo_count_for_one_file"] == 0

    def test_three_repos_sharing_one_file_reports_repo_count_three(self, tmp_path: Path) -> None:
        repos = []
        for name in ("repo-a", "repo-b", "repo-c"):
            r = tmp_path / name
            _write(r, "shared.py", "identical\n")
            repos.append(r)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run_exact_duplicates(repos, out_dir)
        summary = json.loads((out_dir / "exact_duplicate_summary.json").read_text())
        assert summary["max_repo_count_for_one_file"] == 3

    def test_same_relative_path_flagged_distinctly_from_moved_file(self, tmp_path: Path) -> None:
        repo_a = tmp_path / "repo-a"
        repo_b = tmp_path / "repo-b"
        _write(repo_a, "src/shared.py", "identical\n")
        _write(repo_b, "src/shared.py", "identical\n")  # same relative path
        repo_c = tmp_path / "repo-c"
        _write(repo_c, "lib/shared.py", "identical\n")  # different relative path, same content
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run_exact_duplicates([repo_a, repo_b, repo_c], out_dir)
        summary = json.loads((out_dir / "exact_duplicate_summary.json").read_text())
        # all 3 are one group (same content) but NOT "same path" since repo-c differs
        assert summary["cross_repo_identical_groups"] == 1
        assert summary["cross_repo_identical_same_path_groups"] == 0
