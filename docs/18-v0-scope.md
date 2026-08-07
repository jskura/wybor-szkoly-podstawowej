# v0 — the two-week version

**This is the plan of record** (D38). [`13-scope.md`](./13-scope.md) — the 26-epic,
150–200 day plan — is retained as a possible future, not as the current scope.

Goal: answer the question you actually asked — *"is this plot's price sane for this
area?"* — in about two weeks, then decide from evidence what is worth building next.

---

## 1. What v0 is

| | |
|---|---|
| **Question answered** | For a plot in one of the two anchor rings: how does its zł/m² compare to other land on offer nearby, and to what land actually sold for in that powiat? |
| **Geography** | The **two 25 km rings only** — Budy Grabskie and Elbląg. Roughly 40–60 gminas, not ~500 |
| **Asset** | Land only, all four classes as claimed by the advert |
| **Offering prices** | One portal, daily, list-page-first (D40) |
| **Sales prices** | GUS BDL, powiat level, quarterly — free and guaranteed available |
| **Output** | A notebook plus one simple map view. No API, no Next.js, no accounts |
| **Hosting** | Your machine. No VPS (D44) |
| **Effort** | ~10 working days |

## 2. What v0 deliberately excludes

Everything below is *deferred, not cancelled* — each has a home in `13`.

Zoning and buildability · parcel resolution (ULDK/EGiB) · nature attributes ·
travel-time routing (OSRM) · self-hosted geocoding (Nominatim) · the hedonic
feature-value model · mix-adjusted indices · the comparable-set widening ladder ·
RCN parcel-level transactions · saved searches, alerts and digests · housing ·
the full frontend and API · dedup scoring against labelled sets · the extraction
evaluation set.

**Consequence to state plainly:** without zoning, v0 cannot tell you whether a plot
is buildable. It compares price to price. That is a real limitation and the most
likely reason you will want v1.

## 3. What v0 does *not* cut — the foundations

The distinction that makes v0 safe to build: **v0 cuts features, not foundations.**
Four things are irreversible if skipped, and all four are in v0 from day one.

| Foundation | Why it cannot wait |
|---|---|
| **Daily snapshots**, append-only | Price history cannot be backfilled. A month not collected is a month lost forever |
| **Raw payload storage** | Every parser will be wrong at some point; without raw payloads a bad parse is unrecoverable |
| **`price_type` on every price** | Retrofitting this into a schema and a codebase later means auditing every number |
| **Provenance** — source + `as_of` + `n` + spread on every figure | The same argument; and it is nearly free at the start |

Everything else in v0 can be thrown away and rewritten without loss.

## 4. Work plan

Ordered. Days are indicative for one person working focused.

| # | Work | Days | Notes |
|---|---|---|---|
| **0** | **Verify `robots.txt` for the candidate portals (O10)** | 0.2 | **Gate.** If listing paths are disallowed, stop and re-plan — see §7 |
| 1 | Repo skeleton, Postgres+PostGIS in Docker, migrations, config | 1 | Local only |
| 2 | Minimal schema: `source`, `raw_document`, `listing`, `listing_snapshot`, `transaction`, `admin_unit` — with the `price_type` CHECK constraints from [`15`](./15-database-schema.md) | 1 | Foundations, §3 |
| 3 | PRG boundaries + TERYT for the two rings only; the Budy Grabskie → gmina Skierniewice known-answer test | 1 | |
| 4 | GUS BDL client; import land sales series for the rings' powiats, `price_type='sales'` | 1.5 | Free, low risk, gives a working answer before any scraping exists |
| 5 | Portal connector: `robots.txt` handling, rate limiting, list-page-first fetch, raw storage | 2 | |
| 6 | Parse + normalize: area units (ar/ha/comma), zł/m², validity bands, quarantine | 1.5 | |
| 7 | Daily snapshot writer + a scheduled local run | 0.5 | Start collecting as early as possible |
| 8 | Trivial dedup: exact/near-exact match only, no labelled scoring | 0.5 | Good enough to stop obvious double-counting |
| 9 | Gmina and area-band aggregates: median, p25/p75, min/max, n — always with spread | 1 | |
| 10 | Notebook: "price this plot" — enter area + gmina, get the local distribution and where the plot sits in it | 1 | The actual deliverable |
| 11 | One map view (Streamlit + a simple choropleth) | 1 | Optional if the notebook suffices |

**Total ≈ 10–12 days**, with the `robots.txt` gate on day one.

## 5. The v0 answer to "is this plot fairly priced?"

Deliberately crude, and honest about being crude:

```
Działka: 1 500 m², Budy Grabskie, cena ofertowa 213 000 zł → 142 zł/m²

Oferty w gminie Skierniewice, działki 750–2 250 m², ostatnie 12 mies.:
    mediana 118 zł/m² · zakres 96–141 (IQR) · n = 23
    → ta działka jest powyżej górnej granicy zakresu

Ceny transakcyjne, powiat skierniewicki (GUS, 2025 Q4):
    średnia 104 zł/m² · dane kwartalne, poziom powiatu

⚠ v0 nie sprawdza planu zagospodarowania — nie wiemy, czy można tu budować.
```

No comparable-set widening ladder, no size adjustment, no buildability filter.
The area band is a simple ±50%, and it is **provisional** (O11).

## 6. How we know v0 worked (replaces the fictional user testing, D43)

The audit killed the five-user testing programme (A6). These are checks you can run
alone:

| Check | Passes if |
|---|---|
| **Sanity vs GUS** | Our offering median per powiat sits *above* the GUS sales figure, by a plausible margin. An inversion means a broken parser, not a market finding |
| **Known-plot check** | Pick 5 listings you have looked at yourself. Does v0's verdict match your own judgement? Where it disagrees, is v0 wrong or are you? |
| **Unit-conversion audit** | Hand-check 20 listings stated in ar or ha. Zero conversion errors — a 100× error here is silent and fatal |
| **Coverage** | How many gminas in each ring have ≥5 listings? If most have 0–2, portals are not the right source for your areas (audit C2) and that is the finding |
| **Duplicate eyeball** | Scan 50 listings for the same plot appearing twice. If duplicates are rampant, dedup gets promoted |
| **Snapshot integrity** | After two weeks, price changes are reconstructible from the snapshot series |

The middle two are the real test. If v0's numbers disagree with your own sense of
plots you have actually seen, the data or the method is wrong and no amount of
further building fixes that.

## 7. What v0 is designed to find out

v0 is partly an instrument for deciding whether v1 is worth it. Each outcome has a
prepared response:

| If v0 shows… | Then |
|---|---|
| `robots.txt` forbids crawling (O10) | Offering prices are off the table. Fall back to GUS/RCN only — a much smaller, powiat-level product. **Decide before building anything else** |
| Very few listings in the rings (C2) | Rural land trades off-portal. The answer is not more engineering — it is different sources (gmina boards, KOWR, local agents) |
| Listings are plentiful and prices coherent | v1 is worth it. The highest-value addition is **zoning/buildability**, because price without buildability is nearly meaningless |
| Prices look coherent but you still can't decide | The gap is comparables quality — promote the widening ladder and size adjustment (O6) |
| You stop opening the notebook | The tool was not the bottleneck. Stop |

## 8. Rules that still apply in full

`CLAUDE.md` is not suspended for v0:

1. **PRD first** — v0's requirements are this document; anything beyond it needs a PRD entry.
2. **Ask, don't assume** — the audit is the standing reminder. Provisional values are marked (O11).
3. **TDD** — tests before implementation, including for a ten-day build.
4. **Validation method before implementation** — §6 for the product, and the v0 subset of [`04-validation.md`](./04-validation.md) for the code.
5. **Both price types, always labelled** — v0 has both from day one.
6. **Always show, always flag** — every aggregate with `n` and spread, nothing suppressed.

### v0's validation subset

From [`04-validation.md`](./04-validation.md), the methods that apply now:
**V1** (price_type constraints), **V2** (never mixed), **V4** (n + spread, with the
D42 correction), **V5** (provenance), **V6** (boundaries, rings only), **V7**
(anchor config privacy), **V10** (normalization and quarantine), **V12**
(append-only snapshots), **V13** (GUS import), **V14** (crawl politeness), **V28**
(area units), **V30** (TERYT, the Skierniewice trap).

Deferred with their features: V3, V8, V9, V11, V15–V27, V29, V31–V42.

## 9. After v0

Do not plan v1 now. Run v0, apply §6, read §7, then decide. The 26-epic plan in
`13` remains available if the evidence justifies it — but it should be entered
deliberately, one epic at a time, and only where v0 showed the gap.
