"""Agent-skill / MCP tool-definition quality: for repos that ship Claude
Code skills (`SKILL.md`) or MCP tool manifests, does each declared
capability actually carry the fields its own consumers depend on -- a name,
and (weakly) a description?

v1 scope is deliberately narrow: schema presence + structural validity (does
the file parse at all, with the fields its own real convention requires) and
description-completeness (a weak "triggering-accuracy" proxy, not a real
eval). Explicitly OUT of scope: any semantic privilege-scope or
prompt-injection analysis -- that needs live-LLM evaluation, not static
analysis, and isn't attempted here.

Split by concern across this package's submodules -- see each one's own
docstring for what it covers; analyze.py explains how the two file kinds
combine into one result.
"""
from __future__ import annotations

from .analyze import analyze_repo
from .models import AgentSkillQualityResult
from .runner import run_agent_skill_quality

__all__ = ["AgentSkillQualityResult", "analyze_repo", "run_agent_skill_quality"]
