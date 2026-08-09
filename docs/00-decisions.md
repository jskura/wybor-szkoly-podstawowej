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
| D43 | A6 five-user testing programme | Replaced with checks the owner can actually run alone — see [`18-v0-scope.md`](./18-v0-scope.md) §7 |
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
| + Streamlit surface, map, URL paste (D59–D61) | +3.5 |
| **Total** | **~26–29 days** |

**Recommended split, not yet ratified (O15):** keep v0 at ~10–13 days with both
rings, portals, KOWR and auctions — dropping **gmina BIP**, which is the highest
effort and the most heterogeneous of the three — then add parcels, the
good-neighbour test and purchasability as **v0.5** (~8 days). Gmina BIP follows
only if coverage turns out thin.

## Batch 12 — verification (2026-08-07)

From [`20-verification-strategy.md`](./20-verification-strategy.md).

| # | Question | Decision | Consequence |
|---|---|---|---|
| D55 | v0/v0.5 split? | **Everything at once** — the full ~26–29 days | No staged delivery. Closes O15. Trade-off recorded in [`18`](./18-v0-scope.md) §3: nothing usable until week 4–5, and no mid-point evidence to redirect the remaining work |
| D56 | Stock or flow as headline? | **Flow is the headline**, stock alongside, neither ever unlabelled | Closes O20. Every aggregate specified before this was a stock measure |
| D57 | Pre-register estimates for the known-plot check? | **No** | Closes O22. Replaced by **leave-one-out cross-validation** (V51) — automatic, repeatable, and tier A/B rather than tier C. Plus comparability feedback (V51c) |
| D58 | Which verification techniques? | **Metamorphic, differential, mutation.** Golden-corpus regression **not** selected | Closes O21. Leaves a drift-detection gap recorded as O26 |

## Batch 13 — gap closure (2026-08-07)

A decisive pass over every open item. Each is now **closed**, **closed with a
proposal you can overturn**, or **genuinely blocked on you** — with no item left in
the vague middle.

| # | Was | Resolution |
|---|---|---|
| O1 | Which portals | **Proposed**: one portal for v0, chosen after O10. Candidates are the two large consumer portals; whichever permits crawling wins. If both do, pick the one with more land listings in the rings — measurable on day 1 |
| O2 | RCN access research | **Out of v0.** v0's sales baseline is GUS BDL, which is free and guaranteed. RCN returns only if v0 shows powiat-level sales are too coarse to be useful |
| O3 | Repo name | **Recommend `cena-ziemi`.** Awaiting your rename on GitHub; not blocking |
| O4 | Access gate | **N/A for v0** — it runs locally (D44). Returns only if hosted |
| O5 | GUS history depth | **Closed**: import everything BDL publishes. No reason to truncate free data |
| O6 | Size adjustment | **Closed with a measurement plan.** No explicit adjustment in v0. Instead: fit and *report* size elasticity per ring, and let LOOCV (V51) reveal whether error correlates with plot size. Adjust only if the evidence says so — this replaces my guess with a measurement |
| O7 | Standard-plot benchmark | **Adopted.** D48 makes it natural: report "what a 3000 m² buildable plot costs here" per gmina, as one comparable number across areas. Cheap once aggregates exist |
| O8 | Digest cadence | **Out of v0** |
| O9 | Notebook access mechanism | **Closed** — v0 is a local Streamlit app against a local database (D59) |
| **O10** | **robots.txt** | **BLOCKED ON YOU.** Unreachable from here. Procedure: open each portal's `/robots.txt`, record the verbatim text and the date in `docs/evidence/`, and note whether listing and search paths are allowed for a generic agent. Everything on the offering-price side waits on this |
| O11 | Valuation parameters | **Closed as provisional-and-measured.** Values stay as documented, marked `‡`, and V51 reports sensitivity so they are ratified from evidence rather than opinion |
| O12 | 50 ha area cap | **Closed**: band widened to 300 m² – 200,000 m². Anything outside is **flagged and visible**, never silently dropped — the original cap would have discarded legitimate farmland |
| O13 | Thin-data map rendering | **Proposed**: tiles below n=5 render hatched rather than solid, and the gmina label always carries `n`. In v0 the map sits beside the gmina table, which lowers the stakes |
| O14 | Housing | **Proposed**: collect but do not surface. The same connector returns it at near-zero marginal cost, and it keeps your original "housing and land" framing alive without spending v0 days on it |
| O15 | v0/v0.5 split | **Closed by D55** — everything at once |
| O16 | Auction sources | **Proposed**: start with the central e-auction service for bailiff sales, since one integration covers many offices; add *Monitor Sądowy i Gospodarczy* for bankruptcy estates only if the first proves thin |
| O17 | Building data coverage | **Closed**: EGiB buildings where the county publishes them, OSM buildings as a lower-confidence fallback, and **missing data yields `unknown`, never `unlikely`** (`19` §1.2) |
| **O18** | Is it worth building at all | **BLOCKED ON YOU.** ~26–29 days against a six-month horizon. Framed in `18` §9; only you can answer it |
| O19 | Price-kind taxonomy | **Closed by FR-64** — asking / auction_start / tender, never blended |
| O20–O24 | Verification choices | **Closed by D56–D58** |
| O25 | LOOCV thresholds | **Closed as procedure**: set from the first run's actuals, then treat regressions as failures. Guessing them now would be the same error the audit found |
| O26 | Drift-detection gap | **Closed with a cheaper substitute.** Full golden-file regression was declined (D58), so instead each pipeline run prints an **aggregate diff report** — every gmina whose median moved more than a threshold since the last run, with its `n` before and after. Printed for review, not asserted in CI. Catches most silent drift at a fraction of the cost |
| O27 | Flow window | **Proposed 90 days**, with V62's sensitivity check reporting 30 / 60 / 90 / 180 so the choice is evidence-based |

## Batch 15 — gaps found by writing the tests (2026-08-07)

From [`tdd/00-gap-analysis.md`](./tdd/00-gap-analysis.md). Six agents wrote TDD
specifications in parallel; four independently found that the schema did not
support features already specified as requirements.

| # | Question | Decision | Consequence |
|---|---|---|---|
| D64 | **What makes a gmina part of a 25 km ring?** Never defined anywhere, though the whole scope rests on it | **Any part of its boundary within 25 km of the anchor** | Inclusive at the edge: a gmina half inside is more useful shown with its `n` than silently excluded, which matches rule 6. Stated once in `15`; every consumer reads it from there |
| D65 | Are auction and tender prices offering or sales? | **Offering** — nothing has been transacted. Distinguished by a new `price_kind ∈ {asking, auction_start, tender}` | Closes the FR-64 gap; rule 5 unaffected, `price_kind` is the finer axis inside `offering` |
| D66 | `metric_unit_month` could not store stock and flow separately | **Key extended** with `area_band`, `series_kind`, `price_kind` | D56 made flow the headline; without this the two collide on insert |
| D67 | n=5 was frozen into a database CHECK while O11 marks it unratified | **Threshold moves to configuration**; the CHECK enforces internal consistency only | A provisional parameter must not require a migration to change |

## Batch 16 — source access (2026-08-07)

Prompted by "what can we do about robots.txt — it's a private tool for personal
use?". Full analysis in [`22-source-access-options.md`](./22-source-access-options.md).

| # | Question | Decision | Consequence |
|---|---|---|---|
| D70 | Is O10 a binary gate? | **No — four outcomes, four routes** | The plan treated a disallow as fatal to the offering-price layer. It is not |
| D71 | Preferred discovery mechanism | **`sitemap.xml` where available**, regardless of the robots outcome | It is published *for* crawlers, carries `lastmod` so change detection is better than paging search results, and is cheaper and more polite than the D40 list-page pass |
| D72 | Fallback if a portal disallows automated fetching | **Browser-assisted capture** — you browse, the tool parses what your browser already fetched | `robots.txt` governs robots, not you. Costs the daily automated refresh, which D45 already demoted |
| D73 | Evasion techniques | **Never** — no rotating agents, IP pools, CAPTCHA defeat, or claiming compliance while ignoring it | If we ever decide to crawl despite a disallow, that is recorded openly with FR-2 amended, not hidden behind a user-agent string |

### Items raised after batch 13

| # | Raised by | Status |
|---|---|---|
| O28 | Delivery surface (`21` §1a) | **Closed by D59** — Streamlit app |
| O29 | Map at this scale | **Closed by D60** — choropleth plus gmina table |
| O30 | How to point at a plot | **Closed by D61** — paste a listing URL |
| O31 | Keep agree/disagree | **Closed by D62/D63** — withdrawn, replaced by comparability feedback (V51c) |

### Still blocked on you

Only three, and only one blocks work:

1. **O10 — `robots.txt`.** Blocks the entire offering-price path. Minutes to check.
2. **O18 — whether this is worth building** given the timing. Not blocking, but worth answering before day 4 rather than day 20.
3. **O3 — the repo rename.** Cosmetic.

Everything else is decided or has a proposal you can overturn.


## Batch 14 — the interface, and a finding that outranks it (2026-08-07)

| # | Question | Decision | Consequence |
|---|---|---|---|
| D59 | What surface? | **Streamlit app** (O28) | +2 days over a notebook. Reusable, shareable with the few friends (D1) |
| D60 | Map at this scale? | **Yes, worth the day** (O29) | Choropleth over both rings, plus the gmina table |
| D61 | How to point at a plot? | **Paste a listing URL** (O30) | Needs per-portal page parsing; +0.5 day, and it breaks when a portal changes |
| D62 | Keep agree/disagree? | **Withdrawn** — "I will not be able to price the plots myself" | Not a UI answer; see D63 |
| D63 | What follows from that? | **Tier C verification does not exist for this project** | Expanded below: the agree/disagree control is withdrawn, D54's safeguard cannot generally fire, and the tool is the only opinion rather than a second one |

### D63 — The user cannot verify the tool's output. This changes the project.

You said you cannot price plots yourself. Taken seriously, three things follow, and
none of them is about the interface.

**1. Tier C verification no longer exists.** [`20`](./20-verification-strategy.md)
§2 defined four tiers of what is knowable. Tier C — "verifiable only by human
judgement" — assumed a human who could judge. That human does not exist for this
project. V51b (agree/disagree) is withdrawn: asking you to rate a verdict you have
no basis to rate would manufacture false signal, which is worse than no signal.

**2. D54 is now largely unfireable.** You said a number you know is wrong would
destroy your trust. If you cannot price plots, you will rarely be in a position to
know. **The safeguard you named cannot, in general, trigger.** That is worth
stating plainly rather than leaving as an unexamined comfort.

**3. The tool is not a second opinion — it is the only opinion.** Every earlier
document treated it as a check on your own judgement. It is now the judgement.
That raises the cost of being wrong substantially, and it means the burden shifts
entirely onto tier A/B verification: cross-validation, GUS cross-checking, and the
metamorphic, differential and mutation tests. Those must carry weight they were not
designed to carry alone.

**What replaces the human check.** Not a price judgement — a **comparability
judgement**. You may not know what a plot is worth, but you can look at a
comparable and say *"that one is on a main road and mine is in a forest"*. That is
a layperson-answerable question and it directly improves the estimate, because the
comparable set is the estimate. V51c replaces V51b on that basis.

**Consequence for the interface:** where the tool is uncertain it must say so
loudly and specifically, because you cannot supply the missing judgement yourself.
See [`21`](./21-v0-ui-and-ux.md) §7.
