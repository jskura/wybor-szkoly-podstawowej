# TDD gap analysis

Pass 1, step 2 of the standard workflow ([`CLAUDE.md`](../../CLAUDE.md) rule 7).
Six agents wrote TDD specifications for the whole application in parallel. Writing
tests before implementation surfaced defects that reading the documents never did.

**The headline: four of six agents independently hit the same wall — the schema
does not support features that were already specified as requirements.** That is
what a design pass is for, and it is why rule 7 puts a review between authoring and
implementation.

---

## A. Schema gaps — found independently by four agents

[`15-database-schema.md`](../15-database-schema.md) predates FR-61..72 and the
batch-11/14 decisions. Six concrete gaps, each of which would have been discovered
mid-implementation instead:

| # | Gap | Consequence | Found by |
|---|---|---|---|
| **A1** | **`price_kind` does not exist** despite FR-64 requiring it and V46 testing it | Auction starting prices and tender prices would land in the same column as asking prices. `18` §5 names `price_type` as unretrofittable — `price_kind` has exactly the same property | foundation, connectors |
| **A2** | No `price_type` defined for tender and auction rows | Ambiguous whether an auction floor is offering or sales. **Resolved below** | connectors |
| **A3** | `metric_unit_month`'s primary key omits `area_band`, `series_kind` (stock/flow) and `price_kind` | **Stock and flow rows collide on insert.** D56 made flow the headline; the schema cannot store both | aggregates |
| **A4** | No tables for buildings, building coverage, or the WZ verdict | FR-65 was written with nowhere to store its output | feasibility |
| **A5** | `listing` carries foreign keys to `parcel` and `plot_cluster`, built in later work items | Item 2's migration cannot apply in the stated order | foundation |
| **A6** | `admin_unit` has no `as_of` or source | Violates rule 6 — every stored number carries source and as-of, and boundaries are stored data | foundation |

**A2 resolved:** an auction starting price and a tender price are **asks, not
sales** — nothing has been transacted. So `price_type = 'offering'` for all three,
distinguished by `price_kind ∈ {asking, auction_start, tender}`. Rule 5 is
unaffected; FR-64 is the finer axis inside `offering`.

## B. Validation methods that are wrong, not merely incomplete

| # | Defect | Correction |
|---|---|---|
| **B1** | **V10 still carries the superseded area band** (100 m² – 500 000 m²). FR-12 was amended to 300 m² – 200 000 m², flagged rather than dropped (O12), but its validation method was not | Requirement and method contradicted each other. V10 amended |
| **B2** | **V31 asserts distances "to within 1 m"** — the projection distorts by roughly a metre per kilometre, so at 25 km ring scale that is unachievable | The criterion is right at good-neighbour scale and wrong at ring scale. Replaced with a scale-dependent tolerance budget |
| **B3** | **V6 asserts ~177 / ~314 / ~10 gminas** — approximate counts are not falsifiable, *and* they describe the full three-unit scope while `18` §6 item 3 loads **the two rings only** | V6 amended to the ring extent, with an exact count from the fixture manifest as the oracle |
| **B4** | `20` §6.1 and `05` §9 disagree on whether median absolute error measures the **range midpoint** or the **estimate median** | Two different numbers under one name. Fixed to the estimate median in both |

## C. The definitional gap nobody had noticed

**C1 — "within 25 km of the anchor" is nowhere defined.** The entire scope is two
25 km rings, and no document says what makes a gmina a member: does its *boundary*
intersect the circle, its *centroid* fall inside, or its *seat*? The three rules
give materially different gmina sets, and every coverage figure, aggregate and
comparable-set radius depends on which is used.

This survived twenty-one documents and an assumption audit because it reads as
obviously specified until you have to write `test_ring_membership`. Recorded as
**D64** below.

## D. Cross-cutting

- **O-number collisions.** Agents working in parallel each allocated new open-item
  numbers from O28 without coordination, colliding with O28–O31 (already used by
  D59–D62). Renumbered; the register in `00-decisions.md` is the only allocator.
- **The n=5 threshold is hardcoded in a database CHECK** (`range_kind_matches_n`)
  while O11 marks it unratified. A provisional parameter should not be enforced in
  a migration — moved to configuration, with the CHECK relaxed to internal
  consistency rather than a literal.
- **Item 1 has no validation method of its own.** The repo skeleton, Docker and
  migration harness are tested only incidentally through V7. Acceptable, and now
  stated rather than implied.
- **V7(b) cannot run in CI** — scanning full git history for anchor addresses needs
  the whole history, which shallow CI clones lack. Runs as a pre-push hook instead.

## E. What the specs got right that the documents had missed

Worth recording, because these are additions rather than corrections:

- **Non-vacuity companions.** Every metamorphic relation is paired with a test
  proving it can fail. A relation like "adding an out-of-band observation changes
  nothing" passes trivially if the estimator ignores its input entirely.
- **Seeded dishonest fixtures.** Each honesty sweep in the surface spec is paired
  with a deliberately dishonest render tree, proving the sweep has teeth.
- **Making the wrong answer unwritable.** The feasibility spec adds a constraint
  requiring coverage evidence before `unlikely` can be stored, so the
  absence-of-data-as-absence-of-neighbours error cannot reach the database at all.
- **The degrees-are-wrong control.** A test asserting that computing distance in
  degrees *fails* the known-answer check — otherwise a correct-looking test can
  pass against a wrong projection.

## F. Decisions taken to close these gaps

| # | Decision |
|---|---|
| **D64** | **Ring membership** = a gmina is in a ring if **any part of its boundary lies within 25 km of the anchor point**. Chosen because it is inclusive at the edge: a gmina half in the ring is more useful shown with its `n` than silently excluded, which matches rule 6. The rule is stated once, in `15`, and every consumer reads it from there |
| **D65** | **`price_kind`** added to the schema as an enum `{asking, auction_start, tender}`, non-null, with `price_type = 'offering'` for all three (A2). No aggregate may span kinds |
| **D66** | **`metric_unit_month` key extended** with `area_band`, `series_kind` and `price_kind` (A3) |
| **D67** | **n=5 moves to configuration**; the database CHECK enforces internal consistency between `range_kind` and `n`, not the literal 5 (D) |

## G. Still blocked

| # | Blocker | Blocks |
|---|---|---|
| O10 | Portals' `robots.txt` — unreachable from here | The portal connector's parse, count-agreement, list/detail reconciliation and sort-order tests |
| O11 | Valuation parameters unratified | Nothing — they are provisional and measured |
| — | The hand-labelled parcel set does not exist | V60 has no ground truth yet |
| — | The agricultural threshold in `19` §2.1 is an unverified secondary-source claim | The purchasability badge's copy |
