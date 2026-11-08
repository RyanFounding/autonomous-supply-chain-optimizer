from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def test_app_renders_sample_analysis_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    at = AppTest.from_file(APP, default_timeout=30).run()

    assert not at.exception
    assert [s.value for s in at.subheader][:2] == ["Build capacity", "Shortages"]
    assert at.button[0].disabled  # briefing needs a key
