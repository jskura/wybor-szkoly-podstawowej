# UX specification

Screens, states and the rules that keep the interface honest. Polish UI, English
code and docs (D15).

Decision: D34. Validation: [`04-validation.md`](./04-validation.md) §V35–V37.

---

## 1. Rules that apply to every screen

These are not style preferences; they are rule 5 and rule 6 made concrete, and
each is testable.

1. **No bare number.** Every aggregate appears with its sample size and its range,
   in the same visual unit, at the same prominence. Not in a tooltip, not behind a
   hover, not in a footnote.
2. **No unlabelled price.** Every price carries *cena ofertowa* or *cena
   transakcyjna*. The two never share an axis, a colour, or a summary row.
3. **Nothing hidden for thinness.** `n=3` renders with the number and the range,
   never as "insufficient data" (D17).
4. **`Unknown` is visible, not blank.** Missing buildability reads *"brak danych —
   sprawdź w gminie"*. An empty cell would read as "nothing to worry about".
5. **Model output is marked.** Anything from the regression carries a *"szacunek
   modelu"* marker (D33). Comparable-based numbers do not need one.
6. **Provenance is one interaction away**, everywhere, always.

## 2. Screens

### 2.1 Map (J1) — the entry point

- Choropleth of the three target units by gmina; metric selector (median price per
  m², mix-adjusted change, listing count); **price-type toggle** that switches the
  entire map between offering and sales, never blending.
- Filters: budget, area range, asset class, buildability, utilities, travel time
  to a configured anchor.
- Gminas with no matching supply are visibly distinct from gminas with thin
  supply — these are different facts and must not share a colour.
- **Thin-data rendering**: gminas below n=5 are hatched rather than solid. The
  number is still available on click (rule 3 above); the hatch signals that the
  colour is weakly supported. This is the visual half of D18.
- Side panel per gmina: median, range, n, mix-adjusted 12-month change, both price
  types side by side, and the asking-vs-sales gap.

### 2.2 Plot page (J2) — the verdict

Layout order, top to bottom, chosen so the weakest evidence is never the most
prominent element:

1. **Verdict block** — asking price, expected offering range, expected sales
   range, each with n and basis (`05` §5). Verdict phrased relative to the range.
2. **Buildability** — designation, or the explicit unknown state, with what it
   permits where known.
3. **Risk badges** — road access, soil class, flood zone, easements, and any
   disagreement between `zoning_claim` and `buildability` (`06` §1).
4. **Nature attributes** — forest, water, protected status, noise distances, each
   as its own value (FR-19). Protected status shown as both amenity and
   constraint (FR-20).
5. **Comparable set** — map and table, every contributing plot listed, each
   removable with live recompute. The widening step is stated: *"porównania z
   promienia 25 km"*.
6. **Price history** — the interval series (`08` §2), with crawl gaps marked.
7. **Negotiation panel** (J5) — time listed (never "time to sale"), price changes,
   gmina asking-vs-sales gap.

### 2.3 What-if calculator (D31)

A first-class screen, not a mode of the plot page, because it answers the question
with no listing involved: feature inputs on the left, estimate range on the right,
recomputing live. Four tabs matching `05` §6: hypothetical plot, same plot
elsewhere, feature values, value if buildable — the last two carrying their
mandatory caveats as visible copy, not tooltips.

### 2.4 Comparison board (J3)

Column per plot, rows highlighted where plots differ materially, identical rows
collapsed. Weighted ranking with the weights visible and adjustable, and the
reasoning shown as a contribution breakdown rather than a single score.

### 2.5 Trends (J7)

Mix-adjusted index as the headline series, plain median available as a secondary
series, both with sample-size bars beneath (`05` §7). Price types on separate
charts. The incomplete-period marker (`08` §4) is mandatory on sales series.

### 2.6 Coverage & method (J8)

Per gmina: listings collected, last crawl, parcel-match rate, zoning-known rate,
observation counts per price type, geocoding precision distribution (`07` §3).
Plus a written method note per metric, linking to `05`.

## 3. States

Every data-bearing component specifies all five. Missing state handling is where
interfaces quietly start lying.

| State | Rule |
|---|---|
| **Loading** | Skeleton; never a zero or a dash that could be read as a value |
| **Empty (no data)** | *"Brak danych"* plus why — not yet crawled, no listings, or outside scope. These are different and say so |
| **Thin (n < 5)** | Number **and** min–max **and** n, with hatched/muted treatment |
| **Stale** | Where the last crawl is older than expected, the age is shown on the number itself |
| **Error** | What failed and what is still trustworthy — a failed sales query never blanks the offering figures |

## 4. Language and terminology

Polish UI throughout, using the terms in [`12-glossary.md`](./12-glossary.md)
consistently. Numbers formatted Polish-style: space thousands separator, comma
decimal, `zł/m²`. Dates as `DD.MM.YYYY`.

Terms never to translate loosely: *plan ogólny*, *MPZP*, *wypis i wyrys*,
*działka*, *media*, *droga dojazdowa*, *cena ofertowa*, *cena transakcyjna*.

## 5. Deferred

Mobile layout, saved searches and alert digests (J4, M5), and the notebook access
surface (O9) are not specified here. Per rule 4, each needs its validation method
before implementation.
