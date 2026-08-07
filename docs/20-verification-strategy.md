# Verification strategy

How we establish that a feature is *correctly implemented*, not merely that it
runs. Written before the TDD cycle begins, as rule 4 requires.

[`04-validation.md`](./04-validation.md) lists per-feature methods. This document
is the layer above it: **why those methods are the right ones**, what we can and
cannot verify at all, and how we catch the failures that no test will catch.

---

## 1. The core problem: this system fails silently

In most software a defect announces itself — a crash, an exception, a red test.
Here the characteristic defect is **a plausible number that is wrong**. A median of
118 zł/m² computed from mis-parsed areas looks exactly like a correct one. Nothing
throws. The pipeline reports success. The map renders.

Everything below follows from that. Verification here is not primarily about
proving code correct; it is about **arranging for wrongness to become visible**.

Three consequences:

1. **Tests that only check "it produced a number" are worthless.** Every assertion
   must pin a *specific value* or a *specific relationship*.
2. **We need oracles** — sources of truth independent of the code being tested.
   Where no oracle exists, we need techniques that work without one (§4).
3. **Production data assertions matter as much as tests**, because the failure mode
   is data-dependent and arrives after deployment, not at build time.

## 2. Verification tiers — what is knowable

Being honest about this prevents false confidence. Every feature is assigned a
tier, and the tier determines what "verified" is allowed to mean.

| Tier | Meaning | Example | Confidence |
|---|---|---|---|
| **A — Exactly verifiable** | A correct answer exists and we can compute it independently | Area unit conversion; percentile maths; `price_type` constraints; TERYT assignment | High. A failure here is a bug, unambiguously |
| **B — Verifiable against an independent source** | No exact oracle, but a second source constrains the answer | Our offering median vs GUS sales; our listing count vs the portal's own stated result count; parcel geometry vs ULDK | Good. Disagreement means *something* is wrong, though not always what |
| **C — Verifiable only by human judgement** | Truth exists but only in someone's head | Is this plot's verdict sensible? Is this comparable set reasonable? | Weak but essential — D54 makes this the primary acceptance test |
| **D — Verifiable only over time** | The answer does not exist yet | Was the valuation right? Did the plot sell near our estimate? | Not available for v0. Requires realized outcomes months later |

**Rule:** a feature may not ship claiming more confidence than its tier supports.
A tier-C feature is never described in the UI as though it were tier A.

Roughly: v0's ingestion and normalization are tier A/B; its aggregates are tier B;
its verdict is tier C; the valuation's actual accuracy is tier D and **will not be
known during v0 at all**. That last point deserves stating plainly — v0 can be
fully correct as software and still give bad advice, and only tier D would reveal
it.

## 3. The silent-failure catalogue

The specific ways this system can be wrong with nobody noticing. Each needs a
named detector; a failure mode with no detector is an accepted risk, recorded here
rather than forgotten.

| # | Silent failure | Why it's invisible | Detector |
|---|---|---|---|
| F1 | **Area unit mis-parsed** — "12 arów" read as 12 m² | Produces a 100× error in zł/m² that still looks like a number | Tier-A unit tests per form; validity bands; **distribution check** — a spike at 100× the mode; hand audit of 20 ar/ha listings |
| F2 | **Price is for something else** — whole plot vs per m², or price includes a building | Both are plausible magnitudes | Cross-check: where the advert states both total and per-m², assert consistency. Flag mismatches rather than choosing |
| F3 | **Duplicates inflate `n` and skew the median** | More data looks like better data | Cluster-size distribution monitoring; manual eyeball of 50; **`n` before vs after dedup** reported side by side |
| F4 | **Wrong gmina** — geocoded across a boundary | The plot is real, the price is real, the aggregate is wrong | Known-answer tests; boundary-risk flag; listings-per-gmina distribution vs expectation |
| F5 | **Pagination stops early** — connector silently collects a subset | A smaller corpus still produces confident medians | **Compare our count to the portal's own stated result count.** This is the single highest-value tier-B check in the system |
| F6 | **Sort-order bias** — we crawl the first N pages sorted by price | Sample is systematically cheap or expensive | Crawl the same query under two sort orders; assert the price distributions agree |
| F7 | **Stock vs flow bias** — see §5 | The active pool over-represents unsold, overpriced plots | Report new-listings median alongside active-listings median |
| F8 | **Stale data presented as fresh** | Yesterday's numbers look like today's | Freshness assertion; last-crawl age shown on the number itself |
| F9 | **Auction/tender prices blended with asking prices** | Drags medians down, looks like a market move (O19) | Distinct price kind; assertion that no aggregate mixes kinds |
| F10 | **Month-boundary / timezone errors** | Shifts observations between periods | Month-boundary fixtures; UTC storage with explicit Europe/Warsaw bucketing |
| F11 | **Percentile definition drift** — our p25 ≠ the conventional p25 | Slightly wrong ranges, forever | **Differential test** against a reference implementation |
| F12 | **Quarantine swallows a class of listing** — e.g. every ha-stated plot rejected | The corpus silently loses a segment | Quarantine rate by reason, monitored; a spike in one reason alarms |
| F13 | **The corpus is not the market** — cheap plots sell before listing; agents list unsellable ones | No internal check can see this | **No detector.** Accepted limitation, stated in the UI. Only GUS cross-check constrains it, and coarsely |

F13 has no detector and that is the honest answer: portal asking prices are a
biased sample of the market and no amount of engineering fixes it. It is a reason
the GUS sales baseline is in v0 from day one rather than later.

## 4. Techniques, and where each earns its place

### 4.1 Exact-value tests (tier A)

Every parser and every arithmetic path gets tests pinning specific values, not
shapes. `"12 arów" → 1200`, not "returns a positive number".

### 4.2 Property-based testing

For parsers and normalization, where the input space is large and adversarial:

- **Equivalence**: `parse("12 arów") == parse("1200 m²") == parse("0,12 ha")`.
- **Round trip**: `format(parse(x)) == x` for canonical forms.
- **Idempotence**: normalizing twice equals normalizing once.

### 4.3 Metamorphic testing — the important one

Where no oracle exists, we can still assert how output *must change* when input
changes in a known way. These need no ground truth and catch whole classes of bug:

| Input change | Required output change |
|---|---|
| Multiply every price in a fixture by 2 | Median zł/m² exactly doubles |
| Multiply every price **and** area by 10 | Median zł/m² **unchanged** |
| Permute the input order | Output identical |
| Add an exact duplicate listing | After dedup, median **unchanged**; `n` unchanged |
| Add an observation outside the area band | Estimate **unchanged** |
| Add an observation of a different buildability class | Estimate **unchanged** (D28) |
| Shift all observations one month later, shift the query window equally | Same result |
| Add a listing far above the range | Median moves little; mean moves a lot — confirms we use the median |

The duplicate and out-of-band cases are the most valuable: they test that the
filters actually filter, which a fixture-based test can pass while quietly ignoring
its filter arguments.

### 4.4 Differential testing

Percentile and median logic is checked against an independent implementation
(numpy/pandas) on random inputs. Cheap, and it kills F11 outright — percentile
definitions differ between conventions, and picking one silently is exactly the
kind of decision that produces slightly-wrong ranges forever.

### 4.5 Golden-file regression

One frozen corpus — a real crawl of a single gmina, scrubbed and committed — with
its expected aggregate outputs. Any change to normalization, dedup or aggregation
that alters these outputs must be *explained* in the commit, not merely accepted.
This is the main defence against slow, unnoticed drift.

### 4.6 Cross-source agreement (tier B)

- Our offering median per powiat vs GUS sales figures — direction and plausible
  magnitude (V16).
- Our listing count vs the portal's own stated result count (F5).
- Parcel area from the advert vs from the register (F2, V28).

### 4.7 Production data assertions

Δ assertions run every pipeline execution and block publication on failure. They
cover what tests cannot: real data drifting away from what the code assumed.

### 4.8 Mutation testing — verifying the verification

For the numeric core only (normalization, aggregation, estimation): deliberately
introduce small faults — swap `p25`/`p75`, drop a filter clause, change a
comparison operator — and confirm the suite fails. **A test suite that passes
against a mutated median function is not a test suite.**

Worth the cost precisely here because these are the functions whose bugs are
invisible in the output.

## 5. Stock vs flow — a bias I had not accounted for

The pool of **active** listings over-represents plots that have not sold, which
skews toward overpriced ones. A plot listed 14 months ago at an unrealistic price
is still in the pool; a well-priced plot sold in three weeks and left it.

So the median of *active* listings is systematically higher than the median of
*newly listed* ones, and the gap is itself informative about how mispriced the
standing stock is.

**Consequence for v0:** report both.

- **Stock** — median of all currently active listings.
- **Flow** — median of listings *first seen* in the last N weeks.

Neither is "the" answer. Flow is closer to the current market; stock is what you
will actually be choosing from. Showing only one, without saying which, would be a
quiet distortion — and I would have shipped exactly that, since every aggregate
specified so far is a stock measure.

This also partially rehabilitates snapshots after D45: even on a six-month horizon,
distinguishing flow from stock needs *some* history — a few weeks, not years.

## 6. The known-plot check, made rigorous (D54)

You said a number you know is wrong would destroy your trust. That makes human
judgement the primary acceptance test — so it must be run in a way that cannot
retroactively rationalise itself.

**Protocol:**

1. **Pre-register.** Before seeing any tool output, you write down, for 8–10 plots
   you know well: your own estimate of fair zł/m², and a range you would not be
   surprised by. Committed to the repo, timestamped, before the run.
2. **Run blind.** The tool produces its estimate and range for the same plots.
3. **Compare.** Record for each: did the ranges overlap? Was the tool inside your
   range, outside, or wildly off?
4. **Adjudicate disagreements one by one.** For each mismatch, inspect the
   comparable set by hand and record the verdict: **tool wrong** (a defect — fix
   it), **prior wrong** (your intuition was off — the tool taught you something),
   or **undecidable**.
5. **Pass criteria** (provisional, needs ratifying): the tool's range overlaps
   yours for at least 7 of 10, **and** there is no plot where the tool is off by
   more than 2×, **and** every mismatch has been adjudicated rather than waved
   away.

Pre-registration is what makes this a test rather than a vibe. Without it, whatever
the tool outputs becomes "roughly what I expected".

## 7. What v0 cannot verify

Stated so it is not discovered later as a surprise:

- **Whether the valuation is actually right** (tier D). Needs realized sales,
  months away. v0 can only be *internally* correct.
- **Whether the corpus represents the market** (F13). Structurally unknowable from
  inside.
- **Whether a WZ would actually be granted** (v0.5, `19` §1.2). We compute an
  indication and refuse to predict.
- **Whether RCN-level sales data would change the picture.** Not in v0.

## 8. Entry criteria for the TDD cycle

Before writing the first test for any v0 work item, all of these must hold —
this operationalises rules 3 and 4:

1. The item has a PRD requirement or a `18-v0-scope.md` work-plan entry.
2. It has a validation method in `04-validation.md` (or `19` for v0.5 items).
3. Its **verification tier** (§2) is assigned.
4. Any silent-failure modes from §3 it touches have a named detector.
5. Its fixtures exist, are dated, and are scrubbed of personal data.
6. For numeric-core items: the metamorphic properties (§4.3) that apply are listed.

## 9. Open questions this raises

| # | Question |
|---|---|
| **O20** | Should **flow** or **stock** be the headline aggregate (§5)? Flow is closer to the market; stock is what you can actually buy. My recommendation: show both, headline flow, and never show one unlabelled |
| **O21** | Is **mutation testing** (§4.8) worth the setup time for a ~13-day v0, or deferred to v0.5? |
| **O22** | Will you **pre-register** estimates for the known-plot check (§6)? It is the difference between a test and a rationalisation, and it costs you an hour |
| **O23** | Pass criteria in §6 — 7 of 10 overlapping, nothing off by more than 2× — are mine, not yours. Ratify or replace |
| **O24** | Which gmina should the **golden-file corpus** (§4.5) come from? It should be one with enough listings to be meaningful and stable enough to re-record |
