from fpdf import FPDF
from contextlib import nullcontext
from datetime import datetime, timedelta
from dataclasses import dataclass
import random

from .config import ReportConfig
from .data_loader import InventoryLoader, UsageLoader
from .metrics import MetricsGenerator
from .models import LocationReport


@dataclass
class ReportStyle:
    """Centralized style configuration for easy customization"""
    
    # Font settings
    font_family: str = 'Arial'  # Options: 'Arial', 'Courier', 'Times', 'Helvetica'
    font_size_title: int = 16
    font_size_header: int = 14
    font_size_section: int = 12
    font_size_body: int = 10
    font_size_small: int = 9
    font_size_footer: int = 8
    
    # Color scheme (RGB tuples)
    color_header_bg: tuple[int, int, int] = (70, 130, 180)      # Steel blue
    color_header_text: tuple[int, int, int] = (255, 255, 255)   # White
    color_critical_bg: tuple[int, int, int] = (255, 240, 240)   # Light red
    color_critical_text: tuple[int, int, int] = (200, 0, 0)     # Dark red
    color_normal_text: tuple[int, int, int] = (0, 0, 0)         # Black
    color_legend_bg: tuple[int, int, int] = (255, 240, 240)     # Light red (for legend box)
    color_neutral_gray: tuple[int, int, int] = (76, 76, 76)     # For low-impact backgrounds
    
    # Layout settings
    indent_size: int = 5
    line_spacing_items: int = 5
    section_spacing: int = 6
    device_spacing: int = 8


class PyxisInventoryReport(FPDF):
    def __init__(self, config: ReportConfig, metrics: dict[str, list[LocationReport]], style: ReportStyle | None = None):
        super().__init__()
        self.config = config
        self.metrics = metrics
        self.style = style if style is not None else ReportStyle()
    
    def header(self):
        self.set_font(self.style.font_family, 'B', self.style.font_size_title)
        self.cell(0, 10, 'Pyxis Inventory Report', new_x="LMARGIN", new_y="NEXT", align='C')
        self.set_font(self.style.font_family, '', self.style.font_size_body)
        self.cell(0, 6, f'Report Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', new_x="LMARGIN", new_y="NEXT", align='C')
        self.ln(5)
        
    def footer(self):
        self.set_y(-15)
        self.set_font(self.style.font_family, 'I', self.style.font_size_footer)
        self.cell(0, 10, f'Page {self.page_no()} of {{nb}}', align='C')
        
    def add_device_header(self, device_name: str):
        self.set_font(self.style.font_family, 'B', self.style.font_size_header)
        self.set_fill_color(*self.style.color_header_bg)
        self.set_text_color(*self.style.color_header_text)
        self.cell(0, 10, device_name, new_x="LMARGIN", new_y="NEXT", align='L', fill=True)
        self.set_text_color(*self.style.color_normal_text)
        self.ln(3)

    def add_summary(self, metrics: dict[str, list[LocationReport]]):
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
    
    def add_location_report(self, location_report: LocationReport):
        if location_report.is_critical:
            self.set_fill_color(*self.style.color_critical_bg)
        else:
            self.set_fill_color(255, 255, 255)
        
        critical_prefix = f"* " if location_report.is_critical else ''
        self.set_font(self.style.font_family, 'B', self.style.font_size_body + 1)

        self.multi_cell(0, 7, f"{critical_prefix}{location_report.med_desc} (IEN: {location_report.med_id})",  new_x="LMARGIN", new_y="NEXT", align='L', fill=True)
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
        self.cell(self.get_string_width(stockout_str) + stockout_w_margin * 2, 6, stockout_str, fill=True, new_x="LMARGIN", new_y="NEXT", align='C')

        # Reset color and font
        self.set_fill_color(255, 255, 255)
        self.set_text_color(*self.style.color_normal_text)
        self.set_font(self.style.font_family, '', self.style.font_size_body)
        
        # Second line of data
        self.set_x(left_margin + self.style.indent_size)
        self.cell(line_w / 2, 6, f'First Activity: {location_report.first_activity}', 0, 0)
        self.cell(0, 6, f'Last Activity: {location_report.last_activity}', new_x="LMARGIN", new_y="NEXT", align='L')

        underscore_size = self.get_string_width("_")

        # User fields
        dispensed_label = "Dispensed: "
        back_count_label = "Back Count: "

        disp_available =  (line_w / 2) - self.get_string_width(dispensed_label) - 3
        back_count_available = (line_w / 2) - self.get_string_width(back_count_label) - 3

        self.set_x(left_margin + self.style.indent_size)
        self.cell(line_w / 2, 6, dispensed_label + ('_' * int(disp_available / underscore_size)))
        self.cell(line_w / 2, 6, back_count_label + ('_' * int(back_count_available / underscore_size)), new_x="LMARGIN", new_y="NEXT", align='L')
        
        self.ln(self.style.line_spacing_items)
    
    def add_device_summary(self, location_reports: list[LocationReport]):
        self.set_font(self.style.font_family, 'I', self.style.font_size_body)

        total_count = len(location_reports)
        critical_count = sum(1 for r in location_reports if r.is_critical)

        content = f"Total Items: {total_count}"
        if not self.config.only_critical:
            content = f"{content}; Total Critical Items: {critical_count}"

        self.cell(0, 6, content,  new_x="LMARGIN", new_y="NEXT", align='C')
        self.ln(self.style.line_spacing_items)
    
    def add_section(self, device_name: str, location_reports: list[LocationReport]):
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
    
    def add_notes(self):
        self.set_font(self.style.font_family, 'I', self.style.font_size_small)
        with self.unbreakable() as pdf:
            pdf.multi_cell(0, 5, 
                'Notes:\n'
                '- Estimated days remaining calculated based on average usage\n'
                '- Critical item drug names are prefixed with an asterisk ("*")'
            )

# ============================================================================
# Report Generation
# ============================================================================

def create_report(config: ReportConfig):
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
    report.output(config.output_path)
