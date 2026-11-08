"""Typed results produced by the deterministic engine and handed to the agents."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ShortageReason(StrEnum):
    BELOW_REORDER_POINT = "below_reorder_point"
    NOT_IN_INVENTORY = "not_in_inventory"


class Shortage(BaseModel):
    part_name: str
    current_stock: int
    reorder_threshold: int
    order_quantity: int = Field(
        description="Units needed to bring stock back up to the reorder threshold"
    )
    reason: ShortageReason


class ProductCapacity(BaseModel):
    final_product: str
    max_buildable_units: int
    limiting_parts: list[str] = Field(description="Parts that cap the buildable quantity")


class InventoryAudit(BaseModel):
    capacity: list[ProductCapacity]
    shortages: list[Shortage]


class SupplierOption(BaseModel):
    supplier_name: str
    unit_cost_usd: float
    lead_time_days: int
    order_cost_usd: float = Field(description="unit_cost_usd multiplied by the order quantity")


class SourcingOptions(BaseModel):
    part_name: str
    order_quantity: int
    cheapest: SupplierOption | None
    fastest: SupplierOption | None
    all_options: list[SupplierOption] = Field(description="Sorted by lead time, then unit cost")


class SupplyChainAnalysis(BaseModel):
    """Everything the agents need, computed before any model is called."""

    audit: InventoryAudit
    sourcing: list[SourcingOptions]
    unsourceable_parts: list[str] = Field(description="Short parts with no supplier on file")
