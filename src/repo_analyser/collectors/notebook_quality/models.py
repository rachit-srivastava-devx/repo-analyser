"""Data shape and constants shared across notebook_quality's submodules."""
from __future__ import annotations

import re
from dataclasses import dataclass

from ...core.lang import EXCLUDE_DIR_PARTS

# Jupyter's own checkpoint-copy directory: opening a notebook in Jupyter
# writes a shadow copy under this dir on every save. Conventionally
# gitignored, but a repo that forgot to do so would otherwise double-count
# every notebook (the real file plus its checkpoint clone) -- the same
# hazard EXCLUDE_DIR_PARTS already guards against for node_modules/build/
# dist. Extended locally rather than added to core.lang.EXCLUDE_DIR_PARTS
# itself, matching depgraph.py's own precedent (`PY_EXCLUDE = EXCLUDE_DIR_PARTS
# | {"site-packages"}`) for a single module's own extra exclusion.
NOTEBOOK_EXCLUDE_DIR_PARTS = EXCLUDE_DIR_PARTS | {".ipynb_checkpoints"}

# A SMALL, deliberately narrow pattern set -- see secrets.py's own
# docstring. Do not grow this into a general secret-scanning ruleset;
# that is security.py's gitleaks job, not this module's.
SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS access key ID
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),  # OpenAI-shaped secret key
]


@dataclass
class NotebookQualityResult:
    repo: str
    notebooks_total: int
    notebooks_with_uncleared_outputs: int
    notebooks_with_suspected_secrets: int
    notebooks_nonlinear_execution: int
    notebooks_unparseable: int
    skip_reason: str = ""
