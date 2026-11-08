from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _names(specs: list[str]) -> set[str]:
    return {re.split(r"[\[<>=!~ ;]", spec, maxsplit=1)[0].lower() for spec in specs}


def test_streamlit_requirements_match_pyproject() -> None:
    """The deployed app installs requirements.txt, so it must list every runtime dependency."""
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    declared = _names(pyproject["project"]["dependencies"])

    lines = (ROOT / "requirements.txt").read_text().splitlines()
    listed = _names([ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")])

    assert declared == listed
