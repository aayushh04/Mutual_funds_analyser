"""Tests for src/sip.py, including the known answers from the project brief."""

import pandas as pd
import pytest

from src.sip import average_cost, instalment_amount, run_sip, sip_schedule, xirr, xnpv


# ---------- XIRR ----------

def test_xirr_simple_one_year_10_percent():
    flows = [(pd.Timestamp("2023-01-01"), -10_000), (pd.Timestamp("2024-01-01"), 11_000)]
    assert xirr(flows) == pytest.approx(0.10, abs=1e-4)  # 365 days apart


def test_xirr_negative_return():
    flows = [(pd.Timestamp("2023-01-01"), -10_000), (pd.Timestamp("2024-01-01"), 9_000)]
    assert xirr(flows) == pytest.approx(-0.10, abs=1e-4)


def test_xirr_multiple_flows_gives_zero_npv():
    flows = [
        (pd.Timestamp("2022-01-05"), -5_000),
        (pd.Timestamp("2022-02-07"), -5_000),
        (pd.Timestamp("2022-03-05"), -5_000),
        (pd.Timestamp("2023-06-30"), 17_200),
    ]
    rate = xirr(flows)
    assert rate is not None
    assert xnpv(rate, flows) == pytest.approx(0, abs=1e-3)


def test_xirr_needs_both_signs():
    assert xirr([(pd.Timestamp("2023-01-01"), -100), (pd.Timestamp("2024-01-01"), -100)]) is None


# ---------- SIP ----------

def test_sip_known_answer_202_5_units_avg_cost_19_75():
    # 4 monthly buys of Rs 1,000 at NAV 20, 25, 16, 20.
    nav = pd.Series([20.0, 25.0, 16.0, 20.0],
                    index=pd.to_datetime(["2024-01-05", "2024-02-05", "2024-03-05", "2024-04-05"]))
    result = run_sip(nav, 1_000, "2024-01-01", sip_day=5)
    assert result.total_units == pytest.approx(202.5)
    assert result.total_invested == pytest.approx(4_000)
    assert result.average_cost == pytest.approx(19.75, abs=0.01)
    assert result.current_value == pytest.approx(202.5 * 20)


def test_sip_buys_on_next_available_nav_date():
    # The 5th is missing (holiday): the buy should happen on the 6th at NAV 11.
    nav = pd.Series([10.0, 11.0, 12.0], index=pd.to_datetime(["2024-01-04", "2024-01-06", "2024-01-08"]))
    result = run_sip(nav, 1_100, "2024-01-01", sip_day=5)
    assert result.transactions.loc[0, "NAV date"] == pd.Timestamp("2024-01-06")
    assert result.total_units == pytest.approx(100)


def test_sip_starts_at_inception_if_start_is_earlier():
    nav = pd.Series([10.0, 10.0], index=pd.to_datetime(["2024-03-01", "2024-04-01"]))
    result = run_sip(nav, 1_000, "2020-01-01", sip_day=1)
    assert result.transactions["NAV date"].iloc[0] == pd.Timestamp("2024-03-01")


def test_step_up_every_12_instalments():
    assert instalment_amount(5_000, 0, 10) == 5_000
    assert instalment_amount(5_000, 11, 10) == 5_000
    assert instalment_amount(5_000, 12, 10) == pytest.approx(5_500)
    assert instalment_amount(5_000, 24, 10) == pytest.approx(6_050)


def test_schedule_skips_day_already_passed():
    dates = sip_schedule(pd.Timestamp("2024-01-10"), pd.Timestamp("2024-03-31"), 5)
    assert dates == list(pd.to_datetime(["2024-02-05", "2024-03-05"]))


def test_schedule_rejects_bad_day():
    with pytest.raises(ValueError):
        sip_schedule(pd.Timestamp("2024-01-01"), pd.Timestamp("2024-03-01"), 31)


def test_average_cost_zero_units():
    assert average_cost(0, 0) is None
