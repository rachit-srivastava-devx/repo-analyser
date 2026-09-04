# posx — Method *Review*

*This tool's own self-audit: which modules ran, which failed, and what has been independently
checked rather than taken on faith. See `docs/METHODOLOGY.md` for the full list of bugs found
and fixed while building this tool -- kept visible rather than quietly corrected away.*

## Module run status

| Module | Status | Elapsed (s) |
|---|---|---|
| knowledge_graph | ok | 0.3 |

All 1 modules completed.

## What has NOT been independently verified in this run

- Composite risk ranking weights (`synthesize.py`) are a stated judgment call, not
  empirically validated against any outcome.
- Toil clusters (`effort.py`) are mechanically grouped, not diff-read and confirmed.
- Security findings below a format-confirmed rule (generic-api-key, curl-auth-header) are not
  individually triaged for true/false-positive status.

*This section exists so a reader can tell which numbers in this report carry independent
verification and which are this tool's first-pass output -- treat the latter as a lead to
check, not a settled fact.*
