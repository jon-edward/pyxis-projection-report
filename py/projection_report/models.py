from dataclasses import dataclass, field
from typing import Optional
from functools import cached_property
from enum import Enum

import pandas as pd


class TransactionType(Enum):
    """Types of medication transactions."""
    REMOVE = "Remove"
    REFILL = "Refill"


# Fewer removals than this in the usage window is flagged as "low data".
MIN_REMOVALS_FOR_CONFIDENCE = 3

# Shown at the end of the PDF and on the Excel summary sheet.
USAGE_NOTES = [
    "Average usage = units removed during the usage window / days in the window",
    "Days remaining = current quantity / average daily usage; items with no usage have no projected stockout",
    f"Low data = fewer than {MIN_REMOVALS_FOR_CONFIDENCE} removals in the window; treat the estimate with caution",
    "No activity = in the inventory file but with no transactions in the usage file; its current quantity is unknown",
]


@dataclass
class ReportContext:
    """
    Facts about the data behind a report, shown in its summary.

    Attributes:
        usage_window: (start, end) of the usage data, shared by all locations
        warnings: Data problems that change what the report shows
    """
    usage_window: Optional[tuple[pd.Timestamp, pd.Timestamp]] = None
    warnings: list[str] = field(default_factory=list)

    def usage_window_text(self, date_format: str = "%Y-%m-%d") -> Optional[str]:
        """Usage window as text, e.g. "2026-10-04 to 2026-11-03 (30.0 days)"."""
        if self.usage_window is None:
            return None
        start, end = self.usage_window
        days = (end - start).total_seconds() / 86400
        return f"{start.strftime(date_format)} to {end.strftime(date_format)} ({days:.1f} days)"


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
class InventoryEntry:
    """One inventory row with the device and medication it belongs to."""
    device: str
    device_location: str
    med_id: str
    med_desc: Optional[str]
    item: InventoryItem


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
        current_qty: Current quantity in location (None if unknown because
            the location has no transactions)
        first_activity: Timestamp of first transaction (None if no activity)
        last_activity: Timestamp of last transaction (None if no activity)
        removal_count: Number of removal transactions
        refill_count: Number of refill transactions
        inventory_item: Inventory configuration for this location
        to_date: End date for calculations when no usage window is set
        is_critical: Whether item is critically low
        window_start: Start of the usage window shared by all locations
        window_end: End of the usage window shared by all locations
    """
    device: str
    device_location: str
    med_id: str
    med_desc: str
    qty_removed: int
    current_qty: Optional[int]
    first_activity: Optional[pd.Timestamp]
    last_activity: Optional[pd.Timestamp]
    removal_count: int
    refill_count: int
    inventory_item: InventoryItem
    to_date: Optional[pd.Timestamp]
    is_critical: bool = False
    window_start: Optional[pd.Timestamp] = None
    window_end: Optional[pd.Timestamp] = None

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
    
    @property
    def has_activity(self) -> bool:
        """False for an inventory location with no transactions in the usage file."""
        return self.first_activity is not None

    @cached_property
    def days_of_data(self) -> float:
        """
        Length of the usage window in days (minimum 1).

        Uses the window shared by all locations. Without one, falls back to
        this location's first activity through to_date (or last activity).

        Returns:
            Days in the window, including fractions of a day

        Raises:
            ValueError: If the window ends before it starts
        """
        start = self.window_start if self.window_start is not None else self.first_activity
        end = self.window_end if self.window_end is not None else (self.to_date or self.last_activity)
        if start is None or end is None:
            return 1.0
        days = (end - start) / pd.Timedelta(days=1)

        if days < 0:
            raise ValueError(f"Invalid date range: window ends ({end}) before it starts ({start})")

        return max(1.0, days)

    @cached_property
    def avg_daily_usage(self) -> float:
        """
        Calculate average daily usage rate.

        Returns:
            Average number of units removed per day over the usage window
        """
        return self.qty_removed / self.days_of_data

    @property
    def low_data(self) -> bool:
        """True when there are too few removals for a reliable usage rate."""
        return self.removal_count < MIN_REMOVALS_FOR_CONFIDENCE
    
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
            Quantity to add to reach max, or None if max or the current
            quantity is not known
        """
        qty_max = self.qty_max
        if qty_max is None or self.current_qty is None:
            return None
        return max(0, qty_max - self.current_qty)
    
    @property
    def qty_min(self) -> Optional[int]:
        """
        Get minimum par level for this location.
        
        Returns:
            Minimum quantity threshold or None if not set
        """
        if self.inventory_item is None:
            return None
        return self.inventory_item.qty_min
    
    @property
    def qty_max(self) -> Optional[int]:
        """
        Get maximum par level for this location.
        
        Returns:
            Maximum quantity threshold or None if not set
        """
        if self.inventory_item is None:
            return None
        return self.inventory_item.qty_max