# User Journeys — Land & Housing Price Comparison (łódzkie / mazowieckie)

Status: draft for review
Scope: voivodeships **łódzkie** and **mazowieckie**
Priority asset class: **land (działki)** — housing is secondary

These journeys are the input to the PRD. Each one states the trigger, the steps a
user takes, the data the product must already hold to serve those steps, and what
"done" looks like. Journeys are ordered by priority; J1–J3 define the MVP.

---

## Personas

| # | Persona | Who | Primary need | Priority |
|---|---------|-----|--------------|----------|
| P1 | **Self-builder** ("Marek & Ania") | Couple, 30s, live in Warsaw or Łódź, want to build a single-family house in 2–4 years. Budget for the plot: 150–350k PLN. | Find where their budget actually buys a *buildable* plot at an acceptable commute | **Primary** |
| P2 | **Patient investor** | Buys 0.3–3 ha, holds 3–10 years, expects rezoning (rolna → budowlana) or subdivision | Spot gminas where the buildable/agricultural price gap is widening | Secondary |
| P3 | **Relocator** | Selling a flat in Warsaw, deciding between buying a ready house vs. plot + build | Compare "buy finished" vs "buy land and build" per location | Secondary |
| P4 | **Analyst / us** | The people building this | Trust the numbers; see coverage, freshness, method | Internal |

Non-personas for v1: real-estate agents, developers doing land banking at scale,
mortgage brokers.

---

## J1 — "Where can I afford to build?" *(budget-first exploration)* — **P1, MVP**

**Trigger:** User has a budget and a commute constraint, no location in mind.

**Steps**
1. Opens the map, sees łódzkie + mazowieckie as a **choropleth of median PLN/m² for
   building plots**, aggregated per gmina.
2. Sets filters: budget 150–350k PLN, plot area 800–2000 m², zoning = building
   plot, "utilities on the boundary" toggle.
3. Adds a commute constraint: *≤ 60 min drive to Warsaw centre* (isochrone or a
   simpler drive-time-to-city column).
4. The map recolours to **"median price of a plot matching my filter"** — gminas
   with no matching supply grey out. This is the key insight moment: the
   affordable ring is visible as a shape, not a list.
5. Clicks a gmina → side panel: median and IQR of PLN/m², number of active
   listings, 12-month price change, distance/drive time, share of listings that
   are buildable, link to the listings behind the number.
6. Shortlists 3–5 gminas.

**Data required:** gmina boundaries; active land listings normalized to PLN/m²
with area + zoning + utilities; drive time from each gmina seat to Warsaw and
Łódź; ≥ 12 months of listing history for the trend.

**Success:** user can name 3 gminas they had not considered, and state the
price/commute trade-off between them, in under 10 minutes.

**Pain today:** Otodom/OLX filtering is per-listing, not per-area. There is no way
to see "the affordable ring" — you discover it by scrolling hundreds of listings.

---

## J2 — "Is this plot fairly priced?" *(single-plot verdict)* — **P1/P2, MVP**

**Trigger:** User found a listing (or has a parcel ID from the seller) and wants a
second opinion before viewing or negotiating.

**Steps**
1. Pastes a listing URL, or enters a parcel identifier (*numer działki
   ewidencyjnej*, e.g. `146509_8.0201.12/3`), or drops a pin on the map.
2. The product resolves it to a **parcel geometry** and pulls its attributes:
   area, land-use class, zoning designation from the *plan ogólny* / MPZP where
   published, road-access, neighbours' land use.
3. Shows a **verdict card**: `PLN/m² = 142` · `median for comparable plots in this
   gmina = 118` · **`+20% above comparable asking prices`** · sample size 27 ·
   confidence: medium.
4. Shows the **comparable set** as a map + table (same gmina or 10 km radius,
   same zoning class, area within ±50%, listed within 12 months), each row with
   its own PLN/m² and the distance from the subject plot. The user can eject
   comparables they think are wrong; the verdict recomputes.
5. Shows **asking vs. transaction spread** for that gmina, from the property price
   register (RCN): "plots here sell for a median of 8% below asking".
6. Flags **risk badges**: no public-road access, farmland class I–III (protected,
   hard to rezone), within a flood-hazard zone, no MPZP and no *plan ogólny*
   coverage, overhead power line crossing, long/narrow shape.

**Data required:** parcel geometry + attributes; zoning layer; the listing corpus
for comparables; RCN transactions for the spread; hazard/constraint layers.

**Success:** user gets a number with a defensible comparable set behind it, and
at least one risk they had not checked themselves.

---

## J3 — "Which of my 3 shortlisted plots is best?" *(side-by-side)* — **P1, MVP**

**Trigger:** Viewings scheduled, decision imminent.

**Steps**
1. Adds 2–4 plots to a comparison board (from J1 results, J2 lookups, or pasted
   URLs).
2. Sees a **column-per-plot table**: price, area, PLN/m², PLN/m² vs. local median,
   zoning designation and what it permits (max building height, biologically
   active area share, permitted use), utilities present, road access type,
   drive time to Warsaw/Łódź/nearest school/nearest station, days on market,
   price-change history since first seen.
3. Rows where plots differ materially are highlighted; identical rows collapse.
4. Assigns weights to the criteria that matter (price 40%, commute 30%,
   buildability 30%) → a **ranked recommendation with the reasoning shown**, not a
   black-box score.
5. Exports the board to PDF/PNG to argue about it with a partner or a parent.

**Data required:** everything from J2, plus per-listing price history (only exists
if we started collecting early — see PRD §9) and travel-time computation.

**Success:** the board replaces the spreadsheet the user would otherwise build by
hand.

---

## J4 — "Tell me when something good appears" *(saved search + alerts)* — P1

**Trigger:** Nothing on the market matches today; the user is willing to wait.

**Steps**
1. Saves the filter set from J1/J2 as a named search ("≤300k, ≥1000 m²,
   buildable, ≤50 min to Warsaw West").
2. Chooses notification channel and cadence (email/Telegram, daily digest or
   immediate).
3. Receives alerts for: **new** matching listings, **price cuts** on watched
   listings, and **relistings** (same plot, new advert, lower price — a strong
   negotiation signal), each already carrying its J2 verdict card.
4. One click from the alert into the comparison board.

**Data required:** stable listing identity across re-postings (dedup + fingerprint),
scheduled ingestion, per-user saved searches.

**Success:** user stops browsing portals daily and trusts the digest.

---

## J5 — "Prepare my offer" *(negotiation)* — P1/P2

**Trigger:** User is about to make an offer.

**Steps**
1. Opens the plot's page → **negotiation panel**.
2. Sees: days on market vs. gmina median; every price change since first seen;
   how many similar plots the same seller has listed; the gmina's median
   asking-to-transaction discount from RCN; the comparable set's price range.
3. Gets a suggested offer band ("recorded transactions for comparable plots here
   cluster at 95–128 PLN/m²; asking is 142; comparable plots sold 8% under
   asking") — a **range with its evidence**, never a single "you should offer X".

**Data required:** listing history, RCN transactions at parcel/precinct level.

**Success:** the user walks into the negotiation with three concrete facts.

---

## J6 — "Buy a house or build one?" *(housing enters scope)* — P3, post-MVP

**Trigger:** User is undecided between a finished house and land + construction.

**Steps**
1. Picks a gmina or a drive-time ring.
2. Sees two distributions side by side: **PLN/m² of finished houses** vs.
   **plot PLN/m² + a parameterized build cost** (user sets build cost per m²,
   default seeded from public construction-cost indices, and the intended house
   size).
3. Sees the crossover: in which gminas building is cheaper than buying, and by
   how much, plus a reminder of what the model ignores (time, financing, risk).

**Data required:** the housing listing corpus (secondary market houses, and flats
for the sell-side), a build-cost parameter.

**Success:** the user can say "in gmina X building saves ~12%, in gmina Y it
doesn't" — the first journey where housing data is load-bearing.

---

## J7 — "What is actually happening to prices here?" *(trends)* — P2/P4

**Steps**
1. Picks up to 5 gminas/powiats and an asset class.
2. Sees **median PLN/m² over time** (monthly, from our own listing snapshots;
   quarterly, from GUS/RCN for the pre-history baseline), with listing counts
   underneath so thin months are visibly thin.
3. Toggles: asking vs. transaction; buildable vs. agricultural land (the gap is
   the investor's whole thesis); nominal vs. inflation-adjusted.
4. Exports the series as CSV.

**Success:** a claim like "buildable land in gmina X grew 18% y/y while farmland
was flat" is defensible, with sample sizes attached.

---

## J8 — "Can I trust this?" *(transparency, cross-cutting)* — P4 and everyone

Every number in the product must be one click from: **source**, **as-of date**,
**sample size**, and **method**. Every aggregate below a minimum sample size (n<10)
renders as "insufficient data", never as a confident number. A permanent
**coverage page** shows, per gmina: listings collected, last successful crawl,
parcel-match rate, and known gaps.

This is not a nice-to-have. The product's only real asset is the user's trust that
the median it shows is not an artifact of a broken scraper.

---

## Journey → capability map

| Capability | J1 | J2 | J3 | J4 | J5 | J6 | J7 |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| Land listing ingestion + dedup | ● | ● | ● | ● | ● | ○ | ● |
| Normalization to PLN/m² | ● | ● | ● | ● | ● | ● | ● |
| Gmina aggregates + choropleth | ● | ○ | | | | ● | ● |
| Parcel resolution (ULDK/EGiB) | | ● | ● | | | | |
| Zoning enrichment (plan ogólny/MPZP) | ○ | ● | ● | ○ | | | ○ |
| Comparable-set engine | | ● | ● | | ● | | |
| RCN transaction data | | ○ | | | ● | | ● |
| Listing price history | | | ● | ● | ● | | ● |
| Drive-time / accessibility | ● | ○ | ● | ○ | | ● | |
| Saved searches + alerts | | | | ● | | | |
| Housing corpus | | | | | | ● | ○ |

● required ○ improves the journey but not blocking

---

## What the journeys imply for the MVP

1. **J1 + J2 + J3 is the product.** Everything else is an extension of the same
   spine: normalized listings → gmina aggregates → parcel enrichment → comparables.
2. **Zoning is the hardest requirement and the biggest differentiator.** A plot's
   price only means something once you know whether you may build on it. No
   consumer portal answers this reliably; the *plan ogólny* rollout (Urban
   Registry, live since July 2026) makes it feasible for the first time.
3. **Listing history cannot be backfilled.** J3, J4, J5 and half of J7 depend on
   snapshots we take ourselves. Ingestion must start before any UI exists.
4. **Sample size is a first-class UI element.** In rural gminas a "median" over
   4 listings is noise; the design must show that rather than hide it.
