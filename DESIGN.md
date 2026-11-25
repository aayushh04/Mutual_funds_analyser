---
name: MF Analyser Research
description: A broker's research note on Indian mutual funds, set at night in warm charcoal, ivory ink and one house gold.
colors:
  ground: "#111315"
  sheet: "#1a1d21"
  line: "#2a2d31"
  rule-strong: "#3a3e44"
  ink: "#e9e4da"
  ink-soft: "#d9d3c7"
  muted: "#a39d92"
  gold: "#d6b25e"
  gold-fill: "#8a6a22"
  gold-fill-hover: "#9b7828"
  fund-1: "#3987e5"
  fund-2: "#d95926"
  fund-3: "#199e70"
  fund-4: "#c98500"
  benchmark: "#8e939a"
  outperform: "#6fd3a0"
  in-line: "#c9ccd1"
  underperform: "#f08a96"
typography:
  display:
    fontFamily: "'Source Serif 4', Georgia, serif"
    fontSize: "clamp(1.7rem, 2.3vw, 2.5rem)"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "-0.01em"
  headline:
    fontFamily: "'Source Serif 4', Georgia, serif"
    fontSize: "1.85rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.005em"
  title:
    fontFamily: "'Source Serif 4', Georgia, serif"
    fontSize: "1.3rem"
    fontWeight: 600
    lineHeight: 1.25
  lead:
    fontFamily: "'Source Serif 4', Georgia, serif"
    fontSize: "1.22rem"
    fontWeight: 600
    lineHeight: 1.4
  body:
    fontFamily: "'Source Sans 3', sans-serif"
    fontSize: "1.02rem"
    fontWeight: 400
    lineHeight: 1.55
  table:
    fontFamily: "'Source Sans 3', sans-serif"
    fontSize: "0.93rem"
    fontWeight: 400
    fontFeature: "tnum"
  label:
    fontFamily: "'Source Sans 3', sans-serif"
    fontSize: "0.74rem"
    fontWeight: 700
    letterSpacing: "0.05em"
rounded:
  swatch: "2px"
  tag: "3px"
  stamp: "6px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "18px"
  xl: "24px"
components:
  button-primary:
    backgroundColor: "{colors.gold-fill}"
    textColor: "#ffffff"
  button-primary-hover:
    backgroundColor: "{colors.gold-fill-hover}"
  chip-fund:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
  rating-stamp:
    textColor: "{colors.outperform}"
    typography: "{typography.display}"
    rounded: "{rounded.stamp}"
    padding: "18px 20px"
  rating-tag:
    typography: "{typography.label}"
    rounded: "{rounded.tag}"
    padding: "2px 8px"
  data-table:
    textColor: "{colors.ink}"
    typography: "{typography.table}"
    padding: "9px 12px"
---

# Design System: MF Analyser Research

## Overview

**Creative North Star: "The Research Desk at Night"**

The app reads as a sell-side research note on a set of mutual funds, not as a fintech dashboard. A serif headline sentence names the leader, a rating stamp gives the computed verdict in words, three plain-English paragraphs argue it, and hairline-ruled tables carry the numbers. Everything sits on one warm charcoal ground; there are no KPI tiles, no card grid, no drop shadows.

Density is that of a printed note: tabular figures, hairline rules between rows, captions in muted ivory under every chart and table explaining what the numbers mean. Colour does two jobs only. A single house gold marks the brand, the active choice and the one primary action. A fixed four-hue categorical set identifies funds in charts and tables, with the benchmark always grey and always named.

Dark mode is binding. Motion is a single settle of the rating stamp; everything else is short opacity and background transitions on state change.

**Key Characteristics:**
- Warm charcoal ground with one slightly raised sheet tone; ivory ink, never pure white body text.
- Serif (Source Serif 4) for the headline, rating, section heads and the leader sentence; Source Sans 3 with tabular figures for tables and controls.
- Hairline rules instead of cards; the only bordered containers are the rating stamp and the relative-performance chart panel.
- One house gold, rationed.
- Every signal carried in words as well as colour: rating words, named line ends, a starred best value, "(benchmark)" labels.

## Colors

Warm charcoal neutrals and ivory ink, one rationed gold, a fixed colour-blind-safe set for funds, and three rating hues that always travel with their word.

### Primary
- **House Gold** (gold): gold as text on the ground (8:1): the "Research" half of the brand mark, the active tab and active Spotlight segment label, the lit column header under Spotlight, the focus ring, links.
- **Gold Leaf Fill** (gold-fill): the fill of the one primary action, Add fund, in the header; also the theme primary for Streamlit's own active fills. Hover deepens to gold-fill-hover. The chart range selector's active button uses a darker sibling (#7a5c1c) of the same fill.

### Secondary (data series)
- **Fund Blue / Fund Ember / Fund Jade / Fund Ochre** (fund-1 to fund-4): assigned in selection order, not by rank, so a fund keeps its colour in every chart, swatch and table header for the whole session.
- **Benchmark Grey** (benchmark): the benchmark line, bar and swatch, always paired with the word "(benchmark)" or "BENCHMARK".

### Tertiary (ratings)
- **Outperform Green** (outperform), **In-line Grey** (in-line), **Underperform Rose** (underperform): rating text colours, each over its own translucent tint of the same hue (13-14% alpha). Outperform green also colours the starred best value in tables. NOT RATED uses muted.

### Neutral
- **Night Charcoal** (ground): the page, and the background of sticky table row headers so scrolled cells pass under them.
- **Raised Sheet** (sheet): popovers, fund chips, hover labels on charts, range-selector buttons.
- **Hairline** (line): row rules, the header bar's bottom rule, the masthead rule.
- **Strong Rule** (rule-strong): table head underline, group-row rule, chip border, chart axis lines.
- **Ivory Ink** (ink): body text and figures (14:1).
- **Soft Ivory** (ink-soft): thesis paragraphs and chart text, one step quieter than ink.
- **Warm Muted** (muted): captions, table column heads, metadata, axis ticks (6.9:1).

### Named Rules
**The One Gold Rule.** Gold appears only on the brand, the active state (tab, Spotlight segment, chart range button, spotlit column) and the primary action, Add fund. Selected-fund chips are neutral sheet with an ivory label; gold never decorates content.

**The Word Plus Colour Rule.** No rating, series or best value is identified by colour alone. Ratings are written as words; chart line ends are labelled "name value"; the best value carries a star and a screen-reader "Best:"; the benchmark is named.

**The Fixed Seat Rule.** A fund's colour follows its position in the selection, in the order fund-1, fund-2, fund-3, fund-4, and never changes between charts or tabs.

## Typography

**Display Font:** Source Serif 4 (with Georgia, serif)
**Body Font:** Source Sans 3 (with sans-serif)

**Character:** A text serif with optical sizing gives the headline and verdict the authority of a printed note; a humanist sans with tabular figures keeps dense tables and controls quiet and aligned.

### Hierarchy
- **Display** (700, clamp 1.7-2.5rem, 1): the rating word in the stamp. 2rem on phones.
- **Headline** (600, 1.85rem, 1.2, max 42ch): the masthead sentence naming the leader. 1.45rem on phones. Streamlit headings follow the theme scale (2rem / 1.35rem / 1.12rem, all 600).
- **Title** (600, 1.3rem, 1.25): section heads such as "Why it leads", "Relative performance", leaderboard titles. Fund name in the stamp at 1.2rem; table captions and group rows at about 1rem, all serif.
- **Lead** (600, 1.22rem, 1.4, max 70ch): the one serif sentence that names each period's leader on Top funds.
- **Body** (400, 1.02rem, 1.55, max 62ch): thesis paragraphs, with the reason word ("Return:", "Risk:", "Skill:") in 600 white. Captions at Streamlit's caption size in muted, max 80ch.
- **Table** (400, 0.93rem, tabular figures): every table; column heads 600 at 0.82rem in muted. 0.86rem on phones.
- **Label** (700, 0.74rem, 0.05em tracking, uppercase words): rating tags only (OUTPERFORM, IN-LINE, UNDERPERFORM, BENCHMARK, NOT RATED).

### Named Rules
**The Serif Speaks Rule.** Serif carries sentences and verdicts (headline, rating, section heads, leader sentence); every number is set in the sans with tabular figures.

**The No Kicker Rule.** No small uppercase label sits above a heading. Uppercase letter-spaced type is reserved for rating tags, which are data.

## Layout

A single full-width column capped at 1480px, with no sidebar. Top to bottom: a header bar (brand left; fund chips, Add fund, period and Benchmark settings right) closed by a hairline; a masthead with the serif headline sentence left and the period and risk-free rate right, also closed by a hairline; the Spotlight segmented control; then tabs as report sections (Summary, Top funds, Risk, Consistency, Calendar years, SIP backtest, Glossary).

Summary is three columns at 3.2 : 5 : 4.6 with a large gap: rating stamp and Key data left; "Why it leads" and the rating summary table centre; the relative-performance chart in its panel right. Top funds sets three leaderboards side by side under the leader sentence.

Spacing is a loose 4px rhythm: 4, 6, 8, 10, 12, 14, 18 and 24px recur (tag inset 2px 8px, cell padding 9px 12px, stamp padding 18px 20px, masthead gap 24px). Text measures are capped: headline 42ch, thesis 62ch, lead 70ch, captions 80ch.

At 640px and below the header controls pack two per row (brand and chips full width), the page starts 4rem down under a solid header bar, columns stack, type steps down, and table cells tighten to 8px 9px. Wide tables scroll inside their own wrapper with edge shadows and a sticky first column; the rating summary puts each rating tag under the fund name so Fund, CAGR, Alpha and Sharpe fit 390px without sideways scroll.

## Elevation & Depth

Flat. Depth comes from tone and rules: the ground, one raised sheet tone for popovers, chips and chart hover labels, and hairlines between rows. There are no drop shadows on surfaces. The only shadows are functional: scroll-edge shading on overflowing tables (radial gradients that appear only when content is cut off) and a 2px inset gold underline on the spotlit column head.

### Named Rules
**The Ruled Page Rule.** Separate with a 1px hairline, never with a card or a shadow. A bordered container is earned only by the rating stamp and the single chart panel on Summary.

## Shapes

Nearly square. Rating tags are 3px, swatches 2px, the rating stamp 6px, calendar bars 3px at the top; Streamlit controls use the theme's small radius. Borders are 1px throughout. The best-value star is a small filled star drawn as a mask in the cell's text colour, not a glyph.

## Components

### Buttons
- **Shape:** the theme's small radius with a 1px border.
- **Primary (Add fund):** gold-leaf fill and border with white label and icon; hover deepens to gold-fill-hover. Exactly one primary per view.
- **Secondary (period, Benchmark):** Streamlit's default bordered control on the ground, ivory label.
- **Focus:** 2px gold outline, 2px offset, on every focusable element.

### Chips
- **Style:** the selected funds in the header, as a raised-sheet tag with a strong-rule border and a full, untruncated ivory short name.
- **State:** neutral always. Selection is shown by presence, not by colour.

### Rating Stamp (signature)
- A bordered box tinted with the rating's own hue (1px border in the rating colour, background its translucent tint, 6px radius, 18px 20px padding). The rating word in display serif, the fund name below in title serif, then "against [benchmark] (index fund NAV as proxy)" in muted.
- Settles in once on load: 0.55s, translate 6px up and fade, cubic-bezier(.16,1,.3,1). No motion under reduced-motion.

### Rating Tag
- Uppercase rating word at label size on its translucent tint, 3px radius, 2px 8px inset. In the rating summary it sits on its own line under the fund name.

### Key Data
- A two-column ruled list under the stamp: serif caption "Key data", labels left, 600 tabular values right, a hairline under every row.

### Tables
- Right-aligned tabular figures, left-aligned first column; muted 0.82rem column heads over a strong rule; hairline row rules; serif group rows (Return, Risk, ...) on the metrics table; a 9px colour swatch before each fund name; row hover lifts to #1b1e22.
- Sticky row header on the ground; horizontal overflow scrolls inside the wrapper with edge shading.
- Best value per row or column in outperform green with a masked star and a screen-reader "Best:". The benchmark is never ranked. Missing values read "n/a" or an em dash in muted.
- Metric names carry a dotted underline and a hover definition.

### Spotlight
- A segmented control (All funds plus one segment per fund by brief name), active segment label in gold. When a fund is spotlit, every other fund's rows, columns and list items drop to 0.38 opacity while the benchmark stays; its column head turns gold with a 2px inset gold underline. In charts the spotlit line widens to 3px, others fall to 0.2 opacity and 1.5px, and the drawdown chart shades the spotlit fund to zero.

### Navigation
- Streamlit tabs as report sections, labels 600 and never wrapped; the active tab label is gold.

### Charts
- Transparent paper and plot so charts sit on the page; muted ticks, #23262a gridlines, strong-rule axis lines, no vertical grid.
- Fund lines 2px in their fixed seat colour, benchmark 1.5px grey at 0.9 opacity, labelled "(benchmark)".
- A 1Y / 3Y / 5Y / All range selector on time charts in sheet buttons, the active one gold-filled; a full-height crosshair and one unified hover box on the sheet tone.
- The relative-performance chart is rebased to 100 (dotted reference line), drawn from weekly closes for display, with no legend: each line end is labelled "name value" in its own colour, anchored to the plot's right edge.
- SIP charts add the invested amount as a dotted ivory step line.

## Do's and Don'ts

### Do:
- **Do** keep gold to the brand, the active tab, segment or range button, the spotlit column and the Add fund action.
- **Do** write every rating as a word (OUTPERFORM, IN-LINE, UNDERPERFORM, NOT RATED, BENCHMARK) next to its colour.
- **Do** name every chart line end "name value", and label the benchmark "(benchmark)" everywhere.
- **Do** assign fund colours by selection order from fund-1 to fund-4 and keep them fixed across every chart and table.
- **Do** set every number in Source Sans 3 with tabular figures, right-aligned in tables, Indian grouping for rupees.
- **Do** separate rows and sections with 1px hairlines on the charcoal ground.
- **Do** check every view at 390px: header controls two per row, no sideways scroll on the rating summary, wide tables scrolling inside their own wrapper.
- **Do** honour reduced motion: no stamp settle, no table transitions.

### Don't:
- **Don't** add a light theme; dark mode is binding.
- **Don't** tint the selected-fund chips gold or any fund colour; they stay neutral sheet.
- **Don't** put a small uppercase kicker or eyebrow label above a heading.
- **Don't** build KPI tiles, card grids or drop shadows; the rating stamp and the one chart panel are the only bordered containers.
- **Don't** let colour alone carry a rating, a series or a best value.
- **Don't** set running text in pure white (white is kept for the bold reason words in the thesis and labels on the gold fill), or any text below the muted tone's 6.9:1 contrast.
