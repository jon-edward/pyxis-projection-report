from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

@dataclass
class ReportConfig:
    """Immutable configuration for report generation."""
    reports_dir: Path = Path("reports")
    output_path: Path = Path("reports/projection_report.pdf")
    include_unordered: bool = False
    include_min_zero: bool = False
    critical_threshold: float = 3.0
    devices: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    max_days: float = 5.0
    only_critical: bool = False

    def __post_init__(self):
        self.reports_dir = Path(self.reports_dir)
        self.output_path = Path(self.output_path)
        self.devices = tuple(self.devices)
        self.exclude = tuple(self.exclude)

    def should_include_device(self, device: str) -> bool:
        """Determine if a device should be included in the report."""
        device_lower = device.lower()
        
        # Check exclusions first
        for exclude_pattern in self.exclude:
            if device_lower.startswith(exclude_pattern.lower()):
                return False
        
        # Check inclusions if specified
        if self.devices:
            return any(
                device_lower.startswith(pattern.lower()) 
                for pattern in self.devices
            )
        
        return True
