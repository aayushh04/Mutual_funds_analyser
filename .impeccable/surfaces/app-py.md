---
version: 1
slug: "app-py"
primary_target: "app.py"
related_targets: []
---

# Surface brief: Mutual Fund Analyser app (app.py)

Scope: the whole Streamlit app (all six tabs). Visitor mode: Operate (a working comparison tool, demoed to an interviewer at a broker's MF/IPO desk).
Audience and job: interviewer watching a live demo; within 10 seconds they must know which fund wins and why. Constraints: every current feature stays; dark mode; free Streamlit Cloud deploy; usable on a phone; calculations untouched.
Memorable moment: the computed OUTPERFORM rating box beside a three-point "why it leads" thesis.

## Direction contract

THESIS: The app reads as a broker's research note on the funds: each fund is rated against the benchmark (OUTPERFORM / IN-LINE / UNDERPERFORM, computed from CAGR and alpha, never opinion). It refuses the generic fintech dashboard of KPI tiles and cards.

OWN-WORLD: Warm charcoal ground (#111315) with a slightly raised sheet (#1a1d21), warm ivory ink (#e9e4da), one house gold for brand, active tab and primary control. Serif (Source Serif 4) for headlines, rating and section heads; Source Sans 3 for tables and controls, tabular figures. Hairline rules, no cards, no drop shadows. Rating stamps: green OUTPERFORM, grey IN-LINE, red UNDERPERFORM, always as text plus colour.

STORY: The viewer sees the headline sentence naming the leader, the rating box, three plain-English reasons (return, risk, skill), then a rating summary for every fund and a chart rebased to 100. They can change funds, period, benchmark and risk-free rate from the header and dig into Risk, Consistency, Calendar years, SIP backtest and Glossary.

FIRST VIEWPORT: Header bar: brand left; fund chips, Add fund, period, benchmark, risk-free rate right. Tabs as report sections (Summary, Risk, Consistency, Calendar years, SIP backtest, Glossary). Masthead: serif headline sentence left, period and plan right. Three columns: left 330px rating box plus Key data table; centre "Why it leads" three points plus rating summary table; right relative-performance chart rebased to 100 in a panel. Primary action: Add fund in the header. No sidebar.

FORM: Research Desk Rating, position 1 on my ordered grounded list (shown as IMPECCABLE'S PICK), seed:b67ca96e9872c8cb. Signature interaction: Spotlight a fund across every chart and table, plus 1Y/3Y/5Y/All zoom on time charts; motion is a single settle of the rating box.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
