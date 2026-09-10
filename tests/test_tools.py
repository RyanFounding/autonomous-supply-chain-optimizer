import pandas as pd
from src.tools import SupplyChainEngine

def test_calculate_shortages_accuracy():
    # 1. ARRANGE: Set up a fake factory scenario
    bom_df = pd.DataFrame({
        "part_name": ["Titanium Impeller", "Ceramic Bearings"],
        "quantity_required_per_unit": [1, 4]
    })
    
    inv_df = pd.DataFrame({
        "part_name": ["Titanium Impeller", "Ceramic Bearings"],
        "current_stock": [50, 10],
        "reorder_threshold": [20, 100]
    })

    # 2. ACT: Run our math engine
    result = SupplyChainEngine.calculate_shortages(bom_df, inv_df)

    # 3. ASSERT: Prove the logic is flawless
    # 10 bearings available / 4 required per pump = 2 pumps max capacity
    assert result["max_build_capacity"] == 2 
    
    # We should only have 1 critical shortage (Bearings)
    assert len(result["critical_shortages"]) == 1
    
    # Prove the deficit math is exactly 90
    shortage = result["critical_shortages"][0]
    assert shortage["part_name"] == "Ceramic Bearings"
    assert shortage["deficit"] == 90