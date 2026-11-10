import urllib.request
import http.client

def create_dummy(name: str):
    def _raise_used_error():
        raise TypeError(f"{name} is a dummy class for import and should not be instantiated")
    class Dummy:
        def __init__(self, *args, **kwargs):
            _raise_used_error()
    return Dummy

# Create dummy classes for FPDF required imports
urllib.request.HTTPSHandler = create_dummy("urllib.request.HTTPSHandler")
http.client.HTTPSConnection = create_dummy("http.client.HTTPSConnection")

from fpdf import FPDF
from datetime import datetime
from dataclasses import dataclass
import logging
import math
from pathlib import Path

from .config import ReportConfig
from .data_loader import InventoryLoader, UsageLoader
from .excel import write_excel
from .metrics import MetricsGenerator
from .models import LocationReport
from .text import ENCODING as TEXT_ENCODING, to_pdf_text

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
        self.core_fonts_encoding = TEXT_ENCODING
        self.config = config
        self.metrics = metrics
        self.style = style if style is not None else ReportStyle()

    def normalize_text(self, text: str) -> str:
        """Clean text for the built-in fonts; applies to every string drawn."""
        return super().normalize_text(to_pdf_text(text))

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
        max_days_str = (
            "No limit" if self.config.max_days is None
            else f"{self.config.max_days:.1f} days"
        )
        self.cell(0, 6, f"Maximum Days Until Stockout: {max_days_str}", new_x="LMARGIN", new_y="NEXT")

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
    
    @staticmethod
    def _location_title(location_report: LocationReport) -> str:
        critical_prefix = "* " if location_report.is_critical else ""
        return f"{critical_prefix}{location_report.med_desc} (IEN: {location_report.med_id})"

    def _location_report_height(self, location_report: LocationReport) -> float:
        """
        Height in mm that add_location_report advances, including its trailing
        gap (fpdf2 also page-breaks on that gap). Keep in sync with
        add_location_report. Predicting page breaks from this is much faster
        than test-rendering each item, which deep-copies the whole document.
        """
        self.set_font(self.style.font_family, 'B', self.style.font_size_body + 1)
        title_lines = self.multi_cell(
            0, 7, self._location_title(location_report),
            align='L', dry_run=True, output="LINES"
        )
        # Title lines (7 each), 1 gap, 3 rows of 6, then the trailing gap.
        return len(title_lines) * 7 + 1 + 3 * 6 + self.style.line_spacing_items

    def _section_start_height(self) -> float:
        """Height in mm of the device header and device summary, with gaps."""
        return 10 + 3 + 6 + self.style.line_spacing_items

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
        
        self.set_font(self.style.font_family, 'B', self.style.font_size_body + 1)

        self.multi_cell(
            0, 7,
            self._location_title(location_report),
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
        qty_min_str = "N/A" if location_report.qty_min is None else location_report.qty_min
        qty_max_str = "N/A" if location_report.qty_max is None else location_report.qty_max
        self.cell(line_w / 4, 6, f'Min: {qty_min_str}')
        self.cell(line_w / 4, 6, f'Max: {qty_max_str}')

        days_remaining_str = "Days Remaining: "
        self.cell(self.get_string_width(days_remaining_str) + 1, 6, days_remaining_str)

        if location_report.is_critical:
            self.set_font(self.style.font_family, 'B', self.style.font_size_body)
            self.set_fill_color(*self.style.color_critical_text)
            self.set_text_color(255, 255, 255)
            stockout_w_margin = 1
        else:
            stockout_w_margin = 0

        # No usage means an infinite projection; don't print "inf".
        if math.isinf(location_report.days_until_stockout):
            stockout_str = "No usage"
        else:
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
            # Keep the device header, its summary, and the first item together.
            needed = self._section_start_height()
            if location_reports:
                needed += self._location_report_height(location_reports[0])
            if self.get_y() + needed > self.page_break_trigger:
                self.add_page()

            self.add_device_header(device_name)
            self.add_device_summary(location_reports)

            for i, report in enumerate(location_reports):
                # Start a new page (with a continuation header) if the item won't fit.
                if i > 0 and (
                    self.get_y() + self._location_report_height(report)
                    > self.page_break_trigger
                ):
                    self.add_page()
                    self.add_device_header(f"{device_name} cont.")
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
        write_excel(self.config, _sorted_sections(self.metrics), path)


# ============================================================================
# Report Generation
# ============================================================================

def _sorted_sections(
    metrics: dict[str, list[LocationReport]]
) -> list[tuple[str, list[LocationReport]]]:
    """Order devices by name and sort each device's reports in place."""
    sections = sorted(metrics.items(), key=lambda x: x[0].lower())
    for _, location_reports in sections:
        location_reports.sort()
    return sections


def create_report(config: ReportConfig, export_excel: bool = False) -> None:
    """
    Generate inventory report from configuration.

    The report is written to config.output_path (PDF), or to
    config.excel_path when config.output_format is "excel".

    Args:
        config: Report configuration
        export_excel: Also write an Excel file next to the PDF

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

        sections = _sorted_sections(metrics)

        if config.output_format == "excel":
            write_excel(config, sections, config.excel_path)
            logger.info(f"Report generated successfully: {config.excel_path}")
            return

        report = PyxisInventoryReport(config, metrics)
        report.add_page()

        report.add_summary(metrics)

        for device_name, location_reports in sections:
            report.add_section(device_name, location_reports)

        report.add_notes()

        # Ensure output directory exists
        config.output_path.parent.mkdir(parents=True, exist_ok=True)

        report.output(str(config.output_path))
        logger.info(f"Report generated successfully: {config.output_path}")

        # Optional Excel export
        if export_excel:
            write_excel(config, sections, config.excel_path)

    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise