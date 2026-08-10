# Repository layout & module contracts

Where code goes, and the boundaries that several validation methods test
structurally rather than by review.

Epic: E1.1. Validation: V21, V25, V29, V39.

---

## 1. Layout

```
├── CLAUDE.md                  # project rules
├── docs/                      # 00–21
├── config/
│   ├── anchors.example.yml    # placeholders only — committed
│   ├── anchors.yml            # real addresses — GITIGNORED (FR-22)
│   └── sources.yml            # per-source rate limits, cadence, enabled flags
├── src/lpc/                   # "land price compare" — rename with the repo (O3)
│   ├── config/
│   ├── db/                    # models, migrations, roles
│   ├── ingest/
│   │   ├── base.py            # connector contract (§2)
│   │   ├── http.py            # robots, rate limiting, backoff  (V14)
│   │   ├── raw_store.py
│   │   ├── portals/
│   │   └── official/          # gus_bdl, rcn, prg, uldk, egib, urban_registry
│   ├── normalize/             # canonical schema, units, validation, quarantine
│   ├── extract/               # attribute extraction, category maps  (V26, V27)
│   ├── dedup/
│   ├── geo/                   # resolution ladder, precision gating, projections
│   ├── enrich/                # zoning, constraints, nature, access
│   ├── metrics/               # aggregates, strata, mix-adjusted index
│   ├── valuation/
│   │   ├── comparables.py     # the ONLY source of a verdict   (V18)
│   │   ├── estimator.py       # returns ranges, never points   (V17)
│   │   ├── verdict.py         # must not import ..model        (V21)
│   │   └── log.py             # valuation_log writer           (V24)
│   ├── model/                 # hedonic regression — feature values ONLY
│   ├── api/                   # FastAPI, response models, boundary enforcement
│   ├── app/                   # Streamlit surface for v0 (D59)
│   ├── digest/
│   └── ops/                   # pipeline orchestration, assertions, alarms
├── frontend/                  # Next.js + MapLibre — full plan only, not v0
├── tests/
│   ├── unit/ integration/ architecture/ benchmarks/
│   ├── fixtures/<source>/     # recorded, dated, scrubbed
│   └── labelled/              # 200-advert extraction set, 200-listing dedup set
├── scripts/                   # audits, drills, one-off research
└── docker-compose.yml
```

## 2. The connector contract

Every source implements the same three-stage contract, which is what lets FR-6's
health and drift alarms be generic rather than per-connector:

```python
class Connector(Protocol):
    name: str
    kind: Literal["portal", "registry", "api"]

    def fetch(self, since: datetime | None) -> Iterator[RawDocument]:
        """Incremental, resumable. Honours robots.txt and the rate limit."""

    def parse(self, doc: RawDocument) -> Iterator[ParsedItem]:
        """Pure. No I/O — so every parse is testable against a fixture."""

    def emit(self, items: Iterable[ParsedItem]) -> IngestResult:
        """Writes canonical rows. Reports counts, failures, drift signals."""
```

Rules:

1. `parse` is **pure**. This is what makes re-parsing from `raw_document`
   possible (V42) and every parser testable without network access.
2. `fetch` never bypasses `robots.txt`, rate limits or anti-bot measures. HTTP goes
   through `ingest/http.py` only — no connector constructs its own client, so V14
   has a single place to enforce.
3. `emit` returns counts and parse-failure rates; the runner raises the drift alarm
   (V8). Connectors do not decide whether they are healthy.
4. A connector never writes to `metric_*` or `valuation_*`. Ingestion and analysis
   are separate stages.

## 3. Module boundaries enforced by tests

These are architecture tests (E25.3), not conventions:

| Boundary | Rule | Test |
|---|---|---|
| `valuation/verdict` ✗→ `model` | The verdict path cannot import the regression | **V21** |
| `extract` ✗→ `enrich.zoning` writes | Advert text can never set `buildability` | **V25** |
| `api` responses | Every price carries a type; every aggregate carries `n`+range | **V3, V4** |
| `metrics`, `valuation` ✗→ `ingest` | Analysis reads the database, never a source | E25.3 |
| `geo` precision gate | Nature/parcel enrichment unreachable below `address` | **V29** |
| Everything ✗→ `config.anchors` raw values | Anchor addresses never leave config | **V7** |

The strongest of these is V21's: deleting `src/lpc/model/` entirely must leave the
test suite green except for feature-value tests. If verdicts break, the separation
was never real.

## 4. Testing layers

| Layer | What it covers | Speed |
|---|---|---|
| `unit/` | Parsers, extractors, estimator maths, strata | Fast, no I/O |
| `integration/` | Database constraints, connectors against fixtures, API | Medium |
| `architecture/` | Import boundaries, schema constraints, response models | Fast |
| `benchmarks/` | V38 at projected volume | Slow, on demand |
| `labelled/` | Extraction and dedup scoring against hand labels | Medium |
| `drills/` | Restore (V40), re-parse recovery (V42), fault injection (V41) | Slow, scheduled |

Δ data assertions live in `ops/assertions/` and run inside the pipeline, not in the
test suite — they check production data, not code.

## 5. Naming

- English identifiers, Polish only in UI strings (D15) and in the domain terms
  fixed by [`12-glossary.md`](./12-glossary.md).
- Database columns match the schema in [`15-database-schema.md`](./15-database-schema.md)
  exactly; no per-module renaming.
- `parcel` and `plot` are distinct; see [`12-glossary.md`](./12-glossary.md) for the
  definition and the case where one sale spans several parcels.
- `price_type` is spelled identically everywhere — database, API, frontend — so it
  can be grepped as a single token when auditing rule 6.

## 6. Definition of done

A work item is done when all of these hold — this is rules 4 and 5 made operational:

1. Its PRD requirement exists ([`02-prd.md`](./02-prd.md)).
2. Its validation method exists ([`04-validation.md`](./04-validation.md)).
3. Tests were written **before** the implementation and failed first.
4. Tests pass; relevant Δ assertions pass against real data.
5. Provenance holds: any new stored number carries source and `as_of`.
6. Any new price field carries `price_type`; any new aggregate carries `n` and range.
7. No personal data enters git, fixtures or logs.
8. The document map in the PRD is updated if a new document was added.
