"""API-contract / breaking-change discipline detection: does this repo have
a declared, versioned API schema (OpenAPI/Swagger, GraphQL SDL, or
Protobuf); is a breaking-change/schema-diff tool actually wired into CI to
guard it; is spec-to-implementation contract-test tooling (Dredd, Prism,
Schemathesis, Pact) configured; and where a deprecation marker exists in a
spec, is there an accompanying sunset-date convention nearby. Mirrors
ci_gates.py's own shape deliberately: presence-and-correctness-of-practice
detection from real repo config/schema files, not live execution of an
external diff/contract-test tool. See
docs/checklist-by-repo-type/single-repo.md's "Interface & API Contract
Stability" section for the three criteria this answers, and
docs/METHODOLOGY.md for the exact detection method and known limitations.

Four signals, checked and reported independently -- never averaged into
one score (docs/ARCHITECTURE.md's "two tools measuring the same thing stay
two separate outputs" rule):

  1. has_spec / spec_kinds / spec_file_count / spec_files -- which kind(s)
     of machine-readable spec exist, and where. A repo can have more than
     one kind at once (e.g. a gRPC service with a hand-maintained OpenAPI
     gateway doc): all kinds found are reported in spec_kinds, not just the
     first. spec_parse_errors reports a spec file that exists but fails to
     parse, distinctly from "no spec at all" (has_spec=False).
  2. has_breaking_change_check / breaking_change_tools -- whether a known
     breaking-change/schema-diff tool (oasdiff, graphql-inspector, buf
     breaking, openapi-diff, swagger-diff) is invoked as a real command in
     a CI workflow step, not merely mentioned in a comment/string.
  3. has_contract_test_tooling / contract_test_tools -- whether Dredd,
     Prism, Schemathesis, or Pact is configured (dependency manifest, known
     config file/dir, or a CI step invoking it).
  4. deprecated_with_sunset_count / deprecated_without_sunset_count --
     counts of deprecation markers found in the detected spec file(s),
     split by whether a sunset-date convention was found nearby. "Deprecated
     but no sunset signal" is itself the interesting finding this checklist
     item cares about, not an error state.

skip_reason is populated only when has_spec is False (mirrors ci_gates.py's
own skip_reason exactly) -- it says nothing about the other three signals,
which are real, independent findings even for a repo with no detected spec
(e.g. a repo with a Pact broker but no local spec file this collector's
bounded glob can see).

Deliberate v1 scope, stated honestly (see docs/HANDOFF.md's sign-off note):
this is static config/schema-presence detection -- it does not execute
oasdiff/graphql-inspector/buf/Dredd/etc. against two live schema versions.
Integrating and actually running those tools is a reasonable future pass
once this detection layer exists.
"""
from __future__ import annotations

from .analyze import analyze_repo
from .models import ApiContractResult
from .runner import run_api_contract

__all__ = ["ApiContractResult", "analyze_repo", "run_api_contract"]
