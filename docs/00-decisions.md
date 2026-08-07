# Decision log

Decisions taken with the product owner, newest batch last. Every decision here is
binding on the PRD; if a decision changes, the PRD changes in the same commit.

Per [`CLAUDE.md`](../CLAUDE.md) rule 2, these were resolved by asking, not by
assuming. Items marked **ASSUMPTION** were not asked about and must be confirmed
before the affected work starts.

## Batch 1 — project shape (2026-08-07)

| # | Question | Decision | Consequence |
|---|---|---|---|
| D1 | Who uses it, is it published? | **Private + a few friends** | No public launch, no auth beyond a simple gate; scraping stays low-volume and non-commercial (PRD §12) |
| D2 | Budget for paid data? | **Zero — free sources only** | No commercial listing feed. Conflicts with D3; resolved by D5 |
| D3 | Sales prices vs asking prices | **Both equally first-class from the start** | Promoted to `CLAUDE.md` rule 5. Transaction data is not a later milestone |
| D4 | Stack | **Python + PostgreSQL/PostGIS** (my choice, delegated) | FastAPI backend, MapLibre frontend, Docker |

## Batch 2 — scope (2026-08-07)

| # | Question | Decision | Consequence |
|---|---|---|---|
| D5 | How to get free sales prices given D2? | **Research RCN access first, then decide** | FR-31 spike lands before the RCN connector is scheduled |
| D6 | Which land types? | Priority order: **budowlana → rekreacyjna → rolna → leśna/inne** | Recreational ranks above agricultural — matches the anchor areas |
| D7 | Centre of gravity | **Budy Grabskie and surroundings; Elbląg and surroundings** | Two named anchor areas, not a Warsaw commuter-belt product |
| D8 | History depth | **As far as free data allows** | RCN from 2021-07-31; GUS BDL as deep as it publishes |

## Batch 3 — geography and priorities (2026-08-07)

| # | Question | Decision | Consequence |
|---|---|---|---|
| D9 | Elbląg is outside łódzkie/mazowieckie | **Add just the Elbląg area** (powiat elbląski + m. Elbląg) | Third target unit; region stays a pipeline parameter |
| D10 | Two-area comparison or region-wide? | **Still region-wide exploration** | J1's full map survives; anchors set priority, not scope |
| D11 | What does "and surrounding" mean? | **~25 km radius** around each anchor | Defines the priority rings for enrichment and daily crawl depth |
| D12 | What matters for these plots? | **Buildability, price (per m² and total), travel time, nature** — all four | Nature is a first-class attribute, not a nice-to-have |

## Batch 4 — thresholds and operations (2026-08-07)

| # | Question | Decision | Consequence |
|---|---|---|---|
| D13 | Minimum sample size for showing a median | **Show everything, flag uncertainty** | Overrode the drafted suppression rule — see D17 |
| D14 | Crawl cadence | **Daily** | Polite, sufficient for price-change detection |
| D15 | Language | **Polish UI, English code and docs** | Domain terms stay Polish in the UI |
| D16 | Where does it run? | **Cheap VPS** | Unattended daily crawl. Note: D2 is zero budget for *data*; hosting cost accepted separately |

## Batch 5 — metric definitions (2026-08-07)

| # | Question | Decision | Consequence |
|---|---|---|---|
| D17 | Suppression vs always-show conflict | **Rewrite `CLAUDE.md` rule 6 — always show, always flag** | No aggregate is ever hidden; uncertainty is mandatory instead |
| D18 | How is uncertainty displayed? | **Range — IQR or min–max**, alongside the median | Every aggregate carries a spread, not just a point estimate |
| D19 | Travel time to where? | **Three specific addresses**: Niemcewicza (Warszawa), Kamienna (Elbląg), Budy Grabskie 53 | Point-to-point routing against personal anchors, not city centroids |
| D20 | Plots with no zoning data | **Explicit "unknown — check at the gmina"** | Never inferred, never guessed, never silently treated as buildable |

## Batch 6 — privacy, naming, process (2026-08-07)

| # | Question | Decision | Consequence |
|---|---|---|---|
| D21 | How to store the routing anchors | **Gitignored local config** | `config/anchors.example.yml` committed with placeholders; real `config/anchors.yml` never enters git |
| D22 | What does "nature" measure? | **Distance to forest, distance to water, protected-area status, distance to noise sources** — all four | Four separate attributes, each shown with its own value |
| D23 | Next step | **Docs only — PRD + validation, then stop** | No code until this is reviewed |
| D24 | Repo name | **Rename — suggestions requested** | Pending; see README |

## Batch 7 — the analytical layer (2026-08-07)

| # | Question | Decision | Consequence |
|---|---|---|---|
| D25 | Who analyses, and where? | **All three** — UI screens, notebook against the database, and generated digests | Needs a stable documented query layer *and* screens *and* scheduled reports |
| D26 | Which analytical questions matter? | **"Is this plot over- or under-priced?"** and **"What should a plot with these features cost in this place?"** | Reframes the analytical layer around **valuation**, not exploratory dashboards. Now the product's centre of gravity |
| D27 | How to handle mix-shift in time series | **Mix-adjusted — stratify and reweight** | Plain medians are never the headline trend figure |
| D28 | What must be held constant when comparing areas | **Always split by buildability** | No cross-area comparison ever mixes buildable and non-buildable land |

## Batch 8 — valuation design (2026-08-07)

| # | Question | Decision | Consequence |
|---|---|---|---|
| D29 | Valuation target | **Both asking and sales, shown separately** | Two estimates per plot, never blended (rule 5) |
| D30 | Estimator | **Comparable-set median, transparent** | Every estimate is traceable to the specific plots behind it |
| D31 | What-if forms to support | **All four**: price a hypothetical plot; same plot in a different place; value of each feature; value if it became buildable | Valuation is a general function of (features × place), not just a listing lookup |
| D32 | How uncertainty is expressed | **Always a range, never a point** | Consistent with rule 6. Range width *is* the confidence signal |

## Batch 9 — model governance, documentation, evaluation (2026-08-07)

| # | Question | Decision | Consequence |
|---|---|---|---|
| D33 | Comparables can't isolate per-feature value — how to square with D30/D31 | **Comparables for the verdict, regression for feature values** | Two estimators with strictly separated roles; the regression never produces the headline number |
| D34 | Which areas to document next | **All eight**: analytics methodology, taxonomy & extraction, UX, geocoding, temporal model, NFR & access, operations & backup, glossary | Docs 05–12 |
| D35 | How to evaluate the valuation | **Log every prediction, score it later against realized outcomes** | `valuation_log` must exist from the first estimate ever made, or the evidence never accumulates |

## Open — not yet decided

| # | Question | Blocks |
|---|---|---|
| O1 | Which listing portals specifically, and are land-specific boards worth adding for rural plots? | M1 connector work |
| O2 | Outcome of the RCN access research (D5) — which of the ~70 powiats publish freely | M1 sales-price connector |
| O3 | Final repo name (D24) | Cosmetic only |
| O4 | Simple access gate for "a few friends" (D1) — shared password, IP allowlist, or none | M2 deployment |
| O5 | Does "as far as free data allows" (D8) include GUS historical series behind bulk-download friction? | M1 baseline import |
| O6 | **Size adjustment**: price per m² falls as plots get larger. D28 mandated only the buildability split. Do we also adjust for size, beyond the ±50% area band already in FR-26? Recommendation: yes — see [`05-analytics-methodology.md`](./05-analytics-methodology.md) §4 | Area comparison fairness |
| O7 | **Standard-plot benchmark**: express each area's price as "what a fixed reference plot would cost here". Considered in batch 7 and not selected; would make cross-area comparison a single honest number | Area comparison UX |
| O8 | Digest cadence and channel for the generated-report half of D25 | M5 |
| O9 | Notebook access mechanism for D25 — read replica, read-only role, or direct access | M2 |
