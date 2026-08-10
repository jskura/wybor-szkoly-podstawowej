# Assumption audit — self-review of docs 00–16

A critical review of my own planning work against `CLAUDE.md` rule 3: *resolve
ambiguity by asking, not by assuming*. Written before challenging these with the
owner, so the findings are not shaped by the answers.

Verdict up front: **the documents are internally detailed but rest on a large
number of choices I made silently, several arithmetic contradictions, and one
unverified fact that could invalidate the whole offering-price layer.**

---

## A. Contradictions inside my own documents

These are errors, not judgement calls.

### A1 — The crawl budget is impossible by a factor of ~18

- `10` §2 promises a **full daily pipeline in under 4 hours**.
- `03` and PRD §12 promise **single-digit requests per minute per host**.
- `10` §1 estimates **10k–40k active listings**.
- FR-3 says **every crawl records the observed state of each listing**.

9 req/min × 4 h = **2,160 requests**. Observing 40,000 listings needs 40,000. The
politeness policy and the daily-refresh promise cannot both hold.

There is a resolution I never wrote down: fetch **list pages** (≈40 listings each,
so ~1,000 requests for the whole corpus) for price and active status, and fetch
**detail pages only for new or changed listings** (500–2,000/day). That lands at
roughly 3–6 hours for one portal — still at or over budget, and E4.7 adds a second
portal. The strategy needs specifying, and the 4-hour target is probably wrong.

### A2 — Mix adjustment is not computable at gmina level

`05` §7 defines strata as asset class × buildability × area band =
**4 × 4 × 5 = 80 strata**. FR-41 makes the mix-adjusted index the **headline trend
figure**, and `15` keys `metric_unit_month` by gmina.

With ~25k land listings across ~500 gminas, the average gmina holds ~50 listings —
rural gminas far fewer — spread over 80 strata. Most strata are empty; the typical
non-empty stratum has n=1. **A fixed-basket index over mostly-empty strata is
noise, not a measurement.**

Mix adjustment is viable at **powiat** (66 units, ~380 listings each) or
voivodeship level, not gmina. I mandated it at the level where it cannot work.

### A3 — Rule 7 and stratification interact badly on the map

Because `metric_unit_month` is keyed by gmina × class × buildability, most cells
hold n=1–5. "Always show, always flag" then produces a choropleth composed largely
of single-observation cells. Each is *honestly* labelled, but a map where most
tiles rest on one listing may be actively misleading in aggregate — the colour
carries more visual weight than the caveat.

I never resolved this. It is the strongest argument I can make *against* my own
reading of rule 7, and it deserves a decision rather than my quiet assumption that
per-tile honesty is sufficient.

### A4 — "Never a point estimate" contradicts the `median` field

V17 asserts *"no internal code path produces a bare scalar price"*. Both `05` §1
and the `Estimate` type in `14` §2.4 carry a **`median`** field, which is exactly a
bare scalar price. Either the rule means "never a point *without* a range" — in
which case V17 is mis-stated — or the `median` field must go. As written the spec
fails its own test.

### A5 — I dropped my own recommendation without saying so

PRD v0.1 §11 offered a Streamlit shortcut and called it *"reversible… recommended
if the first audience is us"*. You then answered **private + a few friends** — the
exact condition under which I had recommended it. I never resurfaced it, and v0.2
silently committed to FastAPI + Next.js + MapLibre + self-hosted OSRM + Nominatim.

Frontend and API (E15–E21) are roughly **half the total effort** in `13`. For 1–5
users this is likely the largest misallocation in the plan.

### A6 — Success metrics assume a user research programme that cannot exist

PRD §5 targets *"≤10 min to shortlist (moderated test, 5 users)"* and *"≥3 of 5
users say the verdict changed their view"*. D1 says the audience is you plus a few
friends. There is no pool of five test users. These are leftovers from when I
imagined a broader product, and they should be replaced with something you could
actually run.

### A7 — Infrastructure does not fit the box I specified

`10` §6 specifies a **4 vCPU / 8 GB / 160 GB VPS** running PostGIS **plus
self-hosted Nominatim plus OSRM**. A country-extract Nominatim import is
memory- and time-hungry — commonly recommended well above 8 GB — and OSRM needs
several GB more. I sized the box before choosing the components, and did not check
that they fit. Raw-document retention (`10` §4: 90 days hot, 12-month archive) also
likely exceeds 160 GB once list pages, which change daily, are counted.

---

## B. Choices I made that were never yours

Rule 3 says these should have been questions. Grouped by how much damage a wrong
default does.

### B1 — Metric definitions at the heart of the valuation (highest impact)

Every number below is mine, and the entire product output depends on them:

| Parameter | My value | Where |
|---|---|---|
| Comparable area band | **±50%** | `05` §3 |
| Comparable recency window | **12 months** | `05` §3 |
| Minimum comparables before widening | **5** | `05` §3 |
| Widening ladder rungs | gmina → 10 km → 25 km → powiat → powiat wide | `05` §3 |
| IQR vs min–max switch | **n = 5** | rule 7 impl. |
| Strata area bands | **<800 / 800–1500 / 1500–3000 / 3000–10k / >10k m²** | `05` §7 |
| Land area validity band | **100 m² – 500,000 m²** | FR-12 |
| Price validity band | **1 – 100,000 PLN/m²** | FR-12 |
| Dedup false-negative target | **≤3%** | §5 |
| Dedup false-merge target | **≤1%** | §5 |
| Extraction precision target | **≥0.95** | `06` §4 |
| Labelled sample sizes | **200** adverts, **200** listings | `06`, `04` |
| Crawl rate | **single-digit req/min** | `03` |

Two are probably wrong on their face: a **500,000 m² (50 ha) cap** excludes the
larger agricultural parcels your investor journey (J2/P2) explicitly targets, and a
**200-advert labelled set** will contain very few positive examples for rarer
attributes like gas or mains sewage, making per-attribute precision unmeasurable
for exactly the attributes that are hardest to extract.

### B2 — I invented your users

`01` §Personas describes "Marek & Ania", a couple in their 30s, building in 2–4
years, with a **150–350k PLN plot budget**. None of this came from you. I then wrote
journeys, filters and success metrics against a fictional person.

Meanwhile **I never asked about you**: your actual budget, your timeline, whether
you are buying one plot or several, or whether you are buying at all rather than
valuing something you own.

### B3 — I never asked what your three addresses are

You gave Niemcewicza (Warszawa), Kamienna (Elbląg), Budy Grabskie 53. I assumed all
three are *destinations to commute to*. They could as easily be: your home, family
you visit, and **a plot you already own**. If Budy Grabskie 53 is already yours, the
central question may be "what is mine worth / should I buy the neighbouring plot"
rather than "where should I search", which reorders the whole product.

### B4 — Schools and amenities are entirely absent

This repository is named **`wybor-szkoly-podstawowej`** — primary school choice. If
you have school-age children, catchment and distance to school is plausibly a
top-three factor in where you buy land. I asked about travel time and nature; I
never asked about **schools, kindergartens, shops, or health care**. There is not a
single amenity attribute in 17 documents. Given the repository's own history this
is a conspicuous omission.

### B5 — I demoted housing almost out of the product

Your first sentence was *"compare prices of housing and land"*, with land as the
**priority**. I translated priority into: housing is collected but invisible until
M5, the last milestone. Priority is not exclusivity, and I never checked.

### B6 — Technology beyond what you delegated

You delegated "Python + Postgres/PostGIS". I additionally chose FastAPI, Next.js,
MapLibre, OSRM, Nominatim, Docker Compose, pytest, monthly partitioning, and the
entire module layout. Reasonable inferences, but see A5 — the frontend choice in
particular is a large unexamined commitment.

### B7 — Unstated methodological choices

- **Base period for the mix-adjusted index** is never specified (`05` §7). If it is
  the first month observed, the whole series is anchored to a possibly atypical month.
- **Anchor applicability**: I compute travel time from every plot to all three
  anchors. An Elbląg-area plot is ~4 hours from Warsaw; showing that number for
  every plot is noise. Anchors are probably area-specific.
- **Nature attributes require `address` precision or better** (`07` §3, my rule).
  Most portal listings will be `pin` precision. So a feature you ranked as a
  priority may be **absent for the majority of listings** — a consequence of my own
  gating rule that I never surfaced.

---

## C. Unverified external facts

### C1 — Whether we may crawl the portals at all *(project-defining)*

The entire offering-price layer — and therefore J1, J2, J3, J9 and most of the
product — assumes the target portals' `robots.txt` permits crawling listing pages.
**I never checked, and I cannot check from this environment**: the network egress
proxy blocks both domains (403 on CONNECT).

If listing paths are disallowed, the honest options collapse to registry-only data
(GUS/RCN), which is powiat-level and quarterly — a fundamentally different and much
smaller product. This is the single largest risk in the plan and it is checkable in
minutes from any normal browser.

### C2 — Whether portals are even the right source for your areas

Rural and agricultural land frequently trades off-portal — via gmina notice boards,
ANR/KOWR, local agents and word of mouth. Both your anchor areas are rural. I noted
this once in `03` and then planned as though portal coverage would be adequate.

### C3 — Numbers I asserted without checking

Gmina counts (~177 łódzkie, ~314 mazowieckie), listing volumes (10k–40k), churn
(500–2,000/day), RCN parcel-level coverage (≥40% target), and the claim that ≥70%
of in-scope gminas will have a land listing each quarter. All plausible, none
verified. The coverage targets in PRD §5 are therefore aspirations I invented.

### C4 — Sales-price estimates may be near-vacuous

`14` and `05` treat `expected_sales` as symmetric with `expected_offering`. If E3.4
finds RCN is mostly paid or per-county bureaucratic, sales data is **GUS powiat
quarterly averages with no plot features** — from which no honest *per-plot*
estimate can be derived. The API would return an `Estimate` shaped like the
offering one but resting on something categorically weaker. Rule 6 says both price
types are first-class; the data may simply not support that at plot level.

---

## D. The question I never asked

`13` totals roughly **150–200 days of focused work** across 26 epics. At one day a
week that is three years; at two days a week, eighteen months to two years. I never
stated this plainly, and it is the number that should drive every other decision.

For a private tool helping one household buy one plot, that is very probably the
wrong shape. A defensible alternative — which I should have offered rather than
assumed away — is a **two-week version**: GUS BDL sales baseline plus one portal's
land listings for the two 25 km anchor rings only, normalised to PLN/m², in a
notebook or a minimal Streamlit map, with no zoning, no parcels, no routing, no
regression, no alerts. That answers "is this plot's price sane for this area"
— your stated core question — at perhaps 3% of the effort.

The full plan is not wasted if you want it. But it should be a deliberate choice
made against a stated alternative, and I presented it as though it were the only
option.

---

## E. What I got right, briefly

So this reads as an audit rather than a retraction: the separation of
`zoning_claim` from `buildability`, the terminal `unknown` state, the structural
barrier between the regression and the verdict, the append-only snapshot rule,
prediction logging from the first estimate, precision gating of nature attributes,
and the schema-level encoding of the price-type rule are all, I believe, correct
and worth keeping regardless of what scale we settle on.
