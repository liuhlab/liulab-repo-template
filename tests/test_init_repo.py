"""The text `scripts/init_repo.py` cuts from a file it keeps is still that file's text.

`init-repo` reports a cut whose text has drifted as a miss and carries on, so nothing else
fails when the copy and the file part ways.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def constant(name: str) -> str:
    """A string constant from `scripts/init_repo.py`, read without running the script."""
    tree = ast.parse((REPO / "scripts" / "init_repo.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError(f"scripts/init_repo.py has no {name}")


def test_the_time_limits_paragraph_is_agents_md_own() -> None:
    assert constant("AGENTS_TIME_LIMITS") in (REPO / "AGENTS.md").read_text(encoding="utf-8")
