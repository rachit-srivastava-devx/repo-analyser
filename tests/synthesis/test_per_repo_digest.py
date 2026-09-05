from __future__ import annotations

import csv
from pathlib import Path

from repo_analyser.core.util import write_json
from repo_analyser.synthesis.per_repo_digest import _AllData, render_repo_digest, run_per_repo_digest


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("")
        return
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


class TestRenderRepoDigest:
    def test_missing_all_csvs_does_not_crash(self, tmp_path: Path) -> None:
        data = _AllData(tmp_path)
        digest = render_repo_digest("solo-repo", data, "myorg")
        assert "# solo-repo" in digest
        assert "No committed secrets found" in digest
        assert "No cross-repo block-level clones" in digest

    def test_no_prior_trend_data_states_why_not_silently_omitted(self, tmp_path: Path) -> None:
        data = _AllData(tmp_path)
        digest = render_repo_digest("new-repo", data, "myorg")
        assert "No prior run to compare against yet" in digest

    def test_trend_regression_and_improvement_both_listed(self, tmp_path: Path) -> None:
        write_json(tmp_path / "trend_report_per_repo.json", {
            "r": {"regressions": ["risk_score"], "improvements": ["mutation_score"], "metrics": []},
        })
        data = _AllData(tmp_path)
        digest = render_repo_digest("r", data, "myorg")
        assert "Regressed:** risk_score" in digest
        assert "Improved:** mutation_score" in digest

    def test_trend_unchanged_when_no_regressions_or_improvements(self, tmp_path: Path) -> None:
        write_json(tmp_path / "trend_report_per_repo.json", {
            "r": {"regressions": [], "improvements": [], "metrics": []},
        })
        data = _AllData(tmp_path)
        digest = render_repo_digest("r", data, "myorg")
        assert "Unchanged since the last run" in digest

    def test_repo_with_zero_findings_everywhere_renders_clean(self, tmp_path: Path) -> None:
        _write_csv(tmp_path / "security_secrets.csv", [])
        _write_csv(tmp_path / "escapes.csv", [])
        data = _AllData(tmp_path)
        digest = render_repo_digest("clean-repo", data, "myorg")
        assert "No committed secrets found" in digest
        assert "No defect escapes recorded" in digest
        assert "No known-CVE dependency issues" in digest

    def test_not_ranked_when_synthesize_has_not_run(self, tmp_path: Path) -> None:
        data = _AllData(tmp_path)
        digest = render_repo_digest("solo-repo", data, "myorg")
        assert "Not ranked" in digest

    def test_risk_rank_reflects_position_in_risk_ranking_csv(self, tmp_path: Path) -> None:
        _write_csv(tmp_path / "risk_ranking.csv", [
            {"repo": "riskiest", "risk_score": "0.9", "escape_count": "0", "top5_hotspot_sum": "0",
             "exact_dup_file_count": "0", "ci_gate_missing": "True", "test_failure_rate": "0",
             "security_findings": "0", "bus_factor_top_author_share": "0"},
            {"repo": "safest", "risk_score": "0.1", "escape_count": "0", "top5_hotspot_sum": "0",
             "exact_dup_file_count": "0", "ci_gate_missing": "False", "test_failure_rate": "0",
             "security_findings": "0", "bus_factor_top_author_share": "0"},
        ])
        data = _AllData(tmp_path)
        digest = render_repo_digest("riskiest", data, "myorg")
        assert "Ranked **#1 of 2**" in digest

    def test_security_secrets_listed_with_file_and_rule(self, tmp_path: Path) -> None:
        _write_csv(tmp_path / "security_secrets.csv", [
            {"repo": "leaky-repo", "rule_id": "generic-api-key", "file": "public/search-index.json",
             "commit": "abc123", "author": "a", "date": "2026-01-01", "secret_redacted": "rzp_live_***"},
        ])
        data = _AllData(tmp_path)
        digest = render_repo_digest("leaky-repo", data, "myorg")
        assert "1 committed secret(s) found" in digest
        assert "public/search-index.json" in digest
        assert "generic-api-key" in digest

    def test_ci_gate_missing_reported_plainly(self, tmp_path: Path) -> None:
        _write_csv(tmp_path / "ci_gates.csv", [
            {"repo": "deploy-only", "has_ci_config": "True", "workflow_count": "1",
             "workflow_files": "deploy.yml", "any_workflow_runs_tests": "False",
             "all_workflows_deploy_only": "True", "triggers": "push"},
        ])
        data = _AllData(tmp_path)
        digest = render_repo_digest("deploy-only", data, "myorg")
        assert "Not gated" in digest
        assert "deploy.yml" in digest

    def test_cross_repo_duplication_lists_partner_not_self(self, tmp_path: Path) -> None:
        _write_csv(tmp_path / "duplication_clones.csv", [
            {"repo_a": "posx-comet-backend", "path_a": "src/api/middlewares.ts",
             "repo_b": "posx-eume-backend", "path_b": "src/api/middlewares.ts",
             "is_cross_repo": "True", "same_relative_path": "True", "lines": "40", "tokens": "300",
             "format": "typescript"},
        ])
        data = _AllData(tmp_path)
        digest = render_repo_digest("posx-comet-backend", data, "myorg")
        assert "posx-eume-backend" in digest
        assert "1 other repo(s)" in digest

    def test_exact_duplicate_membership_is_exact_not_substring(self, tmp_path: Path) -> None:
        # "posx-comet" must not match "posx-comet-backend" via a naive substring
        # check -- membership is checked against the ';'-split repos list.
        _write_csv(tmp_path / "exact_duplicate_files.csv", [
            {"sha256": "abc", "repo_count": "2", "instance_count": "2",
             "relative_paths": "medusa-config.ts", "repos": "posx-comet-backend;posx-eume-backend"},
        ])
        data = _AllData(tmp_path)
        assert "1 byte-identical file group(s)" in render_repo_digest("posx-comet-backend", data, "myorg")
        assert "No byte-identical files" in render_repo_digest("posx-comet", data, "myorg")

    def test_performance_section_explicit_when_not_measured(self, tmp_path: Path) -> None:
        data = _AllData(tmp_path)
        digest = render_repo_digest("any-repo", data, "myorg")
        assert "Not yet measured" in digest

    def test_testquality_skip_reason_stated_not_silently_omitted(self, tmp_path: Path) -> None:
        _write_csv(tmp_path / "testquality_runs.csv", [
            {"repo": "no-script", "script_used": "", "ran": "False", "exit_code": "-1",
             "runner_detected": "", "tests_passed": "0", "tests_failed": "0", "tests_total": "0",
             "duration_s": "0.0", "skip_reason": "no test script in package.json",
             "node_version_used": "", "failure_mode": ""},
        ])
        data = _AllData(tmp_path)
        digest = render_repo_digest("no-script", data, "myorg")
        assert "no test script in package.json" in digest

    def test_mutation_skip_reason_stated(self, tmp_path: Path) -> None:
        _write_csv(tmp_path / "mutation_results.csv", [
            {"repo": "no-mutants", "file_mutated": "", "total_mutants": "0", "killed": "0",
             "survived": "0", "no_coverage": "0", "timeout": "0", "mutation_score": "0",
             "ran": "False", "skip_reason": "no fully-passing test suite", "suspicious": "0",
             "segfault": "0"},
        ])
        data = _AllData(tmp_path)
        digest = render_repo_digest("no-mutants", data, "myorg")
        assert "no fully-passing test suite" in digest

    def test_lint_skip_reason_stated(self, tmp_path: Path) -> None:
        _write_csv(tmp_path / "lint_quality.csv", [
            {"repo": "no-linter", "linter": "staticcheck", "ran": "False", "error_count": "0",
             "warning_count": "0", "files_with_issues": "0", "top_rules": "",
             "skip_reason": "staticcheck not on PATH"},
        ])
        data = _AllData(tmp_path)
        digest = render_repo_digest("no-linter", data, "myorg")
        assert "staticcheck not on PATH" in digest

    def test_semgrep_findings_listed_with_severity_and_location(self, tmp_path: Path) -> None:
        _write_csv(tmp_path / "security_semgrep.csv", [
            {"repo": "vuln-repo", "check_id": "sql-injection", "severity": "ERROR",
             "file": "src/db.py", "start_line": "42", "message": "unsanitized query"},
        ])
        data = _AllData(tmp_path)
        digest = render_repo_digest("vuln-repo", data, "myorg")
        assert "1 semgrep finding(s)" in digest
        assert "src/db.py:42" in digest
        assert "ERROR" in digest

    def test_escape_latency_summarized(self, tmp_path: Path) -> None:
        _write_csv(tmp_path / "escapes.csv", [
            {"repo": "slow-fix", "fix_sha": "a", "fix_date": "2025-01-01", "file": "x.py",
             "introducing_sha": "b", "introducing_date": "2024-01-01", "latency_days": "300"},
            {"repo": "slow-fix", "fix_sha": "c", "fix_date": "2025-01-01", "file": "y.py",
             "introducing_sha": "d", "introducing_date": "2024-06-01", "latency_days": "100"},
        ])
        data = _AllData(tmp_path)
        digest = render_repo_digest("slow-fix", data, "myorg")
        assert "2 defect(s)" in digest
        assert "100-300 days" in digest


class TestRunPerRepoDigest:
    def test_writes_index_plus_one_file_per_repo(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "deep" / "per-repo"
        written = run_per_repo_digest(tmp_path, out_dir, ["repo-a", "repo-b"], "myorg")
        assert len(written) == 3  # index + 2 repos
        assert (out_dir / "PER_REPO_INDEX.md").exists()
        assert (out_dir / "repo-a.md").exists()
        assert (out_dir / "repo-b.md").exists()

    def test_index_links_to_each_repo_file(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "deep" / "per-repo"
        run_per_repo_digest(tmp_path, out_dir, ["repo-a"], "myorg")
        index = (out_dir / "PER_REPO_INDEX.md").read_text()
        assert "repo-a.md" in index

    def test_empty_repo_list_writes_only_index(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "deep" / "per-repo"
        written = run_per_repo_digest(tmp_path, out_dir, [], "myorg")
        assert len(written) == 1
        assert "No repos in this target" in written[0].read_text()

    def test_single_repo_target_gets_exactly_one_digest(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "deep" / "per-repo"
        written = run_per_repo_digest(tmp_path, out_dir, ["solo"], "solo")
        assert len(written) == 2  # index + the one repo
        assert (out_dir / "solo.md").exists()
