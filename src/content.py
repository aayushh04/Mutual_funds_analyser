"""Plain-English text: metric tooltips, the Learn-tab glossary and the footer."""

FOOTER = (
    "Past performance does not guarantee future returns. "
    "Educational project, not investment advice. Data: mfapi.in."
)

METRIC_TIPS: dict[str, str] = {
    "Absolute return (%)": "Total gain from start to end of the period, ignoring how long it took. 100 -> 150 = 50%.",
    "CAGR (%)": "Compound Annual Growth Rate: the steady yearly return that turns the start NAV into the end NAV. Shown only for periods of 1 year or more.",
    "Volatility (%)": "How much the fund's value swings in a typical year (std. dev. of daily returns x sqrt 252). Lower = smoother ride.",
    "Sharpe ratio": "Return above the risk-free rate per unit of total volatility. Higher = better reward for the risk taken.",
    "Sortino ratio": "Like Sharpe, but only counts downside swings as risk. Higher = better reward per unit of bad volatility.",
    "Max drawdown (%)": "Worst fall from a peak to a later low in this period. Shows the pain an investor would have sat through.",
    "Drawdown peak": "Date of the high just before the worst fall.",
    "Drawdown trough": "Date of the lowest point of the worst fall.",
    "Recovered on": "First date the NAV got back to its old peak, or 'Not recovered' if it hasn't yet.",
    "Beta": "Sensitivity to the market. 1.0 moves with the index, 1.2 moves 20% more, 0.8 moves 20% less. No 'best' value.",
    "Alpha (%)": "Jensen's alpha: return beyond what the fund's beta 'should' have earned (CAPM). Positive = manager added value.",
}

# How the metrics table is grouped on screen (the CSV keeps the plain order).
METRIC_GROUPS: list[tuple[str, list[str]]] = [
    ("Return", ["Absolute return (%)", "CAGR (%)"]),
    ("Risk-adjusted return", ["Sharpe ratio", "Sortino ratio"]),
    ("Risk", ["Volatility (%)", "Max drawdown (%)", "Drawdown peak", "Drawdown trough", "Recovered on"]),
    ("Versus benchmark", ["Beta", "Alpha (%)"]),
]

GLOSSARY: list[tuple[str, str, str]] = [
    ("NAV (Net Asset Value)",
     "The price of one unit of a mutual fund, published every business day: "
     "(market value of holdings - expenses) / units outstanding.",
     "A fund holding Rs 100 crore of assets with 5 crore units has a NAV of Rs 20."),
    ("CAGR (Compound Annual Growth Rate)",
     "The single steady yearly growth rate that takes a starting value to an ending value. "
     "It smooths out the ups and downs along the way.",
     "Rs 10,000 that becomes Rs 20,000 in 5 years grew at a CAGR of about 14.87%."),
    ("XIRR (Extended Internal Rate of Return)",
     "The annual return when money goes in on different dates, as in a SIP. "
     "Each instalment is credited only for the time it was actually invested.",
     "12 SIPs of Rs 5,000 now worth Rs 66,000: XIRR is about 19%, not the 10% absolute gain."),
    ("Rolling returns",
     "The return for every possible holding period of a fixed length (e.g. every 3-year window). "
     "They show how consistent a fund is, not just how it did up to today.",
     "A fund whose 3-year rolling return was positive 95% of the time is more dependable than one at 70%."),
    ("Volatility",
     "How much returns bounce around, measured by standard deviation and annualised. "
     "It is the most common measure of risk.",
     "A fund with 20% volatility swings much more than a debt fund with 2%."),
    ("Sharpe ratio",
     "(Return - risk-free rate) / volatility. How much extra return you got for each unit of risk.",
     "15% CAGR, 6.5% risk-free, 20% volatility: Sharpe = (15 - 6.5) / 20 = 0.43."),
    ("Sortino ratio",
     "Like Sharpe, but divides by downside deviation, which only counts falls. "
     "Useful because investors don't mind upside swings.",
     "Two funds with equal Sharpe: the one with the higher Sortino had milder falls."),
    ("Drawdown",
     "The % fall from a fund's highest NAV to a later low. Maximum drawdown is the worst one in a period.",
     "NAV goes 100 -> 120 -> 90: the drawdown is (90 - 120) / 120 = -25%."),
    ("Beta",
     "How strongly a fund moves with the market (benchmark). 1 = in line, above 1 = amplified, below 1 = muted.",
     "Beta 0.8: if the Nifty 50 falls 10%, the fund tended to fall about 8%."),
    ("Alpha",
     "Return above what the fund should have earned for its market risk (from CAPM). "
     "It is a rough measure of the fund manager's skill.",
     "Expected return 13%, actual 15%: alpha = +2%."),
    ("Direct vs Regular plan",
     "The same fund, sold in two plans. Regular plans pay a commission to the distributor out of the "
     "fund's expenses. Direct plans don't, so their expense ratio and costs are lower.",
     "A 0.7% yearly cost gap on Rs 10 lakh over 20 years adds up to several lakh rupees."),
    ("Expense ratio",
     "The yearly fee the fund charges, as a % of your investment. It is deducted from the NAV daily, "
     "so NAV-based returns already include it.",
     "An expense ratio of 1% on Rs 1 lakh costs about Rs 1,000 a year."),
]
