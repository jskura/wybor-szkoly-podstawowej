# Project rules

These are binding process rules for this repository. They apply to every change,
including small ones.

## 1. Write in Simplified Technical English

This rule applies to all communication: chat replies, documents, commit messages
and code comments. It is the first rule because unclear writing hides unclear
thought.

### 1.1 ASD-STE100 rules

- Write short sentences. Use 20 words or fewer for an instruction. Use 25 words
  or fewer for a description.
- Write one instruction in one sentence.
- Use the active voice. Write "the test asserts the median", not "the median is
  asserted".
- Use simple tenses. Prefer the present tense.
- Use one word for one meaning. Use the same word for the same thing every time.
  The glossary in `docs/12-glossary.md` fixes the terms.
- Keep the articles. Write "the estimate", not "estimate".
- Do not use more than three nouns together.
- Do not use slang, idiom or metaphor.
- Write what to do, not what to avoid, where both are possible.
- Keep paragraphs to six sentences or fewer.

### 1.2 Zinsser's four principles

1. **Simplicity.** Remove every word that does no work.
2. **Brevity.** Say it once. Do not repeat a point for emphasis.
3. **Clarity.** The reader must not read a sentence twice.
4. **Humanity.** Write to a person. Say "I was wrong" and "I do not know".

### 1.3 Where the two conflict

STE forbids metaphor. Zinsser asks for a human voice. The resolution: STE
controls sentence structure and word choice. Zinsser controls what to cut and
how to sound. Warmth comes from directness, not from decoration.

### 1.4 What this rule does not change

Report bad news plainly. State an error as an error. Do not soften a defect with
careful words. Simple English makes a problem easier to see, not easier to hide.

## 2. Ask questions with the AskUserQuestion tool

Use the `AskUserQuestion` tool. Do not guess. Do not settle an open point in
prose and then continue.

- Ask about **every** ambiguity. Do not cover an unclear requirement with a
  "sensible default" and a footnote.
- Ask many questions, not few. Ask them in batches, before the work starts.
- Give real options. Each option must say what happens if the user picks it.
- Recommend one option when you have a view, and say why.
- Ask again when an answer creates a new question.

This applies to scope, data sources, priorities, metric definitions, thresholds,
UX behaviour, stack choices, deployment and naming. Ask when in doubt.

**Assumptions.** An assumption is acceptable only if you do two things. Label it
as an assumption in the PRD. Tell the user in the same turn.

**Why this is rule 2.** This project has one owner and no second reviewer. A
wrong assumption becomes a document, then a schema, then a test. The audit in
`docs/17-assumption-audit.md` records the cost. Many decisions were mine, not the
owner's. Each one had to be found and undone later.

## 3. PRD first, always

No implementation work begins without a PRD entry covering it.

- A new product idea → write/extend `docs/02-prd.md` before anything else.
- A new feature inside an existing area → add it to the PRD as a numbered
  functional requirement (FR-n) before writing code.
- If a change turns out mid-flight to need something the PRD does not cover, stop
  and update the PRD, then continue.

## 4. TDD

After the PRD and before implementation, write the tests.

1. PRD entry (what and why)
2. Validation method (rule 5) — how we will know it works
3. Failing test
4. Implementation
5. Passing test

Never implement first and backfill tests.

## 5. Every feature ships with a validation method

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

## 6. Two price types are first-class

The product carries **both**:

- **Offering prices** (asking prices from listings) — high frequency, biased upward.
- **Actual sales prices** (recorded transactions, RCN/RCiWN and GUS) — authoritative,
  lagging, less granular.

Neither substitutes for the other. Every price figure in the data model, the API
and the UI must be explicitly labelled with which type it is. The gap between the
two is a product feature, never a discrepancy to reconcile away.

## 7. Provenance, and always show — always flag

Every stored and displayed number carries its **source**, **as-of date** and
**sample size**.

Nothing is suppressed. An aggregate computed from four observations is still
shown — but never as a bare number. Every aggregate is displayed together with
its **spread** (interquartile range, or min–max where n is very small) and its
sample size, so that thin evidence looks thin.

The rule is *always show, always flag*, not *hide what is uncertain*. A user who
can see `median 118 PLN/m², range 61–240, n=4` is better served than one who sees
"insufficient data", and far better served than one who sees "118 PLN/m²".

## 8. The standard workflow

Every substantial piece of work follows this cycle. It is two passes, not one, and
each pass ends at a commit.

**Pass 1 — design**

1. **Author** the artefact for *every* part of the application, not a subset.
2. **Review and analyse gaps** — what is missing, contradictory, or unverifiable.
3. **Simplify** — remove duplication, dead content and unnecessary complexity.
4. **Commit.**

**Pass 2 — detail**

5. **Plan the concrete detail** for every part (for TDD: the actual test cases,
   fixtures and data).
6. **Review.**
7. **Simplify.**
8. **Commit.**

**Parallelise.** Steps 1, 2 and 5 fan out across independent agents working on
disjoint areas — one file per agent so they never collide. Steps 3, 4, 7 and 8 are
consolidation and belong to a single writer.

**Why two passes.** A design pass that is immediately implemented hides its gaps;
a review that happens after the detail is written is too late to change the shape.
The first commit is a reviewable checkpoint on the shape, the second on the
substance.

Applies to TDD specs, requirements, validation methods and any other artefact
produced across the whole application at once.
