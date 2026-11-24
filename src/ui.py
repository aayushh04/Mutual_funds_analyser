"""Small presentation helpers: the HTML metrics table (with tooltips + best-value highlight) and formatting."""

from __future__ import annotations

import html
from typing import Optional

import pandas as pd

from src.content import METRIC_TIPS

TABLE_CSS = """
<style>
.mfa-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; border: 1px solid #e6e5e0; border-radius: 8px; }
.mfa-table { border-collapse: collapse; width: 100%; font-size: 0.9rem; font-variant-numeric: tabular-nums; }
.mfa-table th, .mfa-table td { padding: 8px 10px; border-bottom: 1px solid #efeee9; text-align: right; white-space: nowrap; }
.mfa-table thead th { background: #f4f6fa; color: #1b1f24; font-weight: 600; vertical-align: bottom; white-space: normal; min-width: 120px; }
.mfa-table th:first-child, .mfa-table td:first-child { text-align: left; position: sticky; left: 0; background: #ffffff; z-index: 1; }
.mfa-table thead th:first-child { background: #f4f6fa; }
.mfa-table tr:last-child td { border-bottom: none; }
.mfa-swatch { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; vertical-align: middle; }
.mfa-bench { background-image: repeating-linear-gradient(45deg, #6b6a66 0 2px, #ffffff 2px 4px); }
.mfa-best { background: #e3f1e6; font-weight: 700; color: #0f5a1f; }
.mfa-na { color: #8a8984; }
.mfa-tip { position: relative; display: inline-block; margin-left: 4px; color: #52514e; cursor: help; outline: none; }
.mfa-tip .mfa-tiptext { visibility: hidden; opacity: 0; position: absolute; left: 0; top: 130%; width: 240px; z-index: 10;
  background: #1b1f24; color: #ffffff; padding: 8px 10px; border-radius: 6px; font-size: 0.8rem; font-weight: 400;
  white-space: normal; line-height: 1.35; transition: opacity 0.15s; }
.mfa-tip:hover .mfa-tiptext, .mfa-tip:focus .mfa-tiptext { visibility: visible; opacity: 1; }
</style>
"""


def fmt_value(value: object, decimals: int = 2) -> str:
    """Display a table cell: numbers rounded, missing values as 'n/a'."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "n/a"
    if isinstance(value, (int, float)):
        return f"{value:,.{decimals}f}"
    return str(value)


def pct(value: Optional[float], decimals: int = 2) -> str:
    """Decimal -> '12.34%' (or 'n/a')."""
    return "n/a" if value is None or pd.isna(value) else f"{value * 100:.{decimals}f}%"


def rupees(value: Optional[float]) -> str:
    """Number -> 'Rs 1,23,456' style string (Western grouping for simplicity)."""
    return "n/a" if value is None or pd.isna(value) else f"Rs {value:,.0f}"


def metrics_table_html(
    table: pd.DataFrame, best: dict[str, list[str]], colors: dict[str, str], bench_name: str, short_names: dict[str, str]
) -> str:
    """Render the metrics table as HTML: (i) tooltip per metric, best fund value highlighted."""
    head = ['<th>Metric</th>']
    for col in table.columns:
        swatch_cls = "mfa-swatch mfa-bench" if col == bench_name else "mfa-swatch"
        style = "" if col == bench_name else f' style="background:{colors.get(col, "#999")}"'
        label = short_names.get(col, col) + (" (benchmark)" if col == bench_name else "")
        head.append(f'<th title="{html.escape(col)}"><span class="{swatch_cls}"{style}></span>{html.escape(label)}</th>')

    body = []
    for row in table.index:
        tip = html.escape(METRIC_TIPS.get(row, ""))
        cells = [
            f'<td>{html.escape(row)}<span class="mfa-tip" tabindex="0" aria-label="{tip}">ⓘ'
            f'<span class="mfa-tiptext">{tip}</span></span></td>'
        ]
        for col in table.columns:
            text = fmt_value(table.loc[row, col])
            classes = []
            if col in best.get(row, []):
                classes.append("mfa-best")
                text = "★ " + text  # not colour-only
            if text == "n/a":
                classes.append("mfa-na")
            cls = f' class="{" ".join(classes)}"' if classes else ""
            cells.append(f"<td{cls}>{html.escape(text)}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")

    return (
        TABLE_CSS
        + '<div class="mfa-wrap"><table class="mfa-table"><thead><tr>'
        + "".join(head)
        + "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table></div>"
    )


def short_name(name: str, limit: int = 40) -> str:
    """Drop the plan/option suffix from a scheme name for compact headers."""
    for suffix in (" - Direct Plan - Growth Option", " - Direct Plan - Growth", " - Direct Plan", " - Growth Option", " - Growth"):
        name = name.replace(suffix, "")
    return name if len(name) <= limit else name[: limit - 1] + "…"
