"""Excel output for the projection report."""

import logging
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .config import ReportConfig
from .models import LocationReport, ReportContext, USAGE_NOTES

logger = logging.getLogger(__name__)

Sections = Sequence[tuple[str, Sequence[LocationReport]]]

HEADER_FILL = PatternFill("solid", fgColor="4682B4")
HEADER_FONT = Font(bold=True, color="FFFFFF")
CRITICAL_FILL = PatternFill("solid", fgColor="FFF0F0")
CRITICAL_FONT = Font(color="C80000")


def _days_until_stockout(r: LocationReport) -> Optional[float]:
    """Blank (None) when there is no usage, so the column stays numeric."""
    days = r.days_until_stockout
    return None if math.isinf(days) else round(days, 1)


def _date(value) -> Any:
    """Excel date, or blank when there is no activity."""
    return None if value is None else value.to_pydatetime()


# (header, value getter, column width, number format)
COLUMNS: list[tuple[str, Callable[[LocationReport], Any], int, Optional[str]]] = [
    ("Device", lambda r: r.device, 14, None),
    ("Location", lambda r: r.device_location, 14, None),
    ("Medication", lambda r: r.med_desc, 42, None),
    ("Med ID", lambda r: r.med_id, 10, None),
    ("Current Qty", lambda r: r.current_qty, 12, "0"),
    ("Min", lambda r: r.qty_min, 8, "0"),
    ("Max", lambda r: r.qty_max, 8, "0"),
    ("Qty To Refill", lambda r: r.qty_to_refill, 13, "0"),
    ("Days Until Stockout", _days_until_stockout, 19, "0.0"),
    ("Avg Weekly Usage", lambda r: round(r.avg_daily_usage * 7, 1), 17, "0.0"),
    ("Critical", lambda r: "Yes" if r.is_critical else "No", 9, None),
    ("Active Order", lambda r: "Yes" if r.inventory_item.has_orders else "No", 13, None),
    ("First Activity", lambda r: _date(r.first_activity), 14, "yyyy-mm-dd"),
    ("Last Activity", lambda r: _date(r.last_activity), 14, "yyyy-mm-dd"),
    ("Qty Removed", lambda r: r.qty_removed, 12, "0"),
    ("Removals", lambda r: r.removal_count, 10, "0"),
    ("Low Data", lambda r: "Yes" if r.low_data else "No", 10, None),
    ("No Activity", lambda r: "No" if r.has_activity else "Yes", 12, None),
]


CRITICAL_FONT_COLUMNS = [
    i for i, (header, *_) in enumerate(COLUMNS) if header in ("Days Until Stockout", "Critical")
]


def _yes_no(value: bool) -> str:
    return "Yes" if value else "No"


def _summary_rows(
    config: ReportConfig, sections: Sections, context: ReportContext
) -> list[tuple[str, Any]]:
    """Same settings and totals as the PDF summary."""
    total_items = sum(len(reports) for _, reports in sections)
    total_critical = sum(1 for _, reports in sections for r in reports if r.is_critical)

    max_days = "No limit" if config.max_days is None else f"{config.max_days:.1f} days"

    rows: list[tuple[str, Any]] = [
        ("Report Generated", datetime.now().strftime("%Y-%m-%d %H:%M")),
        ("Total Items", total_items),
    ]
    if not config.only_critical:
        rows.append(("Total Critical Items", total_critical))
    rows += [
        ("Include Items With a Min of 0", _yes_no(config.include_min_zero)),
        ("Critical Threshold", f"{config.critical_threshold:.1f} days"),
        ("Maximum Days Until Stockout", max_days),
    ]
    usage_window = context.usage_window_text()
    if usage_window:
        rows.append(("Usage Window", usage_window))
    rows += [
        ("Include Items Without an Active Order", _yes_no(config.include_unordered)),
        ("Only Include Critical Items", _yes_no(config.only_critical)),
    ]
    if config.devices:
        rows.append(("Includes", ", ".join(d.upper() for d in config.devices)))
    if config.exclude:
        rows.append(("Excludes", ", ".join(d.upper() for d in config.exclude)))
    for warning in context.warnings:
        rows.append(("Data Warning", warning))
    return rows


def write_excel(
    config: ReportConfig,
    sections: Sections,
    path: Path,
    context: Optional[ReportContext] = None,
) -> None:
    """
    Write the report to an .xlsx file.

    Args:
        config: Report configuration (shown on the Summary sheet)
        sections: (device name, location reports) pairs, already sorted
        path: Output file path
        context: Facts about the data behind the report (usage window)
    """
    context = context if context is not None else ReportContext()
    logger.info(f"Writing Excel report: {path}")
    wb = Workbook()

    items = wb.active
    items.title = "Items"
    items.append([header for header, *_ in COLUMNS])
    for cell in items[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for _, reports in sections:
        for r in reports:
            items.append([getter(r) for _, getter, _, _ in COLUMNS])
            row = items[items.max_row]
            for cell, (_, _, _, number_format) in zip(row, COLUMNS):
                if number_format:
                    cell.number_format = number_format
                if r.is_critical:
                    cell.fill = CRITICAL_FILL
            if r.is_critical:
                # Days remaining and the flag stand out, like the PDF.
                for idx in CRITICAL_FONT_COLUMNS:
                    row[idx].font = CRITICAL_FONT

    for idx, (_, _, width, _) in enumerate(COLUMNS, start=1):
        items.column_dimensions[get_column_letter(idx)].width = width
    items.freeze_panes = "A2"
    items.auto_filter.ref = items.dimensions

    summary = wb.create_sheet("Summary")
    summary.append(["Pyxis Inventory Report"])
    summary["A1"].font = Font(bold=True, size=14)
    summary.append([])
    for label, value in _summary_rows(config, sections, context):
        summary.append([label, value])
        summary.cell(row=summary.max_row, column=1).font = Font(bold=True)
        if label == "Data Warning":
            for col in (1, 2):
                summary.cell(row=summary.max_row, column=col).font = Font(bold=col == 1, color="C80000")
    summary.append([])
    summary.append(["Notes"])
    summary.cell(row=summary.max_row, column=1).font = Font(bold=True)
    for note in USAGE_NOTES:
        summary.append([note])
    summary.column_dimensions["A"].width = 38
    summary.column_dimensions["B"].width = 36
    wb.move_sheet("Summary", offset=-1)
    wb.active = 0

    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    logger.info(f"Excel report complete: {path}")
