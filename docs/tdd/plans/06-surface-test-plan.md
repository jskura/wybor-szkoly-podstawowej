# Test plan — the v0 surface (pass 2, detail)

Pass 2, step 5 of the standard workflow ([`CLAUDE.md`](../../../CLAUDE.md) rule 8),
detailing [`06-surface.md`](../06-surface.md). Pass 1 gave the sequence; this gives
the literal cases a developer types in.

Rules detailed: **U1–U14** ([`21-v0-ui-and-ux.md`](../../21-v0-ui-and-ux.md) §3, §7.1).
Validation: **V59**, **V51c**, **V45**, **V62**, V35–V37.

---

## 0. Conventions used throughout this document

### 0.1 Node notation

Every tree in this document is written in one notation. It maps one-to-one onto
`RenderNode`, so a test can be transcribed from it directly.

```
role[prominence,disclosure] "text"          {meta…}
    role[prominence,disclosure] "text"      {meta…}      ← a child, one indent level
```

`{meta…}` is elided where it is not load-bearing for the assertion under
discussion. Document order is top-to-bottom, which is exactly what `walk(tree)`
and `index_of(tree, node)` return.

### 0.2 The space convention — read this before any string

> **Every space that separates a digit group from another digit group, and every
> space that separates a number from its unit, is U+00A0 NO-BREAK SPACE.**
> It is written as an ordinary space in the trees below for legibility.
> §5 gives the codepoint sequences literally, and `test_thousands_separator_is_a_non_breaking_space`
> asserts the codepoint, not the rendering.

All other spaces — including the ones around the `·` separator and around `=` in
`n = 23` — are U+0020.

### 0.3 The clock

Every tree in this document is built with the injected clock at
`now = date(2026, 8, 8)`. `render/` never reads a clock (§4 of the spec); `now`
is a parameter.

### 0.4 Configuration values these cases assume

Read from config, never literal in `render/` (V62, D67).

| Key | Value in these cases | Consumed by |
|---|---|---|
| `flow_window_days` | `90` | U4, §5 |
| `thin_n_threshold` | `5` | range kind switch, map hatch |
| `out_of_depth_min_comparables` | `4` | U11 |
| `wide_spread_ratio` | `0.60` | U10 |
| `staleness_threshold_days` | `7` | U8 |
| `method_version` | `"cmp-2026.08.1"` | U9 |

`thin_n_threshold` and `out_of_depth_min_comparables` are **two different
thresholds**, and the difference is deliberate: `n = 4` is thin (min–max range,
worded note) but not out of depth; `n = 3` is both. This is what makes
`AGG_THIN_N4` (§5.10 of the spec, a note) and `COMP_SET_N3` (§5.11, the notice)
different fixtures rather than the same one.

### 0.5 Percentile convention

R-7 linear interpolation, matching
[`04-aggregates-and-valuation.md`](../04-aggregates-and-valuation.md) A5. Every
hand-computed figure in §8 below is computed with it, and the arithmetic is shown
so it can be checked without running code.

---

## 1. The RenderNode schema, literally

### 1.1 The dataclass

```python
# src/lpc/app/render/contract.py

Role = Literal[
    "section", "header",                                    # containers — see OPEN-S5
    "aggregate_block", "value", "sample_size", "spread",
    "price", "price_type_label", "price_kind_label",
    "flow_window_label", "basis", "unknown", "absence",
    "staleness", "provenance", "verdict", "comparable_set",
    "comparable", "uncertainty_note", "out_of_depth_notice",
    "sensitivity_note", "disclosure_banner", "selector",
    "map_feature", "legend", "table_row", "fallback_form",
    "error", "loading",
]
Prominence = Literal["primary", "equal", "secondary"]
Disclosure = Literal["always", "expander", "hover"]

@dataclass(frozen=True)
class RenderNode:
    role: Role
    text: str
    prominence: Prominence
    disclosure: Disclosure
    children: tuple["RenderNode", ...] = ()
    meta: Mapping[str, object] = field(default_factory=lambda: MappingProxyType({}))
```

`frozen=True` plus `tuple` children plus `MappingProxyType` meta is what
`test_render_node_is_immutable` asserts: `node.text = "x"` raises
`FrozenInstanceError`, `node.children.append(...)` raises `AttributeError`,
`node.meta["n"] = 1` raises `TypeError`.

### 1.2 `meta` keys — the closed vocabulary

`test_meta_keys_are_from_a_closed_set` parametrizes over every fixture tree and
asserts every key appears here. An unknown key fails, so a new component cannot
smuggle in an unqualified figure under a private key name.

| Key | Type | Present on | Meaning |
|---|---|---|---|
| `component` | `str` | every registry component root | key into `COMPONENT_REGISTRY` |
| `state` | `"normal"\|"loading"\|"empty"\|"thin"\|"stale"\|"error"` | every registry component root | derived, never passed (§7 spec) |
| `n` | `int` | `aggregate_block`, `sample_size`, `comparable_set` | sample size |
| `median` | `Decimal` | `aggregate_block`, `value` | |
| `range` | `{"low": Decimal\|None, "high": Decimal\|None, "kind": "iqr"\|"min_max"\|"unavailable"}` | `aggregate_block`, `spread` | |
| `price_type` | `"offering"\|"sales"` | `price`, `aggregate_block`, `map_feature` | |
| `price_kind` | `"asking"\|"auction_start"\|"tender"\|"transaction"` | as above | `"transaction"` — see OPEN-S3 |
| `basis` | `"flow"\|"stock"\|"gus_powiat"\|"derived"` | `aggregate_block`, `value` | |
| `flow_window_days` | `int` | every node with `basis == "flow"` | |
| `as_of` | `date` | every `value`, every `aggregate_block` | |
| `provenance` | `{"source": tuple[str,…], "as_of": date, "method_version": str, "n": int}` | every `value` | U9 |
| `absence_reason` | `"not_yet_crawled"\|"no_listings"\|"out_of_scope"\|"too_few_comparables"` | `absence` | §4.2 |
| `tone` | `"ok"\|"warning"` | `unknown`, `absence`, `error`, `uncertainty_note` | U6 |
| `expanded` | `bool` | `verdict` | U5 |
| `exclude_control` | `{"comparable_id": str, "label": "nie pasuje"}` | `comparable` | V51c |
| `comparable_id` | `str` | `comparable` | stable across recompute |
| `action` | `{"office": str, "document": str}` | `sensitivity_note` | U13 |
| `fill` / `pattern` / `legend_key` | `str` | `map_feature`, `legend` | §6 |
| `field` | `str` | `value`, `error`, `fallback_form` children | which attribute failed |
| `subject_id` | `str` | screen root | V51c log join key |

### 1.3 Walkers — the one definition that is load-bearing

`disclosure_chain(tree, node)` is defined as: **the `disclosure` values of the
node's ancestors, root-first, followed by the node's own, with every `"always"`
removed.**

The spec's §2.2 wording ("the ordered disclosures of a node's ancestors") is
ambiguous about whether the node's own disclosure is included, and §5.9 requires
that it is — the `provenance` node's own chain must contain exactly one
`"expander"` and the expander is on the node itself. Pinning it here:

```python
disclosure_chain(tree, n_node)      == ()                # U1 — nothing between it and the root
disclosure_chain(tree, spread_node) == ()                # U1
disclosure_chain(tree, prov_node)   == ("expander",)     # U9 — exactly one
disclosure_chain(tree, prov_source) == ("expander",)     # U9 — a child of the expander
```

`test_disclosure_chain_omits_always_and_includes_the_node_itself` pins all four.

---

## 2. The worked example — the plot-check screen

The screen drawn in [`21-v0-ui-and-ux.md`](../../21-v0-ui-and-ux.md) §2.1, as the
complete expected tree. Fixture bundle: `PLOT_CHECK_SKIERNIEWICE_142`
(`SUBJECT_UNKNOWN_BUILDABILITY` + `AGG_FLOW_N23` + `AGG_STOCK_N61` +
`AGG_SALES_GUS` + `COMP_SET_N23`).

Test: `tests/unit/app/test_plot_check_golden.py::test_plot_check_tree_matches_the_golden_tree`.
It is a whole-tree equality assertion against this literal, not a spot check —
every other test in this plan asserts one property of it.

### 2.1 Subject data

| Field | Value |
|---|---|
| `subject_id` | `subj_0001` |
| `area_m2` | `3200` |
| `gmina` / `teryt` | gmina Skierniewice / `1015042` |
| `price_pln` | `454400` |
| `price_per_m2` | `142.00` (3200 × 142 = 454 400) |
| `price_type` / `price_kind` | `offering` / `asking` |
| `buildability` | `unknown` |
| `road_access` | `unknown` |
| `utilities` | `known` (prąd, woda w granicy) |
| `soil_class` | `known` (V) |

### 2.2 Ordering — one documented deviation from the §2.1 mockup

The mockup places the collapsed `WERDYKT` bar **above** the evidence. U14 and
`test_comparable_set_precedes_the_verdict_block` require
`index_of(comparable_set) < index_of(verdict)`.

**Resolution:** U14 wins, because §7 of `21` is explicitly stated to constrain the
surfaces described earlier in that document, and because §5.14 of the TDD spec
encodes it as a hard assertion. The verdict bar moves below the comparable set.
Nothing else in the mockup moves. Recorded as **OPEN-S1**; it needs a one-line
amendment to `21` §2.1's ASCII sketch, not a design change.

### 2.3 The golden tree

```
section[primary,always] "Sprawdzenie działki"
    {component:"plot_check", state:"normal", subject_id:"subj_0001"}

    header[primary,always] "3 200 m² · gmina Skierniewice · 142 zł/m²"
        {component:"plot_check_header", state:"normal"}

        value[primary,always] "3 200 m²"
            {field:"area_m2", as_of:2026-08-08,
             provenance:{source:("portal_a",), as_of:2026-08-08,
                         method_version:"cmp-2026.08.1", n:1}}

        basis[equal,always] "gmina Skierniewice"
            {field:"teryt", teryt:"1015042"}

        price[primary,always] "142 zł/m²"
            {price_type:"offering", price_kind:"asking", field:"price_per_m2",
             as_of:2026-08-08,
             provenance:{source:("portal_a",), as_of:2026-08-08,
                         method_version:"cmp-2026.08.1", n:1}}

        price_type_label[equal,always] "cena ofertowa"      {price_type:"offering"}
        price_kind_label[equal,always] "oferta"             {price_kind:"asking"}

        value[equal,always] "454 400 zł"
            {field:"price_pln", as_of:2026-08-08,
             provenance:{source:("portal_a",), as_of:2026-08-08,
                         method_version:"cmp-2026.08.1", n:1}}

    aggregate_block[primary,always] "Podobne oferty (przepływ, ostatnie 90 dni)"
        {component:"flow_aggregate_block", state:"normal", basis:"flow",
         flow_window_days:90, n:23, median:118.00,
         range:{low:96.00, high:141.00, kind:"iqr"},
         price_type:"offering", price_kind:"asking", as_of:2026-08-01}

        basis[equal,always] "przepływ"                      {basis:"flow"}
        flow_window_label[equal,always] "ostatnie 90 dni"   {flow_window_days:90}

        value[primary,always] "mediana 118 zł/m²"
            {median:118.00, basis:"flow", as_of:2026-08-01,
             provenance:{source:("portal_a","portal_b"), as_of:2026-08-01,
                         method_version:"cmp-2026.08.1", n:23}}

        spread[equal,always] "zakres międzykwartylowy 96–141"
            {range:{low:96.00, high:141.00, kind:"iqr"}}

        sample_size[equal,always] "n = 23"                  {n:23}

        price_type_label[equal,always] "cena ofertowa"      {price_type:"offering"}
        price_kind_label[equal,always] "oferta"             {price_kind:"asking"}

        provenance[equal,expander] "Źródło i metoda"
            value[equal,always] "Źródło: portal_a, portal_b"
            value[equal,always] "Stan na: 01.08.2026"
            value[equal,always] "Metoda: cmp-2026.08.1"
            value[equal,always] "Liczba obserwacji: n = 23"

    aggregate_block[primary,always] "Podobne oferty (stan, wszystkie aktywne)"
        {component:"stock_aggregate_block", state:"normal", basis:"stock",
         n:61, median:127.00, range:{low:99.00, high:168.00, kind:"iqr"},
         price_type:"offering", price_kind:"asking", as_of:2026-08-01}

        basis[equal,always] "stan"                          {basis:"stock"}

        value[primary,always] "mediana 127 zł/m²"
            {median:127.00, basis:"stock", as_of:2026-08-01,
             provenance:{source:("portal_a","portal_b"), as_of:2026-08-01,
                         method_version:"cmp-2026.08.1", n:61}}

        spread[equal,always] "zakres międzykwartylowy 99–168"
            {range:{low:99.00, high:168.00, kind:"iqr"}}

        sample_size[equal,always] "n = 61"                  {n:61}

        price_type_label[equal,always] "cena ofertowa"      {price_type:"offering"}
        price_kind_label[equal,always] "oferta"             {price_kind:"asking"}

        provenance[equal,expander] "Źródło i metoda"
            value[equal,always] "Źródło: portal_a, portal_b"
            value[equal,always] "Stan na: 01.08.2026"
            value[equal,always] "Metoda: cmp-2026.08.1"
            value[equal,always] "Liczba obserwacji: n = 61"

    value[equal,always] "stan wyżej niż przepływ"
        {field:"stock_flow_gap", basis:"derived", as_of:2026-08-01,
         provenance:{source:("portal_a","portal_b"), as_of:2026-08-01,
                     method_version:"cmp-2026.08.1", n:84}}

    aggregate_block[primary,always] "Ceny transakcyjne · powiat skierniewicki · GUS 2025Q4"
        {component:"gus_sales_block", state:"normal", basis:"gus_powiat",
         n:41, median:104.00,
         range:{low:None, high:None, kind:"unavailable"},
         price_type:"sales", price_kind:"transaction", as_of:2025-12-31}

        basis[equal,always] "poziom powiatu, dane kwartalne"  {basis:"gus_powiat"}

        value[primary,always] "średnia 104 zł/m²"
            {median:104.00, basis:"gus_powiat", as_of:2025-12-31,
             provenance:{source:("gus_bdl",), as_of:2025-12-31,
                         method_version:"cmp-2026.08.1", n:41}}

        spread[equal,always] "zakres niedostępny — GUS publikuje tylko średnią"
            {range:{low:None, high:None, kind:"unavailable"}}

        sample_size[equal,always] "n = 41"                  {n:41}

        price_type_label[equal,always] "cena transakcyjna"  {price_type:"sales"}
        price_kind_label[equal,always] "transakcja"         {price_kind:"transaction"}

        provenance[equal,expander] "Źródło i metoda"
            value[equal,always] "Źródło: gus_bdl"
            value[equal,always] "Stan na: 31.12.2025"
            value[equal,always] "Metoda: cmp-2026.08.1"
            value[equal,always] "Liczba obserwacji: n = 41"

    comparable_set[primary,always] "Podobne oferty — 23"
        {component:"comparable_set", state:"normal", n:23}

        comparable[equal,always] "112 zł/m² · 2 800 m² · gmina Skierniewice · 12.06.2026"
            {comparable_id:"cmp_0001",
             exclude_control:{comparable_id:"cmp_0001", label:"nie pasuje"},
             price_type:"offering", price_kind:"asking", as_of:2026-06-12}
            price_type_label[equal,always] "cena ofertowa"
            price_kind_label[equal,always] "oferta"

        comparable[equal,always] "124 zł/m² · 3 400 m² · gmina Skierniewice · 03.07.2026"
            {comparable_id:"cmp_0002",
             exclude_control:{comparable_id:"cmp_0002", label:"nie pasuje"},
             price_type:"offering", price_kind:"asking", as_of:2026-07-03}
            price_type_label[equal,always] "cena ofertowa"
            price_kind_label[equal,always] "oferta"

        comparable[equal,always] "96 zł/m² · 4 100 m² · gmina Skierniewice · 21.05.2026"
            {comparable_id:"cmp_0003",
             exclude_control:{comparable_id:"cmp_0003", label:"nie pasuje"},
             price_type:"offering", price_kind:"asking", as_of:2026-05-21}
            price_type_label[equal,always] "cena ofertowa"
            price_kind_label[equal,always] "oferta"

        … 20 further `comparable` nodes, identical in shape, ids cmp_0004…cmp_0023,
          values listed in `tests/fixtures/app/COMP_SET_N23.json`

    verdict[secondary,expander] "WERDYKT"
        {component:"verdict_block", state:"normal", expanded:False}

        value[equal,always] "Powyżej górnej granicy zakresu przepływu (96–141)"
            {basis:"flow", as_of:2026-08-01,
             provenance:{source:("portal_a","portal_b"), as_of:2026-08-01,
                         method_version:"cmp-2026.08.1", n:23}}

        basis[equal,always]
            "Podstawa: 23 oferty, ta sama gmina, 1 600–4 800 m², ostatnie 90 dni"
            {basis:"flow", flow_window_days:90, n:23}

    unknown[equal,always] "Nie sprawdzamy planu — nie wiemy, czy można budować"
        {field:"buildability", tone:"warning"}

    unknown[equal,always] "brak danych planistycznych — sprawdź w gminie"
        {field:"buildability", tone:"warning"}

    unknown[equal,always] "brak danych o dojeździe — sprawdź w gminie"
        {field:"road_access", tone:"warning"}

    sensitivity_note[equal,always]
        "gdyby ta działka miała plan miejscowy, porównania byłyby inne"
        {field:"buildability", action:{office:"Urząd Gminy Skierniewice",
                                       document:"wypis i wyrys"}}

    sensitivity_note[equal,always]
        "gdyby dojazd był drogą gminną, a nie służebnością, porównania byłyby inne"
        {field:"road_access", action:{office:"Urząd Gminy Skierniewice",
                                      document:"wypis i wyrys"}}

    disclosure_banner[equal,always]
        "Ten tool porównuje ceny ofertowe. Nie jest wyceną rzeczoznawcy i nie sprawdza, czy na działce można budować. Przy małej liczbie porównań wynik jest orientacyjny."
```

### 2.4 What the golden tree is asserted to satisfy

Assertions that run against this exact tree, each in its own test:

| Assertion | Rule |
|---|---|
| `len(nodes_by_role(t,"uncertainty_note")) == 0` — flow ratio (141−96)/118 = 0.381 < 0.60, stock 0.543 < 0.60 | U10, closed vocabulary §4.4 |
| `len(nodes_by_role(t,"out_of_depth_notice")) == 0` — n = 23 ≥ 4 | U11 |
| `len(nodes_by_role(t,"staleness")) == 0` — `as_of` 2026-08-01, now 2026-08-08, 7 days, not `> 7` | U8 |
| `index_of(comparable_set) < index_of(verdict)` | U14 |
| `index_of(flow_block) < index_of(stock_block)` | U3 |
| every node with `meta["basis"] == "flow"` has a `flow_window_label` sibling | U4 |
| the two `sensitivity_note` nodes are ordered buildability-first (larger stratum gap in the fixture) | U13 |
| no node's `meta` holds `122.5` (the mean of 118 and 127) | U3 |

### 2.5 The uncertainty ratio, computed

`spread_ratio = (high − low) / median`.

| Fixture | low | high | median | ratio | ≥ 0.60? |
|---|---|---|---|---|---|
| `AGG_FLOW_N23` | 96 | 141 | 118 | 0.3814 | no |
| `AGG_STOCK_N61` | 99 | 168 | 127 | 0.5433 | no |
| `AGG_THIN_N4` | 61 | 240 | 118 | 1.5169 | yes |
| `AGG_WIDE_N40` | 62 | 160 | 120 | 0.8167 | yes |
| `AGG_TIGHT_N61` | 118 | 136 | 127 | 0.1417 | no |

`AGG_SALES_GUS` has `kind == "unavailable"`; its ratio is `None` and it takes the
`unavailable` row of the §4.4 vocabulary table.

---

## 3. U1–U14 — the passing tree and the failing tree

Each subsection gives: the tree that must pass, the tree that must fail, and the
single assertion that separates them. The failing trees live in
`tests/fixtures/app/dishonest/` and are the teeth-proving fixtures of spec §12.2 —
a sweep that passes on them is not testing honesty.

### 3.1 U1 — no aggregate without `n` and range, at equal prominence

**Passes** — `tests/fixtures/app/AGG_FLOW_N23.py`

```
aggregate_block[primary,always] "Podobne oferty (przepływ, ostatnie 90 dni)"
    value[equal,always]         "mediana 118 zł/m²"
    spread[equal,always]        "zakres międzykwartylowy 96–141"
    sample_size[equal,always]   "n = 23"
```

`primary` sits on the **block**, never on the value inside it. That placement is
the whole point: a tree with `value[primary]` and `spread[equal]` is arithmetically
identical and reads as a headline with a footnote, which is the demotion U1 exists
to forbid. `test_no_value_node_inside_an_aggregate_block_is_primary` pins it
separately, so it cannot be reintroduced as a styling tweak.

**Fails** — `dishonest/hover_range.py`

```
aggregate_block[primary,always] "Podobne oferty (przepływ, ostatnie 90 dni)"
    value[equal,always]         "mediana 118 zł/m²"
    section[secondary,hover]    "szczegóły"
        spread[equal,always]    "zakres międzykwartylowy 96–141"
        sample_size[equal,always] "n = 23"
```

**The distinguishing assertion**

```python
def test_n_and_spread_are_not_inside_a_hover_only_container(tree):
    block  = nodes_by_role(tree, "aggregate_block")[0]
    n      = nodes_by_role(block, "sample_size")[0]
    spread = nodes_by_role(block, "spread")[0]
    value  = nodes_by_role(block, "value")[0]

    assert "hover" not in disclosure_chain(tree, n)
    assert "hover" not in disclosure_chain(tree, spread)
    assert n.prominence == spread.prominence == value.prominence
    assert value.prominence != "primary"
```

On the passing tree all four hold: `disclosure_chain` is `()` for `n` and
`spread`, and all three prominences are `"equal"`.
On `dishonest/hover_range.py` the first assertion fails with
`disclosure_chain == ("hover",)` — this is the observation V35 names, and it fails
on the chain, not on the node's own `disclosure`, which is `"always"` in both
trees. A test written against `node.disclosure` alone would pass the dishonest
tree.

Second dishonest fixture, `dishonest/secondary_range.py`, moves the range out of
the hover container but marks it `secondary`:

```
    spread[secondary,always]    "zakres międzykwartylowy 96–141"
```

caught by the third assertion, not the first. Both fixtures are needed.

Third, `dishonest/bare_aggregate.py` omits `spread` and `sample_size` entirely —
caught before rendering by
`test_render_aggregate_block_rejects_a_payload_without_n`, which asserts
`BareAggregateError` is raised, so the dishonest tree cannot be constructed
through the public builder at all. The fixture constructs it by hand, which is
what proves the sweep would catch a component that bypasses the builder.

### 3.2 U2 — every price shows type and kind

**Passes**

```
price[equal,always]             "142 zł/m²"       {price_type:"offering", price_kind:"asking"}
price_type_label[equal,always]  "cena ofertowa"   {price_type:"offering"}
price_kind_label[equal,always]  "oferta"          {price_kind:"asking"}
```

**Fails** — `dishonest/kindless_price.py`

```
price[equal,always]             "142 zł/m²"       {price_type:"offering"}
price_type_label[equal,always]  "cena ofertowa"
```

**Assertion**

```python
def test_price_node_carries_type_and_kind_labels(tree):
    for price in nodes_by_role(tree, "price"):
        sibs = {s.role for s in siblings_of(tree, price)}
        assert "price_type_label" in sibs
        assert "price_kind_label" in sibs
        assert "hover" not in disclosure_chain(tree, price)
```

The dishonest tree has no `price_kind_label` sibling. The builder-level twin,
`test_render_price_rejects_a_price_without_kind`, asserts `UnlabelledPriceError`.

**The label table** — parametrized, exact strings:

| `price_type` | label | `price_kind` | label |
|---|---|---|---|
| `offering` | `cena ofertowa` | `asking` | `oferta` |
| `sales` | `cena transakcyjna` | `auction_start` | `cena wywoławcza` |
| | | `tender` | `cena przetargowa` |
| | | `transaction` | `transakcja` |

Legal pairs: `offering × {asking, auction_start, tender}` and
`sales × {transaction}`. Four pairs; every other pair raises
`IllegalPriceCombinationError`. `test_price_pair_matrix_is_exhaustive`
parametrizes all 8 combinations of the two types and four kinds and asserts
exactly these four are legal.

**Fails** — `dishonest/mixed_kinds.py`: an `aggregate_block` whose
`meta["sources"]` span `asking` and `auction_start`. Builder raises
`MixedPriceKindError`; the hand-built tree is caught by
`test_aggregate_block_refuses_inputs_spanning_price_kinds`, the render half of
F9's detector.

### 3.3 U3 — flow and stock both shown, both labelled, flow first

**Passes** — the two `aggregate_block` nodes of §2.3, in that order, each with its
own `basis` child, plus the gap commentary node.

**Fails** — `dishonest/blended_pair.py`

```
aggregate_block[primary,always] "Podobne oferty"
    value[equal,always]         "mediana 122,5 zł/m²"    {median:122.50}
    spread[equal,always]        "zakres międzykwartylowy 96–168"
    sample_size[equal,always]   "n = 84"
```

**Assertions**

```python
def test_flow_block_precedes_stock_block(tree):
    flow  = one(b for b in nodes_by_role(tree,"aggregate_block") if b.meta["basis"]=="flow")
    stock = one(b for b in nodes_by_role(tree,"aggregate_block") if b.meta["basis"]=="stock")
    assert index_of(tree, flow) < index_of(tree, stock)

def test_flow_and_stock_are_never_averaged(tree):
    forbidden = (Decimal("118") + Decimal("127")) / 2       # 122.50
    assert all(node.meta.get("median") != forbidden for node in walk(tree))
    assert "122,5" not in " ".join(text_tokens(tree))
```

`dishonest/blended_pair.py` fails both: `one(...)` raises because no block carries
`basis == "flow"`, and `122.50` is present. Second dishonest fixture
`dishonest/stock_first.py` reverses the two blocks and fails only the first
assertion.

**Exact basis-label strings**, asserted by
`test_both_blocks_carry_their_basis_label`:

- flow block text: `Podobne oferty (przepływ, ostatnie 90 dni)`
- stock block text: `Podobne oferty (stan, wszystkie aktywne)`
- gap commentary: `stan wyżej niż przepływ`

A payload with `basis=None` raises `UnlabelledAggregateError` — V45(c) applied at
the render boundary.

### 3.4 U4 — the flow window next to every flow figure

**Passes**

```
aggregate_block[primary,always] "Podobne oferty (przepływ, ostatnie 90 dni)"  {basis:"flow", flow_window_days:90}
    flow_window_label[equal,always] "ostatnie 90 dni"                          {flow_window_days:90}
    value[equal,always]             "mediana 118 zł/m²"                        {basis:"flow"}
```

**Fails** — `dishonest/windowless_flow.py`

```
aggregate_block[primary,always] "Podobne oferty (przepływ)"                    {basis:"flow"}
    value[equal,always]             "mediana 118 zł/m²"                        {basis:"flow"}
```

**Assertion**

```python
def test_flow_window_label_is_a_sibling_of_every_flow_figure(tree):
    for node in walk(tree):
        if node.meta.get("basis") == "flow" and node.role in {"value","aggregate_block"}:
            sibs = siblings_of(tree, node) if node.role == "value" else node.children
            assert any(s.role == "flow_window_label" for s in sibs)
```

**The config test, and its exact strings.** Rebuild the whole
`COMPONENT_REGISTRY` sweep with `flow_window_days=60`:

| Node | at 90 | at 60 |
|---|---|---|
| flow block text | `Podobne oferty (przepływ, ostatnie 90 dni)` | `Podobne oferty (przepływ, ostatnie 60 dni)` |
| `flow_window_label` | `ostatnie 90 dni` | `ostatnie 60 dni` |
| verdict basis | `…, ostatnie 90 dni` | `…, ostatnie 60 dni` |
| map legend | `cena ofertowa · oferta · przepływ, ostatnie 90 dni` | `… ostatnie 60 dni` |
| export | `ostatnie 90 dni` | `ostatnie 60 dni` |

```python
def test_flow_window_is_read_from_config_not_hardcoded():
    trees = build_every_registered_component(config(flow_window_days=60))
    joined = " ".join(t for tree in trees for t in text_tokens(tree))
    assert "60 dni" in joined
    assert "90" not in joined          # V62's "two call sites, two windows"
```

Paired structural test `test_no_render_module_contains_a_literal_window_length`:
AST scan of `src/lpc/app/render/` for `ast.Constant` integers in `{30, 60, 90, 180}`.

### 3.5 U5 — verdict collapsed until expanded

**Passes** — the `verdict` node of §2.3: `disclosure == "expander"`,
`meta["expanded"] is False`, own text exactly `WERDYKT`.

**Fails** — `dishonest/leaky_verdict.py`

```
verdict[primary,always] "WERDYKT — powyżej górnej granicy zakresu przepływu (96–141)"
    {expanded:True}
```

**Assertion**

```python
LEAK_TOKENS = {"powyżej", "poniżej", "w zakresie"}

def test_collapsed_verdict_leaks_no_conclusion_text(tree):
    v = nodes_by_role(tree, "verdict")[0]
    assert v.text == "WERDYKT"
    assert v.disclosure == "expander"
    assert v.meta["expanded"] is False
    assert not (LEAK_TOKENS & set(v.text.lower().split()))
    for child in walk(v):
        if child is not v:
            assert "expander" in disclosure_chain(tree, child)
```

The dishonest tree fails on `v.text == "WERDYKT"` and on `disclosure`.

**The three sanctioned expanded forms**, asserted by
`test_expanded_verdict_is_phrased_relative_to_the_range` as a closed set:

- `Powyżej górnej granicy zakresu przepływu (96–141)`
- `Poniżej dolnej granicy zakresu przepływu (96–141)`
- `W zakresie przepływu (96–141)`

and `test_verdict_never_expresses_a_percentage_off_a_midpoint`:

```python
assert "%" not in v_text and "od mediany" not in v_text
```

`dishonest/percentage_verdict.py` reads
`Powyżej mediany o 20% (mediana 118)` and fails it.

### 3.6 U6 — `unknown` renders as explicit Polish text

**Passes**

```
unknown[equal,always] "brak danych planistycznych — sprawdź w gminie"  {field:"buildability", tone:"warning"}
unknown[equal,always] "brak danych o dojeździe — sprawdź w gminie"     {field:"road_access", tone:"warning"}
unknown[equal,always] "brak danych o mediach — sprawdź w gminie"       {field:"utilities",   tone:"warning"}
unknown[equal,always] "brak danych o klasie gruntu — sprawdź w gminie" {field:"soil_class",  tone:"warning"}
```

Four separate sentences: `test_unknown_utilities_and_road_access_each_render_their_own_text`
asserts pairwise distinctness, so three unknowns never collapse into one line.

**Fails** — `dishonest/blank_unknown.py`

```
unknown[secondary,always] "—"   {field:"buildability", tone:"ok"}
```

**Assertion**

```python
BLANKS = {"", " ", "-", "–", "—", "?", "n/a", "N/A", "None", "null", "nan", "NaN", "0"}

def test_no_rendered_text_is_blank_or_a_dash_sweep(tree):
    for node in walk(tree):
        if node.role != "value":
            assert node.text.strip() not in BLANKS

def test_unknown_is_not_styled_as_reassurance(tree):
    for u in nodes_by_role(tree, "unknown"):
        assert u.meta["tone"] == "warning"
        assert u.prominence != "secondary"
```

`dishonest/blank_unknown.py` fails all three clauses. A second fixture,
`dishonest/repr_leak.py`, sets the text to `"None"` — caught by the same sweep,
which is why the blank set contains Python reprs and not only dashes.

**Never inferred.** `test_unknown_is_never_inferred` builds a subject with
`zoning_claim = "budowlana"` and `buildability = "unknown"` and asserts both:

```
unknown[equal,always] "brak danych planistycznych — sprawdź w gminie"  {field:"buildability"}
value[equal,always]   "budowlana"                                       {field:"zoning_claim"}
    basis[equal,always] "z ogłoszenia"
```

Falsified by a tree in which the `unknown` node is absent because the claim filled
it in.

### 3.7 U7 — the four absence reasons are distinguished

**Passes** — four trees, one per reason:

```
absence[equal,always] "Brak danych — tej gminy jeszcze nie zebraliśmy"        {absence_reason:"not_yet_crawled",     tone:"warning"}
    basis[equal,always] "jeszcze nie zebraliśmy — sprawdź później"

absence[equal,always] "Brak danych — w tej gminie nie ma ofert"               {absence_reason:"no_listings",         tone:"warning"}
    basis[equal,always] "brak ofert w tej gminie"

absence[equal,always] "Brak danych — ta gmina jest poza zasięgiem narzędzia"  {absence_reason:"out_of_scope",        tone:"warning"}
    basis[equal,always] "poza zasięgiem narzędzia"

absence[equal,always] "Brak danych — za mało podobnych ofert"                 {absence_reason:"too_few_comparables", tone:"warning"}
    basis[equal,always] "za mało podobnych ofert, żeby porównać"
```

The four action strings are quoted verbatim from spec §5.7.

**Fails** — `dishonest/shared_absence.py`: all four reasons render
`Brak danych`, with the same empty `basis` child.

**Assertion**

```python
REASONS = ("not_yet_crawled", "no_listings", "out_of_scope", "too_few_comparables")

def test_four_absence_reasons_render_distinct_text():
    texts   = [render_absence(r).text for r in REASONS]
    actions = [render_absence(r).children[0].text for r in REASONS]
    assert len(set(texts))   == 4
    assert len(set(actions)) == 4

def test_absence_never_renders_as_zero_or_as_a_number():
    for r in REASONS:
        assert nodes_by_role(render_absence(r), "value") == []
```

`dishonest/shared_absence.py` reduces both sets to size 1.

`test_unknown_absence_reason_raises`: `render_absence("no_sales_data_at_all")`
raises `UnknownAbsenceReasonError`, never a generic string.

### 3.8 U8 — stale data shows its age on the number

**Passes** — `AGG_STALE_12D`, `as_of = 2026-07-27`, `now = 2026-08-08`:

```
aggregate_block[primary,always] "Podobne oferty (przepływ, ostatnie 90 dni)"  {state:"stale"}
    value[equal,always]      "mediana 118 zł/m²"                              {as_of:2026-07-27}
    staleness[equal,always]  "dane sprzed 12 dni · ostatnie pobranie 27.07.2026"
    spread[equal,always]     "zakres międzykwartylowy 96–141"
    sample_size[equal,always] "n = 23"
```

**Fails** — `dishonest/banner_staleness.py`

```
section[primary,always] "Sprawdzenie działki"
    staleness[secondary,always] "dane mogą być nieaktualne"      ← at root
    aggregate_block[primary,always] "Podobne oferty (przepływ, ostatnie 90 dni)"
        value[equal,always] "mediana 118 zł/m²"
```

**Assertion**

```python
def test_staleness_node_is_a_sibling_of_the_value_not_a_page_banner(tree):
    for stale in nodes_by_role(tree, "staleness"):
        assert ancestors_of(tree, stale) != ()          # never at root
    for value in nodes_by_role(tree, "value"):
        if is_stale(value.meta["as_of"], now, staleness_threshold_days):
            assert any(s.role == "staleness" for s in siblings_of(tree, value))
```

The dishonest tree fails on the first clause: its `staleness` node's ancestors are
empty. Arithmetic: 2026-08-08 − 2026-07-27 = 12 days > 7, so stale;
2026-08-08 − 2026-08-01 = 7 days, **not** `> 7`, so the golden tree of §2.3 has no
`staleness` node — `test_fresh_data_renders_no_staleness_node` asserts that
boundary exactly, and a `>=` implementation fails it.

### 3.9 U9 — every number is one click from source, as-of and method

**Passes** — the `provenance` subtree of §2.3.

**Fails** — `dishonest/deep_provenance.py`

```
aggregate_block[primary,always] "Podobne oferty (przepływ, ostatnie 90 dni)"
    section[secondary,expander] "Szczegóły"
        section[secondary,expander] "Metodologia"
            provenance[secondary,always] "Źródło: portal_a, portal_b"
```

and `dishonest/hover_provenance.py`, identical but with a single `hover`
container.

**Assertion**

```python
def test_provenance_is_exactly_one_interaction_away(tree):
    for p in nodes_by_role(tree, "provenance"):
        chain = disclosure_chain(tree, p)
        assert chain.count("expander") == 1
        assert "hover" not in chain

def test_every_numeric_node_carries_a_provenance_handle(tree):
    for v in nodes_by_role(tree, "value"):
        prov = v.meta["provenance"]
        assert prov["source"] and prov["as_of"] and prov["method_version"]
        assert isinstance(prov["n"], int)
```

`deep_provenance` gives `chain == ("expander","expander")`, count 2;
`hover_provenance` gives `("hover",)`, count 0 plus a hover. Both fail, for
different reasons, which is why both fixtures exist.

`test_provenance_lists_every_contributing_source` uses a mixed-source aggregate
and asserts the text is `Źródło: portal_a, portal_b, kowr`, not `Źródło: portal_a`.

### 3.10 U10 — uncertainty stated in words

**Passes** — `AGG_THIN_N4`

```
aggregate_block[primary,always] "Podobne oferty (przepływ, ostatnie 90 dni)"  {state:"thin", n:4}
    value[equal,always]         "mediana 118 zł/m²"
    spread[equal,always]        "zakres 61–240"                {range:{low:61, high:240, kind:"min_max"}}
    sample_size[equal,always]   "n = 4"
    uncertainty_note[equal,always] "Zakres szeroki — mało podobnych ofert"   {tone:"warning"}
```

Note `zakres`, not `zakres międzykwartylowy` — `n = 4 < 5` so `kind == "min_max"`.
`test_spread_kind_follows_n` parametrizes `n ∈ {3,4,5,6,23}` against
`kind ∈ {min_max, min_max, iqr, iqr, iqr}` and the two label prefixes.

**Fails** — `dishonest/silent_thin.py`: the same block with the
`uncertainty_note` removed. Numerically correct, and exactly the failure U10
names.

**Assertion**

```python
def test_thin_aggregate_carries_a_worded_uncertainty_note(tree):
    note = one(nodes_by_role(tree, "uncertainty_note"))
    assert note.text == "Zakres szeroki — mało podobnych ofert"
    assert note.disclosure == "always"
    assert note.prominence == "equal"
```

**The closed vocabulary**, asserted exhaustively by
`test_note_wording_is_selected_from_a_closed_vocabulary` over
(n band × spread band):

| n band | spread band | note text |
|---|---|---|
| `n < 5` | ratio < 0.60 | `Mało podobnych ofert — wynik orientacyjny` |
| `n < 5` | ratio ≥ 0.60 | `Zakres szeroki — mało podobnych ofert` |
| `5 ≤ n < 20` | ratio < 0.60 | *(no node)* |
| `5 ≤ n < 20` | ratio ≥ 0.60 | `Zakres szeroki — ceny w tej gminie bardzo się różnią` |
| `n ≥ 20` | ratio < 0.60 | *(no node)* |
| `n ≥ 20` | ratio ≥ 0.60 | `Zakres szeroki — ceny w tej gminie bardzo się różnią` |
| any | `kind == "unavailable"` | `Nie znamy rozrzutu — GUS publikuje tylko średnią` |

Seven cells, all parametrized. A new band that produced `""` would fail
`test_no_rendered_text_is_blank_or_a_dash_sweep` as well.

`test_tight_and_well_supported_aggregate_gets_no_note` runs `AGG_TIGHT_N61`
(ratio 0.1417, n = 61) and asserts zero `uncertainty_note` nodes — the guard
against a note on every aggregate, which trains the user to ignore notes.

### 3.11 U11 — the tool volunteers when it is out of its depth

**Passes** — `COMP_SET_N3` (n = 3 < `out_of_depth_min_comparables` = 4)

```
section[primary,always] "Sprawdzenie działki"
    out_of_depth_notice[primary,always]
        "za mało danych, żeby ocenić — to jest orientacja, nie wycena"   {tone:"warning"}
    aggregate_block[secondary,always] "Podobne oferty (przepływ, ostatnie 90 dni)"  {state:"thin", n:3}
        value[equal,always]         "mediana 112 zł/m²"
        spread[equal,always]        "zakres 104–124"
        sample_size[equal,always]   "n = 3"
        uncertainty_note[equal,always] "Mało podobnych ofert — wynik orientacyjny"
    comparable_set[secondary,always] "Podobne oferty — 3"
    verdict[secondary,expander] "WERDYKT"
```

The estimate still renders — rule 7, nothing is hidden — but demoted beneath the
notice, with its `n` and range intact.

**Fails** — `dishonest/confident_thin.py`

```
section[primary,always] "Sprawdzenie działki"
    verdict[primary,always] "Powyżej górnej granicy zakresu przepływu (104–124)"
    aggregate_block[primary,always] "Podobne oferty (przepływ, ostatnie 90 dni)"  {n:3}
```

**Assertion**

```python
def test_below_the_comparable_threshold_the_notice_leads(tree):
    first = next(walk_children(tree))                 # first node after the root
    assert first.role == "out_of_depth_notice"
    assert first.text == "za mało danych, żeby ocenić — to jest orientacja, nie wycena"

def test_no_confident_band_is_presented_below_the_threshold(tree):
    assert all(v.prominence != "primary" for v in nodes_by_role(tree, "verdict"))
```

`confident_thin` fails both: the first child is a `verdict`, and it is `primary`.

`test_silence_is_never_the_thin_data_rendering` is the sweep form — for every
component in the `thin` state:

```python
assert nodes_by_role(t,"uncertainty_note") or nodes_by_role(t,"out_of_depth_notice")
```

### 3.12 U12 — never a single unqualified number

**Passes** — the export of the §2.3 tree, verbatim:

```
Sprawdzenie działki — 08.08.2026

Działka: 3 200 m² · gmina Skierniewice
Cena z ogłoszenia: 454 400 zł · 142 zł/m² · cena ofertowa · oferta

Podobne oferty (przepływ, ostatnie 90 dni)
  mediana 118 zł/m² · zakres międzykwartylowy 96–141 · n = 23
  cena ofertowa · oferta · stan na 01.08.2026 · źródło: portal_a, portal_b · metoda cmp-2026.08.1

Podobne oferty (stan, wszystkie aktywne)
  mediana 127 zł/m² · zakres międzykwartylowy 99–168 · n = 61
  cena ofertowa · oferta · stan na 01.08.2026 · źródło: portal_a, portal_b · metoda cmp-2026.08.1

Ceny transakcyjne · powiat skierniewicki · GUS 2025Q4
  średnia 104 zł/m² · zakres niedostępny — GUS publikuje tylko średnią · n = 41
  cena transakcyjna · transakcja · poziom powiatu, dane kwartalne · stan na 31.12.2025

WERDYKT
  Powyżej górnej granicy zakresu przepływu (96–141)
  Podstawa: 23 oferty, ta sama gmina, 1 600–4 800 m², ostatnie 90 dni

Nie sprawdzamy planu — nie wiemy, czy można budować
gdyby ta działka miała plan miejscowy, porównania byłyby inne

Ten tool porównuje ceny ofertowe. Nie jest wyceną rzeczoznawcy i nie sprawdza,
czy na działce można budować. Przy małej liczbie porównań wynik jest orientacyjny.
```

**Fails** — `dishonest/bare_export.txt`

```
Sprawdzenie działki — 08.08.2026
Działka: 3 200 m² · gmina Skierniewice
Podobne oferty: mediana 118 zł/m²
WERDYKT: powyżej zakresu
```

**Assertion** — the line lint, with its allowlist stated as a closed set:

```python
AGGREGATE_LINE   = re.compile(r"n = \d+")
RANGE_TOKEN      = re.compile(r"\d+–\d+")
ALLOWLIST = (
    re.compile(r"^Sprawdzenie działki — \d\d\.\d\d\.\d{4}$"),          # dated title
    re.compile(r"^Działka: [\d\u00a0]+ m² · .+$"),                     # area
    re.compile(r"^Cena z ogłoszenia: .+ · cena \w+ · \w+$"),           # listing price, typed+kinded
    re.compile(r"^Podobne oferty \((przepływ|stan)[^)]*\)$"),          # block heading
    re.compile(r"^Ceny transakcyjne · .+ · GUS \d{4}Q\d$"),            # quarter heading
    re.compile(r"^\s*cena \w+ · \w+ · stan na .+ · .+$"),              # provenance line
    re.compile(r"^\s*Powyżej|Poniżej|W zakresie .* \(\d+–\d+\)$"),     # verdict, names its range
    re.compile(r"^\s*Podstawa: \d+ oferty, .+$"),                      # verdict basis
)

def test_export_line_containing_a_number_also_contains_n_and_range(text):
    for line in text.splitlines():
        if not re.search(r"\d", line):
            continue
        if AGGREGATE_LINE.search(line) and RANGE_TOKEN.search(line):
            continue
        assert any(p.match(line) for p in ALLOWLIST), line
```

`bare_export.txt` fails on `Podobne oferty: mediana 118 zł/m²` — a digit, no
`n =`, no range, and it matches no allowlist pattern. The `zakres niedostępny`
line is carried by the `n = 41` + heading pair: it matches neither
`RANGE_TOKEN` nor the allowlist alone, so
`test_export_allowlist_is_closed_and_each_pattern_is_exercised` asserts a ninth
pattern for the GUS spread line and that **every** pattern matches at least one
line of the golden export — an unexercised allowlist entry is a hole.

`test_export_carries_the_honest_disclosure_verbatim` compares against the
paragraph parsed out of `21` §7.2, not a copy in code, so a shortened variant
fails. `test_copy_to_clipboard_payload_equals_the_export_text` asserts string
equality between the two code paths.

### 3.13 U13 — show what would change the answer

**Passes** — the two `sensitivity_note` nodes of §2.3, in that order.

**Fails** — `dishonest/constant_caveat.py`

```
sensitivity_note[secondary,always] "Pamiętaj, że dane mogą być niepełne."  {}
```

**Assertion**

```python
def test_notes_are_derived_from_the_subjects_missing_attributes():
    assert notes_for(unknown={"buildability"}) == [
        "gdyby ta działka miała plan miejscowy, porównania byłyby inne"]
    assert notes_for(unknown={"road_access"}) == [
        "gdyby dojazd był drogą gminną, a nie służebnością, porównania byłyby inne"]
    assert notes_for(unknown={"utilities"}) == [
        "gdyby media były na działce, a nie w granicy, porównania byłyby inne"]
    assert notes_for(unknown=set()) == []                # the falsifier

def test_each_note_names_a_question_the_user_can_take_to_the_gmina(tree):
    for note in nodes_by_role(tree, "sensitivity_note"):
        assert note.meta["action"]["office"].startswith("Urząd Gminy")
        assert note.meta["action"]["document"] == "wypis i wyrys"
```

`constant_caveat` fails on the fully-known case (a note where there must be none)
and on the missing `meta["action"]`.

`test_notes_are_ordered_by_the_size_of_the_difference_they_would_make` uses a
fixture whose stratum gaps are `buildability: 34 zł/m²`, `road_access: 11 zł/m²`,
`utilities: 4 zł/m²`, and asserts that order.

### 3.14 U14 — the comparable set is shown before the verdict

**Passes** — §2.3: `comparable_set` at document index 7, `verdict` at 8.

**Fails** — `dishonest/verdict_first.py`: the same two nodes, swapped.

**Assertion**

```python
def test_comparable_set_precedes_the_verdict_block(tree):
    cs = one(nodes_by_role(tree, "comparable_set"))
    v  = one(nodes_by_role(tree, "verdict"))
    assert index_of(tree, cs) < index_of(tree, v)

def test_every_comparable_carries_its_nie_pasuje_control(tree):
    for c in nodes_by_role(tree, "comparable"):
        assert c.meta["exclude_control"] == {
            "comparable_id": c.meta["comparable_id"], "label": "nie pasuje"}
```

`test_every_comparable_is_listed_with_its_own_price_area_and_distance` asserts
each `comparable` text matches
`r"^\d+ zł/m² · [\d\u00a0]+ m² · gmina .+ · \d\d\.\d\d\.\d{4}$"` and carries both
label children.

`test_ordering_survives_a_recompute` re-runs the first assertion on the tree
produced by §8's exclusion.

---

## 4. The five states, for every registry component

### 4.1 The state machine, and that it is derived

```python
def state_of(payload) -> State:
    if payload.exception is not None:            return "error"
    if payload.pending:                          return "loading"
    if payload.absent:                           return "empty"
    if payload.n < thin_n_threshold:             return "thin"
    if (now - payload.as_of).days > staleness_threshold_days: return "stale"
    return "normal"
```

`test_state_is_derived_not_passed` asserts `render_*` takes no `state` argument
(signature inspection) and that a payload with `n = 4` renders `state == "thin"`
however it is labelled by the caller. Precedence is asserted explicitly by
`test_state_precedence_is_error_loading_empty_thin_stale`, using a payload that is
simultaneously thin and stale (n = 4, as_of 12 days old) — it renders `thin`, and
still carries its `staleness` node, because a state label is not permission to
drop a qualifier.

### 4.2 The four absence reasons — exact Polish copy

Used by every component's `empty` state.

| `absence_reason` | `absence` node text | `basis` child text (the next action) |
|---|---|---|
| `not_yet_crawled` | `Brak danych — tej gminy jeszcze nie zebraliśmy` | `jeszcze nie zebraliśmy — sprawdź później` |
| `no_listings` | `Brak danych — w tej gminie nie ma ofert` | `brak ofert w tej gminie` |
| `out_of_scope` | `Brak danych — ta gmina jest poza zasięgiem narzędzia` | `poza zasięgiem narzędzia` |
| `too_few_comparables` | `Brak danych — za mało podobnych ofert` | `za mało podobnych ofert, żeby porównać` |

All four carry `tone: "warning"`, `prominence: "equal"`, `disclosure: "always"`.

`test_absence_reason_enum_matches_the_api_contract` maps the render enum onto
[`14-api-contract.md`](../../14-api-contract.md) §2.3:

| render reason | API reason |
|---|---|
| `not_yet_crawled` | `not_yet_crawled` |
| `out_of_scope` | `out_of_scope` |
| `too_few_comparables` | `no_comparables` |
| `no_listings` | **no counterpart** — see OPEN-S6 |

### 4.3 The canonical five, written out — `flow_aggregate_block`

```
# loading
aggregate_block[primary,always] "Podobne oferty (przepływ, ostatnie 90 dni)"  {state:"loading"}
    loading[equal,always] "wczytywanie podobnych ofert…"

# empty (reason not_yet_crawled)
aggregate_block[primary,always] "Podobne oferty (przepływ, ostatnie 90 dni)"  {state:"empty"}
    absence[equal,always] "Brak danych — tej gminy jeszcze nie zebraliśmy"    {absence_reason:"not_yet_crawled", tone:"warning"}
        basis[equal,always] "jeszcze nie zebraliśmy — sprawdź później"

# thin  (AGG_THIN_N4)
aggregate_block[primary,always] "Podobne oferty (przepływ, ostatnie 90 dni)"  {state:"thin", n:4}
    flow_window_label[equal,always] "ostatnie 90 dni"
    value[equal,always]         "mediana 118 zł/m²"
    spread[equal,always]        "zakres 61–240"
    sample_size[equal,always]   "n = 4"
    price_type_label[equal,always] "cena ofertowa"
    price_kind_label[equal,always] "oferta"
    uncertainty_note[equal,always] "Zakres szeroki — mało podobnych ofert"
    provenance[equal,expander] "Źródło i metoda"

# stale  (AGG_STALE_12D)
aggregate_block[primary,always] "Podobne oferty (przepływ, ostatnie 90 dni)"  {state:"stale", n:23}
    flow_window_label[equal,always] "ostatnie 90 dni"
    value[equal,always]         "mediana 118 zł/m²"
    staleness[equal,always]     "dane sprzed 12 dni · ostatnie pobranie 27.07.2026"
    spread[equal,always]        "zakres międzykwartylowy 96–141"
    sample_size[equal,always]   "n = 23"
    price_type_label[equal,always] "cena ofertowa"
    price_kind_label[equal,always] "oferta"
    provenance[equal,expander] "Źródło i metoda"

# error
aggregate_block[primary,always] "Podobne oferty (przepływ, ostatnie 90 dni)"  {state:"error"}
    error[equal,always] "Nie udało się policzyć przepływu — stan poniżej jest aktualny"  {tone:"warning", field:"flow_aggregate"}
```

Every other component follows this shape. §4.4 gives the strings that differ.

### 4.4 The full registry × states table

`test_every_registered_component_defines_all_five_states` is parametrized over
these 70 rows and asserts the leaf text exactly.

| Component | State | Exact text of the state-bearing node |
|---|---|---|
| `plot_check_header` | loading | `wczytywanie danych o działce…` |
| | empty | `Brak danych — ta gmina jest poza zasięgiem narzędzia` / `poza zasięgiem narzędzia` |
| | thin | header text unchanged + `Mało podobnych ofert — wynik orientacyjny` |
| | stale | header text unchanged + `dane sprzed 12 dni · ostatnie pobranie 27.07.2026` |
| | error | `Nie udało się odczytać ogłoszenia — wpisz powierzchnię i gminę ręcznie` |
| `verdict_block` | loading | `wczytywanie werdyktu…` |
| | empty | `Brak danych — za mało podobnych ofert` / `za mało podobnych ofert, żeby porównać` |
| | thin | `WERDYKT` (`prominence:"secondary"`, preceded by the out-of-depth notice) |
| | stale | `WERDYKT` + `dane sprzed 12 dni · ostatnie pobranie 27.07.2026` |
| | error | `Nie udało się policzyć werdyktu — podobne oferty powyżej są aktualne` |
| `comparable_set` | loading | `wczytywanie podobnych ofert…` |
| | empty | `Brak danych — w tej gminie nie ma ofert` / `brak ofert w tej gminie` |
| | thin | `Podobne oferty — 3` + `Mało podobnych ofert — wynik orientacyjny` |
| | stale | `Podobne oferty — 23` + `dane sprzed 12 dni · ostatnie pobranie 27.07.2026` |
| | error | `Nie udało się pobrać podobnych ofert — cena z ogłoszenia powyżej jest aktualna` |
| `flow_aggregate_block` | loading | `wczytywanie podobnych ofert…` |
| | empty | `Brak danych — tej gminy jeszcze nie zebraliśmy` / `jeszcze nie zebraliśmy — sprawdź później` |
| | thin | §4.3 |
| | stale | §4.3 |
| | error | `Nie udało się policzyć przepływu — stan poniżej jest aktualny` |
| `stock_aggregate_block` | loading | `wczytywanie wszystkich aktywnych ofert…` |
| | empty | `Brak danych — w tej gminie nie ma ofert` / `brak ofert w tej gminie` |
| | thin | `mediana 127 zł/m²` / `zakres 99–168` / `n = 4` / `Zakres szeroki — mało podobnych ofert` |
| | stale | `dane sprzed 12 dni · ostatnie pobranie 27.07.2026` |
| | error | `Nie udało się policzyć stanu — przepływ powyżej jest aktualny` |
| `gus_sales_block` | loading | `wczytywanie cen transakcyjnych…` |
| | empty | `Brak danych — tej gminy jeszcze nie zebraliśmy` / `jeszcze nie zebraliśmy — sprawdź później` |
| | thin | `średnia 104 zł/m²` / `zakres niedostępny — GUS publikuje tylko średnią` / `n = 3` / `Nie znamy rozrzutu — GUS publikuje tylko średnią` |
| | stale | `dane sprzed 220 dni · ostatnie pobranie 31.12.2025` |
| | error | `Nie udało się pobrać danych GUS — ceny ofertowe poniżej są aktualne` |
| `standard_plot_benchmark` | loading | `wczytywanie typowej działki…` |
| | empty | `Brak danych — za mało podobnych ofert` / `za mało podobnych ofert, żeby porównać` |
| | thin | `Typowa działka 3 000 m² pod zabudowę ≈ 354 000 zł` / `zakres 183 000–720 000` / `n = 4` / `Zakres szeroki — mało podobnych ofert` |
| | stale | `dane sprzed 12 dni · ostatnie pobranie 27.07.2026` |
| | error | `Nie udało się policzyć typowej działki — mediany powyżej są aktualne` |
| `uncertainty_panel` | loading | `wczytywanie oceny pewności…` |
| | empty | `Brak danych — za mało podobnych ofert` / `za mało podobnych ofert, żeby porównać` |
| | thin | `za mało danych, żeby ocenić — to jest orientacja, nie wycena` |
| | stale | `Zakres szeroki — mało podobnych ofert` + `dane sprzed 12 dni · ostatnie pobranie 27.07.2026` |
| | error | `Nie udało się ocenić pewności — liczby powyżej są aktualne` |
| `map_feature` | loading | `wczytywanie mapy…` |
| | empty | `Brak danych — w tej gminie nie ma ofert` / `brak ofert w tej gminie` |
| | thin | `gmina Nowy Kawęczyn · n = 3` (`pattern:"hatch"`, `fill` set) |
| | stale | `gmina Skierniewice · n = 23` + `dane sprzed 12 dni · ostatnie pobranie 27.07.2026` |
| | error | `Nie udało się narysować mapy — tabela poniżej jest aktualna` |
| `map_legend` | loading | `wczytywanie legendy…` |
| | empty | `Brak danych — w żadnej gminie nie ma ofert` / `brak ofert w tej gminie` |
| | thin | `cena ofertowa · oferta · przepływ, ostatnie 90 dni` + `mało ofert (n < 5) — kolor słabo poparty` |
| | stale | legend title + `dane sprzed 12 dni · ostatnie pobranie 27.07.2026` |
| | error | `Nie udało się zbudować legendy — kolory na mapie są nieopisane` |
| `gmina_panel` | loading | `wczytywanie danych gminy…` |
| | empty | `Brak danych — tej gminy jeszcze nie zebraliśmy` / `jeszcze nie zebraliśmy — sprawdź później` |
| | thin | `gmina Nowy Kawęczyn` + `za mało danych, żeby ocenić — to jest orientacja, nie wycena` |
| | stale | `gmina Skierniewice` + `dane sprzed 12 dni · ostatnie pobranie 27.07.2026` |
| | error | `Nie udało się otworzyć panelu gminy — tabela poniżej jest aktualna` |
| `gmina_table_row` | loading | `wczytywanie wiersza…` |
| | empty | `Brak danych — ta gmina jest poza zasięgiem narzędzia` / `poza zasięgiem narzędzia` |
| | thin | `gmina Nowy Kawęczyn · mediana 118 zł/m² · zakres 61–240 · n = 4` |
| | stale | `gmina Skierniewice · mediana 118 zł/m² · zakres międzykwartylowy 96–141 · n = 23` + `dane sprzed 12 dni · ostatnie pobranie 27.07.2026` |
| | error | `Nie udało się policzyć tego wiersza — pozostałe gminy są aktualne` |
| `coverage_row` | loading | `wczytywanie pokrycia…` |
| | empty | `Brak danych — tej gminy jeszcze nie zebraliśmy` / `jeszcze nie zebraliśmy — sprawdź później` |
| | thin | `gmina Nowy Kawęczyn · zebrane oferty: 4 · ostatnie pobranie 06.08.2026 · źródła: portal_a` |
| | stale | `gmina Skierniewice · zebrane oferty: 23 · ostatnie pobranie 27.07.2026` + `dane sprzed 12 dni · ostatnie pobranie 27.07.2026` |
| | error | `Nie udało się policzyć pokrycia — pozostałe gminy są aktualne` |
| `provenance_panel` | loading | `wczytywanie źródeł…` |
| | empty | `Brak danych — tej gminy jeszcze nie zebraliśmy` / `jeszcze nie zebraliśmy — sprawdź później` |
| | thin | `Źródło: portal_a` / `Liczba obserwacji: n = 4` |
| | stale | `Stan na: 27.07.2026` + `dane sprzed 12 dni · ostatnie pobranie 27.07.2026` |
| | error | `Nie udało się odczytać źródeł — liczby powyżej pochodzą z bazy` |

Standard-plot benchmark arithmetic (O7), so the strings above can be checked:
median 118 × 3 000 = 354 000; thin case 61 × 3 000 = 183 000 and 240 × 3 000 =
720 000. `test_standard_plot_benchmark_states_its_basis` asserts the `basis` child
reads `wyliczone z mediany podobnych ofert, nie zaobserwowana cena` and that
`meta["basis"] == "derived"`.

GUS staleness arithmetic: the convention is `(now - as_of).days`, exclusive of the
`as_of` date. 2025-12-31 → 2026-08-08 is **220** days, so the row reads
`dane sprzed 220 dni`; an inclusive count would render 221 and is the off-by-one
this pins. `test_staleness_day_count_is_exclusive_of_the_as_of_date` fixes it with
a one-day fixture: `as_of = 2026-08-07`, `now = 2026-08-08` → `dane sprzed 1 dnia`
(singular form, §5.6).

### 4.5 Independent degradation

```python
def test_a_failed_sales_query_does_not_blank_the_offering_block():
    tree = build_plot_check(PLOT_CHECK_SKIERNIEWICE_142,
                            gus_source=raises(ConnectorError("BDL 503")))
    gus  = component(tree, "gus_sales_block")
    flow = component(tree, "flow_aggregate_block")
    stock= component(tree, "stock_aggregate_block")

    assert gus.meta["state"] == "error"
    assert one(nodes_by_role(gus, "error")).text == \
        "Nie udało się pobrać danych GUS — ceny ofertowe poniżej są aktualne"
    assert flow.meta["state"] == "normal" and stock.meta["state"] == "normal"
    assert one(nodes_by_role(flow, "value")).text  == "mediana 118 zł/m²"
    assert one(nodes_by_role(stock, "value")).text == "mediana 127 zł/m²"
    assert nodes_by_role(flow, "sample_size")[0].text == "n = 23"
```

`test_a_failed_map_tile_does_not_blank_the_gmina_table` is the same property on
item 12: `map_feature` in `error`, every `gmina_table_row` still `normal`.

---

## 5. Polish formatting — exact inputs, exact outputs

`tests/unit/app/test_format.py`. Codepoints are written explicitly; the tests
assert on codepoints, never on visual appearance.

### 5.1 The separators, by codepoint

| Purpose | Character | Codepoint | Forbidden alternatives |
|---|---|---|---|
| Thousands separator | NO-BREAK SPACE | **U+00A0** | U+0020 SPACE, U+202F NARROW NBSP, U+2009 THIN SPACE, `,`, `.`, `'` |
| Number ↔ unit separator | NO-BREAK SPACE | **U+00A0** | U+0020, no separator at all |
| Decimal separator | COMMA | **U+002C** | `.` |
| Range separator | EN DASH | **U+2013** | `-` U+002D, `—` U+2014, ` – ` with spaces |
| Field separator | ` · ` = SPACE + MIDDLE DOT + SPACE | **U+0020 U+00B7 U+0020** | `|`, `,`, ` - ` |
| Negative sign | HYPHEN-MINUS | **U+002D** | U+2212 MINUS SIGN |
| Superscript two | SUPERSCRIPT TWO | **U+00B2** | `2`, `^2` |
| Ellipsis (loading) | HORIZONTAL ELLIPSIS | **U+2026** | `...` |
| Em dash (in sentences) | EM DASH | **U+2014** | `-`, `--` |

```python
NBSP = "\u00a0"

def test_thousands_separator_is_a_non_breaking_space():
    out = format_int(1234567)
    assert out == f"1{NBSP}234{NBSP}567"
    assert out == "1\u00a0234\u00a0567"
    for forbidden in ("\u0020", "\u202f", "\u2009", ",", ".", "'"):
        assert forbidden not in out
```

### 5.2 Integers

| Input | Expected output | Escaped |
|---|---|---|
| `0` | `0` | `"0"` |
| `999` | `999` | `"999"` |
| `1000` | `1 000` | `"1\u00a0000"` |
| `3200` | `3 200` | `"3\u00a0200"` |
| `12345` | `12 345` | `"12\u00a0345"` |
| `454400` | `454 400` | `"454\u00a0400"` |
| `1234567` | `1 234 567` | `"1\u00a0234\u00a0567"` |
| `-1234` | `-1 234` | `"-1\u00a0234"` |

### 5.3 Decimals

| Input | Places | Expected | Escaped |
|---|---|---|---|
| `Decimal("118.5")` | 1 | `118,5` | `"118,5"` |
| `Decimal("0.381")` | 1 | `0,4` | `"0,4"` |
| `Decimal("1234.56")` | 2 | `1 234,56` | `"1\u00a0234,56"` |
| `Decimal("104")` | 1 | `104,0` | `"104,0"` |

`test_decimal_separator_is_a_comma` additionally asserts
`format_decimal(Decimal("1234.56"), 2) != "1,234.56"` — V37's named falsifier,
asserted as an inequality so a locale-derived implementation fails loudly.

### 5.4 Prices, areas, ranges

| Call | Expected | Escaped |
|---|---|---|
| `format_ppm2(Decimal("142"))` | `142 zł/m²` | `"142\u00a0zł/m²"` |
| `format_ppm2(Decimal("142.4999"))` | `142 zł/m²` | `"142\u00a0zł/m²"` |
| `format_ppm2(Decimal("142.5"))` | `143 zł/m²` | `"143\u00a0zł/m²"` (ROUND_HALF_UP) |
| `format_ppm2(Decimal("1180"))` | `1 180 zł/m²` | `"1\u00a0180\u00a0zł/m²"` |
| `format_pln(454400)` | `454 400 zł` | `"454\u00a0400\u00a0zł"` |
| `format_area(3200)` | `3 200 m²` | `"3\u00a0200\u00a0m²"` |
| `format_area(1200)` | `1 200 m²` | `"1\u00a0200\u00a0m²"` |
| `format_range(96, 141)` | `96–141` | `"96–141"` |
| `format_range(1600, 4800)` | `1 600–4 800` | `"1\u00a0600–4\u00a0800"` |
| `format_range(61, 240)` | `61–240` | `"61–240"` |
| `format_ratio(Decimal("0.3814"))` | `0,4` | one decimal, never more |

Forbidden unit variants asserted absent from every fixture tree by
`test_price_unit_is_zl_per_m2_with_a_superscript_two`:
`zl/m2`, `PLN/m2`, `zł/m2`, `zł / m²`, `PLN/m²`, `m2`, `m^2`.
Output never uses *ar* or *hektar* — `test_area_uses_m2_and_never_ar_or_ha_in_output`
asserts the tokens `ar`, `arów`, `ha`, `hektar` are absent from every rendered
tree, while §7.3 asserts they are accepted on **input**.

### 5.5 Dates and quarters

| Call | Expected |
|---|---|
| `format_date(date(2026, 8, 1))` | `01.08.2026` |
| `format_date(date(2026, 8, 8))` | `08.08.2026` |
| `format_date(date(2026, 7, 27))` | `27.07.2026` |
| `format_date(date(2025, 12, 31))` | `31.12.2025` |
| `format_quarter(2025, 4)` | `2025Q4` |
| `format_source_quarter("gus_bdl", 2025, 4)` | `GUS 2025Q4` |

Zero-padding is asserted for both day and month; `1.8.2026` fails.
`test_formatting_is_locale_independent` runs the whole table twice, under
`LC_ALL=C` and `LC_ALL=pl_PL.UTF-8`, and asserts identical output — nothing may
read the process locale.

### 5.6 Polish plurals on the staleness string

`dzień / dni` is the only inflected count in the surface, and getting it wrong is
visible on every stale number.

| days | Expected staleness text |
|---|---|
| `1` | `dane sprzed 1 dnia · ostatnie pobranie 07.08.2026` |
| `2` | `dane sprzed 2 dni · ostatnie pobranie 06.08.2026` |
| `12` | `dane sprzed 12 dni · ostatnie pobranie 27.07.2026` |
| `220` | `dane sprzed 220 dni · ostatnie pobranie 31.12.2025` |

The genitive plural `dni` covers every count except 1, so the rule is a single
special case, and `test_staleness_plural` parametrizes all four rows.

### 5.7 The sweep

```python
def test_no_rendered_number_uses_a_dot_decimal_sweep():
    for tree in every_fixture_tree():
        for token in text_tokens(tree):
            assert not re.search(r"\d\.\d", token), token          # dot decimal
            assert not re.search(r"\d,\d{3}\b", token), token       # comma thousands
```

Both patterns must be checked: `1,234.56` trips the first, `1,234` alone trips the
second. `2026Q4`-style tokens and `cmp-2026.08.1` are exempted by an explicit
allowlist of two regexes, itself asserted exercised.

---

## 6. Terminology lint

`scripts/lint_ui_terms.py`, tests in `tests/unit/app/test_terminology_lint.py`.

### 6.1 The protected-term list

Read from the document at lint time, never duplicated in code
(`test_glossary_protected_list_is_read_from_the_document`). The list is the one
stated in [`09-ux-specification.md`](../../09-ux-specification.md) §4 and defined
in [`12-glossary.md`](../../12-glossary.md).

| # | Protected term | Forbidden rendering | Source of the prohibition |
|---|---|---|---|
| 1 | `cena ofertowa` | `cena rynkowa`, `market price`, `cena` alone | `12` §Prices, explicit |
| 2 | `cena transakcyjna` | `cena` unqualified, `transaction price`, `cena sprzedaży` | `12` §Prices, explicit |
| 3 | `plan ogólny` | `plan`, `studium`, `general plan` | `09` §4; `12` §Planning (replaced *studium*) |
| 4 | `MPZP` | `plan` alone, `plan miejscowy` where the acronym is meant, `zoning plan` | `09` §4 |
| 5 | `wypis i wyrys` | `wypis`, `wyrys`, `zaświadczenie`, `extract` | `09` §4; `12` — the binding document |
| 6 | `działka` | `parcela`, `grunt`, `plot`, `parcel` | `09` §4; `12` distinguishes `plot` from `parcel` |
| 7 | `media` | `infrastruktura`, `przyłącza`, `utilities` | `09` §4 |
| 8 | `droga dojazdowa` | `dojazd` alone, `droga`, `access` | `09` §4; `12` §Infrastructure |

Two further terms are lint-checked because the surface uses them and the glossary
defines them, though `09` §4 does not name them protected:

| # | Term | Forbidden rendering |
|---|---|---|
| 9 | `służebność przejazdu` | `służebność` alone, `easement` |
| 10 | `klasa gruntu` | `klasa`, `soil class` |

**OPEN-S2.** `06-surface.md` §8.3 cites "`12-glossary.md` §4" as the location of
the protected list. `12` has no numbered sections, and its fourth section is
*Infrastructure and access*; the list actually lives in `09` §4. The lint needs a
single machine-readable home. **Proposal:** add a `## Protected terms` section to
`12-glossary.md` holding this table, and have both `09` §4 and `06-surface.md`
§8.3 point at it. Needs ratification before step 17 of the red-green sequence.

### 6.2 Seeded violations the lint must fail

`test_lint_flags_a_seeded_violation` runs the lint over
`tests/fixtures/app/dishonest/bad_terms.py` and asserts one finding per line,
with the line number and the term named:

```python
# tests/fixtures/app/dishonest/bad_terms.py
BAD_1  = "cena rynkowa 118 zł/m²"                              # → term 1
BAD_2  = "mediana ceny w tej gminie to 104 zł/m²"              # → term 2 (cena unqualified)
BAD_3  = "Sprawdź plan przed zakupem"                          # → terms 3, 4 (plan alone)
BAD_4  = "Poproś o wypis w urzędzie gminy"                     # → term 5
BAD_5  = "Ta parcela ma 3 200 m²"                              # → term 6
BAD_6  = "Przyłącza w granicy działki"                         # → term 7
BAD_7  = "Dojazd drogą gruntową"                               # → term 8
BAD_8  = "Działka ze służebnością"                             # → term 9
BAD_9  = "market price 118 PLN/m2"                             # → term 1 + §8.2 + §5.4
```

**The single example that must fail**, quoted for the developer to paste into the
first red run:

```
"Mediana ceny rynkowej dla tej parceli to 118 zł/m² — sprawdź plan w gminie."
```

Expected lint output, asserted as an exact list:

```
bad_terms.py:1: protected term `cena ofertowa` rendered as `cena rynkowa`
bad_terms.py:1: protected term `działka` rendered as `parcela`
bad_terms.py:1: protected term `MPZP` rendered as `plan`
bad_terms.py:1: protected term `plan ogólny` rendered as `plan`
```

Three findings on one line is the point: `test_lint_reports_every_violation_on_a_line`
asserts the lint does not stop at the first.

### 6.3 The other two lint tests

- `test_every_domain_term_used_in_the_ui_exists_in_the_glossary` — the lint
  extracts domain nouns from every string constant in `render/` and asserts each
  appears in the glossary's Polish column. Seeded failure: `"grunt inwestycyjny"`,
  a plausible invented synonym absent from `12`.
- `test_no_ui_string_contains_an_english_stopword` —
  `{"median", "range", "price", "unknown", "loading", "error", "no data", "sample"}`
  absent from every string in `render/`. **Allowlist of one:** the word `tool` in
  the §7.2 honest disclosure, quoted verbatim from `21`. The allowlist is asserted
  to have exactly one entry, so it cannot grow silently.

---

## 7. URL paste

`tests/unit/app/test_url_paste.py`, `tests/unit/app/portals/test_portal_a.py`,
`test_portal_b.py`. Parsing runs against recorded fixture pages; no network.

### 7.1 The four cases and their user-visible outcomes

**Case 1 — well-formed, supported portal, parseable page**

Input: `https://portal-a.example/oferta/dzialka-budowlana-skierniewice-3200m2-ID9x2Kq.html`

Fixture: `tests/fixtures/app/listing_pages/portal_a/ID9x2Kq.html`
Expected: `tests/fixtures/app/listing_pages/portal_a/ID9x2Kq.expected.json`

```json
{
  "listing_id": "ID9x2Kq",
  "portal": "portal_a",
  "area_m2": 3200,
  "price_pln": 454400,
  "price_per_m2": "142.00",
  "locality": "Budy Grabskie",
  "teryt": "1015042",
  "price_type": "offering",
  "price_kind": "asking",
  "first_seen": "2026-07-14",
  "fetched_at": "2026-08-08T09:12:00+02:00",
  "parser_version": "portal_a-2026.08.1",
  "raw_document_sha256": "9f2c…"
}
```

User-visible outcome: the §2.3 golden tree. No `error` node, no `fallback_form`.

**Case 2 — unsupported host**

Input: `https://nieznany-portal.example/ogloszenie/12345`

```
section[primary,always] "Sprawdzenie działki"
    error[equal,always] "Nie obsługujemy tego portalu — wpisz powierzchnię i gminę ręcznie"
        {tone:"warning", field:"url", host:"nieznany-portal.example"}
    fallback_form[primary,always] "Wpisz dane działki"
        value[equal,always] "Powierzchnia (m²)"     {field:"area_m2",  prefill:None}
        value[equal,always] "Gmina"                 {field:"teryt",    prefill:None}
        value[equal,always] "Cena (zł)"             {field:"price_pln",prefill:None}
```

Builder raises `UnsupportedPortalError`, caught at the surface boundary and turned
into this tree. Assertions:

```python
def test_unsupported_portal_is_rejected_by_name(tree):
    err = one(nodes_by_role(tree, "error"))
    assert err.text == "Nie obsługujemy tego portalu — wpisz powierzchnię i gminę ręcznie"
    assert err.meta["host"] == "nieznany-portal.example"
    assert nodes_by_role(tree, "fallback_form")
    assert nodes_by_role(tree, "verdict") == []
    assert nodes_by_role(tree, "aggregate_block") == []
    assert "zł/m²" not in " ".join(text_tokens(tree))
```

The last three clauses are the "never a guess" half: an unsupported host must not
degrade into the gmina average inferred from the URL slug.

**Case 3 — supported host, page cannot be parsed**

Input: `https://portal-a.example/oferta/dzialka-ID0000.html`
Fixture: `listing_pages/portal_a/portal_a_layout_changed.html`

```
section[primary,always] "Sprawdzenie działki"
    error[equal,always] "Nie udało się odczytać tej strony — wpisz powierzchnię i gminę ręcznie"
        {tone:"warning", field:"page", raw_document_sha256:"3ab1…",
         parser_version:"portal_a-2026.08.1"}
        value[equal,always] "nie udało się odczytać powierzchni — wpisz ją"  {field:"area_m2"}
        value[equal,always] "nie udało się odczytać ceny — wpisz ją"         {field:"price_pln"}
        value[equal,always] "nie udało się odczytać gminy — wpisz ją"        {field:"teryt"}
    fallback_form[primary,always] "Wpisz dane działki"
        value[equal,always] "Powierzchnia (m²)"     {field:"area_m2",  prefill:None}
        value[equal,always] "Gmina"                 {field:"teryt",    prefill:None}
        value[equal,always] "Cena (zł)"             {field:"price_pln",prefill:None}
```

```python
def test_total_parse_failure_renders_the_manual_entry_fallback(tree):
    assert nodes_by_role(tree, "fallback_form")
    assert nodes_by_role(tree, "verdict")          == []
    assert nodes_by_role(tree, "aggregate_block")  == []
    assert "zł/m²" not in " ".join(text_tokens(tree))

def test_a_changed_layout_fixture_fails_loudly():
    with pytest.raises(ParseFailure):
        parse_portal_a(read("portal_a_layout_changed.html"))
```

`test_a_changed_layout_fixture_fails_loudly` is the one that matters: a parser
returning a partial record that *looks* complete passes every other test in this
section. The fixture is a real portal-A page with the price container renamed and
the area block removed.

`test_parse_failure_is_logged_with_the_raw_document_hash` asserts one log row
`{url, portal, parser_version, raw_document_sha256, failed_fields, failed_at}` —
so the fix is a re-parse, not a re-crawl.

**Case 3b — partial parse.** Price found, area not:

```
    error[equal,always] "Nie udało się odczytać całej strony — uzupełnij brakujące pole"
        value[equal,always] "nie udało się odczytać powierzchni — wpisz ją"  {field:"area_m2"}
    fallback_form[primary,always] "Wpisz dane działki"
        value[equal,always] "Powierzchnia (m²)"  {field:"area_m2",  prefill:None}
        value[equal,always] "Gmina"              {field:"teryt",    prefill:"1015042"}
        value[equal,always] "Cena (zł)"          {field:"price_pln",prefill:454400}
```

`test_partial_parse_asks_for_the_missing_field_only` asserts exactly one
`nie udało się odczytać …` child, the other two fields prefilled, and — the real
assertion — that **no** `zł/m²` string exists anywhere in the tree, because a
price with no area cannot produce one.

**Case 4 — not a URL at all**

Input: `3200 m2 Skierniewice`

```
    error[equal,always] "To nie jest adres strony — wklej link do ogłoszenia albo wpisz dane ręcznie"
        {tone:"warning", field:"url"}
    fallback_form[primary,always] "Wpisz dane działki"
        …prefilled: area_m2 = None, teryt = None, price_pln = None
```

`test_a_non_url_input_is_rejected_without_a_traceback` asserts the tree is built
and no exception escapes; the prefill is `None` on all three, because guessing
`3200` out of free text is exactly the silent inference this section forbids.

**Case 5 — robots.txt disallows the portal**

```
    error[equal,always] "Ten portal nie pozwala na pobieranie stron — wpisz powierzchnię i gminę ręcznie"
        {tone:"warning", field:"robots", host:"portal-b.example"}
    fallback_form[primary,always] "Wpisz dane działki"
```

`test_paste_is_refused_when_robots_disallows_the_portal` asserts the tree **and**
that the fetcher was never called (a fake transport recording zero requests) —
the work-item-0 gate reaching the surface. Blocked on O10.

### 7.2 Dispatch table

`test_url_is_routed_to_the_parser_for_its_portal`, parametrized:

| Input URL | Routed to |
|---|---|
| `https://portal-a.example/oferta/dzialka-ID9x2Kq.html` | `portal_a` |
| `http://portal-a.example/oferta/dzialka-ID9x2Kq.html` | `portal_a` |
| `https://www.portal-a.example/oferta/dzialka-ID9x2Kq.html` | `portal_a` |
| `https://m.portal-a.example/oferta/dzialka-ID9x2Kq.html` | `portal_a` |
| `https://portal-a.example/oferta/dzialka-ID9x2Kq.html?utm_source=x#opis` | `portal_a` |
| `https://portal-b.example/d/12345/dzialka` | `portal_b` |
| `https://nieznany-portal.example/ogloszenie/12345` | `UnsupportedPortalError` |
| `3200 m2 Skierniewice` | `NotAUrlError` |
| `javascript:alert(1)` | `NotAUrlError` |
| `file:///etc/passwd` | `NotAUrlError` |

### 7.3 Unit conversion at the paste boundary (F1)

| Fixture page states | `area_m2` | Falsified by |
|---|---|---|
| `3200 m²` | `3200` | — |
| `3 200 m2` (NBSP in source) | `3200` | `3` |
| `12 arów` | `1200` | `12` |
| `12 a` | `1200` | `12` |
| `0,35 ha` | `3500` | `0`, `35`, `0.35` |
| `1,5 hektara` | `15000` | `1`, `15` |
| `0,32 ha` | `3200` | — |

Note the comma decimal in the source text: `test_page_stating_hektar_converts_to_m2`
fails if the parser calls `float("0,35")` or truncates at the comma.

`test_implausible_area_is_quarantined_not_rendered`: a page stating `320000 m²`
(outside FR-12's 300–200 000 band) produces

```
    error[equal,always] "Powierzchnia z ogłoszenia jest nieprawdopodobna — sprawdź i wpisz ręcznie"
        {tone:"warning", field:"area_m2", parsed_value:320000}
    fallback_form[primary,always] "Wpisz dane działki"
```

and the tree contains **no** `zł/m²` token. A 100× area error is silent and fatal,
so the surface refuses rather than displays.

---

## 8. Comparable exclusion (V51c)

`tests/unit/app/test_comparable_exclusion.py`,
`tests/unit/app/test_exclusion_report.py`.

### 8.1 `COMP_SET_N6_CONSTRUCTED`

Six comparables, hand-computed under R-7. Subject `subj_0001`.

| id | zł/m² | area m² | gmina | listing date | `road_access` |
|---|---|---|---|---|---|
| `cmp_01` | 96 | 4 100 | Skierniewice | 21.05.2026 | `easement` |
| `cmp_02` | 104 | 3 600 | Skierniewice | 02.06.2026 | `easement` |
| `cmp_03` | 112 | 2 800 | Skierniewice | 12.06.2026 | `public_main` |
| `cmp_04` | 124 | 3 400 | Skierniewice | 03.07.2026 | `public_main` |
| `cmp_05` | 138 | 3 000 | Skierniewice | 19.07.2026 | `public_main` |
| `cmp_hi` | 210 | 1 700 | Skierniewice | 28.07.2026 | `public_main` |

Sorted: `[96, 104, 112, 124, 138, 210]`, n = 6, R-7 index = `(n−1)·q = 5q`.

- median: index 2.5 → `112 + 0.5·(124−112)` = **118.00**
- p25: index 1.25 → `104 + 0.25·(112−104)` = **106.00**
- p75: index 3.75 → `124 + 0.75·(138−124)` = **134.50**
- `n = 6 ≥ 5` → `kind = "iqr"`

### 8.2 The before tree

```
section[primary,always] "Sprawdzenie działki"                {subject_id:"subj_0001"}

    aggregate_block[primary,always] "Podobne oferty (przepływ, ostatnie 90 dni)"
        {component:"flow_aggregate_block", state:"normal", basis:"flow",
         flow_window_days:90, n:6, median:118.00,
         range:{low:106.00, high:134.50, kind:"iqr"}}
        flow_window_label[equal,always] "ostatnie 90 dni"
        value[equal,always]         "mediana 118 zł/m²"
        spread[equal,always]        "zakres międzykwartylowy 106–135"
        sample_size[equal,always]   "n = 6"
        price_type_label[equal,always] "cena ofertowa"
        price_kind_label[equal,always] "oferta"
        provenance[equal,expander] "Źródło i metoda"

    comparable_set[primary,always] "Podobne oferty — 6"      {n:6}
        comparable[equal,always] "96 zł/m² · 4 100 m² · gmina Skierniewice · 21.05.2026"   {comparable_id:"cmp_01", exclude_control:{comparable_id:"cmp_01", label:"nie pasuje"}}
        comparable[equal,always] "104 zł/m² · 3 600 m² · gmina Skierniewice · 02.06.2026"  {comparable_id:"cmp_02", …}
        comparable[equal,always] "112 zł/m² · 2 800 m² · gmina Skierniewice · 12.06.2026"  {comparable_id:"cmp_03", …}
        comparable[equal,always] "124 zł/m² · 3 400 m² · gmina Skierniewice · 03.07.2026"  {comparable_id:"cmp_04", …}
        comparable[equal,always] "138 zł/m² · 3 000 m² · gmina Skierniewice · 19.07.2026"  {comparable_id:"cmp_05", …}
        comparable[equal,always] "210 zł/m² · 1 700 m² · gmina Skierniewice · 28.07.2026"  {comparable_id:"cmp_hi", …}

    verdict[secondary,expander] "WERDYKT"                    {expanded:False}
        value[equal,always] "Powyżej górnej granicy zakresu przepływu (106–135)"
        basis[equal,always] "Podstawa: 6 ofert, ta sama gmina, 1 600–4 800 m², ostatnie 90 dni"
```

`zakres międzykwartylowy 106–135` — 134.50 rounds ROUND_HALF_UP to 135 for
display, while `meta["range"]["high"]` keeps `134.50`.
`test_display_rounding_does_not_reach_the_meta` asserts both.

Note `6 ofert`, not `6 oferty` — Polish genitive plural for 5–21.
`test_verdict_basis_plural` parametrizes `n ∈ {1, 2, 5, 6, 22, 23}` against
`{1 oferta, 2 oferty, 5 ofert, 6 ofert, 22 oferty, 23 oferty}`.

### 8.3 The excluded comparable

The user clicks `nie pasuje` on:

```
comparable[equal,always] "210 zł/m² · 1 700 m² · gmina Skierniewice · 28.07.2026"
    {comparable_id:"cmp_hi",
     exclude_control:{comparable_id:"cmp_hi", label:"nie pasuje"}}
```

Remaining sorted: `[96, 104, 112, 124, 138]`, n = 5, R-7 index = `4q`.

- median: index 2.0 → **112.00**
- p25: index 1.0 → **104.00**
- p75: index 3.0 → **124.00**
- `n = 5 ≥ 5` → `kind = "iqr"` still

The median moves 118 → 112, by exactly 6.00. That is the "does not move"
falsifier V51c names, made arithmetic.

### 8.4 The after tree

```
section[primary,always] "Sprawdzenie działki"                {subject_id:"subj_0001"}

    aggregate_block[primary,always] "Podobne oferty (przepływ, ostatnie 90 dni)"
        {component:"flow_aggregate_block", state:"normal", basis:"flow",
         flow_window_days:90, n:5, median:112.00,
         range:{low:104.00, high:124.00, kind:"iqr"}}
        flow_window_label[equal,always] "ostatnie 90 dni"
        value[equal,always]         "mediana 112 zł/m²"
        spread[equal,always]        "zakres międzykwartylowy 104–124"
        sample_size[equal,always]   "n = 5"
        price_type_label[equal,always] "cena ofertowa"
        price_kind_label[equal,always] "oferta"
        provenance[equal,expander] "Źródło i metoda"

    comparable_set[primary,always] "Podobne oferty — 5"      {n:5, excluded:("cmp_hi",)}
        comparable[equal,always] "96 zł/m² · 4 100 m² · gmina Skierniewice · 21.05.2026"   {comparable_id:"cmp_01"}
        comparable[equal,always] "104 zł/m² · 3 600 m² · gmina Skierniewice · 02.06.2026"  {comparable_id:"cmp_02"}
        comparable[equal,always] "112 zł/m² · 2 800 m² · gmina Skierniewice · 12.06.2026"  {comparable_id:"cmp_03"}
        comparable[equal,always] "124 zł/m² · 3 400 m² · gmina Skierniewice · 03.07.2026"  {comparable_id:"cmp_04"}
        comparable[equal,always] "138 zł/m² · 3 000 m² · gmina Skierniewice · 19.07.2026"  {comparable_id:"cmp_05"}
        value[equal,always] "wykluczono 1 ofertę — cofnij"   {field:"exclusions", excluded:("cmp_hi",)}

    verdict[secondary,expander] "WERDYKT"                    {expanded:False}
        value[equal,always] "Powyżej górnej granicy zakresu przepływu (104–124)"
        basis[equal,always] "Podstawa: 5 ofert, ta sama gmina, 1 600–4 800 m², ostatnie 90 dni"
```

Assertions on the pair:

```python
def test_excluding_a_comparable_recomputes_the_estimate():
    before = build_plot_check(COMP_SET_N6_CONSTRUCTED)
    after  = exclude(before_payload, "cmp_hi")
    b = component(before, "flow_aggregate_block"); a = component(after, "flow_aggregate_block")
    assert b.meta["n"] == 6 and a.meta["n"] == 5
    assert b.meta["median"] == Decimal("118.00")
    assert a.meta["median"] == Decimal("112.00")
    assert a.meta["range"] == {"low": Decimal("104.00"),
                               "high": Decimal("124.00"), "kind": "iqr"}
    assert one(nodes_by_role(a, "value")).text == "mediana 112 zł/m²"
    assert one(nodes_by_role(a, "spread")).text == "zakres międzykwartylowy 104–124"
    assert one(nodes_by_role(a, "sample_size")).text == "n = 5"

def test_recomputed_estimate_still_obeys_u1():
    assert_u1(after)          # §3.1's four assertions, re-run on the new tree

def test_exclusion_never_mutates_the_underlying_listing_or_aggregate():
    assert gmina_aggregate_after == gmina_aggregate_before
    assert listing_row("cmp_hi").excluded is None      # no column was written
```

### 8.5 The log record written

One row per exclusion, in `exclusion_log`:

```json
{
  "exclusion_id": "exc_000001",
  "subject_id": "subj_0001",
  "comparable_id": "cmp_hi",
  "excluded_at": "2026-08-08T11:04:22+02:00",
  "session_id": "sess_7f3a",
  "action": "exclude",
  "estimate_before": {
    "median": "118.00", "low": "106.00", "high": "134.50",
    "n": 6, "range_kind": "iqr"
  },
  "estimate_after": {
    "median": "112.00", "low": "104.00", "high": "124.00",
    "n": 5, "range_kind": "iqr"
  },
  "method_version": "cmp-2026.08.1",
  "comparable_attributes": {
    "road_access": "public_main",
    "area_m2": 1700,
    "price_per_m2": "210.00",
    "buildability": "unknown"
  }
}
```

```python
def test_exclusion_is_logged_with_subject_comparable_and_change(log):
    row = one(log.rows)
    assert row["subject_id"] == "subj_0001" and row["comparable_id"] == "cmp_hi"
    assert row["estimate_before"]["median"] == "118.00"
    assert row["estimate_after"]["median"]  == "112.00"
    assert row["estimate_before"]["n"] == 6 and row["estimate_after"]["n"] == 5
    assert row["method_version"] == "cmp-2026.08.1"
```

Undo writes a second row with `"action": "restore"` and the before/after pair
reversed; `test_exclusion_is_reversible_and_restores_the_original_estimate`
asserts the restored tree equals the §8.2 tree exactly, and that the log has two
rows.

`comparable_attributes` is what makes V51c(b) possible — the report groups on it
without re-reading the listing table, so a later listing edit cannot rewrite
history.

### 8.6 Crossing the threshold into the out-of-depth notice (U11)

The user excludes three: `cmp_hi` (210), `cmp_01` (96), `cmp_05` (138).
Remaining sorted: `[104, 112, 124]`, n = 3.

- median: R-7 index `2·0.5 = 1.0` → **112.00**
- `n = 3 < thin_n_threshold (5)` → `kind = "min_max"`, low **104.00**, high **124.00**
- `n = 3 < out_of_depth_min_comparables (4)` → the notice leads

```
section[primary,always] "Sprawdzenie działki"                {subject_id:"subj_0001"}

    out_of_depth_notice[primary,always]
        "za mało danych, żeby ocenić — to jest orientacja, nie wycena"   {tone:"warning"}

    aggregate_block[secondary,always] "Podobne oferty (przepływ, ostatnie 90 dni)"
        {component:"flow_aggregate_block", state:"thin", basis:"flow",
         flow_window_days:90, n:3, median:112.00,
         range:{low:104.00, high:124.00, kind:"min_max"}}
        flow_window_label[equal,always] "ostatnie 90 dni"
        value[equal,always]         "mediana 112 zł/m²"
        spread[equal,always]        "zakres 104–124"
        sample_size[equal,always]   "n = 3"
        price_type_label[equal,always] "cena ofertowa"
        price_kind_label[equal,always] "oferta"
        uncertainty_note[equal,always] "Mało podobnych ofert — wynik orientacyjny"
        provenance[equal,expander] "Źródło i metoda"

    comparable_set[secondary,always] "Podobne oferty — 3"    {n:3, excluded:("cmp_hi","cmp_01","cmp_05")}
        comparable[equal,always] "104 zł/m² · 3 600 m² · gmina Skierniewice · 02.06.2026"  {comparable_id:"cmp_02"}
        comparable[equal,always] "112 zł/m² · 2 800 m² · gmina Skierniewice · 12.06.2026"  {comparable_id:"cmp_03"}
        comparable[equal,always] "124 zł/m² · 3 400 m² · gmina Skierniewice · 03.07.2026"  {comparable_id:"cmp_04"}
        value[equal,always] "wykluczono 3 oferty — cofnij"   {field:"exclusions"}

    verdict[secondary,expander] "WERDYKT"                    {expanded:False}
        value[equal,always] "Powyżej górnej granicy zakresu przepływu (104–124)"
        basis[equal,always] "Podstawa: 3 oferty, ta sama gmina, 1 600–4 800 m², ostatnie 90 dni"
```

Three things changed at once, and each is a separate assertion:

```python
def test_excluding_down_to_the_threshold_switches_to_the_out_of_depth_notice():
    t = exclude_all(payload, ["cmp_hi", "cmp_01", "cmp_05"])
    first = next(walk_children(t))
    assert first.role == "out_of_depth_notice"
    assert first.text == "za mało danych, żeby ocenić — to jest orientacja, nie wycena"
    assert component(t, "flow_aggregate_block").prominence == "secondary"
    assert all(v.prominence != "primary" for v in nodes_by_role(t, "verdict"))
    assert one(nodes_by_role(t, "spread")).text == "zakres 104–124"   # min_max, not IQR
    assert one(nodes_by_role(t, "uncertainty_note")).text == \
        "Mało podobnych ofert — wynik orientacyjny"
```

The two-exclusion intermediate is asserted separately, because it is the case that
distinguishes the two thresholds. Removing `cmp_hi` and `cmp_01` leaves
`[104, 112, 124, 138]`, n = 4:

- median: R-7 index `3 · 0.5 = 1.5` → `112 + 0.5·(124 − 112)` = **118.00**
- `n = 4 < 5` → `kind = "min_max"`, spread text `zakres 104–138`
- ratio `(138 − 104) / 118` = **0.288** < 0.60 → the tight-and-thin cell of §3.10,
  so the note reads `Mało podobnych ofert — wynik orientacyjny`
- `n = 4 ≥ out_of_depth_min_comparables (4)` → **no** `out_of_depth_notice`

`test_two_exclusions_do_not_yet_trigger_the_notice` pins exactly that: the
interface gets less confident in steps, and the step where it admits defeat is a
config value, not a feeling.

`test_excluding_every_comparable_renders_the_too_few_comparables_absence`:
excluding all six gives

```
    absence[equal,always] "Brak danych — za mało podobnych ofert"  {absence_reason:"too_few_comparables", tone:"warning"}
        basis[equal,always] "za mało podobnych ofert, żeby porównać"
```

with no `verdict`, no `aggregate_block`, no crash, and no empty band.

### 8.7 The exclusion report (V51c(b))

`report_exclusions(log)` over a log where five of six exclusions carry
`road_access == "public_main"`:

```
table_row[equal,always] "droga dojazdowa: droga gminna lub powiatowa — 5 z 6 wykluczeń (83%)"
    {attribute:"road_access", value:"public_main", count:5, total:6, share:0.83}
    basis[equal,always] "sprawdź regułę wyboru podobnych ofert: dopasowanie po dojeździe"
```

```python
def test_exclusion_report_groups_by_attribute(log_of_six):
    row = one(report_exclusions(log_of_six).rows)
    assert row.meta["attribute"] == "road_access"
    assert row.meta["count"] == 5 and row.meta["total"] == 6
    assert row.text == "droga dojazdowa: droga gminna lub powiatowa — 5 z 6 wykluczeń (83%)"

def test_exclusion_report_is_silent_below_the_pattern_threshold(log_of_one):
    assert report_exclusions(log_of_one).rows == ()

def test_exclusion_report_names_the_selection_rule_it_implicates(log_of_six):
    assert one(report_exclusions(log_of_six).rows).children[0].text == \
        "sprawdź regułę wyboru podobnych ofert: dopasowanie po dojeździe"
```

Pattern threshold: `min_exclusions_for_pattern = 3` and `share ≥ 0.60`, both from
config. One exclusion is noise. The third test is what closes V51c's named
failure — "a pattern of exclusions never feeding back" — with an artefact rather
than an intention.

Note the report text uses `droga dojazdowa`, the protected term, not `dojazd`
alone; the terminology lint of §6 covers the report module too.

---

## 9. The map and table cases (item 12)

`MAP_MODEL_TWO_RINGS` covers six gminas, one per treatment.

| gmina | state | `fill` | `pattern` | `legend_key` | label text |
|---|---|---|---|---|---|
| Skierniewice | normal | `#3182bd` | `none` | `bucket_4` | `gmina Skierniewice · n = 23` |
| Nowy Kawęczyn | thin | `#c6dbef` | `hatch` | `thin` | `gmina Nowy Kawęczyn · n = 3` |
| Maków | not_yet_crawled | `#e8e8e8` | `dots` | `not_yet_crawled` | `gmina Maków · jeszcze nie zebraliśmy — sprawdź później` |
| Godzianów | no_listings | `#ffffff` | `none` | `no_listings` | `gmina Godzianów · brak ofert w tej gminie` |
| Elbląg | out_of_scope | `#f5f5f5` | `diagonal_stripe` | `out_of_scope` | `gmina Elbląg · poza zasięgiem narzędzia` |
| Lipce Reymontowskie | too_few_comparables | `#d9d9d9` | `cross_hatch` | `too_few_comparables` | `gmina Lipce Reymontowskie · za mało podobnych ofert, żeby porównać` |

```python
TREATMENTS = ("thin","not_yet_crawled","no_listings","out_of_scope","too_few_comparables")

def test_the_four_absence_reasons_and_thin_have_pairwise_distinct_treatments(model):
    triples = [ (f.meta["fill"], f.meta["pattern"], f.meta["legend_key"])
                for f in features_for(model, TREATMENTS) ]
    assert len(set(triples)) == 5

def test_gmina_below_n5_renders_hatched_and_still_coloured(model):
    f = feature(model, "Nowy Kawęczyn")
    assert f.meta["pattern"] == "hatch"
    assert f.meta["fill"] is not None            # rule 7: the colour is not withheld

def test_every_gmina_label_carries_n_inline(model):
    for f in nodes_by_role(model, "map_feature"):
        assert re.match(r"^.+ · n = \d+$", f.text) or f.meta.get("absence_reason")
```

Legend, always present, never in a sidebar expander:

```
selector[primary,always] "cena ofertowa · oferta"      {price_type:"offering", price_kind:"asking"}
legend[primary,always]   "cena ofertowa · oferta · przepływ, ostatnie 90 dni"
    legend[equal,always] "mało ofert (n < 5) — kolor słabo poparty"   {legend_key:"thin"}
    legend[equal,always] "jeszcze nie zebraliśmy"                     {legend_key:"not_yet_crawled"}
    legend[equal,always] "brak ofert"                                 {legend_key:"no_listings"}
    legend[equal,always] "poza zasięgiem narzędzia"                   {legend_key:"out_of_scope"}
    legend[equal,always] "za mało podobnych ofert"                    {legend_key:"too_few_comparables"}
```

`test_map_refuses_features_spanning_price_types` — a model built from features
where one carries `price_type = "sales"` raises `MixedPriceTypeError`.
`test_map_and_table_agree_for_every_gmina` — for every gmina,
`bucket_of(feature.meta["fill"]) == bucket_of(table_row.meta["median"])`.

Gmina table row, all four series with their own qualifiers:

```
table_row[equal,always] "gmina Skierniewice"
    aggregate_block[equal,always] "Podobne oferty (przepływ, ostatnie 90 dni)"
        value "mediana 118 zł/m²" · spread "zakres międzykwartylowy 96–141" · sample_size "n = 23"
        price_type_label "cena ofertowa" · price_kind_label "oferta" · basis "stan na 01.08.2026"
    aggregate_block[equal,always] "Podobne oferty (stan, wszystkie aktywne)"
        value "mediana 127 zł/m²" · spread "zakres międzykwartylowy 99–168" · sample_size "n = 61"
    aggregate_block[equal,always] "Ceny transakcyjne · GUS 2025Q4"
        value "średnia 104 zł/m²" · spread "zakres niedostępny — GUS publikuje tylko średnią" · sample_size "n = 41"
        basis "poziom powiatu, dane kwartalne"
    aggregate_block[equal,always] "Typowa działka 3 000 m² pod zabudowę"
        value "≈ 354 000 zł" · spread "zakres 288 000–423 000" · sample_size "n = 23"
        basis "wyliczone z mediany podobnych ofert, nie zaobserwowana cena"
```

`test_gminas_with_no_data_still_appear_as_rows` asserts all six gminas of
`MAP_MODEL_TWO_RINGS` produce a `table_row`, the four absent ones carrying their
`absence` node — a table that drops them makes coverage look complete.

---

## 10. Open items this detail pass surfaced

Flagged rather than assumed, per [`CLAUDE.md`](../../../CLAUDE.md) rule 3. Each
blocks the step named.

| # | Item | Proposal | Blocks |
|---|---|---|---|
| **OPEN-S1** | `21` §2.1's mockup puts the collapsed verdict above the evidence; U14 and spec §5.14 put the comparable set first | Amend the `21` §2.1 sketch; U14 wins | step 10 |
| **OPEN-S2** | `06-surface` §8.3 cites `12-glossary.md` §4 for the protected-term list; `12` has no §4 and the list is in `09` §4 | Add `## Protected terms` to `12`, point both documents at it | step 17 |
| **OPEN-S3** | D65's `price_kind` enum is `{asking, auction_start, tender}`, all `price_type = 'offering'`. A **sales** price has no legal kind, so U2 cannot be satisfied for the GUS block | Extend the enum with `transaction`, legal only with `price_type = 'sales'`; Polish label `transakcja` | steps 5, 6 |
| **OPEN-S4** | GUS publishes a mean with no spread. U1 requires a `spread` node; `render_aggregate_block` raises `BareAggregateError` without a range | Add `range.kind = "unavailable"` with `low`/`high` `None` and the explicit text `zakres niedostępny — GUS publikuje tylko średnią`. Structure preserved, honesty preserved | steps 4, 8 |
| **OPEN-S5** | `Role` has no neutral container, so the screen root and the plot-check header have no legal role | Add `"section"` and `"header"` to `Role`; both are covered by `test_adapter_handles_every_role_in_the_role_enum` | step 1 |
| **OPEN-S6** | The render absence reason `no_listings` has no counterpart in `14` §2.3, so `test_absence_reason_enum_matches_the_api_contract` cannot pass as written | Add `no_listings` to the API contract's reason list (it is a real, distinct fact — U7 exists because of it) | step 7 |
| **OPEN-S7** | `06-surface` §5.1's spread wording (`zakres międzykwartylowy`) differs from `21` §2.1's mockup (`zakres` with n = 23) | Spec §5.1 wins; amend the `21` sketch | step 4 |
| **O10** (existing) | Portals' `robots.txt` unreachable | — | §7.1 case 5 |

---

## 11. Coverage of the pass-1 sequence

Every step of `06-surface.md` §3 has its literal cases here.

| Step | Detailed in |
|---|---|
| 1 contract | §1 |
| 2 architecture | §3.4 (AST scan), §7.1 (no network) |
| 3 formatting | §5 |
| 4 U1 + sweep | §3.1, §2.5 |
| 5 U2 | §3.2 |
| 6 U3, U4 | §3.3, §3.4 |
| 7 U6, U7 | §3.6, §3.7, §4.2 |
| 8 five states | §4 |
| 9 U8, U9 | §3.8, §3.9, §5.6 |
| 10 U5, U14 | §3.5, §3.14 |
| 11 U10, U11 | §3.10, §3.11 |
| 12 U13 | §3.13 |
| 13 U12 | §3.12 |
| 14 URL paste | §7 |
| 15 exclusion | §8 |
| 16 map, table | §9 |
| 17 terminology lint | §6 |
| 18 sweeps, properties | §3 (every dishonest fixture), §2.4 |
