from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from supply_chain.data import DataValidationError, SupplyChainData
from supply_chain.engine import analyze, calculate_capacity, find_shortages
from supply_chain.models import ShortageReason

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "data"


def make_data(
    bom: list[tuple[str, str, int]],
    inventory: list[tuple[str, int, int]],
    suppliers: list[tuple[str, str, float, int]] | None = None,
) -> SupplyChainData:
    return SupplyChainData(
        bom=pd.DataFrame(bom, columns=["final_product", "part_name", "quantity_required_per_unit"]),
        inventory=pd.DataFrame(
            inventory, columns=["part_name", "current_stock", "reorder_threshold"]
        ),
        suppliers=pd.DataFrame(
            suppliers or [],
            columns=["part_name", "supplier_name", "unit_cost_usd", "lead_time_days"],
        ),
    )


PUMP = make_data(
    bom=[("Pump", "Impeller", 1), ("Pump", "Bearing", 4)],
    inventory=[("Impeller", 50, 20), ("Bearing", 10, 100)],
    suppliers=[
        ("Bearing", "GlobalTech", 15.0, 14),
        ("Bearing", "Precision", 25.0, 3),
    ],
)


def test_capacity_is_limited_by_scarcest_part() -> None:
    [pump] = calculate_capacity(PUMP)

    assert pump.max_buildable_units == 2  # 10 bearings / 4 per pump
    assert pump.limiting_parts == ["Bearing"]


def test_shortage_order_quantity_restores_reorder_point() -> None:
    [shortage] = find_shortages(PUMP)

    assert shortage.part_name == "Bearing"
    assert shortage.order_quantity == 90
    assert shortage.reason is ShortageReason.BELOW_REORDER_POINT


def test_part_missing_from_inventory_is_reported() -> None:
    data = make_data(
        bom=[("Pump", "Impeller", 1), ("Pump", "Seal", 2)],
        inventory=[("Impeller", 50, 20)],
    )

    shortages = find_shortages(data)
    [capacity] = calculate_capacity(data)

    assert capacity.max_buildable_units == 0
    assert capacity.limiting_parts == ["Seal"]
    assert [(s.part_name, s.reason, s.order_quantity) for s in shortages] == [
        ("Seal", ShortageReason.NOT_IN_INVENTORY, 2)
    ]


def test_capacity_is_calculated_per_product() -> None:
    data = make_data(
        bom=[("Pump", "Shaft", 1), ("Valve", "Shaft", 2), ("Valve", "Body", 1)],
        inventory=[("Shaft", 10, 0), ("Body", 100, 0)],
    )

    capacity = {c.final_product: c.max_buildable_units for c in calculate_capacity(data)}

    assert capacity == {"Pump": 10, "Valve": 5}


def test_shared_part_is_reported_once() -> None:
    data = make_data(
        bom=[("Pump", "Shaft", 1), ("Valve", "Shaft", 2)],
        inventory=[("Shaft", 5, 10)],
    )

    assert [s.part_name for s in find_shortages(data)] == ["Shaft"]


def test_sourcing_identifies_cheapest_and_fastest() -> None:
    [option] = analyze(PUMP).sourcing

    assert option.cheapest is not None and option.cheapest.supplier_name == "GlobalTech"
    assert option.fastest is not None and option.fastest.supplier_name == "Precision"
    assert option.cheapest.order_cost_usd == 1350.0  # 90 x $15
    assert [o.supplier_name for o in option.all_options] == ["Precision", "GlobalTech"]


def test_parts_without_suppliers_are_listed_separately() -> None:
    data = make_data(bom=[("Pump", "Seal", 1)], inventory=[("Seal", 0, 5)])

    analysis = analyze(data)

    assert analysis.sourcing == []
    assert analysis.unsourceable_parts == ["Seal"]


def test_sample_data_produces_expected_analysis() -> None:
    analysis = analyze(SupplyChainData.sample(SAMPLE_DIR))

    [pump] = analysis.audit.capacity
    assert pump.final_product == "Centrifugal Pump"
    assert pump.max_buildable_units == 2
    assert [s.part_name for s in analysis.audit.shortages] == ["Ceramic Bearings"]


@pytest.mark.parametrize(
    ("bom", "inventory", "message"),
    [
        ([("Pump", "Shaft", 0)], [("Shaft", 1, 0)], "greater than zero"),
        ([("Pump", "Shaft", 1)], [("Shaft", -1, 0)], "negative"),
        ([("Pump", "Shaft", 1)], [("Shaft", 1, 0), ("Shaft", 2, 0)], "more than once"),
    ],
)
def test_invalid_input_is_rejected(
    bom: list[tuple[str, str, int]], inventory: list[tuple[str, int, int]], message: str
) -> None:
    with pytest.raises(DataValidationError, match=message):
        make_data(bom=bom, inventory=inventory)


def test_missing_columns_are_reported() -> None:
    with pytest.raises(DataValidationError, match="missing columns: reorder_threshold"):
        SupplyChainData(
            bom=pd.DataFrame(columns=["final_product", "part_name", "quantity_required_per_unit"]),
            inventory=pd.DataFrame(columns=["part_name", "current_stock"]),
            suppliers=pd.DataFrame(
                columns=["part_name", "supplier_name", "unit_cost_usd", "lead_time_days"]
            ),
        )
