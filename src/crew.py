from crewai import Agent, Task, Crew, Process
from src.tools import audit_bom_inventory_tool, match_suppliers_tool
import os

def run_supply_chain_crew(bom_json: str, inv_json: str, sup_json: str):
    # Ensure API Key is passed securely
    llm_model = "gemini/gemini-2.5-flash"

    risk_analyst = Agent(
        role="Risk Analyst",
        goal="Audit factory inventory and report exact bottlenecks.",
        backstory="Strict auditor using deterministic tools.",
        tools=[audit_bom_inventory_tool],
        llm=llm_model
    )

    procurement = Agent(
        role="Procurement Specialist",
        goal="Select optimal suppliers balancing cost vs downtime.",
        backstory="Shrewd negotiator.",
        tools=[match_suppliers_tool],
        llm=llm_model
    )

    director = Agent(
        role="Operations Director",
        goal="Synthesize findings into a final executive plan.",
        backstory="C-level executive focused on plant uptime.",
        llm=llm_model
    )

    task_1 = Task(
        description=f"Run the BOM Shortage Auditor using: BOM={bom_json}, INV={inv_json}.",
        expected_output="Audit report detailing build capacity and shortages.",
        agent=risk_analyst
    )

    task_2 = Task(
        description=f"Using Task 1 shortages, invoke the Supplier Matcher with: {sup_json}. Pick the best vendor.",
        expected_output="Vendor selection with justifications.",
        agent=procurement
    )

    task_3 = Task(
        description="Write a 3-bullet executive resolution briefing based on the previous tasks.",
        expected_output="A 3-bullet executive summary.",
        agent=director
    )

    crew = Crew(
        agents=[risk_analyst, procurement, director], 
        tasks=[task_1, task_2, task_3], 
        process=Process.sequential,
        max_rpm=10  # Throttles execution to prevent 429 Quota errors
    )
    return crew.kickoff()