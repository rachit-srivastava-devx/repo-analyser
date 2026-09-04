# Ontology classifier: independent blind audit

## Method

`ontology.py`'s classifier is deterministic (file + keyword rules, no LLM).
To check whether its rules actually agree with human judgment, a stratified
random sample of 193 commit subjects (up to 15 per leaf category, from the
full 7,137-commit classified corpus) was given to a fresh agent with **no
access to the classifier's own output** — it was handed only `idx, repo,
sha, subject` and the same 14-category taxonomy definition, and asked to
classify independently. Agreement was then computed by this tool, not by
the auditing agent.

Sample: `/tmp/ontology_audit_sample.csv` (193 rows). Independent labels:
`/tmp/ontology_audit_independent.csv`. This tool's labels (not shown to the
auditor): `/tmp/ontology_audit_truth.csv`.

## Result

- **Exact leaf agreement: 132/193 = 68.4%**
- **Superclass agreement: 139/193 = 72.0%**

For comparison, the Button/Chronicle engagement's own LLM-based classifier
scored 77%/82% against a blind LLM re-rating. This tool's deterministic
rules score somewhat lower — read the ontology percentages
(`ontology_summary.json`) as **directionally reliable, not precise to the
percentage point**: a 35% vs 32% split between two superclasses is not
distinguishable at this accuracy; a 35% vs 6% split is.

## Where it disagrees, and why (systematic, not random)

| Pattern | Count | Diagnosis |
|---|---:|---|
| `perf` → `ci_build` | 8 | The `perf` keyword regex (`optimi[sz]e`, `speed up`) fires on commits like "optimize Docker build" that are really CI/build work, not application performance. **Classifier bug**, not a taxonomy disagreement. |
| `style` → `chore` | 7 | Genuine taxonomy boundary — "style" (lint/format) as a chore subtype is a defensible alternate reading, not an error. |
| `test` → `other` | 5 | The independent rater found several `test`-keyword matches too ambiguous to commit to; likely the keyword regex matches "test" as a substring in unrelated contexts. |
| `chore`/`bug_fix` → `ci_build` | 6 | This tool under-detects `ci_build` relative to a human reader willing to infer deploy/pipeline intent from less explicit wording. |
| `other`/`data_schema`/`refactor` → `feature` | 9 | The independent rater defaults to `feature` for ambiguous, jargon-heavy internal commit subjects (e.g. terse project codenames); this tool defaults to a narrower category or `other`. This is a **deliberate asymmetry**: overclaiming "feature" on an unclear commit would inflate the one number (delivery %) most likely to be quoted, so the classifier is built to under-claim there specifically — see `other_pct` in the ontology summary, reported rather than hidden. |

## What this means for the headline ontology numbers

The `perf`→`ci_build` bug is worth fixing in a future pass (it's a handful
of commits, doesn't move the superclass percentages meaningfully — `perf`
is 0.17% of the corpus either way). The `other`-bucket conservatism is a
deliberate design choice, not a bug: it trades a larger unclassified bucket
(17.6%) for lower risk of overclaiming the Delivery percentage specifically.
