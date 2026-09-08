"""Shared fixture-building helpers for the design_docs test package. Named
per-collector (not the generic `_helpers.py`) because tests/ has no
`__init__.py` anywhere -- pytest's prepend import mode means a generic name
would collide with every other collector's identically-named helper module
in sys.modules the moment the full suite runs together (AGENTS.md §4)."""
from __future__ import annotations

import subprocess
from pathlib import Path

_ENV = {
    "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com",
    "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
}


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True,
                           text=True, env=_ENV)


def init_repo(repo: Path) -> Path:
    repo.mkdir(parents=True, exist_ok=True)
    git(repo, "init", "-q")
    return repo


def write(repo: Path, rel: str, content: str) -> Path:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def write_bytes(repo: Path, rel: str, data: bytes) -> Path:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return p


def commit_all(repo: Path, message: str) -> None:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)


ADR_ACCEPTED = """# 0001. Use PostgreSQL

## Context

We need a relational database.

## Decision

We will use PostgreSQL.

## Consequences

Operational cost of running Postgres ourselves.

## Status

Accepted

Tagged as a two-way door -- reversible if we outgrow it.
"""

ADR_PROPOSED_NO_SECTIONS = """# 0002. Maybe use Kafka

Status: Proposed

Just some notes, no real structure yet.
"""

RUNBOOK_TEXT = """# Runbook

## Deploy

Run `make deploy`.

## Rollback

Run `make rollback` to revert to the previous release.

## On-call

Page the on-call engineer via PagerDuty for any known failure mode below.
"""
