# Buildability feasibility & purchase law

Two things that decide whether a plot is actually available to you, neither of
which appeared anywhere in docs 00–18:

1. **Can you build on it in practice** — via *warunki zabudowy* where no plan
   exists (D46, D50).
2. **May you legally buy it** — agricultural land is restricted, and KOWR holds
   pre-emption rights (D51).

Both are risk badges on the plot page, not filters. Neither is legal advice.

---

## 1. The good-neighbour test (D50)

Where no MPZP or *plan ogólny* covers a parcel, building normally requires a
**decyzja o warunkach zabudowy** ("WZ-ka"). The central condition is *dobre
sąsiedztwo* — good neighbourhood: broadly, at least one **neighbouring plot
accessible from the same public road must already be developed** in a way that
lets the new building's parameters be derived from it. Access to a public road,
utilities sufficient for the planned use, and the land not requiring agricultural
de-designation are conditions alongside it.

This is the difference between `buildability = unknown` being a shrug and being an
actual signal. Given D46 — you would take the WZ route — it is more valuable to
you than the zoning layer itself.

### 1.1 What we can compute

| Signal | How | Confidence |
|---|---|---|
| **Developed neighbour exists** | Building geometry within a radius of the parcel boundary, from county EGiB WFS where available, OSM buildings otherwise | Good where EGiB has buildings; weaker on OSM |
| **Shares a public road** | Parcel adjacency to a road parcel, plus OSM road classification | Moderate |
| **Land-use class** | EGiB — whether it is *grunt rolny* needing de-designation | Good |
| **Protected area overlap** | GDOŚ layers — landscape park, Natura 2000 (relevant to the Budy Grabskie ring) | Good |

Composite output: `wz_feasibility ∈ {likely, uncertain, unlikely, unknown}` — an
indication, never a prediction.

### 1.2 What we must not claim

A WZ decision depends on the gmina's interpretation, the *analiza urbanistyczna*
performed by the planner, protected-area rules, soil class, and neighbours'
objections. **We cannot predict the outcome, and the tool must never imply we can.**

Mandatory presentation rules, in the spirit of FR-17's terminal `unknown`:

- The output is labelled *"wstępna ocena — nie jest to gwarancja wydania WZ"*.
- `unlikely` is stated as *"brak spełnienia warunku dobrego sąsiedztwa w promieniu
  X m"* — the observation, not a conclusion.
- `likely` never appears without the same disclaimer as `unlikely`. An
  optimistic-looking answer is the dangerous one, because it is the one that would
  make you spend money.
- Where building data is missing, the answer is `unknown`, **not** `unlikely`
  (O17). Absence of observed buildings in a poorly-mapped county is absence of
  data, not absence of neighbours.

### 1.3 Validation (required before implementation, rule 5)

- **AC** For 10 hand-checked parcels — 5 with obvious built neighbours, 5 clearly
  isolated — the computed signal matches visual inspection on an orthophoto. No
  parcel with missing building data is reported as `unlikely`.
- **How** Known-answer test against a hand-labelled set of 10 parcels in each ring.
- **Against** Orthophotos and the cadastral map, inspected by hand.
- **Falsified by** Any `likely`/`unlikely` verdict contradicted by the imagery; any
  `unlikely` produced from missing data; any UI rendering without the disclaimer.

---

## 2. Agricultural land purchase restrictions (D51)

The *ustawa o kształtowaniu ustroju rolnego* restricts who may acquire agricultural
property and gives KOWR statutory pre-emption over many transactions. This can
delay a purchase, add conditions, or prevent it outright — and it is invisible in a
listing.

### 2.1 What matters at your plot size

You are looking at **2000–4000 m²** (D48), which straddles a meaningful line:

- Small agricultural parcels below the statutory threshold have historically fallen
  outside the act's main restrictions; a 2000 m² *rolna* plot is usually
  unproblematic, a 4000 m² one may not be.
- The regime was **relaxed in 2026**: the threshold for purchase without
  ministerial consent rose from 1 ha to 5 ha (effective 30 April 2026), which
  helps a non-farmer buyer at your sizes.
- KOWR pre-emption can still attach to an agricultural parcel regardless, and a
  buyer may face a holding period restricting resale.

**These specifics must be verified against the current consolidated act before the
badge ships** — the law moved in 2026 and secondary sources disagree. That
verification is part of the work item, not an afterthought.

### 2.2 The badge

For any plot whose register land-use class is agricultural:

```
⚠ Grunt rolny — 3 400 m²
   Możliwe ograniczenia w nabyciu (ustawa o kształtowaniu ustroju rolnego)
   Możliwe prawo pierwokupu KOWR
   → sprawdź u notariusza przed ofertą
```

Rules:

- Driven by the **register** land-use class, never the advert's claim (FR-48).
- Says *possible*, never *certain* — the determination is the notary's.
- Never a filter (D51 chose the badge, not exclusion), so you still see the plot
  and decide.
- Where the register class is unknown, no badge and no reassurance either — silence
  is not a clean bill of health, and the UI says so.

### 2.3 Validation

- **AC** Every plot with an agricultural register class carries the badge; no plot
  with a non-agricultural class carries it; no plot with unknown class is presented
  as unrestricted.
- **How** Unit tests over fixtures at each class, including unknown; plus a
  citation check that the thresholds in the copy match the current consolidated act
  on the date shipped.
- **Against** EGiB land-use classes; the consolidated text of the act.
- **Falsified by** A badge on non-agricultural land; a missing badge on farmland;
  copy citing a superseded threshold.

---

## 3. Why these two rank higher than they look

Given D46 and D52, the honest ordering of what determines whether a plot is worth
pursuing is:

1. **Can I buy it?** (§2) — a legal no ends the conversation.
2. **Can I build on it?** (§1) — for you this is a WZ question, not a plan question.
3. **Is the price fair?** — the original problem, and the one v0 addresses.

I built the documentation in reverse order, and only reached 1 and 2 by asking what
had not been discussed. Both are in scope (D55), immediately after price
comparison works.

## 4. Standing disclaimer

Nothing here is legal advice. Every badge in this document is informational; the
binding answers come from the *wypis i wyrys* for planning and from a notary for
purchase restrictions. This mirrors the PRD's position that the product never
claims legal certainty (PRD §3).
