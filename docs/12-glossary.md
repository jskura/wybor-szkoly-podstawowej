# Glossary

Polish domain terms, their meaning, and the English identifier used in code and
database columns. Polish stays in the UI (D15); English identifiers stay in code.
Where a term has a tempting but wrong translation, that is called out — those are
where bugs come from.

Decision: D34.

---

## Prices

| Polish | Code identifier | Meaning |
|---|---|---|
| cena ofertowa | `price_type = 'offering'` | Asking price in a listing. **Not** a market price — an ask |
| cena transakcyjna | `price_type = 'sales'` | Price recorded in a notarial deed. The actual sale |
| cena za m² | `price_per_m2` | Price divided by area. The comparison unit throughout |
| widełki / zakres | `range`, `low`/`high` | The range every estimate is expressed as (D32) |

Never translate *cena ofertowa* as "market price" or *cena transakcyjna* as
"price" unqualified. Rule 6 exists because these get conflated.

## Land and property

| Polish | Code identifier | Meaning |
|---|---|---|
| działka | `plot` / `parcel` | A plot. **`parcel`** = the cadastral unit in the register; **`plot`** = the thing being sold. They usually coincide but not always — one sale can span several parcels |
| działka budowlana | `land_building` | Plot where building is permitted |
| działka rolna | `land_agricultural` | Farmland |
| działka rekreacyjna | `land_recreational` | Leisure plot; building rights limited |
| działka leśna | `land_forest_other` | Woodland |
| numer działki ewidencyjnej | `parcel_identifier` | Cadastral identifier, e.g. `146509_8.0201.12/3` |
| obręb ewidencyjny | `obreb` / `precinct` | Cadastral precinct; the sub-gmina unit RCN often reports to |
| powierzchnia | `area_m2` | Area. Beware: adverts use *ar* (100 m²) and *hektar* (10 000 m²) — see `06` §3.2 |
| ar | — | 100 m². "12 arów" = 1200 m² |
| hektar | — | 10 000 m² |
| klasa gruntu | `soil_class` | Soil quality class. Classes I–III are protected and hard to rezone |

## Planning and buildability

| Polish | Code identifier | Meaning |
|---|---|---|
| plan ogólny | `plan_type = 'plan_ogolny'` | The general plan, mandatory per gmina under the 2023 reform; replaced *studium* |
| MPZP (miejscowy plan zagospodarowania przestrzennego) | `plan_type = 'mpzp'` | Local zoning plan. Binding, parcel-level |
| warunki zabudowy ("WZ-ka") | `conditional` | Planning conditions issued where no MPZP exists. A route to building, not a guarantee |
| przeznaczenie | `designation` | What the plan permits on this land |
| wypis i wyrys | — | The official extract from the plan. **The binding document** — our data is informational only (PRD §3) |
| Rejestr Urbanistyczny | — | The Urban Registry, live since 2026-07-01 |
| brak danych planistycznych | `buildability = 'unknown'` | No plan data. A terminal state — never inferred (FR-17) |

`zoning_claim` (what the advert says) and `buildability` (what planning data says)
are **different columns and never reconciled** — see `06` §1.

## Infrastructure and access

| Polish | Code identifier | Meaning |
|---|---|---|
| media | `utilities` | Utilities collectively: prąd, woda, gaz, kanalizacja |
| prąd | `utilities.electricity` | Electricity |
| woda / wodociąg | `utilities.water` | Water / mains water |
| kanalizacja | `utilities.sewage = 'mains'` | Mains sewerage |
| szambo | `utilities.sewage = 'septic'` | Septic tank |
| droga dojazdowa | `road_access` | Access road |
| droga gminna / powiatowa | `road_access = 'public_*'` | Public road — materially better than an easement |
| służebność przejazdu | `road_access = 'easement'` | Right of way over someone else's land |
| w granicy / w drodze | `'at_boundary'` | Utilities at the boundary, not on the plot. Different cost — see `06` §3.1 |

## Administrative

| Polish | Code identifier | Meaning |
|---|---|---|
| województwo | `voivodeship` | Region. łódzkie, mazowieckie, warmińsko-mazurskie |
| powiat | `powiat` | County |
| gmina | `gmina` | Municipality. **The primary aggregation unit** |
| miasto na prawach powiatu | — | City with county rights, e.g. Elbląg — both a gmina and a powiat |
| TERYT | `teryt` | Official territorial code. Always used instead of names — names are ambiguous |
| sołectwo / wieś | `locality` | Village |

Gmina **Skierniewice** (rural, contains Budy Grabskie) is a different unit from the
**city** of Skierniewice. Using names rather than TERYT codes will eventually merge
them — see `07` §4.

## Sources

| Term | Meaning |
|---|---|
| RCN / RCiWN | Property price and value register — actual transaction prices |
| GUS / BDL | Statistics office / its Local Data Bank API |
| GUGiK | Head office of geodesy and cartography |
| EGiB | Land and building register — the cadastre |
| ULDK | Parcel location service; parcel identifier → geometry |
| PRG | National register of boundaries |

## Product terms

| Term | Meaning |
|---|---|
| comparable set | The plots an estimate is built from (`05` §3) |
| widening step | How far the search had to widen to find comparables. Displayed, because it qualifies the estimate |
| mix-adjusted | Reweighted to a fixed basket so composition change does not masquerade as price change (`05` §7) |
| plot cluster | One real plot advertised several times, collapsed (FR-13) |
| location precision | How well we know where a listing is (`07` §1). Gates what it may be used for |
| method_version | The valuation method that produced a logged prediction (`05` §9) |


## Protected terms (D99)

The terminology lint checks UI strings against this list. These terms are never
loosely translated and never replaced with a synonym. This section is the only
home for the list; other documents point here.

`cena ofertowa` · `cena transakcyjna` · `działka` · `plan ogólny` · `MPZP` ·
`wypis i wyrys` · `media` · `droga dojazdowa` · `zakres międzykwartylowy` ·
`warunki zabudowy` · `służebność przejazdu` · `klasa gruntu`

The last two joined the list in D118. Both have a tempting loose rendering:
`służebność przejazdu` reads wrongly as *dojazd*, and `klasa gruntu` as
*jakość gleby*. The first is a legal instrument, the second drives the farmland
pre-emption rule, so neither survives a synonym.
