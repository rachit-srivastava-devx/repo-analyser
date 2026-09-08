"""Per-file classification used to flag a `ChangedFile` as a lockfile or as
generated: `_LOCKFILE_NAMES` is matched directly against a path's basename
by `diff.py`'s `get_changed_files`; `_generated_flags` answers the same
question for `.gitattributes`-driven generated-file detection, which needs
an actual git call rather than a static name set.
"""
from __future__ import annotations

from pathlib import Path

from ..core.util import run
from .name_status import _drop_trailing_empty

_LOCKFILE_NAMES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "Gemfile.lock", "poetry.lock", "Pipfile.lock",
    "go.sum", "go.sum.bak", "Cargo.lock", "composer.lock",
}

# git check-attr accepts multiple pathnames per invocation; chunked so one
# PR touching an extreme number of files can't build an argv past the
# platform's ARG_MAX.
_CHECK_ATTR_CHUNK_SIZE = 1000


def _generated_flags(repo: Path, sha: str, paths: list[str]) -> dict[str, bool]:
    """Whether each path matches a `linguist-generated` or `-diff`
    `.gitattributes` rule *as of `sha`*, via `git check-attr --source=<sha>`
    -- reusing git's own gitattributes engine (pattern precedence,
    directory scoping, last-match-wins) rather than re-implementing
    gitattributes glob matching by hand. A path with no `.gitattributes` at
    all, or no matching rule, reports "unspecified" (verified empirically)
    and is simply False here -- same as the task's explicit contract for a
    repo with no `.gitattributes` file at all.

    `--source` needs git >= 2.40; on any older git that rejects the flag,
    this degrades every path to False rather than raising -- the same
    "imperfect signal, never a crash" contract.
    """
    if not paths:
        return {}
    flags: dict[str, bool] = dict.fromkeys(paths, False)
    for i in range(0, len(paths), _CHECK_ATTR_CHUNK_SIZE):
        chunk = paths[i:i + _CHECK_ATTR_CHUNK_SIZE]
        result = run(
            ["git", "check-attr", "-z", f"--source={sha}", "linguist-generated", "diff", "--", *chunk],
            cwd=repo, check=False,
        )
        if result.returncode != 0:
            continue  # unsupported --source on an old git -- fail open to False
        tokens = _drop_trailing_empty(result.stdout.split("\0"))
        for j in range(0, len(tokens), 3):
            path, attr, value = tokens[j], tokens[j + 1], tokens[j + 2]
            if attr == "linguist-generated" and value in ("set", "true"):
                flags[path] = True
            elif attr == "diff" and value == "unset":
                flags[path] = True
    return flags
