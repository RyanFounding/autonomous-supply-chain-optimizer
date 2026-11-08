"""Agent layer: turns the deterministic analysis into a sourcing recommendation.

The analysis is computed before any agent runs and passed in as JSON. Agents
reason about trade-offs (cost versus downtime, supplier risk) but never redo
the arithmetic, so a model mistake cannot change a stock figure.
"""

from __future__ import annotations

import os

from crewai import Agent, Crew, Process, Task
from crewai.crews.crew_output import CrewOutput

from supply_chain.models import SupplyChainAnalysis

DEFAULT_MODEL = "gemini/gemini-2.5-flash"

NUMBERS_RULE = (
    "Use only the figures in the analysis provided. Do not recalculate or invent numbers."
)


def build_crew(analysis: SupplyChainAnalysis, model: str | None = None) -> Crew:
    llm = model or os.environ.get("LLM_MODEL", DEFAULT_MODEL)
    analysis_json = analysis.model_dump_json(indent=2)

    risk_analyst = Agent(
        role="Production Risk Analyst",
        goal="Explain which part shortages put production at risk and why.",
        backstory="Reviews plant inventory audits and translates them into production impact.",
        llm=llm,
    )
    procurement = Agent(
        role="Procurement Specialist",
        goal="Choose a supplier for each short part, balancing unit cost against lead time.",
        backstory="Sources industrial components and weighs price against line-down risk.",
        llm=llm,
    )
    director = Agent(
        role="Operations Director",
        goal="Turn the findings into a short, decision-ready plan.",
        backstory="Accountable for plant uptime and production cost.",
        llm=llm,
    )

    assess = Task(
        description=(
            "Review this inventory and sourcing analysis and identify the shortages that "
            f"limit production most. {NUMBERS_RULE}\n\n{analysis_json}"
        ),
        expected_output="A ranked list of production risks with the figures that support each.",
        agent=risk_analyst,
    )
    source = Task(
        description=(
            "For each short part, recommend one supplier from the listed options and justify "
            "the cost versus lead-time trade-off. Flag any part with no supplier. "
            f"{NUMBERS_RULE}"
        ),
        expected_output="One recommended supplier per part, with a one-line justification.",
        agent=procurement,
        context=[assess],
    )
    brief = Task(
        description=(
            "Write a three-bullet executive briefing: the production impact, the sourcing "
            f"decision with its total cost, and any open risk. {NUMBERS_RULE}"
        ),
        expected_output="Exactly three bullet points.",
        agent=director,
        context=[assess, source],
    )

    return Crew(
        agents=[risk_analyst, procurement, director],
        tasks=[assess, source, brief],
        process=Process.sequential,
        max_rpm=10,  # stays under the Gemini free-tier request quota
    )


def run_briefing(analysis: SupplyChainAnalysis, model: str | None = None) -> str:
    result = build_crew(analysis, model).kickoff()
    if not isinstance(result, CrewOutput):
        raise TypeError("Streaming output is not supported here; expected a CrewOutput.")
    return result.raw
