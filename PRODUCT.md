# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Python 3.11 + Streamlit, deployed free on Streamlit Community Cloud. Custom HTML/CSS/JS components are allowed for key screens (user decision), as long as the app stays pure-Python to deploy, free, and needs no API keys.

## Users

Primary: an interviewer on a stock broker's Mutual Funds & IPO desk, watching the author (a final-year B.Tech AI student applying for a Finance Intern role) demo the app on a laptop or screen-share. The design has to make the author look credible within seconds and survive questions about every number.

Secondary (the scenario the app models): a mutual fund distributor comparing funds the way they would when advising a client.

## Product Purpose

Compare 1 to 4 Indian mutual funds against a Nifty 50 benchmark on return, risk and consistency, and explain the result in plain English. Success: within the first 10 seconds a viewer knows which fund wins and why (its return against the benchmark and the risk it took to get there).

## Positioning

A distributor-style comparison built on raw daily NAV data from mfapi.in, with every metric computed and unit-tested in the app (CAGR, volatility, Sharpe, Sortino, max drawdown, beta, Jensen's alpha, rolling returns, calendar years, SIP XIRR) rather than copied from a fund factsheet.

## Operating Context

- Data: mfapi.in (free, no key), 38,000+ schemes; scheme list cached 24h, NAV history 6h.
- Benchmark: an index fund's NAV used as a proxy for the index (disclosed in the app).
- Shown live in an interview, so it must load quickly and never crash; API failures show friendly messages.

## Capabilities and Constraints

- Must keep every current feature: fund search (Direct + Growth filter), benchmark picker, period selector (1Y/3Y/5Y/10Y/since inception/custom), editable risk-free rate, Overview metrics table with verdict and CSV export, growth of Rs 10,000, drawdown and rolling volatility, rolling returns with summary, calendar-year returns, SIP backtest with step-up and XIRR, plain-English glossary, disclaimer footer.
- Must stay usable on a phone.
- Calculations live in `src/metrics.py`, `src/sip.py`, `src/data.py` and are covered by 62 pytest tests; design work must not change their results.
- Indian conventions: rupees with lakh grouping (Rs 4,52,508), dates as dd Mon yyyy.

## Brand Commitments

- Dark mode is binding (user decision).
- Required footer: "Past performance does not guarantee future returns. Educational project, not investment advice. Data: mfapi.in."

## Evidence on Hand

- Live NAV data only. No testimonials, users, or performance claims about the app itself exist; none may be invented.

## Product Principles

1. Lead with the answer: the verdict comes before the table.
2. Every number is explainable in an interview: show its meaning next to it.
3. Honest comparisons: same end date, common-date beta, n/a when history is too short, assumptions stated.
4. Indian investor's language and formats throughout.

## Accessibility & Inclusion

WCAG AA contrast (4.5:1 body text) on the dark theme; colour is never the only signal (best values carry a star, the benchmark is named).
