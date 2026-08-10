# TDD specification — v0 work items 1, 2, 3

Foundation (repo, Docker, migrations, config) · minimal schema with `price_type`
CHECK constraints · PRG/TERYT import for both anchor rings.

Covers [`18-v0-scope.md`](../18-v0-scope.md) §6 items **1**, **2** and **3**.
Written per `CLAUDE.md` rule 4 (tests before implementation) and rule 5 (a
validation method before implementation), and per
[`20-verification-strategy.md`](../20-verification-strategy.md) §8 entry criteria.

**This document specifies tests only.** No implementation code appears here, by
design: the sequences below are meant to be executable as written, in order, each
one red before the change that makes it green.

**Names (D77, D112).** The repository is `ile-za-dzialke`. The Python package is
`dzialki`, and the source root is `src/dzialki/`. D112 records `dzialki` as a
deliberate exception to D15 (Polish user interface, English code), so a later
reader must not rename it back. Environment variables use the `DZIALKI_` prefix.

---

## 0. How to read this

Every test below states four things:

- **Asserts** — the specific value or relationship pinned. Per `20` §1, "returns
  something" is not an assertion. Every entry names a number, a string, an
  exception class, or an equality between two computed quantities.
- **Green by** — the smallest implementation change that makes it pass.
- **Discharges** — the `04-validation.md` V-number, or an explicit *none*.
- Ordering is the write order. A test that appears later must not be written
  earlier, because its red state depends on the previous test's green.

### 0.1 Entry criteria check (`20` §8)

| Criterion | Item 1 | Item 2 | Item 3 |
|---|---|---|---|
| 1. PRD / work-plan entry | `18` §6 item 1; FR-22, FR-23 | `18` §6 item 2; FR-7, FR-8, FR-64 | `18` §6 item 3; FR-14, FR-54, FR-55 |
| 2. Validation method exists | V7; migrations under V1 (`04` coverage table) — **partial gap, §4.1** | V1, V2 | V6, V30, V31 |
| 3. Verification tier (`20` §2) | **A** — exact; a gitignore rule either matches or does not | **A** — exact; a constraint either exists and rejects, or does not | **A** for TERYT assignment and projections; **B** for PRG content (TERC register is the second source) |
| 4. Silent-failure detectors (`20` §3) | none of F1–F13 touched | F9 (price kinds) — detectors are R2.1b, R2.9b–d, R2.12b | **F4 (wrong gmina)** — detectors are R3.9, R3.10, R3.12, R3.14 |
| 5. Fixtures exist, dated, scrubbed | §3.1 | §3.2 | §3.3 |
| 6. Metamorphic properties listed | §5.1 | §5.2 | §5.3 |

Every entry criterion is now met. D124 gave item 1 the V entry it lacked (**V65**,
§4.1). D65 to D69 and D115 put `price_kind`, `series_kind` and the range rule into
`15-database-schema.md`, which meets criterion 4 for item 2.

### 0.2 Test layout

Per [`16-repository-layout.md`](../16-repository-layout.md) §4:

| Path | Contains |
|---|---|
| `tests/unit/` | Pure functions: config loading, PRG parsing, projection maths. No database, no network. |
| `tests/integration/` | Everything that touches Postgres: migrations, constraints, grants, the loader. |
| `tests/architecture/` | Import-boundary and source-scanning tests (R1.6, R3.13). |
| `tests/fixtures/<source>/` | Recorded, dated, scrubbed (`04` fixtures policy). |

Database tests run against a throwaway database created per test session from
migrations — never against a hand-built schema. A schema built by the test helper
rather than by the migration would let a migration bug pass every constraint test
in item 2.

---

## 1. Work item 1 — repo skeleton, Docker, migrations, config

**1 day.** Verification tier A. Discharges V7 in full; supplies the harness every
later item's tests run inside.

### 1.1 Red–green sequence

#### R1.1 `test_package_version_is_declared`
- **Asserts** `import dzialki; dzialki.__version__ == "0.0.0"` — exact string equality.
- **Green by** `pyproject.toml` with a src-layout package, `src/dzialki/__init__.py`
  declaring `__version__`.
- **Discharges** none. Structural precondition: until the package imports, no
  later test can be red for the right reason.

#### R1.2 `test_v0_package_directories_exist_and_are_importable`
- **Asserts** the set of importable submodules of `dzialki` is **exactly**
  `{config, db, ingest, normalize, geo, metrics, valuation, app, ops}` — equality,
  not containment, so a stray or missing package fails. Each has an `__init__.py`.
- **Green by** Creating those nine packages per `16` §1 (the v0 subset; `extract`,
  `dedup`, `enrich`, `model`, `api`, `digest`, `frontend` arrive with their items).
- **Discharges** none directly. Structural precondition for the architecture tests
  that V21, V25, V29 and V30 rely on — those tests can only assert an absent import
  edge if the modules exist.

#### R1.3 `test_git_tracks_exactly_two_config_files`
- **Asserts** `git ls-files config/` returns **exactly**
  `["config/anchors.example.yml", "config/sources.yml"]` — a sorted list equality.
- **Green by** Committing those two files and nothing else under `config/`.
- **Discharges** **V7(a)**, and it is the strongest form: containment tests pass
  when a third file sneaks in; equality does not.

#### R1.4 `test_anchors_yml_is_gitignored`
- **Asserts** two things: (a) `git check-ignore -q config/anchors.yml` exits `0`;
  (b) after writing a throwaway `config/anchors.yml` into the working tree,
  `git status --porcelain` contains zero lines mentioning `anchors.yml`.
- **Green by** A `.gitignore` line `config/anchors.yml`.
- **Discharges** **V7(a)**. Assertion (b) is what catches a `.gitignore` rule that
  is present but wrong (e.g. `anchors.yml` unanchored, or a later negation).

#### R1.5 `test_anchors_example_contains_only_placeholders`
- **Asserts** loading `config/anchors.example.yml` yields exactly two anchors with
  keys `["A", "B"]`; `anchors["A"].label == "PLACEHOLDER_ANCHOR_A"`;
  `anchors["A"].lat == 0.0` and `.lon == 0.0`; and — the real assertion — for every
  anchor, `re.search(r"\d", anchor.label) is None` and the coordinate pair is
  **not** inside Poland's bounding box (`14.0 ≤ lon ≤ 24.2`, `49.0 ≤ lat ≤ 55.0`).
  A real coordinate committed by accident fails on the bounding box even if
  somebody renames the label.
- **Green by** The example file with sentinel values, plus `dzialki.config.anchors`
  with a typed `Anchor` model.
- **Discharges** **V7(c)**.

#### R1.6 `test_anchor_loader_contains_no_coordinate_literals`
- **Asserts** parsing `src/dzialki/config/anchors.py` with `ast`, the set of numeric
  literals in the module contains **zero** floats inside Poland's bounding box
  (same box as R1.5), and zero string literals matching
  `r"\d+\s*[A-Za-zĄ-ż]"` (a house-number pattern).
- **Green by** A loader that reads coordinates from the YAML path and holds none
  itself.
- **Discharges** **V7** ("no hardcoded coordinate fallback"). This is the test that
  survives refactoring: it forbids the *shape* of the violation, not one instance.

#### R1.7 `test_missing_anchors_config_raises_named_actionable_error`
- **Asserts** `load_anchors(tmp_path / "absent.yml")` raises
  `dzialki.config.AnchorConfigMissing`; `str(exc)` contains the substring
  `"config/anchors.example.yml"`; and the call does **not** return a value, does
  not raise `FileNotFoundError` (a bare OS error is not "actionable"), and does not
  emit a warning-and-default. Asserted by `pytest.raises(AnchorConfigMissing)` plus
  a check that `AnchorConfigMissing` is not a subclass of `OSError`.
- **Green by** The loader raising the named exception with the example path in the
  message.
- **Discharges** **V7(d)**.

#### R1.8 `test_anchor_addresses_absent_from_working_tree_and_history`
- **Asserts** reads the **gitignored** `config/anchors.yml` (never a literal in the
  test file), takes its `street` and `house_number` values, and asserts
  `git grep -F -- <value>` over the working tree returns exit 1 (no match) and
  `git log -p --all -S <value>` returns zero commits, for every value. Zero
  matches, both scans.
- **Green by** Nothing to implement — this is a guard. It goes red only when
  somebody commits an address.
- **Discharges** **V7(b)**.
- **Limitation, recorded** The test `pytest.skip`s with the reason
  `"config/anchors.yml absent — V7(b) not exercised"` when the file is missing, so
  it cannot run in a clean CI checkout. It is a local pre-commit test. Options for
  closing the gap are in §4.5.

#### R1.9 `test_settings_require_explicit_database_url`
- **Asserts** with `DZIALKI_DATABASE_URL` unset, `Settings()` raises `dzialki.config.ConfigError`;
  with it set to `"postgresql://u:p@h:5432/db"`, `Settings().database_url` equals
  that exact string. No default, no `localhost` fallback.
- **Green by** A settings object with a required field.
- **Discharges** none. Prevents a test run silently pointing at the wrong database
  — the failure that would make every item-2 constraint test meaningless.

#### R1.10 `test_sources_config_defaults_are_fail_closed`
- **Asserts** for a `config/sources.yml` entry declaring only `name` and `kind`:
  `source.enabled is False`, `source.robots_ok is False`, `source.rate_limit_rpm == 5`.
  And an entry with `kind: "scraper"` (not in `{portal, registry, api}`) raises
  `ConfigError` naming the offending key.
- **Green by** The sources loader with those defaults, matching the schema defaults
  in `15` §4.
- **Discharges** none directly; it is the configuration half of **V14**'s
  precondition — a source that defaults to enabled with no robots check is the
  failure V14 exists to prevent, and defaults are decided here, not in item 5.

#### R1.11 `test_database_is_postgres_16_with_postgis_3`
- **Asserts** against the container: `current_setting('server_version_num')::int`
  is `>= 160000` and `< 170000`; `postgis_lib_version()` starts with `"3."`;
  `SELECT extname FROM pg_extension` contains `"postgis"`.
- **Green by** `docker-compose.yml` pinning a `postgis/postgis:16-3.x` image with a
  healthcheck, and a migration enabling the extension.
- **Discharges** none of its own. Precondition for **V6** and **V31**, which cannot
  be red-for-the-right-reason without PostGIS.

#### R1.12 `test_migrations_apply_to_empty_database_and_leave_one_head`
- **Asserts** after `upgrade head` on a fresh database:
  `SELECT count(*) FROM alembic_version` equals `1`, and `version_num` equals the
  single head revision id reported by the migration tool's script directory.
  Separately: the script directory reports **exactly one** head (a branched history
  is a merge conflict waiting to be resolved in production).
- **Green by** Migration tooling wired to the settings object, and migration `0001`
  enabling PostGIS.
- **Discharges** none of its own; **V1**'s constraint-existence tests (item 2) all
  run on top of this, and `04`'s coverage table assigns item 1's migrations to V1.

#### R1.13 `test_migrations_are_idempotent`
- **Asserts** running `upgrade head` a second time changes nothing:
  `alembic_version.version_num` is unchanged **and** the schema digest (§5.2) is
  byte-identical to the first run's.
- **Green by** Migrations with no unguarded re-execution side effects.
- **Discharges** none. Property test — see §5.2.

#### R1.14 `test_downgrade_to_base_removes_every_project_table`
- **Asserts** after `downgrade base`, the set of `information_schema.tables` in
  schema `public` minus PostGIS-owned relations (`spatial_ref_sys`,
  `geography_columns`, `geometry_columns`) is **empty**.
- **Green by** Every migration implementing its `downgrade`.
- **Discharges** none. Enforces `15` §13's "every migration is reversible or
  explicitly documented as not". A migration that opts out fails this test until it
  is listed in a committed exceptions file — which is what "explicitly documented"
  should mean mechanically.

#### R1.15 `test_upgrade_downgrade_upgrade_restores_identical_schema`
- **Asserts** `digest(head) == digest(head after down-to-base and up again)`, where
  digest is the normalized `pg_dump --schema-only` hash of §5.2. Exact equality.
- **Green by** Symmetric migrations.
- **Discharges** none. This is the metamorphic relation of §5.2 and the test that
  catches a `downgrade` that drops a column but not its index.

### 1.2 What item 1 does **not** discharge

V1's insert-rejection tests, V2, V6, V30, V31 all need tables that do not exist
yet. Item 1's only complete validation method is **V7**.

---

## 2. Work item 2 — minimal schema with `price_type` CHECK constraints

**1 day.** Verification tier A. Discharges **V1** fully (all three limbs),
**V2(c)**, **V46**'s storage limb, and the database-level limbs of V4, V5, V12,
V25, V31, V32, V57.

Tables in scope for the minimal schema (from `15`): the enum types, `source`,
`admin_unit`, `anchor`, `raw_document`, `listing`, `listing_snapshot`
(partitioned), `notice`, `plot_cluster`, `listing_quarantine`, `transaction`,
`metric_unit_month`, `coverage_snapshot`, `assertion_run`, and the three roles.

**Migration order.** `source` comes before `admin_unit`, because `admin_unit` now
carries `source_id`. `admin_unit` comes before `listing`, `notice`, `transaction`
and `metric_unit_month`, because all four reference it.

**`notice` is in migration `0002`. This is a recorded assumption.** D91 created
the table for KOWR, auction and BIP records, which items 7, 8 and 13 write. The
table carries `price_type` and `price_kind`, and `18` §5 says a price type cannot
be retrofitted cheaply. Creating it now costs one `CREATE TABLE` and keeps `15`
§13's rule true: a `price_type`-bearing table ships with its CHECK in the same
migration. Overturn this and R2.5b moves to item 7.

**Blocked item:** only §4.1 remains. D64 to D69 and D91 close §4.2 to §4.4 and
§4.6.

### 2.1 Red–green sequence — enums

#### R2.1 `test_price_type_enum_has_exactly_two_labels_in_order`
- **Asserts** `SELECT enumlabel FROM pg_enum e JOIN pg_type t ON t.oid=e.enumtypid
  WHERE t.typname='price_type' ORDER BY enumsortorder` equals exactly
  `["offering", "sales"]` — list equality, so a third label added later fails.
- **Green by** `CREATE TYPE price_type AS ENUM ('offering','sales')` in migration `0002`.
- **Discharges** **V1(a)**.

#### R2.1b `test_price_kind_enum_has_exactly_four_labels_in_order`
- **Asserts** the label list of `price_kind` equals exactly
  `["asking","auction_start","tender","transaction"]` — list equality, in
  `enumsortorder`. And `"offering" not in labels`, `"sales" not in labels`, so the
  two axes cannot be confused for one another.
- **Green by** `CREATE TYPE price_kind AS ENUM (...)` of `15` §2.
- **Discharges** **V46**'s storage limb. D65 defines the three offering-side kinds;
  D68 adds `transaction` for the sales side, which is what lets `transaction` pin
  its own kind by CHECK.

#### R2.2 `test_buildability_source_enum_cannot_express_advert`
- **Asserts** the label list equals exactly `["plan_ogolny", "mpzp", "registry"]`,
  and `"advert" not in labels`.
- **Green by** The enum as written in `15` §2.
- **Discharges** **V25** at its structural limb — FR-48's violation is made
  unrepresentable rather than merely tested.

#### R2.3 `test_remaining_enums_match_the_schema_document`
- **Asserts** five exact list equalities: `asset_class` ==
  `["land_building","land_recreational","land_agricultural","land_forest_other","house","flat"]`;
  `buildability` == `["buildable","conditional","agricultural","unknown"]`;
  `unit_level` == `["voivodeship","powiat","gmina","obreb"]`; `range_kind` ==
  `["iqr","min_max","unavailable"]` (D69); `series_kind` == `["stock","flow"]`
  (D56, D66).
- **Green by** The `CREATE TYPE` statements of `15` §2.
- **Discharges** none individually; they are the domains V1, V4 and V18 later
  depend on. A drifted label set would make those tests assert against the wrong
  vocabulary. `range_kind`'s third label is load-bearing: D69 says a source that
  publishes a central value with no spread renders as explicit copy, so the schema
  must be able to store that state rather than raise on it.

### 2.2 Red–green sequence — `price_type` constraints (V1)

#### R2.4 `test_listing_price_type_and_price_kind_are_pinned`
- **Asserts** exactly one row in `pg_constraint` for relation `listing` with
  `contype='c'` whose `pg_get_constraintdef(oid)` contains
  `price_type = 'offering'::price_type`; `pg_attribute.attnotnull` is `true` for
  `listing.price_type`; and — the D115 limb — a **second** CHECK on the same
  relation whose definition contains `price_kind = 'asking'::price_kind`, with
  `listing.price_kind` typed `price_kind`, `NOT NULL`, and its `atthasdef` default
  rendering as `'asking'`.
- **Green by** The `listing` table with both CHECKs, the NOT NULLs and the
  `price_kind` default of `15` §5.
- **Discharges** **V1(a)**, and **V46**'s listing limb.
- **Why the second CHECK.** D91 moved every notice out of `listing`, which left
  `price_kind` there unconstrained. Until D115 a parser bug could write a sales
  price into the offering table, and nothing stopped it. R2.9e is the negative
  companion: it asserts the insert now fails.

#### R2.5 `test_transaction_price_type_and_price_kind_check_constraints_exist`
- **Asserts** the same `price_type` shape for `transaction` with
  `'sales'::price_type`, and `attnotnull` true. And the D68 limb: a second
  `contype='c'` row whose definition contains
  `price_kind = 'transaction'::price_kind`, with `attnotnull` true on
  `transaction.price_kind`.
- **Green by** The `transaction` table of `15` §8.
- **Discharges** **V1(a)**. D68's CHECK is what makes `transaction` exempt from
  R2.6's second limb by its constraint rather than by its name.

#### R2.5b `test_notice_pins_offering_and_restricts_its_price_kind`
- **Asserts** for relation `notice` (D91): a `contype='c'` row containing
  `price_type = 'offering'::price_type`; a second containing
  `price_kind = ANY (ARRAY['auction_start'::price_kind, 'tender'::price_kind])`;
  `attnotnull` true on both columns; and `notice_date` `NOT NULL` while
  `auction_at`, `price_pln` and `area_m2` are nullable.
- **Green by** The `notice` table of `15` §5.
- **Discharges** **V1(a)** for the third price-bearing table. The nullability
  pattern is the reason D91 created a separate table: `listing` requires a non-null
  price and area, and a notice often states neither.

#### R2.6 `test_every_price_bearing_table_declares_price_type_and_price_kind`
- **Asserts** two set differences, both computed to be **empty**, with the
  offending tables named in the failure message. (a) Every table in schema `public`
  having at least one column whose name matches `price%`, `%_ppm2`, `median%`,
  `p25%` or `p75%` also has a column named exactly `price_type` of type
  `price_type`. (b) Every such table also has a column named exactly `price_kind`
  of type `price_kind`.
- **Green by** Nothing new — it passes once R2.4, R2.5 and R2.5b are green and no
  other price-bearing table exists.
- **Discharges** **V1(a)** and **V46**, in the generic form `15` §13 demands:
  *"Adding a `price_type`-bearing table requires its CHECK constraint in the same
  migration; V1's constraint-existence test fails otherwise."* This is that test.
  It is the single most valuable test in item 2, because it constrains migrations
  not yet written.
- **Note** Limb (b) has no exemption list. D68 gave `price_kind` a `transaction`
  label precisely so the sales table can carry the column too, which means every
  price-bearing table can satisfy the same rule. An exemption keyed on a table name
  would go stale the moment a table is renamed.

#### R2.7 `test_listing_price_type_null_is_rejected`
- **Asserts** inserting an otherwise-valid `listing` row with an explicit
  `price_type = NULL` raises `psycopg.errors.NotNullViolation`, and
  `exc.diag.column_name == "price_type"`.
- **Green by** Already green from R2.4's NOT NULL — write it anyway; it is V1(b)'s
  named requirement and it goes red if a later migration relaxes the column.
- **Discharges** **V1(b)**.

#### R2.8 `test_listing_price_type_sales_is_rejected`
- **Asserts** inserting a `listing` with `price_type = 'sales'` raises
  `psycopg.errors.CheckViolation` with
  `exc.diag.constraint_name == "listing_price_type_check"`. Pinning the constraint
  name matters: it proves the CHECK rejected the row, not an unrelated constraint.
- **Green by** Already green from R2.4.
- **Discharges** **V1(b)**.

#### R2.9 `test_listing_price_type_out_of_domain_label_is_rejected`
- **Asserts** inserting `price_type = 'asking'` raises
  `psycopg.errors.InvalidTextRepresentation` — the enum, not the CHECK, is what
  rejects it, and the test asserts that class specifically. `'asking'` is chosen
  deliberately: it is a valid `price_kind` label and an invalid `price_type` label,
  so the test also documents that the two axes are distinct (D65).
- **Green by** Already green from R2.1.
- **Discharges** **V1(b)**.

#### R2.9b `test_listing_price_kind_domain_and_default`
- **Asserts** three cases. (a) `price_kind = 'sprzedaz'` raises
  `InvalidTextRepresentation`. (b) `price_kind = NULL` raises `NotNullViolation`
  with `exc.diag.column_name == "price_kind"`. (c) omitting `price_kind` entirely
  succeeds and `SELECT price_kind` returns `"asking"` — the fail-safe default.
- **Green by** Already green from R2.4.
- **Discharges** **V46**'s storage limb. Case (c) is the one that matters: a
  listing whose kind nobody set is an asking price, which is what a portal advert
  is.

#### R2.10 `test_transaction_price_type_offering_and_null_are_rejected`
- **Asserts** `'offering'` raises `CheckViolation` with constraint name
  `transaction_price_type_check`; `NULL` raises `NotNullViolation` on column
  `price_type`.
- **Green by** Already green from R2.5.
- **Discharges** **V1(b)**.

#### R2.11 `test_metric_unit_month_primary_key_separates_every_axis`
- **Asserts** the primary-key column list of `metric_unit_month`, read from
  `pg_index`/`pg_attribute` in key order, equals exactly
  `["teryt_unit","month","asset_class","buildability","price_type","price_kind",
  "series_kind","area_band","generation"]`. Separately, `"unit_level" not in
  pk_columns` — it is carried, not keyed.
- **Green by** The `metric_unit_month` table of `15` §9.
- **Discharges** **V2(c)** and FR-8's structural limb. D66 added the three middle
  columns: without them a stock row and a flow row, or two area bands, collide on
  insert and one silently overwrites the other.

#### R2.12 `test_metric_unit_month_keeps_both_price_types_as_separate_rows`
- **Asserts** inserting two rows identical in every key column except
  `price_type` (`'offering'` with `median_ppm2 = 200.00`, `'sales'` with
  `median_ppm2 = 100.00`) leaves `SELECT count(*)` equal to `2`, and
  `SELECT median_ppm2 ... WHERE price_type='offering'` equals `Decimal("200.00")`
  while the `'sales'` row equals `Decimal("100.00")`. **No row anywhere equals
  `150.00`** — asserted as `SELECT count(*) FROM metric_unit_month WHERE
  median_ppm2 = 150.00` equals `0`.
- **Green by** Already green from R2.11.
- **Discharges** **V2(c)**. The 200/100/never-150 values are `04` V2's own fixture
  values, reused here at the storage layer so the same numbers recur at the
  aggregation layer in item 10.

#### R2.12b `test_metric_unit_month_keeps_price_kinds_and_series_kinds_apart`
- **Asserts** two more inserts on top of R2.12's two rows. (a) The offering row
  again with `price_kind = 'auction_start'` and `median_ppm2 = 60.00` succeeds;
  `count(*)` equals `3`; `SELECT count(*) WHERE median_ppm2 = 130.00` equals `0`,
  so asking and auction-start do not blend. (b) The offering row again with
  `series_kind = 'flow'` and `flow_window_days = 90` succeeds; `count(*)` equals
  `4`.
- **Green by** Already green from R2.11.
- **Discharges** **V46**'s storage limb and D66. It is the same argument as R2.12
  one axis down: mixing is prevented by the key, not by a query filter someone
  might forget.

#### R2.13 `test_metric_unit_month_rejects_a_duplicate_key_within_one_price_type`
- **Asserts** re-inserting the `'offering'` row of R2.12 verbatim raises
  `psycopg.errors.UniqueViolation`.
- **Green by** Already green from R2.11.
- **Discharges** **V2(c)**.

#### R2.14 `test_price_type_assertion_reports_zero_violations_on_a_clean_database`
- **Asserts** `dzialki.ops.assertions.price_type_complete()` returns a result with
  `passed is True` and `observed == {"listing": 0, "transaction": 0, "metric_unit_month": 0}`
  — the exact dict, not a truthy check.
- **Green by** The Δ assertion in `src/dzialki/ops/assertions/`, plus the
  `assertion_run` table of `15` §11 to record it.
- **Discharges** **V1(c)**.

#### R2.15 `test_price_type_assertion_detects_a_violation_when_the_constraint_is_dropped`
- **Asserts** inside a transaction that is rolled back: drop
  `listing_price_type_check`, insert a `listing` with `price_type='sales'`, run the
  assertion, assert `passed is False` and `observed["listing"] == 1`, and assert a
  row was written to `assertion_run` with `passed = false` and
  `blocked_publication = true`.
- **Green by** The assertion returning a failure and recording it.
- **Discharges** **V1(c)**. Without this test, V1(c) is untestable by construction:
  the constraint makes the condition the assertion looks for unreachable, so an
  assertion that always returns zero would pass R2.14 forever. This is the
  mutation-style control that gives R2.14 meaning.

### 2.3 Red–green sequence — the other rules encoded in the schema

#### R2.16 `test_listing_rejects_non_positive_price_and_area`
- **Asserts** `price_pln = 0` raises `CheckViolation`; `price_pln = -1` raises
  `CheckViolation`; `area_m2 = 0` raises `CheckViolation`. And the boundary the
  other way: `price_pln = 0.01` with `area_m2 = 0.01` **succeeds** — the schema
  floor is `> 0`, not the FR-12 validity band, which is item 6's job.
- **Green by** The two CHECKs of `15` §5.
- **Discharges** **V10** partially (the schema floor only; the 100–500 000 m² and
  1–100 000 PLN/m² bands and the quarantine path are item 6).

#### R2.17 `test_price_per_m2_is_generated_and_cannot_be_written`
- **Asserts** three things. (a) Inserting `price_pln = 300000.00`,
  `area_m2 = 2500.00` yields `price_per_m2 == Decimal("120.00")` exactly.
  (b) `UPDATE listing SET price_pln = 360000.00` yields
  `price_per_m2 == Decimal("144.00")` — the derived value follows its inputs with
  no application involvement. (c) `INSERT ... (price_per_m2) VALUES (99.00)` raises
  an error whose message contains `"generated"`.
- **Green by** The `GENERATED ALWAYS AS (price_pln / area_m2) STORED` column.
- **Discharges** **V10**'s `price_per_m2 = price_pln / area_m2` identity, made
  structural. Limb (c) is the important one: it removes the drift class of bug
  entirely rather than testing for its absence.

#### R2.18a `test_metric_range_bounds_are_ordered`
- **Asserts** three cases against constraint `range_bounds_ordered`:
  `min_ppm2` above `p25_ppm2` → `CheckViolation`; `p75_ppm2` below `median_ppm2` →
  `CheckViolation`; all five percentile columns equal, with `n=1` and
  `range_kind='min_max'` → **succeeds**. The third case is the degenerate row rule 7
  requires: one observation is still shown, with its range collapsed to a point.
- **Green by** The `range_bounds_ordered` CHECK of `15` §9.
- **Discharges** **V4** at the storage layer.
- **D67** The old `range_kind_matches_n` CHECK is gone. O11 marks n=5 unratified,
  and a provisional parameter must not need a migration to change. The database now
  enforces internal consistency only; the threshold moves to R2.18b.

#### R2.18b `test_range_kind_threshold_is_read_from_configuration`
- **Asserts** with `range_kind_min_n: 5` in a temporary configuration file,
  `range_kind_for(1) == "min_max"`, `range_kind_for(4) == "min_max"`,
  `range_kind_for(5) == "iqr"`, `range_kind_for(1000) == "iqr"`. Then, with
  `range_kind_min_n: 8`, `range_kind_for(5) == "min_max"`. The last assertion is
  the one that proves the threshold is not frozen: an implementation with `5`
  written into the code passes the first four and fails the fifth.
- **Green by** `dzialki.config.metrics.load()` and
  `dzialki.metrics.ranges.range_kind_for(n)`.
- **Discharges** **V4** at the application layer. Unit test, no database.
- **Companion architecture test** A scan of `db/migrations/` for the string
  `range_kind_matches_n` asserts **zero** occurrences. D67 removed the CHECK, and a
  re-introduction must fail rather than pass quietly.

#### R2.18c `test_metric_spread_is_absent_only_when_the_source_publishes_none`
- **Asserts** four cases against constraint `spread_present_unless_unavailable`.
  (a) `range_kind='unavailable'` with `n=40`, `median_ppm2` set and all four spread
  columns `NULL` → **succeeds**. (b) The same row with `p25_ppm2` set → rejected.
  (c) `range_kind='iqr'` with any one of the four spread columns `NULL` → rejected,
  asserted once per column. (d) `range_kind='unavailable'` with `median_ppm2=NULL`
  → rejected with `NotNullViolation`, because a row with neither a central value
  nor a spread carries nothing.
- **Green by** The `spread_present_unless_unavailable` CHECK of `15` §9.
- **Discharges** **V4**'s D69 limb. GUS publishes a central value with no spread.
  Rule 7 survives the addition: the spread may be absent only when the source
  publishes none, and then it must be absent completely. A half-filled spread is
  unwritable, so nullability cannot be used to skip the spread. Rendering the
  explicit copy is item 11's job, not the schema's.
- **Note** `range_bounds_ordered` exempts `'unavailable'`, because there are no
  bounds to order. R2.18a's cases therefore all use `'iqr'` or `'min_max'`.

#### R2.18d `test_metric_flow_row_states_its_window`
- **Asserts** three cases against constraint `flow_states_its_window`:
  `series_kind='flow'` with `flow_window_days = NULL` → `CheckViolation`;
  `series_kind='stock'` with `flow_window_days = 90` → `CheckViolation`;
  `series_kind='flow'` with `flow_window_days = 90` → **succeeds**.
- **Green by** The `flow_states_its_window` CHECK of `15` §9.
- **Discharges** **V4**. D56 made the flow series the headline number and D107 set
  the window to 90 days. A flow row that does not say which window produced it is
  not interpretable, and a stock row that names one is a mislabelled flow.

#### R2.19 `test_metric_cannot_be_stored_without_its_sample_size_or_central_value`
- **Asserts** two inserts, each with exactly one of `n` and `median_ppm2` set to
  `NULL`, each raising `NotNullViolation` with `exc.diag.column_name` equal to that
  column. The four spread columns are **not** `NOT NULL` any more; R2.18c covers
  them, because their rule is conditional rather than absolute.
- **Green by** The two remaining NOT NULLs of `15` §9.
- **Discharges** **V4**. Rule 7's floor is a sample size and a central value on
  every row. The spread is required too, but only where a spread exists, which is a
  CHECK rather than a NOT NULL.

#### R2.20 `test_metric_requires_provenance`
- **Asserts** `as_of = NULL` raises `NotNullViolation` on `as_of`;
  `source_ids = '{}'` raises `CheckViolation` on the
  `array_length(source_ids,1) > 0` constraint; `source_ids = NULL` raises
  `NotNullViolation`.
- **Green by** The `as_of` NOT NULL and the `source_ids` CHECK of `15` §9.
- **Discharges** **V5(a)** at the storage layer. (V5's Δ assertion over a populated
  database is item 10; nothing writes `metric_*` rows yet.)

#### R2.21 `test_transaction_rejects_publication_before_transaction_date`
- **Asserts** `transacted_at = 2024-06-01, as_of = 2024-01-01` raises
  `CheckViolation` with constraint name `published_after_transacted`; equal dates
  succeed; `as_of` one day later succeeds.
- **Green by** The `published_after_transacted` CHECK of `15` §8.
- **Discharges** **V32** partially — it catches the specific loader bug of swapping
  the two dates. V32's charting limb is later.

#### R2.22 `test_raw_document_identical_refetch_does_not_duplicate`
- **Asserts** inserting the same `(source_id, url, content_hash)` twice raises
  `UniqueViolation`; inserting the same `(source_id, url)` with a **different**
  `content_hash` succeeds and leaves `SELECT count(*)` equal to `2`.
- **Green by** The `UNIQUE (source_id, url, content_hash)` of `15` §4.
- **Discharges** **V57(a)** at the schema layer. V57(b)'s re-parse drill needs a
  parser and is item 6.

#### R2.23 `test_admin_unit_rejects_invalid_geometry`
- **Asserts** inserting the self-intersecting bow-tie polygon from
  `tests/fixtures/geo/bowtie_2026-08-08.wkt` raises `CheckViolation` with
  constraint name `geom_valid`; the same polygon repaired by `ST_MakeValid`
  succeeds.
- **Green by** The `geom_valid` CHECK of `15` §3.
- **Discharges** **V6** partially (the "no invalid geometry" limb, at the storage
  layer — V6's fixture-wide count is item 3).

#### R2.24 `test_every_geometry_column_declares_an_srid`
- **Asserts** `SELECT f_table_name, f_geometry_column, srid FROM geometry_columns
  WHERE srid = 0` returns **zero rows**; and that
  `admin_unit.geom`'s declared type is exactly `geometry(MultiPolygon,4326)` and
  `anchor.geom` exactly `geometry(Point,4326)`; and that inserting an
  EPSG:2180 geometry into `admin_unit.geom` raises an error mentioning `"SRID"`.
- **Green by** Typed geometry columns per `15` §3.
- **Discharges** **V31** ("a schema test asserting no geometry column lacks an
  SRID").

#### R2.30 `test_listing_foreign_keys_are_exactly_the_two_that_exist_today`
- **Asserts** the set of tables referenced by `contype='f'` constraints on
  `listing` equals exactly `{"source","admin_unit"}`. `parcel` and `plot_cluster`
  are **absent**, while the columns `parcel_id` and `plot_cluster_id` exist as
  plain `BIGINT`. The test docstring names items 9 and 14 as the migrations that
  must add the two missing foreign keys.
- **Green by** The `listing` table of `15` §5, whose comment marks both columns as
  "FK added by a later migration".
- **Discharges** none. It records a deliberate deferral so it stays deliberate: a
  test that pins the current set forces the later migration to change this test on
  purpose, rather than letting the foreign keys be forgotten.

#### R2.31 `test_admin_unit_carries_provenance_and_a_ring_array`
- **Asserts** the `admin_unit` column set contains `as_of` (`date`, `NOT NULL`),
  `source_id` (`integer`, `NOT NULL`, foreign key to `source(id)`) and `in_ring`
  (`text[]`, `NOT NULL`, default `'{}'`). And that inserting a row with
  `as_of = NULL` raises `NotNullViolation` on `as_of`, and one with a `source_id`
  that no `source` row holds raises `ForeignKeyViolation`.
- **Green by** The `admin_unit` table of `15` §3.
- **Discharges** **V5(a)** for reference data. Rule 7 applies to boundaries too:
  PRG is republished, so a stored boundary without its as-of date cannot be dated
  later. `in_ring` is asserted as an **array**, because a boolean cannot express
  membership of two rings and a comma-joined string invites string matching.

### 2.4 Red–green sequence — append-only history (V12)

#### R2.25 `test_listing_snapshot_is_range_partitioned_on_observed_at`
- **Asserts** `SELECT partstrat FROM pg_partitioned_table WHERE partrelid =
  'listing_snapshot'::regclass` equals `"r"`; the partition key column name equals
  `"observed_at"`; and the count of attached partitions is `>= 4`, including
  partitions whose ranges cover the current month and the following three.
- **Green by** The partitioned table of `15` §5 plus a partition-creation step in
  the migration.
- **Discharges** **V12** structurally, and `10` §1's "partitioned from day one".

#### R2.26 `test_snapshot_insert_outside_every_partition_range_is_rejected`
- **Asserts** inserting `observed_at = '2099-01-01'` raises an error whose message
  contains `"no partition of relation"`.
- **Green by** Already green from R2.25.
- **Discharges** none of its own; it pins the operational requirement that
  partitions must be created ahead of time, so the item-5 crawler cannot silently
  lose a day when the calendar rolls past the last partition.

#### R2.27 `test_pipeline_role_can_append_to_listing_snapshot`
- **Asserts** connected as `app_pipeline`, an `INSERT` into `listing_snapshot`
  succeeds and `SELECT count(*)` equals `1`.
- **Green by** `CREATE ROLE app_pipeline` plus `GRANT INSERT, SELECT`.
- **Discharges** none. Positive control, and it must be written **before** R2.28:
  without it, a revocation test would pass against a table that does not exist or a
  role that cannot connect.

#### R2.28 `test_no_application_role_can_update_or_delete_snapshots`
- **Asserts** six privilege checks, all `False`:
  `has_table_privilege(role, 'listing_snapshot', priv)` for
  `role ∈ {app_read, app_write, app_pipeline}` and `priv ∈ {UPDATE, DELETE}`. Then
  two live attempts: connected as `app_pipeline`, `UPDATE listing_snapshot SET
  price_pln = 1` raises `psycopg.errors.InsufficientPrivilege`, and `DELETE FROM
  listing_snapshot` raises the same.
- **Green by** The `REVOKE UPDATE, DELETE` of `15` §5.
- **Discharges** **V12(a)**'s database-level limb. V12(a)'s codebase-scan limb and
  V12(b)'s three-day crawl are item 5.

#### R2.29 `test_read_role_cannot_write_anywhere`
- **Asserts** connected as `app_read`, `INSERT INTO listing ...` raises
  `InsufficientPrivilege`; and `has_table_privilege('app_read', t, 'INSERT')` is
  `False` for **every** table in schema `public` — a loop over the table list, so a
  future table added without thinking about grants fails this test.
- **Green by** Role grants per `15` §12.
- **Discharges** **V39** partially (the role-separation limb; the network and
  endpoint limbs are N/A for v0 per O4, since v0 runs locally under D44).

### 2.5 What item 2 does **not** discharge

**V2(a) and V2(b)** — the divergent-median unit test and the missing-sales-data
absence marker — are *aggregation* behaviour and belong to item 10. Item 2 can only
make mixing structurally impossible (R2.11–R2.13). Claiming V2 as discharged here
would be exactly the overclaim `20` §2 warns about.

**V4's threshold and V46's display limb.** R2.18b proves the n threshold comes from
configuration, and R2.18c proves `range_kind = 'unavailable'` is storable. Neither
proves the user sees the right words. D69 requires explicit copy for a source that
publishes no spread, and that is item 11's job.

---

## 3. Work item 3 — PRG + TERYT for both anchor rings

**1 day.** Verification tier **A** for TERYT assignment and projection maths (an
independently computable correct answer exists), **B** for PRG content (the TERYT
TERC register is the independent second source). Named detector for silent failure
**F4 — wrong gmina**.

**Both former blockers are answered.** D64 fixes ring membership: a gmina belongs
to a ring when **any part of its boundary lies within 25 km of the anchor point**.
`15` §3 states the rule once, materialises it into `admin_unit.in_ring`, and every
consumer reads that column. §4.7 is answered too: the import extent is the two
rings, and V6 now asserts an **exact list from the fixture manifest** rather than
an approximate gmina count.

**No TERYT code appears as a literal in this document.** The repository gave two
different codes for gmina Skierniewice, and I invented one of them. Both are now
removed. The TERC register is the only source; tests read codes from the fixture
manifest, and R3.25 fails when a document disagrees with the register.

### 3.1 Red–green sequence — the pure parser (no I/O)

#### R3.1 `test_prg_parser_yields_the_manifest_feature_counts`
- **Asserts** parsing `tests/fixtures/prg/prg_clip_2026-08-08.gpkg` yields feature
  counts per level exactly equal to the counts recorded in
  `tests/fixtures/prg/manifest.json` — `{"voivodeship": V, "powiat": P, "gmina": G}`
  where V, P, G are the literal integers written into the manifest at recording
  time. Equality, per level.
- **Green by** `dzialki.ingest.official.prg.parse()`, pure, returning
  `Iterator[AdminUnitRecord]` per the `16` §2 connector contract.
- **Discharges** **V6** (the count limb, at fixture scale).
- **Note** The manifest is the oracle, not this document. V6 now asserts the exact
  gmina list for the two rings, taken from the manifest; the earlier "~177",
  "~314", "~10" were approximations and therefore not falsifiable.

#### R3.2 `test_prg_parser_extracts_teryt_level_and_parent_for_a_known_gmina`
- **Asserts** the parsed record whose `teryt` equals
  `manifest["teryt"]["gmina_skierniewice_rural"]` has `name == "Skierniewice"`,
  `level == "gmina"` and `parent_teryt == manifest["teryt"]["powiat_skierniewicki"]`.
  And the record whose `teryt` equals `manifest["teryt"]["miasto_skierniewice"]`
  has `name == "Skierniewice"`, `level == "gmina"` and a **different**
  `parent_teryt`. Two units, identical names, different codes, different parents.
- **Green by** Attribute mapping in the parser.
- **Discharges** **V30**. This is the Skierniewice trap stated as data before it is
  stated as behaviour.
- **Note** Both codes come from the manifest, which the TERC register fills. No
  code is written into the test file. `04`'s fixtures policy rule 2 applies: a
  fixture is never edited to make a test pass.

#### R3.3 `test_prg_teryt_codes_and_names_agree_with_the_terc_register`
- **Asserts** for every gmina record from the PRG fixture, the pair
  `(teryt, name)` appears in `tests/fixtures/teryt/terc_2026-08-08.csv`; the count
  of mismatched pairs equals `0`, and the failure message lists them.
- **Green by** Nothing beyond R3.2 — this is a cross-source agreement check between
  two independently recorded files.
- **Discharges** **V6** ("correct TERYT codes"). Tier **B**: PRG's attributes and
  the TERC register are separate publications, so agreement is evidence and
  disagreement is a real signal.

#### R3.4 `test_fixture_contains_at_least_two_gminas_sharing_a_name`
- **Asserts** the multiset of gmina names in the fixture has at least one name with
  multiplicity `>= 2`, and specifically `names.count("Skierniewice") == 2`.
- **Green by** Recording a fixture clip that includes both.
- **Discharges** none. It is a guard on the *fixture*: R3.10 and R3.13 are
  meaningless against a fixture where every name happens to be unique, and a
  re-record that quietly dropped one would make them vacuously green.

### 3.2 Red–green sequence — the loader

#### R3.5 `test_loader_inserts_every_fixture_unit_with_valid_geometry`
- **Asserts** after loading: `SELECT count(*) FROM admin_unit WHERE level='gmina'`
  equals the manifest's gmina count; `SELECT count(*) FROM admin_unit WHERE NOT
  ST_IsValid(geom)` equals `0`; `SELECT count(*) FROM admin_unit WHERE
  ST_IsEmpty(geom)` equals `0`; and `ST_SRID(geom)` equals `4326` for every row.
- **Green by** `dzialki.ingest.official.prg.emit()` writing `admin_unit`.
- **Discharges** **V6**.

#### R3.6 `test_every_gmina_parent_resolves_to_an_in_scope_powiat`
- **Asserts** the query counting gminas whose `parent_teryt` is NULL, or joins to a
  row whose `level <> 'powiat'`, returns exactly `0`. And symmetrically, every
  powiat's parent resolves to a `voivodeship`.
- **Green by** Loading parents before children, or deferring the FK to end of
  transaction.
- **Discharges** **V6** ("every gmina's `parent_teryt` resolves to an in-scope
  powiat").

#### R3.7 `test_gmina_geometries_do_not_overlap_beyond_rounding_tolerance`
- **Asserts** for every pair of gminas whose bounding boxes intersect,
  `ST_Area(ST_Intersection(ST_Transform(a.geom,2180), ST_Transform(b.geom,2180)))`
  is `< 1.0` square metre. The maximum observed overlap is reported in the failure
  message.
- **Green by** Nothing — a guard on the source data and on the loader not
  duplicating features.
- **Discharges** **V6** ("no two gmina geometries overlap by more than a rounding
  tolerance"). The tolerance is pinned at **1 m²**; `04` leaves it unquantified,
  and an unquantified tolerance is not falsifiable.

#### R3.8 `test_gmina_areas_sum_to_their_powiat_area`
- **Asserts** for every powiat in the fixture,
  `|Σ area(gmina) − area(powiat)| / area(powiat) < 0.0001` (0.01%), areas computed
  in EPSG:2180.
- **Green by** Nothing — a hierarchy-consistency guard.
- **Discharges** **V6**. It catches a missing gmina that R3.5's count check would
  miss when the manifest itself was recorded from a short download.

#### R3.9 `test_every_gmina_resolves_to_itself_from_its_own_interior_point`
- **Asserts** for **every** gmina in the fixture (not one known answer):
  `gmina_for_point(ST_PointOnSurface(g.geom))` returns `g.teryt`. The count of
  self-resolution failures equals `0`.
- **Green by** `dzialki.geo.gmina_for_point()`, a point-in-polygon against `admin_unit`
  filtered to `level='gmina'`.
- **Discharges** **V6**, **V30**. Property test over the whole fixture — see §5.3.
  It catches a CRS mix-up, an inverted polygon, and an off-by-one in the lookup,
  none of which a single known-answer test reliably catches.

### 3.3 Red–green sequence — known answers and the Skierniewice trap

#### R3.10 `test_budy_grabskie_resolves_to_rural_gmina_skierniewice`
- **Asserts** for the Budy Grabskie **village centroid** read from
  `tests/fixtures/known_answers/known_points_2026-08-08.json`:
  `gmina_for_point(p).teryt == point["expected_teryt_gmina"]`,
  `.name == "Skierniewice"`,
  `.parent_teryt == point["expected_parent_teryt"]`, and the resolved powiat's name
  equals `"skierniewicki"`. The two codes come from the fixture, which the TERC
  register fills.
- **Green by** Already green from R3.9 if the loader is correct; red if the
  fixture clip omits the gmina.
- **Discharges** **V6** (the named known-answer spatial test) and **V30(b)**. This
  is the check `18` §6 item 3 calls out by name.
- **Privacy note** The input is the **public village centroid**, never the anchor's
  address or house number (FR-23, D36 — the anchor is a place visited, not the
  subject). The fixture file carries no street and no house number, and R1.8 scans
  for both.

#### R3.11 `test_city_of_skierniewice_resolves_to_a_different_unit`
- **Asserts** for the Skierniewice city-centre point from the same fixture:
  `gmina_for_point(p).teryt == point["expected_teryt_gmina"]`; that this differs
  from R3.10's result (`!=` asserted explicitly); that **both** resolved names
  equal `"Skierniewice"`; and that the two `parent_teryt` values differ.
- **Green by** Nothing beyond R3.10.
- **Discharges** **V30(b)**. Asserting the names are *equal* while the codes
  *differ* is the whole point: it proves the resolution cannot have gone via the
  name.

#### R3.12 `test_elblag_ring_anchor_resolves_to_the_city_unit`
- **Asserts** for the Elbląg centre point: the resolved unit's `teryt` equals the
  value recorded in the known-answers fixture for `m. Elbląg`, and its
  `parent_teryt` differs from that of at least one gmina of powiat elbląski — the
  same city/rural distinction as ring A, verified for ring B (D49 requires both
  rings, so a known-answer test for only one ring leaves half the scope unverified).
- **Green by** Fixture coverage of ring B.
- **Discharges** **V6**, **V30** for ring B.

#### R3.13 `test_no_code_path_resolves_a_gmina_by_name`
- **Asserts** an architecture test over `src/dzialki/`: parsing every module with `ast`,
  (a) no function in `dzialki.geo` has a parameter named `gmina_name`, `name` or
  `nazwa` whose value reaches an `admin_unit` query; (b) no SQL string literal
  anywhere in `src/` matches
  `r"admin_unit[\s\S]{0,200}\bname\s*(=|ILIKE|LIKE)"` (case-insensitive); (c) the
  count of matches is `0` and the failure message names the file and line.
- **Green by** Nothing — a standing prohibition.
- **Discharges** **V30(a)** ("static check for gmina lookups by name string").

#### R3.14 `test_boundary_risk_flag_fires_at_400m_and_not_at_600m`
- **Asserts** for the two points recorded in the known-answers fixture — one
  measured at 400 m and one at 600 m from a named gmina boundary segment, both
  distances computed in EPSG:2180 at fixture-recording time and written into the
  fixture — `boundary_risk(p_400) is True` and `boundary_risk(p_600) is False`.
  The threshold is 500 m per `07` §2.
- **Green by** `dzialki.geo.boundary_risk()` using `ST_Distance` in EPSG:2180 against
  `ST_Boundary` of the containing gmina.
- **Discharges** **V30(c)**. Detector for **F4**.

### 3.4 Red–green sequence — projections (V31)

#### R3.15 `test_distance_between_two_known_points_is_correct_within_one_metre`
- **Asserts** for the point pair in the known-answers fixture,
  `|dzialki.geo.distance_m(p1, p2) − geod_inverse_distance(p1, p2)| <= 1.0` metre,
  where the reference is `pyproj.Geod(ellps="WGS84").inv()` — an implementation
  independent of PostGIS and of our code.
- **Green by** `distance_m()` transforming to EPSG:2180 before measuring.
- **Discharges** **V31**.

#### R3.16 `test_distance_computed_in_degrees_fails_the_known_answer`
- **Asserts** the same pair measured **without** transformation (treating EPSG:4326
  as planar and scaling by a nominal 111 320 m/degree) differs from the reference by
  more than `1000.0` metres — i.e. the naive computation is demonstrably wrong at
  this location, which is what makes R3.15 a real test rather than a coincidence.
- **Green by** Nothing — a control.
- **Discharges** **V31** ("a test that a distance computed in degrees would fail
  the known-answer check"). Mutation-style control in the sense of `20` §4.8.

#### R3.17 `test_geometry_round_trip_through_epsg_2180_is_lossless_to_a_millimetre`
- **Asserts** for every gmina geometry,
  `ST_MaxDistance(g.geom, ST_Transform(ST_Transform(g.geom, 2180), 4326)) < 0.000001`
  degrees (≈0.1 mm), and `ST_NPoints` is unchanged.
- **Green by** Nothing — a property of the transform, asserted so a later switch to
  a wrong EPSG code is caught.
- **Discharges** **V31**. See §5.3.

### 3.5 Red–green sequence — anchors and rings

#### R3.18 `test_anchor_table_stores_only_key_label_and_point`
- **Asserts** the column set of `anchor` equals exactly `{"key","label","geom"}`;
  loading from `config/anchors.example.yml` inserts 2 rows; for every row,
  `re.search(r"\d", label) is None`; and `GeometryType(geom) == "POINT"` with
  `ST_SRID(geom) == 4326`.
- **Green by** The `anchor` table of `15` §3 and a loader reading the config
  produced in item 1.
- **Discharges** **V7** (FR-23's "no street address or house number in the
  database") and **V31**.

#### R3.19 `test_ring_membership_is_boundary_within_25km_not_centroid` (D64)
- **Asserts** against the synthetic ring fixture, whose four gminas sit at known
  geodesic offsets from a synthetic anchor: the set of gminas with the anchor key
  in `in_ring` equals exactly the manifest's `in_ring_T` list. And the
  **discriminator**: a gmina whose nearest boundary point lies inside 25 km while
  its centroid lies outside is a member. An implementation that used the centroid,
  or the gmina seat, fails here and passes every other spatial test in the suite.
  `in_ring` holds a `TEXT[]`, and the member's value equals exactly `["T"]`.
- **Green by** `dzialki.geo.rings.assign(conn, radius_m=25000)` writing `in_ring`
  with `ST_DWithin(unit.geom::geography, anchor.geom::geography, 25000)`, per `15`
  §3.
- **Discharges** **V6**'s D64 limb.

#### R3.19b `test_ring_assignment_is_idempotent`
- **Asserts** running `assign()` twice leaves the member's `in_ring` equal to
  `["T"]`, **not** `["T","T"]`.
- **Green by** An assignment that replaces the array rather than appending to it.
- **Discharges** none. The `array_append` shown in `15` §3 appends
  unconditionally, so this test is red against the SQL as printed. That is why it
  is written.

#### R3.20 `test_ring_membership_matches_the_manifest_gmina_list`
- **Asserts** two limbs. (a) On the synthetic fixture, the member set equals the
  manifest's `in_ring_T` list — set equality, not a count. (b) On the recorded PRG
  clip, `set(ring("A"))` equals `manifest["ring_gminas"]["A"]` and `set(ring("B"))`
  equals `manifest["ring_gminas"]["B"]`, both **exact TERYT lists**.
- **Green by** Nothing beyond R3.19.
- **Discharges** **V6**. V6 no longer asserts an approximate gmina count. It
  asserts the exact list for the two rings, and the manifest is the oracle. Limb
  (b) reads the gitignored anchors, so it skips outside a developer machine with a
  named reason; limb (a) runs everywhere.

#### R3.21 `test_both_rings_are_non_empty_and_disjoint`
- **Asserts** `len(ring("A")) > 0`, `len(ring("B")) > 0`, and
  `set(ring("A")) & set(ring("B")) == set()` — the two rings are ~300 km apart, so
  any overlap means the anchor points were swapped or mis-parsed.
- **Green by** The ring builder.
- **Discharges** none of its own; it is the cheapest available guard on D49's
  "both rings" actually meaning two distinct places.

#### R3.22 `test_prg_load_is_idempotent`
- **Asserts** running the loader twice leaves `SELECT count(*) FROM admin_unit`
  unchanged and the geometry digest of §5.3 byte-identical.
- **Green by** An upsert keyed on `teryt`.
- **Discharges** none. Property — §5.3.

#### R3.23 `test_prg_load_is_independent_of_feature_order`
- **Asserts** loading the fixture with its features shuffled by a seeded RNG
  produces the same geometry digest as loading it in file order. Exact equality.
- **Green by** Nothing if the loader is order-independent; red if it, say, assigns
  parents positionally.
- **Discharges** none. Property — §5.3. It is also the relation `20` §4.3 lists as
  "permute the input order → output identical", applied at the first place in the
  pipeline where it can be applied.

#### R3.24 `test_loaded_admin_units_carry_their_as_of_and_source`
- **Asserts** after the load: `count(*) WHERE as_of IS NULL` equals `0`;
  `count(*) WHERE source_id IS NULL` equals `0`; every `as_of` equals the
  manifest's `downloaded_at`; and every `source_id` resolves to the `source` row
  named `prg`.
- **Green by** The loader reading the manifest date and the source id, rather than
  defaulting either.
- **Discharges** **V5(a)** for `admin_unit`. R2.31 proves the columns exist and
  reject a null; this proves the loader fills them with the right values. A column
  that exists and always holds today's date carries no provenance.

#### R3.25 `test_repository_documents_cite_the_register_teryt_codes`
- **Asserts** an architecture test over the committed Markdown files: every 7-digit
  string adjacent to the token `Skierniewice` equals the manifest's
  `teryt.gmina_skierniewice_rural` or its `teryt.miasto_skierniewice`. The count of
  mismatches equals `0`, and the failure message prints the file, the line and the
  offending code.
- **Green by** Nothing — a standing guard.
- **Discharges** none. The repository once held two different codes for gmina
  Skierniewice, in `14-api-contract.md` and in this document. I invented one of
  them. This test keeps the register as the only source and fails when a document
  disagrees with it. It does **not** pick a code; picking one is what caused the
  error.

---

## 4. Blocked, ambiguous, or missing — resolve before the first test

Per `CLAUDE.md` rule 2 these are asked, not assumed. Each blocks a specific test.

**Eight items were raised. Batch 22 closed the last two open ones.** Only 4.8
remains, and it is a download, not a decision. The table records which decision
closed each item and which test now carries it.

| # | Item | Status | Test |
|---|---|---|---|
| 4.1 | Item 1 has no validation method | **Closed by D124** — V65 written | R1.11–R1.15 |
| 4.2 | `listing` foreign keys to future tables | **Closed** — plain `BIGINT`, foreign keys land with items 9 and 14 | R2.30 |
| 4.3 | `price_kind` absent from `15` | **Closed by D65, D66, D68, D115** | R2.1b, R2.4, R2.5, R2.6, R2.9b, R2.9e, R2.12b |
| 4.4 | `admin_unit` carries no provenance | **Closed** — `as_of` and `source_id` added | R2.31, R3.24 |
| 4.5 | V7(b) cannot run in CI | **Closed by D124** — pre-push hook, never CI | R1.8 |
| 4.6 | Ring membership undefined | **Closed by D64** — boundary within 25 km | R3.19, R3.19b, R3.20 |
| 4.7 | Import extent, and V6's approximate counts | **Closed** — the two rings, exact list from the manifest | R3.20 |
| 4.8 | The two Skierniewice TERYT codes | **Open** until the register is downloaded; the guard test stands | R3.25 |

### 4.1 Item 1 has no validation method of its own — **closed by D124**
`04`'s coverage table assigned item 1 to "V7 (anchor privacy); migrations covered
by V1's constraint-existence test". But R1.11–R1.15 — engine version, migration
head, idempotence, reversibility, schema-digest symmetry — were discharged by **no
V entry**, and rule 5 says a validation method precedes implementation.

**V65 now covers configuration loading and the parameter file** (FR-75). It carries
the four failure modes R1.11–R1.15 exercise, plus the static scan that catches a
ratified value copied into code. R1.11–R1.15 are writable.

### 4.2 `listing.parcel_id` and `listing.plot_cluster_id` — **closed**
The columns exist in migration `0002` as plain `BIGINT` with no foreign key. Items
9 and 14 add the two foreign keys when `plot_cluster` and `parcel` exist. R2.30
pins the current set, so the later migration must change that test on purpose.

### 4.3 `price_kind` — **closed by D65, D66 and D68**
`15` §2 now declares `price_kind AS ENUM ('asking','auction_start','tender',
'transaction')`. D65 names the three offering-side kinds. D68 adds `transaction`,
so a sales row can carry a kind too and `transaction` pins it by CHECK. D66 puts
`price_kind`, `series_kind` and `area_band` into `metric_unit_month`'s primary
key. Rule 6 is unaffected: `price_type` still separates offering from sales, and
`price_kind` is the finer axis inside each. Tests R2.1b, R2.4, R2.5, R2.5b, R2.6,
R2.9b, R2.11 and R2.12b carry it.

### 4.4 `admin_unit` provenance — **closed**
`15` §3 now gives `admin_unit` an `as_of DATE NOT NULL` and a `source_id INT NOT
NULL REFERENCES source(id)`, plus the `in_ring TEXT[]` that D64 materialises. R2.31
asserts the columns; R3.24 asserts the loader fills them. One consequence for the
migration order: `source` must be created before `admin_unit`.

### 4.5 V7(b) cannot run in CI — **closed by D124**
R1.8 needs the gitignored `config/anchors.yml` to know what strings to search for,
so it skips in a clean checkout — the exact environment where a leak would be
found.

**D124 settles it: V7(b) is a local pre-push hook and never runs in CI.** Putting
the addresses in CI to test that they are not in the repository defeats the point.
CI keeps V7(a), (c) and (d), which need no address. R1.8 keeps its skip, and the
skip reason names the hook so a reader knows where the check does run.

### 4.6 Ring membership — **closed by D64**
A gmina belongs to a ring when any part of its boundary lies within 25 km of the
anchor point. Not the centroid, not the gmina seat. The rule is inclusive at the
edge, which matches rule 7: a gmina half inside the ring is more useful shown with
its `n` than silently excluded. `15` §3 states it once and materialises it into
`admin_unit.in_ring`; every consumer reads that column and nothing recomputes it.
R3.19 is the discriminating test, and R3.19b keeps the assignment idempotent.

### 4.7 Import extent and V6's counts — **closed**
The v0 import extent is the **two rings**, per `18` §6 item 3. The three-voivodeship
extent belongs to the deferred full plan. V6 no longer asserts an approximate gmina
count: it asserts the **exact gmina list for the two rings**, taken from the fixture
manifest, which R3.20 checks. An approximate count cannot be falsified, so no test
in this document states one.

### 4.8 The two Skierniewice TERYT codes — **open, and the guard stands**
The repository gave two different codes for gmina Skierniewice: one in
`14-api-contract.md`, one in an earlier draft of this document. I invented the
first. Both are removed. I do **not** pick a code here, because picking one is what
produced the error. The GUS TERYT **TERC** register is the only source. The
recording step writes both Skierniewice codes into the fixture manifest, every test
reads them from there, and **R3.25 fails when any committed document disagrees with
the register**. This item closes when the register is downloaded, not before.

### 4.9 Tests deferred to later items (not blocked — simply not item 1–3 work)

| Deferred test | Needs | Item |
|---|---|---|
| V2(a) divergent-median (200/100/never-150 at the aggregate level) | an aggregator | 10 |
| V2(b) absent-sales marker | the query layer | 10 |
| V12(a) codebase scan for UPDATE/DELETE on `listing_snapshot`; V12(b) three-day crawl | a connector | 5 |
| V57(b) re-parse drill | a parser | 6 |
| V10 validity bands, quarantine, ar/ha conversion | normalization | 6 |
| V4's API-boundary and UI limbs | the app | 11 |
| V5's Δ assertion over populated `metric_*` | aggregates | 10 |
| V47 metamorphic price relations; V48 differential percentiles; V52 mutation run | a numeric core | 10 |
| V31's gmina-area cross-check against the published GUS area | that figure recorded as a fixture | 3, once recorded |

---

## 5. Fixtures

Per `04`'s fixtures policy: recorded once from the live source, dated in the
filename, committed, never hand-edited to make a test pass, re-recorded quarterly.

### 5.1 Item 1

| Path | Must contain |
|---|---|
| `config/anchors.example.yml` | Exactly two anchors, keys `A` and `B`, labels `PLACEHOLDER_ANCHOR_A`/`_B`, `lat: 0.0`, `lon: 0.0`. No digits in labels. Committed, not a fixture as such, but R1.5 asserts against it. |
| `config/sources.yml` | At least one entry with only `name` and `kind` set, so R1.10 can assert the three defaults. |
| `tests/fixtures/config/sources_bad_kind_2026-08-08.yml` | A source entry with `kind: "scraper"`, for R1.10's rejection limb. |
| `tests/fixtures/config/anchors_real_looking_2026-08-08.yml` | An anchor at a coordinate **inside** Poland's bounding box, used as the negative control proving R1.5's bounding-box assertion can fail. Use a round graticule crossing, never an address and never a named place. |

### 5.2 Item 2

| Path | Must contain |
|---|---|
| `tests/fixtures/geo/bowtie_2026-08-08.wkt` | One self-intersecting POLYGON in EPSG:4326 for which `ST_IsValid` is false — R2.23. |
| `tests/fixtures/geo/bowtie_repaired_2026-08-08.wkt` | The `ST_MakeValid` output of the above, for R2.23's positive limb. |
| No listing fixtures | Item 2's inserts are built in-test from literals (300000.00 / 2500.00 → 120.00 etc.) because the values under test are constraint boundaries, not source data. A recorded fixture here would obscure which value is doing the work. |

### 5.3 Item 3

| Path | Must contain |
|---|---|
| `tests/fixtures/prg/prg_clip_2026-08-08.gpkg` | A **clipped** PRG extract (the full national file is too large to commit). The clip rule is D64's rule, applied at clip time: every gmina with any part of its boundary within 25 km of anchor A or anchor B. Plus **both** Skierniewice units (the rural gmina and the city), powiat skierniewicki, powiat elbląski, m. Elbląg, m. Skierniewice, and every parent powiat and voivodeship of every included gmina. MultiPolygon, EPSG:4326. |
| `tests/fixtures/prg/manifest.json` | Source URL; download date; SHA-256 of the clip; the clip bounding box; the clip rule as a string; **exact** feature counts per level (the oracle for R3.1); `ring_gminas.A` and `ring_gminas.B` as **exact TERYT lists**, which is what V6 now asserts (R3.20); and the `teryt` block holding the register codes for the two Skierniewice units, powiat skierniewicki, m. Elbląg and powiat elbląski. |
| `tests/fixtures/teryt/terc_2026-08-08.csv` | The TERYT **TERC** register extract: `WOJ, POW, GMI, RODZ, NAZWA, NAZWA_DOD`, covering at minimum every unit in the PRG clip. The independent second source for R3.3. Recorded separately from PRG — if it is derived from PRG, R3.3 is vacuous. |
| `tests/fixtures/known_answers/known_points_2026-08-08.json` | Five entries, each with a `note` naming its provenance: (1) Budy Grabskie **village centroid** with its expected gmina and powiat codes; (2) Skierniewice city centre with its expected codes; (3) Elbląg city centre with its expected codes; (4) a pair `p_400`/`p_600` with the named boundary segment and the EPSG:2180 distances measured at recording time; (5) a two-point pair with an independently computed geodesic separation for R3.15/R3.16. Every code comes from the TERC register at recording time; **this document states none of them**. **No street names, no house numbers, no anchor address** — R1.8 scans this file too. |
| `tests/fixtures/prg/shuffled_seed.txt` | The RNG seed used by R3.23, committed so the shuffle is reproducible. |
| `tests/fixtures/synthetic/ring_membership.json` | The D64 fixture. Four synthetic gminas at known geodesic offsets from a synthetic anchor, generated by a committed script. Two of them are members under the boundary rule and non-members under the centroid rule; one is a member under both and one under neither. This is the fixture R3.19 discriminates on, and it needs no download. |
| `tests/fixtures/teryt/terc_2026-08-08.csv` (see above) | Recorded **before** R3.2 is typed. It resolves both Skierniewice codes into the manifest. |

**Fixture size note.** If the clipped PRG file exceeds a comfortable git size,
store it as a `.gpkg.zst` and decompress in a session fixture; do **not** reduce it
by dropping gminas, since R3.7, R3.8 and R3.9 derive their value from covering the
whole clip.

---

## 6. Metamorphic and property-based relations

`20` §4.3's price relations (double the prices → double the median) belong to the
numeric core and have nothing to act on in items 1–3. The relations that **do**
apply here are structural and spatial, and they are worth as much: each one holds
over the whole fixture rather than at one point, so they catch classes of bug that
known-answer tests pass straight through.

### 6.1 Item 1 — migrations

| Relation | Test | Why it earns its place |
|---|---|---|
| **Idempotence** — `upgrade(upgrade(∅)) == upgrade(∅)` | R1.13 | A migration re-run must be a no-op; the alternative is a duplicated seed row nobody notices. |
| **Involution** — `up ∘ down ∘ up == up` on the schema digest | R1.15 | Catches a `downgrade` that drops a table but leaves its type, index or grant. |

**Schema digest**, used by R1.13/R1.15 and R3.22: `pg_dump --schema-only
--no-owner --no-privileges`, with comments and `SET` lines stripped and remaining
lines sorted, hashed with SHA-256. Sorting removes dump-order nondeterminism, which
would otherwise make the digest flaky and the test worthless.

### 6.2 Item 2 — constraints

| Relation | Test | Statement |
|---|---|---|
| **Generated-column identity** | property test over `hypothesis` integers | For random `price ∈ [1, 10⁹]`, `area ∈ [1, 5·10⁵]` inserted as NUMERIC(12,2): `abs(price_per_m2 * area_m2 − price_pln) <= 0.005 * area_m2` (the rounding bound of a 2-dp quotient). Catches an operand swap that R2.17's single case could survive. |
| **Scaling** | property test | For any `(price, area)`, inserting `(2·price, area)` yields exactly `2 ×` the first row's `price_per_m2` where both are exactly representable at 2 dp. This is `20` §4.3's "double every price → median doubles" asserted at the earliest layer it can be. |
| **Ratio invariance** | property test | Inserting `(10·price, 10·area)` yields an **unchanged** `price_per_m2`. `20` §4.3's second relation, likewise pulled forward. |
| **Enum closure** | property test | For any generated string not in `{offering, sales}`, the insert raises `InvalidTextRepresentation`. Generalises R2.9 from one hand-picked label to the whole complement. |
| **Range-bound ordering** | property test | For five generated `Decimal`s, the insert succeeds iff `min <= p25 <= median <= p75 <= max`, else raises `CheckViolation` on `range_bounds_ordered`. Generalises R2.18a to the whole domain. D67 removed the `n`-coupled CHECK, so the database property is ordering, not the threshold. |
| **Threshold monotonicity** | property test, `unit` | For a configured `range_kind_min_n = k` and random `n ∈ [1, 1000]`: `range_kind_for(n) == "iqr"` iff `n >= k`, for `k ∈ {3, 5, 8}`. The property runs over three thresholds, so an implementation with any single value written into the code fails on the other two. |

### 6.3 Item 3 — spatial

| Relation | Test | Statement |
|---|---|---|
| **Self-resolution** | R3.9 | For every gmina `g`: `gmina_for_point(ST_PointOnSurface(g.geom)) == g.teryt`. Universally quantified over the fixture; catches CRS mix-ups and lookup off-by-ones that a single known answer will not. |
| **Hierarchy additivity** | R3.8 | `Σ area(children) == area(parent)` within 0.01%. |
| **Disjointness** | R3.7 | Pairwise gmina intersection area `< 1 m²`. |
| **Projection round-trip** | R3.17 | `4326 → 2180 → 4326` moves no vertex by more than ~0.1 mm and changes no vertex count. |
| **Distance symmetry** | property test | `distance_m(p, q) == distance_m(q, p)` exactly, and `distance_m(p, p) == 0.0`, for generated point pairs inside the fixture bbox. |
| **Load idempotence** | R3.22 | Loading twice equals loading once, by geometry digest. |
| **Order independence** | R3.23 | Loading a shuffled fixture equals loading it in file order, by geometry digest. `20` §4.3's permutation relation. |

**Geometry digest**, used by R3.22/R3.23: SHA-256 over
`SELECT teryt, ST_AsBinary(geom) FROM admin_unit ORDER BY teryt` — ordering by
`teryt` rather than by physical row order is what makes it comparable across loads.

---

## 7. Definition of done for items 1–3

Per `16` §6, and specific to these items:

1. §4.1 is answered and recorded in `00-decisions.md`, and §4.8 is closed by the
   TERC download. §4.2 to §4.4, §4.6 and §4.7 are already closed, and
   `15-database-schema.md` carries D64 to D69 and D91.
2. Every test in §1–§3 exists, was observed red, and is now green.
3. R3.19, R3.19b and R3.20 exist rather than being silently dropped.
4. Fixtures in §5 are committed, dated, and carry a manifest recording source URL,
   download date and hash. The known-answers file has been checked by eye for a
   street name or house number.
5. `V1`, `V2(c)`, `V6`, `V7`, `V12(a)`, `V30`, `V31` and `V46`'s storage limb pass;
   `V2(a)`, `V2(b)` and the rest of §4.9 are recorded as *not yet dischargeable*
   rather than claimed.
6. The Δ assertion `price_type_complete` runs in `ops/assertions/` and both R2.14
   and R2.15 pass — the second is what makes the first mean anything.
7. No TERYT code appears as a literal in any test file or in this document. R3.25
   is green, so no committed document disagrees with the register.
