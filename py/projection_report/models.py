from dataclasses import dataclass
from typing import Optional
from functools import cached_property
from enum import Enum

import pandas as pd


class TransactionType(Enum):
    """Types of medication transactions."""
    REMOVE = "Remove"
    REFILL = "Refill"


@dataclass
class InventoryItem:
    """
    Inventory parameters for a medication location.
    
    Attributes:
        qty_min: Minimum quantity threshold (par level)
        qty_max: Maximum quantity threshold (par level)
        has_orders: Whether location has active orders
    """
    qty_min: Optional[int]
    qty_max: Optional[int]
    has_orders: bool

    def par_level_range(self) -> Optional[tuple[int, int]]:
        """
        Return the par level range (min, max) for this location.
        
        Returns:
            Tuple of (min, max) quantities or None if either is missing
        """
        if self.qty_min is not None and self.qty_max is not None:
            return (self.qty_min, self.qty_max)
        return None

    def is_below_minimum(self, quantity: int) -> bool:
        """
        Check if quantity is below minimum threshold.
        
        Args:
            quantity: Current quantity to check
            
        Returns:
            True if quantity is at or below minimum, False otherwise
        """
        if self.qty_min is None:
            return False
        return quantity <= self.qty_min


@dataclass
class LocationReport:
    """
    Usage and inventory status for a medication at a specific Pyxis location.
    
    Attributes:
        device: Name of the Pyxis device
        device_location: Specific drawer/pocket location
        med_id: Medication identifier
        med_desc: Medication description
        qty_removed: Total quantity removed during the period
        current_qty: Current quantity in location
        first_activity: Timestamp of first transaction
        last_activity: Timestamp of last transaction
        removal_count: Number of removal transactions
        refill_count: Number of refill transactions
        inventory_item: Inventory configuration for this location
        to_date: End date for calculations (defaults to now)
        is_critical: Whether item is critically low
    """
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
    to_date: Optional[pd.Timestamp]
    is_critical: bool = False

    def __lt__(self, other) -> bool:
        """
        Compare reports for sorting by medication description and location.
        
        Args:
            other: Another LocationReport to compare against
            
        Returns:
            True if this report should sort before the other
        """
        if not isinstance(other, LocationReport):
            return NotImplemented
        return (self.med_desc.lower(), self.device_location) < (
            other.med_desc.lower(), other.device_location
        )
    
    @cached_property
    def days_of_data(self) -> int:
        """
        Calculate the number of days covered by the data.
        
        Returns:
            Number of days between first and last activity (minimum 1)
            
        Raises:
            ValueError: If date range is invalid
        """
        last_day = self.to_date or self.last_activity
        days = (last_day - self.first_activity).days
        
        if days < 0:
            raise ValueError(
                f"Invalid date range: last activity ({last_day}) before "
                f"first activity ({self.first_activity})"
            )
        
        return max(1, days)
    
    @cached_property
    def avg_daily_usage(self) -> float:
        """
        Calculate average daily usage rate.
        
        Returns:
            Average number of units removed per day
        """
        return self.qty_removed / self.days_of_data
    
    @cached_property
    def days_until_stockout(self) -> float:
        """
        Estimate days until stockout based on current usage rate.
        
        Returns:
            Estimated days until quantity reaches zero (inf if no usage)
        """
        if self.avg_daily_usage > 0:
            return self.current_qty / self.avg_daily_usage
        return float("inf")
    
    @property
    def qty_to_refill(self) -> Optional[int]:
        """
        Calculate quantity needed to reach maximum par level.
        
        Returns:
            Quantity to add to reach max, or None if max is not set
        """
        qty_max = self.qty_max
        if qty_max is None:
            return None
        return max(0, qty_max - self.current_qty)
    
    @property
    def qty_min(self) -> Optional[int]:
        """
        Get minimum par level for this location.
        
        Returns:
            Minimum quantity threshold or None if not set
        """
        if not self.inventory_item or not self.inventory_item.qty_min:
            return None
        return self.inventory_item.qty_min
    
    @property
    def qty_max(self) -> Optional[int]:
        """
        Get maximum par level for this location.
        
        Returns:
            Maximum quantity threshold or None if not set
        """
        if not self.inventory_item or not self.inventory_item.qty_max:
            return None
        return self.inventory_item.qty_max