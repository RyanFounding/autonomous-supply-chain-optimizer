"""Deterministic inventory and sourcing calculations.

All arithmetic lives here. The agents receive these results as facts and are
never asked to compute a number themselves.
"""

from __future__ import annotations

import pandas as pd

from supply_chain.data import SupplyChainData
from supply_chain.models import (
    InventoryAudit,
    ProductCapacity,
    Shortage,
    ShortageReason,
    SourcingOptions,
    SupplierOption,
    SupplyChainAnalysis,
)


def calculate_capacity(data: SupplyChainData) -> list[ProductCapacity]:
    """Maximum buildable units per final product, limited by its scarcest part."""
    merged = data.bom.merge(
        data.inventory[["part_name", "current_stock"]], on="part_name", how="left"
    )
    merged["current_stock"] = merged["current_stock"].fillna(0)
    merged["buildable"] = (merged["current_stock"] // merged["quantity_required_per_unit"]).astype(
        int
    )

    capacity: list[ProductCapacity] = []
    for product, parts in merged.groupby("final_product", sort=True):
        max_units = int(parts["buildable"].min())
        limiting = sorted(parts.loc[parts["buildable"] == max_units, "part_name"])
        capacity.append(
            ProductCapacity(
                final_product=str(product),
                max_buildable_units=max_units,
                limiting_parts=limiting,
            )
        )
    return capacity


def find_shortages(data: SupplyChainData) -> list[Shortage]:
    """Parts used in the BOM that are at or below their reorder point, or not stocked at all."""
    bom_parts = pd.DataFrame({"part_name": data.bom["part_name"].drop_duplicates()})
    merged = bom_parts.merge(data.inventory, on="part_name", how="left")

    shortages: list[Shortage] = []
    for row in merged.to_dict("records"):
        part_name = str(row["part_name"])
        if pd.isna(row["current_stock"]):
            needed = int(
                data.bom.loc[data.bom["part_name"] == part_name, "quantity_required_per_unit"].max()
            )
            shortages.append(
                Shortage(
                    part_name=part_name,
                    current_stock=0,
                    reorder_threshold=0,
                    order_quantity=needed,
                    reason=ShortageReason.NOT_IN_INVENTORY,
                )
            )
        else:
            stock = int(row["current_stock"])
            threshold = int(row["reorder_threshold"])
            if stock > threshold:
                continue
            shortages.append(
                Shortage(
                    part_name=part_name,
                    current_stock=stock,
                    reorder_threshold=threshold,
                    order_quantity=threshold - stock,
                    reason=ShortageReason.BELOW_REORDER_POINT,
                )
            )
    return shortages


def sourcing_options(shortage: Shortage, suppliers: pd.DataFrame) -> SourcingOptions:
    quotes = suppliers[suppliers["part_name"] == shortage.part_name].sort_values(
        ["lead_time_days", "unit_cost_usd", "supplier_name"]
    )
    options = [
        SupplierOption(
            supplier_name=str(q["supplier_name"]),
            unit_cost_usd=float(q["unit_cost_usd"]),
            lead_time_days=int(q["lead_time_days"]),
            order_cost_usd=round(float(q["unit_cost_usd"]) * shortage.order_quantity, 2),
        )
        for q in quotes.to_dict("records")
    ]
    return SourcingOptions(
        part_name=shortage.part_name,
        order_quantity=shortage.order_quantity,
        cheapest=min(options, key=lambda o: (o.unit_cost_usd, o.lead_time_days), default=None),
        fastest=options[0] if options else None,
        all_options=options,
    )


def analyze(data: SupplyChainData) -> SupplyChainAnalysis:
    shortages = find_shortages(data)
    sourcing = [sourcing_options(s, data.suppliers) for s in shortages]
    return SupplyChainAnalysis(
        audit=InventoryAudit(capacity=calculate_capacity(data), shortages=shortages),
        sourcing=[s for s in sourcing if s.all_options],
        unsourceable_parts=[s.part_name for s in sourcing if not s.all_options],
    )
