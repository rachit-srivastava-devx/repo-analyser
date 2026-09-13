"""Age of a specific line, via `git blame`.

**Complexity, stated plainly**: this calls `git blame --line-porcelain`
*once per file that has at least one marker match*, not once per matched
line/marker. A file with 40 TODOs costs one subprocess call, not 40 --
that's O(F) git invocations (F = files with >=1 match), each itself
O(lines in that file), rather than the naive O(M) (M = total marker count)
per-line design a first draft might reach for. For a huge repo with
thousands of markers concentrated in relatively few files this is the
difference between a handful of subprocess calls and thousands.

Parsing follows escape.py's `_blame_map` precedent (same porcelain header
shape, same defensive full-hex-sha + non-metadata-line check) but reads
`author-time` instead of the introducing sha, since the brief only needs
each line's age, and `--line-porcelain` (unlike plain `--porcelain`)
repeats full metadata after every single header line -- no cross-line
"which commit does this short header refer to" state to track.

A line git blame attributes to the all-zero "Not Committed Yet" pseudo-commit
(an uncommitted/staged working-tree change) still gets a real author-time
(effectively "now"), so it naturally reports as a ~0-day-old marker rather
than crashing or requiring special-casing -- an honest reading of "how old
is this line", not a distinct code path.

`core.util.run()` decodes the subprocess's stdout/stderr as text
(`subprocess.Popen(..., text=True)`, no `errors=`). `git blame`'s
`--line-porcelain` output embeds each line's *commit author name* verbatim,
and git does not validate that commit metadata is valid UTF-8 -- a real
repo can (and, per an adversarial-fixture report, does) contain a commit
whose author name has raw invalid-UTF-8 bytes, which makes `run()`'s own
decode raise `UnicodeDecodeError` before this function ever sees a
`RunResult`. That is caught here, not fixed in `core.util.run()` itself:
`run()` is shared by every collector that shells out (see `escape.py`),
so a decoding-mode change there would need re-verifying against every one
of those call sites' expectations -- out of scope for a `debt_markers`-only
fix. Treated exactly like a non-zero blame `returncode`: this file's ages
come back as `{}` ("unknown"), the marker itself is still counted by the
caller (`aggregate.collect` increments `by_type` before ever consulting
this mapping), so the failure degrades one file's age data, not the whole
result -- not a crash, and not a silent "found nothing" either.
"""
from __future__ import annotations

import re
from pathlib import Path

from ...core.util import run

_HEADER_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")


def line_author_times(repo: Path, rel_path: str) -> dict[int, int]:
    """final line number (1-indexed, current working-tree content) -> the
    introducing/last-touching commit's author-time (unix epoch seconds).
    Empty dict on any blame failure (deleted path, git error, or the
    output containing a commit author name that isn't valid UTF-8 -- see
    module docstring) -- callers treat a missing entry as "age unknown",
    not a crash."""
    try:
        res = run(["git", "blame", "--line-porcelain", "--", rel_path], cwd=repo, check=False)
    except UnicodeDecodeError:
        return {}
    if res.returncode != 0:
        return {}
    mapping: dict[int, int] = {}
    current_line: int | None = None
    for raw_line in res.stdout.splitlines():
        parts = raw_line.split()
        if (parts and _HEADER_SHA_RE.fullmatch(parts[0]) and len(parts) >= 3
                and not raw_line.startswith(("author ", "committer ", "summary "))):
            try:
                current_line = int(parts[2])
            except ValueError:
                current_line = None
            continue
        if raw_line.startswith("author-time ") and current_line is not None:
            try:
                mapping[current_line] = int(raw_line.split(maxsplit=1)[1])
            except (ValueError, IndexError):
                pass
    return mapping
