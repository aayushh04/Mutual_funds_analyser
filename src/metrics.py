"""Return and risk calculations on NAV series.

Conventions
-----------
- A NAV series is a pandas Series of floats indexed by date, oldest first.
- Every return/ratio is a plain decimal: 0.1487 means 14.87%. The UI turns
  decimals into percentages for display.
- None means "not available" (for example, too little history). The UI shows
  that as "n/a".
- 252 = trading days in a year (used to annualise daily numbers).
  365 = calendar days in a year (used to annualise using real dates).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

TRADING_DAYS = 252
DAYS_PER_YEAR = 365
PERIOD_YEARS = {"1Y": 1, "3Y": 3, "5Y": 5, "10Y": 10}
# A period's start date often falls on a weekend or holiday. If a fund's first NAV
# is within this many days of the requested start, we still treat it as covering the period.
START_TOLERANCE_DAYS = 7


# ---------------------------------------------------------------------------
# Basic returns
# ---------------------------------------------------------------------------

def daily_returns(nav: pd.Series) -> pd.Series:
    """% change in NAV from one NAV date to the next (0.01 = +1% that day)."""
    return nav.pct_change().dropna()


def absolute_return(nav: pd.Series) -> Optional[float]:
    """Total % gain from the first to the last NAV, ignoring how long it took."""
    if len(nav) < 2:
        return None
    return float(nav.iloc[-1] / nav.iloc[0] - 1)


def days_between(nav: pd.Series) -> int:
    """Calendar days between the first and last NAV dates."""
    if len(nav) < 2:
        return 0
    return int((nav.index[-1] - nav.index[0]).days)


def cagr(nav: pd.Series, min_days: int = DAYS_PER_YEAR) -> Optional[float]:
    """Compound Annual Growth Rate = (end NAV / start NAV)^(365 / days) - 1.

    The steady yearly growth rate that would turn the start NAV into the end
    NAV. Returns None for periods shorter than `min_days`, because
    annualising a few months of returns gives misleadingly huge or tiny numbers.
    """
    days = days_between(nav)
    if days <= 0 or days < min_days:
        return None
    return float((nav.iloc[-1] / nav.iloc[0]) ** (DAYS_PER_YEAR / days) - 1)


# ---------------------------------------------------------------------------
# Risk
# ---------------------------------------------------------------------------

def annualised_volatility(nav: pd.Series) -> Optional[float]:
    """Standard deviation of daily returns x sqrt(252).

    How much the fund's value jumps around in a typical year. Higher = bumpier.
    sqrt(252) scales daily to yearly, because variance grows with time.
    """
    rets = daily_returns(nav)
    if len(rets) < 2:
        return None
    return float(rets.std(ddof=1) * np.sqrt(TRADING_DAYS))


def downside_deviation(nav: pd.Series) -> Optional[float]:
    """Annualised volatility counting only the bad days.

    Positive daily returns are replaced by 0, so only falls add to the number:
    sqrt(mean(min(r, 0)^2)) x sqrt(252). Investors don't mind upside swings,
    so this is a fairer "risk" measure for Sortino.
    """
    rets = daily_returns(nav)
    if len(rets) < 2:
        return None
    downside = np.minimum(rets.to_numpy(), 0.0)
    return float(np.sqrt(np.mean(downside**2)) * np.sqrt(TRADING_DAYS))


def sharpe_ratio(cagr_value: Optional[float], volatility: Optional[float], rf: float) -> Optional[float]:
    """(CAGR - risk-free rate) / volatility: extra return earned per unit of total risk."""
    if cagr_value is None or not volatility:
        return None
    return float((cagr_value - rf) / volatility)


def sortino_ratio(cagr_value: Optional[float], downside_dev: Optional[float], rf: float) -> Optional[float]:
    """(CAGR - risk-free rate) / downside deviation: extra return per unit of *downside* risk."""
    if cagr_value is None or not downside_dev:
        return None
    return float((cagr_value - rf) / downside_dev)


def drawdown_series(nav: pd.Series) -> pd.Series:
    """How far below its previous highest NAV the fund is on each day (0 to -1)."""
    return nav / nav.cummax() - 1


@dataclass(frozen=True)
class Drawdown:
    """The worst peak-to-trough fall in a NAV series."""

    max_drawdown: float                       # e.g. -0.25 for a 25% fall
    peak_date: pd.Timestamp                   # date of the high before the fall
    trough_date: pd.Timestamp                 # date of the lowest point
    recovery_date: Optional[pd.Timestamp]     # first date back at the old high, or None


def max_drawdown(nav: pd.Series) -> Optional[Drawdown]:
    """Find the largest % fall from a peak, with its peak, trough and recovery dates."""
    if len(nav) < 2:
        return None
    dd = drawdown_series(nav)
    trough_date = dd.idxmin()
    peak_value = nav.loc[:trough_date].max()
    peak_date = nav.loc[:trough_date].idxmax()
    after = nav.loc[trough_date:]
    recovered = after[after >= peak_value]
    recovery_date = recovered.index[0] if not recovered.empty and dd.min() < 0 else None
    return Drawdown(float(dd.min()), peak_date, trough_date, recovery_date)


def rolling_volatility(nav: pd.Series, window: int = TRADING_DAYS) -> pd.Series:
    """Annualised volatility over the trailing `window` NAV days (default about 1 year)."""
    return (daily_returns(nav).rolling(window).std(ddof=1) * np.sqrt(TRADING_DAYS)).dropna()


# ---------------------------------------------------------------------------
# Market comparison
# ---------------------------------------------------------------------------

def beta(fund_nav: pd.Series, bench_nav: pd.Series) -> Optional[float]:
    """cov(fund, benchmark) / var(benchmark), on daily returns for dates both have.

    Beta 1.2 means: when the market moves 1%, this fund tended to move 1.2%.
    Below 1 = less sensitive to market swings than the index.
    """
    both = pd.concat({"f": fund_nav, "b": bench_nav}, axis=1, join="inner").dropna()
    rets = both.pct_change().dropna()
    if len(rets) < 20:  # too few days for a meaningful estimate
        return None
    var_b = rets["b"].var(ddof=1)
    if var_b == 0:
        return None
    return float(rets["f"].cov(rets["b"]) / var_b)


def jensens_alpha(
    fund_cagr: Optional[float], bench_cagr: Optional[float], beta_value: Optional[float], rf: float
) -> Optional[float]:
    """Fund CAGR - [rf + beta x (benchmark CAGR - rf)].

    The bracket is the return the fund "should" have earned for the market risk
    it took (CAPM). Alpha is what the manager added (+) or lost (-) beyond that.
    """
    if fund_cagr is None or bench_cagr is None or beta_value is None:
        return None
    return float(fund_cagr - (rf + beta_value * (bench_cagr - rf)))


def common_window(a: pd.Series, b: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Trim two NAV series to the date range both cover."""
    start = max(a.index[0], b.index[0])
    end = min(a.index[-1], b.index[-1])
    return a.loc[start:end], b.loc[start:end]


# ---------------------------------------------------------------------------
# Periods
# ---------------------------------------------------------------------------

def period_start(end: pd.Timestamp, period: str) -> Optional[pd.Timestamp]:
    """Start date for a named period ending on `end`. None for 'Since inception'."""
    if period in PERIOD_YEARS:
        return end - pd.DateOffset(years=PERIOD_YEARS[period])
    return None


def slice_nav(nav: pd.Series, start: Optional[pd.Timestamp], end: pd.Timestamp) -> Optional[pd.Series]:
    """Cut a NAV series to [start, end].

    The start NAV is the last one on or before `start` (the NAV you'd have
    bought at). Returns None if the fund started after `start` (+ a few days'
    tolerance), i.e. its history is shorter than the period.
    """
    nav = nav.loc[:end]
    if nav.empty:
        return None
    if start is None:  # since inception
        return nav if len(nav) >= 2 else None
    if nav.index[0] > start + pd.Timedelta(days=START_TOLERANCE_DAYS):
        return None
    before = nav.loc[:start]
    first_date = before.index[-1] if not before.empty else nav.index[0]
    sliced = nav.loc[first_date:]
    return sliced if len(sliced) >= 2 else None


# ---------------------------------------------------------------------------
# Metrics table
# ---------------------------------------------------------------------------

METRIC_ROWS = [
    "Absolute return (%)",
    "CAGR (%)",
    "Volatility (%)",
    "Sharpe ratio",
    "Sortino ratio",
    "Max drawdown (%)",
    "Drawdown peak",
    "Drawdown trough",
    "Recovered on",
    "Beta",
    "Alpha (%)",
]
# For highlighting the best value: "max" = higher is better, "min" = lower is better.
BEST_RULE = {
    "Absolute return (%)": "max",
    "CAGR (%)": "max",
    "Volatility (%)": "min",
    "Sharpe ratio": "max",
    "Sortino ratio": "max",
    "Max drawdown (%)": "max",  # -10% is better than -30%
    "Alpha (%)": "max",
}


def _pct(x: Optional[float]) -> Optional[float]:
    return None if x is None else round(x * 100, 2)


def _rnd(x: Optional[float]) -> Optional[float]:
    return None if x is None else round(x, 2)


def _date(d: Optional[pd.Timestamp]) -> Optional[str]:
    return None if d is None else d.strftime("%d %b %Y")


def fund_metrics(nav: Optional[pd.Series], bench_nav: Optional[pd.Series], rf: float) -> dict[str, object]:
    """All metric rows for one fund over an already-sliced period.

    `nav` None means the fund doesn't cover the period: every row is None.
    Beta and alpha use only the dates the fund and benchmark both cover.
    """
    if nav is None:
        return {row: None for row in METRIC_ROWS}
    fund_cagr = cagr(nav)
    vol = annualised_volatility(nav)
    dd = max_drawdown(nav)
    b = alpha = None
    if bench_nav is not None and len(bench_nav) >= 2:
        f_win, b_win = common_window(nav, bench_nav)
        b = beta(f_win, b_win)
        alpha = jensens_alpha(cagr(f_win), cagr(b_win), b, rf)
    recovered = None
    if dd is not None:
        recovered = _date(dd.recovery_date) if dd.recovery_date is not None else "Not recovered"
    return {
        "Absolute return (%)": _pct(absolute_return(nav)),
        "CAGR (%)": _pct(fund_cagr),
        "Volatility (%)": _pct(vol),
        "Sharpe ratio": _rnd(sharpe_ratio(fund_cagr, vol, rf)),
        "Sortino ratio": _rnd(sortino_ratio(fund_cagr, downside_deviation(nav), rf)),
        "Max drawdown (%)": _pct(dd.max_drawdown) if dd else None,
        "Drawdown peak": _date(dd.peak_date) if dd else None,
        "Drawdown trough": _date(dd.trough_date) if dd else None,
        "Recovered on": recovered,
        "Beta": _rnd(b),
        "Alpha (%)": _pct(alpha),
    }


def metrics_table(
    sliced: dict[str, Optional[pd.Series]], bench_name: str, bench_nav: Optional[pd.Series], rf: float
) -> pd.DataFrame:
    """One column per fund plus the benchmark, one row per metric."""
    cols = {name: fund_metrics(nav, bench_nav, rf) for name, nav in sliced.items()}
    cols[bench_name] = fund_metrics(bench_nav, bench_nav, rf)
    return pd.DataFrame(cols, index=METRIC_ROWS)


def best_columns(table: pd.DataFrame, fund_cols: list[str]) -> dict[str, list[str]]:
    """For each 'better/worse' row, which fund column(s) hold the best value.

    Only funds compete; the benchmark is the yardstick. Beta and the dates
    have no 'best', so they are skipped.
    """
    best: dict[str, list[str]] = {}
    for row, rule in BEST_RULE.items():
        values = pd.to_numeric(table.loc[row, fund_cols], errors="coerce").dropna()
        if len(values) < 2:
            continue
        target = values.max() if rule == "max" else values.min()
        best[row] = list(values[values == target].index)
    return best


# ---------------------------------------------------------------------------
# Growth, rolling and calendar returns
# ---------------------------------------------------------------------------

def growth_of_investment(navs: pd.DataFrame, amount: float = 10_000) -> pd.DataFrame:
    """Value of `amount` invested in each column on the first date where all have a NAV."""
    df = navs.ffill().dropna()
    if df.empty:
        return df
    return df / df.iloc[0] * amount


def rolling_cagr(nav: pd.Series, years: int) -> pd.Series:
    """CAGR for every possible `years`-long holding period, indexed by start date.

    For each start date, the end NAV is the first NAV on or after
    start + `years`. Each result answers: "if I had invested on this day and
    held for N years, what yearly return would I have earned?"
    """
    if len(nav) < 2:
        return pd.Series(dtype=float)
    dates = nav.index
    targets = dates + pd.DateOffset(years=years)
    end_pos = dates.searchsorted(targets, side="left")
    valid = end_pos < len(dates)
    if not valid.any():
        return pd.Series(dtype=float)
    start_idx = np.flatnonzero(valid)
    end_idx = end_pos[valid]
    start_nav = nav.to_numpy()[start_idx]
    end_nav = nav.to_numpy()[end_idx]
    days = (dates[end_idx] - dates[start_idx]).days.to_numpy()
    values = (end_nav / start_nav) ** (DAYS_PER_YEAR / days) - 1
    return pd.Series(values, index=dates[start_idx], name=f"{years}Y rolling CAGR")


def rolling_summary(rolling: dict[str, pd.Series], bench_rolling: pd.Series) -> pd.DataFrame:
    """Min / median / max rolling CAGR, % positive, and % of periods beating the benchmark.

    The benchmark comparison uses only start dates both series share.
    """
    rows = {}
    for name, series in rolling.items():
        if series.empty:
            rows[name] = {k: None for k in ("Minimum (%)", "Median (%)", "Maximum (%)", "Positive (%)", "Beat benchmark (%)", "Periods")}
            continue
        both = pd.concat({"f": series, "b": bench_rolling}, axis=1, join="inner").dropna()
        beat = float((both["f"] > both["b"]).mean() * 100) if not both.empty else None
        rows[name] = {
            "Minimum (%)": round(series.min() * 100, 2),
            "Median (%)": round(series.median() * 100, 2),
            "Maximum (%)": round(series.max() * 100, 2),
            "Positive (%)": round(float((series > 0).mean() * 100), 1),
            "Beat benchmark (%)": None if beat is None else round(beat, 1),
            "Periods": int(len(series)),
        }
    return pd.DataFrame(rows).T


def calendar_year_returns(nav: pd.Series) -> pd.Series:
    """Return in each calendar year, from the last NAV of the previous year to the last NAV of this year.

    A fund's first year is skipped when there is no NAV from the year before,
    because a part-year return isn't comparable with a full year.
    The current year is year-to-date (the UI labels it YTD).
    """
    if len(nav) < 2:
        return pd.Series(dtype=float)
    year_end = nav.groupby(nav.index.year).last()
    returns = year_end.pct_change().dropna()
    returns.index.name = "year"
    return returns


# ---------------------------------------------------------------------------
# Rating against the benchmark (research-note style, computed, never opinion)
# ---------------------------------------------------------------------------

def rating(fund_cagr: Optional[float], bench_cagr: Optional[float], alpha: Optional[float]) -> str:
    """Rate a fund against its benchmark the way a research note rates a stock.

    OUTPERFORM: higher CAGR than the benchmark AND positive Jensen's alpha
        (it beat the index even after allowing for the market risk it took).
    UNDERPERFORM: lower CAGR AND negative alpha.
    IN-LINE: anything in between (the two signals disagree, or are both zero).
    NOT RATED: not enough history (CAGR or alpha unavailable, e.g. under a year).
    Inputs can be decimals or percentages, as long as they use the same unit.
    """
    if fund_cagr is None or bench_cagr is None or alpha is None:
        return "NOT RATED"
    if fund_cagr > bench_cagr and alpha > 0:
        return "OUTPERFORM"
    if fund_cagr < bench_cagr and alpha < 0:
        return "UNDERPERFORM"
    return "IN-LINE"


# ---------------------------------------------------------------------------
# Leaderboard: best trailing CAGR in a group of funds
# ---------------------------------------------------------------------------

def leaderboard(
    navs: dict[str, pd.Series], years: int, end: pd.Timestamp, rf: float, top: int = 5
) -> tuple[pd.DataFrame, int]:
    """Rank funds by trailing CAGR over the last `years` years ending on `end`.

    Only funds whose history covers the whole window compete (no annualising a
    short history). Volatility, Sharpe and worst fall ride along so a high
    return can be judged against the risk taken to earn it.
    Returns (top rows, number of funds that qualified).
    """
    start = end - pd.DateOffset(years=years)
    rows = []
    for name, nav in navs.items():
        window = slice_nav(nav, start, end)
        if window is None:
            continue
        growth = cagr(window)
        if growth is None:
            continue
        vol = annualised_volatility(window)
        dd = max_drawdown(window)
        rows.append({"Fund": name, "CAGR": growth, "Volatility": vol, "Sharpe": sharpe_ratio(growth, vol, rf),
                     "Worst fall": dd.max_drawdown if dd else None})
    if not rows:
        return pd.DataFrame(columns=["Fund", "CAGR", "Volatility", "Sharpe", "Worst fall"]), 0
    ranked = pd.DataFrame(rows).sort_values("CAGR", ascending=False, kind="stable").reset_index(drop=True)
    return ranked.head(top), len(ranked)
