"""S10 — the interaction rules of `21` §3 and §7.1, as predicates over a tree.

Each rule gets two trees: one the builders produce, and one built by hand that
breaks the rule. A rule tested only against correct input is not tested — the
predicate could return an empty tuple for every input and every assertion would
still pass. The hand-built trees are the teeth.

The hand-built trees live here rather than in a fixture package because they are
arguments in a test, not data anyone reuses: each one differs from the passing
tree in exactly the way its rule forbids, and reading the pair side by side is
the point.
"""

from __future__ import annotations

import datetime
import pathlib
from decimal import Decimal

import pytest

from dzialki.render.absence import ABSENCE_REASONS, render_absence, render_unknown
from dzialki.render.contract import RenderNode, nodes_by_role, walk
from dzialki.render.errors import (
    BareAggregateError,
    IllegalPriceCombinationError,
    UnknownAbsenceReasonError,
    UnlabelledAggregateError,
    UnlabelledPriceError,
)
from dzialki.render.format import Formatter
from dzialki.render.honesty import (
    HONESTY_CHECKS,
    HonestyContext,
    check_all,
)
from dzialki.render.price import (
    KIND_LABELS,
    LEGAL_PRICE_PAIRS,
    TYPE_LABELS,
    render_price,
)
from dzialki.render.screen import ScreenPayload, assemble_plot_check
from dzialki.render.state import (
    Comparable,
    Payload,
    RenderConfig,
    render_config_from_params,
)

pytestmark = [pytest.mark.unit]

NOW = datetime.date(2026, 8, 8)


@pytest.fixture
def config(repo_root: pathlib.Path) -> RenderConfig:
    from dzialki.config import load_params

    return render_config_from_params(
        load_params(repo_root / "config" / "params.yml"),
        out_of_depth_min_comparables=4,
        wide_spread_ratio=Decimal("0.60"),
        staleness_threshold_days=7,
        method_version="cmp-2026.08.1",
    )


@pytest.fixture
def formatter(config: RenderConfig) -> Formatter:
    return Formatter(thousands_sep=config.thousands_sep)


@pytest.fixture
def context(config: RenderConfig) -> HonestyContext:
    return HonestyContext(config=config, now=NOW)


def comparables(count: int) -> tuple[Comparable, ...]:
    return tuple(
        Comparable(
            comparable_id=f"cmp_{index:04d}",
            price_per_m2=Decimal(112 + index),
            area_m2=2800 + index,
            gmina="Skierniewice",
            listed_on=datetime.date(2026, 6, 12),
            price_type="offering",
            price_kind="asking",
        )
        for index in range(1, count + 1)
    )


def subject_payload() -> Payload:
    return Payload(
        gmina="Skierniewice",
        teryt="1015042",
        as_of=NOW,
        sources=("portal_a",),
        price_type="offering",
        price_kind="asking",
        area_m2=3200,
        price_pln=454400,
        price_per_m2=Decimal(142),
        n=23,
    )


def flow_payload(**changes) -> Payload:
    base = Payload(
        n=23,
        median=Decimal(118),
        low=Decimal(96),
        high=Decimal(141),
        basis="flow",
        gmina="Skierniewice",
        teryt="1015042",
        as_of=datetime.date(2026, 8, 1),
        sources=("portal_a", "portal_b"),
        price_type="offering",
        price_kind="asking",
        area_m2=3200,
        price_per_m2=Decimal(142),
    )
    import dataclasses

    return dataclasses.replace(base, **changes)


def stock_payload(**changes) -> Payload:
    return flow_payload(
        **{
            "n": 61,
            "median": Decimal(127),
            "low": Decimal(99),
            "high": Decimal(168),
            "basis": "stock",
            **changes,
        }
    )


def gus_payload(**changes) -> Payload:
    return flow_payload(
        **{
            "n": 41,
            "median": Decimal(104),
            "low": None,
            "high": None,
            "spread_published": False,
            "basis": "gus_powiat",
            "powiat": "skierniewicki",
            "quarter": (2025, 4),
            "as_of": datetime.date(2025, 12, 31),
            "sources": ("gus_bdl",),
            "price_type": "sales",
            "price_kind": "transaction",
            **changes,
        }
    )


def screen_payload(**changes) -> ScreenPayload:
    base = ScreenPayload(
        subject_id="subj_0001",
        subject=subject_payload(),
        flow=flow_payload(),
        stock=stock_payload(),
        gus=gus_payload(),
        comparables=comparables(23),
        unknown_fields=("buildability", "road_access"),
        stratum_gaps={
            "buildability": Decimal(34),
            "road_access": Decimal(11),
            "utilities": Decimal(4),
        },
    )
    import dataclasses

    return dataclasses.replace(base, **changes)


@pytest.fixture
def screen(config, formatter) -> RenderNode:
    return assemble_plot_check(
        screen_payload(), config=config, formatter=formatter, now=NOW
    )


def block(payload, config, formatter, now=NOW) -> RenderNode:
    from dzialki.render.aggregate import render_aggregate_block

    return render_aggregate_block(payload, config=config, formatter=formatter, now=now)


def leaf(role, text, prominence="equal", disclosure="always", **meta) -> RenderNode:
    return RenderNode(
        role=role,
        text=text,
        prominence=prominence,
        disclosure=disclosure,
        meta=meta,
    )


def rules_broken(violations) -> list[str]:
    return sorted({violation.rule for violation in violations})


# --- the check set itself --------------------------------------------------


def test_every_rule_this_stage_carries_has_a_check() -> None:
    assert tuple(HONESTY_CHECKS) == (
        "U1",
        "U1a",
        "U2",
        "U3",
        "U4",
        "U5",
        "U6",
        "U7",
        "U8",
        "U9",
        "U10",
        "U11",
        "U13",
        "U14",
    )


def test_the_assembled_screen_breaks_no_rule(screen, context) -> None:
    assert check_all(screen, context) == ()


# --- U1 — no aggregate without n and range, at equal prominence ------------


def test_u1_passes_on_a_block_that_carries_its_value_its_n_and_its_spread(
    config, formatter, context
) -> None:
    tree = block(flow_payload(), config, formatter)
    roles = [child.role for child in tree.children]
    assert roles.count("value") == 1
    assert roles.count("sample_size") == 1
    assert roles.count("spread") == 1
    assert HONESTY_CHECKS["U1"](tree, context) == ()


def test_u1_fails_when_the_range_sits_in_a_hover_container(context) -> None:
    """The observation V35 names. The spread's own disclosure reads ``always``
    in both trees; only the chain sees the container above it."""
    dishonest = RenderNode(
        role="aggregate_block",
        text="Podobne oferty (przepływ, ostatnie 90 dni)",
        prominence="primary",
        disclosure="always",
        children=(
            leaf("value", "mediana 118 zł/m²"),
            RenderNode(
                role="section",
                text="szczegóły",
                prominence="secondary",
                disclosure="hover",
                children=(
                    leaf("spread", "zakres międzykwartylowy 96–141"),
                    leaf("sample_size", "n = 23"),
                ),
            ),
        ),
        meta={"n": 23, "median": Decimal(118)},
    )
    violations = HONESTY_CHECKS["U1"](dishonest, context)
    assert rules_broken(violations) == ["U1"]
    assert "hover" in " ".join(violation.detail for violation in violations)


def test_u1_fails_when_the_range_is_demoted_to_secondary(context) -> None:
    dishonest = RenderNode(
        role="aggregate_block",
        text="Podobne oferty (przepływ, ostatnie 90 dni)",
        prominence="primary",
        disclosure="always",
        children=(
            leaf("value", "mediana 118 zł/m²"),
            leaf("spread", "zakres międzykwartylowy 96–141", "secondary"),
            leaf("sample_size", "n = 23"),
        ),
        meta={"n": 23, "median": Decimal(118)},
    )
    assert rules_broken(HONESTY_CHECKS["U1"](dishonest, context)) == ["U1"]


def test_u1_fails_when_the_value_is_promoted_above_its_qualifiers(context) -> None:
    """A headline with a footnote is arithmetically identical and reads
    differently. `primary` belongs on the block, never on the value inside it."""
    dishonest = RenderNode(
        role="aggregate_block",
        text="Podobne oferty (przepływ, ostatnie 90 dni)",
        prominence="primary",
        disclosure="always",
        children=(
            leaf("value", "mediana 118 zł/m²", "primary"),
            leaf("spread", "zakres międzykwartylowy 96–141"),
            leaf("sample_size", "n = 23"),
        ),
        meta={"n": 23, "median": Decimal(118)},
    )
    assert rules_broken(HONESTY_CHECKS["U1"](dishonest, context)) == ["U1"]


def test_u1_fails_on_a_bare_aggregate_built_by_hand(context) -> None:
    """The builder refuses this payload, so the tree can only be hand-built.
    That is exactly what proves the sweep would catch a component bypassing the
    builder."""
    dishonest = RenderNode(
        role="aggregate_block",
        text="Podobne oferty (przepływ, ostatnie 90 dni)",
        prominence="primary",
        disclosure="always",
        children=(leaf("value", "mediana 118 zł/m²"),),
        meta={"median": Decimal(118)},
    )
    assert rules_broken(HONESTY_CHECKS["U1"](dishonest, context)) == ["U1"]


def test_the_builder_refuses_a_payload_with_no_sample_size(config, formatter) -> None:
    with pytest.raises(BareAggregateError) as caught:
        block(flow_payload(n=None), config, formatter)
    assert "n" in str(caught.value)


def test_the_builder_refuses_a_payload_with_no_range(config, formatter) -> None:
    with pytest.raises(BareAggregateError) as caught:
        block(flow_payload(low=None), config, formatter)
    assert "range" in str(caught.value)


def test_the_builder_refuses_a_payload_with_no_basis(config, formatter) -> None:
    with pytest.raises(UnlabelledAggregateError):
        block(flow_payload(basis=None), config, formatter)


@pytest.mark.parametrize(
    "n,kind,text",
    [
        (3, "min_max", "zakres 96–141"),
        (4, "min_max", "zakres 96–141"),
        (5, "iqr", "zakres międzykwartylowy 96–141"),
        (6, "iqr", "zakres międzykwartylowy 96–141"),
        (23, "iqr", "zakres międzykwartylowy 96–141"),
    ],
)
def test_the_spread_kind_follows_the_sample_size(
    config, formatter, n, kind, text
) -> None:
    """D100: the interquartile range is named in full, because the short word
    does not say which range it is. The min-max range keeps the short word,
    which is a different range and not renamed."""
    tree = block(flow_payload(n=n), config, formatter)
    spread = nodes_by_role(tree, "spread")[0]
    assert spread.meta["range"]["kind"] == kind
    assert spread.text == text


def test_an_interquartile_range_is_never_labelled_zakres_alone(
    config, formatter
) -> None:
    spread = nodes_by_role(block(flow_payload(), config, formatter), "spread")[0]
    assert spread.text.startswith("zakres międzykwartylowy")
    for forbidden in ("IQR", "rozstęp ćwiartkowy", "interquartile range"):
        assert forbidden not in spread.text


# --- U1a — a source with no spread says so in words (D69) ------------------


def test_u1a_renders_the_unavailable_text_and_never_raises(
    config, formatter, context
) -> None:
    tree = block(gus_payload(), config, formatter)
    spread = nodes_by_role(tree, "spread")[0]
    assert spread.text == "zakres niedostępny — GUS publikuje tylko średnią"
    assert spread.meta["range"] == {"low": None, "high": None, "kind": "unavailable"}
    assert spread.prominence == "equal"
    assert spread.disclosure == "always"
    assert HONESTY_CHECKS["U1a"](tree, context) == ()
    assert HONESTY_CHECKS["U1"](tree, context) == ()


def test_u1a_fails_when_the_unavailable_spread_renders_empty(context) -> None:
    """A missing range line reads as "no uncertainty". GUS is the case that
    forces the rule, so the empty string is the failure to catch."""
    dishonest = RenderNode(
        role="aggregate_block",
        text="Ceny transakcyjne · powiat skierniewicki · GUS 2025Q4",
        prominence="primary",
        disclosure="always",
        children=(
            leaf("value", "średnia 104 zł/m²"),
            leaf(
                "spread",
                "",
                range={"low": None, "high": None, "kind": "unavailable"},
            ),
            leaf("sample_size", "n = 41"),
        ),
        meta={"n": 41, "median": Decimal(104)},
    )
    assert rules_broken(HONESTY_CHECKS["U1a"](dishonest, context)) == ["U1a"]


def test_u1a_fails_when_the_unavailable_spread_node_is_dropped(context) -> None:
    dishonest = RenderNode(
        role="aggregate_block",
        text="Ceny transakcyjne · powiat skierniewicki · GUS 2025Q4",
        prominence="primary",
        disclosure="always",
        children=(
            leaf("value", "średnia 104 zł/m²"),
            leaf("sample_size", "n = 41"),
        ),
        meta={
            "n": 41,
            "median": Decimal(104),
            "range": {"low": None, "high": None, "kind": "unavailable"},
        },
    )
    assert rules_broken(HONESTY_CHECKS["U1a"](dishonest, context)) == ["U1a"]


# --- U2 — every price shows type and kind ----------------------------------


def test_the_label_tables_are_exactly_the_ones_d68_settles() -> None:
    assert TYPE_LABELS == {
        "offering": "cena ofertowa",
        "sales": "cena transakcyjna",
    }
    assert KIND_LABELS == {
        "asking": "oferta",
        "auction_start": "cena wywoławcza",
        "tender": "cena przetargowa",
        "transaction": "transakcja",
    }
    assert LEGAL_PRICE_PAIRS == (
        ("offering", "asking"),
        ("offering", "auction_start"),
        ("offering", "tender"),
        ("sales", "transaction"),
    )


@pytest.mark.parametrize("price_type", ("offering", "sales"))
@pytest.mark.parametrize(
    "price_kind", ("asking", "auction_start", "tender", "transaction")
)
def test_the_price_pair_matrix_is_exhaustive(
    config, formatter, price_type, price_kind
) -> None:
    """Eight pairs, four legal. D68 makes `transaction` legal only with sales,
    and the three offering kinds legal only with offering."""
    legal = (price_type, price_kind) in LEGAL_PRICE_PAIRS
    if legal:
        node = render_price(
            Decimal(142),
            price_type=price_type,
            price_kind=price_kind,
            formatter=formatter,
        )
        assert node[0].meta["price_type"] == price_type
    else:
        with pytest.raises(IllegalPriceCombinationError) as caught:
            render_price(
                Decimal(142),
                price_type=price_type,
                price_kind=price_kind,
                formatter=formatter,
            )
        assert price_kind in str(caught.value)


@pytest.mark.parametrize("missing", ("price_type", "price_kind"))
def test_a_price_without_its_type_or_its_kind_is_refused(formatter, missing) -> None:
    kwargs = {"price_type": "offering", "price_kind": "asking"}
    kwargs[missing] = None
    with pytest.raises(UnlabelledPriceError) as caught:
        render_price(Decimal(142), formatter=formatter, **kwargs)
    assert missing in str(caught.value)


def test_u2_passes_on_a_price_with_both_labels_beside_it(
    config, formatter, context
) -> None:
    tree = RenderNode(
        role="header",
        text="3 200 m² · gmina Skierniewice · 142 zł/m²",
        prominence="primary",
        disclosure="always",
        children=render_price(
            Decimal(142),
            price_type="offering",
            price_kind="asking",
            formatter=formatter,
        ),
    )
    assert [child.text for child in tree.children] == [
        "142 zł/m²",
        "cena ofertowa",
        "oferta",
    ]
    assert HONESTY_CHECKS["U2"](tree, context) == ()


def test_u2_fails_when_the_kind_label_is_missing(context) -> None:
    dishonest = RenderNode(
        role="header",
        text="3 200 m² · gmina Skierniewice · 142 zł/m²",
        prominence="primary",
        disclosure="always",
        children=(
            leaf("price", "142 zł/m²", price_type="offering"),
            leaf("price_type_label", "cena ofertowa", price_type="offering"),
        ),
    )
    assert rules_broken(HONESTY_CHECKS["U2"](dishonest, context)) == ["U2"]


def test_u2_fails_when_the_labels_hide_behind_a_hover(context) -> None:
    dishonest = RenderNode(
        role="header",
        text="3 200 m² · gmina Skierniewice · 142 zł/m²",
        prominence="primary",
        disclosure="hover",
        children=(
            leaf("price", "142 zł/m²", price_type="offering", price_kind="asking"),
            leaf("price_type_label", "cena ofertowa", price_type="offering"),
            leaf("price_kind_label", "oferta", price_kind="asking"),
        ),
    )
    assert rules_broken(HONESTY_CHECKS["U2"](dishonest, context)) == ["U2"]


def test_offering_and_sales_never_share_one_block(screen) -> None:
    blocks = nodes_by_role(screen, "aggregate_block")
    types = [node.meta["price_type"] for node in blocks]
    assert types == ["offering", "offering", "sales"]
    for node in blocks:
        kinds = {
            child.meta["price_kind"]
            for child in node.children
            if child.role == "price_kind_label"
        }
        assert len(kinds) == 1


# --- U3 — flow and stock both shown, flow first ----------------------------


def test_u3_passes_on_the_assembled_screen(screen, context) -> None:
    from dzialki.render.contract import index_of

    blocks = nodes_by_role(screen, "aggregate_block")
    flow = next(node for node in blocks if node.meta["basis"] == "flow")
    stock = next(node for node in blocks if node.meta["basis"] == "stock")
    assert index_of(screen, flow) < index_of(screen, stock)
    assert flow.text == "Podobne oferty (przepływ, ostatnie 90 dni)"
    assert stock.text == "Podobne oferty (stan, wszystkie aktywne)"
    assert HONESTY_CHECKS["U3"](screen, context) == ()


def test_the_gap_between_stock_and_flow_is_described_never_averaged(screen) -> None:
    forbidden = (Decimal(118) + Decimal(127)) / 2
    for node in walk(screen):
        assert node.meta.get("median") != forbidden
    assert "122,5" not in " ".join(node.text for node in walk(screen))
    gap = [node for node in walk(screen) if node.meta.get("field") == "stock_flow_gap"]
    assert [node.text for node in gap] == ["stan wyżej niż przepływ"]


def test_u3_fails_when_the_stock_block_renders_first(context) -> None:
    dishonest = RenderNode(
        role="section",
        text="Sprawdzenie działki",
        prominence="primary",
        disclosure="always",
        children=(
            leaf(
                "aggregate_block",
                "Podobne oferty (stan, wszystkie aktywne)",
                basis="stock",
            ),
            leaf(
                "aggregate_block",
                "Podobne oferty (przepływ, ostatnie 90 dni)",
                basis="flow",
            ),
        ),
    )
    assert rules_broken(HONESTY_CHECKS["U3"](dishonest, context)) == ["U3"]


def test_u3_fails_when_the_two_medians_are_blended(context) -> None:
    dishonest = RenderNode(
        role="section",
        text="Sprawdzenie działki",
        prominence="primary",
        disclosure="always",
        children=(
            RenderNode(
                role="aggregate_block",
                text="Podobne oferty",
                prominence="primary",
                disclosure="always",
                children=(leaf("value", "mediana 122,5 zł/m²"),),
                meta={"basis": "flow", "median": Decimal("122.5")},
            ),
        ),
    )
    assert rules_broken(HONESTY_CHECKS["U3"](dishonest, context)) == ["U3"]


# --- U4 — the flow window sits beside every flow figure --------------------


def test_u4_passes_and_names_the_window_the_configuration_holds(
    config, formatter, context
) -> None:
    tree = block(flow_payload(), config, formatter)
    label = nodes_by_role(tree, "flow_window_label")[0]
    assert label.text == "ostatnie 90 dni"
    assert label.meta["flow_window_days"] == config.flow_window_days
    assert HONESTY_CHECKS["U4"](tree, context) == ()


def test_u4_fails_when_a_flow_figure_carries_no_window(context) -> None:
    dishonest = RenderNode(
        role="aggregate_block",
        text="Podobne oferty (przepływ)",
        prominence="primary",
        disclosure="always",
        children=(leaf("value", "mediana 118 zł/m²", basis="flow"),),
        meta={"basis": "flow", "n": 23},
    )
    assert rules_broken(HONESTY_CHECKS["U4"](dishonest, context)) == ["U4"]


# --- U5 — the verdict is collapsed, and last (D98) -------------------------


def test_u5_passes_on_a_verdict_that_is_shut(screen, context) -> None:
    verdict = nodes_by_role(screen, "verdict")[0]
    assert verdict.text == "WERDYKT"
    assert verdict.disclosure == "expander"
    assert verdict.meta["expanded"] is False
    assert HONESTY_CHECKS["U5"](screen, context) == ()


def test_the_expanded_verdict_is_phrased_against_the_range(screen) -> None:
    verdict = nodes_by_role(screen, "verdict")[0]
    conclusion = nodes_by_role(verdict, "value")[0]
    assert conclusion.text == "Powyżej górnej granicy zakresu przepływu (96–141)"
    basis = nodes_by_role(verdict, "basis")[0]
    assert basis.text == (
        "Podstawa: 23 oferty, ta sama gmina, 1 600–4 800 m², ostatnie 90 dni"
    )


@pytest.mark.parametrize(
    "price,expected",
    [
        (Decimal(142), "Powyżej górnej granicy zakresu przepływu (96–141)"),
        (Decimal(80), "Poniżej dolnej granicy zakresu przepływu (96–141)"),
        (Decimal(118), "W zakresie przepływu (96–141)"),
    ],
)
def test_the_verdict_takes_one_of_three_sanctioned_forms(
    config, formatter, price, expected
) -> None:
    import dataclasses

    payload = screen_payload(
        subject=dataclasses.replace(subject_payload(), price_per_m2=price),
    )
    tree = assemble_plot_check(payload, config=config, formatter=formatter, now=NOW)
    verdict = nodes_by_role(tree, "verdict")[0]
    assert nodes_by_role(verdict, "value")[0].text == expected


def test_the_verdict_never_expresses_a_percentage_off_a_midpoint(screen) -> None:
    verdict = nodes_by_role(screen, "verdict")[0]
    for node in walk(verdict):
        assert "%" not in node.text
        assert "od mediany" not in node.text


def test_u5_fails_when_the_collapsed_verdict_leaks_its_conclusion(context) -> None:
    dishonest = RenderNode(
        role="section",
        text="Sprawdzenie działki",
        prominence="primary",
        disclosure="always",
        children=(
            leaf(
                "verdict",
                "WERDYKT — powyżej górnej granicy zakresu przepływu (96–141)",
                "primary",
                "always",
                expanded=True,
            ),
        ),
    )
    assert rules_broken(HONESTY_CHECKS["U5"](dishonest, context)) == ["U5"]


def test_u14_fails_when_a_warning_renders_after_the_verdict(context) -> None:
    """D98's stronger form. The pair assertion alone would pass this screen."""
    dishonest = RenderNode(
        role="section",
        text="Sprawdzenie działki",
        prominence="primary",
        disclosure="always",
        children=(
            leaf("comparable_set", "Podobne oferty — 23", n=23),
            leaf("verdict", "WERDYKT", "secondary", "expander", expanded=False),
            leaf(
                "unknown",
                "brak danych planistycznych — sprawdź w gminie",
                field="buildability",
                tone="warning",
            ),
        ),
    )
    assert rules_broken(HONESTY_CHECKS["U14"](dishonest, context)) == ["U14"]


def test_u14_passes_on_the_assembled_screen(screen, context) -> None:
    from dzialki.render.contract import index_of, top_level_nodes

    comparable_set = nodes_by_role(screen, "comparable_set")[0]
    verdict = nodes_by_role(screen, "verdict")[0]
    assert index_of(screen, comparable_set) < index_of(screen, verdict)
    assert top_level_nodes(screen)[-1] is verdict
    assert HONESTY_CHECKS["U14"](screen, context) == ()


def test_u14_fails_when_the_verdict_precedes_the_comparable_set(context) -> None:
    dishonest = RenderNode(
        role="section",
        text="Sprawdzenie działki",
        prominence="primary",
        disclosure="always",
        children=(
            leaf("verdict", "WERDYKT", "secondary", "expander", expanded=False),
            leaf("comparable_set", "Podobne oferty — 23", n=23),
        ),
    )
    assert rules_broken(HONESTY_CHECKS["U14"](dishonest, context)) == ["U14"]


def test_every_comparable_carries_its_price_area_gmina_date_and_control(
    screen,
) -> None:
    import re

    listed = nodes_by_role(screen, "comparable")
    assert len(listed) == 23
    pattern = re.compile(
        "^\\d+\u00a0zł/m² · [\\d\u00a0]+\u00a0m² · gmina .+ · \\d\\d\\.\\d\\d\\.\\d{4}$"
    )
    for node in listed:
        assert pattern.match(node.text), node.text
        assert node.meta["exclude_control"] == {
            "comparable_id": node.meta["comparable_id"],
            "label": "nie pasuje",
        }
        assert [child.role for child in node.children] == [
            "price_type_label",
            "price_kind_label",
        ]


# --- U6 — unknown renders as explicit Polish text --------------------------


@pytest.mark.parametrize(
    "field,expected",
    [
        ("buildability", "brak danych planistycznych — sprawdź w gminie"),
        ("road_access", "brak danych o dojeździe — sprawdź w gminie"),
        ("utilities", "brak danych o mediach — sprawdź w gminie"),
        ("soil_class", "brak danych o klasie gruntu — sprawdź w gminie"),
    ],
)
def test_each_unknown_attribute_renders_its_own_sentence(field, expected) -> None:
    node = render_unknown(field)
    assert node.text == expected
    assert node.meta["field"] == field
    assert node.meta["tone"] == "warning"
    assert node.prominence == "equal"


def test_three_unknowns_never_collapse_into_one_line() -> None:
    texts = [
        render_unknown(field).text
        for field in ("buildability", "road_access", "utilities", "soil_class")
    ]
    assert len(set(texts)) == 4


def test_u6_fails_on_a_dash_and_on_a_python_repr(context) -> None:
    for leaked in ("—", "None", "", "n/a"):
        dishonest = RenderNode(
            role="section",
            text="Sprawdzenie działki",
            prominence="primary",
            disclosure="always",
            children=(
                leaf("unknown", leaked, "secondary", field="buildability", tone="ok"),
            ),
        )
        assert rules_broken(HONESTY_CHECKS["U6"](dishonest, context)) == ["U6"], leaked


def test_u6_passes_on_the_assembled_screen(screen, context) -> None:
    assert HONESTY_CHECKS["U6"](screen, context) == ()


def test_an_advert_claim_never_fills_in_an_unknown(config, formatter) -> None:
    """FR-17. `zoning_claim` and `buildability` are different columns and are
    never reconciled, so the claim renders beside the unknown, not instead."""
    payload = screen_payload(zoning_claim="budowlana")
    tree = assemble_plot_check(payload, config=config, formatter=formatter, now=NOW)
    unknowns = [
        node.text
        for node in nodes_by_role(tree, "unknown")
        if node.meta.get("field") == "buildability"
    ]
    assert "brak danych planistycznych — sprawdź w gminie" in unknowns
    claim = [node for node in walk(tree) if node.meta.get("field") == "zoning_claim"]
    assert [node.text for node in claim] == ["budowlana"]
    assert claim[0].children[0].text == "z ogłoszenia"


# --- U7 — the four absence reasons are distinguished -----------------------


def test_the_four_absence_reasons_render_pairwise_distinct_text() -> None:
    texts = [render_absence(reason).text for reason in ABSENCE_REASONS]
    actions = [render_absence(reason).children[0].text for reason in ABSENCE_REASONS]
    assert texts == [
        "Brak danych — tej gminy jeszcze nie zebraliśmy",
        "Brak danych — w tej gminie nie ma ofert",
        "Brak danych — ta gmina jest poza zasięgiem narzędzia",
        "Brak danych — za mało podobnych ofert",
    ]
    assert actions == [
        "jeszcze nie zebraliśmy — sprawdź później",
        "brak ofert w tej gminie",
        "poza zasięgiem narzędzia",
        "za mało podobnych ofert, żeby porównać",
    ]
    assert len(set(texts)) == 4
    assert len(set(actions)) == 4


def test_an_absence_never_renders_as_zero_or_as_a_number() -> None:
    for reason in ABSENCE_REASONS:
        assert nodes_by_role(render_absence(reason), "value") == ()


def test_a_reason_outside_the_enum_raises_rather_than_falling_back() -> None:
    """Without this the four collapse back into one the first time a fifth
    appears."""
    with pytest.raises(UnknownAbsenceReasonError) as caught:
        render_absence("no_sales_data_at_all")
    assert "no_sales_data_at_all" in str(caught.value)


def test_u7_fails_when_two_reasons_share_one_string(context) -> None:
    dishonest = RenderNode(
        role="section",
        text="Sprawdzenie działki",
        prominence="primary",
        disclosure="always",
        children=(
            leaf(
                "absence", "Brak danych", absence_reason="no_listings", tone="warning"
            ),
            leaf(
                "absence",
                "Brak danych",
                absence_reason="not_yet_crawled",
                tone="warning",
            ),
        ),
    )
    assert rules_broken(HONESTY_CHECKS["U7"](dishonest, context)) == ["U7"]


def test_u7_passes_when_two_reasons_render_their_own_string(context) -> None:
    honest = RenderNode(
        role="section",
        text="Sprawdzenie działki",
        prominence="primary",
        disclosure="always",
        children=(render_absence("no_listings"), render_absence("not_yet_crawled")),
    )
    assert HONESTY_CHECKS["U7"](honest, context) == ()


# --- U8 — stale data shows its age on the number ---------------------------


def test_u8_puts_the_age_beside_the_value(config, formatter, context) -> None:
    tree = block(flow_payload(as_of=datetime.date(2026, 7, 27)), config, formatter)
    staleness = nodes_by_role(tree, "staleness")[0]
    assert staleness.text == "dane sprzed 12 dni · ostatnie pobranie 27.07.2026"
    assert HONESTY_CHECKS["U8"](tree, context) == ()


def test_u8_fails_when_the_age_moves_into_a_page_banner(context) -> None:
    dishonest = RenderNode(
        role="section",
        text="Sprawdzenie działki",
        prominence="primary",
        disclosure="always",
        children=(
            RenderNode(
                role="aggregate_block",
                text="Podobne oferty (przepływ, ostatnie 90 dni)",
                prominence="primary",
                disclosure="always",
                children=(
                    leaf(
                        "value",
                        "mediana 118 zł/m²",
                        as_of=datetime.date(2026, 7, 27),
                    ),
                ),
                meta={"basis": "flow", "n": 23},
            ),
        ),
    )
    with_banner = RenderNode(
        role=dishonest.role,
        text=dishonest.text,
        prominence=dishonest.prominence,
        disclosure=dishonest.disclosure,
        children=(
            leaf("staleness", "dane mogą być nieaktualne", "secondary"),
            *dishonest.children,
        ),
    )
    assert rules_broken(HONESTY_CHECKS["U8"](with_banner, context)) == ["U8"]


def test_fresh_data_renders_no_staleness_node(config, formatter, context) -> None:
    """Seven days is not more than seven. A `>=` implementation fails here."""
    tree = block(flow_payload(as_of=datetime.date(2026, 8, 1)), config, formatter)
    assert nodes_by_role(tree, "staleness") == ()
    assert HONESTY_CHECKS["U8"](tree, context) == ()


# --- U9 — every number is one interaction from its source ------------------


def test_u9_puts_provenance_behind_exactly_one_expander(
    config, formatter, context
) -> None:
    tree = block(flow_payload(), config, formatter)
    provenance = nodes_by_role(tree, "provenance")[0]
    assert provenance.text == "Źródło i metoda"
    assert [child.text for child in provenance.children] == [
        "Źródło: portal_a, portal_b",
        "Stan na: 01.08.2026",
        "Metoda: cmp-2026.08.1",
        "Liczba obserwacji: n = 23",
    ]
    assert HONESTY_CHECKS["U9"](tree, context) == ()


def test_u9_fails_when_provenance_sits_two_expanders_deep(context) -> None:
    dishonest = RenderNode(
        role="aggregate_block",
        text="Podobne oferty (przepływ, ostatnie 90 dni)",
        prominence="primary",
        disclosure="always",
        children=(
            RenderNode(
                role="section",
                text="Szczegóły",
                prominence="secondary",
                disclosure="expander",
                children=(
                    RenderNode(
                        role="section",
                        text="Metoda",
                        prominence="secondary",
                        disclosure="expander",
                        children=(leaf("provenance", "Źródło: portal_a, portal_b"),),
                    ),
                ),
            ),
        ),
    )
    assert rules_broken(HONESTY_CHECKS["U9"](dishonest, context)) == ["U9"]


def test_u9_fails_when_provenance_is_reachable_on_hover_only(context) -> None:
    """Hover is unreachable on a touch device and cannot be screenshotted."""
    dishonest = RenderNode(
        role="aggregate_block",
        text="Podobne oferty (przepływ, ostatnie 90 dni)",
        prominence="primary",
        disclosure="always",
        children=(
            RenderNode(
                role="section",
                text="Szczegóły",
                prominence="secondary",
                disclosure="hover",
                children=(leaf("provenance", "Źródło: portal_a, portal_b"),),
            ),
        ),
    )
    assert rules_broken(HONESTY_CHECKS["U9"](dishonest, context)) == ["U9"]


def test_u9_fails_when_a_value_carries_no_provenance_handle(context) -> None:
    dishonest = RenderNode(
        role="aggregate_block",
        text="Podobne oferty (przepływ, ostatnie 90 dni)",
        prominence="primary",
        disclosure="always",
        children=(leaf("value", "mediana 118 zł/m²"),),
    )
    assert rules_broken(HONESTY_CHECKS["U9"](dishonest, context)) == ["U9"]


def test_provenance_lists_every_contributing_source(config, formatter) -> None:
    tree = block(
        flow_payload(sources=("portal_a", "portal_b", "kowr")), config, formatter
    )
    provenance = nodes_by_role(tree, "provenance")[0]
    assert provenance.children[0].text == "Źródło: portal_a, portal_b, kowr"


# --- U10 — uncertainty stated in words -------------------------------------


@pytest.mark.parametrize(
    "n,low,high,expected",
    [
        (
            4,
            Decimal(110),
            Decimal(130),
            "Mało podobnych ofert — wynik orientacyjny",
        ),
        (4, Decimal(61), Decimal(240), "Zakres szeroki — mało podobnych ofert"),
        (23, Decimal(96), Decimal(141), None),
        (
            23,
            Decimal(62),
            Decimal(160),
            "Zakres szeroki — ceny w tej gminie bardzo się różnią",
        ),
        (61, Decimal(118), Decimal(136), None),
        (
            61,
            Decimal(62),
            Decimal(160),
            "Zakres szeroki — ceny w tej gminie bardzo się różnią",
        ),
    ],
)
def test_the_note_wording_comes_from_a_closed_vocabulary(
    config, formatter, n, low, high, expected
) -> None:
    median = Decimal(120) if high == Decimal(160) else Decimal(118)
    tree = block(
        flow_payload(n=n, low=low, high=high, median=median), config, formatter
    )
    notes = [node.text for node in nodes_by_role(tree, "uncertainty_note")]
    assert notes == ([] if expected is None else [expected])


def test_a_source_with_no_spread_gets_its_own_worded_note(config, formatter) -> None:
    tree = block(gus_payload(), config, formatter)
    notes = [node.text for node in nodes_by_role(tree, "uncertainty_note")]
    assert notes == ["Nie znamy rozrzutu — GUS publikuje tylko średnią"]


def test_the_note_is_neither_hover_only_nor_secondary(config, formatter) -> None:
    tree = block(
        flow_payload(n=4, low=Decimal(61), high=Decimal(240)), config, formatter
    )
    note = nodes_by_role(tree, "uncertainty_note")[0]
    assert note.disclosure == "always"
    assert note.prominence == "equal"
    assert note.meta["tone"] == "warning"


def test_u10_fails_on_a_thin_block_that_renders_numbers_only(context) -> None:
    """Numerically correct, and exactly the failure U10 names."""
    dishonest = RenderNode(
        role="aggregate_block",
        text="Podobne oferty (przepływ, ostatnie 90 dni)",
        prominence="primary",
        disclosure="always",
        children=(
            leaf("flow_window_label", "ostatnie 90 dni", flow_window_days=90),
            leaf("value", "mediana 118 zł/m²"),
            leaf("spread", "zakres 61–240"),
            leaf("sample_size", "n = 4"),
        ),
        meta={
            "basis": "flow",
            "n": 4,
            "median": Decimal(118),
            "range": {"low": Decimal(61), "high": Decimal(240), "kind": "min_max"},
        },
    )
    assert rules_broken(HONESTY_CHECKS["U10"](dishonest, context)) == ["U10"]


def test_u10_fails_on_a_note_outside_the_closed_vocabulary(context) -> None:
    dishonest = RenderNode(
        role="aggregate_block",
        text="Podobne oferty (przepływ, ostatnie 90 dni)",
        prominence="primary",
        disclosure="always",
        children=(
            leaf("value", "mediana 118 zł/m²"),
            leaf("spread", "zakres 61–240"),
            leaf("sample_size", "n = 4"),
            leaf("uncertainty_note", "Uwaga, dane mogą być niepełne", tone="warning"),
        ),
        meta={
            "basis": "flow",
            "n": 4,
            "median": Decimal(118),
            "range": {"low": Decimal(61), "high": Decimal(240), "kind": "min_max"},
        },
    )
    assert rules_broken(HONESTY_CHECKS["U10"](dishonest, context)) == ["U10"]


def test_a_tight_and_well_supported_aggregate_gets_no_note(
    config, formatter, context
) -> None:
    """The guard against a note on every aggregate, which would train the reader
    to ignore notes."""
    tree = block(
        flow_payload(n=61, median=Decimal(127), low=Decimal(118), high=Decimal(136)),
        config,
        formatter,
    )
    assert nodes_by_role(tree, "uncertainty_note") == ()
    assert HONESTY_CHECKS["U10"](tree, context) == ()


# --- U11 — the tool volunteers when it is out of its depth -----------------


@pytest.fixture
def thin_screen(config, formatter) -> RenderNode:
    payload = screen_payload(
        flow=flow_payload(
            n=3, median=Decimal(112), low=Decimal(104), high=Decimal(124)
        ),
        stock=stock_payload(n=3),
        comparables=comparables(3),
    )
    return assemble_plot_check(payload, config=config, formatter=formatter, now=NOW)


def test_u11_leads_with_the_notice_below_the_threshold(thin_screen, context) -> None:
    from dzialki.render.contract import top_level_nodes

    first = top_level_nodes(thin_screen)[0]
    assert first.role == "out_of_depth_notice"
    assert first.text == "za mało danych, żeby ocenić — to jest orientacja, nie wycena"
    assert HONESTY_CHECKS["U11"](thin_screen, context) == ()


def test_the_estimate_still_renders_below_the_notice(thin_screen) -> None:
    """Rule 7 — nothing is hidden. The estimate is demoted, not withheld."""
    blocks = nodes_by_role(thin_screen, "aggregate_block")
    flow = next(node for node in blocks if node.meta["basis"] == "flow")
    assert flow.prominence == "secondary"
    assert nodes_by_role(flow, "value")[0].text == "mediana 112 zł/m²"
    assert nodes_by_role(flow, "spread")[0].text == "zakres 104–124"
    assert nodes_by_role(flow, "sample_size")[0].text == "n = 3"


def test_no_confident_band_is_presented_below_the_threshold(thin_screen) -> None:
    for verdict in nodes_by_role(thin_screen, "verdict"):
        assert verdict.prominence != "primary"


def test_the_notice_is_absent_when_the_set_is_adequate(screen, context) -> None:
    assert nodes_by_role(screen, "out_of_depth_notice") == ()
    assert HONESTY_CHECKS["U11"](screen, context) == ()


def test_u11_fails_when_a_confident_verdict_leads_a_thin_screen(context) -> None:
    dishonest = RenderNode(
        role="section",
        text="Sprawdzenie działki",
        prominence="primary",
        disclosure="always",
        children=(
            leaf(
                "verdict",
                "Powyżej górnej granicy zakresu przepływu (104–124)",
                "primary",
                "always",
                expanded=True,
            ),
            leaf("aggregate_block", "Podobne oferty (przepływ, ostatnie 90 dni)", n=3),
        ),
    )
    assert rules_broken(HONESTY_CHECKS["U11"](dishonest, context)) == ["U11"]


def test_silence_is_never_the_thin_rendering(thin_screen) -> None:
    """Silence would read as confidence, which is the rule's whole content."""
    assert nodes_by_role(thin_screen, "out_of_depth_notice") != ()
    blocks = nodes_by_role(thin_screen, "aggregate_block")
    for node in blocks:
        assert nodes_by_role(node, "uncertainty_note") != ()


# --- U13 — show what would change the answer -------------------------------


def test_the_notes_are_derived_from_the_missing_attributes(config, formatter) -> None:
    from dzialki.render.notes import notes_for

    assert [
        note.text for note in notes_for(("buildability",), gmina="Skierniewice")
    ] == ["gdyby ta działka miała plan miejscowy, porównania byłyby inne"]
    assert [
        note.text for note in notes_for(("road_access",), gmina="Skierniewice")
    ] == ["gdyby dojazd był drogą gminną, a nie służebnością, porównania byłyby inne"]
    assert [note.text for note in notes_for(("utilities",), gmina="Skierniewice")] == [
        "gdyby media były na działce, a nie w granicy, porównania byłyby inne"
    ]
    assert notes_for((), gmina="Skierniewice") == ()


def test_each_note_names_a_question_for_the_gmina(screen, context) -> None:
    notes = nodes_by_role(screen, "sensitivity_note")
    assert notes != ()
    for note in notes:
        assert note.meta["action"] == {
            "office": "Urząd Gminy Skierniewice",
            "document": "wypis i wyrys",
        }
    assert HONESTY_CHECKS["U13"](screen, context) == ()


def test_the_notes_are_ordered_by_the_difference_they_would_make(screen) -> None:
    assert [
        note.meta["field"] for note in nodes_by_role(screen, "sensitivity_note")
    ] == [
        "buildability",
        "road_access",
    ]


def test_u13_fails_on_a_constant_caveat_with_no_action(context) -> None:
    dishonest = RenderNode(
        role="section",
        text="Sprawdzenie działki",
        prominence="primary",
        disclosure="always",
        children=(
            leaf(
                "sensitivity_note", "Pamiętaj, że dane mogą być niepełne.", "secondary"
            ),
        ),
    )
    assert rules_broken(HONESTY_CHECKS["U13"](dishonest, context)) == ["U13"]


# --- the disclosure, quoted from the design document -----------------------


def test_the_honest_disclosure_matches_the_paragraph_in_the_design_document(
    repo_root: pathlib.Path, screen
) -> None:
    """`render/` cannot read a file, so it holds the paragraph. This test is
    what stops the held copy drifting from `21` §7.2."""
    from dzialki.render.wording import HONEST_DISCLOSURE

    document = (repo_root / "docs" / "21-v0-ui-and-ux.md").read_text(encoding="utf-8")
    section = document.split("### 7.2 The honest disclosure", 1)[1]
    quoted = [
        line[2:].strip() for line in section.splitlines() if line.startswith("> ")
    ]
    paragraph = " ".join(quoted).strip("*")
    assert paragraph == HONEST_DISCLOSURE
    banners = nodes_by_role(screen, "disclosure_banner")
    assert HONEST_DISCLOSURE in [node.text for node in banners]


def test_the_banner_renders_before_the_verdict(screen) -> None:
    from dzialki.render.contract import index_of

    banner = nodes_by_role(screen, "disclosure_banner")[-1]
    verdict = nodes_by_role(screen, "verdict")[0]
    assert index_of(screen, banner) < index_of(screen, verdict)
