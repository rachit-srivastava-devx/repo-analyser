from __future__ import annotations

from pathlib import Path

from repo_analyser.collectors.codebase_modularity.god_class import find_god_class_findings

from ._codebase_modularity_helpers import (
    class_with_exact_loc,
    class_with_method_count,
    init_repo,
    write,
)


def test_class_with_exactly_20_methods_is_not_a_god_class(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "m.py", class_with_method_count("C", 20))
    result = find_god_class_findings(repo)
    assert result.god_class_count == 0
    assert result.god_class_language_supported is True


def test_class_with_21_methods_is_a_god_class(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "m.py", class_with_method_count("C", 21))
    result = find_god_class_findings(repo)
    assert result.god_class_count == 1
    assert "m.py:C(methods=21," in result.god_classes


def test_class_at_exactly_300_loc_is_not_a_god_class(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "m.py", class_with_exact_loc("C", 300))
    result = find_god_class_findings(repo)
    assert result.god_class_count == 0


def test_class_at_301_loc_is_a_god_class(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "m.py", class_with_exact_loc("C", 301))
    result = find_god_class_findings(repo)
    assert result.god_class_count == 1
    assert "m.py:C(methods=1,loc=301)" in result.god_classes


def test_nested_class_methods_do_not_count_toward_outer_class(tmp_path: Path) -> None:
    src = (
        "class Outer:\n"
        "    def m0(self):\n"
        "        return None\n"
        "\n"
        "    class Inner:\n"
        + "\n".join(f"        def im{i}(self):\n            return None" for i in range(25))
        + "\n"
    )
    repo = init_repo(tmp_path / "r")
    write(repo, "m.py", src)
    result = find_god_class_findings(repo)
    # Inner has 25 direct methods -> god class. Outer has 1 direct method
    # (Inner doesn't count as a method) -> not a god class on method count,
    # and its LOC is small, so only Inner should be flagged.
    assert result.god_class_count == 1
    assert "Inner(methods=25" in result.god_classes
    assert "Outer(methods=" not in result.god_classes


def test_class_with_only_nested_class_child_has_zero_methods_but_loc_still_checked(tmp_path: Path) -> None:
    pad_lines = "\n".join(f"            p{i} = {i}" for i in range(310))
    src = (
        "class Outer:\n"
        "    class Inner:\n"
        "        def m0(self):\n"
        f"{pad_lines}\n"
        "            return None\n"
    )
    repo = init_repo(tmp_path / "r")
    write(repo, "m.py", src)
    result = find_god_class_findings(repo)
    # Outer has zero direct methods (Inner is a class, not a FunctionDef)
    # but Outer's own LOC spans the whole (long) Inner body, so it must
    # still be flagged via the LOC half of the check, methods=0.
    assert "Outer(methods=0,loc=" in result.god_classes


def test_nested_class_def_inside_a_function_is_found(tmp_path: Path) -> None:
    src = (
        "def factory():\n"
        "    class Local:\n"
        + "\n".join(f"        def m{i}(self):\n            return None" for i in range(22))
        + "\n"
        "    return Local\n"
    )
    repo = init_repo(tmp_path / "r")
    write(repo, "m.py", src)
    result = find_god_class_findings(repo)
    assert result.god_class_count == 1
    assert "Local(methods=22" in result.god_classes


def test_syntax_error_file_is_skipped_not_crashed(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "broken.py", "def f(:\n    pass\n")
    write(repo, "ok.py", class_with_method_count("Fine", 21))
    result = find_god_class_findings(repo)
    assert result.god_class_count == 1
    assert "Fine(methods=21" in result.god_classes


def test_non_utf8_python_source_does_not_crash(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    (repo / "bad.py").write_bytes(b"class C:\n    x = '\xff\xfe'\n")
    result = find_god_class_findings(repo)
    assert result.god_class_language_supported is True
    assert isinstance(result.god_class_count, int)


def test_non_python_repo_reports_language_not_supported_not_zero_found(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    write(repo, "main.go", "package main\n\nfunc main() {}\n")
    result = find_god_class_findings(repo)
    assert result.god_class_count == 0
    assert result.god_classes == ""
    assert result.god_class_language_supported is False


def test_empty_repo_reports_language_not_supported(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    result = find_god_class_findings(repo)
    assert result.god_class_language_supported is False
