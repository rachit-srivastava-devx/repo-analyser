"""Chronicle Analyzer: multi-dimensional, reproducible codebase analysis.

Every module here computes one measurable dimension of a repo or a portfolio
of repos (git history, tests, dependencies, security, duplication) and writes
its raw output as CSV/JSON so any number in a report can be recomputed by
re-running the same module against the same commit.
"""
