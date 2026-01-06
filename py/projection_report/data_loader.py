from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
import logging

import pandas as pd

from .models import InventoryItem

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
    """

    inventory_path: Path

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
        for row in df.itertuples():
            items[str(row.device_location)] = InventoryItem(
                qty_min=self._safe_int(row.qty_min),
                qty_max=self._safe_int(row.qty_max),
                has_orders=row.has_orders == "Y",
            )
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
            logger.info(f"Loaded {len(df)} usage records for {df.device.nunique()} devices")
            return df
        except Exception as e:
            raise DataLoadError(
                f"Failed to load usage data: {e}",
                file_path=self.usage_path,
                original_error=e
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