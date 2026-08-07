# Temporal model

Four different dates matter in this product and conflating any two of them
produces wrong answers that look right. This document fixes their meanings and the
rules for recomputation.

Decision: D34. Validation: [`04-validation.md`](./04-validation.md) §V32–V34.

---

## 1. The four times

| Field | Meaning | Example |
|---|---|---|
| `observed_at` | When **we** saw it | Our crawler read this listing at 03:14 on 12 March |
| `valid_from` / `valid_to` | When the fact was **true in the world** | The plot was listed at 142 zł/m² from 3 March to 19 April |
| `transacted_at` | When a sale **happened** | The notarial deed was signed on 8 January |
| `as_of` | The **publication date of the source** for derived or aggregated data | GUS BDL published this quarter's figure on 30 June |

The distinction that bites hardest: for a transaction, `transacted_at` and
`as_of` can be a year apart. RCN data published in 2026 Q3 describes deeds signed
in 2025. A chart plotting sales prices by publication date rather than transaction
date shows a market that never existed.

**Rule:** time series are always plotted on the time the fact was true —
`transacted_at` for sales, listing-active period for offers — never on
`observed_at` or `as_of`. Those two are provenance, not measurement.

## 2. Offering prices are intervals, not points

A listing is not a price on a date; it is a price over a period. Derived from the
snapshot series (FR-3):

```
snapshots:  Mar 3: 150k · Mar 10: 150k · Mar 17: 138k · ... · Apr 19: absent

intervals:  150k  [Mar 3 → Mar 17)
            138k  [Mar 17 → Apr 19)
            delisted at Apr 19
```

Consequences that must be implemented deliberately:

- **A listing contributes to every month it was active**, not only the month it
  first appeared. A plot listed January–June is in all six monthly medians.
- Whether it contributes its January price or its June price to the June median
  depends on the interval covering that month — the price *in force* then.
- **Interval boundaries are uncertain by up to one crawl cycle** (24 h, D14). The
  price changed somewhere between two observations; we record the observation
  times, not a guessed change moment.
- A gap in crawling is a gap in knowledge, recorded as such. If the crawler was
  down for three days, intervals spanning that gap are marked
  `boundary_uncertainty = 3 days` rather than being silently interpolated.

## 3. Delisting ≠ sale

A listing disappearing means one of: sold, withdrawn, expired, or relisted
elsewhere. We cannot distinguish these, and pretending otherwise would corrupt the
evaluation in `05` §9.

- `is_active = false` records disappearance only.
- Time-on-market is reported as **time listed**, explicitly not time-to-sale.
- Final price before delisting is a **weak** outcome signal in valuation scoring,
  labelled as such, and never treated as a realized sale price. Only RCN
  transactions are real sales.

## 4. Revisions and recomputation

Both official sources revise, and our own derived data changes when upstream
resolution improves (`07` §7).

**Principle: recomputation is versioned, never silent.**

- `metric_unit_month` rows carry `as_of` and a `computed_at`. Recomputing a month
  writes a new row generation rather than mutating in place, so "the March median
  as we understood it in April" remains answerable.
- A revision that materially changes a published figure is surfaced on the
  coverage page, not absorbed quietly. If last quarter's sales median moved 8%
  because RCN released more deeds, the user should be able to see that it moved.
- `listing_snapshot` is append-only (PRD §10 invariant 1) and is **never** revised.
  It is the raw record; everything else is derived from it and may be recomputed.

**Late-arriving data.** RCN publishes deeds well after signature, so a recent
quarter's sales figures are systematically incomplete. Every sales aggregate
therefore carries a **completeness indicator**: how many deeds we hold for that
period, and whether the period is still expected to grow. A quarter still filling
up is labelled *"dane niepełne"* rather than shown as if final — otherwise the
most recent quarter always appears to show a price drop, purely because the data
has not arrived.

This is a real trap: naive charts of registry data almost always show a spurious
decline at the right-hand edge.

## 5. Comparable-set recency

`05` §3 filters comparables to the last 12 months. Precisely:

- For offers: the listing was **active at any point** in the window.
- For sales: `transacted_at` falls in the window.
- The window is relative to the **subject's valuation date**, not to today, so a
  logged prediction (`05` §9) can be reproduced exactly as it was made.

Reproducibility of past predictions is the reason the temporal model needs this
much care: without it, `method_version` scoring cannot distinguish "the method
changed" from "the data underneath changed".

## 6. Time zone and calendar

- All timestamps stored in **UTC**, rendered in Europe/Warsaw.
- Monthly buckets follow the Europe/Warsaw calendar month.
- Quarters follow the calendar quarters GUS uses, so our periods align with the
  official series rather than needing reconciliation.
