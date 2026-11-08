"""Load and validate the three input tables."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import IO

import pandas as pd

BOM_COLUMNS = ("final_product", "part_name", "quantity_required_per_unit")
INVENTORY_COLUMNS = ("part_name", "current_stock", "reorder_threshold")
SUPPLIER_COLUMNS = ("part_name", "supplier_name", "unit_cost_usd", "lead_time_days")

CsvSource = str | Path | IO[bytes] | IO[str]


class DataValidationError(ValueError):
    pass


def _require_columns(df: pd.DataFrame, columns: tuple[str, ...], table: str) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise DataValidationError(f"{table} is missing columns: {', '.join(missing)}")


def _require_non_negative(df: pd.DataFrame, columns: tuple[str, ...], table: str) -> None:
    for column in columns:
        values = pd.to_numeric(df[column], errors="coerce")
        if values.isna().any():
            raise DataValidationError(f"{table}.{column} contains non-numeric or empty values")
        if (values < 0).any():
            raise DataValidationError(f"{table}.{column} contains negative values")
        df[column] = values


@dataclass(frozen=True)
class SupplyChainData:
    bom: pd.DataFrame
    inventory: pd.DataFrame
    suppliers: pd.DataFrame

    def __post_init__(self) -> None:
        _require_columns(self.bom, BOM_COLUMNS, "BOM")
        _require_columns(self.inventory, INVENTORY_COLUMNS, "Inventory")
        _require_columns(self.suppliers, SUPPLIER_COLUMNS, "Suppliers")

        _require_non_negative(self.bom, ("quantity_required_per_unit",), "BOM")
        if (self.bom["quantity_required_per_unit"] == 0).any():
            raise DataValidationError("BOM.quantity_required_per_unit must be greater than zero")
        _require_non_negative(self.inventory, ("current_stock", "reorder_threshold"), "Inventory")
        _require_non_negative(self.suppliers, ("unit_cost_usd", "lead_time_days"), "Suppliers")

        duplicated = self.inventory["part_name"][self.inventory["part_name"].duplicated()]
        if not duplicated.empty:
            raise DataValidationError(
                f"Inventory lists these parts more than once: {', '.join(sorted(set(duplicated)))}"
            )

    @classmethod
    def from_csv(
        cls, bom: CsvSource, inventory: CsvSource, suppliers: CsvSource
    ) -> SupplyChainData:
        return cls(
            bom=pd.read_csv(bom),
            inventory=pd.read_csv(inventory),
            suppliers=pd.read_csv(suppliers),
        )

    @classmethod
    def sample(cls, data_dir: Path) -> SupplyChainData:
        """Load the sample plant data from ``data_dir``.

        The caller supplies the directory because the data ships with the repository, not
        with the installed package, so it cannot be located reliably from this module.
        """
        return cls.from_csv(
            data_dir / "sample_bom.csv",
            data_dir / "sample_inventory.csv",
            data_dir / "sample_suppliers.csv",
        )
