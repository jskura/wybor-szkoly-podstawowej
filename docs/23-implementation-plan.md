# Implementation plan

The test plans say what to assert. This says what to build, in what order, and
what "done" means at each stage.

Rules that govern it: rule 4 orders the work as failing test, then implementation,
then passing test. Rule 8 makes every stage end at a review and a commit.

---

## 1. Repository layout

The package is `dzialki` (D112). The repository is `ile-za-dzialke` (D77).

```
ile-za-dzialke/
├── CLAUDE.md               project rules
├── docs/                   00–23
├── config/
│   ├── anchors.example.yml placeholders only, committed
│   ├── anchors.yml         real addresses, gitignored (FR-22)
│   ├── sources.yml         per-source rate limit, cadence, enabled flag
│   ├── params.yml          every ratified parameter (§2)
│   ├── teryt_bdl.yml       TERYT to BDL unit map, as data (D97)
│   └── register_classes.yml  register class → regime, one row each (D117)
├── src/dzialki/
│   ├── config/             loading, validation, the missing-file error
│   ├── db/                 models, migrations, roles
│   ├── ingest/
│   │   ├── base.py         the three-stage contract
│   │   ├── http.py         robots, rate limit, backoff. The ONLY HTTP client
│   │   ├── raw_store.py    content-hashed payload storage
│   │   ├── portals/
│   │   └── official/       gus_bdl, kowr, auctions, bip, prg, uldk, egib
│   ├── normalize/          units, price per m², bands, quarantine
│   ├── extract/            attributes, category maps
│   ├── dedup/
│   ├── geo/                resolution ladder, precision gate, projections
│   ├── enrich/             buildings, feasibility, restrictions
│   ├── metrics/            aggregates, stock and flow
│   ├── valuation/
│   │   ├── comparables.py  the only source of a verdict
│   │   ├── estimator.py    returns ranges, never a bare median
│   │   ├── verdict.py      must not import ..model
│   │   └── log.py          valuation_log writer
│   ├── render/             pure functions returning a node tree
│   ├── app/                Streamlit, reads render/ only
│   └── ops/                pipeline, assertions, alarms
├── tests/
│   ├── unit/ integration/ architecture/ property/ drills/
│   ├── fixtures/<source>/  recorded, dated, scrubbed
│   └── labelled/           the hand-labelled sets
├── scripts/                audits, drills, research
└── docker-compose.yml
```

Two boundaries are load-bearing and tested, not trusted:

- `render/` is pure and returns a node tree. `app/` maps that tree to Streamlit.
  This is what makes every honesty rule testable without driving a browser.
- `valuation/verdict.py` cannot import the model. Deleting the model package must
  leave the suite green except for feature-value tests.

## 2. One file holds every ratified parameter

`config/params.yml`. Every value the owner ratified, in one place, with its
decision number. No parameter is written as a literal in code or in a migration.

```yaml
comparables:
  area_band_pct: 50          # D108
  recency_months: 12         # D110
  min_before_widening: 3     # D109 — a median of 3 is close to noise
  widening_ladder: [gmina, radius_10km, radius_25km, powiat]
aggregates:
  flow_window_days: 90       # D107
  iqr_switch_n: 5            # D67 — configuration, never a database CHECK
validation:
  area_min_m2: 300           # O12
  area_max_m2: 200000
  conflict_threshold_pct: 5  # D81
  conflict_threshold_base: register   # D120 — the register area is the denominator
crawl:
  fraction_tolerance_pln: 1  # D94
  count_tolerance: {abs: 3, pct: 2}   # D95
  retry_after_max_s: 3600    # D93
feasibility:
  good_neighbour_radius_m: 100        # D102 — the labelled set arbitrates
  coverage_probe_radius_m: 500        # D103 — separates "isolated" from "unmapped"
  coverage_probe_min_buildings: 3     # D103
surface:
  thousands_sep: " "    # D125 — non-breaking, so a number never breaks
```

Three of these are **configurable because the evidence has not arrived yet**, not
because someone may want to change them. D102 and D103 name the 20-parcel labelled
set as their arbiter, and V60 scores the shipped value against it. A wrong
coverage probe reproduces the exact error the `unknown` verdict exists to prevent:
it reads an unmapped county as an empty one.

Why this matters: the audit found nine documents hard-coding one unratified
threshold. A single file makes a change one edit, and makes the current value
readable without grep.

## 3. Stages

Each stage ends with a review and a commit. A stage is done when its tests pass
**and** the checks in the "done" column hold.

| Stage | Builds | Tests first | Done when |
|---|---|---|---|
| **S1** | Repo, Docker, Postgres with PostGIS, migration harness, config loading | V7, V65 | `docker compose up` gives an empty working system. Anchors load from the gitignored file. A missing key gives a named error, not a crash. No ratified value appears outside `params.yml`. V7(b) runs as a pre-push hook, never in CI (D124) |
| **S2** | The schema | V1, V2, V4 database limbs | Every CHECK exists. A bad `price_type` cannot be inserted. A listing cannot carry a `transaction` price kind (D115). Stock and flow rows do not collide |
| **S3** | Boundaries and TERYT for both rings | V6, V30, V31 | Budy Grabskie resolves to gmina Skierniewice. The ring set matches the fixture manifest exactly. Distances hold at both scales, and the degrees control fails |
| **S4** | GUS sales client | V13, V16 | Every in-scope powiat has a sales series. The unit map is read from config |
| **S5** | Connector contract, HTTP client, robots, rate limit | V14, V57, V58, contract tests | `parse` is pure under a blocked socket. Only `http.py` imports an HTTP library. Rate limit holds over 500 requests |
| **S6** | Normalization and quarantine | V10, V28, and the property tests | Every area form parses to its exact value. Compound areas sum. Out-of-band records are flagged, not dropped |
| **S7** | Dedup at v0 strength | V56, V47 duplicate relation | Exact duplicates collapse. Near-duplicates do not. No duplicate rate is claimed |
| **S8** | Aggregates, stock and flow | V4, V45, V47, V48, V62 | The metamorphic suite passes with its non-vacuity companions. Percentiles match the reference. Stock and flow differ by the constructed amount |
| **S9** | Comparable estimator and the valuation log | V17–V20, V24, V51 | No mixed-buildability set at any widening step. Every estimate writes a log row. Cross-validation reports its four metrics |
| **S10** | Render layer | V59, V35–V37 | Every honesty rule has a passing and a failing tree. All five states exist for every component |
| **S11** | Streamlit app and map | V59, V51c | URL paste works and fails loudly. Excluding a comparable recomputes and logs |
| **S12** | Portal connector | V43, V44, and the S5 tests | **Blocked on the robots.txt reading.** Corpus count agrees with the source's own total |
| **S13** | KOWR, auctions, BIP | V53, V54, V55 | Every gmina is covered or explicitly listed as uncovered. Auction fractions parse |
| **S14** | Parcels, buildings, feasibility | V60, V66, V29, V31 | Missing building data yields `unknown`, never `unlikely`. A `likely` verdict from the road proxy carries its own disclaimer, and its wording differs from the confirmed-ownership wording (D114) |
| **S15** | Purchase restrictions | V61, V63, V64 | Neither badge renders on the other class. One prompt **per regime** per session (D116). **The forest badge waits on the three `‡` claims in `19` §2a.1** |

## 3a. What external data each stage needs, and what blocks it

Written after building S1 to S5. Three stages turned out to need data no code can
produce, and the plan above did not say which.

| Needs | Stages | State |
|---|---|---|
| Nothing external | S1, S2, S5, S6, S7, S8, S9, S10, S11 | **Built.** 1 521 tests pass, one skips outside CI by design |
| The national boundary register, clipped to the two rings | S3, S4 | **Blocked.** The clip gives the gmina and powiat lists every later stage keys off |
| The BDL unit register | S4 | **Blocked.** Recorded as data (D97); the committed map is empty and refuses to load |
| The portal `robots.txt` reading (O10) | S12 | **Blocked on you** |
| The KOWR, auction and BIP `robots.txt` readings (Q9) | S13 | **Blocked on you** |
| County building data, or OSM as the fallback | S14 | **Blocked** |
| The two acts read against their consolidated text (O40) | S15 | **Blocked on you** |

**Where the eleven built stages stand.** Every one of them runs against synthetic
data, recorded fixtures or the database, and none needs a network. The four that
remain need something no code can produce, which is why they are listed above
rather than scheduled below.

**A stage split by its data is recorded as split, never as done.** S3 and S4 each
have a half that runs on synthetic geometry and a half that waits on a download.
Marking either as finished would make the plan agree with itself and disagree
with the repository.

## 4. Order, and why

S1 to S4 depend on nothing external. They run now.

S5 builds the connector machinery without any portal, so it also runs now. Only
S12 needs the robots.txt answer.

S6 to S11 depend on data, but tests use fixtures, so they run without a live
crawl. Real data arrives when S12 or S13 lands.

**The one ordering trap:** S9 writes the valuation log. Every estimate must be
logged from the first one, because a comparable set cannot be reconstructed later.
So S9 ships the log with the estimator, never after it.

## 5. What "review after each stage" means

Not a glance at the diff. Four checks:

1. Do the tests assert **specific values**, or only that something was produced?
2. Does any new number appear without its source and its date?
3. Does any new parameter appear as a literal instead of in `params.yml`?
4. Does the stage's own validation method still describe what was built?

The fourth catches the failure this project keeps producing: the code drifts from
the document, and both look right on their own.

## 6. Simplify after each stage

Rule 8 puts a simplify step before each commit. For code, that means:

- Remove any helper used once.
- Remove any configuration option with one caller and one value.
- Collapse any abstraction added for a case that has not arrived.

The plan above deliberately has no plugin system, no dependency injection
framework and no abstract base beyond the connector contract. Each of those would
be an abstraction built for a second case that does not exist yet.

## 7. What this plan does not cover

The full-plan epics in `13-scope.md`. Zoning plans, nature attributes, routing,
the hedonic model, alerts, the API and the Next.js frontend. None of them is in
the 15 stages above.
