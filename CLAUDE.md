# Project rules

These are binding process rules for this repository. They apply to every change,
including small ones.

## 1. PRD first, always

No implementation work begins without a PRD entry covering it.

- A new product idea → write/extend `docs/02-prd.md` before anything else.
- A new feature inside an existing area → add it to the PRD as a numbered
  functional requirement (FR-n) before writing code.
- If a change turns out mid-flight to need something the PRD does not cover, stop
  and update the PRD, then continue.

## 2. Resolve ambiguity by asking, not by assuming

Use `AskUserQuestion` for **every** ambiguity — do not paper over an unclear
requirement with a "sensible default" and a footnote. Ask many questions rather
than few, and ask them in batches before the work rather than after.

Applies to: scope, data sources, priorities, metric definitions, thresholds,
UX behaviour, stack choices, deployment, naming. When in doubt, ask.

Assumptions are only acceptable when explicitly labelled as such in the PRD and
flagged to the user in the same turn.

## 3. TDD

After the PRD and before implementation, write the tests.

1. PRD entry (what and why)
2. Validation method (rule 4) — how we will know it works
3. Failing test
4. Implementation
5. Passing test

Never implement first and backfill tests.

## 4. Every feature ships with a validation method

Before implementing any feature, its **validation method** must be written down
in `docs/04-validation.md` — how we will judge whether it was implemented
correctly. This is a precondition of implementation, not a follow-up.

A validation method states:

- **Acceptance criteria** — observable, specific, and falsifiable. Not "the map
  works" but "a gmina with fewer than 10 observations renders as suppressed, not
  as a number".
- **How it is verified** — unit test, integration test against a recorded
  fixture, golden-file comparison, a manual check with a written script, or a
  data-quality assertion that runs on every pipeline execution.
- **The data it is verified against** — recorded fixtures, a hand-labelled
  sample, or an independent source used as ground truth.
- **What would falsify it** — the specific observation that means it is broken.

Data features get data assertions, not just code tests: coverage, freshness,
duplicate rate, outlier rate and cross-source agreement are all testable and all
run on a schedule, not once.

## 5. Two price types are first-class

The product carries **both**:

- **Offering prices** (asking prices from listings) — high frequency, biased upward.
- **Actual sales prices** (recorded transactions, RCN/RCiWN and GUS) — authoritative,
  lagging, less granular.

Neither substitutes for the other. Every price figure in the data model, the API
and the UI must be explicitly labelled with which type it is. The gap between the
two is a product feature, never a discrepancy to reconcile away.

## 6. Provenance, and always show — always flag

Every stored and displayed number carries its **source**, **as-of date** and
**sample size**.

Nothing is suppressed. An aggregate computed from four observations is still
shown — but never as a bare number. Every aggregate is displayed together with
its **spread** (interquartile range, or min–max where n is very small) and its
sample size, so that thin evidence looks thin.

The rule is *always show, always flag*, not *hide what is uncertain*. A user who
can see `median 118 PLN/m², range 61–240, n=4` is better served than one who sees
"insufficient data", and far better served than one who sees "118 PLN/m²".
