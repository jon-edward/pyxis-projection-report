from fpdf import FPDF
from datetime import datetime
from dataclasses import dataclass
import logging
from pathlib import Path

import pandas as pd

from .config import ReportConfig
from .data_loader import InventoryLoader, UsageLoader
from .metrics import MetricsGenerator
from .models import LocationReport

logger = logging.getLogger(__name__)


@dataclass
class ReportStyle:
    """
    Centralized style configuration for easy customization.
    
    Attributes:
        font_family: Font family name (Arial, Courier, Times, Helvetica)
        font_size_*: Font sizes for different elements
        color_*: RGB color tuples for various elements
        date_format: Format string for datetime objects
        short_date_format: Format string for date-only display
        indent_size: Indentation size in mm
        line_spacing_items: Spacing between items in mm
        section_spacing: Spacing between sections in mm
        device_spacing: Spacing between devices in mm
    """
    
    # Font settings
    font_family: str = 'Arial'
    font_size_title: int = 16
    font_size_header: int = 14
    font_size_section: int = 12
    font_size_body: int = 10
    font_size_small: int = 9
    font_size_footer: int = 8
    
    # Color scheme (RGB tuples)
    color_header_bg: tuple[int, int, int] = (70, 130, 180)
    color_header_text: tuple[int, int, int] = (255, 255, 255)
    color_critical_bg: tuple[int, int, int] = (255, 240, 240)
    color_critical_text: tuple[int, int, int] = (200, 0, 0)
    color_normal_text: tuple[int, int, int] = (0, 0, 0)
    color_legend_bg: tuple[int, int, int] = (255, 240, 240)
    color_neutral_gray: tuple[int, int, int] = (76, 76, 76)
    
    # Date formatting
    date_format: str = "%Y-%m-%d %H:%M"
    short_date_format: str = "%Y-%m-%d"
    
    # Layout settings
    indent_size: int = 5
    line_spacing_items: int = 5
    section_spacing: int = 6
    device_spacing: int = 8


class PyxisInventoryReport(FPDF):
    """
    PDF report generator for Pyxis inventory data.
    
    Attributes:
        config: Report configuration
        metrics: Dictionary of device reports
        style: Style configuration for the report
    """
    
    def __init__(
        self, 
        config: ReportConfig, 
        metrics: dict[str, list[LocationReport]], 
        style: ReportStyle | None = None
    ):
        super().__init__()
        self.config = config
        self.metrics = metrics
        self.style = style if style is not None else ReportStyle()
    
    def header(self) -> None:
        """Generate report header with title and timestamp."""
        self.set_font(self.style.font_family, 'B', self.style.font_size_title)
        self.cell(0, 10, 'Pyxis Inventory Report', new_x="LMARGIN", new_y="NEXT", align='C')
        self.set_font(self.style.font_family, '', self.style.font_size_body)
        self.cell(
            0, 6, 
            f'Report Generated: {datetime.now().strftime(self.style.date_format)}', 
            new_x="LMARGIN", 
            new_y="NEXT", 
            align='C'
        )
        self.ln(5)
        
    def footer(self) -> None:
        """Generate report footer with page number."""
        self.set_y(-15)
        self.set_font(self.style.font_family, 'I', self.style.font_size_footer)
        self.cell(0, 10, f'Page {self.page_no()} of {{nb}}', align='C')
        
    def add_device_header(self, device_name: str) -> None:
        """
        Add a device section header.
        
        Args:
            device_name: Name of the device section
        """
        self.set_font(self.style.font_family, 'B', self.style.font_size_header)
        self.set_fill_color(*self.style.color_header_bg)
        self.set_text_color(*self.style.color_header_text)
        self.cell(0, 10, device_name, new_x="LMARGIN", new_y="NEXT", align='L', fill=True)
        self.set_text_color(*self.style.color_normal_text)
        self.ln(3)

    def add_summary(self, metrics: dict[str, list[LocationReport]]) -> None:
        """
        Add report summary section.
        
        Args:
            metrics: Dictionary of all device reports
        """
        self.set_font(self.style.font_family, 'B', self.style.font_size_section)
        self.cell(0, 8, "Inventory Status Summary", new_x="LMARGIN", new_y="NEXT")
        self.set_font(self.style.font_family, '', self.style.font_size_body)
        
        left_margin = self.l_margin

        total_items = 0
        total_critical = 0
        for v in metrics.values():
            total_items += len(v)
            total_critical += sum(1 for r in v if r.is_critical)

        self.set_x(left_margin + self.style.indent_size)
        self.cell(0, 6, f"Total Items: {total_items}", new_x="LMARGIN", new_y="NEXT")

        if not self.config.only_critical:
            self.set_x(left_margin + self.style.indent_size)
            self.cell(0, 6, f"Total Critical Items: {total_critical}", new_x="LMARGIN", new_y="NEXT")

        self.set_x(left_margin + self.style.indent_size)
        self.cell(0, 6, f"Include Items With a Min of 0: {'Yes' if self.config.include_min_zero else 'No'}", new_x="LMARGIN", new_y="NEXT")

        self.set_x(left_margin + self.style.indent_size)
        self.cell(0, 6, f"Critical Threshold: {self.config.critical_threshold:.1f} days", new_x="LMARGIN", new_y="NEXT")

        self.set_x(left_margin + self.style.indent_size)
        self.cell(0, 6, f"Maximum Days Until Stockout: {self.config.max_days:.1f} days", new_x="LMARGIN", new_y="NEXT")

        self.set_x(left_margin + self.style.indent_size)
        self.cell(0, 6, f"Include Orders Without an Active Order: {'Yes' if self.config.include_unordered else 'No'}", new_x="LMARGIN", new_y="NEXT")

        self.set_x(left_margin + self.style.indent_size)
        self.cell(0, 6, f"Only Include Critical Items: {'Yes' if self.config.only_critical else 'No'}", new_x="LMARGIN", new_y="NEXT")

        if self.config.devices:
            self.set_x(left_margin + self.style.indent_size)
            self.cell(0, 6, f"Includes: {', '.join(c.upper() for c in self.config.devices)}", new_x="LMARGIN", new_y="NEXT")
        
        if self.config.exclude:
            self.set_x(left_margin + self.style.indent_size)
            self.cell(0, 6, f"Excludes: {', '.join(c.upper() for c in self.config.exclude)}", new_x="LMARGIN", new_y="NEXT")

        self.ln(self.style.line_spacing_items)
    
    def add_location_report(self, location_report: LocationReport) -> None:
        """
        Add a single location report item.
        
        Args:
            location_report: LocationReport to display
        """
        if location_report.is_critical:
            self.set_fill_color(*self.style.color_critical_bg)
        else:
            self.set_fill_color(255, 255, 255)
        
        critical_prefix = f"* " if location_report.is_critical else ''
        self.set_font(self.style.font_family, 'B', self.style.font_size_body + 1)

        self.multi_cell(
            0, 7, 
            f"{critical_prefix}{location_report.med_desc} (IEN: {location_report.med_id})",  
            new_x="LMARGIN", 
            new_y="NEXT", 
            align='L', 
            fill=True
        )
        self.ln(1)

        self.set_font(self.style.font_family, '', self.style.font_size_body)
        left_margin = self.l_margin
        line_w = self.epw - self.style.indent_size

        self.set_x(left_margin + self.style.indent_size)
        self.cell(line_w / 4, 6, f'Current: {location_report.current_qty}')
        self.cell(line_w / 4, 6, f'Min: {location_report.qty_min}')
        self.cell(line_w / 4, 6, f'Max: {location_report.qty_max}')

        days_remaining_str = "Days Remaining: "
        self.cell(self.get_string_width(days_remaining_str) + 1, 6, days_remaining_str)

        if location_report.is_critical:
            self.set_font(self.style.font_family, 'B', self.style.font_size_body)
            self.set_fill_color(*self.style.color_critical_text)
            self.set_text_color(255, 255, 255)
            stockout_w_margin = 1
        else:
            stockout_w_margin = 0

        stockout_str = f"{location_report.days_until_stockout:.1f}"
        self.cell(
            self.get_string_width(stockout_str) + stockout_w_margin * 2, 
            6, 
            stockout_str, 
            fill=True, 
            new_x="LMARGIN", 
            new_y="NEXT", 
            align='C'
        )

        # Reset color and font
        self.set_fill_color(255, 255, 255)
        self.set_text_color(*self.style.color_normal_text)
        self.set_font(self.style.font_family, '', self.style.font_size_body)
        
        # Second line of data
        self.set_x(left_margin + self.style.indent_size)
        first_activity_str = location_report.first_activity.strftime(self.style.short_date_format)
        last_activity_str = location_report.last_activity.strftime(self.style.short_date_format)
        self.cell(line_w / 3, 6, f'First Activity: {first_activity_str}')
        self.cell(line_w / 3, 6, f'Last Activity: {last_activity_str}')
        self.cell(line_w / 3, 6, f'Average Weekly Usage: {location_report.avg_daily_usage * 7:.1f}', new_x="LMARGIN", new_y="NEXT", align='L')

        underscore_size = self.get_string_width("_")

        # User fields
        dispensed_label = "Dispensed: "
        back_count_label = "Back Count: "

        disp_available = (line_w / 2) - self.get_string_width(dispensed_label) - 3
        back_count_available = (line_w / 2) - self.get_string_width(back_count_label) - 3

        self.set_x(left_margin + self.style.indent_size)
        self.cell(line_w / 2, 6, dispensed_label + ('_' * int(disp_available / underscore_size)))
        self.cell(line_w / 2, 6, back_count_label + ('_' * int(back_count_available / underscore_size)), new_x="LMARGIN", new_y="NEXT", align='L')
        
        self.ln(self.style.line_spacing_items)
    
    def add_device_summary(self, location_reports: list[LocationReport]) -> None:
        """
        Add summary statistics for a device section.
        
        Args:
            location_reports: List of LocationReports for this device
        """
        self.set_font(self.style.font_family, 'I', self.style.font_size_body)

        total_count = len(location_reports)
        critical_count = sum(1 for r in location_reports if r.is_critical)

        content = f"Total Items: {total_count}"
        if not self.config.only_critical:
            content = f"{content}; Total Critical Items: {critical_count}"

        self.cell(0, 6, content, new_x="LMARGIN", new_y="NEXT", align='C')
        self.ln(self.style.line_spacing_items)
    
    def add_section(self, device_name: str, location_reports: list[LocationReport]) -> None:
        """
        Add a complete device section with header, summary, and reports.
        
        Args:
            device_name: Name of the device
            location_reports: List of LocationReports for this device
        """
        try:
            with self.unbreakable() as pdf:
                pdf.add_device_header(device_name)
                pdf.add_device_summary(location_reports)
                if len(location_reports):
                    pdf.add_location_report(location_reports[0])
            
            for report in location_reports[1:]:
                # Check if the resulting content will trigger a page break 
                with self.offset_rendering() as dummy:
                    dummy.add_location_report(report)
                
                if dummy.page_break_triggered:
                    # Add continuation header
                    self.add_page()
                    self.add_device_header(f"{device_name} cont.")
                    self.add_location_report(report)
                else:
                    # Add content on same page
                    self.add_location_report(report)
            
            self.ln(self.style.line_spacing_items)
        except Exception as e:
            logger.error(f"Failed to add section for {device_name}: {e}")
            raise
    
    def add_notes(self) -> None:
        """Add notes section at end of report."""
        self.set_font(self.style.font_family, 'I', self.style.font_size_small)
        with self.unbreakable() as pdf:
            pdf.multi_cell(0, 5, 
                'Notes:\n'
                '- Estimated days remaining calculated based on average usage\n'
                '- Critical item drug names are prefixed with an asterisk ("*")'
            )

    def export_to_excel(self, path: Path) -> None:
        """
        Export metrics to Excel for further analysis.
        
        Args:
            path: Path for output Excel file
        """
        logger.info(f"Exporting metrics to Excel: {path}")
        with pd.ExcelWriter(path) as writer:
            for device, reports in self.metrics.items():
                df = pd.DataFrame([{
                    'Device Location': r.device_location,
                    'Medication': r.med_desc,
                    'Med ID': r.med_id,
                    'Current Qty': r.current_qty,
                    'Min': r.qty_min,
                    'Max': r.qty_max,
                    'Days Until Stockout': round(r.days_until_stockout, 1),
                    'Avg Daily Usage': round(r.avg_daily_usage, 2),
                    'Is Critical': r.is_critical,
                    'Has Orders': r.inventory_item.has_orders,
                    'First Activity': r.first_activity,
                    'Last Activity': r.last_activity,
                } for r in reports])
                
                # Excel sheet names limited to 31 characters
                sheet_name = device[:31]
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        logger.info(f"Excel export complete: {path}")


# ============================================================================
# Report Generation
# ============================================================================

def create_report(config: ReportConfig, export_excel: bool = False) -> None:
    """
    Generate inventory report from configuration.
    
    Args:
        config: Report configuration
        export_excel: Whether to also export to Excel format
        
    Raises:
        DataLoadError: If data loading fails
        Exception: If report generation fails
    """
    logger.info("Starting report generation")
    
    try:
        metrics = MetricsGenerator(
            config, 
            inventory_loader=InventoryLoader(config.reports_dir / "Inventory.xlsx"), 
            usage_loader=UsageLoader(config.reports_dir / "Usage.xlsx")
        ).metrics()

        report = PyxisInventoryReport(config, metrics)
        report.add_page()

        report.add_summary(metrics)
        
        sections = list(metrics.items())
        sections.sort(key=lambda x: x[0].lower())

        for device_name, location_reports in sections:
            location_reports.sort()
            report.add_section(device_name, location_reports)

        report.add_notes()
        
        # Ensure output directory exists
        config.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        report.output(str(config.output_path))
        logger.info(f"Report generated successfully: {config.output_path}")
        
        # Optional Excel export
        if export_excel:
            excel_path = config.output_path.with_suffix('.xlsx')
            report.export_to_excel(excel_path)
            
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise