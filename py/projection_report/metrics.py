from dataclasses import dataclass
from collections import defaultdict

import pandas as pd

from .config import ReportConfig
from .data_loader import UsageLoader, InventoryLoader
from .models import LocationReport, InventoryItem


@dataclass
class MetricsGenerator:
    config: ReportConfig
    inventory_loader: InventoryLoader
    usage_loader: UsageLoader

    def metrics(self) -> dict[str, list[LocationReport]]:
        inventory_items = self.inventory_loader.load()
        usage_df = self.usage_loader.load()

        device_reports = defaultdict(list)
        id_to_desc = self._build_id_map(usage_df)

        for device in usage_df.device.unique():
            if not self.config.should_include_device(device):
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
        return {k: v for k, v in device_reports.items() if v}
    
    def _build_id_map(self, df: pd.DataFrame) -> dict[str, str]:
        """Build medication ID to description mapping."""
        return {str(row.med_id): str(row.med_desc) for row in df.itertuples()}
    
    def _should_include_report(self, report: LocationReport) -> bool:
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
    ) -> LocationReport | None:
        """Create a location report from grouped data."""
        group = group.sort_values(by=["dt"]).reset_index(drop=True)
        
        qty_removed = self._sum_positive(group.qty_beg - group.qty_end)

        if device_location not in inventory_items:
            return
        
        report = LocationReport(
            device=device,
            device_location=device_location,
            med_id=med_id,
            med_desc=str(id_to_desc[med_id]),
            qty_removed=qty_removed,
            current_qty=int(group.qty_end.iloc[-1]),
            first_activity=group.dt.iloc[0],
            last_activity=group.dt.iloc[-1],
            removal_count=len(group[group.transaction_type == "Remove"]),
            refill_count=len(group[group.transaction_type == "Refill"]),
            to_date=pd.Timestamp.now(),
            inventory_item=inventory_items[device_location],
        )

        report.is_critical = report.days_until_stockout < self.config.critical_threshold
        
        return report
    
    @staticmethod
    def _sum_positive(values) -> int:
        """Sum only positive values."""
        return sum(v for v in values if v >= 0)

