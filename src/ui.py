"""Presentation helpers for the "Research Desk" design: page CSS, the research-note blocks
(headline, rating box, key data, thesis, rating summary), HTML tables and number formats.

Everything here returns strings. app.py decides where they go.
"""

from __future__ import annotations

import html
import re
from typing import Callable, Optional, Sequence

import pandas as pd

from src.content import METRIC_GROUPS, METRIC_TIPS
from src.metrics import rating

# Research Desk tokens (dark, warm). Contrast measured against GROUND / SHEET.
GROUND = "#111315"    # page (matches theme backgroundColor)
SHEET = "#1a1d21"     # raised panels and table headers
LINE = "#2a2d31"      # hairline rules
INK = "#e9e4da"       # body text, warm ivory (14:1)
MUTED = "#a39d92"     # secondary text (6.9:1)
GOLD = "#d6b25e"      # house colour as text (8:1); fills use the theme primary
SERIF = "'Source Serif 4', Georgia, serif"
BENCH_SWATCH = "#8e939a"  # must match charts.BENCH_COLOR
RATING_STYLE = {      # (text colour, tint) per rating; always shown as words too
    "OUTPERFORM": ("#6fd3a0", "rgba(47,163,107,.13)"),
    "IN-LINE": ("#c9ccd1", "rgba(142,147,154,.14)"),
    "UNDERPERFORM": ("#f08a96", "rgba(208,80,94,.14)"),
    "NOT RATED": ("#a39d92", "rgba(142,147,154,.10)"),
    "BENCHMARK": ("#c9ccd1", "rgba(142,147,154,.14)"),
}

STAR_MASK = ("url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Cpath "
             "d='M8 1.2l2 4.3 4.7.6-3.4 3.2.9 4.7L8 11.7 3.8 14l.9-4.7L1.3 6.1 6 5.5z'/%3E%3C/svg%3E\") center / contain no-repeat")

PAGE_CSS = f"""
<style>
::selection {{ background: rgba(214,178,94,.35); color: #fff; }}
:focus-visible {{ outline: 2px solid {GOLD}; outline-offset: 2px; }}
html {{ scrollbar-color: #33373c {GROUND}; }}
[data-testid="stMainBlockContainer"] {{ padding-top: 1.6rem; max-width: 1480px; }}
/* Streamlit's top bar is see-through and lets clicks pass, except on its own menu. */
[data-testid="stHeader"], [data-testid="stHeader"] * {{ background: transparent; pointer-events: none; }}
[data-testid="stHeader"] button, [data-testid="stHeader"] button * {{ pointer-events: auto; }}
.st-key-mfa-header {{ border-bottom: 1px solid {LINE}; padding-bottom: 14px; margin-bottom: 4px; }}
/* Selected funds: neutral chips, full short names. Gold goes to the primary action, Add fund. */
.st-key-mfa-header [data-baseweb="tag"] {{ background: {SHEET} !important; border: 1px solid #3a3e44; max-width: none !important; }}
.st-key-mfa-header [data-baseweb="tag"] span {{ color: {INK} !important; max-width: none !important; }}
.st-key-mfa-header [data-testid="stColumn"]:nth-child(3) [data-testid="stPopover"] button {{
  background: #8a6a22; border-color: #8a6a22; color: #fff; }}
.st-key-mfa-header [data-testid="stColumn"]:nth-child(3) [data-testid="stPopover"] button:hover {{ background: #9b7828; border-color: #9b7828; }}
.st-key-mfa-header [data-testid="stColumn"]:nth-child(3) [data-testid="stPopover"] button * {{ color: #fff !important; }}
/* Rating summary: the tag sits under the fund name so Fund, CAGR, Alpha, Sharpe fit the centre column. */
.mfa-rin {{ display: block; margin-top: 4px; }}
.mfa-rs .mfa-table th[scope="row"], .mfa-rs .mfa-table thead th {{ min-width: 0; }}
.mfa-lead {{ font: 600 1.22rem/1.4 {SERIF}; color: {INK}; margin: 6px 0 2px; max-width: 70ch; text-wrap: pretty; }}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {{ color: {MUTED} !important; opacity: 1 !important; }}
[data-testid="stCaptionContainer"] {{ max-width: 80ch; }}
[data-testid="stMarkdownContainer"] p, .mfa-thesis p, .mfa-head {{ text-wrap: pretty; }}
input::placeholder, textarea::placeholder {{ color: #8f897f !important; opacity: 1; }}
button[role="tab"][aria-selected="true"] p,
[data-testid="stBaseButton-segmented_controlActive"] p {{ color: {GOLD} !important; }}
button[role="tab"] p {{ font-weight: 600; }}
[data-testid="stPopoverBody"] [data-testid="stButton"] button,
[data-testid="stPopoverBody"] [data-testid="stButton"] button > div,
[data-testid="stPopoverBody"] [data-testid="stButton"] button > div > span {{ justify-content: flex-start; text-align: left; width: 100%; }}

.mfa-brand {{ font: 700 1.3rem/1.2 {SERIF}; color: {INK}; white-space: nowrap; padding-top: .35rem; }}
.mfa-brand span {{ color: {GOLD}; }}
.mfa-mast {{ display: flex; align-items: baseline; justify-content: space-between; gap: 24px; flex-wrap: wrap;
  border-bottom: 1px solid {LINE}; padding: 4px 0 14px; }}
.mfa-head {{ font: 600 1.85rem/1.2 {SERIF}; color: {INK}; margin: 0; max-width: 42ch; letter-spacing: -.005em; }}
.mfa-meta {{ color: {MUTED}; font-size: .92rem; font-variant-numeric: tabular-nums; }}
.mfa-h {{ font: 600 1.3rem/1.25 {SERIF}; color: {INK}; margin: 0 0 10px; }}
.mfa-sub {{ color: {MUTED}; font-size: .85rem; margin: -6px 0 6px; }}

@keyframes mfa-settle {{ from {{ opacity: 0; transform: translateY(6px); }} to {{ opacity: 1; transform: none; }} }}
.mfa-rating {{ border: 1px solid var(--rc); background: var(--rt); border-radius: 6px; padding: 18px 20px;
  animation: mfa-settle .55s cubic-bezier(.16,1,.3,1) both; }}
.mfa-rating .r {{ font: 700 clamp(1.7rem, 2.3vw, 2.5rem)/1 {SERIF}; color: var(--rc); margin: 2px 0 8px; letter-spacing: -.01em; }}
.mfa-rating .f {{ font: 600 1.2rem/1.25 {SERIF}; color: {INK}; }}
.mfa-rating .b {{ color: {MUTED}; font-size: .88rem; margin-top: 3px; }}

.mfa-kd {{ width: 100%; border-collapse: collapse; margin-top: 18px; font-variant-numeric: tabular-nums; color: {INK}; }}
.mfa-kd caption {{ text-align: left; font: 600 1.02rem {SERIF}; padding-bottom: 4px; color: {INK}; }}
.mfa-kd td {{ padding: 8px 0; border-bottom: 1px solid {LINE}; font-size: .95rem; }}
.mfa-kd td:last-child {{ text-align: right; font-weight: 600; }}

.mfa-thesis p {{ margin: 0 0 13px; font-size: 1.02rem; line-height: 1.55; color: #d9d3c7; max-width: 62ch; }}
.mfa-thesis b {{ color: #fff; font-weight: 600; }}

.mfa-tag {{ display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: .74rem; font-weight: 700;
  letter-spacing: .05em; color: var(--rc); background: var(--rt); }}

.mfa-funds {{ list-style: none; margin: 0 !important; padding: 0 !important; display: grid; gap: 6px; }}
.mfa-funds li {{ font-size: .9rem; color: {MUTED}; line-height: 1.4; margin: 0 !important; padding: 0 !important; transition: opacity .25s ease; }}
.mfa-funds li b {{ color: {INK}; font-weight: 600; }}

.mfa-wrap {{ overflow-x: auto; -webkit-overflow-scrolling: touch;
  background: linear-gradient(to right, {GROUND} 30%, rgba(17,19,21,0)) left center / 24px 100% no-repeat local,
              linear-gradient(to left, {GROUND} 30%, rgba(17,19,21,0)) right center / 24px 100% no-repeat local,
              radial-gradient(farthest-side at 0 50%, rgba(0,0,0,.6), rgba(0,0,0,0)) left center / 12px 100% no-repeat scroll,
              radial-gradient(farthest-side at 100% 50%, rgba(0,0,0,.6), rgba(0,0,0,0)) right center / 12px 100% no-repeat scroll,
              {GROUND}; }}
.mfa-table {{ border-collapse: collapse; width: 100%; font-size: .93rem; font-variant-numeric: tabular-nums; color: {INK}; }}
.mfa-table caption {{ position: absolute; left: -9999px; }}
.mfa-table th, .mfa-table td {{ padding: 9px 12px; border-bottom: 1px solid {LINE}; text-align: right; white-space: nowrap;
  transition: background-color .15s ease, opacity .25s ease; }}
.mfa-table th:first-child, .mfa-table td:first-child {{ padding-left: 0; }}
.mfa-table thead th {{ color: {MUTED}; font-size: .82rem; font-weight: 600; vertical-align: bottom; white-space: normal; min-width: 72px;
  border-bottom: 1px solid #3a3e44; }}
.mfa-table th[scope="row"] {{ text-align: left; font-weight: 400; position: sticky; left: 0; background: {GROUND}; z-index: 2;
  white-space: normal; min-width: 140px; }}
.mfa-table thead th:first-child {{ text-align: left; position: sticky; left: 0; background: {GROUND}; z-index: 3; }}
.mfa-table tr.mfa-group th {{ text-align: left; color: {INK}; font: 600 .98rem {SERIF}; padding-top: 16px; position: static;
  border-bottom: 1px solid #3a3e44; }}
.mfa-table tbody tr:not(.mfa-group):hover td, .mfa-table tbody tr:not(.mfa-group):hover th[scope="row"] {{ background-color: #1b1e22; }}
.mfa-term {{ text-decoration: underline dotted #6b665e; text-underline-offset: 3px; cursor: help; }}
.mfa-swatch {{ display: inline-block; width: 9px; height: 9px; border-radius: 2px; margin-right: 7px; vertical-align: 1px; }}
.mfa-best {{ color: #6fd3a0; font-weight: 700; }}
.mfa-best::before {{ content: ""; display: inline-block; width: 10px; height: 10px; margin-right: 5px; vertical-align: -1px;
  background: currentColor; -webkit-mask: {STAR_MASK}; mask: {STAR_MASK}; }}
.mfa-na {{ color: {MUTED}; }}
.mfa-table .mfa-dim, .mfa-funds li.mfa-dim {{ opacity: .38; }}
.mfa-table thead th.mfa-lit {{ color: {GOLD}; box-shadow: inset 0 -2px 0 {GOLD}; }}
.mfa-sr {{ position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }}
.mfa-note {{ color: {MUTED}; font-size: .8rem; margin-top: 8px; }}
.mfa-rank {{ font: 600 1.05rem {SERIF}; color: {GOLD}; text-align: left !important; width: 28px; }}
.mfa-lb .mfa-table thead th {{ min-width: 0; white-space: nowrap; }}
.mfa-lb .mfa-table thead th:nth-child(-n+2) {{ text-align: left; }}
.mfa-lb .mfa-table th[scope="row"] {{ min-width: 0; position: static; padding-left: 4px; }}
.mfa-lb .mfa-table td.mfa-rank, .mfa-lb .mfa-table thead th:first-child {{ width: 26px; padding-right: 4px; }}

@media (prefers-reduced-motion: reduce) {{
  .mfa-rating {{ animation: none; }}
  .mfa-table th, .mfa-table td, .mfa-funds li {{ transition: none; }}
}}
[data-testid="stTabs"] button[role="tab"] p {{ white-space: nowrap; }}
@media (max-width: 640px) {{
  /* Phone: pack the header controls two per row instead of one tall stack. */
  .st-key-mfa-header [data-testid="stHorizontalBlock"] {{ flex-wrap: wrap; gap: .5rem; }}
  .st-key-mfa-header [data-testid="stColumn"] {{ min-width: calc(50% - .25rem) !important; flex: 1 1 calc(50% - .25rem) !important; }}
  .st-key-mfa-header [data-testid="stColumn"]:nth-child(-n+2) {{ min-width: 100% !important; flex-basis: 100% !important; }}
  /* Phone: the menu button sits over the content column, so its bar gets a solid ground
     and the page starts below it; nothing scrolls under the button. */
  [data-testid="stHeader"] {{ background: {GROUND}; }}
  [data-testid="stMainBlockContainer"] {{ padding-top: 4rem; }}
  .mfa-head {{ font-size: 1.45rem; }}
  .mfa-rating .r {{ font-size: 2rem; }}
  .mfa-table {{ font-size: .86rem; }}
  .mfa-table th, .mfa-table td {{ padding: 8px 9px; }}
}}
</style>
"""


# ---------------------------------------------------------------------------
# Number formats
# ---------------------------------------------------------------------------

def _missing(value: object) -> bool:
    return value is None or (isinstance(value, float) and pd.isna(value))


def inr(value: Optional[float]) -> str:
    """Rupees with Indian digit grouping: 452508 -> 'Rs 4,52,508' (lakh/crore style)."""
    if _missing(value):
        return "—"
    digits = str(int(round(abs(float(value)))))
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join(groups) + "," + tail
    return ("-" if float(value) < 0 else "") + "Rs " + digits


def pct(value: Optional[float], decimals: int = 2) -> str:
    """Decimal -> '12.34%'; missing -> '—'."""
    return "—" if _missing(value) else f"{float(value) * 100:.{decimals}f}%"


def num(value: object, decimals: int = 2) -> str:
    """Plain number with fixed decimals; text passes through; missing -> '—'."""
    if _missing(value):
        return "—"
    if isinstance(value, (int, float)):
        return f"{value:,.{decimals}f}"
    return str(value)


_PLAN_SUFFIX = re.compile(r"\s*[-–(]+\s*(?:direct|growth|regular|dir\b)", re.IGNORECASE)
_SMALL_WORDS = {"of", "and", "the", "&"}


def display_case(name: str) -> str:
    """Even out fund-house casing: 'BANK OF INDIA FLEXI CAP FUND' -> 'Bank of India Flexi Cap Fund',
    'ICICI Prudential Flexi Cap fund' -> '... Fund'. Short all-caps words (SBI, UTI, ITI) stay as they are."""
    shouting = name.isupper()
    out = []
    for i, w in enumerate(name.split()):
        lw = w.lower()
        if shouting and not (len(w) <= 3 and lw not in _SMALL_WORDS | {"cap"}):
            w = lw if (lw in _SMALL_WORDS and i) else w.capitalize()
        elif w.islower() and lw not in _SMALL_WORDS:
            w = w[:1].upper() + w[1:]
        out.append(w)
    return " ".join(out)


def short_name(name: str, limit: int = 40) -> str:
    """Drop the plan/option suffix ("- Direct Plan - Growth", "- GROWTH", "(Direct)") from a scheme name.

    Fund houses write these suffixes inconsistently, so everything from the first
    dash or bracket that starts a plan/option word is cut, in any letter case.
    """
    name = display_case(_PLAN_SUFFIX.split(name, maxsplit=1)[0].strip())
    return name if len(name) <= limit else name[: limit - 1] + "…"


def brief_names(fund_names: Sequence[str]) -> dict[str, str]:
    """Shortest readable labels for tight spaces (spotlight buttons, chart line ends).

    Drops a trailing 'Fund' and any words every fund shares at the end (e.g. 'Flexi Cap'),
    so 'Parag Parikh Flexi Cap Fund' and 'HDFC Flexi Cap Fund' become 'Parag Parikh' and 'HDFC'.
    """
    words = {n: short_name(n, 200).split() for n in fund_names}
    for w in words.values():
        if len(w) > 1 and w[-1].lower() == "fund":
            w.pop()
    if len(words) > 1:
        while all(len(w) > 1 for w in words.values()) and len({w[-1].lower() for w in words.values()}) == 1:
            for w in words.values():
                w.pop()
    return {n: " ".join(w) for n, w in words.items()}


def _value(table: pd.DataFrame, row: str, col: str) -> Optional[float]:
    """A numeric cell of the metrics table, or None."""
    v = pd.to_numeric(pd.Series([table.loc[row, col]]), errors="coerce").iloc[0]
    return None if pd.isna(v) else float(v)


# ---------------------------------------------------------------------------
# Research-note blocks
# ---------------------------------------------------------------------------

def fund_ratings(table: pd.DataFrame, fund_names: list[str], bench_name: str) -> dict[str, str]:
    """Computed rating for every fund (see metrics.rating)."""
    bench = _value(table, "CAGR (%)", bench_name)
    return {f: rating(_value(table, "CAGR (%)", f), bench, _value(table, "Alpha (%)", f)) for f in fund_names}


def leader(table: pd.DataFrame, fund_names: list[str]) -> Optional[str]:
    """The fund with the highest CAGR (or absolute return when the period is under a year)."""
    row = "CAGR (%)" if any(_value(table, "CAGR (%)", f) is not None for f in fund_names) else "Absolute return (%)"
    scores = {f: _value(table, row, f) for f in fund_names}
    scores = {f: v for f, v in scores.items() if v is not None}
    return max(scores, key=scores.get) if scores else None


def category_label(categories: Sequence[str]) -> str:
    """'Equity Scheme - Flexi Cap Fund' for every fund -> 'Flexi cap'; mixed -> 'Fund'."""
    cleaned = {c.split(" - ")[-1].replace(" Fund", "").strip() for c in categories}
    if len(cleaned) == 1:
        label = cleaned.pop()
        return label[:1].upper() + label[1:].lower() if label and label != "Unknown" else "Fund"
    return "Fund"


def headline_html(table: pd.DataFrame, fund_names: list[str], short_names: dict[str, str], category: str,
                  meta: str) -> str:
    """Masthead: a serif sentence naming the leader, with the period on the right."""
    top = leader(table, fund_names)
    if top is None:
        text = f"{category} comparison: not enough history for this period"
    else:
        text = f"{category} comparison: {short_names.get(top, top)} leads on return"
        sharpe = {f: _value(table, "Sharpe ratio", f) for f in fund_names}
        sharpe = {f: v for f, v in sharpe.items() if v is not None}
        if len(fund_names) > 1 and sharpe and max(sharpe, key=sharpe.get) == top:
            text += " and risk-adjusted return"
    return (f'<div class="mfa-mast"><h1 class="mfa-head">{html.escape(text)}</h1>'
            f'<div class="mfa-meta">{html.escape(meta)}</div></div>')


def rating_box_html(fund: str, verdict: str, bench_short: str, short_names: dict[str, str]) -> str:
    """The large rating stamp for one fund."""
    color, tint = RATING_STYLE.get(verdict, RATING_STYLE["NOT RATED"])
    return (f'<div class="mfa-rating" style="--rc:{color};--rt:{tint}">'
            f'<div class="r">{verdict}</div>'
            f'<div class="f">{html.escape(short_names.get(fund, fund))}</div>'
            f'<div class="b">against {html.escape(bench_short)} (index fund NAV as proxy)</div></div>')


def key_data_html(table: pd.DataFrame, fund: str, inception: pd.Timestamp, period_word: str) -> str:
    """Key data box for one fund, like the sidebar of a research note."""
    rows = [
        (f"CAGR, {period_word}", num(_value(table, "CAGR (%)", fund)) + "%" if _value(table, "CAGR (%)", fund) is not None else "n/a"),
        ("Jensen's alpha", f"{_value(table, 'Alpha (%)', fund):+.2f}%" if _value(table, "Alpha (%)", fund) is not None else "n/a"),
        ("Beta", num(_value(table, "Beta", fund))),
        ("Sharpe ratio", num(_value(table, "Sharpe ratio", fund))),
        ("Worst fall", num(_value(table, "Max drawdown (%)", fund)) + "%" if _value(table, "Max drawdown (%)", fund) is not None else "n/a"),
        ("Recovered by", str(table.loc["Recovered on", fund]) if not _missing(table.loc["Recovered on", fund]) else "n/a"),
        ("NAV history since", f"{inception:%b %Y}"),
    ]
    body = "".join(f"<tr><td>{html.escape(k)}</td><td>{html.escape(v)}</td></tr>" for k, v in rows)
    return f'<table class="mfa-kd"><caption>Key data</caption>{body}</table>'


def thesis_html(table: pd.DataFrame, fund: str, bench_name: str, short_names: dict[str, str],
                final_value: Optional[float]) -> str:
    """Three plain-English reasons (return, risk, skill), written from the numbers."""
    bench = html.escape(short_names.get(bench_name, bench_name))
    c, bc = _value(table, "CAGR (%)", fund), _value(table, "CAGR (%)", bench_name)
    points = []
    if c is not None and bc is not None:
        grew = f", turning Rs 10,000 into {inr(final_value)}" if final_value else ""
        points.append(f"<b>Return:</b> compounded {c:.2f}% a year against {bc:.2f}% for {bench}{grew}.")
    else:
        a, ba = _value(table, "Absolute return (%)", fund), _value(table, "Absolute return (%)", bench_name)
        if a is not None and ba is not None:
            points.append(f"<b>Return:</b> gained {a:.2f}% over the period against {ba:.2f}% for {bench}.")
    v, bv = _value(table, "Volatility (%)", fund), _value(table, "Volatility (%)", bench_name)
    d, bd = _value(table, "Max drawdown (%)", fund), _value(table, "Max drawdown (%)", bench_name)
    if v is not None and bv is not None and d is not None and bd is not None:
        ride = "less bumpy than" if v < bv else ("bumpier than" if v > bv else "as bumpy as")
        fall = "shallower" if d > bd else ("deeper" if d < bd else "the same")
        points.append(f"<b>Risk:</b> it was {ride} the index ({v:.2f}% volatility vs {bv:.2f}%) and its worst fall was "
                      f"{fall}, {d:.2f}% vs {bd:.2f}%.")
    b, al = _value(table, "Beta", fund), _value(table, "Alpha (%)", fund)
    if b is not None and al is not None:
        risk = "slightly less" if 0.8 <= b < 0.97 else ("much less" if b < 0.8 else ("more" if b > 1.03 else "about the same"))
        if al >= 0:
            points.append(f"<b>Skill:</b> with a beta of {b:.2f} it took {risk} market risk than the index, yet earned "
                          f"{al:.2f}% a year above what that risk explains.")
        else:
            points.append(f"<b>Skill:</b> with a beta of {b:.2f} it took {risk} market risk than the index, but earned "
                          f"{abs(al):.2f}% a year less than that risk explains.")
    if not points:
        return '<div class="mfa-thesis"><p>Not enough history for this period. Try a longer period or another fund.</p></div>'
    return '<div class="mfa-thesis">' + "".join(f"<p>{p}</p>" for p in points) + "</div>"


RATING_ORDER = {"OUTPERFORM": 0, "IN-LINE": 1, "UNDERPERFORM": 2, "NOT RATED": 3}


def rating_order(table: pd.DataFrame, fund_names: list[str], bench_name: str) -> list[str]:
    """Funds best-first: by rating, then by CAGR (highest first). The benchmark is not included."""
    ratings = fund_ratings(table, fund_names, bench_name)

    def key(f: str) -> tuple[int, float]:
        c = _value(table, "CAGR (%)", f)
        return RATING_ORDER.get(ratings[f], 9), -(c if c is not None else float("-inf"))
    return sorted(fund_names, key=key)


def rating_summary_html(table: pd.DataFrame, fund_names: list[str], bench_name: str, colors: dict[str, str],
                        short_names: dict[str, str], focus: Optional[str] = None) -> str:
    """Every fund with its computed rating, CAGR, alpha and Sharpe; leader first, benchmark last.

    The rating tag sits under the fund name, so the table fits a narrow column or a phone
    without scrolling sideways.
    """
    ratings = fund_ratings(table, fund_names, bench_name)
    head = ['<th scope="col">Fund</th>', '<th scope="col">CAGR</th>', '<th scope="col">Alpha</th>',
            '<th scope="col">Sharpe</th>']
    body = []
    for name in rating_order(table, fund_names, bench_name) + [bench_name]:
        verdict = "BENCHMARK" if name == bench_name else ratings[name]
        color, tint = RATING_STYLE[verdict]
        tag = f'<span class="mfa-tag" style="--rc:{color};--rt:{tint}">{verdict}</span>'
        cagr, alpha, sharpe = (_value(table, r, name) for r in ("CAGR (%)", "Alpha (%)", "Sharpe ratio"))
        dim = ' class="mfa-dim"' if _dimmed(name, focus, bench_name) else ""
        body.append(
            f"<tr{dim}><th scope=\"row\">{_swatch(name, colors, bench_name)}{html.escape(short_names.get(name, name))}"
            f'<span class="mfa-rin">{tag}</span></th>'
            f"<td>{'n/a' if cagr is None else f'{cagr:.2f}%'}</td>"
            f"<td>{'n/a' if alpha is None else f'{alpha:+.2f}%'}</td>"
            f"<td>{'n/a' if sharpe is None else f'{sharpe:.2f}'}</td></tr>")
    return '<div class="mfa-rs">' + _table("Rating summary", head, body) + "</div>"


# ---------------------------------------------------------------------------
# Building blocks for tables
# ---------------------------------------------------------------------------

def _swatch(name: str, colors: dict[str, str], bench_name: str) -> str:
    color = BENCH_SWATCH if name == bench_name else colors.get(name, BENCH_SWATCH)
    return f'<span class="mfa-swatch" style="background:{color}" aria-hidden="true"></span>'


def _header_label(name: str, bench_name: str, short_names: dict[str, str]) -> str:
    label = html.escape(short_names.get(name, name))
    return label + (' <span class="mfa-na">(benchmark)</span>' if name == bench_name else "")


def _cell(text: str, best: bool, dim: bool = False) -> str:
    classes = ["mfa-dim"] if dim else []
    content = html.escape(text)
    if best:
        classes.append("mfa-best")
        content = f'<span class="mfa-sr">Best: </span>{content}'
    if text in ("n/a", "—"):
        classes.append("mfa-na")
    cls = f' class="{" ".join(classes)}"' if classes else ""
    return f"<td{cls}>{content}</td>"


def _dimmed(name: str, focus: Optional[str], bench_name: str) -> bool:
    """With a spotlight on, every other fund steps back; the benchmark stays as the yardstick."""
    return bool(focus) and name != focus and name != bench_name


def _head_cls(name: str, focus: Optional[str], bench_name: str) -> str:
    if focus and name == focus:
        return ' class="mfa-lit"'
    return ' class="mfa-dim"' if _dimmed(name, focus, bench_name) else ""


def _best_index(values: pd.Series, rule: str) -> list:
    """Labels holding the best value (needs at least two values to compete)."""
    values = pd.to_numeric(values, errors="coerce").dropna()
    if len(values) < 2:
        return []
    target = values.max() if rule == "max" else values.min()
    return list(values[values == target].index)


def _table(caption: str, head_cells: list[str], body_rows: list[str]) -> str:
    return (
        f'<div class="mfa-wrap"><table class="mfa-table"><caption>{html.escape(caption)}</caption>'
        f'<thead><tr>{"".join(head_cells)}</tr></thead><tbody>{"".join(body_rows)}</tbody></table></div>'
    )


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def metrics_table_html(
    table: pd.DataFrame, best: dict[str, list[str]], colors: dict[str, str], bench_name: str, short_names: dict[str, str],
    focus: Optional[str] = None,
) -> str:
    """Full metrics table: grouped rows, a hover definition on each metric name, best fund value starred."""
    cols = list(table.columns)
    head = ['<th scope="col">Metric</th>'] + [
        f'<th scope="col" title="{html.escape(c)}"{_head_cls(c, focus, bench_name)}>'
        f'{_swatch(c, colors, bench_name)}{_header_label(c, bench_name, short_names)}</th>'
        for c in cols
    ]
    body = []
    for group, rows in METRIC_GROUPS:
        body.append(f'<tr class="mfa-group"><th scope="colgroup" colspan="{len(cols) + 1}">{html.escape(group)}</th></tr>')
        for row in rows:
            tip = html.escape(METRIC_TIPS.get(row, ""))
            cells = [f'<th scope="row"><span class="mfa-term" title="{tip}">{html.escape(row)}</span></th>']
            cells += [_cell(num(table.loc[row, c]) if not _missing(table.loc[row, c]) else "n/a",
                            c in best.get(row, []), _dimmed(c, focus, bench_name))
                      for c in cols]
            body.append("<tr>" + "".join(cells) + "</tr>")
    return _table("Key metrics for each fund and the benchmark", head, body)


def entity_table_html(
    df: pd.DataFrame,
    colors: dict[str, str],
    bench_name: str,
    short_names: dict[str, str],
    formats: dict[str, Callable[[object], str]],
    best_rules: dict[str, str],
    caption: str,
    first_header: str = "Fund",
    focus: Optional[str] = None,
) -> str:
    """One row per fund (index = full scheme name), one column per measure; best fund per column starred."""
    head = [f'<th scope="col">{html.escape(first_header)}</th>'] + [f'<th scope="col">{html.escape(c)}</th>' for c in df.columns]
    ranked = [i for i in df.index if i != bench_name]
    best = {c: _best_index(df.loc[ranked, c], rule) for c, rule in best_rules.items() if c in df.columns}
    body = []
    for name in df.index:
        dim = _dimmed(name, focus, bench_name)
        cls = ' class="mfa-dim"' if dim else ""
        cells = [f'<th scope="row"{cls}>{_swatch(name, colors, bench_name)}{_header_label(name, bench_name, short_names)}</th>']
        for c in df.columns:
            fmt = formats.get(c, num)
            cells.append(_cell(fmt(df.loc[name, c]), name in best.get(c, []), dim))
        body.append("<tr>" + "".join(cells) + "</tr>")
    return _table(caption, head, body)


def year_table_html(
    cal: pd.DataFrame, colors: dict[str, str], bench_name: str, short_names: dict[str, str], ytd_year: Optional[int],
    focus: Optional[str] = None,
) -> str:
    """Calendar-year returns: one row per year (newest first); each year's best fund is starred."""
    cols = list(cal.columns)
    funds = [c for c in cols if c != bench_name]
    head = ['<th scope="col">Year</th>'] + [
        f'<th scope="col"{_head_cls(c, focus, bench_name)}>{_swatch(c, colors, bench_name)}'
        f'{_header_label(c, bench_name, short_names)}</th>' for c in cols
    ]
    body = []
    for year in sorted(cal.index, reverse=True):
        best = _best_index(cal.loc[year, funds], "max")
        label = f"{year} (YTD)" if year == ytd_year else str(year)
        cells = [f'<th scope="row">{label}</th>'] + [_cell(pct(cal.loc[year, c]), c in best, _dimmed(c, focus, bench_name))
                                                     for c in cols]
        body.append("<tr>" + "".join(cells) + "</tr>")
    return _table("Calendar-year return of each fund and the benchmark", head, body)


def fund_list_html(rows: Sequence[tuple[str, str, str, pd.Timestamp]], colors: dict[str, str], bench_name: str,
                   short_names: dict[str, str], focus: Optional[str] = None) -> str:
    """Compact one-line description per fund: name · fund house · category · first NAV date."""
    items = []
    for name, house, category, inception in rows:
        role = " (benchmark)" if name == bench_name else ""
        cls = ' class="mfa-dim"' if _dimmed(name, focus, bench_name) else ""
        items.append(
            f"<li{cls}>{_swatch(name, colors, bench_name)}<b>{html.escape(short_names.get(name, name))}</b>{role}"
            f" · {html.escape(house)} · {html.escape(category)} · NAV since {inception:%b %Y}</li>"
        )
    return f'<ul class="mfa-funds">{"".join(items)}</ul>'


def volatility_peak_note(vols: dict[str, pd.Series], short_names: dict[str, str]) -> str:
    """Caption naming the highest 1-year volatility reading in the window shown."""
    best_name, best_date, best_val = None, None, -1.0
    for name, series in vols.items():
        if series.empty:
            continue
        if float(series.max()) > best_val:
            best_name, best_date, best_val = name, series.idxmax(), float(series.max())
    if best_name is None:
        return ""
    return (f"Highest reading in this window: {best_val * 100:.1f}% for "
            f"{short_names.get(best_name, best_name)} on {best_date:%d %b %Y}.")


def leaders_sentence(category: str, leaders: dict[int, str]) -> str:
    """One serif line naming each period's top fund, longest period first."""
    parts = [(yrs, short_name(name, 60)) for yrs, name in sorted(leaders.items(), reverse=True) if name]
    if not parts:
        return ""
    first = f"{html.escape(parts[0][1])} leads {category.lower()} over {parts[0][0]} years"
    rest = [f"{html.escape(n)} over {y}" for y, n in parts[1:]]
    if len(rest) == 1:
        first += ", " + rest[0]
    elif rest:
        first += ", " + ", ".join(rest[:-1]) + " and " + rest[-1]
    return f'<p class="mfa-lead">{first}.</p>'


def leaderboard_html(top: pd.DataFrame, title: str, qualified: int, years: int, in_comparison: set[str]) -> str:
    """One ranked list (top N by CAGR) in research-note style; funds already being compared are marked."""
    if top.empty:
        return (f'<h2 class="mfa-h">{html.escape(title)}</h2>'
                f'<p class="mfa-sub">No fund in this category has {years} years of NAV history yet.</p>')
    head = ['<th scope="col">#</th>', '<th scope="col">Fund</th>', '<th scope="col">CAGR</th>',
            '<th scope="col">Sharpe</th>', '<th scope="col">Worst fall</th>']
    body = []
    for i, row in top.iterrows():
        name = row["Fund"]
        mark = ' <span class="mfa-tag" style="--rc:#d6b25e;--rt:rgba(214,178,94,.14)">IN COMPARISON</span>' \
            if name in in_comparison else ""
        body.append(
            f'<tr><td class="mfa-rank">{i + 1}</td>'
            f'<th scope="row">{html.escape(short_name(name, 46))}{mark}</th>'
            f'<td class="{"mfa-best" if i == 0 else ""}">{pct(row["CAGR"])}</td>'
            f'<td>{num(row["Sharpe"])}</td><td>{pct(row["Worst fall"], 1)}</td></tr>')
    table = _table(f"{title}: top funds by CAGR", head, body)
    return (f'<div class="mfa-lb"><h2 class="mfa-h">{html.escape(title)}</h2>'
            f'<p class="mfa-sub">Top {len(top)} of {qualified} funds with {years}+ years of history</p>{table}</div>')
