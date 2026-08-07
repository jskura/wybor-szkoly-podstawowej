# Land & housing price comparison — łódzkie, mazowieckie, Elbląg area

A tool for comparing **land and housing prices** in Poland: both **offering
prices** (asking prices from listings) and **actual sales prices** (recorded
transactions), collected daily, enriched with parcel, zoning and nature data, and
compared visually. Priority asset class: **land (działki)**.

> ⚠️ The repository is still named `wybor-szkoly-podstawowej` from an earlier
> project. A rename is agreed (D24) — candidate names below.

## Status

**Planning — no code yet.** Per [`CLAUDE.md`](CLAUDE.md), the PRD and validation
methods come first; implementation starts only after this is reviewed.

## Documents

| Doc | What it is |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Binding project rules: PRD first, ask don't assume, TDD, validation method per feature, two price types, provenance |
| [`docs/00-decisions.md`](docs/00-decisions.md) | Decision log — 24 decisions taken with the owner, plus what remains open |
| [`docs/01-user-journeys.md`](docs/01-user-journeys.md) | 4 personas, 8 journeys, journey → capability map |
| [`docs/02-prd.md`](docs/02-prd.md) | Requirements: goals, scope, metrics, FR-1..31, data model, architecture, milestones, risks |
| [`docs/03-data-sources.md`](docs/03-data-sources.md) | Polish data sources, what's verified vs. needs a spike, scraping ground rules |
| [`docs/04-validation.md`](docs/04-validation.md) | How we will know each feature works — required before implementing any of them |

## The idea

A buyer looking for a plot cannot see where their budget works across ~500 gminas,
cannot tell whether a plot is even buildable, and cannot see what similar plots
actually *sold* for as opposed to what sellers are *asking*. This tool collects
both price types continuously, joins them to official parcel, transaction and
zoning registries, and presents a price map, a per-plot verdict against a
transparent comparable set, and a side-by-side board.

Every number shows its **source**, **as-of date**, **sample size**, **spread** and
**price type**. Nothing is suppressed for being thin — it is shown with its
uncertainty visible.

## Scope

- **łódzkie**, **mazowieckie**, and the **Elbląg area** (powiat elbląski + m. Elbląg)
- Anchor areas with 25 km priority rings: **Budy Grabskie** (gmina Skierniewice)
  and **Elbląg**
- Land types by priority: budowlana → rekreacyjna → rolna → leśna/inne
- Free data sources only; Polish UI, English code and docs; daily crawl; runs on a
  small VPS

## MVP

Journeys **J1** (where can I afford to build), **J2** (is this plot fairly priced),
**J3** (which of my shortlist is best). Milestones in
[PRD §9](docs/02-prd.md#9-sequencing).

Two constraints drive sequencing: **listing history cannot be backfilled**, so
ingestion starts before any UI exists; and **sales prices are first-class from the
start**, so the GUS BDL baseline lands in M1 rather than late.

## Candidate repo names (D24)

| Name | Reading |
|---|---|
| `cena-ziemi` | "price of land" — plain, descriptive, Polish |
| `ile-za-dzialke` | "how much for a plot" — the user's actual question |
| `grunt-radar` | *grunt* = land/ground; suggests monitoring over time |
| `dzialkometr` | "plot-meter" — memorable, slightly playful |
| `parcela` | short, neutral, unambiguous |

`cena-ziemi` is the safest and `ile-za-dzialke` the most descriptive of what it
does. Tell me which and I'll update every reference.

## Next step

Review this planning set. Implementation begins with M0 only after that, following
the rule-3 cycle: validation method → failing test → implementation → passing test.
