# Analytics & valuation methodology

How every number in the product is computed. This is the document that makes the
product's central claim testable: *"a plot with these features, in this place,
should cost roughly this."*

Decisions: D26–D33, corrected by D40–D42. Validation:
[`04-validation.md`](./04-validation.md) §V17–V24.

> **Status after the audit.** This document describes the **full** method, which
> is deferred: [`18-v0-scope.md`](./18-v0-scope.md) is the plan of record and uses
> only a simple banded median (§3 hard filters, no widening ladder, no size
> adjustment). Two corrections have been applied below — mix adjustment is no
> longer specified at gmina level (D41, audit A2), and the "never a point estimate"
> rule is restated (D42, audit A4).
>
> **Every numeric parameter in this document is provisional and unratified (O11).**
> They were chosen by me, not agreed with you, and the whole output depends on
> them. They are marked `‡` throughout.

---

## 1. The question the product answers

Two forms of one question (D26):

- **Verdict**: given a plot that exists and has an asking price — is it over- or
  under-priced?
- **Expectation**: given a set of features and a place, with no listing at all —
  what should it cost?

The second is the general case; the first is the second plus a comparison. So the
core object is an **estimator**:

```
estimate(features, place, price_type, as_of) → { low, median, high, n, basis }
```

`features` = area, buildability, utilities, road access, nature attributes.
`place` = a gmina, or a point with a radius.
`price_type` ∈ {offering, sales} — **never blended** (rule 6, D29).

The return is **always a range** (D32). Precisely — and this is the D42 correction,
because the earlier wording contradicted itself — the rule is:

> **A median may never be produced, returned, stored or displayed without its range
> and its sample size travelling with it.**

The estimate carries a `median`; that is useful and stays. What is forbidden is a
median *alone*. The earlier phrasing ("no point estimate, not even internally")
was self-contradictory, since `median` is exactly a point value, and V17 asserted a
property the spec itself violated.

## 2. Two estimators with strictly separated roles (D30, D33)

| | **Comparable-set median** | **Hedonic regression** |
|---|---|---|
| Role | **The verdict.** Every headline number. | **Feature values only.** What each attribute is worth. |
| Why | Fully traceable — you can see the exact plots behind it | Isolates the effect of one feature holding others constant, which comparables cannot |
| Shown as | "Expected 95–140 zł/m², from 23 comparable plots" | "Buildability is associated with +85% (model estimate, ±12%)" |
| May produce the verdict? | **Yes** | **Never** |
| May be shown unlabelled? | Yes | **No** — always marked as a model estimate |

This separation is the point. A regression that quietly becomes the headline
number is exactly the opaque score FR-28 forbids. The regression exists to answer
"what is forest proximity worth", and its output is never substituted for the
comparable-set verdict even when it looks better.

## 3. The comparable set

Given a subject (real plot or hypothetical feature bundle):

**Hard filters** — a candidate must match all of these:

| Dimension | Rule | Why |
|---|---|---|
| Buildability | **Exact match** (D28) | The dominant price determinant. A buildable plot is never compared to farmland |
| Asset class | Exact match | budowlana ≠ rekreacyjna ≠ rolna |
| Price type | Exact match | Rule 6 |
| Area | Within **±50%** of subject (D108) | Price per m² varies systematically with size (§4) |
| Recency | Observed within **12 months** (D110) | Older observations are a different market |
| Geography | Same gmina; widen by **10 km** rings if under the minimum count | Local markets are local |

**Widening ladder.** If the same-gmina set yields fewer than **3** comparables
(D109), widen in this fixed order, stopping at the first step that reaches 3:
same gmina → 10 km radius → 25 km radius → same powiat → same powiat with the area
band relaxed to ±100%. The step reached is recorded and **displayed** — an estimate
built from a 25 km radius is a weaker claim than one from the same gmina, and the
user must be able to see which they are getting.

**The trigger is ratified; the ladder is not.** D109 fixes the minimum at 3. The
five steps and their order were never asked about, and the fifth changes a
different axis — it relaxes the area band D108 ratified at ±50%. That step can
therefore return comparables D108 excludes. Recorded as **O41**; the ladder is
configuration until it is answered, and `config/params.yml` marks it as such.

Buildability is **never** relaxed. It would be the easiest way to find more
comparables and the fastest way to make the number meaningless.

**Never widened by**: price type, or across the `unknown` buildability boundary.
An `unknown` plot is compared only to other `unknown` plots, because treating
unknown as buildable is precisely the error FR-17 exists to prevent.

**Output**: median, p25, p75 of the comparables' price per m², the count, the
widening step reached, and the full list of contributing plots.

- `median` → the expectation
- `p25–p75` → the range shown when n ≥ 5
- `min–max` → the range shown when n < 5 (rule 7)

## 4. Size adjustment — closed as measure-then-decide (O6)

Price per m² falls as plots get larger: a 5000 m² plot rarely costs five times a
1000 m² plot. The ±50% area band limits the damage but does not remove it.

**Decided (O6, `00` batch 13): measure first, adjust only on evidence.** Fit a size-elasticity curve per
(voivodeship × asset class × buildability) — regress `log(price_per_m2)` on
`log(area)` — and adjust each comparable to the subject's size before taking the
median. Elasticity is reported, so the adjustment is inspectable.

For v0 the area band is the only size control, and the surface states that
comparables are unadjusted for size within the band. The elasticity is **reported**
and LOOCV (V51) is checked for size-correlated error; an adjustment ships only if
that evidence supports it.

## 5. The verdict

For a listing with asking price `P` and area `A`:

```
observed_ppm2   = P / A
expected_asking = estimate(features, place, 'offering')
expected_sales  = estimate(features, place, 'sales')
```

Displayed as two separate lines, never combined (rule 6, D29):

```
Cena ofertowa:     142 zł/m²
Oczekiwana ofertowa: 95–140 zł/m²  (mediana 118, n=23, ta sama gmina)
    → powyżej górnej granicy zakresu

Oczekiwana transakcyjna: 88–121 zł/m²  (mediana 104, n=7, powiat, dane RCN 2025Q4)
    → ceny ofertowe w tej gminie są średnio o 9% wyższe od transakcyjnych
```

The verdict is expressed relative to the **range**, not the median: *below range*,
*within range*, *above range*. "12% above the median" invites false precision when
the range is 95–140; "above the top of the range" does not.

Where sales data is missing for the area, that line reads *"brak danych
transakcyjnych"* — never filled in from the asking estimate (FR-8).

## 6. What-if valuation (D31)

All four forms are the same estimator with different inputs:

| Form | Mechanism | Caveat shown |
|---|---|---|
| **Price a hypothetical plot** | `estimate(user_features, chosen_place)` | Depends on features being realistic for that place; if no comparables match the bundle, say so rather than extrapolate |
| **Same plot, different place** | Hold features, vary `place`; run once per target area | Compares like with like by construction — this is the honest area comparison D28 asks for |
| **Value of each feature** | Regression coefficients (§2), in zł/m² at the subject's size | Association, **not** causation. A model estimate, labelled |
| **Value if it became buildable** | Contrast strata: median of `buildable` comparables ÷ median of the subject's current buildability class, same gmina, same period | The observed market gap between classes — **not** a probability of obtaining rezoning, and not advice that rezoning is achievable |

The rezoning-uplift caveat matters enough to be UI copy rather than a footnote:
the gap between farmland and building-plot prices is large precisely *because*
conversion is uncertain and slow. Presenting it as attainable upside would be the
most misleading thing this product could do.

## 7. Time series and mix-shift (D27)

A plain median moves when composition changes. If three large cheap farm plots get
listed in a small gmina, the median drops without any price changing.

### 7.1 The level at which this is computable (D41 — audit A2)

Strata are `asset_class × buildability × area_band` = **4 × 4 × 5 = 80 strata**.
A gmina holding ~50 land listings spread over 80 strata has a typical non-empty
stratum of n=1. **A fixed-basket index over mostly-empty strata is noise, not a
measurement**, so the original instruction to make it the headline figure *at gmina
level* was wrong.

Corrected rule:

| Level | Units | Typical listings per unit | Mix adjustment |
|---|---|---|---|
| Voivodeship | 3 | thousands | **Yes** |
| Powiat | ~66 | hundreds | **Yes** — the finest level where it is meaningful |
| Gmina | ~500 | tens | **No.** Plain median with spread, labelled *unadjusted* |
| Obręb | thousands | single digits | No |

A gmina-level series therefore carries an explicit note that it is **not**
mix-adjusted and may move because composition changed. That is honest; computing an
index there and calling it adjusted would not be.

Before publishing an index at any level, assert that a minimum share of strata are
non-empty; below that threshold ‡ the index is not produced and the plain median is
shown instead.

**Method — stratify and reweight:**

1. Define strata: `asset_class × buildability × area_band`, where area bands ‡ are
   `<800`, `800–1500`, `1500–3000`, `3000–10000`, `>10000` m².
2. Compute the median price per m² **within each stratum** per unit per month.
3. Reweight to a **fixed basket** — the stratum composition of the base period,
   held constant across the series.
4. The mix-adjusted index is the weighted combination.

Strata with no observations in a period are carried with their weight and an
explicit gap marker, never dropped — dropping them silently reweights the basket
and reintroduces exactly the bias this removes.

**Both series are published**: the plain median (what people expect to see) and
the mix-adjusted index (what actually moved), with the difference explained. When
they diverge sharply, that divergence is itself informative — it means the *kind*
of land being offered changed.

The headline trend figure is the mix-adjusted one **wherever it is computable**
(D27, narrowed by D41 §7.1). At gmina level the headline is the plain median,
labelled as unadjusted.

## 8. Area comparison

Two mechanisms, both required to split by buildability (D28):

1. **Like-for-like estimate** — §6's "same plot, different place". The cleanest
   comparison: one feature bundle, priced in each area.
2. **Stratified distributions** — per area, the price distribution within a chosen
   stratum, shown side by side rather than reduced to one number.

A single "average price in this area" figure is **not** offered as a comparison
tool. It is available on the coverage page as a descriptive statistic, labelled as
descriptive, because comparing raw area averages is the specific error §7 and D28
exist to prevent.

O7 (standard-plot benchmark) is **adopted** (`00` batch 13) and rendered in the
gmina panel (`21` §2.2): what a 3 000 m² buildable plot costs in each area.

## 9. Prediction logging and evaluation (D35)

Every estimate the product ever produces is written to `valuation_log`:

```
valuation_log (id, created_at, subject_kind[listing|hypothetical],
               listing_id?, parcel_id?, teryt_unit, features_json,
               price_type, estimate_low, estimate_median, estimate_high,
               n_comparables, widening_step, method_version,
               observed_price_ppm2?)
```

This must exist from the **first estimate ever made**. Predictions cannot be
reconstructed after the fact — the comparable set that existed in March is gone by
June — so a logging gap is permanently unrecoverable, the same way the listing
snapshot gap is.

**Scoring**, run quarterly once realized outcomes accumulate:

| Measure | Definition | Healthy |
|---|---|---|
| **Calibration** | Share of realized prices falling inside the predicted range | Close to the range's nominal coverage — a 50% interval (p25–p75) should contain ~50% |
| **Bias** | Median signed error of the estimate median | Near zero; persistent sign means systematic over- or under-estimation |
| **MAPE** | Median of \|realized − estimate **median**\| / realized. Not the range midpoint (`20` §6.1) | Tracked as a trend, not against an absolute target |
| **Coverage** | Share of subjects we could estimate at all | Rising over time |
| **Widening profile** | Distribution of widening steps | Mostly same-gmina; a shift outward means data thinning |

Realized outcomes come from two sources, scored separately: RCN transactions
(true sales price — the real test), and final asking price before delisting (weak,
since delisting is not sale).

**Governance.** `method_version` is stamped on every logged prediction. Changing
the comparable rules, the strata, or the size adjustment increments the version;
old predictions keep the version that produced them and are scored within their
version. A method change never silently rewrites history.

## 10. What would falsify this methodology

Stated here so §9's scoring has teeth:

- Calibration far from nominal — a p25–p75 range containing 90% of realized prices
  is uselessly wide; containing 15% is dishonestly narrow.
- Persistent bias in one direction that survives a method version change.
- The regression's feature values disagreeing in **sign** with the comparable
  contrasts — e.g. regression says buildability is worth less than nothing. Either
  the model or the strata are wrong, and the product should say so rather than
  show both.
- Mix-adjusted and plain series diverging with no composition change to explain it
  — indicates a stratification bug, not a market signal.
