# posx — Commit *Ontology*

*Every non-merge commit classified by a deterministic rule table (file-pattern rules first,
then conventional-commit prefix / keyword match, `other` when neither matches -- see
`docs/METHODOLOGY.md` for the exact rules and priority order). No LLM in the loop, fully
reproducible. Data: `ontology_commits.csv`, `ontology_summary.json`.*

## 1. The headline: where the work actually goes

7137 non-merge commits classified, **17.58% left honestly unclassified** rather than
force-fit into a category.

| Superclass | % of commits |
|---|---|
| delivery | 34.87% |
| correction | 31.81% |
| other | 17.58% |
| code_health | 7.66% |
| ops_config | 5.86% |
| housekeeping | 1.44% |
| data_schema | 0.77% |

**Delivery (34.87%) vs. Correction (31.81%)**: correction is nearly as large as delivery -- for every commit that ships something new, a comparable amount of work is spent fixing something.
Ops & config sits at 5.86% of all commits -- low, consistent with a young codebase that hasn't yet accumulated infrastructure sprawl.

## 2. Full leaf-type breakdown

| Leaf type | Count |
|---|---|
| feature | 2489 |
| bug_fix | 2223 |
| other | 1255 |
| refactor | 399 |
| ci_build | 388 |
| docs | 100 |
| chore | 92 |
| data_schema | 55 |
| revert | 47 |
| test | 36 |
| access_admin | 25 |
| perf | 12 |
| style | 11 |
| dependency_bump | 5 |

## 3. Honest limitations

- The classifier's "other" bucket (17.58%) is deliberately conservative: an ambiguous,
  jargon-heavy commit subject is left unclassified rather than guessed into a category (see
  `ONTOLOGY_AUDIT.md`'s disagreement analysis for the specific asymmetry this produces against
  a more liberal human rater).
- File-pattern rules only fire when *all* files a commit touched match one pattern; a mixed
  commit (e.g. a lockfile bump alongside a real code change) falls through to message-based
  classification, which may miscategorize it.

*Raw data: `ontology_commits.csv`. Run `ontology_audit` (see README) to independently verify
this classifier's accuracy on your own corpus before trusting the headline percentages.*
