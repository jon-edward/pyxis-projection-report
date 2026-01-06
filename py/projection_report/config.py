from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ReportConfig:
    """
    Immutable configuration for report generation.
    
    Args:
        reports_dir: Directory containing input Excel files
        output_path: Path for generated PDF report
        include_unordered: Include items without active orders
        include_min_zero: Include items with minimum quantity of 0
        critical_threshold: Days threshold for critical items
        devices: Tuple of device name prefixes to include (empty = all)
        exclude: Tuple of device name prefixes to exclude
        max_days: Maximum days until stockout to include in report
        only_critical: Only include critical items in report
        
    Examples:
        >>> config = ReportConfig(devices=('EMER',), critical_threshold=5.0)
        >>> config.should_include_device('EMER-01')
        True
    """
    reports_dir: Path = Path("reports")
    output_path: Path = Path("reports/projection_report.pdf")
    include_unordered: bool = False
    include_min_zero: bool = False
    critical_threshold: float = 3.0
    devices: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    max_days: float = 5.0
    only_critical: bool = False

    def __post_init__(self) -> None:
        """Validate and normalize configuration values."""
        self.reports_dir = Path(self.reports_dir)
        self.output_path = Path(self.output_path)
        self.devices = tuple(self.devices)
        self.exclude = tuple(self.exclude)
        
        # Validation
        if self.critical_threshold < 0:
            raise ValueError("Critical threshold must be non-negative")
        if self.max_days <= 0:
            raise ValueError("Max days must be positive")

    def should_include_device(self, device: str) -> bool:
        """
        Determine if a device should be included in the report.
        
        Args:
            device: Device name to check (case-insensitive)
            
        Returns:
            True if device should be included, False otherwise
            
        Examples:
            >>> config = ReportConfig(devices=('pyxis',), exclude=('test',))
            >>> config.should_include_device('Pyxis-Main')
            True
            >>> config.should_include_device('Test-Pyxis')
            False
        """
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