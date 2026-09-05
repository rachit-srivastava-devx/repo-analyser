"""Repo Analyser: multi-dimensional, reproducible codebase analysis.

Every module here computes one measurable dimension of a repo or a portfolio
of repos (git history, tests, dependencies, security, duplication) and writes
its raw output as CSV/JSON so any number in a report can be recomputed by
re-running the same module against the same commit.

Package layout (see docs/ARCHITECTURE.md for the full map):
  core/       shared primitives -- subprocess execution, repo discovery, language detection
  collectors/ one module per measured dimension; each wraps one external tool or git itself
  graph/      the cross-repo/cross-file knowledge graph (GraphML export)
  synthesis/  composite risk ranking and report generation, computed over collectors' output
  reporting/  presentation layer -- charts, markdown, PDF
"""

__version__ = "0.2.0"
