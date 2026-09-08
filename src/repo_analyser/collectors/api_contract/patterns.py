"""Detection constants for the api_contract collector: conventional spec
paths, CI-tool command patterns, contract-test dependency/config names, and
deprecation/sunset marker regexes. Kept separate from models.py so each
file stays under the package's own ~80-line convention."""
from __future__ import annotations

import re

# Conventional OpenAPI/Swagger source-of-truth filenames -- fixed list
# (matches ci_gates.py/performance.py's own "conventional paths, not a
# blind glob" precedent), checked at repo root, docs/, and api/.
OPENAPI_FILENAMES = [
    "openapi.yaml", "openapi.yml", "openapi.json",
    "swagger.yaml", "swagger.yml", "swagger.json",
]
OPENAPI_DIRS = ["", "docs", "api"]

# Broader, bounded glob for a repo that names its spec unconventionally but
# still names the file after itself (e.g. "openapi.v2.yaml",
# "my-service.swagger.json") -- a filename *containing* "openapi"/"swagger"
# anywhere in the tree, gated by a content check (must actually parse into
# a dict with "openapi"/"swagger" + "paths" keys) so a coincidentally-named
# file that isn't really a schema doesn't count.
OPENAPI_NAME_HINT_RE = re.compile(r"(openapi|swagger)", re.IGNORECASE)
OPENAPI_SUFFIXES = {".yaml", ".yml", ".json"}

GRAPHQL_SUFFIXES = {".graphql", ".gql", ".graphqls"}
PROTO_SUFFIX = ".proto"

# CI step text pattern for each breaking-change/schema-diff tool's real
# invocation shape -- a subcommand/flag where the tool's CLI has one
# (oasdiff, buf breaking), name-only where it genuinely has no fixed
# subcommand (graphql-inspector, swagger-diff). Comment lines are stripped
# before matching (see ci_signals.strip_comment_lines) so a bash comment
# merely *mentioning* a tool doesn't count -- narrows, does not eliminate,
# the residual false positive of a `run:` step whose text is an echo/string
# mentioning a tool (see package docstring's stated residual risk).
BREAKING_CHANGE_CI_PATTERNS = {
    "oasdiff": re.compile(r"\boasdiff\s+(breaking|changelog|diff|summary)\b|oasdiff-action", re.I),
    "graphql-inspector": re.compile(r"\bgraphql-inspector\b", re.I),
    "buf breaking": re.compile(r"\bbuf\s+breaking\b", re.I),
    "openapi-diff": re.compile(r"\bopenapi-diff\b", re.I),
    "swagger-diff": re.compile(r"\bswagger-diff\b", re.I),
}

# Contract-test tooling: dependency-manifest package names and known config
# files/dirs for each tool. Checked independently of CI-wiring (a repo can
# have the dependency/config present and run it locally/pre-commit without
# a dedicated CI step this module's bounded workflow scan would see).
CONTRACT_TEST_DEPENDENCY_NAMES = {
    "dredd": ["dredd"],
    "prism": ["@stoplight/prism-cli", "@stoplight/prism-http"],
    "schemathesis": ["schemathesis"],
    "pact": ["pact", "@pact-foundation/pact", "pact-python", "pact_python"],
}
CONTRACT_TEST_CONFIG_PATHS = {
    "dredd": ["dredd.yml", "dredd.yaml", ".dredd.yml"],
    "pact": ["pact.json", "pacts", "pact-broker.yml"],
}
CONTRACT_TEST_CI_PATTERNS = {
    "dredd": re.compile(r"\bdredd\b", re.I),
    "prism": re.compile(r"\bprism\s+(mock|validate)\b", re.I),
    "schemathesis": re.compile(r"\bschemathesis\b|\bst\s+run\b", re.I),
    "pact": re.compile(r"\bpact-broker\b|\bpact\s+verify\b|\bpact_verifier\b", re.I),
}

# Deprecation-marker regexes, one per spec kind, and the sunset-signal
# regex searched in a small window of lines around each match.
DEPRECATED_MARKER_RE = {
    "openapi": re.compile(r"deprecated\s*:\s*true", re.I),
    "graphql": re.compile(r"@deprecated(?:\s*\(([^)]*)\))?"),
    "protobuf": re.compile(r"\[\s*deprecated\s*=\s*true\s*\]"),
}
SUNSET_SIGNAL_RE = re.compile(
    r"(x-sunset|x-deprecated-date|sunset)\s*[:=]?\s*[\"']?(\d{4}-\d{2}-\d{2})"
    r"|(\d{4}-\d{2}-\d{2})",
    re.I,
)
SUNSET_WINDOW_LINES = 3
