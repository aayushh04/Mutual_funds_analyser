"""Tests for src/ui.py: formatting and the research-note blocks."""

import pandas as pd
import pytest

from src.ui import (
    brief_names,
    category_label,
    display_case,
    leaders_sentence,
    fund_ratings,
    headline_html,
    inr,
    leader,
    metrics_table_html,
    pct,
    rating_summary_html,
    short_name,
    thesis_html,
)


@pytest.mark.parametrize("value, expected", [
    (999, "Rs 999"),
    (1000, "Rs 1,000"),
    (300000, "Rs 3,00,000"),
    (452508.4, "Rs 4,52,508"),
    (12345678, "Rs 1,23,45,678"),
    (-71441, "-Rs 71,441"),
    (None, "—"),
])
def test_inr_uses_indian_grouping(value, expected):
    assert inr(value) == expected


def test_pct_and_missing():
    assert pct(0.12345) == "12.35%"
    assert pct(float("nan")) == "—"


def test_short_name_drops_plan_suffix():
    assert short_name("HDFC Flexi Cap Fund - Direct Plan - Growth Option") == "HDFC Flexi Cap Fund"


def _table():
    return pd.DataFrame({
        "A": {"Absolute return (%)": 127.3, "CAGR (%)": 17.8, "Volatility (%)": 12.8, "Sharpe ratio": 0.88,
              "Sortino ratio": 1.26, "Max drawdown (%)": -13.3, "Drawdown peak": "06 Jan 2026",
              "Drawdown trough": "31 Mar 2026", "Recovered on": "03 Aug 2026", "Beta": 0.87, "Alpha (%)": 9.41},
        "B": {"Absolute return (%)": 75.1, "CAGR (%)": 11.8, "Volatility (%)": 11.4, "Sharpe ratio": 0.47,
              "Sortino ratio": 0.67, "Max drawdown (%)": -17.6, "Drawdown peak": "13 Dec 2021",
              "Drawdown trough": "17 Jun 2022", "Recovered on": "27 Apr 2023", "Beta": 0.69, "Alpha (%)": 3.83},
        "N": {"Absolute return (%)": 51.8, "CAGR (%)": 8.7, "Volatility (%)": 13.9, "Sharpe ratio": 0.16,
              "Sortino ratio": 0.22, "Max drawdown (%)": -15.9, "Drawdown peak": "17 Jan 2022",
              "Drawdown trough": "17 Jun 2022", "Recovered on": "01 Nov 2022", "Beta": 1.0, "Alpha (%)": 0.0},
    })


SHORTS = {"A": "Fund A", "B": "Fund B", "N": "Nifty"}


def test_leader_and_ratings():
    t = _table()
    assert leader(t, ["A", "B"]) == "A"
    assert fund_ratings(t, ["A", "B"], "N") == {"A": "OUTPERFORM", "B": "OUTPERFORM"}


def test_headline_names_leader_and_sharpe():
    text = headline_html(_table(), ["A", "B"], SHORTS, "Flexi cap", "5 years")
    assert "Flexi cap comparison: Fund A leads on return and risk-adjusted return" in text


def test_thesis_is_written_from_the_numbers():
    text = thesis_html(_table(), "A", "N", SHORTS, 22726)
    assert "compounded 17.80% a year against 8.70% for Nifty, turning Rs 10,000 into Rs 22,726" in text
    assert "less bumpy than the index" in text and "shallower, -13.30% vs -15.90%" in text
    assert "beta of 0.87" in text and "9.41% a year above" in text


def test_thesis_handles_missing_history():
    empty = _table().copy()
    empty["A"] = None
    assert "Not enough history" in thesis_html(empty, "A", "N", SHORTS, None)


def test_rating_summary_lists_benchmark_last():
    html = rating_summary_html(_table(), ["A", "B"], "N", {"A": "#000", "B": "#111"}, SHORTS)
    assert html.index("Fund B") < html.index("BENCHMARK")
    assert html.count('class="mfa-rin"') == 3 and html.count(">OUTPERFORM<") == 2
    assert "Sharpe" in html and "0.88" in html


def test_rating_summary_puts_leader_first():
    # B is listed first by the user, but A has the higher CAGR with the same rating.
    html = rating_summary_html(_table(), ["B", "A"], "N", {"A": "#000", "B": "#111"}, SHORTS)
    assert html.index("Fund A") < html.index("Fund B")


@pytest.mark.parametrize("raw, expected", [
    ("BANK OF INDIA FLEXI CAP FUND", "Bank of India Flexi Cap Fund"),
    ("ICICI Prudential Flexi Cap fund", "ICICI Prudential Flexi Cap Fund"),
    ("SBI SMALL CAP FUND", "SBI Small Cap Fund"),
    ("360 ONE Flexicap Fund", "360 ONE Flexicap Fund"),
])
def test_display_case(raw, expected):
    assert display_case(raw) == expected


def test_brief_names_drop_shared_words():
    assert brief_names(["Parag Parikh Flexi Cap Fund - Direct Plan - Growth", "HDFC Flexi Cap Fund - Direct Plan - Growth"]) \
        == {"Parag Parikh Flexi Cap Fund - Direct Plan - Growth": "Parag Parikh",
            "HDFC Flexi Cap Fund - Direct Plan - Growth": "HDFC"}
    assert brief_names(["HDFC Flexi Cap Fund"]) == {"HDFC Flexi Cap Fund": "HDFC Flexi Cap"}


def test_plan_sentence_reads_naturally():
    from src.advisor import build_plan
    from src.ui import plan_sentence
    plan = build_plan("Conservative", "Tax saving (80C)", 5)
    text = plan_sentence(plan, [("ELSS (tax saver)", "HDFC ELSS Tax Saver - Direct Plan - Growth"),
                                ("Corporate bond", "DSP Corporate Bond Fund - Direct Plan - Growth")])
    assert ("For a conservative investor saving tax under section 80C over 5 years: 25% in growth funds, "
            "75% in stability (debt) funds.") in text
    assert "HDFC ELSS Tax Saver (ELSS) and DSP Corporate Bond Fund (corporate bond)." in text
    assert "For an emergency fund kept for 1 year: 100% in stability" in plan_sentence(
        build_plan("Moderate", "Emergency fund", 1), [])


def test_leaders_sentence():
    text = leaders_sentence("Flexi cap", {3: "ITI Flexi Cap Fund", 5: "HDFC Flexi Cap Fund", 10: "Quant Flexi Cap Fund"})
    assert ("Quant Flexi Cap Fund leads flexi cap over 10 years, HDFC Flexi Cap Fund over 5 "
            "and ITI Flexi Cap Fund over 3.") in text


@pytest.mark.parametrize("cats, expected", [
    (["Equity Scheme - Flexi Cap Fund", "Equity Scheme - Flexi Cap Fund"], "Flexi cap"),
    (["Equity Scheme - Flexi Cap Fund", "Equity Scheme - Small Cap Fund"], "Fund"),
])
def test_category_label(cats, expected):
    assert category_label(cats) == expected


def test_metrics_table_marks_best_with_hidden_text():
    html = metrics_table_html(_table(), {"CAGR (%)": ["A"]}, {"A": "#000", "B": "#111"}, "N", {})
    assert 'class="mfa-best"' in html and "Best: " in html
    assert 'title="Compound Annual Growth Rate' in html
    assert "Versus benchmark" in html


@pytest.mark.parametrize("raw, expected", [
    ("360 ONE Flexicap Fund - Direct Plan - GROWTH", "360 ONE Flexicap Fund"),
    ("Sundaram Mid Cap Fund Direct Plan - GROWTH", "Sundaram Mid Cap Fund Direct Plan"),
    ("Canara Robeco Large Cap Fund - Direct Plan - Growth Option", "Canara Robeco Large Cap Fund"),
    ("UTI Nifty 50 Index Fund - Direct Plan - Growth", "UTI Nifty 50 Index Fund"),
    ("Some Fund (Direct) Growth", "Some Fund"),
])
def test_short_name_handles_inconsistent_suffixes(raw, expected):
    assert short_name(raw, 80) == expected
