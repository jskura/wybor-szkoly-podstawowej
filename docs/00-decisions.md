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

## Batch 10 — post-audit corrections (2026-08-07)

Prompted by [`17-assumption-audit.md`](./17-assumption-audit.md). These supersede
earlier decisions where they conflict.

| # | Question | Decision | Consequence |
|---|---|---|---|
| D36 | What is Budy Grabskie 53? | **A place visited/stayed at**, not owned | Stays a travel anchor and an area of interest. The product remains search-shaped, not "value my asset" |
| D37 | What decision is being made? | **Buy land to build on** | P1 self-builder is the only primary persona. The investor persona drops to a secondary interest; "value land I own" is out |
| D38 | What scale? | **Two-week version first, then decide** | **Supersedes the 26-epic plan as the active scope.** `13` is retained as a possible future, not the plan of record |
| D39 | Schools and amenities? | **Not relevant** | No amenity attributes. B4 in the audit is closed as a non-issue |

### Audit resolutions (technical corrections, no preference involved)

| # | Finding | Resolution |
|---|---|---|
| D40 | A1 crawl budget impossible | **List-page-first strategy**: list pages give price and active status for the whole corpus; detail pages fetched only for new or changed listings. The "<4 h daily" target is withdrawn and replaced with a per-scope budget |
| D41 | A2 mix adjustment at gmina level is noise | **Mix adjustment computed at powiat level and above only.** Gmina-level series are plain medians with their spread, explicitly labelled as unadjusted |
| D42 | A4 "never a point" contradicts `median` | Rule restated: **never a median without its range and n**. V17 is corrected; the `median` field stays |
| D43 | A6 five-user testing programme | Replaced with checks the owner can actually run alone — see [`18-v0-scope.md`](./18-v0-scope.md) §6 |
| D44 | A7 infrastructure does not fit | v0 needs **no VPS, no OSRM, no Nominatim**. Sizing is deferred until something needs hosting |

## Batch 11 — the buying situation (2026-08-07)

These came from asking what had still never been discussed. Several overturn
reasoning I had repeated throughout the documents.

| # | Question | Decision | Consequence |
|---|---|---|---|
| D45 | When are you buying? | **Within 6 months** | **Overturns the sequencing argument I used everywhere.** Accrued price history barely pays off on that horizon. Snapshots stay as cheap insurance, but "history cannot be backfilled" is no longer the reason to hurry |
| D46 | Would you buy without a zoning plan? | **Yes — the *warunki zabudowy* route** | `unknown` buildability is a **flag, not a filter**. The zoning epic (E8) drops in urgency; WZ *feasibility* rises in its place |
| D47 | Other land sources? | **Bailiff/bankruptcy auctions, KOWR state land, gmina BIP notices** — all three | Three new connector families, none previously in the plan |
| D48 | Plot size? | **~2000–4000 m²** | Comparable band and strata bands re-centred (O11). Straddles the 0.3 ha line in farmland law — see D51 |
| D49 | Which ring for v0? | **Both rings** (overrides the earlier "one ring, all sources") | v0 no longer fits ten days — see §Effort below |
| D50 | Estimate WZ feasibility? | **Yes — compute the "dobre sąsiedztwo" test** | Requires parcel geometry **and** building data, both of which v0 had excluded |
| D51 | Flag farmland purchasability? | **Yes, as a risk badge** | New legal layer: who may buy, and KOWR pre-emption. See [`19-legal-and-feasibility.md`](./19-legal-and-feasibility.md) |
| D52 | What is the real constraint, if not budget? | **Knowing whether the price is fair** | Confirms the original framing. Budget filtering is not built; distributions are shown instead |
| D53 | How do we build it? | **I implement, you review each step** | TDD cycle per rule 3, reviewed incrementally rather than in one lump |
| D54 | What would make you distrust it? | **A number you know is wrong** | Makes the known-plot check the **primary** acceptance test, not a secondary one |

### Effort consequence of D49 + D47 + D50

Both rings, four source families and the good-neighbour test do not fit in ten
days. The honest arithmetic:

| Increment | Days |
|---|---|
| v0 baseline — portals, both rings, price comparison | ~10 |
| + bailiff / bankruptcy auction connector | +2 |
| + KOWR state land connector | +1.5 |
| + gmina BIP notices (~50 gminas, each a different format) | +4–6 |
| + parcels, buildings and the good-neighbour test (D50) | +3–4 |
| + farmland purchasability flag (rides on the parcel work) | +1 |
| **Total** | **~22–25 days** |

**Recommended split, not yet ratified (O15):** keep v0 at ~10–13 days with both
rings, portals, KOWR and auctions — dropping **gmina BIP**, which is the highest
effort and the most heterogeneous of the three — then add parcels, the
good-neighbour test and purchasability as **v0.5** (~8 days). Gmina BIP follows
only if coverage turns out thin.

## Open — not yet decided

| # | Question | Blocks |
|---|---|---|
| O1 | Which listing portals specifically, and are land-specific boards worth adding for rural plots? | M1 connector work |
| O2 | Outcome of the RCN access research (D5) — which of the ~70 powiats publish freely | M1 sales-price connector |
| O3 | Final repo name (D24) | Cosmetic only |
| O4 | Simple access gate for "a few friends" (D1) — shared password, IP allowlist, or none | M2 deployment |
| O5 | Does "as far as free data allows" (D8) include GUS historical series behind bulk-download friction? | M1 baseline import |
| O6 | **Size adjustment**: price per m² falls as plots get larger. D28 mandated only the buildability split. Do we also adjust for size, beyond the ±50% area band? Recommendation: yes — see [`05-analytics-methodology.md`](./05-analytics-methodology.md) §4 | Post-v0 valuation |
| O7 | **Standard-plot benchmark**: express each area's price as "what a fixed reference plot would cost here" | Post-v0 |
| O8 | Digest cadence and channel | Post-v0 |
| O9 | Notebook access mechanism | Post-v0 |
| **O10** | **Do the target portals' `robots.txt` permit crawling listing pages?** Unverifiable from this environment (audit C1). **Gates all offering-price work, including v0** | **v0 day 1** |
| **O11** | **All valuation parameters are unratified** — comparable area band, recency window, minimum comparables, widening rungs, the IQR/min–max switch at n=5, strata bands, validity bands, quality targets, labelled sample sizes (audit B1). Provisional values are in use and marked as such | Post-v0 valuation |
| **O12** | The **50 ha area cap** probably excludes legitimate agricultural parcels. Provisional; revisit if agricultural land matters (D37 suggests it may not) | Post-v0 |
| **O13** | **A3 — thin-data map rendering.** Rule 6 says always show; a choropleth where most tiles rest on 1–3 listings may mislead in aggregate even when each tile is honestly labelled. Not resolved | When a map exists |
| **O14** | Housing: the original request said "housing and land". Land is priority (D6, D37), but housing is currently deferred to the last milestone. Is that acceptable, or should housing be collected in v0? | v0 scope |
| **O15** | **v0 no longer fits ten days** (D49 + D47 + D50 ⇒ ~22–25 days). Recommended split: v0 ≈ 10–13 days dropping gmina BIP; v0.5 adds parcels, good-neighbour and purchasability. **Needs ratifying** | v0 start |
| **O16** | Which auction sources specifically — e-licytacje.komornik.pl, individual bailiff sites, Monitor Sądowy i Gospodarczy for bankruptcy estates? Each has a different access model | Auction connector |
| **O17** | The good-neighbour test needs **building** geometry, not just parcels. County EGiB WFS coverage for buildings is uneven; where absent, fall back to OSM buildings with lower confidence, or decline to answer? | v0.5 |
| **O19** | **Price-kind taxonomy.** Auction starting prices, KOWR tender prices and portal asking prices are three different kinds of number. Rule 5 forbids mixing offering and sales; this needs a third category or explicit sub-types, settled **before** the auction connector is written | Auction connector |
| **O18** | D45 (buying within 6 months) undercuts the value of the whole build. If the tool is not usable in time to inform the actual purchase, is it still worth building — as a market-learning exercise, or for a later purchase? Worth answering explicitly rather than discovering in month five | Whole project |
