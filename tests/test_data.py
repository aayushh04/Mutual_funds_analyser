"""Tests for src/data.py. No real network calls: requests.get is replaced with fakes."""

import pandas as pd
import pytest
import requests

from src import data
from src.data import (
    DataError,
    align_navs,
    clean_nav_records,
    filter_schemes,
    find_default_benchmark,
    is_direct_growth,
    parse_nav_payload,
)


# ---------- cleaning ----------

def test_clean_sorts_parses_and_drops_bad_rows():
    raw = [  # newest first, like the API
        {"date": "05-01-2024", "nav": "12.50"},
        {"date": "04-01-2024", "nav": "0"},        # zero NAV -> dropped
        {"date": "03-01-2024", "nav": ""},         # blank -> dropped
        {"date": "02-01-2024", "nav": "12.00"},
        {"date": "02-01-2024", "nav": "11.90"},    # duplicate date -> first one kept
        {"date": "bad-date", "nav": "10.00"},      # unreadable date -> dropped
        {"date": "01-01-2024", "nav": "N.A."},     # unreadable NAV -> dropped
    ]
    nav = clean_nav_records(raw)
    assert list(nav.index) == [pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-05")]
    assert list(nav.values) == [12.00, 12.50]
    assert nav.dtype == float


def test_clean_reads_day_first_dates():
    nav = clean_nav_records([{"date": "03-02-2024", "nav": "10"}])
    assert nav.index[0] == pd.Timestamp("2024-02-03")  # 3 Feb, not 2 Mar


def test_clean_empty_records():
    assert clean_nav_records([]).empty


def test_parse_payload_builds_fund_history():
    payload = {
        "meta": {"fund_house": "Test AMC", "scheme_type": "Open Ended Schemes",
                 "scheme_category": "Equity Scheme - Flexi Cap Fund",
                 "scheme_code": 123, "scheme_name": "Test Fund - Direct Plan - Growth"},
        "data": [{"date": "02-01-2024", "nav": "11"}, {"date": "01-01-2024", "nav": "10"}],
        "status": "SUCCESS",
    }
    fund = parse_nav_payload(payload, 123)
    assert fund.fund_house == "Test AMC"
    assert fund.inception_date == pd.Timestamp("2024-01-01")
    assert fund.nav.iloc[-1] == 11


def test_parse_unknown_code_raises_friendly_error():
    # This is what mfapi.in really returns for a code that doesn't exist.
    payload = {"meta": {"fund_house": "", "scheme_code": 0, "scheme_name": ""}, "data": [], "status": "SUCCESS"}
    with pytest.raises(DataError, match="No NAV history"):
        parse_nav_payload(payload, 99999999)


# ---------- network errors ----------

@pytest.fixture
def no_sleep(monkeypatch):
    monkeypatch.setattr(data.time, "sleep", lambda s: None)


def test_timeout_becomes_data_error(monkeypatch, no_sleep):
    def fake_get(*args, **kwargs):
        raise requests.Timeout()
    monkeypatch.setattr(data.requests, "get", fake_get)
    with pytest.raises(DataError, match="timed out"):
        data.fetch_nav_history(120716)


def test_connection_error_becomes_data_error(monkeypatch, no_sleep):
    def fake_get(*args, **kwargs):
        raise requests.ConnectionError()
    monkeypatch.setattr(data.requests, "get", fake_get)
    with pytest.raises(DataError, match="could not be reached"):
        data.fetch_scheme_list()


def test_retry_then_success(monkeypatch, no_sleep):
    calls = {"n": 0}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return [{"schemeCode": 1, "schemeName": "B Fund"}, {"schemeCode": 2, "schemeName": "a fund"}]

    def fake_get(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise requests.Timeout()
        return FakeResponse()

    monkeypatch.setattr(data.requests, "get", fake_get)
    schemes = data.fetch_scheme_list()
    assert calls["n"] == 2
    assert list(schemes["scheme_name"]) == ["a fund", "B Fund"]  # sorted ignoring case


# ---------- search ----------

SCHEMES = pd.DataFrame({
    "scheme_code": [1, 2, 3, 4, 5, 6],
    "scheme_name": [
        "UTI Nifty 50 Index Fund - Direct Plan - Growth",
        "UTI Nifty 50 Index Fund - Direct Plan - IDCW",
        "UTI Nifty 50 Index Fund - Regular Plan - Growth",
        "UTI Nifty Next 50 Index Fund - Direct Plan - Growth",
        "Parag Parikh Flexi Cap Fund - Direct Plan - Growth",
        "UTI Nifty 500 Value 50 Index Fund - Direct Plan - Growth",
    ],
})


@pytest.mark.parametrize("name, expected", [
    ("X Fund - Direct Plan - Growth", True),
    ("X Fund - Direct Plan - IDCW", False),
    ("X Fund - Regular Plan - Growth", False),
    ("X Fund - Direct Plan - Dividend Reinvestment", False),
    ("X Fund Growth Direct", True),
])
def test_is_direct_growth(name, expected):
    assert is_direct_growth(name) is expected


def test_filter_matches_all_words_any_order_any_case():
    result = filter_schemes(SCHEMES, "flexi PARIKH")
    assert list(result["scheme_code"]) == [5]


def test_filter_toggle_off_shows_all_plans():
    assert len(filter_schemes(SCHEMES, "uti nifty 50", direct_growth_only=False)) == 5
    assert len(filter_schemes(SCHEMES, "uti nifty 50", direct_growth_only=True)) == 3


def test_filter_empty_query_returns_nothing():
    assert filter_schemes(SCHEMES, "   ").empty


def test_default_benchmark_is_plain_nifty_50_direct_growth():
    code, name = find_default_benchmark(SCHEMES)
    assert code == 1
    assert name == "UTI Nifty 50 Index Fund - Direct Plan - Growth"


# ---------- aligning ----------

def test_align_inner_keeps_only_common_dates():
    a = pd.Series([1.0, 2.0, 3.0], index=pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]))
    b = pd.Series([10.0, 30.0], index=pd.to_datetime(["2024-01-01", "2024-01-03"]))
    df = align_navs({"A": a, "B": b})
    assert list(df.index) == list(pd.to_datetime(["2024-01-01", "2024-01-03"]))


def test_align_ffill_carries_last_nav_forward():
    a = pd.Series([1.0, 2.0, 3.0], index=pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]))
    b = pd.Series([10.0, 30.0], index=pd.to_datetime(["2024-01-01", "2024-01-03"]))
    df = align_navs({"A": a, "B": b}, how="ffill")
    assert df.loc["2024-01-02", "B"] == 10.0
