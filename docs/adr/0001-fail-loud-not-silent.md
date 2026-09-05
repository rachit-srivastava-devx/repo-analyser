# ADR-0001: A module returns real data or raises — never a silent empty result

- **Status:** Accepted (in force since the first collector was written; formalized here)
- **Formerly cited as:** `CHRONICLE-ADR-001` (pre-rename references in old commit messages/docs)

## Context

`dependency-cruiser` returned "0 modules" for a real directory during development — not because
the directory had no dependencies, but because it was passed a directory argument instead of an
explicit file list, and it silently no-oped instead of erroring. The 0 looked exactly like "this
repo has no internal imports," which is a plausible, boring, easy-to-believe answer. It was wrong.
It was caught only by comparing directory-mode output against explicit-file-list mode on the same
repo (0 vs. 7,585 modules) — an accident of double-checking, not something the code itself flagged.

The same shape of bug recurred independently at least three more times while building this tool
(see `docs/METHODOLOGY.md`'s "Known issues" section): osv-scanner's severity field, vitest's
all-failed output format, and the Python import resolver each had a code path that produced a
quiet, plausible-looking zero or wrong value instead of surfacing that something had gone wrong.

## Decision

Every collector module returns real computed data, or raises `core.util.ToolExecutionError` (or a
documented, explicit `skipped_reason`) — never an empty/zero result standing in for "the tool
didn't work" or "I didn't handle this case." Concretely:

- `core.util.run()` raises `ToolExecutionError` (with the real captured stderr) on non-zero exit
  by default. A caller that expects legitimate non-zero exits (gitleaks finding a secret, semgrep
  finding a match) passes `check=False` and inspects `returncode` **explicitly** — never by
  defaulting a swallowed exception to "no findings."
- An unsupported language, tool, or code path returns an explicit `skipped_reason` string in its
  output row — never a bare `0`/`[]`/`{}` that's indistinguishable from "checked, found nothing."
- A `0` that *is* a legitimate answer (a repo really does have zero circular imports) is
  distinguished from a `0` that means "the check didn't run" by the presence of a `skipped_reason`
  key — code that reads collector output checks for that key before treating a count as real.

## Consequences

- More verbose failure paths than a naive `try/except: return []`. This is the point — every one
  of those `except` blocks is a place a future silent-zero bug would otherwise hide.
- A collector that isn't sure whether an empty result is real or a failure must find out (compare
  against a known-non-empty case, as the dependency-cruiser bug above was actually caught) rather
  than ship the ambiguity.
- New collectors are reviewed against this ADR specifically: "what does this return when the
  external tool finds nothing, versus when it's not installed, versus when it errors?" — three
  different questions, three different (and distinguishable) answers.
