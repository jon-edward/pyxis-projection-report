from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pandas as pd

@dataclass
class InventoryItem:
    """Inventory parameters for a medication location."""
    qty_min: Optional[int]
    qty_max: Optional[int]
    has_orders: bool

    def par_level_range(self) -> Optional[tuple[int, int]]:
        """Return the par level range (min, max) for this location."""
        if self.qty_min is not None and self.qty_max is not None:
            return (self.qty_min, self.qty_max)
        return None

    def is_below_minimum(self, quantity: int) -> bool:
        """Check if quantity is below minimum threshold."""
        if self.qty_min is None:
            return False
        return quantity <= self.qty_min


@dataclass
class LocationReport:
    """Usage and inventory status for a medication at a specific Pyxis location."""
    device: str
    device_location: str
    med_id: str
    med_desc: str
    qty_removed: int
    current_qty: int
    first_activity: pd.Timestamp
    last_activity: pd.Timestamp
    removal_count: int
    refill_count: int
    inventory_item: InventoryItem
    to_date: pd.Timestamp | None
    is_critical: bool = False

    def __lt__(self, other) -> bool:
        if not isinstance(other, LocationReport):
            return NotImplemented
        return (self.med_desc.lower(), self.device_location) < (
            other.med_desc.lower(), other.device_location
        )
    
    @property
    def days_of_data(self) -> int:
        last_day = self.to_date or self.last_activity
        return max(1, (last_day - self.first_activity).days)
    
    @property
    def avg_daily_usage(self) -> float:
        return self.qty_removed / self.days_of_data
    
    @property
    def days_until_stockout(self) -> float:
        if self.avg_daily_usage > 0:
            return self.current_qty / self.avg_daily_usage
        return float("inf")
    
    @property
    def qty_to_refill(self) -> Optional[int]:
        qty_max = self.qty_max
        if qty_max is None:
            return None
        return max(0, qty_max - self.current_qty)
    
    @property
    def qty_min(self) -> Optional[int]:
        if not self.inventory_item or not self.inventory_item.qty_min:
            return None
        return self.inventory_item.qty_min
    
    @property
    def qty_max(self) -> Optional[int]:
        if not self.inventory_item or not self.inventory_item.qty_max:
            return None
        return self.inventory_item.qty_max
