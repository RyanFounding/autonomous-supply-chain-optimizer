"""Streamlit front end.

The deterministic analysis runs without an API key. The agent briefing is an
optional second step that needs a Gemini key.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

from supply_chain.data import DataValidationError, SupplyChainData
from supply_chain.engine import analyze
from supply_chain.models import SupplyChainAnalysis

DATA_DIR = Path(__file__).resolve().parent / "data"

st.set_page_config(page_title="Supply Chain Disruption Analyzer", layout="wide")
st.title("Supply Chain Disruption Analyzer")
st.caption(
    "Inventory and sourcing figures are computed in Python. "
    "The optional agent briefing interprets them but never recalculates them."
)


def load_data() -> SupplyChainData:
    with st.sidebar:
        st.header("Data")
        use_sample = st.toggle("Use sample plant data", value=True)
        if use_sample:
            return SupplyChainData.sample(DATA_DIR)
        bom = st.file_uploader("Bill of materials (CSV)", type="csv")
        inventory = st.file_uploader("Inventory (CSV)", type="csv")
        suppliers = st.file_uploader("Supplier quotes (CSV)", type="csv")
    if not (bom and inventory and suppliers):
        st.info("Upload all three CSV files, or switch back to the sample data.")
        st.stop()
    return SupplyChainData.from_csv(bom, inventory, suppliers)


def render_analysis(analysis: SupplyChainAnalysis) -> None:
    st.subheader("Build capacity")
    st.dataframe(pd.DataFrame([c.model_dump() for c in analysis.audit.capacity]), hide_index=True)

    st.subheader("Shortages")
    if analysis.audit.shortages:
        st.dataframe(
            pd.DataFrame([s.model_dump() for s in analysis.audit.shortages]), hide_index=True
        )
    else:
        st.success("No parts are at or below their reorder point.")

    if analysis.sourcing:
        st.subheader("Sourcing options")
        for option in analysis.sourcing:
            st.markdown(f"**{option.part_name}**: order {option.order_quantity} units")
            st.dataframe(
                pd.DataFrame([o.model_dump() for o in option.all_options]), hide_index=True
            )
    if analysis.unsourceable_parts:
        st.warning(f"No supplier on file for: {', '.join(analysis.unsourceable_parts)}")


try:
    data = load_data()
except DataValidationError as exc:
    st.error(f"Input data is invalid: {exc}")
    st.stop()

with st.expander("Input data"):
    st.write("Inventory", data.inventory)
    st.write("Bill of materials", data.bom)
    st.write("Supplier quotes", data.suppliers)

analysis = analyze(data)
render_analysis(analysis)

st.divider()
st.subheader("Agent briefing")
api_key = os.environ.get("GEMINI_API_KEY") or st.text_input(
    "Gemini API key", type="password", help="Used for this session only; not stored."
)
if st.button("Generate executive briefing", disabled=not api_key):
    os.environ["GEMINI_API_KEY"] = api_key
    from supply_chain.crew import run_briefing  # imported lazily; CrewAI is slow to load

    with st.spinner("Agents are reviewing the analysis..."):
        try:
            st.markdown(run_briefing(analysis))
        except Exception as exc:
            if "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc):
                st.error("Gemini rate limit reached. Wait about a minute and try again.")
            else:
                st.error("The agent run failed. Check the API key and try again.")
