# Operations & backup runbook

Decision: D34. Validation: [`04-validation.md`](./04-validation.md) §V40–V42.

---

## 1. Why backup is the highest-priority operational concern

Most of this system is reproducible. Code can be rebuilt, official data can be
re-downloaded, aggregates can be recomputed. **Two things cannot:**

1. `listing_snapshot` — the daily observed state of the market. If the VPS dies
   without backups, every price change, every days-listed figure and every trend
   built from our own observations is gone, and the only way to get them back is
   to wait months collecting again.
2. `valuation_log` — the predictions we made, which cannot be reconstructed
   because the comparable set that produced them no longer exists (`05` §9).

The product's core assets accrue slowly and vanish instantly. Backups are
therefore not housekeeping; they are the main thing standing between a working
product and a restart from zero.

## 2. Backup policy

| What | Frequency | Where | Retention |
|---|---|---|---|
| Postgres full dump | Nightly, after the pipeline | Off-site object storage, encrypted | 30 daily, 12 monthly |
| WAL / incremental | Continuous if cheap, else skip | Off-site | 7 days |
| `config/anchors.yml` and secrets | On change, manually | Encrypted, off the VPS | Current + 1 |
| `raw_document` archive | Weekly | Off-site, compressed | 12 months |

Rules:

- Backups go **off the VPS**. A backup on the same disk protects against nothing
  that actually happens.
- Backups are **encrypted at rest** — they contain the full listing corpus.
- The anchor config is backed up **separately and never to git** (FR-22).

## 3. Restore drill — the part that is usually skipped

A backup that has never been restored is a hypothesis, not a backup.

**Quarterly**, and after any schema migration:

1. Provision a clean container.
2. Restore the most recent nightly dump.
3. Assert: row counts within expected bounds of production, `listing_snapshot`
   maximum `observed_at` within 24 h of the dump, all V1–V5 hard invariants pass
   on the restored database.
4. Record the wall-clock restore time. If it exceeds two hours, the backup format
   needs revisiting.

A failed drill is treated as a production incident, because it means the system is
currently one disk failure away from unrecoverable.

## 4. Daily pipeline

Order matters — enrichment depends on ingestion, aggregates on enrichment:

```
01  health check: sources reachable, disk space, last-run status
02  ingest listings (all connectors, per-host rate limited)
03  normalize, validate, quarantine          → V10
04  deduplicate into plot clusters           → V11
05  geocode / resolve parcels                → 07
06  enrich: zoning, constraints, nature, travel time
07  ingest official data (scheduled cadence, not daily)
08  recompute aggregates (metric_unit_month) → 05 §7
09  run all Δ data assertions                → 04
10  refresh coverage page data
11  backup
```

- Steps 02–06 are **resumable**: a crash resumes rather than restarting, so a
  partial day is not lost.
- Step 09 failing **blocks step 10** — a failed assertion must not reach the
  coverage page as though it passed.
- Step 11 runs regardless of earlier failures. Backing up a partially updated
  database is better than not backing up.

## 5. Monitoring and alarms

For a one-person system, alarms must be few and each must be actionable.

| Alarm | Trigger | Response |
|---|---|---|
| **Connector silent** | Zero items where the floor is higher (FR-6) | Check for site change; re-record fixtures |
| **Schema drift** | Parse failure rate above threshold | Fix parser; re-parse from `raw_document` |
| **Assertion failure** | Any Δ assertion fails | Aggregates not published; investigate before the next run |
| **Pipeline overrun** | Runtime beyond the per-scope budget in `10` §2.1 | Check for a crawl loop or a missing index |
| **Backup failure** | Nightly dump missing or size anomalous | **Highest priority** — §1 |
| **Disk > 80%** | | Prune `raw_document`, check snapshot growth |
| **Cross-source divergence** | Offering below sales per powiat (V16) | Almost always a parser bug |

Alarms go to one channel the owner actually reads. An alarm nobody sees is
indistinguishable from no monitoring.

## 6. Recovery from a bad parse

The scenario that will happen: a portal changes, the parser produces plausible but
wrong values, and this is noticed a week later.

Recovery is possible **only because `raw_document` is retained** (`10` §4):

1. Fix the parser; add a fixture from the drifted format.
2. Quarantine the affected `listing` rows.
3. Re-parse from `raw_document` for the affected window.
4. Recompute aggregates for that window — a new generation, not a silent
   overwrite (`08` §4).
5. Note the correction on the coverage page.

`listing_snapshot` is not rewritten — the raw observation was correct; only its
interpretation was wrong. This is exactly why the raw layer exists.

## 7. Secrets

No API keys are needed for the free sources, which removes most secret handling.
What exists — the shared access password, backup encryption key, VPS SSH key —
lives in environment files that are gitignored, and in an off-VPS password
manager. Never in the repo, never in fixtures, never in logs.

## 8. Deployment

Docker Compose, one command, on the VPS. A deploy is: pull, migrate, restart, run
the invariant tests against the live database (V1–V5). A migration that changes a
price-bearing table requires the restore drill (§3) afterwards, because those are
the migrations that can silently destroy the irreplaceable data.
