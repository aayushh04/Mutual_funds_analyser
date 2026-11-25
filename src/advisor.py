"""Client fit: turn a client's risk appetite, goal and time horizon into a portfolio and a fund shortlist.

The steps follow how an advisor works:
1. Profile   - the risk the plan acts on is the stated risk, capped by the horizon and the goal.
2. Allocate  - how much goes to growth (equity) and how much to stability (debt).
3. Categories - which fund categories fill each part, for this risk and horizon.
4. Select    - inside each category, rank funds by a fit score built from past data.

Everything here is rule-based and explainable on purpose: every number can be traced to a table below.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from src.metrics import leaderboard

RISK_LEVELS = ["Conservative", "Moderate", "Aggressive"]

# Goal -> highest risk level the goal allows (None = no cap).
GOALS: dict[str, str | None] = {
    "Wealth creation": None,
    "Retirement": None,
    "Child's education": "Moderate",      # a fixed date that can't move: avoid the deepest falls
    "Buying a home": "Moderate",
    "Tax saving (80C)": None,
    "Emergency fund": "Conservative",
}
TAX_GOAL = "Tax saving (80C)"
EMERGENCY_GOAL = "Emergency fund"
ELSS = "ELSS (tax saver)"
ELSS_LOCK_IN_YEARS = 3

# Horizon buckets: 1 year | 2-3 | 4-5 | 6-7 | 8+
BUCKET_LABELS = ["up to 1 year", "2 to 3 years", "4 to 5 years", "6 to 7 years", "8 years or more"]
# A short horizon caps risk: there is no time to recover from a fall.
HORIZON_CAP = {0: "Conservative", 1: "Moderate"}

# Share of the portfolio in growth (equity), by risk and horizon bucket.
GROWTH_SHARE = {
    "Conservative": [0.00, 0.10, 0.25, 0.35, 0.40],
    "Moderate":     [0.00, 0.20, 0.45, 0.60, 0.70],
    "Aggressive":   [0.00, 0.30, 0.65, 0.80, 0.90],
}

# Categories that fill the growth part, with their share of it, by (risk, bucket).
_BAF = [("Balanced advantage", 1.0)]
GROWTH_CATEGORIES: dict[tuple[str, int], list[tuple[str, float]]] = {
    ("Conservative", 1): _BAF, ("Moderate", 1): _BAF, ("Aggressive", 1): _BAF,
    ("Conservative", 2): _BAF,
    ("Moderate", 2): [("Large cap", 1.0)],
    ("Aggressive", 2): [("Flexi cap", 0.6), ("Large & mid cap", 0.4)],
    ("Conservative", 3): [("Large cap", 1.0)],
    ("Moderate", 3): [("Flexi cap", 0.6), ("Large cap", 0.4)],
    ("Aggressive", 3): [("Flexi cap", 0.5), ("Mid cap", 0.5)],
    ("Conservative", 4): [("Large cap", 0.6), ("Flexi cap", 0.4)],
    ("Moderate", 4): [("Flexi cap", 0.5), ("Large & mid cap", 0.5)],
    ("Aggressive", 4): [("Flexi cap", 0.4), ("Mid cap", 0.3), ("Small cap", 0.3)],
}
# The stability (debt) part: shorter horizon, shorter bonds.
STABILITY_CATEGORY = {0: "Liquid", 1: "Short duration", 2: "Corporate bond", 3: "Corporate bond", 4: "Corporate bond"}

WHY = {
    "Liquid": "Money that may be needed any day: very low volatility, and withdrawals are usually paid the next working day.",
    "Short duration": "Bonds maturing in about 1 to 3 years: steadier than equity for a goal a few years away.",
    "Corporate bond": "Mostly top-rated company bonds: the steady part of the portfolio.",
    "Balanced advantage": "Moves between equity and debt based on valuations, so its falls are usually smaller than pure equity's.",
    "Large cap": "India's 100 biggest companies: the steadiest part of equity.",
    "Flexi cap": "The manager can invest across company sizes, which makes it a good core holding.",
    "Large & mid cap": "At least 35% each in large and mid caps: more growth, more swing.",
    "Mid cap": "Companies ranked 101 to 250 by size: faster growth, deeper falls.",
    "Small cap": "Companies beyond the top 250: the most growth and the deepest falls; needs 8+ years.",
    ELSS: "Tax deduction under section 80C (old tax regime), a 3-year lock-in, invested in equity.",
}

# Fit-score weights (CAGR, Sharpe, worst fall) per risk level. Conservative cares most about falls.
FIT_WEIGHTS = {
    "Conservative": (0.2, 0.4, 0.4),
    "Moderate":     (0.4, 0.35, 0.25),
    "Aggressive":   (0.6, 0.3, 0.1),
}


@dataclass
class Sleeve:
    """One part of the plan: a fund category and its share of the whole portfolio."""
    category: str
    weight: float
    role: str          # "Growth" or "Stability"
    why: str


@dataclass
class Plan:
    """The client's plan before any fund is picked."""
    stated_risk: str
    risk: str          # the risk the plan acts on, after caps
    goal: str
    years: int
    growth: float      # share in equity / hybrid
    sleeves: list[Sleeve] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def horizon_bucket(years: int) -> int:
    """1 year -> 0, 2-3 -> 1, 4-5 -> 2, 6-7 -> 3, 8+ -> 4."""
    if years <= 1:
        return 0
    if years <= 3:
        return 1
    if years <= 5:
        return 2
    if years <= 7:
        return 3
    return 4


def _lower(a: str, b: str) -> str:
    """The more cautious of two risk levels."""
    return a if RISK_LEVELS.index(a) <= RISK_LEVELS.index(b) else b


def effective_risk(stated: str, goal: str, years: int) -> tuple[str, list[str]]:
    """Stated risk capped by the horizon and the goal, with a plain-English note for each cap applied."""
    risk, notes = stated, []
    cap = HORIZON_CAP.get(horizon_bucket(years))
    if cap and _lower(risk, cap) != risk:
        risk = cap
        notes.append(f"A {years}-year horizon leaves little time to recover from a market fall, "
                     f"so the plan is treated as {cap.lower()}.")
    goal_cap = GOALS.get(goal)
    if goal_cap and _lower(risk, goal_cap) != risk:
        risk = goal_cap
        notes.append(f"{goal} has a date that can't move, so the plan is capped at {goal_cap.lower()}.")
    return risk, notes


def build_plan(stated_risk: str, goal: str, years: int) -> Plan:
    """Profile -> allocation -> categories. Sleeve weights always add up to 1."""
    if goal == EMERGENCY_GOAL:
        plan = Plan(stated_risk, "Conservative", goal, years, 0.0)
        plan.sleeves = [Sleeve("Liquid", 1.0, "Stability", WHY["Liquid"])]
        plan.notes.append("An emergency fund must be available any day, so it stays fully in liquid funds "
                          "whatever the risk appetite.")
        return plan

    risk, notes = effective_risk(stated_risk, goal, years)
    bucket = horizon_bucket(years)
    growth = GROWTH_SHARE[risk][bucket]
    plan = Plan(stated_risk, risk, goal, years, growth, notes=notes)

    if growth > 0:
        categories = GROWTH_CATEGORIES[(risk, bucket)]
        if goal == TAX_GOAL:
            if years >= ELSS_LOCK_IN_YEARS:
                categories = [(ELSS, 1.0)]
            else:
                plan.notes.append(f"ELSS has a {ELSS_LOCK_IN_YEARS}-year lock-in, longer than this horizon, "
                                  "so the tax-saving fund is left out.")
        plan.sleeves += [Sleeve(cat, growth * share, "Growth", WHY[cat]) for cat, share in categories]
    if growth < 1:
        debt = STABILITY_CATEGORY[bucket]
        plan.sleeves.append(Sleeve(debt, 1 - growth, "Stability", WHY[debt]))
    return plan


# Typical scheme minimums (they vary by fund; check the scheme document).
MIN_SIP = 500
MIN_LUMPSUM = 1_000
STP_THRESHOLD = 1_00_000   # lump sums into equity from this size are worth staggering
ROUND_TO = 100


def split_amount(total: float, weights: list[float], step: int = ROUND_TO) -> list[int]:
    """Split `total` by `weights`, each part rounded to `step` rupees.

    The rounding difference goes to the largest share, so the parts always add up to the total.
    Example: Rs 10,000 at 35% / 35% / 30% -> 3,500 / 3,500 / 3,000.
    """
    if total <= 0 or not weights:
        return [0] * len(weights)
    parts = [int(round(total * w / step)) * step for w in weights]
    biggest = max(range(len(weights)), key=lambda i: weights[i])
    parts[biggest] += int(round(total)) - sum(parts)
    return parts


def investment_notes(plan: Plan, monthly_parts: list[int], lump_parts: list[int], lumpsum: float) -> list[str]:
    """Practical warnings for the rupee split: minimums, and staggering a big lump sum into equity."""
    notes = []
    if any(0 < p < MIN_SIP for p in monthly_parts):
        notes.append(f"Some monthly amounts are below Rs {MIN_SIP:,}, a common SIP minimum. Raise the SIP or "
                     "use fewer funds.")
    if any(0 < p < MIN_LUMPSUM for p in lump_parts):
        notes.append(f"Some lump-sum amounts are below Rs {MIN_LUMPSUM:,}, a common minimum for a first investment.")
    equity_lump = sum(p for p, s in zip(lump_parts, plan.sleeves) if s.role == "Growth")
    if lumpsum > 0 and equity_lump >= STP_THRESHOLD:
        notes.append("For the equity part of the lump sum, consider parking it in a liquid fund and moving it in "
                     "over 6 to 12 months through an STP (systematic transfer plan), so it isn't all invested at "
                     "a market peak.")
    return notes


def lookback_years(sleeve: Sleeve, years: int) -> int:
    """How much history to judge funds on: 5 years for long-horizon equity, otherwise 3."""
    return 5 if sleeve.role == "Growth" and years >= 5 else 3


def score_funds(navs: dict[str, pd.Series], lookback: int, end: pd.Timestamp, rf: float,
                risk: str) -> tuple[pd.DataFrame, int]:
    """Rank funds by a 0-100 fit score for this risk level.

    Each fund gets a percentile rank on CAGR, Sharpe and worst fall (a smaller fall ranks higher)
    within its category; the fit score is the weighted average of those ranks, using FIT_WEIGHTS.
    Returns (all qualifying funds best-first, number qualified).
    """
    table, qualified = leaderboard(navs, lookback, end, rf, top=max(len(navs), 1))
    if table.empty:
        return table.assign(Fit=pd.Series(dtype=float)), 0
    w_cagr, w_sharpe, w_fall = FIT_WEIGHTS[risk]
    ranks = {col: pd.to_numeric(table[col], errors="coerce").rank(pct=True).fillna(0)
             for col in ("CAGR", "Sharpe", "Worst fall")}
    table["Fit"] = 100 * (w_cagr * ranks["CAGR"] + w_sharpe * ranks["Sharpe"] + w_fall * ranks["Worst fall"])
    table = table.sort_values(["Fit", "CAGR"], ascending=False, kind="stable").reset_index(drop=True)
    return table, qualified
