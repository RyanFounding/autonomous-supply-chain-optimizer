from __future__ import annotations

import pytest

from supply_chain.data import SupplyChainData
from supply_chain.engine import analyze

crew_module = pytest.importorskip("supply_chain.crew")


def test_crew_receives_precomputed_figures(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    analysis = analyze(SupplyChainData.sample())

    crew = crew_module.build_crew(analysis)

    assert len(crew.agents) == 3
    assert len(crew.tasks) == 3
    first_task = crew.tasks[0].description
    assert '"max_buildable_units": 2' in first_task
    assert "Ceramic Bearings" in first_task
    assert crew.tasks[2].context == [crew.tasks[0], crew.tasks[1]]
