"""Plotly figure builders. Each function takes ready-made data and returns a Figure.

Colour rules: each fund keeps the same colour in every chart (it follows the
fund's position in the selection, not its rank). The benchmark is always a
grey dashed line, so it can be told apart without relying on colour.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

# Validated colour-blind-safe categorical palette (slots 1-4) + neutral benchmark.
FUND_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
BENCH_COLOR = "#6b6a66"
INVESTED_COLOR = "#52514e"
GRID = "#e6e5e0"


def color_map(fund_names: list[str]) -> dict[str, str]:
    """Fixed colour per fund, in selection order."""
    return {name: FUND_COLORS[i % len(FUND_COLORS)] for i, name in enumerate(fund_names)}


def _short(name: str, limit: int = 38) -> str:
    """Shorten long scheme names for legends (full name stays in the hover)."""
    name = name.replace(" - Direct Plan", "").replace(" - Growth Option", "").replace(" - Growth", "")
    return name if len(name) <= limit else name[: limit - 1] + "…"


def _layout(fig: go.Figure, y_title: str, y_format: str = "", height: int = 420) -> go.Figure:
    """Shared, phone-friendly styling: legend under the chart, light grid, hover across series."""
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=16, b=8),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="left", x=0, title=None),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(color="#1b1f24"),
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID)
    fig.update_yaxes(title=y_title, gridcolor=GRID, zerolinecolor="#c9c8c2", tickformat=y_format)
    return fig


def _line(name: str, series: pd.Series, color: str, is_bench: bool, hover_fmt: str) -> go.Scatter:
    return go.Scatter(
        x=series.index, y=series.values, mode="lines", name=_short(name),
        line=dict(color=color, width=2, dash="dash" if is_bench else "solid"),
        hovertemplate=f"{_short(name, 30)}: %{{y:{hover_fmt}}}<extra></extra>",
    )


def line_chart(
    data: pd.DataFrame, colors: dict[str, str], bench_name: str | None,
    y_title: str, y_format: str = "", hover_fmt: str = ",.2f",
) -> go.Figure:
    """Generic multi-series line chart: one column per fund (benchmark dashed grey)."""
    fig = go.Figure()
    for col in data.columns:
        series = data[col].dropna()
        if series.empty:
            continue
        is_bench = col == bench_name
        fig.add_trace(_line(col, series, BENCH_COLOR if is_bench else colors.get(col, BENCH_COLOR), is_bench, hover_fmt))
    return _layout(fig, y_title, y_format)


def growth_chart(growth: pd.DataFrame, colors: dict[str, str], bench_name: str) -> go.Figure:
    """Growth of Rs 10,000 invested on the common start date."""
    return line_chart(growth, colors, bench_name, "Value (Rs)", ",.0f", ",.0f")


def drawdown_chart(drawdowns: pd.DataFrame, colors: dict[str, str], bench_name: str) -> go.Figure:
    """% below the previous peak, over time."""
    return line_chart(drawdowns, colors, bench_name, "Below previous peak", ".0%", ".1%")


def rolling_vol_chart(vols: pd.DataFrame, colors: dict[str, str], bench_name: str) -> go.Figure:
    """Rolling 1-year annualised volatility."""
    return line_chart(vols, colors, bench_name, "1-year volatility", ".0%", ".1%")


def rolling_returns_chart(rolling: pd.DataFrame, colors: dict[str, str], bench_name: str, years: int) -> go.Figure:
    """Rolling CAGR indexed by investment start date."""
    return line_chart(rolling, colors, bench_name, f"{years}Y rolling CAGR", ".0%", ".1%")


def calendar_chart(cal: pd.DataFrame, colors: dict[str, str], bench_name: str) -> go.Figure:
    """Grouped bars: return in each calendar year, one bar per fund + benchmark."""
    fig = go.Figure()
    x = [str(y) for y in cal.index]
    for col in cal.columns:
        is_bench = col == bench_name
        marker = dict(color=BENCH_COLOR if is_bench else colors.get(col, BENCH_COLOR), line=dict(width=0))
        fig.add_trace(go.Bar(
            x=x, y=cal[col].values, name=_short(col), marker=marker,
            hovertemplate=f"{_short(col, 30)}: %{{y:.1%}}<extra></extra>",
        ))
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.08)
    fig = _layout(fig, "Calendar-year return", ".0%")
    fig.update_xaxes(type="category")
    return fig


def sip_chart(timelines: dict[str, pd.DataFrame], colors: dict[str, str], bench_name: str) -> go.Figure:
    """Amount invested (one dark dotted line) vs portfolio value for each fund."""
    fig = go.Figure()
    longest = max(timelines.values(), key=len)
    fig.add_trace(go.Scatter(
        x=longest.index, y=longest["Invested"], mode="lines", name="Amount invested",
        line=dict(color=INVESTED_COLOR, width=2, dash="dot", shape="hv"),
        hovertemplate="Invested: Rs %{y:,.0f}<extra></extra>",
    ))
    for name, tl in timelines.items():
        is_bench = name == bench_name
        fig.add_trace(_line(name, tl["Value"], BENCH_COLOR if is_bench else colors.get(name, BENCH_COLOR), is_bench, ",.0f"))
    return _layout(fig, "Rs", ",.0f")
