from dataclasses import dataclass
from collections import defaultdict
import logging
from typing import Optional

import pandas as pd

from .config import ReportConfig
from .data_loader import UsageLoader, InventoryLoader
from .models import LocationReport, InventoryItem, TransactionType

logger = logging.getLogger(__name__)


@dataclass
class MetricsGenerator:
    """
    Generates inventory metrics from usage and inventory data.
    
    Attributes:
        config: Report configuration
        inventory_loader: Loader for inventory data
        usage_loader: Loader for usage data
    """
    config: ReportConfig
    inventory_loader: InventoryLoader
    usage_loader: UsageLoader

    def metrics(self) -> dict[str, list[LocationReport]]:
        """
        Generate location reports for all devices.
        
        Returns:
            Dictionary mapping device names to lists of LocationReport objects
            
        Examples:
            >>> generator = MetricsGenerator(config, inv_loader, usage_loader)
            >>> reports = generator.metrics()
            >>> len(reports['PYXIS-01'])
            15
        """
        inventory_items = self.inventory_loader.load()
        usage_df = self.usage_loader.load()

        device_reports = defaultdict(list)
        id_to_desc = self._build_id_map(usage_df)
        
        devices = usage_df.device.unique()
        logger.info(f"Generating metrics for {len(devices)} devices")

        for device in devices:
            if not self.config.should_include_device(device):
                logger.debug(f"Skipping device: {device}")
                continue

            device_df = usage_df[usage_df.device == device].sort_values(by=["med_desc"])
            
            for (device_location, med_id), group in device_df.groupby(["device_location", "med_id"]):
                med_id = str(med_id)
                report = self._create_location_report(
                    device, device_location, med_id, group, 
                    id_to_desc, inventory_items
                )
                
                # Apply filters
                if report and self._should_include_report(report):
                    device_reports[device].append(report)

        # Remove empty devices
        result = {k: v for k, v in device_reports.items() if v}
        logger.info(f"Generated reports for {len(result)} devices with {sum(len(v) for v in result.values())} total items")
        return result
    
    def _build_id_map(self, df: pd.DataFrame) -> dict[str, str]:
        """
        Build medication ID to description mapping.
        
        Args:
            df: Usage DataFrame
            
        Returns:
            Dictionary mapping medication IDs to descriptions
        """
        return {str(row.med_id): str(row.med_desc) for row in df.itertuples()}
    
    def _should_include_report(self, report: LocationReport) -> bool:
        """
        Determine if a report should be included based on filters.
        
        Args:
            report: LocationReport to evaluate
            
        Returns:
            True if report passes all filter criteria
        """
        if not self.config.include_min_zero and report.inventory_item.qty_min == 0:
            return False
        if not self.config.include_unordered and not report.inventory_item.has_orders:
            return False
        if self.config.only_critical and not report.is_critical:
            return False
        return not (report.days_until_stockout > self.config.max_days)
    
    def _create_location_report(
        self,
        device: str,
        device_location: str,
        med_id: str,
        group: pd.DataFrame,
        id_to_desc: dict[str, str],
        inventory_items: dict[str, InventoryItem]
    ) -> Optional[LocationReport]:
        """
        Create a location report from grouped transaction data.
        
        Args:
            device: Device name
            device_location: Location within device
            med_id: Medication identifier
            group: DataFrame of transactions for this location/medication
            id_to_desc: Mapping of medication IDs to descriptions
            inventory_items: Inventory configuration by location
            
        Returns:
            LocationReport object or None if location not in inventory
        """
        group = group.sort_values(by=["dt"]).reset_index(drop=True)
        
        qty_removed = self._sum_positive(group.qty_beg - group.qty_end)

        if device_location not in inventory_items:
            logger.warning(f"Location {device_location} not found in inventory data")
            return None
        
        report = LocationReport(
            device=device,
            device_location=device_location,
            med_id=med_id,
            med_desc=str(id_to_desc[med_id]),
            qty_removed=qty_removed,
            current_qty=int(group.qty_end.iloc[-1]),
            first_activity=group.dt.iloc[0],
            last_activity=group.dt.iloc[-1],
            removal_count=len(group[group.transaction_type == TransactionType.REMOVE.value]),
            refill_count=len(group[group.transaction_type == TransactionType.REFILL.value]),
            to_date=pd.Timestamp.now(),
            inventory_item=inventory_items[device_location],
        )

        report.is_critical = report.days_until_stockout < self.config.critical_threshold
        
        return report
    
    @staticmethod
    def _sum_positive(values) -> int:
        """
        Sum only positive values from a series.
        
        Args:
            values: Pandas Series or iterable of numeric values
            
        Returns:
            Sum of all positive values
        """
        return sum(v for v in values if v >= 0)