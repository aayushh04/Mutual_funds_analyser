"""Mutual Fund Analyser: Streamlit layout only. All calculations live in src/."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src import charts
from src import metrics as m
from src.content import FOOTER, GLOSSARY
from src.data import (
    DataError,
    FundHistory,
    filter_schemes,
    find_codes_by_name,
    find_default_benchmark,
    get_nav_history,
    get_scheme_list,
)
from src.sip import run_sip
from src.ui import metrics_table_html, pct, rupees, short_name

DEFAULT_FUNDS = [
    "Parag Parikh Flexi Cap Fund - Direct Plan - Growth",
    "HDFC Flexi Cap Fund - Direct Plan - Growth Option",
]
PERIODS = ["1Y", "3Y", "5Y", "10Y", "Since inception", "Custom"]

st.set_page_config(page_title="Mutual Fund Analyser", page_icon="📈", layout="wide")


def footer() -> None:
    """Disclaimer shown at the bottom of every page."""
    st.divider()
    st.caption(FOOTER)


# ---------------------------------------------------------------------------
# Scheme list (needed for search and defaults)
# ---------------------------------------------------------------------------
try:
    schemes = get_scheme_list()
except DataError as err:
    st.title("📈 Mutual Fund Analyser")
    st.error(f"{err}")
    footer()
    st.stop()

names = dict(zip(schemes["scheme_code"], schemes["scheme_name"]))
default_bench_code, _ = find_default_benchmark(schemes)
if "funds" not in st.session_state:
    st.session_state.funds = find_codes_by_name(schemes, DEFAULT_FUNDS)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Funds")
    direct_only = st.toggle("Direct plan + Growth option only", value=True,
                            help="Filters search results by scheme name.")
    query = st.text_input("Search funds", placeholder="e.g. axis small cap")
    results = filter_schemes(schemes, query, direct_only) if query.strip() else schemes.iloc[0:0]
    if query.strip() and results.empty:
        st.caption("No matching schemes. Try fewer words, or turn off the Direct + Growth filter.")
    options = list(dict.fromkeys(st.session_state.funds + results["scheme_code"].tolist()))
    st.multiselect("Funds to compare (1 to 4)", options, key="funds", max_selections=4,
                   format_func=lambda c: names.get(c, str(c)),
                   help="Type in the search box above, then pick from this list.")

    st.header("Benchmark")
    bench_query = st.text_input("Search a different benchmark", placeholder="e.g. nifty 100 index")
    bench_results = filter_schemes(schemes, bench_query, direct_only) if bench_query.strip() else schemes.iloc[0:0]
    bench_options = list(dict.fromkeys([default_bench_code] + bench_results["scheme_code"].tolist()))
    bench_code = st.selectbox("Benchmark (index fund NAV used as a proxy for the index)", bench_options,
                              format_func=lambda c: names.get(c, str(c)))

    st.header("Period")
    period = st.selectbox("Analysis period", PERIODS, index=2)
    custom_start = custom_end = None
    if period == "Custom":
        today = pd.Timestamp.today().normalize()
        custom_start = st.date_input("From", value=(today - pd.DateOffset(years=3)).date(), format="DD/MM/YYYY")
        custom_end = st.date_input("To", value=today.date(), format="DD/MM/YYYY")

    st.header("Assumption")
    rf_pct = st.number_input("Risk-free rate (% a year, editable assumption)", min_value=0.0, max_value=20.0,
                             value=6.5, step=0.25, help="Roughly the yield on Indian government T-bills.")
    rf = rf_pct / 100

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
st.title("📈 Mutual Fund Analyser")
st.caption("Compare Indian mutual funds on return, risk and consistency, the way a distributor would.")

if not st.session_state.funds:
    st.info("👈 Search for a fund in the sidebar and add 1 to 4 funds to compare.")
    footer()
    st.stop()

funds: dict[str, FundHistory] = {}
for code in st.session_state.funds:
    try:
        f = get_nav_history(int(code))
        funds[f.scheme_name] = f
    except DataError as err:
        st.warning(f"Skipped {names.get(code, code)}: {err}")
try:
    bench = get_nav_history(int(bench_code))
except DataError as err:
    st.error(f"Could not load the benchmark. {err}")
    footer()
    st.stop()
if not funds:
    st.error("None of the selected funds could be loaded. Please try again or pick other funds.")
    footer()
    st.stop()

bench_name = bench.scheme_name
fund_names = list(funds)
if bench_name in funds:  # same scheme picked as fund and benchmark
    bench_name = bench_name + " "
colors = charts.color_map(fund_names)
shorts = {n: short_name(n) for n in fund_names + [bench_name]}

# Common end date = the latest date every series has a NAV for, so all are compared to the same day.
end = min([f.latest_date for f in funds.values()] + [bench.latest_date])
if period == "Custom":
    start = pd.Timestamp(custom_start)
    end = min(end, pd.Timestamp(custom_end))
    if start >= end:
        st.error("The custom 'From' date must be before the 'To' date (and before the latest NAV date).")
        footer()
        st.stop()
else:
    start = m.period_start(end, period)

sliced = {n: m.slice_nav(f.nav, start, end) for n, f in funds.items()}
bench_sliced = m.slice_nav(bench.nav, start, end)
full = {n: f.nav.loc[:end] for n, f in funds.items()}
full_bench = bench.nav.loc[:end]
too_short = [n for n, s in sliced.items() if s is None]

period_label = "since inception" if period == "Since inception" else (
    f"{start:%d %b %Y} to {end:%d %b %Y}" if start is not None else "")
st.markdown(f"**Period:** {period_label} · **NAVs as of** {end:%d %b %Y} · **Risk-free rate** {rf_pct:.2f}%")
if too_short:
    st.info("Not enough history for this period (shown as n/a): " + ", ".join(shorts[n] for n in too_short))

tab_over, tab_risk, tab_roll, tab_cal, tab_sip, tab_learn = st.tabs(
    ["Overview", "Risk", "Rolling returns", "Calendar year", "SIP backtest", "Learn"]
)

# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------
with tab_over:
    cards = st.columns(len(funds) + 1)
    for col, (name, f) in zip(cards, list(funds.items()) + [(bench_name, bench)]):
        with col.container(border=True):
            tag = " · benchmark" if name == bench_name else ""
            st.markdown(f"**{short_name(f.scheme_name, 60)}**{tag}")
            st.caption(f"{f.fund_house}  \n{f.scheme_category}  \n"
                       f"Inception (first NAV): {f.inception_date:%d %b %Y}  \nScheme code: {f.scheme_code}")

    st.subheader("Key metrics")
    table = m.metrics_table(sliced, bench_name, bench_sliced, rf)
    best = m.best_columns(table, fund_names)
    st.html(metrics_table_html(table, best, colors, bench_name, shorts))
    st.caption("★ = best among the selected funds (benchmark not ranked). Hover or tap ⓘ for an explanation. "
               "CAGR, Sharpe, Sortino and alpha need a period of at least 1 year. "
               "Beta and alpha use dates both the fund and the benchmark cover.")
    st.download_button("Download metrics as CSV", table.to_csv(index_label="Metric").encode("utf-8"),
                       file_name=f"fund_metrics_{period.replace(' ', '_').lower()}_{end:%Y%m%d}.csv",
                       mime="text/csv")

    st.subheader("Growth of Rs 10,000")
    usable = {n: s for n, s in sliced.items() if s is not None}
    if bench_sliced is not None:
        usable[bench_name] = bench_sliced
    growth = m.growth_of_investment(pd.concat(usable, axis=1))
    if growth.empty or len(growth) < 2:
        st.info("Not enough overlapping history to draw this chart.")
    else:
        st.plotly_chart(charts.growth_chart(growth, colors, bench_name), config={"displayModeBar": False})
        st.caption(f"All lines start at Rs 10,000 on {growth.index[0]:%d %b %Y}, the first date every series has a NAV.")

# ---------------------------------------------------------------------------
# Risk
# ---------------------------------------------------------------------------
with tab_risk:
    st.subheader("Drawdown: how far below its last peak")
    dds = {n: m.drawdown_series(s) for n, s in usable.items()}
    if dds:
        st.plotly_chart(charts.drawdown_chart(pd.concat(dds, axis=1), colors, bench_name),
                        config={"displayModeBar": False})
        st.caption("0% means the fund is at a new high. The deepest dip is the maximum drawdown in the Overview table.")
    else:
        st.info("No fund has enough history for this period.")

    st.subheader("Rolling 1-year volatility")
    vol_src = {**full, bench_name: full_bench}
    vols = {}
    for n, s in vol_src.items():
        v = m.rolling_volatility(s)
        if start is not None:
            v = v.loc[start:end]
        if not v.empty:
            vols[n] = v
    if vols:
        st.plotly_chart(charts.rolling_vol_chart(pd.concat(vols, axis=1), colors, bench_name),
                        config={"displayModeBar": False})
        st.caption("Each point is the annualised volatility of the previous ~252 trading days. "
                   "Spikes line up with market stress (e.g. March 2020).")
    else:
        st.info("Rolling volatility needs more than one year of NAV history.")

# ---------------------------------------------------------------------------
# Rolling returns
# ---------------------------------------------------------------------------
with tab_roll:
    window = st.radio("Holding period", ["1Y", "3Y", "5Y"], index=1, horizontal=True)
    years = m.PERIOD_YEARS[window]
    rolling = {n: m.rolling_cagr(s, years) for n, s in full.items()}
    bench_roll = m.rolling_cagr(full_bench, years)
    st.caption("Rolling returns show consistency. Trailing returns depend on today's date.")
    plot = {n: r for n, r in rolling.items() if not r.empty}
    if not bench_roll.empty:
        plot[bench_name] = bench_roll
    if not plot:
        st.info(f"None of the funds has more than {years} years of history.")
    else:
        st.plotly_chart(charts.rolling_returns_chart(pd.concat(plot, axis=1), colors, bench_name, years),
                        config={"displayModeBar": False})
        st.caption(f"Each point: the CAGR you'd have earned investing on that date and holding for {years} years. "
                   "Uses each fund's full history.")
        summary = m.rolling_summary({**rolling, bench_name: bench_roll}, bench_roll)
        summary.loc[bench_name, "Beat benchmark (%)"] = None
        summary.index = [shorts.get(n, n) for n in summary.index]
        st.dataframe(summary, column_config={
            "Minimum (%)": st.column_config.NumberColumn(format="%.2f"),
            "Median (%)": st.column_config.NumberColumn(format="%.2f"),
            "Maximum (%)": st.column_config.NumberColumn(format="%.2f"),
            "Positive (%)": st.column_config.NumberColumn(format="%.1f", help="Share of periods with a gain"),
            "Beat benchmark (%)": st.column_config.NumberColumn(
                format="%.1f", help="Share of common start dates where the fund's rolling CAGR beat the benchmark's"),
            "Periods": st.column_config.NumberColumn(format="%d", help="Number of rolling windows"),
        })

# ---------------------------------------------------------------------------
# Calendar year
# ---------------------------------------------------------------------------
with tab_cal:
    cal = pd.concat({**{n: m.calendar_year_returns(s) for n, s in full.items()},
                     bench_name: m.calendar_year_returns(full_bench)}, axis=1).sort_index()
    cal = cal.dropna(how="all")
    if cal.empty:
        st.info("Calendar-year returns need NAVs from at least the end of one year to the end of the next.")
    else:
        ytd = end.month < 12 or end.day < 24
        st.subheader("Return in each calendar year")
        st.plotly_chart(charts.calendar_chart(cal.tail(10), colors, bench_name), config={"displayModeBar": False})
        st.caption("Last 10 years shown in the chart. Each year runs from the last NAV of the previous year "
                   "to the last NAV of that year." + (f" {end.year} is year-to-date." if ytd else ""))
        shown = (cal * 100).round(2).sort_index(ascending=False)
        shown.index = [f"{y} (YTD)" if ytd and y == end.year else str(y) for y in shown.index]
        shown.columns = [shorts.get(c, c) for c in shown.columns]
        st.dataframe(shown, column_config={c: st.column_config.NumberColumn(f"{c} (%)", format="%.2f")
                                           for c in shown.columns})

# ---------------------------------------------------------------------------
# SIP backtest
# ---------------------------------------------------------------------------
with tab_sip:
    st.subheader("SIP backtest")
    c1, c2 = st.columns(2)
    amount = c1.number_input("Monthly amount (Rs)", min_value=100, max_value=10_00_000, value=5_000, step=500)
    sip_start = c2.date_input("Start date", value=(end - pd.DateOffset(years=5)).date(),
                              max_value=end.date(), min_value=pd.Timestamp("1995-01-01").date(),
                              format="DD/MM/YYYY")
    c3, c4 = st.columns(2)
    sip_day = c3.number_input("SIP day of month (1 to 28)", min_value=1, max_value=28, value=5)
    step_up = c4.number_input("Yearly step-up (%)", min_value=0.0, max_value=50.0, value=0.0, step=5.0,
                              help="Raise the SIP amount by this % every 12 instalments.")

    sip_navs = {**full, bench_name: full_bench}
    sip_results = {n: run_sip(s, amount, sip_start, int(sip_day), step_up, end) for n, s in sip_navs.items()}
    sip_results = {n: r for n, r in sip_results.items() if r is not None}
    if not sip_results:
        st.info("No SIP instalment falls inside the available NAV history. Try an earlier start date.")
    else:
        rows = []
        for n, r in sip_results.items():
            rows.append({
                "Fund": shorts.get(n, n),
                "Instalments": len(r.transactions),
                "First SIP": r.transactions["NAV date"].iloc[0].strftime("%d %b %Y"),
                "Total invested": rupees(r.total_invested),
                "Current value": rupees(r.current_value),
                "Profit": rupees(r.profit),
                "XIRR": pct(r.xirr),
                "Avg cost / unit": f"Rs {r.average_cost:,.2f}" if r.average_cost else "n/a",
            })
        st.dataframe(pd.DataFrame(rows).set_index("Fund"))
        late = [shorts.get(n, n) for n, r in sip_results.items()
                if r.transactions["NAV date"].iloc[0] > pd.Timestamp(sip_start) + pd.Timedelta(days=35)]
        if late:
            st.caption("Started later because the fund didn't exist yet: " + ", ".join(late)
                       + ". Their totals are not directly comparable.")
        st.plotly_chart(charts.sip_chart({n: r.timeline for n, r in sip_results.items()}, colors, bench_name),
                        config={"displayModeBar": False})
        st.caption(f"Valued at the NAV of {end:%d %b %Y}. Units bought on the SIP date, or the next NAV date if the "
                   "market was closed. Ignores stamp duty, exit load and tax.")

# ---------------------------------------------------------------------------
# Learn
# ---------------------------------------------------------------------------
with tab_learn:
    st.subheader("Glossary in plain English")
    for term, meaning, example in GLOSSARY:
        with st.expander(term):
            st.markdown(f"{meaning}\n\n*Example:* {example}")

footer()
