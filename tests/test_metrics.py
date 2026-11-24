"""Tests for src/metrics.py, including the known answers from the project brief."""

import numpy as np
import pandas as pd
import pytest

from src import metrics as m


def make_nav(values, start="2020-01-01", freq="D"):
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq=freq), dtype=float)


# ---------- CAGR / returns ----------

def test_cagr_nav_doubles_in_5_years_is_about_14_87_percent():
    nav = pd.Series([100.0, 200.0], index=pd.to_datetime(["2019-01-01", "2024-01-01"]))
    assert m.cagr(nav) == pytest.approx(0.1487, abs=5e-4)  # 2^(1/5) - 1 = 14.87%


def test_cagr_exact_formula_with_365_day_years():
    nav = pd.Series([100.0, 200.0], index=[pd.Timestamp("2019-01-01"), pd.Timestamp("2019-01-01") + pd.Timedelta(days=5 * 365)])
    assert m.cagr(nav) == pytest.approx(2 ** (1 / 5) - 1, rel=1e-12)


def test_cagr_not_shown_under_one_year():
    nav = pd.Series([100.0, 110.0], index=pd.to_datetime(["2024-01-01", "2024-06-01"]))
    assert m.cagr(nav) is None
    assert m.absolute_return(nav) == pytest.approx(0.10)


# ---------- drawdown ----------

def test_max_drawdown_known_answer_minus_25_then_recovered():
    nav = make_nav([100, 120, 90, 130])
    dd = m.max_drawdown(nav)
    assert dd.max_drawdown == pytest.approx(-0.25)
    assert dd.peak_date == nav.index[1]
    assert dd.trough_date == nav.index[2]
    assert dd.recovery_date == nav.index[3]


def test_max_drawdown_not_recovered():
    dd = m.max_drawdown(make_nav([100, 120, 90, 110]))
    assert dd.recovery_date is None


def test_drawdown_series_values():
    assert list(m.drawdown_series(make_nav([100, 120, 90, 130])).round(4)) == [0, 0, -0.25, 0]


# ---------- volatility, Sharpe, Sortino ----------

def test_volatility_of_constant_growth_is_zero():
    nav = make_nav(100 * 1.001 ** np.arange(300))
    assert m.annualised_volatility(nav) == pytest.approx(0, abs=1e-12)


def test_volatility_formula():
    nav = make_nav([100, 102, 99, 101, 100])
    rets = nav.pct_change().dropna()
    assert m.annualised_volatility(nav) == pytest.approx(rets.std(ddof=1) * np.sqrt(252))


def test_downside_deviation_ignores_up_days():
    nav = make_nav([100, 110, 121, 133.1])  # only up days
    assert m.downside_deviation(nav) == 0


def test_sharpe_and_sortino():
    assert m.sharpe_ratio(0.15, 0.20, 0.065) == pytest.approx(0.425)
    assert m.sortino_ratio(0.15, 0.10, 0.065) == pytest.approx(0.85)
    assert m.sharpe_ratio(None, 0.2, 0.065) is None
    assert m.sharpe_ratio(0.15, 0.0, 0.065) is None


# ---------- beta / alpha ----------

def test_beta_of_fund_that_moves_twice_the_benchmark():
    rng = np.random.default_rng(0)
    b_rets = rng.normal(0, 0.01, 500)
    bench = make_nav(100 * np.cumprod(1 + b_rets))
    fund = make_nav(100 * np.cumprod(1 + 2 * b_rets))
    assert m.beta(fund, bench) == pytest.approx(2.0, rel=1e-9)
    assert m.beta(bench, bench) == pytest.approx(1.0)


def test_beta_uses_only_common_dates():
    bench = make_nav(100 * np.cumprod(1 + np.random.default_rng(1).normal(0, 0.01, 100)))
    fund = bench.drop(bench.index[10:15])  # fund missing a few days
    assert m.beta(fund, bench) == pytest.approx(1.0)


def test_jensens_alpha():
    # rf 6.5%, beta 1.2, benchmark 12% -> expected 13.1%; fund earned 15% -> alpha 1.9%
    assert m.jensens_alpha(0.15, 0.12, 1.2, 0.065) == pytest.approx(0.019)


# ---------- periods ----------

def test_slice_returns_none_when_history_too_short():
    nav = make_nav(range(1, 400))  # about 13 months
    end = nav.index[-1]
    assert m.slice_nav(nav, m.period_start(end, "3Y"), end) is None
    assert m.slice_nav(nav, m.period_start(end, "1Y"), end) is not None


def test_slice_starts_at_last_nav_on_or_before_start():
    nav = pd.Series([1.0, 2.0, 3.0], index=pd.to_datetime(["2023-01-02", "2023-01-06", "2024-01-08"]))
    sliced = m.slice_nav(nav, pd.Timestamp("2023-01-04"), pd.Timestamp("2024-01-08"))
    assert sliced.index[0] == pd.Timestamp("2023-01-02")


# ---------- rolling / calendar ----------

def test_rolling_cagr_constant_growth():
    nav = make_nav(100 * (1.10 ** (np.arange(3 * 365) / 365)))
    roll = m.rolling_cagr(nav, 1)
    assert not roll.empty
    assert roll.iloc[0] == pytest.approx(0.10, abs=1e-3)
    assert roll.index[-1] + pd.DateOffset(years=1) <= nav.index[-1]


def test_rolling_cagr_too_short_is_empty():
    assert m.rolling_cagr(make_nav([1, 2, 3]), 1).empty


def test_rolling_summary_beat_benchmark():
    idx = pd.date_range("2020-01-01", periods=4)
    fund = pd.Series([0.10, 0.05, -0.02, 0.20], index=idx)
    bench = pd.Series([0.08, 0.06, -0.05, 0.10], index=idx)
    s = m.rolling_summary({"F": fund}, bench).loc["F"]
    assert s["Positive (%)"] == 75.0
    assert s["Beat benchmark (%)"] == 75.0
    assert s["Median (%)"] == pytest.approx(7.5)


def test_calendar_year_returns_skip_partial_first_year():
    nav = pd.Series([100.0, 110.0, 121.0, 133.1],
                    index=pd.to_datetime(["2021-06-01", "2021-12-31", "2022-12-30", "2023-12-29"]))
    cal = m.calendar_year_returns(nav)
    assert list(cal.index) == [2022, 2023]
    assert cal.loc[2022] == pytest.approx(0.10)


# ---------- table ----------

def test_metrics_table_marks_short_history_as_none_and_picks_best():
    nav_a = make_nav(100 * 1.0005 ** np.arange(800) * (1 + 0.01 * np.sin(np.arange(800))))
    nav_b = make_nav(100 * 1.0002 ** np.arange(800) * (1 + 0.02 * np.sin(np.arange(800))))
    table = m.metrics_table({"A": nav_a, "B": nav_b, "C": None}, "Bench", nav_b, 0.065)
    assert table["C"].isna().all()
    assert table.loc["Beta", "Bench"] == pytest.approx(1.0)
    best = m.best_columns(table, ["A", "B", "C"])
    assert best["CAGR (%)"] == ["A"]
    assert best["Volatility (%)"] == ["A"]
