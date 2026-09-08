from __future__ import annotations

from pathlib import Path

from _notebook_quality_helpers import code_cell, git_repo, markdown_cell, nb

from repo_analyser.collectors.notebook_quality import analyze_repo


class TestSuspectedSecrets:
    def test_aws_key_shaped_string_in_code_source_is_flagged(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "analysis.ipynb").write_text(nb([
            code_cell(
                ["aws_access_key_id = \"AKIAABCDEFGHIJKLMNOP\"\n",
                 "s3 = boto3.client('s3', aws_access_key_id=aws_access_key_id)\n"],
                execution_count=1,
            ),
        ]))
        result = analyze_repo(repo)
        assert result.notebooks_total == 1
        assert result.notebooks_with_suspected_secrets == 1
        assert result.notebooks_with_uncleared_outputs == 0
        assert result.notebooks_nonlinear_execution == 0

    def test_openai_shaped_key_in_source_is_flagged(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "analysis.ipynb").write_text(nb([
            code_cell(["api_key = 'sk-abcdefghijklmnopqrstuvwxyz012345'\n"], execution_count=1),
        ]))
        result = analyze_repo(repo)
        assert result.notebooks_with_suspected_secrets == 1

    def test_secret_in_markdown_cell_source_is_also_flagged(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "analysis.ipynb").write_text(nb([markdown_cell(["Example key: AKIAABCDEFGHIJKLMNOP\n"])]))
        result = analyze_repo(repo)
        assert result.notebooks_with_suspected_secrets == 1

    def test_ordinary_source_has_no_false_positive(self, tmp_path: Path) -> None:
        repo = git_repo(tmp_path / "repo")
        (repo / "analysis.ipynb").write_text(nb([
            code_cell(["api_key = os.environ['API_KEY']\n"], execution_count=1),
        ]))
        result = analyze_repo(repo)
        assert result.notebooks_with_suspected_secrets == 0
