# Non-functional requirements & access

Decision: D34. Validation: [`04-validation.md`](./04-validation.md) §V38–V39.

---

## 1. Scale — what we are actually building for

Sizing honestly matters here: the temptation is to build for a scale that will
never arrive and pay for it in complexity.

| Quantity | Estimate | Basis |
|---|---|---|
| Gminas in scope | ~500 | łódzkie 177 + mazowieckie 314 + Elbląg area ~10 |
| Active land listings at any time | 10k–40k | Two voivodeships plus a small powiat |
| New/changed listings per day | 500–2 000 | Typical churn |
| Snapshot rows per year | 4M–15M | Active listings × 365 |
| Parcels enriched | 10k–50k | Only listings we resolve, not all parcels |
| RCN transactions | 50k–300k | 2021→ present, coverage permitting |
| Concurrent users | **1–5** | D1 |

Snapshot rows dominate and grow linearly forever. At ~15M rows/year with narrow
rows this is small for Postgres, but it is the table that needs partitioning by
month from the start — retrofitting partitioning onto the one table that must
never be rewritten is unpleasant.

## 2. Performance targets

Modest, because the user count is 1–5 and the data is not large. These are
targets, not SLAs.

| Operation | Target | Note |
|---|---|---|
| Map choropleth, all gminas | < 1.5 s | Served from precomputed `metric_unit_month`, never computed live |
| Gmina side panel | < 500 ms | Precomputed |
| Plot page including comparable set | < 2 s | Comparable set computed live; this is the expensive one |
| What-if recompute | < 1 s | Must feel interactive to be usable |
| Full daily pipeline | < 4 h | Runs overnight; failure leaves yesterday's data intact |
| Nightly aggregate recomputation | < 30 min | |

The architectural rule that makes these achievable: **aggregates are precomputed,
verdicts are computed live**. Nothing in the map path touches the listing table.

## 3. Availability and failure behaviour

- No uptime target. A few hours down is an inconvenience, not an incident.
- **Data loss is the real failure mode**, not downtime — see
  [`11-operations.md`](./11-operations.md).
- The pipeline is **fail-safe, not fail-open**: a connector failure leaves the
  previous day's data in place and raises an alarm (FR-6). It never publishes
  partial results as if complete.
- The UI degrades per-component: a failed sales query blanks the sales line only,
  with an error state (`09` §3), never the whole page.

## 4. Retention

| Data | Retention | Why |
|---|---|---|
| `listing_snapshot` | **Forever** | Irreplaceable; the entire history asset |
| `raw_document` | 90 days hot, then compressed archive | Needed to re-parse after a parser fix; large |
| `transaction` | Forever | Small, authoritative |
| `valuation_log` | Forever | Required for `05` §9 scoring |
| Derived `metric_*` | Recomputable, but generations kept 24 months | Supports `08` §4 revision visibility |
| Quarantined records | 12 months | Diagnostics |

Personal data is not retained at all (FR-23): seller contacts exist only as salted
hashes, and no free-text field containing a phone number or name is stored
unscrubbed.

## 5. Access control (resolves O4)

Audience is the owner plus a few known people (D1). Proposed, pending
confirmation:

- **Single shared password** at a reverse proxy in front of the app, over HTTPS.
  No user accounts, no registration, no password reset flow — all of which would
  be substantial work for an audience of five.
- Postgres is **not** exposed publicly. Notebook access (O9) is via SSH tunnel to a
  read-only role with access to derived tables only.
- The write path (pipeline) runs as a separate role from the read path (API).
- No public endpoints at all, including the API — it exists only behind the proxy.

Flagged: a single shared password is appropriate for a private tool among people
who trust each other, and inappropriate the moment the audience widens. That
widening is a gate requiring a fresh review (PRD §12), and this is one of the
things it would need to revisit.

## 6. Cost envelope

Zero for data (D2). Hosting only:

| Item | Estimate |
|---|---|
| VPS (4 vCPU, 8 GB RAM, 160 GB SSD) | ~40–60 PLN/month |
| Off-site backup storage | ~5–10 PLN/month |
| Domain, optional | ~50 PLN/year |

8 GB is sized for PostGIS plus a self-hosted OSRM and Nominatim over a
Poland-region extract, which are the memory-hungry components. Running routing and
geocoding offline in batch rather than as live services keeps this within a small
VPS.

## 7. Portability

Everything runs under Docker Compose (PRD §11) so the whole system can move to
another host, or to a laptop, with a volume restore. Given the data is
irreplaceable, being able to bring it up somewhere else quickly *is* the disaster
recovery plan.
