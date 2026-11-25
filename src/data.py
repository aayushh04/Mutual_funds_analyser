"""Data layer: fetch from mfapi.in, clean NAV history, cache it, align dates.

Finance background
------------------
NAV (Net Asset Value) is the price of one unit of a mutual fund. The fund
house publishes it once per business day:
    NAV = (market value of everything the fund owns - its expenses) / units issued
Every return metric in this project is computed from the daily NAV series.

Design
------
- `fetch_*` functions do the network work and raise `DataError` (a friendly
  message) on failure. They have no Streamlit dependency, so tests can call them.
- `get_*` functions are the cached versions that app.py uses.
  st.cache_data does not cache exceptions, so a failed call is retried next time.
"""

from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Optional

import pandas as pd
import requests
import streamlit as st

BASE_URL = "https://api.mfapi.in/mf"
TIMEOUT = (5, 25)  # (seconds to connect, seconds to wait for data)
RETRIES = 2

# Checked via GET /mf/search?q=UTI Nifty 50 Index on 2026-11-24:
# 120716 -> "UTI Nifty 50 Index Fund - Direct Plan - Growth" (NAV history from Jan 2013).
# Only used as a last resort if the search-based lookup finds nothing.
FALLBACK_BENCHMARK_CODE = 120716

# Words in a scheme name that mean the plan pays out dividends instead of
# reinvesting gains (so it is NOT the Growth option).
_NON_GROWTH_WORDS = ("idcw", "dividend", "bonus", "payout", "reinvest")


class DataError(Exception):
    """A problem getting or reading fund data. The message is safe to show users."""


@dataclass(frozen=True)
class FundHistory:
    """One scheme's details plus its cleaned daily NAV series (oldest first)."""

    scheme_code: int
    scheme_name: str
    fund_house: str
    scheme_category: str
    scheme_type: str
    nav: pd.Series  # index: pd.Timestamp dates, values: float NAV

    @property
    def inception_date(self) -> pd.Timestamp:
        """First NAV date available. Used as a stand-in for the fund's launch date."""
        return self.nav.index[0]

    @property
    def latest_date(self) -> pd.Timestamp:
        """Most recent NAV date."""
        return self.nav.index[-1]


# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------

def _get_json(url: str, params: dict[str, Any] | None = None, retries: int = RETRIES) -> Any:
    """GET a URL and return parsed JSON. Retries briefly, then raises DataError."""
    problem = "an unknown error"
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, timeout=TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.Timeout:
            problem = "the request timed out"
        except requests.ConnectionError:
            problem = "the server could not be reached (check your internet connection)"
        except requests.HTTPError as exc:
            problem = f"the server returned an error (HTTP {exc.response.status_code})"
        except ValueError:  # response body was not valid JSON
            problem = "the server sent a response we could not read"
        if attempt < retries - 1:
            time.sleep(1.0)
    raise DataError(f"Could not load data from mfapi.in: {problem}. Please try again in a minute.")


def fetch_scheme_list() -> pd.DataFrame:
    """Download every scheme (code + name) from mfapi.in.

    Returns a DataFrame with columns `scheme_code` (int) and `scheme_name` (str),
    sorted by name.
    """
    payload = _get_json(BASE_URL)
    if not isinstance(payload, list) or not payload:
        raise DataError("mfapi.in returned an empty scheme list. Please try again later.")
    df = pd.DataFrame(payload).rename(columns={"schemeCode": "scheme_code", "schemeName": "scheme_name"})
    if not {"scheme_code", "scheme_name"} <= set(df.columns):
        raise DataError("mfapi.in changed its scheme list format; the app needs an update.")
    df = df[["scheme_code", "scheme_name"]].dropna()
    df["scheme_name"] = df["scheme_name"].astype(str).str.strip()
    df = df[df["scheme_name"] != ""]
    df["scheme_code"] = df["scheme_code"].astype(int)
    df = df.drop_duplicates(subset="scheme_code")
    return df.sort_values("scheme_name", key=lambda s: s.str.lower()).reset_index(drop=True)


def fetch_nav_history(scheme_code: int) -> FundHistory:
    """Download and clean the full NAV history for one scheme."""
    payload = _get_json(f"{BASE_URL}/{int(scheme_code)}")
    return parse_nav_payload(payload, scheme_code)


# ---------------------------------------------------------------------------
# Cleaning and parsing (pure functions, no network)
# ---------------------------------------------------------------------------

def clean_nav_records(records: list[dict[str, Any]]) -> pd.Series:
    """Turn the API's raw [{"date": "dd-mm-yyyy", "nav": "123.45"}, ...] into a clean Series.

    Steps: parse dates, convert NAV to float, drop blank/zero/unreadable NAVs,
    sort oldest to newest, and drop duplicate dates (keeping the first one the
    API listed, which is the most recent entry).
    """
    if not records:
        return pd.Series(dtype=float, name="nav", index=pd.DatetimeIndex([], name="date"))
    df = pd.DataFrame(records)
    if not {"date", "nav"} <= set(df.columns):
        raise DataError("mfapi.in changed its NAV data format; the app needs an update.")
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce")
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
    df = df.dropna(subset=["date", "nav"])
    df = df[df["nav"] > 0]
    df = df.sort_values("date", kind="stable").drop_duplicates(subset="date", keep="first")
    series = df.set_index("date")["nav"].astype(float)
    series.name = "nav"
    return series


def parse_nav_payload(payload: Any, scheme_code: int) -> FundHistory:
    """Validate one /mf/<code> response and build a FundHistory.

    mfapi.in answers unknown codes with status SUCCESS but an empty `data`
    list, so an empty result is treated as "no such fund".
    """
    if not isinstance(payload, dict) or "data" not in payload:
        raise DataError(f"Unexpected response for scheme {scheme_code}.")
    nav = clean_nav_records(payload.get("data") or [])
    if nav.empty:
        raise DataError(
            f"No NAV history found for scheme code {scheme_code}. "
            "The code may be wrong or the scheme may have closed."
        )
    meta = payload.get("meta") or {}
    return FundHistory(
        scheme_code=int(meta.get("scheme_code") or scheme_code),
        scheme_name=str(meta.get("scheme_name") or f"Scheme {scheme_code}").strip(),
        fund_house=str(meta.get("fund_house") or "Unknown").strip(),
        scheme_category=str(meta.get("scheme_category") or "Unknown").strip(),
        scheme_type=str(meta.get("scheme_type") or "Unknown").strip(),
        nav=nav,
    )


# ---------------------------------------------------------------------------
# Searching
# ---------------------------------------------------------------------------

def is_direct_growth(scheme_name: str) -> bool:
    """True if the name looks like a Direct plan with the Growth option.

    Direct plan: bought straight from the fund house, no distributor commission,
    so a lower expense ratio than the Regular plan.
    Growth option: profits stay invested (NAV grows) instead of being paid out
    as IDCW (dividends). That makes NAV returns the investor's true return.
    This is a name-based check, so it can miss oddly named schemes.
    """
    name = scheme_name.lower()
    return "direct" in name and "growth" in name and not any(w in name for w in _NON_GROWTH_WORDS)


def filter_schemes(
    schemes: pd.DataFrame, query: str, direct_growth_only: bool = True, limit: int = 50
) -> pd.DataFrame:
    """Return schemes whose name contains every word of `query` (any order, any case)."""
    words = [w for w in re.split(r"\s+", query.lower().strip()) if w]
    if not words:
        return schemes.iloc[0:0]
    names = schemes["scheme_name"].str.lower()
    mask = pd.Series(True, index=schemes.index)
    for word in words:
        mask &= names.str.contains(word, regex=False)
    if direct_growth_only:
        mask &= schemes["scheme_name"].map(is_direct_growth)
    return schemes[mask].head(limit).reset_index(drop=True)


def find_default_benchmark(schemes: pd.DataFrame) -> tuple[int, str]:
    """Pick a Nifty 50 index fund (Direct, Growth) to stand in for the Nifty 50 index.

    The free API has no index data, so we use an index fund's NAV as a proxy.
    It tracks the index closely, minus a small expense ratio and tracking error.
    Prefers the UTI fund because it has a long, clean history.
    """
    candidates = filter_schemes(schemes, "nifty 50 index", direct_growth_only=True, limit=500)
    # Keep the plain Nifty 50 only, not "Nifty 500", "Next 50", "Midcap 150 ... 50", etc.
    plain = candidates[candidates["scheme_name"].str.contains(r"nifty\s*50\s+index", case=False, regex=True)]
    plain = plain[~plain["scheme_name"].str.contains(r"next|500|equal|value|momentum|quality", case=False)]
    if plain.empty:
        return FALLBACK_BENCHMARK_CODE, "UTI Nifty 50 Index Fund - Direct Plan - Growth"
    uti = plain[plain["scheme_name"].str.lower().str.startswith("uti")]
    row = (uti if not uti.empty else plain).iloc[0]
    return int(row["scheme_code"]), str(row["scheme_name"])


def find_codes_by_name(schemes: pd.DataFrame, names: list[str]) -> list[int]:
    """Look up scheme codes by exact scheme name (case-insensitive). Unknown names are skipped."""
    lookup = dict(zip(schemes["scheme_name"].str.lower(), schemes["scheme_code"]))
    return [int(lookup[n.lower()]) for n in names if n.lower() in lookup]


# ---------------------------------------------------------------------------
# Category universes (for the Top funds leaderboard)
# ---------------------------------------------------------------------------

# Category -> (name patterns that put a scheme in it, extra words that keep it out).
# mfapi.in's scheme list has names only, so categories are matched by name.
CATEGORIES: dict[str, tuple[list[str], list[str]]] = {
    "Flexi cap": (["flexi cap", "flexicap"], []),
    "Large cap": (["large cap", "largecap", "bluechip"], ["mid", "small"]),
    "Large & mid cap": (["large & mid", "large and mid"], []),
    "Mid cap": (["mid cap", "midcap"], ["large", "small"]),
    "Small cap": (["small cap", "smallcap"], []),
    "ELSS (tax saver)": (["elss", "tax saver", "taxsaver"], []),
    # Hybrid and debt (used by Client fit for shorter horizons and the stable part of a portfolio).
    "Balanced advantage": (["balanced advantage", "dynamic asset allocation"], []),
    "Corporate bond": (["corporate bond"], []),
    "Short duration": (["short duration", "short term"], ["ultra", "gilt", "government"]),
    "Liquid": (["liquid"], ["gilt"]),
}
EQUITY_CATEGORIES = ["Flexi cap", "Large cap", "Large & mid cap", "Mid cap", "Small cap", "ELSS (tax saver)"]
# Passive and overseas schemes would distort an active-fund ranking. Unclaimed-money and segregated
# (bad-debt) portfolios, and closed-ended schemes (fixed term, interval, "series"), can't be bought today.
_NOT_ACTIVE_DOMESTIC = re.compile(r"index|etf|fof|fund of fund|nifty|sensex|bse|\bus\b|global|international|nasdaq"
                                  r"|unclaimed|segregated|fixed term|fixed maturity|\bftp\b|\bfmp\b|interval|series",
                                  re.IGNORECASE)


def category_universe(schemes: pd.DataFrame, category: str) -> pd.DataFrame:
    """Direct-plan, Growth-option, actively managed domestic schemes whose name places them in `category`."""
    include, exclude = CATEGORIES[category]
    names = schemes["scheme_name"]
    lower = names.str.lower()
    mask = lower.str.contains("|".join(map(re.escape, include))) & names.map(is_direct_growth)
    mask &= ~names.str.contains(_NOT_ACTIVE_DOMESTIC)
    for word in exclude:
        mask &= ~lower.str.contains(word, regex=False)
    return schemes[mask].reset_index(drop=True)


def live_navs(cat_funds: dict[int, FundHistory], max_gap_days: int = 10
              ) -> tuple[dict[str, pd.Series], pd.Timestamp, dict[str, int]]:
    """Keep funds still publishing NAVs (closed or merged funds stop), cut to a common latest date.

    Returns ({scheme name: NAV series}, latest date, {scheme name: scheme code}).
    """
    latest = max(f.latest_date for f in cat_funds.values())
    live = {f.scheme_name: f.nav.loc[:latest] for f in cat_funds.values()
            if f.latest_date >= latest - pd.Timedelta(days=max_gap_days)}
    codes = {f.scheme_name: code for code, f in cat_funds.items()}
    return live, latest, codes


def fetch_many(codes: list[int], workers: int = 8) -> dict[int, FundHistory]:
    """Download several NAV histories in parallel; schemes that fail or have no data are skipped."""
    def one(code: int) -> Optional[FundHistory]:
        try:
            return fetch_nav_history(code)
        except DataError:
            return None

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(one, codes))
    return {code: fund for code, fund in zip(codes, results) if fund is not None}


# ---------------------------------------------------------------------------
# Aligning several funds on the same dates
# ---------------------------------------------------------------------------

def align_navs(series_by_name: dict[str, pd.Series], how: str = "inner") -> pd.DataFrame:
    """Put several NAV series side by side, one column each.

    how="inner": keep only dates where every fund has a NAV. Use this for beta
        and other comparisons, which need same-day returns.
    how="ffill": keep all dates and carry the last known NAV forward over gaps.
        Dates before a fund existed stay empty (NaN). Use this for charts.
    """
    if not series_by_name:
        return pd.DataFrame()
    if how not in ("inner", "ffill"):
        raise ValueError("how must be 'inner' or 'ffill'")
    df = pd.concat(series_by_name, axis=1, join="inner" if how == "inner" else "outer").sort_index()
    if how == "ffill":
        df = df.ffill()
    return df


# ---------------------------------------------------------------------------
# Cached versions used by the Streamlit app
# ---------------------------------------------------------------------------

@st.cache_data(ttl=24 * 3600, show_spinner="Loading the list of all mutual fund schemes...")
def get_scheme_list() -> pd.DataFrame:
    """Cached for 24 hours: the scheme list rarely changes."""
    return fetch_scheme_list()


@st.cache_data(ttl=6 * 3600, show_spinner="Fetching NAV history...")
def get_nav_history(scheme_code: int) -> FundHistory:
    """Cached for 6 hours: NAVs update once a day, in the evening."""
    return fetch_nav_history(scheme_code)


@st.cache_data(ttl=6 * 3600, show_spinner="Downloading every fund in this category...")
def get_category_funds(category: str) -> dict[int, FundHistory]:
    """Cached for 6 hours: NAV history of every scheme in a category (about 40 to 55 funds)."""
    codes = category_universe(get_scheme_list(), category)["scheme_code"].astype(int).tolist()
    return fetch_many(codes)


def search_schemes(query: str, direct_growth_only: bool = True, limit: int = 50) -> pd.DataFrame:
    """Search the cached scheme list. Raises DataError if the list can't be loaded."""
    return filter_schemes(get_scheme_list(), query, direct_growth_only, limit)


# ---------------------------------------------------------------------------
# Printed sample: python -m src.data
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        all_schemes = fetch_scheme_list()
        print(f"Schemes on mfapi.in: {len(all_schemes):,}\n")

        print('Search "parag parikh flexi cap" (Direct + Growth only):')
        print(filter_schemes(all_schemes, "parag parikh flexi cap").to_string(index=False), "\n")

        bench_code, bench_name = find_default_benchmark(all_schemes)
        print(f"Default benchmark: {bench_code} - {bench_name}\n")

        fund = fetch_nav_history(bench_code)
        print(f"Fund house : {fund.fund_house}")
        print(f"Category   : {fund.scheme_category}")
        print(f"Inception  : {fund.inception_date:%d %b %Y} (first NAV date)")
        print(f"Latest NAV : {fund.nav.iloc[-1]:.4f} on {fund.latest_date:%d %b %Y}")
        print(f"NAV rows   : {len(fund.nav):,}\n")
        print("First 3 rows:\n", fund.nav.head(3).to_string(), "\n")
        print("Last 3 rows:\n", fund.nav.tail(3).to_string())
    except DataError as err:
        print(f"Error: {err}")
