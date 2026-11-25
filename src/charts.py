"""Plotly figure builders ("Research Desk" dark theme). Each function takes ready-made data and returns a Figure.

Colour rules: each fund keeps the same colour in every chart (it follows the
fund's position in the selection, not its rank). The benchmark is always a
grey line labelled "(benchmark)", so it is identified by name, not colour alone.

Interactivity: every time-series chart has 1Y / 3Y / 5Y / All zoom buttons, a
crosshair line, one shared hover box, drag-to-zoom and double-click to reset.
Passing `focus` (a fund name) spotlights that fund and fades the others.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.graph_objects as go

# Colour-blind-safe categorical palette, dark-surface steps (slots 1-4) + neutral benchmark.
FUND_COLORS = ["#3987e5", "#d95926", "#199e70", "#c98500"]
BENCH_COLOR = "#8e939a"
INVESTED_COLOR = "#e9e4da"
GRID = "#23262a"
AXIS = "#3a3e44"
TEXT = "#d9d3c7"
MUTED = "#a39d92"
FONT = "Source Sans 3, sans-serif"
FADED = 0.2  # opacity of funds outside the spotlight


def color_map(fund_names: list[str]) -> dict[str, str]:
    """Fixed colour per fund, in selection order."""
    return {name: FUND_COLORS[i % len(FUND_COLORS)] for i, name in enumerate(fund_names)}


def _short(name: str, limit: int = 38) -> str:
    """Shorten long scheme names for legends (full name stays in the hover)."""
    name = name.replace(" - Direct Plan", "").replace(" - Growth Option", "").replace(" - Growth", "").strip()
    return name if len(name) <= limit else name[: limit - 1] + "…"


# Plotly sizes legend entries before the web font loads, so measured widths come out too small and the
# real text overlaps or gets clipped. Fixed-width entries avoid relying on that measurement.
LEGEND_ENTRY_PX = 240  # text width per entry (the line swatch is extra); fits "… Index Fund (benchmark)"


def _label(name: str, is_bench: bool, limit: int = 38) -> str:
    """Legend label; the benchmark is named as such."""
    return _short(name, limit) + (" (benchmark)" if is_bench else "")


def _style(name: str, is_bench: bool, focus: Optional[str]) -> tuple[float, float]:
    """(line width, opacity) for a series, given the current spotlight."""
    if is_bench:
        return 1.5, 0.9
    if focus is None:
        return 2.0, 1.0
    return (3.0, 1.0) if name == focus else (1.5, FADED)


def _layout(fig: go.Figure, y_title: str, y_format: str = "", height: int = 400, time_axis: bool = True) -> go.Figure:
    """Shared dark styling: legend on top, range buttons under it, crosshair, one hover box."""
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=8, b=8, autoexpand=True),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.13 if time_axis else 1.02, xanchor="left", x=0,
                    title=None, font=dict(size=12, color=TEXT), bgcolor="rgba(0,0,0,0)",
                    entrywidth=LEGEND_ENTRY_PX, entrywidthmode="pixels"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=TEXT, size=12),
        hoverlabel=dict(bgcolor="#1a1d21", bordercolor="#3a3e44", font=dict(family=FONT, color="#e9e4da", size=12)),
        dragmode="zoom",
    )
    fig.update_xaxes(automargin=True, showgrid=False, linecolor=AXIS, tickfont=dict(color=MUTED), zeroline=False,
                     showspikes=True, spikemode="across", spikesnap="cursor", spikecolor="#6b665e",
                     spikethickness=1, spikedash="solid")
    fig.update_yaxes(automargin=True, title=dict(text=y_title, font=dict(color=MUTED)), gridcolor=GRID, zerolinecolor=AXIS,
                     tickformat=y_format, tickfont=dict(color=MUTED))
    if time_axis:
        fig.update_xaxes(rangeselector=dict(
            buttons=[dict(count=1, label="1Y", step="year", stepmode="backward"),
                     dict(count=3, label="3Y", step="year", stepmode="backward"),
                     dict(count=5, label="5Y", step="year", stepmode="backward"),
                     dict(step="all", label="All")],
            x=0, xanchor="left", y=1.02, yanchor="bottom",
            bgcolor="#1a1d21", activecolor="#7a5c1c", bordercolor=AXIS, borderwidth=1,
            font=dict(color="#e9e4da", size=11),
        ))
    return fig


def _line(name: str, series: pd.Series, color: str, is_bench: bool, hover_fmt: str,
          focus: Optional[str], scale: float = 1.0, prefix: str = "", suffix: str = "") -> go.Scatter:
    width, opacity = _style(name, is_bench, focus)
    return go.Scatter(
        x=series.index, y=series.values / scale, mode="lines", name=_label(name, is_bench),
        line=dict(color=color, width=width), opacity=opacity,
        hovertemplate=f"{_short(name, 30)}: {prefix}%{{y:{hover_fmt}}}{suffix}<extra></extra>",
    )


def line_chart(
    data: pd.DataFrame, colors: dict[str, str], bench_name: Optional[str],
    y_title: str, y_format: str = "", hover_fmt: str = ",.2f", focus: Optional[str] = None,
) -> go.Figure:
    """Generic multi-series line chart: one column per fund (benchmark grey)."""
    fig = go.Figure()
    for col in data.columns:
        series = data[col].dropna()
        if series.empty:
            continue
        is_bench = col == bench_name
        color = BENCH_COLOR if is_bench else colors.get(col, BENCH_COLOR)
        fig.add_trace(_line(col, series, color, is_bench, hover_fmt, focus))
    return _layout(fig, y_title, y_format)


def add_end_labels(fig: go.Figure, fmt: str = ",.0f", prefix: str = "",
                   names: Optional[dict[str, str]] = None) -> go.Figure:
    """Print each series' final value just past its last point, in the series colour (research-chart style).

    `names` maps a trace name to a short label written before the value, so lines are
    identified by words and not by colour alone.
    """
    widest = 0
    for trace in fig.data:
        if trace.x is None or len(trace.x) == 0 or trace.opacity is not None and trace.opacity < 0.5:
            continue
        y = float(trace.y[-1])
        label = (names or {}).get(trace.name, "")
        text = f"{label} {prefix}{y:{fmt}}".strip()
        widest = max(widest, len(text))
        # Anchored to the plot's right edge (where every line ends), not to a date: a date-anchored
        # label makes plotly widen the x-axis to fit the text.
        fig.add_annotation(xref="paper", x=1, y=y, text=text, showarrow=False, xanchor="left", xshift=6,
                           font=dict(color=trace.line.color, size=12, family=FONT))
    fig.update_layout(margin=dict(r=max(64, 14 + 7 * widest)))
    return fig


def rebased_chart(rebased: pd.DataFrame, colors: dict[str, str], bench_name: str,
                  focus: Optional[str] = None, labels: Optional[dict[str, str]] = None) -> go.Figure:
    """Relative performance: every series rebased to 100 on the common start date, final values labelled.

    For display only, the line is drawn from each week's last NAV (and the final day), which reads
    cleanly in a narrow panel. The numbers in the tables still use every daily NAV.
    """
    weekly = rebased.groupby(rebased.index.to_period("W")).tail(1)
    fig = line_chart(weekly, colors, bench_name, "", ",.0f", ",.1f", focus)
    fig.add_hline(y=100, line=dict(color=AXIS, width=1, dash="dot"))
    # Narrow panel: no legend; each line end carries its fund's name and final value.
    fig.update_layout(height=340, showlegend=False)
    fig.update_yaxes(ticksuffix="  ")  # keeps the '100' tick clear of where the lines start
    fig.update_xaxes(nticks=4)  # the plot is narrow on a phone; more year labels run together
    names = {_label(c, c == bench_name): (labels or {}).get(c, "") for c in rebased.columns}
    return add_end_labels(fig, ",.0f", names=names)


def growth_chart(growth: pd.DataFrame, colors: dict[str, str], bench_name: str, focus: Optional[str] = None) -> go.Figure:
    """Growth of Rs 10,000 invested on the common start date."""
    return line_chart(growth, colors, bench_name, "Value (Rs)", ",.0f", ",.0f", focus)


def drawdown_chart(drawdowns: pd.DataFrame, colors: dict[str, str], bench_name: str,
                   focus: Optional[str] = None) -> go.Figure:
    """% below the previous peak, over time. The spotlighted fund is shaded down to its line."""
    fig = line_chart(drawdowns, colors, bench_name, "Below previous peak", ".0%", ".1%", focus)
    if focus is not None:
        for trace in fig.data:
            if trace.name == _label(focus, False):
                trace.update(fill="tozeroy", fillcolor=_alpha(colors.get(focus, BENCH_COLOR), 0.18))
    return fig


def rolling_vol_chart(vols: pd.DataFrame, colors: dict[str, str], bench_name: str,
                      focus: Optional[str] = None) -> go.Figure:
    """Rolling 1-year annualised volatility."""
    return line_chart(vols, colors, bench_name, "1-year volatility", ".0%", ".1%", focus)


def rolling_returns_chart(rolling: pd.DataFrame, colors: dict[str, str], bench_name: str, years: int,
                          focus: Optional[str] = None) -> go.Figure:
    """Rolling CAGR indexed by investment start date."""
    return line_chart(rolling, colors, bench_name, f"{years}Y rolling CAGR", ".0%", ".1%", focus)


def calendar_chart(cal: pd.DataFrame, colors: dict[str, str], bench_name: str, focus: Optional[str] = None) -> go.Figure:
    """Grouped bars: return in each calendar year, one bar per fund + benchmark."""
    fig = go.Figure()
    x = [str(y) for y in cal.index]
    for col in cal.columns:
        is_bench = col == bench_name
        _, opacity = _style(col, is_bench, focus)
        fig.add_trace(go.Bar(
            x=x, y=cal[col].values, name=_label(col, is_bench), opacity=opacity,
            marker=dict(color=BENCH_COLOR if is_bench else colors.get(col, BENCH_COLOR), line=dict(width=0),
                        cornerradius=3),
            hovertemplate=f"{_short(col, 30)}: %{{y:.1%}}<extra></extra>",
        ))
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.08)
    fig = _layout(fig, "Calendar-year return", ".0%", time_axis=False)
    fig.update_xaxes(type="category", showspikes=False)
    return fig


def sip_chart(timelines: dict[str, pd.DataFrame], colors: dict[str, str], bench_name: str,
              focus: Optional[str] = None) -> go.Figure:
    """Amount invested (light dotted step line) vs portfolio value per fund, in Rs lakh (1 lakh = 1,00,000)."""
    lakh = 1e5
    fig = go.Figure()
    longest = max(timelines.values(), key=len)
    fig.add_trace(go.Scatter(
        x=longest.index, y=longest["Invested"] / lakh, mode="lines", name="Amount invested",
        line=dict(color=INVESTED_COLOR, width=1.5, dash="dot", shape="hv"), opacity=0.8,
        hovertemplate="Invested: Rs %{y:.2f} L<extra></extra>",
    ))
    for name, tl in timelines.items():
        is_bench = name == bench_name
        color = BENCH_COLOR if is_bench else colors.get(name, BENCH_COLOR)
        fig.add_trace(_line(name, tl["Value"], color, is_bench, ".2f", focus, scale=lakh, prefix="Rs ", suffix=" L"))
    return _layout(fig, "Value (Rs lakh)", ".1f")


def _alpha(hex_color: str, alpha: float) -> str:
    """'#rrggbb' -> 'rgba(r,g,b,alpha)' for translucent fills."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"
