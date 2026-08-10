# Foundation test plan — work items 1, 2, 3

Pass 2 detail for [`../01-foundation-and-schema.md`](../01-foundation-and-schema.md).

Pass 1 fixed the **order** of the red–green sequence. This document fixes the
**values**: every fixture's literal content, every test's exact input, its exact
expected output, and the exact exception class it must observe. A developer should
be able to type these tests without making a further decision.

Where a value genuinely cannot be determined without downloading external data, it
is marked **`⟨RECORD⟩`** and §3.9 names exactly what has to be fetched and the
command that produces it. Nothing in this document is a plausible-looking
placeholder standing in for a real coordinate or a real TERYT code.

---

## 0. Names, and the decisions this plan now carries

### 0.1 Names (D77, D112)

The repository is `ile-za-dzialke`. The Python package is `dzialki`, and the source
root is `src/dzialki/`. Environment variables use the `DZIALKI_` prefix:
`DZIALKI_DATABASE_URL` for the application, `DZIALKI_TEST_DATABASE_URL` for the
suite. D112 records `dzialki` as a deliberate exception to D15, so a later reader
must not rename it back to English.

### 0.2 Decisions that change what to type

Batches 15, 17, 19 and 21 settled the schema after pass 1 was written. Pass 1 is
now corrected, and both documents agree. The table records the state to type.

| Area | What to type | Because |
|---|---|---|
| `price_kind` enum | Four labels, in order: `["asking","auction_start","tender","transaction"]` | **D65** names the three offering-side kinds; **D68** adds the sales-side one |
| `range_kind` enum | Three labels: `["iqr","min_max","unavailable"]` | **D69** — a source that publishes a central value with no spread must be storable, not an error |
| `series_kind` enum | `["stock","flow"]` | **D56**, **D66** |
| `metric_unit_month` primary key | `["teryt_unit","month","asset_class","buildability","price_type","price_kind","series_kind","area_band","generation"]` — `unit_level` is **not** a key column | **D66** |
| The n threshold | No `range_kind_matches_n` CHECK. R2.18a tests `range_bounds_ordered` in the database; R2.18b tests `range_kind_for(n)` against configuration | **D67** |
| `listing.price_kind` | `price_kind NOT NULL DEFAULT 'asking'` | **D65** |
| `transaction.price_kind` | `price_kind NOT NULL DEFAULT 'transaction' CHECK (price_kind = 'transaction')` | **D68** |
| `notice` table | A separate table with `notice_date DATE NOT NULL`, a nullable `auction_at`, a nullable price and area, and `price_kind` restricted to `{auction_start, tender}` | **D91** |
| Ring membership | `ST_DWithin(gmina.geom::geography, anchor.geom::geography, 25000)`, materialised into `admin_unit.in_ring TEXT[]` | **D64** |
| `admin_unit` provenance | `as_of DATE NOT NULL` and `source_id INT NOT NULL REFERENCES source(id)` | rule 7 |
| `listing.parcel_id`, `listing.plot_cluster_id` | Plain `BIGINT`, **no** foreign key in migration `0002`. R2.30 pins their absence so items 9 and 14 must add them on purpose | deferred by design |

### 0.3 Migration order the tests depend on

1. `source` before `admin_unit` — the `source_id` foreign key.
2. `admin_unit` before `listing`, `notice`, `transaction` and `metric_unit_month` —
   all four reference it.

---

## 1. Marker vocabulary

Every test carries exactly one layer marker and zero or more requirement markers.
CI selects on these (§7).

```python
# pytest.ini / pyproject [tool.pytest.ini_options] markers
unit          # no database, no network, no git, no filesystem beyond tmp_path and tests/fixtures
integration   # touches Postgres
architecture  # parses src/ with ast, or shells out to git ls-files / git check-ignore
property      # hypothesis-driven; implies its layer marker as well

needs_db              # requires the live Postgres+PostGIS container
needs_git_history     # requires a non-shallow clone with all refs
needs_local_secrets   # requires the gitignored config/anchors.yml
slow                  # > 5 s
```

---

## 2. Shared setup

Three conftest files. Nothing else may create a database connection.

### 2.1 `tests/conftest.py`

| Fixture | Scope | Yields | Notes |
|---|---|---|---|
| `repo_root` | session | `pathlib.Path` of the git top level, from `git rev-parse --show-toplevel` | Not `__file__`-relative arithmetic — that breaks under `pytest --rootdir` changes |
| `fixtures_dir` | session | `repo_root / "tests" / "fixtures"` | |
| `poland_bbox` | session | `(14.0, 49.0, 24.2, 55.0)` as `(min_lon, min_lat, max_lon, max_lat)` | The single definition. R1.5 and R1.6 both import it; two copies would drift |
| `git_is_shallow` | session | `bool` from `git rev-parse --is-shallow-repository` | Used by `needs_git_history` tests to `pytest.skip` with a **named** reason |

### 2.2 `tests/integration/conftest.py`

| Fixture | Scope | Behaviour |
|---|---|---|
| `pg_container` | session | Asserts `DZIALKI_TEST_DATABASE_URL` is set; refuses to run if the database name does not end in `_test` (a guard against pointing the suite at a real database and truncating it) |
| `migrated_db` | session | Drops and recreates the target database, then runs `alembic upgrade head` **as a subprocess**. Never builds the schema from SQLAlchemy metadata — a schema built by the helper would let a migration bug pass every constraint test in item 2 |
| `conn` | function | A `psycopg.Connection` opened on `migrated_db` inside an explicit transaction, **rolled back** in teardown. `autocommit=False`. Every constraint test uses this |
| `conn_as(role)` | function | Factory returning a connection authenticated as `app_read` / `app_write` / `app_pipeline`. Used only by R2.27–R2.29 |
| `schema_digest` | function | Callable implementing §6.1 of pass 1: `pg_dump --schema-only --no-owner --no-privileges`, strip `--` comments, `SET`/`SELECT pg_catalog.set_config` lines **and the `\restrict`/`\unrestrict` pair**, strip blank lines, sort remaining lines, SHA-256 |
| `geometry_digest` | function | `SHA-256` over `SELECT teryt, ST_AsBinary(geom) FROM admin_unit ORDER BY teryt` |

**The `\restrict` pair was found by running the test, not by writing it.** Recent
`pg_dump` versions wrap their output in `\restrict <nonce>` and `\unrestrict
<nonce>`, and the nonce is fresh on every dump. Without stripping it, two dumps of
one unchanged database differ, so R1.13 and R1.15 fail for a reason that has
nothing to do with the migrations. The rule above named only comments and `SET`
lines, which was the whole normalization until a real dump proved otherwise.

`migrated_db` sets `SET TIME ZONE 'UTC'` on every connection it hands out.
Partition-bound assertions (R2.25) compare rendered `timestamptz` literals, and
those render in the session time zone.

### 2.3 `tests/unit/conftest.py`

| Fixture | Scope | Yields |
|---|---|---|
| `synthetic_admin` | session | Parsed `tests/fixtures/synthetic/admin_hierarchy.json` (§3.3) |
| `synthetic_ring` | session | Parsed `tests/fixtures/synthetic/ring_membership.json` (§3.4) |
| `known_points` | session | Parsed `tests/fixtures/known_answers/known_points_2026-08-08.json` (§3.7) |

---

## 3. Fixture inventory — literal contents

### 3.1 `config/anchors.example.yml` (committed, not a fixture, asserted by R1.5)

```yaml
# Placeholder anchors. Copy to config/anchors.yml and fill in real values.
# config/anchors.yml is gitignored and must never be committed (FR-23, V7).
anchors:
  A:
    label: PLACEHOLDER_ANCHOR_A
    lat: 0.0
    lon: 0.0
  B:
    label: PLACEHOLDER_ANCHOR_B
    lat: 0.0
    lon: 0.0
```

`(0.0, 0.0)` is outside the Poland bounding box on both axes, so R1.5's bbox limb
is genuinely exercised. Neither label contains a digit.

### 3.2 `config/sources.yml` (committed, asserted by R1.10)

```yaml
sources:
  - name: minimal_registry
    kind: registry
  - name: gus_bdl
    kind: api
    base_url: https://bdl.stat.gov.pl/api/v1/
    enabled: true
    robots_ok: true
    rate_limit_rpm: 30
```

`minimal_registry` declares only `name` and `kind`, which is what lets R1.10 assert
all three fail-closed defaults on a single entry.

### 3.3 `tests/fixtures/synthetic/admin_hierarchy.json`

Hand-written, exact, no external data. Reserved TERYT namespace **`99`** — real
voivodeship codes are the even numbers 02–32, so `99` can never collide with a real
unit and can never be mistaken for one in a grep. Geometry is axis-aligned boxes in
EPSG:4326 chosen so that child areas sum to the parent **exactly**, which is what
makes R3.8 a real test rather than a tolerance test.

```json
{
  "as_of": "2026-08-08",
  "source_name": "synthetic",
  "units": [
    {"teryt": "99",      "level": "voivodeship", "name": "Testowskie", "parent_teryt": null,
     "wkt": "MULTIPOLYGON(((20.0 52.0, 20.4 52.0, 20.4 52.2, 20.0 52.2, 20.0 52.0)))"},

    {"teryt": "9901",    "level": "powiat", "name": "testowski zachodni", "parent_teryt": "99",
     "wkt": "MULTIPOLYGON(((20.0 52.0, 20.2 52.0, 20.2 52.2, 20.0 52.2, 20.0 52.0)))"},
    {"teryt": "9902",    "level": "powiat", "name": "testowski wschodni", "parent_teryt": "99",
     "wkt": "MULTIPOLYGON(((20.2 52.0, 20.4 52.0, 20.4 52.2, 20.2 52.2, 20.2 52.0)))"},

    {"teryt": "9901011", "level": "gmina", "name": "Testowo", "parent_teryt": "9901",
     "wkt": "MULTIPOLYGON(((20.0 52.0, 20.1 52.0, 20.1 52.1, 20.0 52.1, 20.0 52.0)))"},
    {"teryt": "9901021", "level": "gmina", "name": "Nowa Wola", "parent_teryt": "9901",
     "wkt": "MULTIPOLYGON(((20.1 52.0, 20.2 52.0, 20.2 52.1, 20.1 52.1, 20.1 52.0)))"},
    {"teryt": "9901031", "level": "gmina", "name": "Stara Wola", "parent_teryt": "9901",
     "wkt": "MULTIPOLYGON(((20.0 52.1, 20.1 52.1, 20.1 52.2, 20.0 52.2, 20.0 52.1)))"},
    {"teryt": "9901041", "level": "gmina", "name": "Zalesie", "parent_teryt": "9901",
     "wkt": "MULTIPOLYGON(((20.1 52.1, 20.2 52.1, 20.2 52.2, 20.1 52.2, 20.1 52.1)))"},

    {"teryt": "9902011", "level": "gmina", "name": "Testowo", "parent_teryt": "9902",
     "wkt": "MULTIPOLYGON(((20.2 52.0, 20.3 52.0, 20.3 52.1, 20.2 52.1, 20.2 52.0)))"},
    {"teryt": "9902021", "level": "gmina", "name": "Brzeziny", "parent_teryt": "9902",
     "wkt": "MULTIPOLYGON(((20.3 52.0, 20.4 52.0, 20.4 52.1, 20.3 52.1, 20.3 52.0)))"},
    {"teryt": "9902031", "level": "gmina", "name": "Podlesie", "parent_teryt": "9902",
     "wkt": "MULTIPOLYGON(((20.2 52.1, 20.3 52.1, 20.3 52.2, 20.2 52.2, 20.2 52.1)))"},
    {"teryt": "9902041", "level": "gmina", "name": "Krzywda", "parent_teryt": "9902",
     "wkt": "MULTIPOLYGON(((20.3 52.1, 20.4 52.1, 20.4 52.2, 20.3 52.2, 20.3 52.1)))"}
  ],
  "expected": {
    "counts": {"voivodeship": 1, "powiat": 2, "gmina": 8},
    "duplicate_names": {"Testowo": ["9901011", "9902011"]},
    "gminas_of_9901": ["9901011", "9901021", "9901031", "9901041"],
    "gminas_of_9902": ["9902011", "9902021", "9902031", "9902041"]
  }
}
```

`"Testowo"` appears at `9901011` and `9902011` — the same name under two different
parents. This is the **Skierniewice trap in synthetic form**, and it lets R3.9,
R3.11 and R3.13 be exercised on every commit without the recorded PRG clip. The
real Skierniewice pair (§3.6) remains the acceptance case; this one is the fast one.

### 3.4 `tests/fixtures/synthetic/ring_membership.json` — the D64 fixture

This is the fixture that discriminates between the three candidate ring rules. It
is **generated**, not hand-typed, by a committed script, because its vertices are
geodesic offsets and a hand-typed lon/lat would be a fabricated number. The script
needs only the WGS84 ellipsoid — **no PROJ grids, no download** — so the fixture is
fully determined by this document.

`scripts/fixtures/build_ring_fixture.py`:

```python
"""Builds tests/fixtures/synthetic/ring_membership.json. Deterministic.
Every vertex is Geod.fwd() from the synthetic anchor, so the distance from the
anchor to each arc is exact by construction rather than measured after the fact."""
from pyproj import Geod

GEOD = Geod(ellps="WGS84")          # matches PostGIS geography ST_DWithin(use_spheroid=true)
ANCHOR_LON, ANCHOR_LAT = 19.0, 53.0  # synthetic: a round graticule crossing, not an address

def sector(az_from, az_to, r_inner, r_outer, step_deg):
    """Annular sector as a closed 4326 ring, sampled finely enough that the chord
    sag between consecutive vertices is < 0.1 m at these radii."""
    ...
```

Sectors, and the expectation each one pins:

| teryt | name | azimuths | inner r (m) | outer r (m) | vertex step | nearest boundary distance | centroid distance | in ring `T`? |
|---|---|---|---|---|---|---|---|---|
| `9801011` | Straddler | 0.0° → 30.0° | 24 000 | 40 000 | 1.0° | ≈ 23 999.09 m | ≈ 32 700 m | **yes** |
| `9801021` | JustInside | 60.0° → 90.0° | 24 900 | 26 000 | 0.25° | ≈ 24 899.94 m | ≈ 25 450 m | **yes** |
| `9801031` | JustOutside | 120.0° → 150.0° | 25 100 | 30 000 | 0.25° | ≈ 25 099.94 m | ≈ 27 600 m | **no** |
| `9801041` | FullyInside | 180.0° → 210.0° | 1 000 | 10 000 | 1.0° | ≈ 999.96 m | ≈ 6 700 m | **yes** |

Centroid radii are area centroids of an annular sector,
`r̄ = ⅔·(r_out³ − r_in³)/(r_out² − r_in²)`, which is why `9801021` sits at 25.45 km
despite its boundary reaching 24.9 km — it is a member under D64 and a non-member
under the centroid rule. `9801011` is the same trap at larger scale.

Parents: voivodeship `98` "Pierscieniowskie", powiat `9801` "pierscieniowski",
each the convex hull of its children (computed by the same script, so hierarchy FKs
resolve; area additivity is **not** asserted on this fixture — that is §3.3's job).

Anchor row written by the same script:

```json
{"key": "T", "label": "SYNTHETIC_RING_ANCHOR", "lon": 19.0, "lat": 53.0}
```

The manifest block the script emits, which is the oracle for R3.19/R3.20:

```json
"expected": {
  "anchor": {"key": "T", "lon": 19.0, "lat": 53.0},
  "radius_m": 25000,
  "in_ring_T": ["9801011", "9801021", "9801041"],
  "not_in_ring_T": ["9801031"],
  "would_be_in_ring_under_centroid_rule": ["9801041"],
  "measured_nearest_m": {"9801011": null, "9801021": null,
                         "9801031": null, "9801041": null},
  "measured_centroid_m": {"9801011": null, "9801021": null,
                          "9801031": null, "9801041": null}
}
```

The `measured_*` nulls are filled by the script with `Geod.inv()` results at build
time and committed. The **discriminating assertion** is
`in_ring_T != would_be_in_ring_under_centroid_rule`: `9801011` and `9801021` are
members under D64 and non-members under the centroid rule, which is precisely the
ambiguity C1 identified. A ring implementation that silently used centroids fails
R3.19 on those two gminas and passes every other spatial test in the suite.
`9801041` (both rules include it) and `9801031` (both rules exclude it) are the
controls that stop R3.19 from passing for a trivial reason.

The script asserts before writing, and fails the build if any of these is false:

- every polygon is `shapely.is_valid`
- `GEOD.inv()` from the anchor to each sampled inner-arc vertex is within
  ±0.05 m of the nominal inner radius
- the four sectors are pairwise disjoint

### 3.5 `tests/fixtures/geo/` — invalid geometry (R2.23)

`bowtie_2026-08-08.wkt`, one line, no trailing newline issues:

```
POLYGON((20.0 52.0, 20.1 52.1, 20.1 52.0, 20.0 52.1, 20.0 52.0))
```

`ST_IsValid` is `false`; `ST_IsValidReason` contains `Self-intersection`. Small,
inside Poland, deliberately in the same neighbourhood as §3.3 so a CRS mistake
looks the same in both files.

`bowtie_repaired_2026-08-08.wkt` is the **verbatim output** of

```sql
SELECT ST_AsText(ST_Multi(ST_MakeValid(ST_GeomFromText(:bowtie, 4326))));
```

recorded once and committed. It is not hand-typed: `ST_MakeValid`'s output for a
bow-tie is a `MULTIPOLYGON` of two triangles whose vertex order is a PostGIS
implementation detail. Record it against the pinned image (§7.1) and re-record if
the image is bumped.

`admin_unit.geom` is `geometry(MultiPolygon, 4326)`, so R2.23's negative limb must
insert `ST_Multi(ST_GeomFromText(<bowtie>, 4326))` — otherwise the insert fails on
the geometry **type** (22023) before the `geom_valid` CHECK is reached, and the
test would pass for the wrong reason.

### 3.6 `tests/fixtures/prg/` and `tests/fixtures/teryt/` — recorded

`prg_clip_2026-08-08.gpkg` — clipped GUGiK PRG extract. Required content:

- every gmina with any part of its boundary within 25 km of anchor A or anchor B
  (D64 — the same rule the code uses, applied at clip time)
- **both** Skierniewice units: the rural gmina and the city
- powiat skierniewicki, powiat elbląski, m. Elbląg, m. Skierniewice
- every parent powiat and voivodeship of every included gmina
- geometry `MultiPolygon`, EPSG:4326

`manifest.json` — every key below is mandatory; `⟨RECORD⟩` values are produced by
the recording script, not by this document:

```json
{
  "source_url": "⟨RECORD⟩",
  "downloaded_at": "⟨RECORD⟩",
  "sha256": "⟨RECORD⟩",
  "clip_bbox_4326": [ "⟨RECORD⟩", "⟨RECORD⟩", "⟨RECORD⟩", "⟨RECORD⟩" ],
  "clip_rule": "ST_DWithin(unit.geom::geography, anchor.geom::geography, 25000) for anchors A and B, plus all ancestors",
  "counts": {"voivodeship": "⟨RECORD⟩", "powiat": "⟨RECORD⟩", "gmina": "⟨RECORD⟩"},
  "ring_gminas": {"A": ["⟨RECORD⟩", "…"], "B": ["⟨RECORD⟩", "…"]},
  "teryt": {
    "gmina_skierniewice_rural": "⟨RECORD⟩",
    "miasto_skierniewice":      "⟨RECORD⟩",
    "powiat_skierniewicki":     "⟨RECORD⟩",
    "miasto_elblag":            "⟨RECORD⟩",
    "powiat_elblaski":          "⟨RECORD⟩"
  },
  "duplicate_gmina_names": {"Skierniewice": ["⟨RECORD⟩", "⟨RECORD⟩"]}
}
```

`ring_gminas` holds two **exact TERYT lists**, not two counts. V6 no longer asserts
an approximate gmina count, so R3.20 compares sets. A list also says *which* gmina
went missing when the clip is re-recorded; a count says only that one did.

`terc_2026-08-08.csv` — the TERYT **TERC** register, columns
`WOJ;POW;GMI;RODZ;NAZWA;NAZWA_DOD`, semicolon-separated, covering at minimum every
unit in the clip. It must be downloaded **separately** from PRG; if it is derived
from the clip, R3.3 is vacuous and the cross-source check has no independence.

### 3.7 `tests/fixtures/known_answers/known_points_2026-08-08.json`

```json
{
  "recorded_at": "2026-08-08",
  "crs_note": "lon/lat are EPSG:4326. x2180/y2180 are the pyproj Transformer output for EPSG:2180 in PROJ axis order (easting, northing) — see §4.3.",
  "points": {
    "budy_grabskie_village_centroid": {
      "note": "⟨RECORD⟩ — public locality centroid from PRG PRNG (localities layer). NOT an address.",
      "lon": "⟨RECORD⟩", "lat": "⟨RECORD⟩",
      "expected_teryt_gmina": "⟨RECORD⟩",
      "expected_gmina_name": "Skierniewice",
      "expected_parent_teryt": "⟨RECORD⟩",
      "expected_powiat_name": "skierniewicki"
    },
    "skierniewice_city_centre": {
      "note": "⟨RECORD⟩ — city centroid, PRG city polygon centroid.",
      "lon": "⟨RECORD⟩", "lat": "⟨RECORD⟩",
      "expected_teryt_gmina": "⟨RECORD⟩",
      "expected_gmina_name": "Skierniewice",
      "expected_parent_teryt": "⟨RECORD⟩"
    },
    "elblag_city_centre": {
      "note": "⟨RECORD⟩ — city centroid, PRG city polygon centroid.",
      "lon": "⟨RECORD⟩", "lat": "⟨RECORD⟩",
      "expected_teryt_gmina": "⟨RECORD⟩",
      "expected_parent_teryt": "⟨RECORD⟩"
    },
    "boundary_400m": {
      "note": "Constructed: ST_LineInterpolatePoint at 0.5 on the named segment, offset 400 m inward, EPSG:2180.",
      "boundary_between": ["⟨RECORD⟩", "⟨RECORD⟩"],
      "lon": "⟨RECORD⟩", "lat": "⟨RECORD⟩",
      "measured_distance_m_2180": 400.0,
      "expected_boundary_risk": true
    },
    "boundary_600m": {
      "note": "Same segment, offset 600 m inward.",
      "boundary_between": ["⟨RECORD⟩", "⟨RECORD⟩"],
      "lon": "⟨RECORD⟩", "lat": "⟨RECORD⟩",
      "measured_distance_m_2180": 600.0,
      "expected_boundary_risk": false
    },
    "dist_pair_short": { "…": "see §4" },
    "dist_pair_ring":  { "…": "see §4" }
  }
}
```

Privacy: this file carries locality and city **centroids** only. No street, no
house number, no anchor address (FR-23, D36). R1.8 scans this file along with the
rest of the tree.

### 3.8 Small fixtures completing item 1

| Path | Literal content |
|---|---|
| `tests/fixtures/config/sources_bad_kind_2026-08-08.yml` | `sources:\n  - name: bad_one\n    kind: scraper` |
| `tests/fixtures/config/anchors_real_looking_2026-08-08.yml` | `anchors:\n  A:\n    label: PUBLIC_LANDMARK_CONTROL\n    lat: 53.0\n    lon: 19.0` — inside the Poland bbox, so it proves R1.5's bbox limb can fail. Same round graticule crossing as §3.4's synthetic anchor; a landmark name would still be a real place, and a graticule crossing is not |
| `tests/fixtures/prg/shuffled_seed.txt` | `20260808` — single line, no newline sensitivity |

### 3.9 Values this document cannot determine, and what is needed

Stated explicitly per `CLAUDE.md` rule 2 rather than guessed.

| Value | Why it cannot be fixed here | What is needed |
|---|---|---|
| TERYT of rural gmina Skierniewice | **The repository gave two different codes for this one gmina**, one in the API contract and one in the pass-1 specification. I invented the first. Both are now deleted, and I do not pick a replacement: picking one is what produced the error | The GUS TERYT **TERC** download (`TERC_Urzedowy_<date>.csv`). Resolve with the filter in §3.10. Determinable from the repository without guessing: `WOJ=10` (łódzkie), `POW=15` (skierniewicki), `RODZ=2` (gmina wiejska). The `GMI` pair is unknown |
| TERYT of the city of Skierniewice | Cited once and never corroborated, so the citation is not evidence. The city is a *miasto na prawach powiatu*, so `GMI=01`, `RODZ=1` and `WOJ=10` are structural — the `POW` pair is the unknown | Same TERC download |
| TERYT of m. Elbląg, powiat elbląski | Not stated anywhere in the repository | Same TERC download |
| Budy Grabskie / Skierniewice / Elbląg coordinates | Real-world locations; any lon/lat written here would be fabricated | PRG PRNG localities layer (or the PRG city polygon centroid), recorded with its own provenance note |
| PRG feature counts, and the two `ring_gminas` lists | Depend on the clip, which depends on the anchors in the gitignored `config/anchors.yml` | Run the clip script locally; the manifest is the oracle thereafter |
| The 400 m / 600 m boundary points | Depend on the recorded PRG geometry | Constructed by the recording script from the clip; see §3.7 |
| EPSG:2180 coordinates of the distance pair | Require the PROJ transformation grids | `pyproj` ≥ 3.4 with bundled PROJ ≥ 9; see §4 |

### 3.10 The TERC resolution step, written once

Run **before** R3.2 is typed. It replaces every `⟨RECORD⟩` TERYT above.

```bash
# gmina wiejska Skierniewice
awk -F';' 'NR==1 || ($5=="Skierniewice")' tests/fixtures/teryt/terc_2026-08-08.csv
```

Read off the row where `NAZWA_DOD` is `gmina wiejska` → `teryt = WOJ||POW||GMI||RODZ`.
Read off the row where `NAZWA_DOD` is `gmina miejska` and `POW` differs → the city.
Write both into `tests/fixtures/prg/manifest.json` under `teryt`, and write
**neither into a test file as a literal** — tests read them from the manifest, so a
re-record propagates automatically.

One test guards the drift that produced the contradiction:

#### R3.25 `test_repository_documents_cite_the_register_teryt_codes`
- **Input** every tracked `docs/**/*.md` file, read as text, from
  `git ls-files 'docs/**/*.md'`; and the manifest's
  `teryt.gmina_skierniewice_rural` and `teryt.miasto_skierniewice`.
- **Expected** Every 7-digit string within 80 characters of the token
  `Skierniewice` equals one of the two manifest values. The count of mismatches
  equals `0`. The failure message prints the file, the line and the offending code.
- **Marker** `architecture`. **Discharges** none.
- **Why it scans every document, not two.** The contradiction was found in two
  files, but the failure mode is copying a code into a third. A test naming two
  paths goes stale the moment somebody writes a fourth document. The scan is
  cheap, so scan everything.
- **What this test does not do.** It does not choose a code. It reports that a
  document disagrees with the register and stops there. The register decides.
- **Ordering.** This test is red until the TERC download fills the manifest. That
  is correct: an empty manifest value must not let the guard pass.

---

## 4. The known-answer spatial data (V31)

### 4.1 Construction, not selection

Both pairs are **constructed by geodesic forward computation from the synthetic
anchor**, so their separation is exact by construction rather than measured after
the fact. This is what makes them "two points with an independently known
separation": the independent quantity is the WGS84 geodesic distance that
`Geod.fwd` was asked to produce, and the reference check is `Geod.inv` — neither
touching PostGIS nor our code.

```python
GEOD = Geod(ellps="WGS84")
P0 = (19.0, 53.0)                                    # lon, lat — the synthetic anchor

# short pair — good-neighbour scale
lon1, lat1, _ = GEOD.fwd(19.0, 53.0, az=90.0,  dist=600.0)

# ring pair — 25 km-ring scale
lon2, lat2, _ = GEOD.fwd(19.0, 53.0, az=45.0,  dist=20000.0)
```

### 4.2 The two pairs

| Pair | From | To | Azimuth | **Known separation** | Tolerance | Rule |
|---|---|---|---|---|---|---|
| `dist_pair_short` | `(19.0, 53.0)` | `Geod.fwd(19.0, 53.0, 90.0, 600.0)` | 90.0° | **600.000 m** exactly | **≤ 1.0 m** | V31 good-neighbour scale (< 1 km) |
| `dist_pair_ring` | `(19.0, 53.0)` | `Geod.fwd(19.0, 53.0, 45.0, 20000.0)` | 45.0° | **20 000.000 m** exactly | **≤ 0.1 % = 20.0 m** | V31 ring scale |

Why the scale-dependent tolerance is not slack: EPSG:2180 is a transverse Mercator
with `k₀ = 0.9993` on the 19°E central meridian. At `lon ≈ 19.0` the point scale
factor is ≈ 0.99930, so a 20 km line measured planar in EPSG:2180 sits roughly
**14 m** below its geodesic length — inside the 20 m budget and far outside a
flat 1 m budget. The same distortion over 600 m is ≈ **0.42 m**, inside the 1 m
budget. B2 in the gap analysis is exactly this arithmetic.

### 4.3 Fixture fields, and the axis-order trap

The fixture stores each point in **both** CRSs:

```json
"dist_pair_short": {
  "p1": {"lon": 19.0, "lat": 53.0, "x2180": "⟨RECORD⟩", "y2180": "⟨RECORD⟩"},
  "p2": {"lon": "⟨RECORD⟩", "lat": "⟨RECORD⟩", "x2180": "⟨RECORD⟩", "y2180": "⟨RECORD⟩"},
  "construction": {"azimuth_deg": 90.0, "distance_m": 600.0, "ellps": "WGS84"},
  "expected_distance_m": 600.0,
  "tolerance_m": 1.0
}
```

`x2180`/`y2180` cannot be computed without PROJ and are `⟨RECORD⟩`. The recording
script must state which axis convention it wrote, because **EPSG:2180's authority
axis order is (northing, easting) while PROJ's `always_xy=True` returns
(easting, northing)** — a swap is a 400 km error that still looks like a
coordinate. Record with:

```python
Transformer.from_crs("EPSG:4326", "EPSG:2180", always_xy=True)
```

and have the recording script assert the sanity band `171000 ≤ x2180 ≤ 862000` and
`133000 ≤ y2180 ≤ 775000` before writing. If PostGIS `ST_Transform(geom, 2180)`
disagrees with the recorded pair by more than 1 mm, that is a real finding about
the PROJ build, not a test to relax.

### 4.4 The degrees control (R3.16), with its expected magnitude

The naive computation under test:

```python
naive = 111320.0 * math.hypot(lon2 - lon1, lat2 - lat1)   # degrees treated as planar
```

| Pair | Correct | Naive result | Error | Assertion |
|---|---|---|---|---|
| `dist_pair_ring` | 20 000 m | **≈ 27 500 m** | ≈ 7 500 m | `abs(naive - 20000.0) > 1000.0` |
| `dist_pair_short` | 600 m | **≈ 1 000 m** | ≈ 400 m | `abs(naive - 600.0) > 1.0` |

The ring pair is the load-bearing one: the error there is ~37 %, so no plausible
tolerance hides it. The short pair is included because it shows the naive method
also fails at the scale where the tolerance is tightest — but note it fails by
about 400 m, not by 1000 m, so R3.16's `> 1000.0` threshold applies to the ring
pair **only**. Pass 1 did not distinguish them; type both limbs.

The magnitudes above are arithmetic from `cos(53°) ≈ 0.6018` and the 111 320 m
constant, and are stated as "≈, assert `>`" rather than as equalities — the exact
naive value depends on `Geod.fwd`'s meridian arc, which is not 111 320 m/degree.
Assert the inequality; record the observed value in the test's failure message so a
future PROJ change is visible rather than silent.

---

## 5. Per-test detail

Exception classes are `psycopg` (v3) classes throughout. Every constraint test uses
the `conn` fixture and is rolled back.

### 5.1 Item 1 — repo, config, Docker, migrations

| Test | Exact input | Exact expected | Exception | Markers |
|---|---|---|---|---|
| R1.1 | `import dzialki` | `dzialki.__version__ == "0.0.0"` | — | `unit` |
| R1.2 | `pkgutil.iter_modules(dzialki.__path__)` | set equals `{"config","db","ingest","normalize","geo","metrics","valuation","app","ops"}` | — | `unit` |
| R1.3 | `git ls-files config/` | `sorted(out) == ["config/anchors.example.yml", "config/sources.yml"]` | — | `architecture` |
| R1.4a | `git check-ignore -q config/anchors.yml` | returncode `0` | — | `architecture` |
| R1.4b | write `config/anchors.yml`, run `git status --porcelain` | zero lines containing `anchors.yml`; file removed in teardown even on failure | — | `architecture` |
| R1.5 | `load_anchors("config/anchors.example.yml")` | `sorted(keys) == ["A","B"]`; `A.label == "PLACEHOLDER_ANCHOR_A"`; `A.lat == 0.0`; `A.lon == 0.0`; for each anchor `re.search(r"\d", label) is None` and `not (14.0 <= lon <= 24.2 and 49.0 <= lat <= 55.0)` | — | `unit` |
| R1.5-control | `load_anchors(fixtures/config/anchors_real_looking_2026-08-08.yml)` | the bbox predicate is `True` — i.e. R1.5's bbox limb is capable of failing | — | `unit` |
| R1.6 | `ast.parse(Path("src/dzialki/config/anchors.py").read_text())` | count of `ast.Constant` floats `f` with `14.0<=f<=24.2` or `49.0<=f<=55.0` equals `0`; count of `ast.Constant` strings matching `r"\d+\s*[A-Za-zĄ-ż]"` equals `0` | — | `architecture` |
| R1.7 | `load_anchors(tmp_path/"absent.yml")` | raises; `"config/anchors.example.yml" in str(exc)`; `not issubclass(AnchorConfigMissing, OSError)`; no warning recorded via `recwarn` | `dzialki.config.AnchorConfigMissing` | `unit` |
| R1.8 | for each `street`/`house_number` value read from the gitignored `config/anchors.yml`: `git grep -F -- <v>` and `git log -p --all -S <v> --format=%H` | grep returncode `1` (no match); `git log` stdout is empty | — | `architecture`, `needs_git_history`, `needs_local_secrets` |
| R1.9a | `DZIALKI_DATABASE_URL` deleted via `monkeypatch.delenv`, then `Settings()` | raises | `dzialki.config.ConfigError` | `unit` |
| R1.9b | `DZIALKI_DATABASE_URL="postgresql://u:p@h:5432/db"` | `Settings().database_url == "postgresql://u:p@h:5432/db"` | — | `unit` |
| R1.10a | `config/sources.yml`, entry `minimal_registry` | `enabled is False`; `robots_ok is False`; `rate_limit_rpm == 5` | — | `unit` |
| R1.10b | `fixtures/config/sources_bad_kind_2026-08-08.yml` | raises; `"scraper" in str(exc)` and `"kind" in str(exc)` | `dzialki.config.ConfigError` | `unit` |
| R1.11 | `SELECT current_setting('server_version_num')::int`, `postgis_lib_version()`, `SELECT extname FROM pg_extension` | `160000 <= v < 170000`; `lib.startswith("3.")`; `"postgis" in extnames` | — | `integration`, `needs_db` |
| R1.12 | `alembic upgrade head` on a fresh database | `SELECT count(*) FROM alembic_version == 1`; `version_num == ScriptDirectory.get_heads()[0]`; `len(get_heads()) == 1` | — | `integration`, `needs_db` |
| R1.13 | `alembic upgrade head` twice | `version_num` unchanged; `schema_digest()` byte-identical | — | `integration`, `needs_db` |
| R1.14 | `alembic downgrade base` | `{t for t in information_schema.tables where table_schema='public'} - {"spatial_ref_sys","geography_columns","geometry_columns"} == set()` | — | `integration`, `needs_db` |
| R1.15 | `up → down base → up` | `digest_before == digest_after` | — | `integration`, `needs_db`, `slow` |

R1.14 note: the exceptions file is `db/migrations/irreversible.txt`, one revision
id per line. An empty file is the expected committed state; the test reads it and
excludes listed revisions. "Explicitly documented as not reversible" (`15` §13)
means a line in that file, not a code comment.

### 5.2 Item 2 — enums

| Test | Exact query | Exact expected list |
|---|---|---|
| R2.1 | `enumlabel … typname='price_type' ORDER BY enumsortorder` | `["offering","sales"]` |
| R2.1b **(D65, D68)** | `… typname='price_kind'` | `["asking","auction_start","tender","transaction"]`, and `"offering" not in labels`, `"sales" not in labels` |
| R2.2 | `… typname='buildability_source'` | `["plan_ogolny","mpzp","registry"]`, and `"advert" not in labels` |
| R2.3a | `… typname='asset_class'` | `["land_building","land_recreational","land_agricultural","land_forest_other","house","flat"]` |
| R2.3b | `… typname='buildability'` | `["buildable","conditional","agricultural","unknown"]` |
| R2.3c | `… typname='unit_level'` | `["voivodeship","powiat","gmina","obreb"]` |
| R2.3d **(D69)** | `… typname='range_kind'` | `["iqr","min_max","unavailable"]` |
| R2.3e **(D56, D66)** | `… typname='series_kind'` | `["stock","flow"]` |

### 5.3 Item 2 — the canonical valid rows

Every constraint test below mutates exactly one field of one of these. Define them
once in `tests/integration/rows.py`; a test that builds its own row inline makes
the mutated field invisible.

```python
SOURCE = dict(name="test_source", kind="registry")            # id captured after insert

ADMIN_UNIT = dict(teryt="9901011", level="gmina", name="Testowo",
                  parent_teryt=None, wkt=SYNTH_9901011_WKT,
                  as_of="2026-08-08", source_id=SOURCE_ID)

LISTING = dict(source_id=SOURCE_ID, external_id="EXT-1",
               url="https://example.invalid/1",
               first_seen_at="2026-08-01T00:00:00Z", last_seen_at="2026-08-08T00:00:00Z",
               is_active=True,
               price_pln=Decimal("300000.00"), area_m2=Decimal("2500.00"),
               price_type="offering", price_kind="asking",
               area_source="structured", asset_class="land_building",
               teryt_gmina="9901011")

TRANSACTION = dict(source_id=SOURCE_ID, teryt_unit="9901011", unit_level="gmina",
                   transacted_at=date(2024, 6, 1), as_of=date(2024, 6, 1),
                   price_pln=Decimal("250000.00"), area_m2=Decimal("2500.00"),
                   price_type="sales", price_kind="transaction")   # D68

NOTICE = dict(source_id=SOURCE_ID, external_id="NOT-1",            # D91
              url="https://example.invalid/notice/1",
              notice_date=date(2026, 7, 15),
              auction_at=None,                                     # a plain sale notice
              price_pln=None, area_m2=None,                        # a notice may state neither
              price_type="offering", price_kind="auction_start",
              teryt_gmina="9901011", as_of=date(2026, 8, 8))

METRIC = dict(teryt_unit="9901011", unit_level="gmina", month=date(2026, 7, 1),
              asset_class="land_building", buildability="unknown",
              price_type="offering", price_kind="asking",
              series_kind="stock", area_band="1000-3000",
              flow_window_days=None, generation=1,
              n=10, median_ppm2=Decimal("120.00"),
              p25_ppm2=Decimal("100.00"), p75_ppm2=Decimal("140.00"),
              min_ppm2=Decimal("80.00"),  max_ppm2=Decimal("200.00"),
              range_kind="iqr", as_of=date(2026, 8, 8), source_ids=[SOURCE_ID])
```

`ADMIN_UNIT.parent_teryt=None` is deliberate: item 2's constraint tests must not
depend on a loaded hierarchy. The hierarchy is item 3's subject.

### 5.4 Item 2 — `price_type` and `price_kind` (V1)

| Test | Mutation of the canonical row | Exact expected | Exception / diagnostic |
|---|---|---|---|
| R2.4 | none — introspection | exactly one `pg_constraint` row on `listing` with `contype='c'` whose `pg_get_constraintdef` contains `price_type = 'offering'::price_type`; `pg_attribute.attnotnull` for `listing.price_type` is `True`; `listing.price_kind` has type `price_kind`, `attnotnull True`, and its default renders as `'asking'::price_kind` | — |
| R2.5 | none — introspection | same `price_type` shape on `transaction` with `'sales'::price_type`, `attnotnull True`. **D68 limb:** a second `contype='c'` row whose definition contains `price_kind = 'transaction'::price_kind`; `attnotnull True` on `transaction.price_kind` | — |
| R2.5b **(D91)** | none — introspection on `notice` | a `contype='c'` row containing `price_type = 'offering'::price_type`; a second containing both `'auction_start'` and `'tender'`; `attnotnull True` on `price_type`, `price_kind` and `notice_date`; `attnotnull False` on `auction_at`, `price_pln` and `area_m2` | — |
| R2.5c **(D91)** | insert `NOTICE` verbatim | **succeeds**; `SELECT price_per_m2` returns `None`, because the generated expression yields NULL when `price_pln` is NULL | — |
| R2.5d **(D91)** | `NOTICE` with `price_kind='asking'` | rejected — a notice is never an asking price | `CheckViolation`, `diag.constraint_name == "notice_price_kind_check"` |
| R2.5e **(D91)** | `NOTICE` with `notice_date=None` | rejected | `NotNullViolation`, `diag.column_name == "notice_date"` |
| R2.6 | none — catalogue scan | for every `public` table with a column matching `price%`, `%_ppm2`, `median%`, `p25%`, `p75%`: **(a)** it has `price_type` of type `price_type`; **(b)** it has `price_kind` of type `price_kind`. Both set differences `== set()`, both failure messages list the offending tables. **No exemption list.** D68 gave `price_kind` a `transaction` label so the sales table satisfies limb (b) too, which is what removes the need for one | — |
| R2.7 | `price_type=None` | rejected | `NotNullViolation`, `exc.diag.column_name == "price_type"` |
| R2.8 | `price_type='sales'` | rejected | `CheckViolation`, `exc.diag.constraint_name == "listing_price_type_check"` |
| R2.9 | `price_type='asking'` | rejected | `InvalidTextRepresentation` (SQLSTATE `22P02`); `"asking" in str(exc)` and `"price_type" in str(exc)` |
| R2.9b | `price_kind='sprzedaz'` | rejected | `InvalidTextRepresentation`; `"sprzedaz" in str(exc)` |
| R2.9c | `price_kind=None` | rejected | `NotNullViolation`, `diag.column_name == "price_kind"` |
| R2.9d | omit `price_kind` entirely | insert **succeeds**; `SELECT price_kind` returns `"asking"` — the fail-safe default | — |
| R2.9e **(D115)** | `listing.price_kind='transaction'` | rejected | `CheckViolation`, `diag.constraint_name == "listing_price_kind_check"` |
| R2.10a | `transaction.price_type='offering'` | rejected | `CheckViolation`, `diag.constraint_name == "transaction_price_type_check"` |
| R2.10b | `transaction.price_type=None` | rejected | `NotNullViolation`, `diag.column_name == "price_type"` |
| R2.10c **(D68)** | `transaction.price_kind='asking'` | rejected | `CheckViolation`, `diag.constraint_name == "transaction_price_kind_check"` |

R2.9 uses `'asking'` deliberately: it is a valid `price_kind` label and an invalid
`price_type` label, so the test also documents that the two axes are distinct.

**R2.9e was a finding, and D115 closed it.** `15` §5 gave `listing.price_kind` a
`NOT NULL` and a default but no CHECK, so a `listing` row could carry
`price_kind = 'transaction'` — a portal advert recorded as a completed sale. D91
had closed the same hole on `notice`; `listing` was missed.

`15` §5 now carries `CHECK (price_kind = 'asking')`, matching how the same table
already pins `price_type`. Every table using the shared enum pins its own subset:
`listing` to `asking`, `notice` to `auction_start` and `tender`, `transaction` to
`transaction`. R2.9e and R2.10c are the negative pair, one per table, and both are
green once the migration lands.

### 5.5 Item 2 — `metric_unit_month`

| Test | Input | Expected | Exception |
|---|---|---|---|
| R2.11 | read PK columns from `pg_index`/`pg_attribute` in key order | `["teryt_unit","month","asset_class","buildability","price_type","price_kind","series_kind","area_band","generation"]` — **exact list, D66**. Separately assert `"unit_level" not in pk_columns` | — |
| R2.12 | insert `METRIC` with `median_ppm2=200.00`; insert a copy with `price_type='sales'`, `median_ppm2=100.00` | `count(*) == 2`; offering row `median_ppm2 == Decimal("200.00")`; sales row `== Decimal("100.00")`; `SELECT count(*) … WHERE median_ppm2 = 150.00` equals `0` | — |
| R2.12b **(D65)** | insert the offering row again with `price_kind='auction_start'`, `median_ppm2=60.00` | `count(*) == 3`; `SELECT count(*) WHERE median_ppm2 = 130.00` equals `0` — kinds do not blend either (V46's storage limb) | — |
| R2.12c **(D66)** | insert the offering row again with `series_kind='flow'`, `flow_window_days=90`, `median_ppm2=90.00` | `count(*) == 4` — stock and flow are separate rows, not one row overwritten | — |
| R2.12d **(D66)** | insert the offering row again with `area_band='3000-10000'`, `median_ppm2=70.00` | `count(*) == 5` — bands do not collide | — |
| R2.13 | re-insert the R2.12 offering row verbatim | rejected | `UniqueViolation`, `diag.constraint_name == "metric_unit_month_pkey"` |
| R2.18a-1 | `min_ppm2=200.00` (above `p25=100.00`) | rejected | `CheckViolation`, `diag.constraint_name == "range_bounds_ordered"` |
| R2.18a-2 | `p75_ppm2=90.00` (below `median=120.00`) | rejected | `CheckViolation`, `range_bounds_ordered` |
| R2.18a-3 | all five equal to `Decimal("120.00")`, `n=1`, `range_kind='min_max'` | **succeeds** — the degenerate n=1 row rule 7 requires | — |
| R2.18c-1 **(D69)** | `range_kind='unavailable'`, `n=40`, `median_ppm2=120.00`, all four spread columns `None` | **succeeds** — the GUS row | — |
| R2.18c-2 **(D69)** | as above but `p25_ppm2=100.00` | rejected — a half-filled spread is unwritable | `CheckViolation`, `spread_present_unless_unavailable` |
| R2.18c-3 **(D69)** | `range_kind='iqr'`, exactly one of `p25_ppm2, p75_ppm2, min_ppm2, max_ppm2` set to `None`, four cases | each rejected | `CheckViolation`, `spread_present_unless_unavailable` |
| R2.18c-4 **(D69)** | `range_kind='unavailable'`, `median_ppm2=None` | rejected — no central value and no spread carries nothing | `NotNullViolation`, `diag.column_name == "median_ppm2"` |
| R2.18c-5 **(D69)** | `range_kind='unavailable'`, `n=1`, spread columns `None`, `median_ppm2=120.00` | **succeeds** — no CHECK couples `unavailable` to a sample size | — |
| R2.18d-1 **(D66)** | `series_kind='flow'`, `flow_window_days=None` | rejected | `CheckViolation`, `flow_states_its_window` |
| R2.18d-2 **(D66)** | `series_kind='stock'`, `flow_window_days=90` | rejected | `CheckViolation`, `flow_states_its_window` |
| R2.18d-3 **(D107)** | `series_kind='flow'`, `flow_window_days=90` | **succeeds** — 90 days is D107's window | — |
| R2.19 | two inserts, one nulling `n` and one nulling `median_ppm2` | each rejected | `NotNullViolation`, `diag.column_name` equal to that column, asserted per case. The four spread columns are no longer `NOT NULL` — R2.18c covers them, because their rule is conditional |
| R2.20a | `as_of=None` | rejected | `NotNullViolation`, `diag.column_name == "as_of"` |
| R2.20b | `source_ids=[]` | rejected | `CheckViolation`, `diag.constraint_name == "metric_unit_month_source_ids_check"` |
| R2.20c | `source_ids=None` | rejected | `NotNullViolation`, `diag.column_name == "source_ids"` |

`R2.20b` note: `array_length('{}'::int[], 1)` is `NULL`, so `NULL > 0` is `NULL`
and a plain `CHECK` would **pass**. The migration must therefore write
`CHECK (COALESCE(array_length(source_ids,1), 0) > 0)`. Write R2.20b first; it is
red against the schema as literally printed in `15` §9, and that is the point.

#### R2.18b `test_range_kind_threshold_is_read_from_configuration` (D67)

- **Layer** `unit`. No database.
- **Input** `dzialki.config.metrics.load()` over a temporary config file, plus
  `dzialki.metrics.ranges.range_kind_for(n)`.
- **Expected** with `range_kind_min_n: 5` → `range_kind_for(1) == "min_max"`,
  `range_kind_for(4) == "min_max"`, `range_kind_for(5) == "iqr"`,
  `range_kind_for(1000) == "iqr"`. With `range_kind_min_n: 8` →
  `range_kind_for(5) == "min_max"`. The second case is the one that proves the
  threshold is not frozen: an implementation with `5` hardcoded passes the first
  four assertions and fails the fifth.
- **Companion** an `architecture` test: `ast` over `src/dzialki/metrics/` finds zero
  `ast.Constant` integers equal to `5` in any comparison against a name containing
  `n`. And a scan of `db/migrations/` for the string `range_kind_matches_n`,
  asserting `0` occurrences — D67 removed it and a re-introduction must fail.
- **Third case, D69** `range_kind_for(n, spread_available=False)` returns
  `"unavailable"` for every `n`, and the threshold never applies. GUS publishes a
  central value with no spread. The threshold decides between IQR and min–max; it
  cannot decide between a spread and no spread, because that is a property of the
  source, not of the sample size.
- **Configuration file** `config/metrics.yml`, committed, holding
  `range_kind_min_n: 5`. The value stays 5 until O11 ratifies one, and it changes
  by editing a file rather than by writing a migration. That is the whole of D67.

### 5.6 Item 2 — the other schema rules

| Test | Input | Expected | Exception |
|---|---|---|---|
| R2.16a | `price_pln=0` | rejected | `CheckViolation`, `listing_price_pln_check` |
| R2.16b | `price_pln=-1` | rejected | `CheckViolation`, `listing_price_pln_check` |
| R2.16c | `area_m2=0` | rejected | `CheckViolation`, `listing_area_m2_check` |
| R2.16d | `price_pln=0.01`, `area_m2=0.01` | **succeeds**; `price_per_m2 == Decimal("1.00")` | — |
| R2.17a | `price_pln=300000.00`, `area_m2=2500.00` | `price_per_m2 == Decimal("120.00")` | — |
| R2.17b | then `UPDATE listing SET price_pln=360000.00` | `price_per_m2 == Decimal("144.00")` | — |
| R2.17c | `INSERT … (price_per_m2) VALUES (99.00)` | rejected; `"generated" in str(exc)` | `psycopg.errors.GeneratedAlways` (SQLSTATE `428C9`) |
| R2.21a | `transacted_at=2024-06-01`, `as_of=2024-01-01` | rejected | `CheckViolation`, `published_after_transacted` |
| R2.21b | both `2024-06-01` | **succeeds** | — |
| R2.21c | `as_of=2024-06-02` | **succeeds** | — |
| R2.22a | same `(source_id,url,content_hash)` twice | second rejected | `UniqueViolation`, `raw_document_source_id_url_content_hash_key` |
| R2.22b | same `(source_id,url)`, `content_hash` differing | **succeeds**; `count(*) == 2` | — |
| R2.23a | `ST_Multi(ST_GeomFromText(<bowtie>, 4326))` into `admin_unit.geom` | rejected | `CheckViolation`, `diag.constraint_name == "geom_valid"` |
| R2.23b | `<bowtie_repaired>` | **succeeds** | — |
| R2.24a | `SELECT … FROM geometry_columns WHERE srid = 0` | zero rows | — |
| R2.24b | `format_type` of `admin_unit.geom` / `anchor.geom` | `"geometry(MultiPolygon,4326)"` / `"geometry(Point,4326)"` | — |
| R2.24c | `ST_Transform(<valid multipolygon>, 2180)` into `admin_unit.geom` | rejected; `"SRID" in str(exc)` | `psycopg.errors.InvalidParameterValue` (SQLSTATE `22023`) |
| R2.30 | `pg_constraint` rows on `listing` with `contype='f'` | referenced tables equal exactly `{"source","admin_unit"}` — `parcel` and `plot_cluster` are **absent**, and their columns exist as plain `BIGINT`. Test docstring names items 9 and 14 as the migrations that must add them | — |
| R2.31a | column introspection on `admin_unit` | `as_of` is `date` `NOT NULL`; `source_id` is `integer` `NOT NULL` with a foreign key to `source(id)`; `in_ring` is `text[]` `NOT NULL` with default `'{}'::text[]` | — |
| R2.31b | `ADMIN_UNIT` with `as_of=None` | rejected | `NotNullViolation`, `diag.column_name == "as_of"` |
| R2.31c | `ADMIN_UNIT` with `source_id=999999` | rejected | `ForeignKeyViolation`, `diag.constraint_name == "admin_unit_source_id_fkey"` |
| R2.31d | `ADMIN_UNIT` with `in_ring` omitted | **succeeds**; `SELECT in_ring` returns `[]`, not `None` — a unit belongs to no ring until the assignment runs | — |

R2.24c caveat: the class for a PostGIS typmod mismatch is pinned to the image in
§7.1. If the pinned image reports a different SQLSTATE, pin the observed class in
the test and record the observation in the commit message — do **not** widen the
assertion to bare `Exception`.

### 5.7 Item 2 — partitions and grants

| Test | Input | Expected | Exception |
|---|---|---|---|
| R2.25a | `SELECT partstrat FROM pg_partitioned_table WHERE partrelid='listing_snapshot'::regclass` | `"r"` | — |
| R2.25b | partition key column via `pg_get_partkeydef` | `"observed_at"` | — |
| R2.25c | attached partition names | exactly `{f"listing_snapshot_2026_{m:02d}" for m in range(1,13)}` — **12**, deterministic, created by migration `0002` | — |
| R2.25d | `pg_get_expr(relpartbound, oid)` of `listing_snapshot_2026_01` | `"FOR VALUES FROM ('2026-01-01 00:00:00+00') TO ('2026-02-01 00:00:00+00')"` under `TIME ZONE 'UTC'` | — |
| R2.25e | `dzialki.db.partitions.ensure_months(4)` then re-read names | a partition exists whose range contains `date_trunc('month', now())` and each of the next three months | — |
| R2.26 | insert snapshot with `observed_at='2099-01-01'` | rejected; `'no partition of relation "listing_snapshot" found for row' in str(exc)` | `CheckViolation` (SQLSTATE `23514`) |
| R2.27 | as `app_pipeline`, insert one `listing_snapshot` row | succeeds; `count(*) == 1` | — |
| R2.28a | `has_table_privilege(r,'listing_snapshot',p)` for `r ∈ {app_read,app_write,app_pipeline}`, `p ∈ {UPDATE,DELETE}` | all six `False` | — |
| R2.28b | as `app_pipeline`, `UPDATE listing_snapshot SET price_pln = 1` | rejected | `InsufficientPrivilege` (SQLSTATE `42501`) |
| R2.28c | as `app_pipeline`, `DELETE FROM listing_snapshot` | rejected | `InsufficientPrivilege` |
| R2.29a | as `app_read`, `INSERT INTO listing …` | rejected | `InsufficientPrivilege` |
| R2.29b | `has_table_privilege('app_read', t, 'INSERT')` for **every** table in `public` | all `False`; failure message lists offenders | — |

Deliberately fixing 12 partitions for calendar 2026 rather than "current month plus
three" is what makes R2.25d a literal-equality test. `ensure_months` covers the
rolling requirement and is tested separately in R2.25e, where the expectation is
computed rather than literal.

### 5.8 Item 2 — the Δ assertion (V1(c))

| Test | Input | Expected | Exception |
|---|---|---|---|
| R2.14 | `dzialki.ops.assertions.price_type_complete(conn)` on a clean migrated database | `result.passed is True`; `result.observed == {"listing": 0, "transaction": 0, "metric_unit_month": 0}` — exact dict equality, not truthiness | — |
| R2.15 | inside `conn`'s transaction: `ALTER TABLE listing DROP CONSTRAINT listing_price_type_check`; insert `LISTING` with `price_type='sales'`; run the assertion | `result.passed is False`; `result.observed["listing"] == 1`; one row in `assertion_run` with `assertion='price_type_complete'`, `passed = false`, `blocked_publication = true` | — |

R2.15 is the control that gives R2.14 meaning: with the constraint in place, the
condition the assertion looks for is unreachable, so an assertion that returns zero
unconditionally would pass R2.14 forever. The `DROP CONSTRAINT` happens inside the
rolled-back transaction and must never be committed.

### 5.9 Item 3 — parser, loader, spatial

Tests R3.1–R3.4 are `unit` and read the recorded PRG/TERC fixtures from disk. They
must not open a database connection.

| Test | Exact input | Exact expected | Exception | Markers |
|---|---|---|---|---|
| R3.1 | `parse(fixtures/prg/prg_clip_2026-08-08.gpkg)` | per-level counts equal `manifest["counts"]` — three integer equalities, values from the manifest, never literals in the test | — | `unit` |
| R3.2 | the parsed records | record with `teryt == manifest["teryt"]["gmina_skierniewice_rural"]` has `name=="Skierniewice"`, `level=="gmina"`, `parent_teryt==manifest["teryt"]["powiat_skierniewicki"]`; record with `teryt == manifest["teryt"]["miasto_skierniewice"]` has `name=="Skierniewice"`, `level=="gmina"`, and a **different** `parent_teryt` | — | `unit` |
| R3.3 | every parsed gmina `(teryt, name)` vs `terc_2026-08-08.csv` | count of pairs absent from TERC `== 0`; message lists them | — | `unit` |
| R3.4 | multiset of gmina names in the fixture | `names.count("Skierniewice") == 2`; and `max(Counter(names).values()) >= 2` | — | `unit` |
| R3.5 | load fixture, then query | `count(level='gmina') == manifest["counts"]["gmina"]`; `count(NOT ST_IsValid(geom)) == 0`; `count(ST_IsEmpty(geom)) == 0`; `count(ST_SRID(geom) <> 4326) == 0` | — | `integration`, `needs_db` |
| R3.6 | join query | gminas with NULL parent or non-powiat parent `== 0`; powiats with non-voivodeship parent `== 0` | — | `integration`, `needs_db` |
| R3.7 | pairwise, bbox-intersecting gminas | `max(ST_Area(ST_Intersection(a2180, b2180))) < 1.0` m²; message prints the max and the pair | — | `integration`, `needs_db`, `slow` |
| R3.8 | per powiat, on the **synthetic** fixture (§3.3) | `abs(Σ child_area − parent_area) / parent_area < 0.0001` | — | `integration`, `needs_db` |
| R3.8b | same, on the recorded PRG clip | same relation, powiats whose gminas are **wholly** inside the clip only — a clipped powiat cannot satisfy additivity, and asserting it on one would be a test that must be relaxed later | — | `integration`, `needs_db`, `slow` |
| R3.9 | for every gmina: `gmina_for_point(ST_PointOnSurface(geom))` | self-resolution failures `== 0`; message lists failing teryts | — | `integration`, `needs_db` |
| R3.10 | `known_points["budy_grabskie_village_centroid"]` | `.teryt == expected_teryt_gmina` (from the fixture), `.name == "Skierniewice"`, `.parent_teryt == expected_parent_teryt`, resolved powiat name `== "skierniewicki"` | — | `integration`, `needs_db` |
| R3.11 | `known_points["skierniewice_city_centre"]` | `.teryt == expected_teryt_gmina`; `city.teryt != rural.teryt`; `city.name == rural.name == "Skierniewice"`; `city.parent_teryt != rural.parent_teryt` | — | `integration`, `needs_db` |
| R3.11b | the **synthetic** `Testowo` pair (§3.3) | `gmina_for_point` at each interior point returns `9901011` and `9902011` respectively; names equal, teryts differ, parents differ | — | `integration`, `needs_db` |
| R3.12 | `known_points["elblag_city_centre"]` | `.teryt == expected_teryt_gmina`; its `parent_teryt` differs from that of at least one gmina whose parent is `manifest["teryt"]["powiat_elblaski"]` | — | `integration`, `needs_db` |
| R3.13 | `ast` over `src/dzialki/`; regex over SQL string literals | (a) no `dzialki.geo` function has a parameter named `gmina_name`/`name`/`nazwa` reaching an `admin_unit` query; (b) zero matches of `r"admin_unit[\s\S]{0,200}\bname\s*(=|ILIKE|LIKE)"` case-insensitively; (c) failure message names file and line | — | `architecture` |
| R3.14 | `known_points["boundary_400m"]`, `["boundary_600m"]` | `boundary_risk(p400) is True`; `boundary_risk(p600) is False` | — | `integration`, `needs_db` |
| R3.15a | `distance_m(dist_pair_short)` | `abs(d − 600.0) <= 1.0`; reference `Geod(ellps="WGS84").inv()` agrees to `1e-3` m | — | `unit` |
| R3.15b | `distance_m(dist_pair_ring)` | `abs(d − 20000.0) <= 20.0` (0.1 %) | — | `unit` |
| R3.16a | naive degrees formula on `dist_pair_ring` | `abs(naive − 20000.0) > 1000.0` (expected ≈ 7 000) | — | `unit` |
| R3.16b | naive degrees formula on `dist_pair_short` | `abs(naive − 600.0) > 1.0` (expected ≈ 375) | — | `unit` |
| R3.17 | every gmina geometry | `ST_MaxDistance(geom, ST_Transform(ST_Transform(geom,2180),4326)) < 0.000001` degrees; `ST_NPoints` unchanged | — | `integration`, `needs_db`, `slow` |
| R3.18 | load `config/anchors.example.yml` into `anchor` | column set `== {"key","label","geom"}`; `count(*) == 2`; every `label` has `re.search(r"\d", label) is None`; `GeometryType(geom) == "POINT"`; `ST_SRID(geom) == 4326` | — | `integration`, `needs_db` |
| R3.22 | run the loader twice | `count(*)` unchanged; `geometry_digest()` byte-identical | — | `integration`, `needs_db` |
| R3.23 | load features shuffled with `random.Random(int(shuffled_seed.txt))` | `geometry_digest()` equals the file-order digest | — | `integration`, `needs_db` |
| R3.24 | every loaded `admin_unit` row | `count(as_of IS NULL) == 0`; `count(source_id IS NULL) == 0`; every `as_of` equals `manifest["downloaded_at"]`; every `source_id` resolves to the `source` row named `prg` | — | `integration`, `needs_db` |

### 5.10 Item 3 — ring membership, now unblocked (D64)

Both run against the §3.4 synthetic fixture, not against the recorded clip. The
recorded clip's ring counts depend on the gitignored anchors and therefore cannot
be asserted in CI; the synthetic fixture can, exactly.

#### R3.19 `test_ring_membership_is_boundary_within_25km_not_centroid`
- **Layer** `integration`, `needs_db`.
- **Input** load `ring_membership.json` and its anchor `T`; run
  `dzialki.geo.rings.assign(conn, radius_m=25000)`.
- **Expected**
  - `set(teryt for row where 'T' = ANY(in_ring)) == {"9801011","9801021","9801041"}` —
    exact set equality against `manifest["expected"]["in_ring_T"]`
  - `"9801031" not in members`
  - **the discriminator:** `"9801011" in members` while its centroid distance is
    `> 25000` m (asserted from `measured_centroid_m`). A centroid-rule
    implementation fails here and nowhere else.
  - `in_ring` is a `TEXT[]`, and `9801011`'s value equals exactly `["T"]` — not a
    boolean, not a comma-joined string.
- **Exception** none.
- **Discharges** the D64 limb of V6.

#### R3.20 `test_ring_membership_matches_the_manifest_gmina_list`
- **Input** the same load, and separately the recorded clip.
- **Expected**
  - Synthetic limb: `set(members) == set(manifest["expected"]["in_ring_T"])` — set
    equality, three gminas.
  - Recorded limb: `set(ring("A")) == set(manifest["ring_gminas"]["A"])` and
    `set(ring("B")) == set(manifest["ring_gminas"]["B"])` — **exact TERYT lists**,
    for the two rings only.
- **Markers** the synthetic limb `integration`, `needs_db`; the recorded limb adds
  `needs_local_secrets` and skips with the reason
  `"ring membership depends on gitignored anchors"`.
- **Why a list and not a count.** V6 no longer asserts an approximate gmina count.
  A count says a gmina went missing; a list says which one. The failure message
  prints the symmetric difference.

#### R3.21 `test_both_rings_are_non_empty_and_disjoint`
- **Input** the recorded clip with both real anchors loaded.
- **Expected** `len(ring("A")) > 0`, `len(ring("B")) > 0`,
  `set(ring("A")) & set(ring("B")) == set()`. The rings are ~300 km apart, so a
  non-empty intersection means the anchor points were swapped or mis-parsed.
- **Markers** `integration`, `needs_db`, `needs_local_secrets`.

#### R3.19b `test_ring_assignment_is_idempotent`
- **Input** run `assign()` twice.
- **Expected** `in_ring` for `9801011` equals `["T"]` after both runs — **not**
  `["T","T"]`. The `array_append` in `15` §3 appends unconditionally; this test is
  red against the SQL as printed, which is the point of writing it.

### 5.11 Property tests (pass 1 §6.2, §6.3)

| Property | Strategy | Assertion | Markers |
|---|---|---|---|
| Generated-column identity | `price ∈ [1, 10⁹]`, `area ∈ [1, 5·10⁵]`, both as `NUMERIC(12,2)` | `abs(price_per_m2 * area_m2 − price_pln) <= Decimal("0.005") * area_m2` | `property`, `integration`, `needs_db` |
| Scaling | any `(price, area)` with `2·price` exactly representable at 2 dp | `ppm2(2p, a) == 2 * ppm2(p, a)` | same |
| Ratio invariance | `(10p, 10a)` | `ppm2(10p, 10a) == ppm2(p, a)` | same |
| Enum closure | any `text` not in `{"offering","sales"}` | raises `InvalidTextRepresentation` | same |
| Range-bound ordering | five sorted `Decimal`s, `range_kind='iqr'` | insert succeeds iff `min<=p25<=median<=p75<=max`, else `CheckViolation` on `range_bounds_ordered`. `range_kind='unavailable'` is excluded from the strategy: the constraint exempts it, because there are no bounds to order | same |
| Threshold monotonicity (D67) | `k ∈ {3, 5, 8}`, `n ∈ [1, 1000]` | `range_kind_for(n) == "iqr"` iff `n >= k`. Running over three thresholds is what fails an implementation with any single value written into the code | `property`, `unit` |
| Enum closure, `price_kind` | any `text` not in the four labels | raises `InvalidTextRepresentation`. Generalises R2.9b | `property`, `integration`, `needs_db` |
| Distance symmetry | point pairs inside the §3.3 bbox | `distance_m(p,q) == distance_m(q,p)` exactly; `distance_m(p,p) == 0.0` | `property`, `unit` |

Hypothesis profile: `deadline=None` for database-backed properties (container
latency is not a correctness signal), `max_examples=50` in CI, `500` in the nightly
job. Each property runs inside `conn`'s rolled-back transaction — a property test
that leaks rows makes the next test's `count(*)` assertion flaky.

---

## 6. Ordering and forbidden dependencies

### 6.1 Write order, and the ordering constraints that actually matter

Pass 1's numbering is the write order. Four orderings are load-bearing rather than
merely tidy; the rest may be reordered within their group.

| Must come first | Must come second | Why |
|---|---|---|
| R1.1, R1.2 | everything | Until the package imports, no later test can be red for the right reason |
| R1.12 (`upgrade head` works) | every `needs_db` test | The session fixture depends on it; a broken migration would surface as 40 confusing failures instead of one |
| R2.27 (pipeline role **can** insert) | R2.28 (no role can update/delete) | Without the positive control, a revocation test passes against a table that does not exist or a role that cannot connect |
| R2.14 (assertion is green) | R2.15 (assertion can go red) | R2.15 is the mutation control; writing it first hides which of the two is doing the work |
| R3.9 (every gmina self-resolves) | R3.10–R3.12 (known answers) | A known-answer failure after R3.9 is green means the fixture clip is wrong, not the lookup |
| R3.5 (loader inserts) | R3.19 (ring assignment) | Ring assignment reads `admin_unit` |

### 6.2 What each test must **not** depend on

| Test group | Must not depend on |
|---|---|
| All | Any row left behind by another test. Every database test runs in a rolled-back transaction; a test that needs `COMMIT` must create its own database |
| All | Test execution order beyond §6.1. `pytest -p no:randomly` must not be required to pass |
| R1.x config tests | The gitignored `config/anchors.yml` — except R1.8, which skips with a named reason when it is absent |
| R1.3, R1.4 | Full git history (they use `ls-files` and `check-ignore`, both shallow-safe) |
| R2.x | Any PRG or TERC fixture. Item 2's inserts are literals from §5.3 because the values under test are constraint boundaries, not source data |
| R2.x | A hierarchy in `admin_unit`. `ADMIN_UNIT.parent_teryt` is `None` |
| R2.x | The wall clock, except R2.25e which computes its expectation from `now()` and asserts a relation, never a literal month |
| R3.1–R3.4 | Postgres. They are pure-parser tests; opening a connection there would make the parser untestable without a container |
| R3.8, R3.9, R3.11b, R3.19 | The recorded PRG clip. They run on the synthetic fixtures so they stay green when the clip is re-recorded |
| R3.10–R3.12, R3.21 | Anything but the recorded clip. Their whole value is that the data is real |
| R3.x | Gmina **names** as lookup keys. R3.13 forbids it in `src/`; the tests must not do it either. `name` may be asserted, never used to select |
| Property tests | Row counts. They assert relations between outputs, not absolute state |
| Everything | A hardcoded TERYT literal. Codes come from `manifest.json` (real) or from the synthetic fixture's `99`/`98` namespace |

### 6.3 Fixture-scope discipline

`migrated_db` is session-scoped and expensive; `conn` is function-scoped and cheap.
No test may promote itself to session scope to "save time" — a session-scoped test
that writes rows breaks the isolation every other test in §6.2 depends on. The two
exceptions, both of which create and drop their own database, are R1.13/R1.15
(migration idempotence and involution) and R2.27–R2.29 (role connections need real
sessions, not a shared transaction).

---

## 7. CI wiring

### 7.1 Pinned environment

```yaml
# docker-compose.yml
services:
  db:
    image: postgis/postgis:16-3.4      # pin the digest too; R2.23b and R2.24c are image-sensitive
    environment: [POSTGRES_PASSWORD, POSTGRES_DB]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 2s
      retries: 30
```

R1.11 asserts `160000 <= server_version_num < 170000` and
`postgis_lib_version().startswith("3.")`, which is what makes the pin testable
rather than decorative.

### 7.2 Job matrix

| Job | Trigger | Selection | Needs |
|---|---|---|---|
| `fast` | every push, every PR | `pytest -m "unit or architecture" --deselect-marker needs_git_history --deselect-marker needs_local_secrets` | Python only. Target < 30 s |
| `db` | every push, every PR | `pytest -m "integration and not slow"` | Postgres service container. `DZIALKI_TEST_DATABASE_URL` pointing at a database whose name ends `_test` |
| `db-slow` | every push to the default branch; nightly | `pytest -m "integration and slow"` | Same, plus the recorded PRG clip decompressed |
| `history` | nightly, and as a **pre-push hook** | `pytest -m needs_git_history` | `actions/checkout` with `fetch-depth: 0`. **V7(b) cannot run in a shallow clone** — the default `fetch-depth: 1` makes `git log -p --all -S` scan one commit and pass vacuously |
| `local-only` | pre-commit hook on the developer's machine | `pytest -m needs_local_secrets` | The gitignored `config/anchors.yml`. Never runs in CI, by construction |
| `property-deep` | nightly | `pytest -m property` with `HYPOTHESIS_PROFILE=deep` | Postgres |
| `fixtures` | quarterly, manual | `python scripts/fixtures/record_all.py --check` | Network. Re-records PRG/TERC and fails if the committed hash has drifted |

### 7.3 The two skip conditions, and how they must be written

Both must skip with a **named reason**, never pass silently:

```python
@pytest.mark.needs_local_secrets
def test_anchor_addresses_absent_from_working_tree_and_history(...):
    if not (repo_root / "config" / "anchors.yml").exists():
        pytest.skip("config/anchors.yml absent — V7(b) not exercised")
    if git_is_shallow:
        pytest.skip("shallow clone — V7(b) history scan not exercised")
```

A CI job that reports "all tests passed" while V7(b) skipped is exactly the false
green the gap analysis flagged. The `fast` and `db` jobs therefore run with
`-p no:cacheprovider --strict-markers` and the workflow asserts, as a final step,
that the count of skipped tests in `fast` and `db` is **zero**. Skips are legal
only in the `history` and `local-only` jobs.

### 7.4 Coverage of the item-1 preconditions (§4.1 of pass 1)

R1.11–R1.15 are discharged by **V65(B) — environment and migration
reproducibility** (D124). R1.9, R1.10 and the parameter-file tests are discharged
by **V65(A)**. The rule 5 gap is closed: every item-1 test now names the validation
method it discharges.

---

## 8. What remains open after this plan

| Item | Status |
|---|---|
| §4.1 — item 1 has no validation method of its own | **Closed by D124.** V65(A) covers the parameter file and the loaders; V65(B) covers environment and migration reproducibility, which is what R1.11–R1.15 assert |
| §4.2 — `listing` foreign keys to future tables | **Closed.** Plain `BIGINT`, foreign keys later, pinned by R2.30 |
| §4.3 — `price_kind` | **Closed by D65, D66, D68, D115.** Tests R2.1b, R2.4, R2.5, R2.5b–e, R2.6, R2.9b–e, R2.11, R2.12b–d |
| §4.4 — `admin_unit` provenance | **Closed.** Tests R2.31a–d and R3.24 |
| §4.5 — V7(b) in CI | **Closed by D124.** Pre-push hook, never CI (§7.2). Putting the addresses in CI to prove they are absent defeats the point |
| §4.6 — ring membership | **Closed by D64.** Tests R3.19, R3.19b, R3.20 |
| §4.7 — import extent and V6's approximate counts | **Closed.** The extent is the two rings; V6 asserts the exact gmina list from `manifest["ring_gminas"]`, which R3.20 checks. The list is `⟨RECORD⟩` until the clip is recorded — a recording step, not an open question |
| The two Skierniewice TERYT codes | **Open** until the TERC register is downloaded. Both invented codes are deleted, no replacement is guessed, and R3.25 fails when any document disagrees with the register. §3.9, §3.10 |
| `listing.price_kind` has no CHECK | **Closed by D115.** `15` §5 now carries `CHECK (price_kind = 'asking')`. R2.9e is the negative test and goes green with the migration |
| `notice` in migration `0002` | **Recorded assumption**, stated in `../01-foundation-and-schema.md` §2. Overturn it and R2.5b–e move to item 7 |
| The 400 m / 600 m boundary points | **Open** until the PRG clip is recorded |
| EPSG:2180 coordinates of the distance pair | **Open** until the recording script runs; the *separations* (600 m, 20 000 m) are fixed here and are not open |
