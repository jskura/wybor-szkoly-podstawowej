# Taxonomy & attribute extraction

How inconsistent advert text becomes the structured attributes the valuation
depends on. This is the largest error-prone surface in the pipeline: everything in
[`05-analytics-methodology.md`](./05-analytics-methodology.md) assumes
`buildability`, `area` and `utilities` are correct, and none of them arrive clean.

Decision: D34. Validation: [`04-validation.md`](./04-validation.md) §V25–V28.

---

## 1. Asset class taxonomy

Our canonical classes (PRD §6.2), in priority order:

| Class | Polish | Definition |
|---|---|---|
| `land_building` | działka budowlana | Land whose planning status permits residential building |
| `land_recreational` | działka rekreacyjna | Leisure/seasonal use; building rights limited or absent |
| `land_agricultural` | działka rolna | Farmland; *grunt rolny* in the register |
| `land_forest_other` | działka leśna / inna | Woodland and everything else |
| `house` | dom | Single-family, secondary market |
| `flat` | mieszkanie | Secondary market |

**The category trap.** A portal category saying *"działka budowlana"* is a
**seller's claim**, not a planning fact. Sellers routinely label farmland as
"budowlana z warunkami" or "budowlana w planie". So:

- The portal category populates `zoning_claim` — what the advert says.
- `buildability` (FR-16) is populated **only** from planning data.
- The two are separate columns and are never reconciled into one.
- Where they disagree, the plot page shows both: *"ogłoszenie: budowlana ·
  dane planistyczne: rolna"*. That disagreement is a genuine risk flag, not noise.

This distinction is the single most important rule in this document. Collapsing
`zoning_claim` into `buildability` would let seller marketing set the price
expectation, which inverts the product's purpose.

## 2. Mapping portal categories

Each connector ships a `category_map` from source category strings to our classes,
plus a `zoning_claim` string preserved verbatim. Rules:

1. The map is **explicit and exhaustive** — an unmapped source category raises an
   alarm (FR-6) rather than defaulting to a class.
2. Never guess a class from the title. A title reading "piękna działka pod dom"
   with source category "rolna" stays `land_agricultural`.
3. Category maps are versioned; a portal renaming a category is schema drift and
   must alarm.
4. Where a portal has no usable category, the class is `unknown` and the listing is
   excluded from class-stratified aggregates rather than assigned a guess.

## 3. Attribute extraction from free text

Attributes needed by the valuation that adverts state inconsistently or not at all:

| Attribute | Values | Typical advert phrasing |
|---|---|---|
| `utilities.electricity` | present / at boundary / absent / unknown | "prąd na działce", "prąd w drodze", "media w granicy" |
| `utilities.water` | present / at boundary / absent / unknown | "woda miejska", "studnia", "wodociąg w drodze" |
| `utilities.gas` | present / at boundary / absent / unknown | "gaz w ulicy" |
| `utilities.sewage` | mains / septic / none / unknown | "kanalizacja", "szambo", "przydomowa oczyszczalnia" |
| `road_access` | public paved / public unpaved / easement / none / unknown | "droga asfaltowa", "dojazd drogą gminną", "służebność przejazdu" |
| `area_m2` | number | "1200 m²", "12 arów", "0,12 ha" |
| `shape_note` | free text | "kształt prostokąta", "wąska i długa" |
| `mpzp_mention` | yes / no | "objęta MPZP", "brak planu" |

### 3.1 Extraction approach

**Rule-based first, deliberately.** A curated Polish phrase-pattern set per
attribute, with:

- Polish inflection handled explicitly (*prąd / prądu / prądem*; *droga /
  drogi / drogą*).
- **Negation detection** — "brak prądu", "bez dostępu do drogi", "media w
  planach" must not become `present`. Negation is the dominant failure mode and
  gets its own test suite.
- **Proximity qualifiers** — "w drodze", "w granicy", "przy działce", "300 m od"
  distinguish *at boundary* from *present*, which materially changes cost to build.
- Confidence per extraction: `high` (explicit phrase), `low` (inferred), `unknown`
  (absent). Anything below `high` is displayed as uncertain.

**Why not an LLM or classifier first:** rules are inspectable, testable against a
labelled set, and free. If the labelled evaluation (§4) shows rules plateauing
below acceptable accuracy, a model becomes justified — measured against the same
labelled set, and adopted only if it wins. Same governance as the hedonic model
in `05` §2.

**`unknown` is never coerced.** An advert that does not mention gas yields
`unknown`, not `absent`. Absence of evidence is stored as absence of evidence —
the same principle as FR-17's terminal `unknown` for buildability.

### 3.2 Unit normalisation

Polish adverts mix units freely and this silently corrupts price per m²:

- `ar` = 100 m², `hektar` = 10 000 m², and "12a" means 1200 m².
- A decimal comma is standard: "0,12 ha".
- Some adverts state area in the title and a different area in the body; the
  parcel register is authoritative where available (FR-15), then the structured
  field, then the body, then the title — in that order, with the source recorded.

An area conversion error produces a plausible-looking price per m² that is wrong
by 100×, which is why V10's band checks and the hectare/ares fixtures exist.

## 4. Labelled evaluation set

Extraction quality is measured, not assumed.

- **200 adverts**, sampled across both anchor rings and all four land classes,
  hand-labelled once for every attribute in §3, committed with personal fields
  scrubbed.
- Every extractor is scored on this set: precision and recall per attribute,
  reported per attribute rather than averaged — an extractor that is excellent on
  electricity and useless on road access must not hide behind a mean.
- **Negation subset**: at least 30 of the 200 chosen specifically because they
  contain negations or proximity qualifiers.
- Re-labelled and expanded whenever a portal changes materially.

Targets, to be ratified once the first run reports actuals: precision ≥ 0.95 on
`present` claims (a false "utilities present" misleads about real money), recall
secondary — missing an attribute yields `unknown`, which is honest, whereas a
false positive is not.

## 5. Housing attributes

Deferred until housing is surfaced (J6), but the same rules apply, and the
attribute list needs writing before any housing extractor is built:
build year, floor area, plot area, construction technology, energy class,
condition (*do remontu* / *stan deweloperski* / *pod klucz*). Listed here so the
gap is explicit rather than discovered at M5.
