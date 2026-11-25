"""Tests for src/advisor.py: profile caps, allocation, categories and the fit score."""

import numpy as np
import pandas as pd
import pytest

from src.advisor import (
    GOALS,
    RISK_LEVELS,
    build_plan,
    effective_risk,
    horizon_bucket,
    investment_notes,
    lookback_years,
    score_funds,
    split_amount,
)


def test_split_amount_known_answer():
    assert split_amount(10_000, [0.35, 0.35, 0.30]) == [3_500, 3_500, 3_000]


def test_split_amount_always_adds_up():
    # 36% / 27% / 27% / 10% of 7,777 doesn't round cleanly; the difference goes to the biggest share.
    parts = split_amount(7_777, [0.36, 0.27, 0.27, 0.10])
    assert sum(parts) == 7_777 and parts[1:] == [2_100, 2_100, 800]
    assert split_amount(0, [0.5, 0.5]) == [0, 0]


def test_investment_notes_flag_minimums_and_suggest_stp():
    plan = build_plan("Aggressive", "Retirement", 10)          # 36 / 27 / 27 / 10
    weights = [s.weight for s in plan.sleeves]
    small = investment_notes(plan, split_amount(1_000, weights), [], 0)
    assert any("SIP minimum" in n for n in small)
    lump = split_amount(5_00_000, weights)
    assert any("STP" in n for n in investment_notes(plan, [], lump, 5_00_000))
    assert investment_notes(plan, split_amount(20_000, weights), [], 0) == []


@pytest.mark.parametrize("years, bucket", [(1, 0), (2, 1), (3, 1), (4, 2), (5, 2), (6, 3), (7, 3), (8, 4), (30, 4)])
def test_horizon_bucket(years, bucket):
    assert horizon_bucket(years) == bucket


@pytest.mark.parametrize("risk", RISK_LEVELS)
@pytest.mark.parametrize("goal", list(GOALS))
@pytest.mark.parametrize("years", [1, 2, 4, 6, 10, 25])
def test_weights_always_add_up_to_one(risk, goal, years):
    plan = build_plan(risk, goal, years)
    assert sum(s.weight for s in plan.sleeves) == pytest.approx(1.0)
    assert all(s.weight > 0 for s in plan.sleeves)


def test_aggressive_long_horizon_spreads_across_sizes():
    plan = build_plan("Aggressive", "Retirement", 10)
    weights = {s.category: round(s.weight, 2) for s in plan.sleeves}
    assert plan.growth == 0.9
    assert weights == {"Flexi cap": 0.36, "Mid cap": 0.27, "Small cap": 0.27, "Corporate bond": 0.1}


def test_short_horizon_caps_risk_and_keeps_money_liquid():
    plan = build_plan("Aggressive", "Wealth creation", 1)
    assert plan.risk == "Conservative" and plan.growth == 0
    assert [s.category for s in plan.sleeves] == ["Liquid"]
    assert "1-year horizon" in plan.notes[0]


def test_fixed_date_goal_caps_at_moderate():
    risk, notes = effective_risk("Aggressive", "Child's education", 12)
    assert risk == "Moderate" and "can't move" in notes[0]
    assert effective_risk("Conservative", "Child's education", 12) == ("Conservative", [])


def test_emergency_fund_is_all_liquid_whatever_the_appetite():
    plan = build_plan("Aggressive", "Emergency fund", 15)
    assert [(s.category, s.weight) for s in plan.sleeves] == [("Liquid", 1.0)]


def test_tax_saving_uses_elss_only_when_lock_in_fits():
    long = build_plan("Moderate", "Tax saving (80C)", 5)
    assert [s.category for s in long.sleeves] == ["ELSS (tax saver)", "Corporate bond"]
    short = build_plan("Aggressive", "Tax saving (80C)", 2)
    assert "ELSS (tax saver)" not in [s.category for s in short.sleeves]
    assert any("lock-in" in n for n in short.notes)


def test_lookback_is_longer_for_long_horizon_equity():
    plan = build_plan("Moderate", "Retirement", 10)
    growth, stability = plan.sleeves[0], plan.sleeves[-1]
    assert lookback_years(growth, 10) == 5 and lookback_years(stability, 10) == 3
    assert lookback_years(growth, 4) == 3


def _navs():
    """Fund 'Rocket' grows faster but falls 35% on the way (then recovers); 'Steady' grows slower, tiny swings."""
    idx = pd.bdate_range("2021-01-01", "2025-12-31")
    n = len(idx)
    t = np.arange(n) / 252
    rocket = 100 * np.exp(0.20 * t)
    dip = np.concatenate([np.linspace(1, 0.65, 60), np.linspace(0.65, 1, 120)])  # down 35%, back over ~6 months
    rocket[n // 2: n // 2 + len(dip)] *= dip
    rocket = rocket * (1 + 0.004 * np.sin(np.arange(n)))
    steady = 100 * np.exp(0.10 * t) * (1 + 0.0005 * np.sin(np.arange(n)))
    return {"Rocket": pd.Series(rocket, index=idx), "Steady": pd.Series(steady, index=idx)}


def test_fit_score_follows_the_risk_profile():
    navs = _navs()
    end = navs["Rocket"].index[-1]
    aggressive, qualified = score_funds(navs, 3, end, 0.065, "Aggressive")
    conservative, _ = score_funds(navs, 3, end, 0.065, "Conservative")
    assert qualified == 2
    assert aggressive["CAGR"].iloc[0] == aggressive["CAGR"].max()   # sanity: Rocket has the higher CAGR
    assert aggressive["Fund"].iloc[0] == "Rocket"
    assert conservative["Fund"].iloc[0] == "Steady"
    assert conservative["Fit"].between(0, 100).all()


def test_fit_score_with_no_qualifying_fund():
    short = {"New": pd.Series([10.0, 10.1], index=pd.to_datetime(["2025-01-01", "2025-01-02"]))}
    table, qualified = score_funds(short, 3, pd.Timestamp("2025-01-02"), 0.065, "Moderate")
    assert table.empty and qualified == 0
