"""Per-repo orchestration: combines discovery, CI-signal, contract-test,
and deprecation detection into one ApiContractResult. See package
docstring for the full contract and precedence rules."""
from __future__ import annotations

from pathlib import Path

from .ci_signals import breaking_change_tools_wired_into_ci
from .contract_testing import contract_test_tools_detected
from .deprecation import count_deprecations
from .discovery import find_graphql_and_protobuf_files, find_openapi_files
from .models import ApiContractResult


def _rel(repo: Path, p: Path) -> str:
    try:
        return str(p.relative_to(repo))
    except ValueError:
        return str(p)


def analyze_repo(repo: Path) -> ApiContractResult:
    openapi_files, openapi_errors = find_openapi_files(repo)
    graphql_files, protobuf_files = find_graphql_and_protobuf_files(repo)

    kinds = []
    all_files: list[tuple[Path, str]] = []
    if openapi_files:
        kinds.append("openapi")
        all_files += [(p, "openapi") for p in openapi_files]
    if graphql_files:
        kinds.append("graphql")
        all_files += [(p, "graphql") for p in graphql_files]
    if protobuf_files:
        kinds.append("protobuf")
        all_files += [(p, "protobuf") for p in protobuf_files]
    has_spec = bool(all_files)

    with_sunset = without_sunset = 0
    for path, kind in all_files:
        w, wo = count_deprecations(path, kind)
        with_sunset += w
        without_sunset += wo

    ci_tools, ci_errors = breaking_change_tools_wired_into_ci(repo)
    contract_tools = contract_test_tools_detected(repo)
    parse_errors = openapi_errors + ci_errors

    skip_reason = "" if has_spec else (
        "no API schema source-of-truth found (openapi/swagger file, graphql schema, or .proto files)"
    )
    return ApiContractResult(
        repo=repo.name,
        has_spec=has_spec,
        spec_kinds=";".join(kinds),
        spec_file_count=len(all_files),
        spec_files=";".join(sorted(_rel(repo, p) for p, _ in all_files)),
        spec_parse_errors=";".join(parse_errors),
        has_breaking_change_check=bool(ci_tools),
        breaking_change_tools=";".join(sorted(ci_tools)),
        has_contract_test_tooling=bool(contract_tools),
        contract_test_tools=";".join(sorted(contract_tools)),
        deprecated_with_sunset_count=with_sunset,
        deprecated_without_sunset_count=without_sunset,
        skip_reason=skip_reason,
    )
