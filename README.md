# Land price comparison — Budy Grabskie & Elbląg areas

A tool for comparing **land prices** in Poland — both **offering prices** (asking
prices from listings) and **actual sales prices** (recorded transactions) — so that
a plot's asking price can be judged against what comparable land actually costs.

> ⚠️ The repository is still named `wybor-szkoly-podstawowej` from an earlier
> project. A rename is agreed (D24); candidates are at the bottom.

## Status

**Planning complete, scope deliberately reduced after an audit.** No code yet.

The full design — 26 epics, roughly **150–200 focused days** — is documented and
retained, but the **plan of record is [`docs/18-v0-scope.md`](docs/18-v0-scope.md)**:
a ~26–29 day version covering both 25 km anchor rings, both price types,
off-portal supply and the feasibility layer. Build it, learn from it, then decide what else earns its place.

Why the change: [`docs/17-assumption-audit.md`](docs/17-assumption-audit.md) is a
self-review that found seven internal contradictions and a long list of choices
made without asking.

**One unverified fact gates the offering-price half of the project:** nobody has
confirmed that the target portals' `robots.txt` permits crawling listing pages
(O10). It takes minutes to check, and it decides whether this is a listings product
or a registry-only one.

## v0 — the plan of record

| | |
|---|---|
| Question | "Is this plot's price fair?" — confirmed as the real constraint (D52) |
| Geography | Both 25 km rings — Budy Grabskie and Elbląg |
| Plot focus | ~2000–4000 m² |
| Offering prices | One portal, plus KOWR state land and bailiff/bankruptcy auctions |
| Sales prices | GUS BDL, powiat level — free and guaranteed available |
| Output | A Streamlit app, plus a choropleth and gmina table |
| Hosting | Your machine. No VPS, no routing engine, no geocoder |
| Effort | ~26–29 days — everything at once (D55), incl. the Streamlit surface (D59) |
| Includes | Gmina BIP, the WZ good-neighbour test, and the purchasability badge |
| Not included | Zoning plans, nature, routing, hedonic model, alerts, API, frontend |
| Headline number | **Flow** (recently listed), with stock alongside |
| Acceptance | Leave-one-out cross-validation, not human pre-registration |

The feasibility layer — the WZ good-neighbour test and whether you may legally buy
the plot at all — is folded in rather than staged after
([`docs/19-legal-and-feasibility.md`](docs/19-legal-and-feasibility.md)).

v0 cuts **features, not foundations**. Three things cannot be retrofitted, so all
three are there from day one: raw payload storage (every parser is eventually
wrong), `price_type` on every price, and provenance on every figure. Daily
snapshots run too, but as cheap insurance rather than the point — a six-month
buying horizon (D45) means accrued history barely pays off.

**What v0 cannot do:** it does not read zoning plans, so buildability comes from
the WZ good-neighbour test rather than from an MPZP. It shows no price trends,
because there is no accrued history to show.

### What v0 is designed to find out

| If v0 shows… | Then |
|---|---|
| `robots.txt` forbids crawling | Offering prices are off the table — fall back to a registry-only product, or stop |
| Very few listings in the rings | Rural land trades off-portal; the answer is different sources, not more engineering |
| Listings plentiful, prices coherent | The remaining question is buildability — invest in zoning data next |
| KOWR and auctions add little supply | Drop them rather than maintain three connectors |
| You stop opening the app | The tool was not the bottleneck. Stop |

## Documents

Start with `18` (what we're building), then `17` (why it shrank).

| Doc | What it is |
|---|---|
| [`docs/18-v0-scope.md`](docs/18-v0-scope.md) | **The plan of record** — the ~26–29 day version, its work plan, its checks, and what it will teach us |
| [`docs/17-assumption-audit.md`](docs/17-assumption-audit.md) | **Self-review** — contradictions, unasked questions, unverified facts |
| [`CLAUDE.md`](CLAUDE.md) | Binding project rules. Rule 1 is Simplified Technical English. Then: PRD first, ask do not assume, TDD, a validation method per feature, two price types, provenance, the two-pass workflow |
| [`docs/00-decisions.md`](docs/00-decisions.md) | Decision log — D1–D63; open items O1–O31, all closed or assigned, 3 blocked on you |
| [`docs/01-user-journeys.md`](docs/01-user-journeys.md) | 12 journeys (J1–J8 buying, J9–J12 analytical) and the capability map |
| [`docs/02-prd.md`](docs/02-prd.md) | Requirements FR-1..72, data model, architecture, milestones, risks |
| [`docs/03-data-sources.md`](docs/03-data-sources.md) | Polish data sources, the `robots.txt` gate, scraping ground rules |
| [`docs/04-validation.md`](docs/04-validation.md) | V1–V62 — how we know each feature works, plus a work-item → coverage table |
| [`docs/05-analytics-methodology.md`](docs/05-analytics-methodology.md) | The valuation method — comparables, ranges, mix adjustment, scoring |
| [`docs/06-taxonomy-and-extraction.md`](docs/06-taxonomy-and-extraction.md) | Asset classes, and how messy advert text becomes structured attributes |
| [`docs/07-geocoding.md`](docs/07-geocoding.md) | Location resolution, precision tiers, and what each tier may be used for |
| [`docs/08-temporal-model.md`](docs/08-temporal-model.md) | The four times, price intervals, revisions, incomplete periods |
| [`docs/09-ux-specification.md`](docs/09-ux-specification.md) | Screens, states, and the rules that keep the interface honest |
| [`docs/10-nfr-and-access.md`](docs/10-nfr-and-access.md) | Scale, the crawl budget, retention, access, cost |
| [`docs/11-operations.md`](docs/11-operations.md) | Daily pipeline, backup, monitoring, recovery drills |
| [`docs/12-glossary.md`](docs/12-glossary.md) | Polish ↔ code terminology |
| [`docs/19-legal-and-feasibility.md`](docs/19-legal-and-feasibility.md) | The WZ good-neighbour test, and agricultural purchase restrictions |
| [`docs/21-v0-ui-and-ux.md`](docs/21-v0-ui-and-ux.md) | **What you actually look at** — the plot check, the map, the coverage view, and the interaction rules that keep them honest |
| [`docs/20-verification-strategy.md`](docs/20-verification-strategy.md) | **How we know it's right** — verification tiers, the silent-failure catalogue, metamorphic testing, cross-validation |
| [`docs/13-scope.md`](docs/13-scope.md) | 26-epic work breakdown. **Retained as a menu, not the current plan** |
| [`docs/14-api-contract.md`](docs/14-api-contract.md) | Endpoints and types; where the price-type and sample-size rules are enforced |
| [`docs/15-database-schema.md`](docs/15-database-schema.md) | Full DDL — the product rules encoded as constraints |
| [`docs/16-repository-layout.md`](docs/16-repository-layout.md) | Module layout, connector contract, enforced boundaries, definition of done |

## The idea

A buyer looking for a plot cannot tell whether an asking price is reasonable,
cannot see what comparable land actually *sold* for as opposed to what sellers are
*asking*, and cannot easily tell whether building is permitted at all.

Every number in this product shows its **source**, **as-of date**, **sample size**,
**spread** and **price type**. Nothing is suppressed for being thin — it is shown
with its uncertainty visible, so that weak evidence looks weak.

## Scope

- **v0**: the two 25 km anchor rings — **Budy Grabskie** (gmina Skierniewice,
  łódzkie) and **Elbląg**
- **Full plan**: łódzkie, mazowieckie, and the Elbląg area (powiat elbląski +
  m. Elbląg)
- Land types by priority: budowlana → rekreacyjna → rolna → leśna/inne
- Free data sources only; Polish UI, English code and docs; daily collection
- Not a factor (D39): schools and amenities

## The central question, once valuation exists

*"What should a plot with these features cost in this place — and is this one over
or under?"*

The answer is **a median that never travels without its range and sample size**,
always traceable to the specific comparable plots behind it. A regression runs
alongside to say what each feature is worth, clearly marked as a model estimate,
and structurally barred from producing the verdict. See
[`docs/05-analytics-methodology.md`](docs/05-analytics-methodology.md).

## The full plan, if v0 justifies it

```
E1  Foundation
 └─ E2  Reference data ──┬─ E3  Official sales data
                         ├─ E4  Listing ingestion ─ E5 Normalization ─ E6 Dedup
                         │                                     │
                         │                            E7 Geospatial resolution
                         │              ┌──────────────────────┼───────────────┐
                         │           E8 Zoning        E9 Constraints/nature  E10 Access
                         │              └──────────────────────┼───────────────┘
                         └──────────────────────────── E11 Aggregation ─ E12 Valuation
                                                              │              │
                                                    E13 Feature model    E14 Scoring
                                                              │
                                                          E15 API ─ E16..E21 Frontend
                                                                       │
                                                                   E22 Alerts/digests
E24 Operations · E25 Quality harness · E26 Access control   (cross-cutting)
```

Critical path: E1 → E2 → E4 → E5 → E7 → E11 → E15 → E16. v0 takes thin slices of
E1–E6 and E11 only; see [`docs/13-scope.md`](docs/13-scope.md) §3a.

## Candidate repo names (D24)

| Name | Reading |
|---|---|
| `cena-ziemi` | "price of land" — plain, descriptive, Polish |
| `ile-za-dzialke` | "how much for a plot" — the actual question |
| `grunt-radar` | *grunt* = land/ground; suggests monitoring over time |
| `dzialkometr` | "plot-meter" — memorable, slightly playful |
| `parcela` | short, neutral, unambiguous |

`cena-ziemi` is the safest, `ile-za-dzialke` the most descriptive. Say which and
I'll update every reference.

## Next step

Check `robots.txt` (O10), then start v0 day 1 following the rule-3 cycle:
validation method → failing test → implementation → passing test. Definition of
done is in [`docs/16-repository-layout.md`](docs/16-repository-layout.md) §6.
