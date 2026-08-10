"""R2.23–R2.31 — partitioning, append-only grants, provenance and deferred keys.

The append-only rule on `listing_snapshot` is a grant, not a convention. A
convention is a sentence in a document; a revoked grant is a database refusing
the statement.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.needs_db]

ROLES = ["app_read", "app_write", "app_pipeline"]


def test_listing_snapshot_is_range_partitioned(conn) -> None:
    """Retrofitting partitioning onto the one table that grows forever and must
    never be rewritten would be the riskiest migration in the system."""
    strategy = conn.execute(
        "SELECT p.partstrat FROM pg_partitioned_table p "
        "JOIN pg_class c ON c.oid = p.partrelid "
        "WHERE c.relname = 'listing_snapshot'"
    ).fetchone()
    assert strategy is not None, "listing_snapshot is not partitioned"
    assert strategy[0] == "r"


def test_listing_snapshot_partitions_by_observed_at(conn) -> None:
    column = conn.execute(
        "SELECT a.attname FROM pg_partitioned_table p "
        "JOIN pg_class c ON c.oid = p.partrelid "
        "JOIN unnest(p.partattrs) AS k(attnum) ON TRUE "
        "JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = k.attnum "
        "WHERE c.relname = 'listing_snapshot'"
    ).fetchone()
    assert column[0] == "observed_at"


@pytest.mark.parametrize("role", ROLES)
def test_role_exists(conn, role) -> None:
    found = conn.execute(
        "SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)
    ).fetchone()
    assert found is not None


@pytest.mark.parametrize("role", ["app_read", "app_write"])
@pytest.mark.parametrize("privilege", ["UPDATE", "DELETE"])
def test_no_role_may_rewrite_a_snapshot(conn, role, privilege) -> None:
    granted = conn.execute(
        "SELECT has_table_privilege(%s, 'listing_snapshot', %s)", (role, privilege)
    ).fetchone()[0]
    assert granted is False


def test_admin_unit_carries_its_provenance(conn) -> None:
    """Rule 7: boundaries are stored data, so they carry a source and a date."""
    columns = {
        row[0]: row[1]
        for row in conn.execute(
            "SELECT column_name, is_nullable FROM information_schema.columns "
            "WHERE table_name = 'admin_unit'"
        ).fetchall()
    }
    assert columns["as_of"] == "NO"
    assert columns["source_id"] == "NO"
    assert columns["in_ring"] == "NO"


def test_listing_parcel_keys_are_deferred_on_purpose(conn) -> None:
    """R2.30. `parcel` and `plot_cluster` arrive with their own work items.

    Pinning the current set means the later migration has to change this test
    deliberately, rather than the keys appearing by accident.
    """
    referenced = {
        row[0]
        for row in conn.execute(
            "SELECT confrelid::regclass::text FROM pg_constraint c "
            "JOIN pg_class r ON r.oid = c.conrelid "
            "WHERE r.relname = 'listing' AND c.contype = 'f'"
        ).fetchall()
    }
    assert referenced == {"source", "admin_unit"}


def test_quarantine_always_states_a_reason(conn) -> None:
    """V10: a quarantined record without a reason is a record nobody can act on."""
    nullable = conn.execute(
        "SELECT is_nullable FROM information_schema.columns "
        "WHERE table_name = 'listing_quarantine' AND column_name = 'reason'"
    ).fetchone()[0]
    assert nullable == "NO"


def test_every_expected_table_exists(conn) -> None:
    """Equality, not containment. A stray table is as much a finding as a
    missing one, because it means a migration did something unintended."""
    present = {
        row[0]
        for row in conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
        ).fetchall()
    }
    postgis_owned = {"spatial_ref_sys"}
    tooling = {"alembic_version"}
    expected = {
        "source",
        "admin_unit",
        "anchor",
        "raw_document",
        "listing",
        "listing_snapshot",
        "notice",
        "plot_cluster",
        "listing_quarantine",
        "transaction",
        "metric_unit_month",
        "coverage_snapshot",
        "assertion_run",
        # Added by 0004, with the estimator. The log cannot be backfilled, so it
        # ships with the thing it records rather than after it.
        "valuation_log",
        "valuation_exclusion",
    }
    assert present - postgis_owned - tooling == expected
