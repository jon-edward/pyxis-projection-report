from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
import logging

import pandas as pd

from .models import InventoryItem, TransactionType

logger = logging.getLogger(__name__)


class DataLoadError(Exception):
    """
    Raised when data loading fails.
    
    Attributes:
        file_path: Path to the file that failed to load
        original_error: The underlying exception that caused the failure
    """
    
    def __init__(
        self, 
        message: str, 
        file_path: Optional[Path] = None, 
        original_error: Optional[Exception] = None
    ):
        self.file_path = file_path
        self.original_error = original_error
        super().__init__(message)


class DataNormalizer:
    """Normalizes DataFrame column names to standard format."""

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
        """
        Normalize column names to lowercase with underscores.
        
        Args:
            df: DataFrame with original column names
            
        Returns:
            DataFrame with normalized column names
        """
        return df.rename(columns=cls.COLUMN_MAP)


@dataclass
class InventoryLoader:
    """
    Loads and processes inventory data from Excel files.
    
    Attributes:
        inventory_path: Path to the inventory Excel file
        conflicting_locations: Locations that appear more than once with
            different values; set by load(). The last row is used.
    """

    inventory_path: Path
    conflicting_locations: list[str] = field(default_factory=list, init=False)

    def load(self) -> dict[str, InventoryItem]:
        """
        Load inventory items from Excel file.
        
        Returns:
            Dictionary mapping device_location to InventoryItem
            
        Raises:
            DataLoadError: If file loading or processing fails
        """
        if not self.inventory_path.exists():
            logger.warning(f"{self.inventory_path} not found. Running without inventory data.")
            return {}

        try:
            logger.info(f"Loading inventory from {self.inventory_path}")
            df = pd.read_excel(self.inventory_path)
            df = DataNormalizer.normalize(df)
            self._validate_inventory_data(df)
            items = self._build_inventory_items(df)
            logger.info(f"Loaded {len(items)} inventory items")
            return items
        except Exception as e:
            raise DataLoadError(
                f"Failed to load inventory: {e}",
                file_path=self.inventory_path,
                original_error=e
            )

    def _validate_inventory_data(self, df: pd.DataFrame) -> None:
        """
        Validate loaded inventory data has required columns.
        
        Args:
            df: DataFrame to validate
            
        Raises:
            DataLoadError: If validation fails
        """
        required_cols = ['device_location', 'qty_min', 'qty_max', 'has_orders']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise DataLoadError(
                f"Missing required columns: {missing}",
                file_path=self.inventory_path
            )
        
        if df.empty:
            logger.warning("Inventory data is empty")

    def _build_inventory_items(self, df: pd.DataFrame) -> dict[str, InventoryItem]:
        """
        Build inventory items from DataFrame.
        
        Args:
            df: Normalized inventory DataFrame
            
        Returns:
            Dictionary mapping device_location to InventoryItem
        """
        items = {}
        conflicts = set()
        for row in df.itertuples():
            key = str(row.device_location)
            item = InventoryItem(
                qty_min=self._safe_int(row.qty_min),
                qty_max=self._safe_int(row.qty_max),
                has_orders=row.has_orders == "Y",
            )
            # Items are keyed by location alone, so a repeated location with
            # different values would silently overwrite the earlier row.
            if key in items and items[key] != item:
                conflicts.add(key)
            items[key] = item
        self.conflicting_locations = sorted(conflicts)
        return items

    @staticmethod
    def _safe_int(value: Any) -> Optional[int]:
        """
        Safely convert value to int.
        
        Args:
            value: Value to convert
            
        Returns:
            Integer value or None if conversion fails
        """
        try:
            return int(value)
        except (ValueError, TypeError):
            return None


@dataclass
class UsageLoader:
    """
    Loads and processes usage data from Excel files.
    
    Attributes:
        usage_path: Path to the usage Excel file
    """

    usage_path: Path

    def load(self) -> pd.DataFrame:
        """
        Load usage data from Excel file.
        
        Returns:
            DataFrame with normalized usage data
            
        Raises:
            DataLoadError: If file loading or processing fails
        """
        if not self.usage_path.exists():
            raise DataLoadError(
                f"Required file not found: {self.usage_path}",
                file_path=self.usage_path
            )

        try:
            logger.info(f"Loading usage data from {self.usage_path}")
            df = pd.read_excel(self.usage_path)
            df = DataNormalizer.normalize(df)
            self._validate_usage_data(df)
            df.dt = pd.to_datetime(df.dt)
            df["transaction_type"] = self._normalize_transaction_types(df.transaction_type)
            self._validate_removals(df)
            logger.info(f"Loaded {len(df)} usage records for {df.device.nunique()} devices")
            return df
        except Exception as e:
            raise DataLoadError(
                f"Failed to load usage data: {e}",
                file_path=self.usage_path,
                original_error=e
            )

    @staticmethod
    def _normalize_transaction_types(types: pd.Series) -> pd.Series:
        """Trim whitespace and match known types ("remove" -> "Remove")."""
        known = {t.value.lower(): t.value for t in TransactionType}
        return types.astype(str).str.strip().map(lambda s: known.get(s.lower(), s))

    def _validate_removals(self, df: pd.DataFrame) -> None:
        """
        Usage is measured from Remove transactions, so there must be some.
        Without any, the file most likely uses other labels, and every item
        would silently show no usage.

        Raises:
            DataLoadError: If there are no Remove transactions
        """
        removal = TransactionType.REMOVE.value
        if not (df.transaction_type == removal).any():
            found = sorted(df.transaction_type.unique())
            raise DataLoadError(
                f"No '{removal}' transactions found. Transaction types in file: {found}",
                file_path=self.usage_path
            )

    def _validate_usage_data(self, df: pd.DataFrame) -> None:
        """
        Validate loaded usage data has required columns and data.
        
        Args:
            df: DataFrame to validate
            
        Raises:
            DataLoadError: If validation fails
        """
        required_cols = [
            'device', 'device_location', 'med_id', 'med_desc',
            'dt', 'transaction_type', 'qty_beg', 'qty_end'
        ]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise DataLoadError(
                f"Missing required columns: {missing}",
                file_path=self.usage_path
            )
        
        if df.empty:
            raise DataLoadError(
                "Usage data is empty",
                file_path=self.usage_path
            )