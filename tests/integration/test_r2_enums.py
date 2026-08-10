"""R2.1–R2.3 — the enumerated types exist with exactly the labels decided.

Label order matters for `price_kind`: D65 named the three offering kinds and D68
added the sales one, so the order records which came from which decision.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.needs_db]

EXPECTED = {
    "price_type": ["offering", "sales"],
    # D65 gave the first three, D68 the fourth.
    "price_kind": ["asking", "auction_start", "tender", "transaction"],
    "asset_class": [
        "land_building",
        "land_recreational",
        "land_agricultural",
        "land_forest_other",
        "house",
        "flat",
    ],
    "buildability": ["buildable", "conditional", "agricultural", "unknown"],
    # FR-48: no 'advert'. The violation cannot be written because the value
    # does not exist.
    "buildability_source": ["plan_ogolny", "mpzp", "registry"],
    "location_precision": ["parcel", "address", "pin", "locality", "gmina", "none"],
    "utility_state": ["present", "at_boundary", "absent", "unknown"],
    "road_access": [
        "public_paved",
        "public_unpaved",
        "easement",
        "none",
        "unknown",
    ],
    "unit_level": ["voivodeship", "powiat", "gmina", "obreb"],
    # D69 added 'unavailable' so a source publishing no spread is storable.
    "range_kind": ["iqr", "min_max", "unavailable"],
    "series_kind": ["stock", "flow"],
}


def _labels(conn, type_name: str) -> list[str]:
    return [
        row[0]
        for row in conn.execute(
            "SELECT e.enumlabel FROM pg_enum e "
            "JOIN pg_type t ON t.oid = e.enumtypid "
            "WHERE t.typname = %s ORDER BY e.enumsortorder",
            (type_name,),
        ).fetchall()
    ]


@pytest.mark.parametrize("type_name,labels", sorted(EXPECTED.items()))
def test_enum_has_exactly_the_decided_labels(conn, type_name, labels) -> None:
    assert _labels(conn, type_name) == labels


def test_buildability_source_has_no_advert_label(conn) -> None:
    """FR-48 stated as a non-existent value, so it cannot be inserted by mistake."""
    assert "advert" not in _labels(conn, "buildability_source")
