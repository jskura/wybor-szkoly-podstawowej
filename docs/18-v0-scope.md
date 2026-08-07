# v0 — the first buildable version

**Plan of record** (D38, reshaped by batch 11). [`13-scope.md`](./13-scope.md) —
the 26-epic, 150–200 day plan — is retained as a menu, not the plan.

Goal: answer the question you confirmed is the real constraint (D52) — *"is this
price fair?"* — across both anchor rings, using every source where rural land
actually appears.

---

## 1. What changed after batch 11

Four answers reshaped this document, and one of them overturned reasoning I had
repeated throughout the whole documentation set.

| Answer | Effect |
|---|---|
| **Buying within 6 months** (D45) | *"Listing history cannot be backfilled"* was my headline sequencing argument in five documents. On a six-month horizon it barely matters. **Snapshots stay — they are nearly free and they are insurance — but they are no longer the reason to hurry.** What matters now is seeing what is on the market *this week*, across as many sources as possible |
| **WZ route acceptable** (D46) | `unknown` buildability is a **flag, not a filter**. The zoning epic drops in urgency; the **good-neighbour test** (`19` §1) replaces it as the thing worth building |
| **Three off-portal sources** (D47) | Auctions, KOWR and gmina BIP enter scope. For rural land these may carry more signal than the portals |
| **Both rings** (D49) | No geographic narrowing, so the ten-day figure no longer holds — §3 |

## 2. What v0 is

| | |
|---|---|
| **Question** | For a plot in either ring: is its zł/m² sane next to comparable land, and next to what land actually sold for in that powiat? |
| **Geography** | **Both** 25 km rings — Budy Grabskie and Elbląg (D49) |
| **Plot focus** | ~2000–4000 m² (D48). Comparables band around that; nothing is excluded, but the defaults centre there |
| **Offering prices** | One portal, daily, list-page-first — **plus** KOWR and auction sources (D47) |
| **Sales prices** | GUS BDL, powiat level, quarterly — free and guaranteed |
| **Output** | A notebook, plus one simple map |
| **Hosting** | Your machine. No VPS (D44) |
| **How built** | I implement, you review each step (D53), TDD per rule 3 |

## 3. Effort — v0 no longer fits ten days (O15)

Stated plainly rather than absorbed silently:

| Increment | Days |
|---|---|
| Baseline — portals, **both rings**, price comparison | ~10 |
| + bailiff / bankruptcy auctions | +2 |
| + KOWR state land | +1.5 |
| + gmina BIP notices (~50 gminas, each a different format) | +4–6 |
| + parcels, buildings, good-neighbour test (D50) | +3–4 |
| + farmland purchasability badge (D51) | +1 |
| **Everything you asked for** | **~22–25 days** |

**Recommended split — needs your ratification (O15):**

- **v0 (~10–13 days)** — both rings; portals + KOWR + auctions; price comparison;
  snapshots as insurance. **Drops gmina BIP**, which is the highest-effort and most
  heterogeneous of the three sources.
- **v0.5 (~8 days)** — parcels, the good-neighbour test, the purchasability badge.
  Given D46 and D52 this is where the product gets genuinely decision-useful.
- **Gmina BIP** — only if v0 shows portal and KOWR coverage is thin.

If you would rather have everything at once, that is your call to make — it is
~4–5 weeks rather than ~2, and I would rather say so than deliver it late.

## 4. What v0 still excludes

Zoning plans (MPZP / plan ogólny) · nature attributes · travel-time routing ·
self-hosted geocoding · the hedonic feature-value model · mix-adjusted indices ·
the comparable widening ladder · RCN parcel-level transactions · alerts and
digests · housing · API and frontend · labelled evaluation sets for extraction and
dedup.

**The honest limitation:** v0 compares price to price. It cannot tell you whether
you may build — that is v0.5's good-neighbour test — nor whether you may legally
buy — that is v0.5's purchasability badge. Both matter more than price
(`19` §3), and both come immediately after.

## 5. What v0 does not cut — the foundations

v0 cuts features, not foundations. Three things cannot be retrofitted cheaply:

| Foundation | Why |
|---|---|
| **Raw payload storage** | Every parser is eventually wrong; without raw payloads a bad parse is unrecoverable |
| **`price_type` on every price** | Retrofitting means auditing every number in the system |
| **Provenance** — source, `as_of`, `n`, spread | Same argument, and nearly free at the start |

**Daily snapshots** were on this list; after D45 they are demoted to *cheap
insurance*. They cost little and protect against the horizon slipping, but they are
no longer a reason to prioritise anything.

## 6. Work plan

| # | Work | Days |
|---|---|---|
| **0** | **Verify `robots.txt` for the candidate portals (O10)** — gate; if disallowed, stop and re-plan | 0.2 |
| 1 | Repo skeleton, Postgres+PostGIS in Docker, migrations, config | 1 |
| 2 | Minimal schema with the `price_type` CHECK constraints from [`15`](./15-database-schema.md) | 1 |
| 3 | PRG + TERYT for **both rings**; the Budy Grabskie → gmina Skierniewice known-answer test | 1 |
| 4 | GUS BDL client; sales series for both rings' powiats | 1.5 |
| 5 | Portal connector: robots handling, rate limiting, list-page-first, raw store, snapshots | 2.5 |
| 6 | Parse + normalize: area units, zł/m², validity bands, quarantine | 1.5 |
| 7 | KOWR connector | 1.5 |
| 8 | Auction connector (source choice open — O16) | 2 |
| 9 | Trivial dedup — exact/near-exact only | 0.5 |
| 10 | Aggregates by gmina and area band: median, p25/p75, min/max, n — always with spread, computed as **both stock and flow** (`20` §5) | 1.5 |
| 11 | Notebook: "price this plot" | 1 |
| 12 | One map view | 1 |

**≈ 13 days** with gmina BIP dropped and the good-neighbour work in v0.5.

## 7. How we know v0 worked

D54 makes this concrete: what would make you distrust it is **a number you know is
wrong**. So the known-plot check is the **primary** acceptance test, not a
secondary one.

| Check | Passes if | Priority |
|---|---|---|
| **Known-plot check** | Pick 5–10 plots you have actually looked at. v0's verdict matches your own judgement, or where it differs, v0 turns out to be right | **Primary (D54)** |
| **Sanity vs GUS** | Our offering median per powiat sits *above* the GUS sales figure by a plausible margin. An inversion means a broken parser, not a market finding | High |
| **Unit-conversion audit** | Hand-check 20 listings stated in ar or ha. Zero errors — a 100× error here is silent and fatal | High |
| **Coverage** | How many gminas in each ring have ≥5 listings? If most have 0–2, portals are the wrong source and that is the finding | High |
| **Source contribution** | How much supply do KOWR and auctions add over portals? Decides whether gmina BIP is worth the 4–6 days | Medium |
| **Duplicate eyeball** | Scan 50 listings for the same plot twice | Medium |

## 8. What v0 is designed to find out

| If v0 shows… | Then |
|---|---|
| `robots.txt` forbids crawling (O10) | Offering prices are off the table. Fall back to GUS/RCN plus KOWR and auctions — a smaller product. Decide before building further |
| Few listings in the rings (audit C2) | Rural land trades off-portal; promote gmina BIP and local agents over more engineering |
| KOWR and auctions add little | Drop them and stop maintaining three connectors |
| Prices coherent, but you still can't decide | The gap is buildability and purchasability — go straight to v0.5 (`19`) |
| A number you know is wrong (D54) | Diagnose before adding anything. Raw payloads make re-parsing possible |
| You stop opening the notebook | The tool was not the bottleneck. Stop |

## 9. The question worth asking before starting (O18)

You are buying within six months (D45). v0 is ~2 weeks and v0.5 another ~1.5, and
that assumes focused time. If the build slips, **the tool may not exist in time to
inform the purchase it was built for.**

That does not make it pointless — it may still be worth having for market
understanding, for a later purchase, or for the friends it is shared with. But it
is worth answering deliberately now rather than discovering it in month five.

## 10. Rules that still apply

`CLAUDE.md` is not suspended. PRD first · ask, don't assume · TDD · a validation
method before each feature · both price types always labelled · always show, always
flag.

**v0's validation subset** from [`04-validation.md`](./04-validation.md):
V1, V2, V4 (with the D42 correction), V5, V6 (both rings), V7, V10, V12, V13, V14,
V28, V30 — **plus the v0 additions** V43–V52, which cover the new sources and the
biases found in [`20-verification-strategy.md`](./20-verification-strategy.md):
corpus completeness against the source's own count, sort-order bias, stock vs flow,
auction/tender price separation, metamorphic properties, percentile differential
testing, golden-corpus regression, quarantine composition, the known-plot
acceptance check, and mutation testing of the numeric core.

The good-neighbour and purchasability methods are written in
[`19-legal-and-feasibility.md`](./19-legal-and-feasibility.md) §1.3 and §2.3.

**Before the first test is written**, each work item must clear the entry criteria
in [`20-verification-strategy.md`](./20-verification-strategy.md) §8.
