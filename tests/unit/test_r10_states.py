"""S10.8 — the five states, derived from the payload and never passed in.

Every data-bearing component answers five questions before it answers the
user's: is it still loading, is the data absent, is it thin, is it stale, did it
fail. A component that defines fewer than five states has one that renders as
another, and the one it borrows is almost always ``normal``.

The state is derived (V36). A caller cannot label a thin aggregate as normal,
because no builder takes a state argument.
"""

from __future__ import annotations

import datetime
import inspect
import pathlib
from decimal import Decimal

import pytest

from dzialki.render.contract import nodes_by_role, walk
from dzialki.render.errors import UnknownAbsenceReasonError
from dzialki.render.format import Formatter
from dzialki.render.inventory import (
    COMPONENT_REGISTRY,
    build_component,
    public_builders,
)
from dzialki.render.state import (
    STATES,
    Comparable,
    Payload,
    RenderConfig,
    render_config_from_params,
    staleness_days,
    state_of,
)

pytestmark = [pytest.mark.unit]

NOW = datetime.date(2026, 8, 8)
FIVE_STATES = ("loading", "empty", "thin", "stale", "error")

COMPONENTS = (
    "plot_check_header",
    "flow_aggregate_block",
    "stock_aggregate_block",
    "gus_sales_block",
    "comparable_set",
    "verdict_block",
    "uncertainty_panel",
    "provenance_panel",
)


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


def normal_payload(component: str) -> Payload:
    """The payload every component renders in its ``normal`` state."""
    common = {
        "gmina": "Skierniewice",
        "teryt": "1015042",
        "as_of": datetime.date(2026, 8, 1),
        "sources": ("portal_a", "portal_b"),
        "price_type": "offering",
        "price_kind": "asking",
        "area_m2": 3200,
        "price_pln": 454400,
        "price_per_m2": Decimal(142),
    }
    if component == "flow_aggregate_block":
        return Payload(
            n=23,
            median=Decimal(118),
            low=Decimal(96),
            high=Decimal(141),
            basis="flow",
            **common,
        )
    if component == "stock_aggregate_block":
        return Payload(
            n=61,
            median=Decimal(127),
            low=Decimal(99),
            high=Decimal(168),
            basis="stock",
            **common,
        )
    if component == "gus_sales_block":
        return Payload(
            n=41,
            median=Decimal(104),
            spread_published=False,
            basis="gus_powiat",
            powiat="skierniewicki",
            quarter=(2025, 4),
            **{
                **common,
                "as_of": datetime.date(2025, 12, 31),
                "sources": ("gus_bdl",),
                "price_type": "sales",
                "price_kind": "transaction",
            },
        )
    return Payload(
        n=23,
        median=Decimal(118),
        low=Decimal(96),
        high=Decimal(141),
        basis="flow",
        comparables=comparables(23),
        **common,
    )


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


def payload_for(component: str, state: str) -> Payload:
    base = normal_payload(component)
    if state == "normal":
        return base
    if state == "loading":
        return dataclass_replace(base, pending=True)
    if state == "empty":
        return dataclass_replace(
            base, absent=True, absence_reason=COMPONENT_REGISTRY[component].empty_reason
        )
    if state == "error":
        return dataclass_replace(base, failed=True)
    if state == "thin":
        if component in ("gus_sales_block", "uncertainty_panel"):
            # `thin_n_threshold` is 5 and `out_of_depth_min_comparables` is 4,
            # so n = 3 is both thin and out of depth. The uncertainty panel is
            # the component that must say the second thing.
            return dataclass_replace(base, n=3, comparables=comparables(3))
        return dataclass_replace(
            base,
            n=4,
            median=Decimal(118),
            low=Decimal(61),
            high=Decimal(240),
            comparables=comparables(4),
        )
    if state == "stale":
        return dataclass_replace(base, as_of=datetime.date(2026, 7, 27))
    raise AssertionError(state)


def dataclass_replace(payload: Payload, **changes) -> Payload:
    import dataclasses

    return dataclasses.replace(payload, **changes)


def build(component: str, state: str, config, formatter):
    return build_component(
        component,
        payload_for(component, state),
        config=config,
        formatter=formatter,
        now=NOW,
    )


# --- the state machine -----------------------------------------------------


def test_the_state_vocabulary_is_normal_plus_the_five(config) -> None:
    assert STATES == ("normal", "loading", "empty", "thin", "stale", "error")


@pytest.mark.parametrize(
    "changes,expected",
    [
        ({}, "normal"),
        ({"pending": True}, "loading"),
        ({"absent": True, "absence_reason": "no_listings"}, "empty"),
        ({"failed": True}, "error"),
        ({"n": 4}, "thin"),
        ({"as_of": datetime.date(2026, 7, 27)}, "stale"),
    ],
)
def test_the_state_follows_the_payload(config, changes, expected) -> None:
    payload = dataclass_replace(normal_payload("flow_aggregate_block"), **changes)
    assert state_of(payload, config=config, now=NOW) == expected


def test_state_precedence_is_error_loading_empty_thin_stale(config) -> None:
    """A payload can satisfy several conditions at once. The order is fixed, so
    two components never disagree about which one wins."""
    base = normal_payload("flow_aggregate_block")
    every = dataclass_replace(
        base,
        failed=True,
        pending=True,
        absent=True,
        absence_reason="no_listings",
        n=4,
        as_of=datetime.date(2026, 7, 27),
    )
    assert state_of(every, config=config, now=NOW) == "error"
    assert state_of(dataclass_replace(every, failed=False), config=config, now=NOW) == (
        "loading"
    )
    assert (
        state_of(
            dataclass_replace(every, failed=False, pending=False),
            config=config,
            now=NOW,
        )
        == "empty"
    )
    assert (
        state_of(
            dataclass_replace(every, failed=False, pending=False, absent=False),
            config=config,
            now=NOW,
        )
        == "thin"
    )


def test_a_thin_and_stale_payload_keeps_its_staleness_node(config, formatter) -> None:
    """A state label is not permission to drop a qualifier."""
    payload = dataclass_replace(
        normal_payload("flow_aggregate_block"),
        n=4,
        low=Decimal(61),
        high=Decimal(240),
        as_of=datetime.date(2026, 7, 27),
    )
    tree = build_component(
        "flow_aggregate_block",
        payload,
        config=config,
        formatter=formatter,
        now=NOW,
    )
    assert tree.meta["state"] == "thin"
    assert [node.text for node in nodes_by_role(tree, "staleness")] == [
        "dane sprzed 12 dni · ostatnie pobranie 27.07.2026"
    ]


def test_no_builder_takes_a_state_argument(config) -> None:
    """V36's "derived, not passed", asserted structurally."""
    for name, builder in sorted(public_builders().items()):
        parameters = inspect.signature(builder).parameters
        assert "state" not in parameters, name


@pytest.mark.parametrize(
    "as_of,days",
    [
        (datetime.date(2026, 8, 7), 1),
        (datetime.date(2026, 8, 6), 2),
        (datetime.date(2026, 7, 27), 12),
        (datetime.date(2025, 12, 31), 220),
    ],
)
def test_the_day_count_excludes_the_as_of_date(as_of, days) -> None:
    """An inclusive count renders 221 for the GUS row. This pins the off-by-one."""
    assert staleness_days(as_of, now=NOW) == days


def test_the_staleness_threshold_is_a_strict_comparison(config, formatter) -> None:
    """01.08.2026 is exactly seven days before the clock, and seven is not more
    than seven, so the golden screen carries no staleness node."""
    tree = build("flow_aggregate_block", "normal", config, formatter)
    assert nodes_by_role(tree, "staleness") == ()
    assert tree.meta["state"] == "normal"


# --- the registry ----------------------------------------------------------


def test_the_registry_names_every_component_this_stage_builds() -> None:
    assert tuple(COMPONENT_REGISTRY) == COMPONENTS


def test_the_registry_covers_every_public_builder() -> None:
    """A component outside the registry ships outside every sweep, which is how
    the honesty rules would erode one helper at a time."""
    registered = {entry.builder for entry in COMPONENT_REGISTRY.values()}
    assert set(public_builders().values()) == registered


@pytest.mark.parametrize("component", COMPONENTS)
@pytest.mark.parametrize("state", FIVE_STATES)
def test_every_registered_component_defines_all_five_states(
    config, formatter, component, state
) -> None:
    tree = build(component, state, config, formatter)
    assert tree.meta["state"] == state
    assert tree.meta["component"] == component
    assert len(walk(tree)) > 1


@pytest.mark.parametrize("component", COMPONENTS)
def test_the_loading_state_shows_no_value_like_token(
    config, formatter, component
) -> None:
    """A zero or a dash skeleton reads as a value. The block keeps its own
    heading, which is a label and not a figure."""
    tree = build(component, "loading", config, formatter)
    assert [node.role for node in nodes_by_role(tree, "loading")] == ["loading"]
    for role in ("value", "spread", "sample_size", "price", "comparable"):
        assert nodes_by_role(tree, role) == (), role
    skeleton = nodes_by_role(tree, "loading")[0]
    assert not any(character.isdigit() for character in skeleton.text)
    assert "—" not in skeleton.text
    assert "–" not in skeleton.text


@pytest.mark.parametrize("component", COMPONENTS)
def test_the_loading_text_ends_with_a_horizontal_ellipsis(
    config, formatter, component
) -> None:
    text = nodes_by_role(build(component, "loading", config, formatter), "loading")[
        0
    ].text
    assert text.endswith("…")
    assert "..." not in text


@pytest.mark.parametrize("component", COMPONENTS)
def test_the_empty_state_names_which_of_the_four_reasons_applies(
    config, formatter, component
) -> None:
    tree = build(component, "empty", config, formatter)
    absence = nodes_by_role(tree, "absence")[0]
    assert absence.meta["absence_reason"] == COMPONENT_REGISTRY[component].empty_reason
    assert absence.meta["tone"] == "warning"
    assert absence.prominence == "equal"
    assert absence.children[0].role == "basis"
    assert nodes_by_role(tree, "value") == ()


@pytest.mark.parametrize("component", COMPONENTS)
def test_the_thin_state_never_replaces_the_number_with_a_refusal(
    config, formatter, component
) -> None:
    """Rule 7. Thin evidence looks thin; it is not withheld."""
    tree = build(component, "thin", config, formatter)
    joined = " ".join(node.text for node in walk(tree))
    assert "za mało danych" not in joined or "orientacja" in joined
    assert "insufficient data" not in joined


@pytest.mark.parametrize(
    "component",
    ("flow_aggregate_block", "stock_aggregate_block", "gus_sales_block"),
)
def test_the_thin_aggregate_still_renders_its_number_its_range_and_its_n(
    config, formatter, component
) -> None:
    tree = build(component, "thin", config, formatter)
    assert len(nodes_by_role(tree, "value")) >= 1
    assert len(nodes_by_role(tree, "spread")) == 1
    assert len(nodes_by_role(tree, "sample_size")) == 1


def test_the_thin_flow_block_reads_exactly_as_the_plan_writes_it(
    config, formatter
) -> None:
    tree = build("flow_aggregate_block", "thin", config, formatter)
    texts = {node.role: node.text for node in tree.children}
    assert tree.text == "Podobne oferty (przepływ, ostatnie 90 dni)"
    assert texts["flow_window_label"] == "ostatnie 90 dni"
    assert texts["value"] == "mediana 118 zł/m²"
    assert texts["spread"] == "zakres 61–240"
    assert texts["sample_size"] == "n = 4"
    assert texts["price_type_label"] == "cena ofertowa"
    assert texts["price_kind_label"] == "oferta"
    assert texts["uncertainty_note"] == "Zakres szeroki — mało podobnych ofert"
    assert texts["provenance"] == "Źródło i metoda"


def test_the_stale_flow_block_reads_exactly_as_the_plan_writes_it(
    config, formatter
) -> None:
    tree = build("flow_aggregate_block", "stale", config, formatter)
    texts = {node.role: node.text for node in tree.children}
    assert texts["value"] == "mediana 118 zł/m²"
    assert texts["staleness"] == "dane sprzed 12 dni · ostatnie pobranie 27.07.2026"
    assert texts["spread"] == "zakres międzykwartylowy 96–141"
    assert texts["sample_size"] == "n = 23"
    assert "uncertainty_note" not in texts


@pytest.mark.parametrize(
    "component,expected",
    [
        (
            "plot_check_header",
            "Nie udało się odczytać ogłoszenia — wpisz powierzchnię i gminę ręcznie",
        ),
        (
            "verdict_block",
            "Nie udało się policzyć werdyktu — podobne oferty powyżej są aktualne",
        ),
        (
            "comparable_set",
            (
                "Nie udało się pobrać podobnych ofert — "
                "cena z ogłoszenia powyżej jest aktualna"
            ),
        ),
        (
            "flow_aggregate_block",
            "Nie udało się policzyć przepływu — stan poniżej jest aktualny",
        ),
        (
            "stock_aggregate_block",
            "Nie udało się policzyć stanu — przepływ powyżej jest aktualny",
        ),
        (
            "gus_sales_block",
            "Nie udało się pobrać danych GUS — ceny ofertowe poniżej są aktualne",
        ),
        (
            "uncertainty_panel",
            "Nie udało się ocenić pewności — liczby powyżej są aktualne",
        ),
        (
            "provenance_panel",
            "Nie udało się odczytać źródeł — liczby powyżej pochodzą z bazy",
        ),
    ],
)
def test_the_error_state_names_what_failed_and_what_is_still_trustworthy(
    config, formatter, component, expected
) -> None:
    tree = build(component, "error", config, formatter)
    error = nodes_by_role(tree, "error")[0]
    assert error.text == expected
    assert error.meta["tone"] == "warning"


@pytest.mark.parametrize(
    "component,expected",
    [
        ("plot_check_header", "wczytywanie danych o działce…"),
        ("verdict_block", "wczytywanie werdyktu…"),
        ("comparable_set", "wczytywanie podobnych ofert…"),
        ("flow_aggregate_block", "wczytywanie podobnych ofert…"),
        ("stock_aggregate_block", "wczytywanie wszystkich aktywnych ofert…"),
        ("gus_sales_block", "wczytywanie cen transakcyjnych…"),
        ("uncertainty_panel", "wczytywanie oceny pewności…"),
        ("provenance_panel", "wczytywanie źródeł…"),
    ],
)
def test_the_loading_text_is_the_one_the_plan_fixes(
    config, formatter, component, expected
) -> None:
    tree = build(component, "loading", config, formatter)
    assert nodes_by_role(tree, "loading")[0].text == expected


@pytest.mark.parametrize(
    "component,expected",
    [
        ("plot_check_header", "Mało podobnych ofert — wynik orientacyjny"),
        ("comparable_set", "Mało podobnych ofert — wynik orientacyjny"),
        ("flow_aggregate_block", "Zakres szeroki — mało podobnych ofert"),
        ("stock_aggregate_block", "Zakres szeroki — mało podobnych ofert"),
        ("gus_sales_block", "Nie znamy rozrzutu — GUS publikuje tylko średnią"),
    ],
)
def test_the_thin_state_says_in_words_what_the_numbers_only_imply(
    config, formatter, component, expected
) -> None:
    """U10. A range is legible only to a reader who already has a prior, and
    the reader this product is for does not have one."""
    tree = build(component, "thin", config, formatter)
    assert [node.text for node in nodes_by_role(tree, "uncertainty_note")] == [expected]


def test_the_thin_uncertainty_panel_leads_with_the_admission(config, formatter) -> None:
    """U11. Below the comparable threshold the tool says so, first."""
    tree = build("uncertainty_panel", "thin", config, formatter)
    assert [node.text for node in nodes_by_role(tree, "out_of_depth_notice")] == [
        "za mało danych, żeby ocenić — to jest orientacja, nie wycena"
    ]
    assert tree.children[0].role == "out_of_depth_notice"


def test_the_normal_uncertainty_panel_stays_silent(config, formatter) -> None:
    """A note on every aggregate trains the reader to ignore notes."""
    tree = build("uncertainty_panel", "normal", config, formatter)
    assert nodes_by_role(tree, "out_of_depth_notice") == ()
    assert nodes_by_role(tree, "uncertainty_note") == ()


# --- independent degradation ----------------------------------------------


def test_a_failed_sales_query_does_not_blank_the_offering_blocks(
    config, formatter
) -> None:
    """V36's partial-degradation case. One source failing must cost one block."""
    gus = build("gus_sales_block", "error", config, formatter)
    flow = build("flow_aggregate_block", "normal", config, formatter)
    stock = build("stock_aggregate_block", "normal", config, formatter)

    assert gus.meta["state"] == "error"
    assert (
        nodes_by_role(gus, "error")[0].text
        == "Nie udało się pobrać danych GUS — ceny ofertowe poniżej są aktualne"
    )
    assert flow.meta["state"] == "normal"
    assert stock.meta["state"] == "normal"
    assert nodes_by_role(flow, "value")[0].text == "mediana 118 zł/m²"
    assert nodes_by_role(stock, "value")[0].text == "mediana 127 zł/m²"
    assert nodes_by_role(flow, "sample_size")[0].text == "n = 23"


# --- determinism -----------------------------------------------------------


@pytest.mark.parametrize("component", COMPONENTS)
@pytest.mark.parametrize("state", ("normal", *FIVE_STATES))
def test_a_builder_called_twice_returns_an_equal_tree(
    config, formatter, component, state
) -> None:
    first = build(component, state, config, formatter)
    second = build(component, state, config, formatter)
    assert first == second


# --- the absence enum ------------------------------------------------------


def test_an_absence_reason_outside_the_enum_is_refused(config, formatter) -> None:
    payload = dataclass_replace(
        normal_payload("flow_aggregate_block"),
        absent=True,
        absence_reason="no_sales_data_at_all",
    )
    with pytest.raises(UnknownAbsenceReasonError) as caught:
        build_component(
            "flow_aggregate_block",
            payload,
            config=config,
            formatter=formatter,
            now=NOW,
        )
    assert "no_sales_data_at_all" in str(caught.value)


def test_the_render_absence_enum_is_a_subset_of_the_api_contract(
    repo_root: pathlib.Path,
) -> None:
    """The surface may render fewer reasons than the API carries. It may never
    invent one of its own."""
    from dzialki.render.absence import ABSENCE_REASONS

    contract = (repo_root / "docs" / "14-api-contract.md").read_text(encoding="utf-8")
    documented = {
        "not_yet_crawled",
        "out_of_scope",
        "no_comparables",
        "no_listings",
    }
    for reason in documented:
        assert reason in contract, reason
    assert set(ABSENCE_REASONS) <= documented | {"too_few_comparables"}
    assert set(ABSENCE_REASONS) == {
        "not_yet_crawled",
        "no_listings",
        "out_of_scope",
        "too_few_comparables",
    }


# --- the configuration -----------------------------------------------------


def test_the_ratified_values_come_from_the_parameter_file(
    repo_root: pathlib.Path, config: RenderConfig
) -> None:
    from dzialki.config import load_params

    params = load_params(repo_root / "config" / "params.yml")
    assert config.flow_window_days == params.aggregates.flow_window_days
    assert config.thin_n_threshold == params.aggregates.iqr_switch_n
    assert config.area_band_pct == params.comparables.area_band_pct
    assert config.thousands_sep == params.surface.thousands_sep


def test_the_flow_window_is_read_from_the_configuration_everywhere(
    config, formatter
) -> None:
    """V62's "two call sites, two windows", caught by rebuilding the whole
    registry at a different window and looking for a survivor."""
    import dataclasses

    narrowed = dataclasses.replace(config, flow_window_days=45)
    joined = " ".join(
        node.text
        for component in COMPONENTS
        for state in ("normal", *FIVE_STATES)
        for node in walk(build(component, state, narrowed, formatter))
    )
    assert "ostatnie 45 dni" in joined
    assert "90" not in joined


# --- Polish throughout (D15) ----------------------------------------------


@pytest.mark.parametrize("component", COMPONENTS)
@pytest.mark.parametrize("state", ("normal", *FIVE_STATES))
def test_no_rendered_text_contains_an_english_stopword(
    config, formatter, component, state
) -> None:
    """D15 keeps the interface Polish. Code identifiers stay English, so the
    sweep reads the rendered text and never the source."""
    import re

    stopwords = (
        "median",
        "range",
        "price",
        "unknown",
        "loading",
        "error",
        "no data",
        "sample",
    )
    for node in walk(build(component, state, config, formatter)):
        for word in stopwords:
            assert not re.search(
                rf"(?<!\w){re.escape(word)}(?!\w)", node.text.lower()
            ), (word, node.text)


@pytest.mark.parametrize("component", COMPONENTS)
@pytest.mark.parametrize("state", ("normal", *FIVE_STATES))
def test_no_rendered_number_uses_a_dot_decimal_or_a_comma_thousand(
    config, formatter, component, state
) -> None:
    """`1,234.56` trips the first pattern and `1,234` the second. Both must be
    checked, or an unformatted float leaks through a new component."""
    import re

    allowed = re.compile(r"cmp-\d{4}\.\d{2}\.\d+|\d\d\.\d\d\.\d{4}|\d{4}Q\d")
    for node in walk(build(component, state, config, formatter)):
        text = allowed.sub("", node.text)
        assert not re.search(r"\d\.\d", text), node.text
        assert not re.search(r"\d,\d{3}\b", text), node.text


@pytest.mark.parametrize("component", COMPONENTS)
@pytest.mark.parametrize("state", ("normal", *FIVE_STATES))
def test_no_rendered_area_uses_ar_or_hektar(
    config, formatter, component, state
) -> None:
    """Adverts state *ar* and *hektar*; the interface states m² only."""
    import re

    for node in walk(build(component, state, config, formatter)):
        for word in ("ar", "arów", "ha", "hektar"):
            assert not re.search(rf"(?<!\w){word}(?!\w)", node.text.lower()), node.text
