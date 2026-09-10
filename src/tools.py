import pandas as pd
from crewai.tools import tool
import json

class SupplyChainEngine:
    @staticmethod
    def calculate_shortages(bom_df: pd.DataFrame, inv_df: pd.DataFrame) -> dict:
        merged = pd.merge(bom_df, inv_df, on="part_name", how="left")
        merged["current_stock"] = merged["current_stock"].fillna(0)
        
        # Exact math: stock / required
        merged["possible_units"] = merged["current_stock"] // merged["quantity_required_per_unit"]
        max_build_capacity = int(merged["possible_units"].min())
        
        shortages = []
        for _, row in merged.iterrows():
            if row["current_stock"] <= row["reorder_threshold"]:
                shortages.append({
                    "part_name": row["part_name"],
                    "current_stock": int(row["current_stock"]),
                    "deficit": int(row["reorder_threshold"] - row["current_stock"])
                })
                
        return {"max_build_capacity": max_build_capacity, "critical_shortages": shortages}

    @staticmethod
    def rank_suppliers(shortage_parts: list, suppliers_df: pd.DataFrame) -> list:
        matches = suppliers_df[suppliers_df["part_name"].isin(shortage_parts)].copy()
        if matches.empty: return []
        
        results = []
        for part in shortage_parts:
            part_suppliers = matches[matches["part_name"] == part].to_dict(orient="records")
            results.append({"part_name": part, "available_options": part_suppliers})
        return results

# Expose these to CrewAI
@tool("BOM Shortage Auditor")
def audit_bom_inventory_tool(bom_json: str, inv_json: str) -> str:
    """Calculates exact factory build capacity and itemized stock deficits from JSON data."""
    # We parse the JSON string into a Python list first, then load into Pandas
    bom_df = pd.DataFrame(json.loads(bom_json))
    inv_df = pd.DataFrame(json.loads(inv_json))
    
    result = SupplyChainEngine.calculate_shortages(bom_df, inv_df)
    return json.dumps(result, indent=2)

@tool("Supplier Procurement Matcher")
def match_suppliers_tool(shortage_parts_json: str, suppliers_json: str) -> str:
    """Finds available supplier quotes and lead times for needed parts."""
    parts = json.loads(shortage_parts_json)
    sup_df = pd.DataFrame(json.loads(suppliers_json))
    
    result = SupplyChainEngine.rank_suppliers(parts, sup_df)
    return json.dumps(result, indent=2)