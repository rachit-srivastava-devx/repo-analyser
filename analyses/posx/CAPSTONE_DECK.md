# posx — *Capstone* Briefing (deck spec)

**Deck meta:** Audience: engineering leadership. Slide count: 8. Generated from this
run's own data -- every number below traces to a CSV/JSON in this output directory. This is a
*specification* for a deck, not a rendered one: hand it to a slide-design pass (or read it
directly) to produce the actual presentation.

---

### Slide 1 — Cover / why this engagement happened
- **Purpose:** Frame the whole briefing before any data.
- **Content:**
  - This is one integrated analysis of posx's engineering estate: 26 repos, 10169 commits, ten measurement categories, cross-referenced against each other.
  - The question: where is real risk actually concentrated, and what is the highest-leverage fix?
  - Every number in this deck traces to a CSV/JSON that ships alongside it -- nothing here is asserted without a rerunnable source.
- **Visual:** none -- title/framing slide.
- **Takeaway:** One integrated analysis, ten categories, one prioritized action list.
### Slide 2 — The estate at a glance: 26 repos
- **Purpose:** Establish the structural starting point.
- **Content:**
  - 26 repos analyzed, 10169 total commits.
  - CI gate status: **1 of 26** repos actually run tests before merge/deploy; **25** configure CI for build/deploy only.
  - Duplication: 3001 files are byte-identical across multiple repos.
- **Visual:** charts/repo_activity_top15.png
- **Takeaway:** 25 of 26 repos ship without a test gate.
### Slide 3 — Where the time goes
- **Purpose:** Establish the effort baseline.
- **Content:**
  - Delivery (new capability) is **34.87%** of all classified commits; Correction (bug fixes + reverts) is **31.81%**.
  - 72 candidate toil clusters found, covering 3060 commits of repeated, mechanical work.
- **Visual:** charts/effort_share_over_time.png
- **Takeaway:** See EFFORT_ALLOCATION.md for the full per-author and per-cluster breakdown.
### Slide 4 — Defect escape rate
- **Purpose:** State the quality-risk trend plainly.
- **Content:**
  - 6333 bug-introducing commits attributed (SZZ). Median fix latency 22 days, p90 242 days.
  - Most recent observed months: 9-15% escape rate.
- **Visual:** charts/escape_trend.png
- **Takeaway:** See ESCAPE.md for the full monthly series and per-repo breakdown.
### Slide 5 — Security
- **Purpose:** Name what needs action today, separate from everything else.
- **Content:**
  - 80 secret-history findings across 8 repos (gitleaks, full git history).
  - 2 code-pattern findings (semgrep).
- **Visual:** none -- see SECURITY.md for the per-repo, per-rule breakdown.
- **Takeaway:** Credential rotation, where applicable, is a today action independent of the rest of this deck.
### Slide 6 — Test quality: real execution, not a proxy
- **Purpose:** Distinguish 'has tests' from 'tests pass, right now.'
- **Content:**
  - 4 repos fully passing right now.
  - 9 repos have real failures right now.
  - 3 repos have a working harness and zero tests behind it.
- **Visual:** none.
- **Takeaway:** Every number in this section came from actually running the suite, not counting test files.
### Slide 7 — The highest-priority repos
- **Purpose:** Turn everything above into a short, specific list.
- **Content:**
  - By composite risk score (escape rate, hotspots, duplication, missing CI gates, test failures, security findings, bus-factor): posx-comet-backend, posx-mokobara-store, posx-mokobara-backend.
- **Visual:** none -- see CONSOLIDATION_ROADMAP.md's ranked table.
- **Takeaway:** posx-comet-backend, posx-mokobara-store, posx-mokobara-backend carries the most compounding risk right now.
### Slide 8 — The ask
- **Purpose:** State the concrete next step.
- **Content:**
  - See CONSOLIDATION_ROADMAP.md section 2 for the full, numbered action list, ordered by leverage and urgency.
  - This deck and every underlying number can be regenerated at any time by re-running `python3 cli.py analyze` against the same target.
- **Visual:** none.
- **Takeaway:** The data, the ranking, and the action list are all reproducible -- rerun this analysis on a cadence to track whether the picture is improving.

