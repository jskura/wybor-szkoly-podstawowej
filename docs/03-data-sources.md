# Data Sources — findings and open items

Companion to the [PRD](./02-prd.md) §7. Everything below was checked in
August 2026; anything marked **verify** still needs a hands-on spike before we
commit a milestone to it.

---

## Official / open data (authoritative layer)

### GUS BDL — Bank Danych Lokalnych API
- REST API returning XML/JSON, covering Poland → voivodeship → powiat → gmina and
  NUTS units. Portal: `https://api.stat.gov.pl/Home/BdlApi`.
- Relevant series: average market transaction prices of **land designated for
  residential construction**, at national/voivodeship/powiat level, split
  urban/rural; plus agricultural land prices (*ceny w rolnictwie* subgroup).
- **Role for us:** the pre-history baseline and the sanity check. If our scraped
  median for a powiat is 3× the GUS transaction average, our pipeline is wrong.
- Cadence: quarterly, with a lag. Coarse (powiat, not gmina).
- **verify:** exact variable IDs for the land-price series; how deep the history
  goes; whether the rural/urban split is populated for all target powiats.

### RCN / RCiWN — Rejestr Cen Nieruchomości
- The register of actual notarial transaction prices — plots, houses, flats,
  primary and secondary market.
- 2026 status: opened up for the whole country, extended beyond big-city flats to
  **plots and houses nationwide**. Data is published in **GML** covering
  transactions from 2021-07-31 onward. Aggregated views exist at powiat and
  voivodeship level. Aggregator portal: `rciwn.pl`; also surfaced through
  geoportal-based front-ends.
- The EU open-data directive designates the property price register as
  high-value data that should be free, machine-readable and API-served — but in
  practice access has been **paid, non-uniform across counties, and
  bureaucratic**, with inconsistent formats.
- **Role for us:** ground truth for J5 (asking-vs-transaction spread) and J7.
- **verify (start early — this is the M4 critical path):** which of our 66
  powiats publish GML directly vs. require a request; per-county fees; whether
  parcel identifiers are included (determines whether we can join transactions to
  parcels, or only to precincts).

### GUGiK ULDK — Usługa Lokalizacji Działek Katastralnych
- Docs: `https://uldk.gugik.gov.pl/opis.html`. Locate a parcel by its identifier,
  by precinct name + number, or by X/Y coordinates. Returns geometry (WKB), default
  CRS **EPSG:2180** (PUWG 1992). A QGIS plugin exists, which is a useful reference
  implementation for the request shapes.
- **Role for us:** FR-9/FR-10 — turning a listing that mentions a parcel number
  into a real geometry, and reverse-locating a map pin to the parcel under it.
- Free, no key, well documented. Lowest-risk enrichment we have.

### EGiB via county WFS
- ~295 counties expose parcel and building geometry over **WFS**; KIEG is the
  aggregate WMS that composes the cadastral map from ~380 county servers.
  Endpoints are listed in the spatial data registry on `geoportal.gov.pl`.
- **Role for us:** bulk parcel attributes (registry area, land-use and soil class)
  where ULDK's per-parcel calls would be too many.
- **verify:** coverage and quality specifically for łódzkie + mazowieckie counties
  — this is exactly where "uneven per county" bites.

### Rejestr Urbanistyczny + plan ogólny (zoning)
- The Urban Registry went live **2026-07-01** as part of the planning reform that
  replaced *studium* with the **plan ogólny**. It comprises: spatial planning acts
  (with spatial data), a repository of planning documents, and **e-Wyrys POG** in
  mObywatel for extracts from the general plan.
- Local plans must be produced against a **unified spatial data model (UML)**,
  which is what makes systematic ingestion possible at all. GUGiK maintains a
  national register of adopted general plans, reachable via geoportal or API.
- Rollout reality: a transition period ran to **2026-09-30** for gminas to load
  data, and the deadline for the extended spatial-data scope for *local* plans and
  Urban Registry data runs to **2029-07-01**.
- **Role for us:** FR-11, the buildability tier — the single most valuable
  enrichment for a land buyer, and the one competitors don't have.
- **Consequence for the plan:** coverage will be partial for the life of v1. Hence
  the explicit `unknown` tier and the rule that unknown is never treated as
  buildable. Worth tracking per-gmina plan-ogólny availability as its own coverage
  metric — it also tells us which gminas to prioritise.

### Boundaries, constraints, routing
- **PRG** (GUGiK) — administrative boundaries for voivodeship/powiat/gmina, plus
  TERYT codes. Stable, free.
- **Flood hazard maps** (Wody Polskie / ISOK), **protected areas** (GDOŚ), soil
  class from EGiB — risk badges (FR-12).
- **OSM extract** of both voivodeships + self-hosted OSRM/Valhalla for drive times
  (FR-13). Precompute per gmina seat; no per-request routing needed in v1.

---

## ⚠ Unverified gate — read before any connector work (O10, audit C1)

**Nobody has checked whether the candidate portals' `robots.txt` permits crawling
listing pages.** I planned the entire offering-price layer — and therefore most of
the product — on the assumption that it does, and I could not verify it: the
network egress proxy in my environment blocks both domains (403 on CONNECT).

This is **day-one work in [`18-v0-scope.md`](./18-v0-scope.md) §6, item 0** and it gates
everything downstream:

- If listing paths are **allowed**: proceed as planned.
- If **disallowed**: the offering-price layer is off the table under our own rules
  (FR-2, §Operating rules below). What remains is GUS BDL and RCN — powiat-level,
  quarterly, historical. That is a genuinely different and much smaller product,
  and the decision to accept it or stop belongs to the owner, not to the plan.
- If **partially allowed** (e.g. detail pages disallowed, search pages permitted):
  the list-page-first strategy (D40) may still work for prices, but attribute
  extraction would lose its source. Scope that case explicitly rather than
  assuming around it.

Checking takes minutes from any ordinary browser. Nothing else in the offering-price
path should be built first.

## Off-portal supply (D47) — new, and possibly the more valuable half

Both anchor rings are rural, and rural land often never reaches a consumer portal.
Three source families, none of which were in the plan before batch 11:

### Bailiff and bankruptcy auctions (O16)

Court bailiffs (*licytacje komornicze*) and bankruptcy trustees (*syndyk*) sell
land through public auctions, with statutory starting prices set as a fraction of a
surveyor's valuation. This is where materially under-market land appears.

- Access models differ per source — a central e-auction service, individual bailiff
  office sites, and *Monitor Sądowy i Gospodarczy* for bankruptcy estates. Which
  to target is **O16**.
- Prices here are **not comparable to asking prices** without care: an auction
  starting price is a legally-derived floor, not an ask. It needs its own
  price type or at minimum an explicit marker, otherwise it will drag every median
  down and look like a market shift. **This is a rule-5 question** — see the open
  item at the end of this section.
- Auction listings carry the parcel identifier far more often than portal adverts
  do, which makes them the easiest to resolve to real geometry.

### KOWR — state agricultural land

KOWR publishes sales and tender notices for state-owned agricultural land. Relevant
given the sizes in play (D48), and it comes with the purchase-law questions in
[`19-legal-and-feasibility.md`](./19-legal-and-feasibility.md) §2 attached.

### Gmina BIP sale notices

Gminas publish their own land sale notices in their public information bulletins.
Genuinely off-portal supply, but roughly 50 gminas across the two rings, each with
its own bulletin layout — the highest-effort source by a wide margin (4–6 days),
and the reason it is sequenced last (`18` §6 item 13).

### Three different kinds of number — settled

Auction starting prices, KOWR tender prices and portal asking prices are not
comparable. **FR-64** gives each a distinct `price_kind`, and no aggregate may span
kinds (V46). Settled before the auction connector is written, because the first
aggregate that blended them would be quietly wrong.

## Listing portals (high-frequency layer)

The big two consumer portals (Otodom, OLX) carry the volume for building plots;
agricultural land trades much more off-portal, so rural coverage will be
structurally thinner — worth checking land-specific boards and gmina/ANR notice
boards before assuming the big two are enough.

Legal position, summarized from Polish practitioner sources: scraping publicly
available data is **in principle lawful**, conditional on GDPR compliance for
personal data, the site's terms, `robots.txt`, and proportionality. Risk rises
sharply when extraction is **mass, systematic and continuous**, when a substantial
part of a protected database is taken, when terms explicitly forbid it, when the
data feeds a **commercial competing product**, or when personal data is involved.
`robots.txt` itself is a voluntary standard, not a legal instrument — but ignoring
it is the clearest evidence of bad faith, so we follow it.

**Our operating rules** (also in PRD §12):
1. Read `robots.txt` per host before writing any connector; honour it.
2. Single-digit requests per minute per host, off-peak, with backoff.
3. No authentication bypass, no anti-bot circumvention, no CAPTCHA solving.
4. Store price/area/attributes/location only. Seller name and phone → salted hash
   for dedup, never a readable field.
5. Never republish listing text or images; link back to the source.
6. Keep v1 private and non-commercial. Publishing or monetizing triggers a fresh
   legal review — it is a different risk profile, not a bigger version of this one.

**Considered and rejected:** commercial data providers sell structured feeds, which
would remove most of the above risk. Ruled out by **D2** — zero budget for data.

---

## Source priority for M1

Build in this order — earliest value per unit of risk:

1. PRG boundaries + TERYT (no risk, unblocks everything)
2. GUS BDL baseline (no risk, gives a working map before any scraping exists)
3. ULDK (no risk, unlocks J2's spine)
4. One listing portal, land only, both voivodeships (the volume)
5. Plan ogólny / Urban Registry (highest value, highest uncertainty — spike early
   even if the connector lands in M3)
6. RCN (start the access process in M1, land the connector in M4)
7. Second listing portal (redundancy against risk #1)

---

## Sources consulted

- [Portal API GUS — API BDL](https://api.stat.gov.pl/Home/BdlApi)
- [Ceny w rolnictwie — Bank Danych Lokalnych](https://bdl.stat.gov.pl/bdl/metadane/podgrupy/186)
- [rciwn.pl — Rejestr Cen Nieruchomości](https://www.rciwn.pl/)
- [Ceny transakcyjne nieruchomości już jawne. RCN otwarty dla wszystkich — rp.pl](https://www.rp.pl/nieruchomosci/art43810951-ceny-transakcyjne-nieruchomosci-juz-jawne-rcn-otwarty-dla-wszystkich)
- [Rejestr Cen i Wartości Nieruchomości — OnGeo blog](https://blog.ongeo.pl/ongeo-ceny-rejestr-cen-i-wartosci-nieruchomosci)
- [Dokumentacja API ULDK — GUGiK](https://uldk.gugik.gov.pl/opis.html)
- [Usługi WFS dla danych EGiB — GUGiK](https://www.gov.pl/web/gugik/uslugi-wfs-dla-danych-ewidencji-gruntow-i-budynkow)
- [Land and building register (EGiB) — geoportal.gov.pl](https://www.geoportal.gov.pl/en/data/land-and-building-register-egib/)
- [Rusza Rejestr Urbanistyczny — MFiPR](https://www.kpo.gov.pl/strony/aktualnosci/rusza-rejestr-urbanistyczny/)
- [Rejestr Urbanistyczny — nowe terminy publikacji danych (Geo-System)](https://geo-system.blogspot.com/2026/07/rejestr-urbanistyczny-nowe-terminy.html)
- [Tak ma wyglądać Rejestr Urbanistyczny — Gazeta Prawna](https://www.gazetaprawna.pl/urzad/administracja/artykuly/11231567,tak-ma-wygladac-rejestr-urbanistyczny-ministerstwo-pokazalo-szczegoly.html)
- [Web scraping a prawo — Kancelaria Prawnik IT](https://www.prawnikit.com.pl/web-scraping-a-prawo-kiedy-mozna-skanowac-cudze-strony-a-kiedy-zaczyna-sie-ryzyko/)
- [Web scraping — czym jest? Czy jest legalny? — Kancelaria RPMS](https://rpms.pl/web-scraping-czym-jest-czy-jest-legalny/)
