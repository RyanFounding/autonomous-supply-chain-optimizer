import streamlit as st
import pandas as pd
import os
from src.crew import run_supply_chain_crew

st.set_page_config(page_title="Supply Chain AI", layout="wide")
st.title("🏭 Multi-Agent Supply Chain Optimizer")

# Security check for API Key
api_key = st.text_input("Enter your Gemini API Key:", type="password")
if api_key:
    os.environ["GEMINI_API_KEY"] = api_key

if st.button("Load Data & Run Simulation") and api_key:
    with st.spinner("Loading Enterprise Datasets..."):
        # Load local CSVs
        df_bom = pd.read_csv("data/sample_bom.csv")
        df_inv = pd.read_csv("data/sample_inventory.csv")
        df_sup = pd.read_csv("data/sample_suppliers.csv")

        # Show the data to the user
        st.write("### Inventory Status", df_inv)

        # Convert to JSON strings for the AI tools
        bom_json = df_bom.to_json(orient="records")
        inv_json = df_inv.to_json(orient="records")
        sup_json = df_sup.to_json(orient="records")

    with st.spinner("Agents are analyzing disruptions and executing tools... (This takes a moment to respect rate limits)"):
        try:
            # Kick off the backend CrewAI logic
            result = run_supply_chain_crew(bom_json, inv_json, sup_json)
            
            st.success("✅ Protocol Complete")
            st.markdown("### Executive Summary")
            st.write(result.raw)
            
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                st.error("⚠️ Google API Free Tier Limit Reached. The server requires exactly 60 seconds to reset. Please wait one minute and click run again.")
            else:
                st.error(f"⚠️ An unexpected system error occurred: {error_msg}")