# wybor-szkoly-podstawowej

A tool for comparing **land and housing prices** in the Polish voivodeships of
**łódzkie** and **mazowieckie** — collect, normalize, enrich, and compare
visually. Priority asset class: **land (działki)**.

> The repository name is historical; the project it now holds is the land/housing
> price comparison tool described below.

## Status

Planning. No code yet — the design documents are the current deliverable.

## Documents

| Doc | What it is |
|---|---|
| [`docs/01-user-journeys.md`](docs/01-user-journeys.md) | Personas and eight user journeys, ordered by priority, with a journey → capability map |
| [`docs/02-prd.md`](docs/02-prd.md) | Product requirements: goals, scope, metrics, functional requirements, data model, architecture, milestones, risks, open questions |
| [`docs/03-data-sources.md`](docs/03-data-sources.md) | Polish data sources (GUS BDL, RCN, ULDK, EGiB WFS, Rejestr Urbanistyczny), what's verified vs. still to spike, and the scraping ground rules |

## The idea in three sentences

A buyer looking for a plot cannot see where their budget works across ~490
gminas, and cannot tell whether a given plot is fairly priced or even buildable.
This tool continuously collects asking prices, joins them to official parcel,
transaction and zoning registries, and presents the result as a price map, a
per-plot verdict against a transparent comparable set, and a side-by-side board.
Every number shows its source, date and sample size.

## MVP

Journeys **J1** (where can I afford to build), **J2** (is this plot fairly
priced), **J3** (which of my shortlist is best) — see the PRD's milestone table.

One constraint drives the sequencing: **listing history cannot be backfilled**.
Ingestion starts before any UI exists.

## Next decisions

Open questions are listed in [PRD §14](docs/02-prd.md#14-open-questions); the two
that change the shape of the project are whether this stays a private tool or
becomes a public one, and whether there is budget for paid data.
