"""SIP (Systematic Investment Plan) backtest and XIRR.

A SIP invests a fixed amount every month. Each instalment buys
amount / NAV units, so you automatically buy more units when NAV is low and
fewer when it is high (rupee-cost averaging).

Simplifications (say these in an interview): no stamp duty (0.005%), no exit
load or tax, and units are not rounded to 3 decimals as registrars do.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional, Sequence

import pandas as pd

DAYS_PER_YEAR = 365.0


# ---------------------------------------------------------------------------
# XIRR
# ---------------------------------------------------------------------------

def xnpv(rate: float, cashflows: Sequence[tuple[pd.Timestamp, float]]) -> float:
    """Net present value of dated cash flows at a yearly `rate`.

    Each flow is discounted by (1 + rate)^(days since first flow / 365).
    """
    t0 = cashflows[0][0]
    return sum(cf / (1.0 + rate) ** ((pd.Timestamp(d) - pd.Timestamp(t0)).days / DAYS_PER_YEAR) for d, cf in cashflows)


def xirr(cashflows: Sequence[tuple[pd.Timestamp, float]], tol: float = 1e-9, max_iter: int = 200) -> Optional[float]:
    """The yearly rate that makes the NPV of all cash flows zero, found by bisection.

    Sign convention: money you put in is negative, money you get back (the
    final value) is positive. XIRR is the "true" annual return of a SIP, because
    each instalment is invested for a different length of time.

    Bisection: start with a low rate (NPV > 0) and a high rate (NPV < 0), then
    keep halving the gap, keeping the half where NPV changes sign.
    Returns None if the flows don't have both signs or no answer is found.
    """
    flows = sorted(((pd.Timestamp(d), float(cf)) for d, cf in cashflows), key=lambda x: x[0])
    if len(flows) < 2 or not any(cf < 0 for _, cf in flows) or not any(cf > 0 for _, cf in flows):
        return None
    low, high = -0.9999, 1.0
    f_low = xnpv(low, flows)
    f_high = xnpv(high, flows)
    while f_low * f_high > 0 and high < 1e6:  # widen until the root is bracketed
        high *= 2
        f_high = xnpv(high, flows)
    if f_low * f_high > 0:
        return None
    for _ in range(max_iter):
        mid = (low + high) / 2
        f_mid = xnpv(mid, flows)
        if abs(f_mid) < tol or (high - low) / 2 < tol:
            return mid
        if f_low * f_mid < 0:
            high, f_high = mid, f_mid
        else:
            low, f_low = mid, f_mid
    return (low + high) / 2


# ---------------------------------------------------------------------------
# SIP schedule and backtest
# ---------------------------------------------------------------------------

def sip_schedule(start: pd.Timestamp, end: pd.Timestamp, sip_day: int) -> list[pd.Timestamp]:
    """Planned SIP dates: day `sip_day` (1-28) of every month from `start` to `end`."""
    if not 1 <= sip_day <= 28:
        raise ValueError("SIP day must be between 1 and 28")
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    first = pd.Timestamp(start.year, start.month, sip_day)
    if first < start:
        first += pd.DateOffset(months=1)
    dates = []
    current = first
    while current <= end:
        dates.append(current)
        current += pd.DateOffset(months=1)
    return dates


def instalment_amount(base: float, instalment_no: int, step_up_pct: float) -> float:
    """Amount for the n-th instalment (0-based). It rises by `step_up_pct` every 12 instalments."""
    return base * (1 + step_up_pct / 100) ** (instalment_no // 12)


def average_cost(total_invested: float, total_units: float) -> Optional[float]:
    """Average price paid per unit = total invested / total units."""
    return total_invested / total_units if total_units else None


@dataclass(frozen=True)
class SipResult:
    """Outcome of a SIP backtest for one fund."""

    transactions: pd.DataFrame   # one row per instalment
    timeline: pd.DataFrame       # daily 'Invested' and 'Value', for the chart
    total_invested: float
    total_units: float
    current_value: float
    profit: float
    xirr: Optional[float]
    valuation_date: pd.Timestamp

    @property
    def average_cost(self) -> Optional[float]:
        """Average NAV paid per unit."""
        return average_cost(self.total_invested, self.total_units)


def run_sip(
    nav: pd.Series,
    monthly_amount: float,
    start: pd.Timestamp | date,
    sip_day: int,
    step_up_pct: float = 0.0,
    end: pd.Timestamp | date | None = None,
) -> Optional[SipResult]:
    """Backtest a monthly SIP on a NAV series.

    On each SIP date, units are bought at that day's NAV, or at the next
    available NAV date if the market was closed. The portfolio is valued at
    the last NAV on or before `end`. If `start` is before the fund existed,
    the SIP starts from the fund's first NAV date.
    Returns None if no instalment falls inside the NAV history.
    """
    if nav.empty:
        return None
    end_ts = pd.Timestamp(end) if end is not None else nav.index[-1]
    nav = nav.loc[:end_ts]
    if nav.empty:
        return None
    start_ts = max(pd.Timestamp(start), nav.index[0])
    dates = nav.index
    rows = []
    for i, planned in enumerate(sip_schedule(start_ts, dates[-1], sip_day)):
        pos = dates.searchsorted(planned, side="left")  # first NAV date on/after planned date
        if pos >= len(dates):
            break
        amount = instalment_amount(monthly_amount, i, step_up_pct)
        price = float(nav.iloc[pos])
        rows.append({"Planned date": planned, "NAV date": dates[pos], "Amount": amount,
                     "NAV": price, "Units": amount / price})
    if not rows:
        return None

    tx = pd.DataFrame(rows)
    tx["Total units"] = tx["Units"].cumsum()
    tx["Total invested"] = tx["Amount"].cumsum()

    # Daily running totals for the chart. Several instalments could land on one NAV date.
    per_day = tx.groupby("NAV date")[["Amount", "Units"]].sum()
    daily = per_day.reindex(dates[dates >= tx["NAV date"].iloc[0]], fill_value=0.0).cumsum()
    timeline = pd.DataFrame({
        "Invested": daily["Amount"],
        "Value": daily["Units"] * nav.loc[daily.index],
    })

    units = float(tx["Units"].sum())
    invested = float(tx["Amount"].sum())
    valuation_date = dates[-1]
    value = units * float(nav.iloc[-1])
    flows = [(d, -a) for d, a in zip(tx["NAV date"], tx["Amount"])] + [(valuation_date, value)]
    return SipResult(tx, timeline, invested, units, value, value - invested, xirr(flows), valuation_date)
