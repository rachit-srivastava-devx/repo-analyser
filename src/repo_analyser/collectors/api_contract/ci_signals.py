"""Signal 2: does CI plausibly run a breaking-change/schema-diff tool
against a spec file. See ci_workflows.py for the "read the actual config,
don't infer it" loading logic and the comment-stripping that narrows (but
does not eliminate) the echo/TODO-string false positive.

Checked independently of which spec_kind (if any) discovery.py found: a
repo can run `buf breaking` in CI without this collector's own bounded
glob happening to find its .proto files (e.g. they live in a vendored/
generated path not walked), or vice versa -- gating one signal on the
other would silently under-report real findings."""
from __future__ import annotations

from pathlib import Path

from .ci_workflows import load_workflow_docs, step_texts
from .patterns import BREAKING_CHANGE_CI_PATTERNS


def breaking_change_tools_wired_into_ci(repo: Path) -> tuple[set[str], list[str]]:
    docs, errors = load_workflow_docs(repo)
    all_text = " ".join(text for doc in docs for text in step_texts(doc))
    tools = {tool for tool, pattern in BREAKING_CHANGE_CI_PATTERNS.items() if pattern.search(all_text)}
    return tools, errors
