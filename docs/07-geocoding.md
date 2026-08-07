# Geocoding & spatial resolution

How a listing becomes a location. Everything spatial downstream — gmina
aggregates, comparable sets, distance to forest, travel time — inherits whatever
error is introduced here, and geocoding fails *silently*: a plot placed in the
wrong gmina still produces a confident-looking number.

Decision: D34. Validation: [`04-validation.md`](./04-validation.md) §V29–V31.

---

## 1. Resolution ladder

For each listing, resolve to the most precise location available, stopping at the
first success. The step reached is stored as `location_precision` and is **never
discarded** — it determines what the observation may be used for (§3).

| Step | Method | Precision | `location_precision` |
|---|---|---|---|
| 1 | **Parcel identifier** in the advert text → GUGiK ULDK → true geometry | Exact parcel | `parcel` |
| 2 | Street address → geocoder → point | ~10–50 m | `address` |
| 3 | Portal-supplied map pin | Varies wildly (§2) | `pin` |
| 4 | Village/locality name → PRG locality centroid | ~500 m–2 km | `locality` |
| 5 | Gmina name only | Gmina | `gmina` |
| 6 | Nothing usable | — | `none` — quarantined |

Parcel identifiers follow the pattern `WWPPGG_R.XXXX.NNNN[/N]` (e.g.
`146509_8.0201.12/3`) and appear in a meaningful minority of adverts, especially
from surveyors and agencies. Extracting them is high-value: step 1 is the only
step that yields a true boundary rather than a point, which in turn unlocks parcel
area, land-use class, soil class and the nature distances.

## 2. The map-pin problem

Portal pins are the most common and most dangerous input:

- Many are **deliberately fuzzed** by the seller to prevent buyers going direct.
- Many are **placed at the locality centre**, not the plot.
- Some are **the agency's office**.

A pin is therefore treated as a *claim about approximate location*, not a
position. Practical consequences:

1. A pin never overrides a parcel geometry (step 1 wins, FR-14).
2. A pin near a gmina boundary is flagged: if the point lies within 500 m of a
   boundary, `boundary_risk = true`, because the gmina assignment — which drives
   the comparable set — may be wrong.
3. **Pin clustering detection**: many listings sharing a near-identical point is
   evidence of centroid-placement or an agency office, not a real cluster of
   plots. Detected as a data assertion; those points are demoted to `locality`
   precision rather than trusted as `pin`.

## 3. What each precision level may be used for

This table is the mechanism that stops imprecise data from silently contaminating
precise analysis.

| Use | `parcel` | `address` | `pin` | `locality` | `gmina` |
|---|:--:|:--:|:--:|:--:|:--:|
| Gmina-level aggregates | ✓ | ✓ | ✓ | ✓ | ✓ |
| Comparable set by radius | ✓ | ✓ | ✓ | — | — |
| Nature distances (forest, water, noise) | ✓ | ✓ | — | — | — |
| Travel time to anchors | ✓ | ✓ | ✓ | ✓ | — |
| Parcel attributes and zoning | ✓ | — | — | — | — |
| Displayed as a precise location on the map | ✓ | ✓ | — | — | — |

Distance-to-forest computed from a fuzzed pin is a fabricated number, so `pin` and
below are excluded from nature attributes entirely, and the plot page says *"brak
dokładnej lokalizacji"* rather than showing a distance it cannot support.

## 4. Gmina assignment

The gmina is the primary aggregation unit and must be right.

- Assignment is a PostGIS point-in-polygon against PRG boundaries, or a
  polygon-intersection where a parcel geometry exists.
- A parcel straddling a boundary is assigned by majority area, and flagged.
- Every assignment stores the TERYT code, never the gmina *name* — names are
  ambiguous (there are multiple gminas called Brzeziny, and gmina Skierniewice is
  distinct from the city of Skierniewice, which matters directly for anchor A).
- `boundary_risk` listings are included in aggregates but counted separately, so
  their contribution can be inspected if a gmina's median looks wrong.

## 5. Coordinate systems

- Storage: **EPSG:4326** for points, so everything interoperates.
- Distance and area computation: **EPSG:2180** (PUWG 1992), the Polish national
  grid — computing metres in degrees is a classic source of quietly wrong
  distances.
- ULDK returns EPSG:2180 by default; that is the native form and is reprojected
  once, on ingest, with the original retained.
- Every stored geometry carries its SRID explicitly. A geometry column without a
  declared SRID is a bug.

## 6. Geocoder choice

Free options only (D2): Nominatim (OSM) self-hosted on the VPS over a Poland
extract, avoiding public-instance rate limits and terms issues, with the national
address registry as a possible later improvement.

Self-hosting also makes geocoding **reproducible**: a public geocoder's answers
drift over time, so the same advert could resolve differently across runs and
silently move between gminas. The geocoder version is recorded alongside each
resolution.

## 7. Re-resolution policy

Geocoding improves — a parcel identifier may be extracted later, a geocoder
updated. Therefore:

- Resolutions are **versioned**, not overwritten: `listing_location` rows carry
  `resolved_at`, `method`, `precision`, `geocoder_version`.
- A better resolution supersedes an older one; the older row remains.
- Aggregates are recomputed from the current best resolution, and because
  `metric_unit_month` rows carry `as_of` (PRD §10 invariant 4), a recomputation is
  visible rather than a silent rewrite of history. See
  [`08-temporal-model.md`](./08-temporal-model.md) §4.
