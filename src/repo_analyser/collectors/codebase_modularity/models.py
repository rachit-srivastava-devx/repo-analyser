"""Result dataclass for the codebase_modularity collector. See package
docstring (__init__.py) for the full contract; see module_size.py/
god_class.py/layering.py for the three independent signals this combines."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CodebaseModularityResult:
    repo: str
    oversized_file_count: int
    oversized_files: str
    oversized_package_count: int
    oversized_packages: str
    god_class_count: int
    god_classes: str
    god_class_language_supported: bool
    layering_tool_detected: str
    layering_config_path: str
    skip_reason: str
