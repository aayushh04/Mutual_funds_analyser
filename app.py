"""Mutual Fund Analyser: Streamlit layout only. All calculations live in src/.

Design: "Research Desk". The app reads like a broker's research note: controls in a header bar,
tabs as report sections, and a Summary that leads with a computed rating and three reasons.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src import charts
from src import metrics as m
from src.content import FOOTER, GLOSSARY, METRIC_GROUPS, METRIC_TIPS
from src.data import (
    CATEGORIES,
    DataError,
    FundHistory,
    filter_schemes,
    find_codes_by_name,
    find_default_benchmark,
    get_category_funds,
    get_nav_history,
    get_scheme_list,
)
from src.sip import run_sip
from src.ui import (
    PAGE_CSS,
    brief_names,
    category_label,
    entity_table_html,
    fund_list_html,
    fund_ratings,
    headline_html,
    inr,
    key_data_html,
    leader,
    leaderboard_html,
    leaders_sentence,
    metrics_table_html,
    num,
    pct,
    rating_box_html,
    rating_summary_html,
    short_name,
    thesis_html,
    volatility_peak_note,
    year_table_html,
)

DEFAULT_FUNDS = [
    "Parag Parikh Flexi Cap Fund - Direct Plan - Growth",
    "HDFC Flexi Cap Fund - Direct Plan - Growth Option",
]
MAX_FUNDS = 4
SEARCH_SHOWN = 8
PERIODS = {"1Y": "1 year", "3Y": "3 years", "5Y": "5 years", "10Y": "10 years",
           "Since inception": "Since inception", "Custom": "Custom dates"}
CHART = dict(config={"displayModeBar": False}, theme=None)  # our own chart styling, not Streamlit's

st.set_page_config(page_title="MF Analyser Research", page_icon=":material/query_stats:", layout="wide",
                   initial_sidebar_state="collapsed")
st.html(PAGE_CSS)


def footer() -> None:
    """Disclaimer shown at the bottom of every page."""
    st.divider()
    st.caption(FOOTER)


def add_fund(code: int) -> None:
    """Button callback: add a fund to the comparison and clear the search box."""
    if code not in st.session_state.funds and len(st.session_state.funds) < MAX_FUNDS:
        st.session_state.funds = st.session_state.funds + [code]
    st.session_state.fund_query = ""


# ---------------------------------------------------------------------------
# Scheme list (needed for search and defaults)
# ---------------------------------------------------------------------------
try:
    schemes = get_scheme_list()
except DataError as err:
    st.html('<div class="mfa-brand">MF Analyser <span>Research</span></div>')
    st.error(f"{err}")
    footer()
    st.stop()

names = dict(zip(schemes["scheme_code"], schemes["scheme_name"]))
default_bench_code, _ = find_default_benchmark(schemes)
if "funds" not in st.session_state:
    st.session_state.funds = find_codes_by_name(schemes, DEFAULT_FUNDS)

# ---------------------------------------------------------------------------
# Header bar: brand, funds, add fund, period, benchmark settings
# ---------------------------------------------------------------------------
header = st.container(key="mfa-header")
brand, funds_col, add_col, period_col, settings_col = header.columns([2.1, 3.9, 1.2, 1.3, 1.4],
                                                                     vertical_alignment="bottom")
brand.html('<div class="mfa-brand">MF Analyser <span>Research</span></div>')
funds_col.multiselect("Funds", st.session_state.funds, key="funds", label_visibility="collapsed",
                      format_func=lambda c: short_name(names.get(c, str(c)), 44),
                      placeholder="No funds yet. Use Add fund.")
with add_col.popover("Add fund", icon=":material/add:", width="stretch"):
    st.text_input("Search all 38,000+ schemes", key="fund_query", placeholder="e.g. axis small cap")
    direct_only = st.toggle("Direct plan, Growth option only", value=True, key="direct_only",
                            help="Direct plans have no distributor commission; Growth reinvests gains.")
    query = st.session_state.fund_query.strip()
    if query:
        matches = filter_schemes(schemes, query, direct_only, limit=500)
        full = len(st.session_state.funds) >= MAX_FUNDS
        if matches.empty:
            st.caption("No matching schemes. Try fewer words, or turn off the Direct + Growth filter.")
        else:
            count = len(matches)
            more = f" Showing the first {SEARCH_SHOWN}." if count > SEARCH_SHOWN else ""
            st.caption(f"{count} match{'es' if count != 1 else ''}.{more}")
            for code, name in matches.head(SEARCH_SHOWN).itertuples(index=False):
                label = short_name(name, 80) if direct_only else name
                if code in st.session_state.funds:
                    st.button(label, key=f"add_{code}", icon=":material/check:", disabled=True, width="stretch")
                else:
                    st.button(label, key=f"add_{code}", icon=":material/add:", on_click=add_fund, args=(int(code),),
                              disabled=full, width="stretch")
            if full:
                st.caption(f"You're comparing {MAX_FUNDS} funds, the maximum. Remove one to add another.")
period = period_col.selectbox("Period", list(PERIODS), index=2, format_func=PERIODS.get,
                              label_visibility="collapsed")
with settings_col.popover("Benchmark", icon=":material/tune:", width="stretch"):
    bench_query = st.text_input("Find another benchmark", placeholder="e.g. nifty 100 index")
    bench_results = (filter_schemes(schemes, bench_query, st.session_state.get("direct_only", True))
                     if bench_query.strip() else schemes.iloc[0:0])
    bench_options = list(dict.fromkeys([default_bench_code] + bench_results["scheme_code"].tolist()))
    bench_code = st.selectbox("Index fund used as the benchmark", bench_options,
                              format_func=lambda c: short_name(names.get(c, str(c)), 60),
                              help="The free data has no index values, so an index fund's NAV stands in for the index.")
    rf_pct = st.number_input("Risk-free rate (%)", min_value=0.0, max_value=20.0, value=6.5, step=0.25,
                             help="An editable assumption, roughly the Indian T-bill yield. Used in Sharpe, Sortino, alpha.")
rf = rf_pct / 100

custom_start = custom_end = None
if period == "Custom":
    c1, c2, _ = st.columns([1, 1, 3])
    today = pd.Timestamp.today().normalize()
    custom_start = c1.date_input("From", value=(today - pd.DateOffset(years=3)).date(), format="DD/MM/YYYY")
    custom_end = c2.date_input("To", value=today.date(), format="DD/MM/YYYY")

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
if not st.session_state.funds:
    st.info("Use Add fund in the header to pick up to 4 funds to compare.")
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
briefs = {**brief_names(fund_names), bench_name: "Benchmark"}  # for tight spots: spotlight, chart line ends

# Common end date = the latest date every series has a NAV for, so all are compared to the same day.
end = min([f.latest_date for f in funds.values()] + [bench.latest_date])
if period == "Custom":
    start = pd.Timestamp(custom_start)
    end = min(end, pd.Timestamp(custom_end))
    if start >= end:
        st.error("The 'From' date must be before the 'To' date and before the latest NAV date.")
        footer()
        st.stop()
else:
    start = m.period_start(end, period)

sliced = {n: m.slice_nav(f.nav, start, end) for n, f in funds.items()}
bench_sliced = m.slice_nav(bench.nav, start, end)
full_nav = {n: f.nav.loc[:end] for n, f in funds.items()}
full_bench = bench.nav.loc[:end]
too_short = [n for n, s in sliced.items() if s is None]
table = m.metrics_table(sliced, bench_name, bench_sliced, rf)

period_word = {"1Y": "1 year", "3Y": "3 years", "5Y": "5 years", "10Y": "10 years"}.get(period, "period")
if period == "Since inception":
    meta = f"Since each fund's first NAV, to {end:%d %b %Y} · Rf {rf_pct:.2f}%"
elif period == "Custom":
    meta = f"{start:%d %b %Y} to {end:%d %b %Y} · Rf {rf_pct:.2f}%"
else:
    meta = f"{PERIODS[period]} to {end:%d %b %Y} · Rf {rf_pct:.2f}%"
category = category_label([f.scheme_category for f in funds.values()])
st.html(headline_html(table, fund_names, shorts, category, meta))
if too_short:
    st.info("Not enough history for this period, so these show n/a: "
            + "; ".join(f"{shorts[n]} (NAV since {funds[n].inception_date:%b %Y})" for n in too_short)
            + ". Try a shorter period.")

# Spotlight: pick one fund to highlight in every chart and table; the others fade back.
focus = None
if len(fund_names) > 1:
    spot_options = ["all"] + fund_names
    if st.session_state.get("spotlight") not in spot_options:
        st.session_state.spotlight = "all"
    pick = st.segmented_control("Spotlight", spot_options, key="spotlight", label_visibility="collapsed",
                                format_func=lambda n: "All funds" if n == "all" else briefs[n],
                                help="Highlight one fund across every chart and table.")
    focus = None if pick in (None, "all") else pick

tab_sum, tab_top, tab_risk, tab_roll, tab_cal, tab_sip, tab_learn = st.tabs(
    ["Summary", "Top funds", "Risk", "Consistency", "Calendar years", "SIP backtest", "Glossary"]
)

# ---------------------------------------------------------------------------
# Summary: rating box + key data | why it leads + rating summary | relative performance
# ---------------------------------------------------------------------------
with tab_sum:
    lead_fund = leader(table, fund_names)
    top = focus or lead_fund
    usable = {n: s for n, s in sliced.items() if s is not None}
    if bench_sliced is not None:
        usable[bench_name] = bench_sliced
    rebased = m.growth_of_investment(pd.concat(usable, axis=1), amount=100) if usable else pd.DataFrame()

    left, centre, right = st.columns([3.2, 5, 4.6], gap="large")
    with left:
        if top is not None:
            verdict = fund_ratings(table, fund_names, bench_name)[top]
            st.html(rating_box_html(top, verdict, shorts[bench_name], shorts))
            st.html(key_data_html(table, top, funds[top].inception_date, period_word))
    with centre:
        st.html(f'<h2 class="mfa-h">{"Why it leads" if top == lead_fund else "The case for this fund"}</h2>')
        if top is not None:
            final = rebased[top].iloc[-1] * 100 if not rebased.empty and top in rebased else None
            st.html(thesis_html(table, top, bench_name, shorts, final))
        st.html(rating_summary_html(table, fund_names, bench_name, colors, shorts, focus))
        st.html('<p class="mfa-note">Ratings are computed: OUTPERFORM when CAGR beats the benchmark and alpha is '
                'positive, UNDERPERFORM when both are worse, IN-LINE otherwise.</p>')
    with right:
        with st.container(border=True):
            st.html('<h2 class="mfa-h">Relative performance</h2>')
            if rebased.empty or len(rebased) < 2:
                st.info("Not enough overlapping history to draw this chart.")
            else:
                st.html(f'<p class="mfa-sub">Rebased to 100 on {rebased.index[0]:%d %b %Y}</p>')
                st.plotly_chart(charts.rebased_chart(rebased, colors, bench_name, focus, briefs), **CHART)
                st.caption("Rs 10,000 became " + ", ".join(
                    f"{inr(rebased[c].iloc[-1] * 100)} ({shorts[c]})" for c in rebased.columns) + ".")

    st.header("Full metrics", anchor=False)
    best = m.best_columns(table, fund_names)
    st.html(metrics_table_html(table, best, colors, bench_name, shorts, focus))
    st.caption("Starred figures are the best among your funds; the benchmark is not ranked. "
               "Hover a metric name for its meaning. CAGR, Sharpe, Sortino and alpha need at least a year.")
    c1, c2 = st.columns([3, 1])
    with c1.expander("What do these metrics mean?"):
        for group, rows in METRIC_GROUPS:
            st.markdown(f"**{group}**\n\n" + "\n".join(f"- **{r}**: {METRIC_TIPS[r]}" for r in rows))
    c2.download_button("Download metrics (CSV)", table.to_csv(index_label="Metric").encode("utf-8"),
                       file_name=f"fund_metrics_{period.replace(' ', '_').lower()}_{end:%Y%m%d}.csv",
                       mime="text/csv", icon=":material/download:", width="stretch")
    st.header("Funds covered", anchor=False)
    st.html(fund_list_html(
        [(n, f.fund_house, f.scheme_category, f.inception_date) for n, f in funds.items()]
        + [(bench_name, bench.fund_house, bench.scheme_category, bench.inception_date)],
        colors, bench_name, shorts, focus))

# ---------------------------------------------------------------------------
# Top funds: best 5 in a category over 3, 5 and 10 years
# ---------------------------------------------------------------------------
with tab_top:
    cats = list(CATEGORIES)
    default_cat = next((c for c in cats if c.lower().startswith(category.lower())), "Flexi cap")
    pick_col, _ = st.columns([1, 2])
    cat = pick_col.selectbox("Category", cats, index=cats.index(default_cat), key="top_category")
    cat_funds = get_category_funds(cat)
    if not cat_funds:
        st.warning("Could not load the funds in this category right now. Please try again in a minute.")
    else:
        latest = max(f.latest_date for f in cat_funds.values())
        # Funds that stopped publishing NAVs (closed or merged) are left out.
        live = {f.scheme_name: f.nav.loc[:latest] for f in cat_funds.values()
                if f.latest_date >= latest - pd.Timedelta(days=10)}
        code_of = {f.scheme_name: code for code, f in cat_funds.items()}
        st.caption(f"{len(live)} actively managed {cat.lower()} funds (Direct plan, Growth option), ranked by trailing "
                   f"CAGR to {latest:%d %b %Y}. Sharpe uses the {rf_pct:.2f}% risk-free rate from Benchmark settings.")
        boards = {yrs: m.leaderboard(live, yrs, latest, rf) for yrs in (3, 5, 10)}
        st.html(leaders_sentence(cat, {y: (t["Fund"].iloc[0] if not t.empty else "") for y, (t, _) in boards.items()}))
        shown: list[str] = []
        for col, (yrs, (top5, qualified)) in zip(st.columns(3, gap="large"), boards.items()):
            col.html(leaderboard_html(top5, f"Best over {yrs} years", qualified, yrs, set(funds)))
            shown += list(top5["Fund"])
        candidates = [n for n in dict.fromkeys(shown) if code_of[n] not in st.session_state.funds]
        if candidates:
            add_pick, add_btn, _ = st.columns([2.2, 1, 2.8], vertical_alignment="bottom")
            chosen = add_pick.selectbox("Add a ranked fund to your comparison", candidates,
                                        format_func=lambda n: short_name(n, 70), key="top_add_pick")
            add_btn.button("Add to comparison", icon=":material/add:", on_click=add_fund,
                           args=(int(code_of[chosen]),), disabled=len(st.session_state.funds) >= MAX_FUNDS,
                           width="stretch")
            if len(st.session_state.funds) >= MAX_FUNDS:
                st.caption(f"You're comparing {MAX_FUNDS} funds, the maximum. Remove one in the header to add another.")
        st.caption("Rankings use past returns only and change with the end date. Funds that closed or merged are not "
                   "in the data, so the lists flatter the category (survivorship bias). Index funds, ETFs, "
                   "fund-of-funds and international funds are excluded; categories are matched by scheme name. "
                   "A top rank is a starting point for research, not a recommendation.")

# ---------------------------------------------------------------------------
# Risk
# ---------------------------------------------------------------------------
with tab_risk:
    st.caption("Uses the period in the header.")
    st.header("Drawdown: how far below its last peak", anchor=False)
    dds = {n: m.drawdown_series(s) for n, s in usable.items()}
    if dds:
        st.plotly_chart(charts.drawdown_chart(pd.concat(dds, axis=1), colors, bench_name, focus), **CHART)
        st.caption("0% means the fund is at a new high. The lowest point is the maximum drawdown in the Summary.")
    else:
        st.info("No fund has enough history for this period.")

    st.header("Rolling 1-year volatility", anchor=False)
    vols = {}
    for n, s in {**full_nav, bench_name: full_bench}.items():
        v = m.rolling_volatility(s)
        if start is not None:
            v = v.loc[start:end]
        if not v.empty:
            vols[n] = v
    if vols:
        st.plotly_chart(charts.rolling_vol_chart(pd.concat(vols, axis=1), colors, bench_name, focus), **CHART)
        st.caption("Each point is the annualised volatility of the previous ~252 trading days. "
                   + volatility_peak_note(vols, shorts))
    else:
        st.info("Rolling volatility needs more than one year of NAV history.")

# ---------------------------------------------------------------------------
# Consistency (rolling returns)
# ---------------------------------------------------------------------------
with tab_roll:
    st.caption(f"Uses each fund's full history up to {end:%d %b %Y}, not the header period. "
               "Rolling returns show consistency. Trailing returns depend on today's date.")
    window = st.radio("Holding period", ["1Y", "3Y", "5Y"], index=1, horizontal=True,
                      format_func=lambda w: PERIODS[w])
    years = m.PERIOD_YEARS[window]
    rolling = {n: m.rolling_cagr(s, years) for n, s in full_nav.items()}
    bench_roll = m.rolling_cagr(full_bench, years)
    plot = {n: r for n, r in rolling.items() if not r.empty}
    if not bench_roll.empty:
        plot[bench_name] = bench_roll
    if not plot:
        st.info(f"None of the funds has more than {years} years of history. Try a shorter holding period.")
    else:
        st.plotly_chart(charts.rolling_returns_chart(pd.concat(plot, axis=1), colors, bench_name, years, focus),
                        **CHART)
        st.caption(f"Each point is the CAGR you'd have earned by investing on that date and holding for {years} years. "
                   "In the table, Median, Worst and Best are rolling CAGRs; Beat benchmark and Positive are the share "
                   "of windows; Windows is how many start dates were tested.")
        summary = m.rolling_summary({**rolling, bench_name: bench_roll}, bench_roll)
        summary.loc[bench_name, "Beat benchmark (%)"] = None
        cols = ["Median (%)", "Beat benchmark (%)", "Positive (%)", "Minimum (%)", "Maximum (%)", "Periods"]
        summary = summary[cols].rename(columns={"Minimum (%)": "Worst (%)", "Maximum (%)": "Best (%)",
                                                "Periods": "Windows"})
        st.html(entity_table_html(
            summary, colors, bench_name, shorts,
            formats={"Beat benchmark (%)": lambda v: num(v, 1), "Positive (%)": lambda v: num(v, 1),
                     "Windows": lambda v: num(v, 0)},
            best_rules={"Median (%)": "max", "Beat benchmark (%)": "max", "Positive (%)": "max",
                        "Worst (%)": "max", "Best (%)": "max"},
            caption=f"{years}-year rolling return summary", focus=focus))

# ---------------------------------------------------------------------------
# Calendar years
# ---------------------------------------------------------------------------
with tab_cal:
    st.caption(f"Uses each fund's full history up to {end:%d %b %Y}, not the header period.")
    cal = pd.concat({**{n: m.calendar_year_returns(s) for n, s in full_nav.items()},
                     bench_name: m.calendar_year_returns(full_bench)}, axis=1).sort_index().dropna(how="all")
    if cal.empty:
        st.info("Calendar-year returns need NAVs from at least the end of one year to the end of the next.")
    else:
        ytd_year = end.year if (end.month < 12 or end.day < 24) else None
        st.header("Return in each calendar year", anchor=False)
        st.plotly_chart(charts.calendar_chart(cal.tail(10), colors, bench_name, focus), **CHART)
        st.caption("Chart shows the last 10 years. Each year runs from the last NAV of the previous year to the last NAV "
                   "of that year." + (f" {end.year} is year-to-date." if ytd_year else ""))
        st.html(year_table_html(cal, colors, bench_name, shorts, ytd_year, focus))

# ---------------------------------------------------------------------------
# SIP backtest
# ---------------------------------------------------------------------------
with tab_sip:
    st.caption("Uses its own start date below, not the header period.")
    st.header("SIP backtest", anchor=False)
    c1, c2, c3, c4 = st.columns(4)
    amount = c1.number_input("Monthly amount (Rs)", min_value=100, max_value=10_00_000, value=5_000, step=500)
    sip_start = c2.date_input("Start date", value=(end - pd.DateOffset(years=5)).date(),
                              max_value=end.date(), min_value=pd.Timestamp("1995-01-01").date(),
                              format="DD/MM/YYYY")
    sip_day = c3.number_input("SIP day of month (1 to 28)", min_value=1, max_value=28, value=5)
    step_up = c4.number_input("Yearly step-up (%)", min_value=0.0, max_value=50.0, value=0.0, step=5.0,
                              help="Raise the SIP amount by this % every 12 instalments.")

    sip_results = {n: run_sip(s, amount, sip_start, int(sip_day), step_up, end)
                   for n, s in {**full_nav, bench_name: full_bench}.items()}
    sip_results = {n: r for n, r in sip_results.items() if r is not None}
    if not sip_results:
        st.info("No SIP instalment falls inside the available NAV history. Try an earlier start date.")
    else:
        sip_table = pd.DataFrame({
            n: {"XIRR": r.xirr, "Current value": r.current_value, "Profit": r.profit, "Invested": r.total_invested}
            for n, r in sip_results.items()}).T
        st.html(entity_table_html(
            sip_table, colors, bench_name, shorts,
            formats={"XIRR": pct, "Current value": inr, "Profit": inr, "Invested": inr},
            best_rules={"XIRR": "max"}, caption="SIP backtest result per fund", focus=focus))
        starts = {r.transactions["NAV date"].iloc[0] for r in sip_results.values()}
        counts = {len(r.transactions) for r in sip_results.values()}
        if len(starts) == 1 and len(counts) == 1:
            st.caption(f"{counts.pop()} monthly instalments, the first on {starts.pop():%d %b %Y}.")
        late = [shorts.get(n, n) for n, r in sip_results.items()
                if r.transactions["NAV date"].iloc[0] > pd.Timestamp(sip_start) + pd.Timedelta(days=35)]
        if late:
            st.caption("Started later because the fund didn't exist yet: " + ", ".join(late)
                       + ". Their totals are not directly comparable.")
        st.plotly_chart(charts.sip_chart({n: r.timeline for n, r in sip_results.items()}, colors, bench_name, focus),
                        **CHART)
        st.caption(f"Valued at the NAV of {end:%d %b %Y}. Units are bought on the SIP date, or the next NAV date if "
                   "the market was closed. Ignores stamp duty, exit load and tax.")

# ---------------------------------------------------------------------------
# Glossary
# ---------------------------------------------------------------------------
with tab_learn:
    st.header("Glossary in plain English", anchor=False)
    for term, meaning, example in GLOSSARY:
        with st.expander(term):
            st.markdown(f"{meaning}\n\n*Example:* {example}")

footer()
