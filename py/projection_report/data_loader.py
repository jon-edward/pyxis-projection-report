from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from .models import InventoryItem

class DataLoadError(Exception):
    """Raised when data loading fails."""

class DataNormalizer:
    """Normalizes DataFrame column names."""

    COLUMN_MAP = {
        "Device": "device",
        "Drw|Sub Drw|Pkt": "device_location",
        "Med ID": "med_id",
        "Med Description": "med_desc",
        "Transaction Date/Time": "dt",
        "Transaction Type": "transaction_type",
        "Beg": "qty_beg",
        "End": "qty_end",
        "Min": "qty_min",
        "Max": "qty_max",
        "Active Orders": "has_orders",
    }

    @classmethod
    def normalize(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names to lowercase with underscores."""
        return df.rename(columns=cls.COLUMN_MAP)

@dataclass
class InventoryLoader:
    """Loads and processes inventory data."""

    inventory_path: Path

    def load(self) -> dict[str, InventoryItem]:
        """Load inventory items from Excel file."""
        if not self.inventory_path.exists():
            print(f"Warning: {self.inventory_path} not found. Running without inventory data.")
            return {}

        try:
            df = pd.read_excel(self.inventory_path)
            df = DataNormalizer.normalize(df)
            return self._build_inventory_items(df)
        except Exception as e:
            raise DataLoadError(f"Failed to load inventory: {e}")

    def _build_inventory_items(self, df: pd.DataFrame) -> dict[str, InventoryItem]:
        """Build inventory items from DataFrame."""
        items = {}
        for row in df.itertuples():
            items[str(row.device_location)] = InventoryItem(
                qty_min=self._safe_int(row.qty_min),
                qty_max=self._safe_int(row.qty_max),
                has_orders=row.has_orders == "Y",
            )
        return items

    @staticmethod
    def _safe_int(value: Any) -> Optional[int]:
        """Safely convert value to int."""
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

@dataclass
class UsageLoader:
    """Loads and processes usage data."""

    usage_path: Path

    def load(self) -> pd.DataFrame:
        """Load usage data from Excel file."""
        if not self.usage_path.exists():
            raise DataLoadError(f"Required file not found: {self.usage_path}")

        try:
            df = pd.read_excel(self.usage_path)
            df = DataNormalizer.normalize(df)
            df.dt = pd.to_datetime(df.dt)
            return df
        except Exception as e:
            raise DataLoadError(f"Failed to load usage data: {e}")
