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
| **C — Verifiable only by human judgement** | Truth exists but only in someone's head | ~~Is this plot's verdict sensible?~~ **Unavailable (D63)** — the owner cannot price plots, so no one can judge a verdict. Only *comparability* judgements survive: is this comparable actually similar? | **Largely gone.** See §6.4 |
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

## 6. Acceptance without pre-registration (D54, D57)

D54 says a number you know is wrong would destroy your trust, which made human
judgement the natural primary acceptance test. I proposed pre-registering your own
estimates for 8–10 plots before seeing any output — the standard fix for hindsight
bias. **You declined (D57), so it is off the table**, and asking for a weaker
version of the same homework would be worse than useless.

The better answer turns out not to need you at all.

### 6.1 Leave-one-out cross-validation — the primary acceptance test

The estimator's job is: *given everything except this plot, predict this plot's
price.* That is directly testable against data we already hold, with no human
input and no pre-registration:

1. For every listing in the corpus, remove it.
2. Build its comparable set from the remaining listings.
3. Produce the estimate range.
4. Compare to the listing's **actual asking price**.

This yields real, repeatable numbers:

| Measure | Meaning | Healthy |
|---|---|---|
| **Coverage** | Share of listings we can estimate at all | High and rising; low means comparables are too scarce |
| **Hit rate** | Share whose actual price falls inside the predicted range | Near the range's nominal coverage — a p25–p75 range should contain roughly half |
| **Median absolute % error** | Typical miss of the range's midpoint | Tracked as a trend, not against an absolute target |
| **Tail** | Share missed by more than 2× | Near zero; each one is a bug lead |

It runs in CI, it re-runs on every change to the comparable logic, and it is
**tier A/B rather than tier C** — a genuine upgrade over what I originally
proposed, not a fallback.

**Its limitation, stated plainly:** LOOCV proves the estimator predicts *asking
prices* consistently. It does **not** prove asking prices are fair — a corpus of
uniformly overpriced plots would score perfectly. Level is constrained separately
by the GUS sales cross-check (V16); LOOCV constrains internal consistency. Neither
alone is sufficient, and together they are still not tier D.

### 6.4 Tier C is unavailable (D63)

The owner cannot price plots. Every use of human judgement as a check on *price*
is therefore withdrawn — asking for a rating with no basis manufactures false
signal, which is worse than none.

What survives is narrower and genuinely answerable: **is this comparable similar to
the subject plot?** A layperson can see that one sits on a main road and the other
in forest. Since the comparable set determines the estimate, that judgement feeds
straight into correctness.

**Consequence:** the burden falls entirely on tiers A and B. In particular the GUS
sales cross-check (V16) is now the *only* external constraint on the level of our
estimates — if the whole corpus were biased upward, LOOCV would score perfectly and
nothing else would catch it. V16 is promoted from sanity check to primary safeguard.

### 6.2 Zero-effort human check — WITHDRAWN (D63)

Your judgement still matters, but it should cost you nothing beyond looking:

- The notebook shows a plot's data — area, location, attributes, comparables —
  **with the verdict collapsed**. You form an impression, then expand it.
- One click records *agree* / *disagree* / *unsure*. No numbers to write, no
  homework, no commitment beforehand.
- Any **disagree** is a bug lead: inspect the comparable set and record whether the
  tool was wrong, your impression was wrong, or it is undecidable.

Because the verdict is hidden until after you have looked, this keeps most of the
blindness pre-registration would have given, at roughly zero cost. It is weaker
evidence, and it is not the primary test any more — LOOCV is.

### 6.3 A slower signal worth collecting

Plots we flag as **above range** should, on average, sit unsold longer than those
in range. Our own snapshots can test this after a few weeks with no extra input.
It is noisy and slow, but it is the only signal available before real sales data,
and it costs nothing to record.

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

| # | Status | Question |
|---|---|---|
| O20 | **Closed (D56)** | Flow is the headline, stock shown alongside, neither ever unlabelled |
| O21 | **Closed (D58)** | Mutation testing is in scope for v0 |
| O22 | **Closed (D57)** | No pre-registration. Replaced by LOOCV (§6.1) plus a zero-effort check (§6.2) |
| O23 | **Superseded** | The 7-of-10 pass criteria died with pre-registration. LOOCV thresholds are set from the first run's actuals rather than guessed — see O25 |
| O24 | **Superseded** | Golden-corpus regression was not selected (D58) — see the gap below |
| **O25** | Open | LOOCV thresholds (hit rate, error, tail) cannot be set honestly before the first run. Set them from actuals, then treat regressions against them as failures |
| **O26** | Open | **Drift detection gap.** Golden-corpus regression was the main defence against slow, unnoticed change in normalization/dedup/aggregation output. Mutation testing proves the suite has teeth; metamorphic tests prove relations hold; **neither notices output quietly changing over time.** Options: adopt the golden corpus after all, or accept the gap and rely on LOOCV metrics moving as the alarm |

### The gap left by dropping golden-file regression

Worth stating rather than leaving implicit. The three selected techniques cover
different things:

- **Differential** — our percentiles match a reference. Catches definition errors.
- **Metamorphic** — output changes correctly when input changes. Catches filters
  that silently ignore their arguments.
- **Mutation** — the suite fails when the code is broken. Catches worthless tests.

None of them catches *"the aggregate for gmina X was 118 last month and is 131 now,
and no one changed the market"*. That was golden-file regression's job. The
partial substitute is watching the LOOCV metrics (§6.1) as a trend — a change in
normalization that shifts outputs will usually move hit rate or error too. Partial,
not equivalent.
