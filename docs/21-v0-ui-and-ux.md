# v0 UI & UX

What you actually look at. [`09-ux-specification.md`](./09-ux-specification.md)
describes the eventual full interface; this describes the two surfaces v0 ships —
a **notebook** and **one map** — and the interaction design that makes them honest.

Requirements: FR-71, FR-67, FR-25. Validation: V59, V51b, V45, V62.

---

## 1. What the interface is for

One question (D52): **is this plot's price fair?** Everything else is supporting
evidence. So the design principle is not "show the data" but:

> **Answer first, evidence immediately under it, provenance one step away.**

A dashboard that makes you assemble the answer yourself has failed, even if every
number on it is correct.

## 2. Three surfaces, in priority order

### 2.1 The plot check — the primary surface

You have a listing or a plot in mind. You want a verdict.

**Input:** paste a listing URL, or type area + gmina, or click a point on the map.

**Output, in this order:**

```
┌─────────────────────────────────────────────────────────┐
│  3 200 m² · gmina Skierniewice · 142 zł/m²              │
│  cena ofertowa                                          │
├─────────────────────────────────────────────────────────┤
│  ▸ WERDYKT                                    [rozwiń]  │   ← collapsed (V51b)
├─────────────────────────────────────────────────────────┤
│  Podobne oferty (przepływ, ostatnie 90 dni)             │
│    mediana 118 · zakres 96–141 · n = 23                 │
│  Podobne oferty (stan, wszystkie aktywne)               │
│    mediana 127 · zakres 99–168 · n = 61                 │
│                                                          │
│  Ceny transakcyjne · powiat skierniewicki · GUS 2025Q4  │
│    średnia 104 · poziom powiatu, dane kwartalne         │
│                                                          │
│  ⚠ Nie sprawdzamy planu — nie wiemy, czy można budować  │
└─────────────────────────────────────────────────────────┘
```

The **verdict is collapsed by default**. That is not decoration: it is V51b's
mechanism for getting your unbiased impression before you see the tool's answer,
which is what replaced pre-registration (D57). You look at the evidence, form a
view, then expand.

Expanding shows the verdict phrased **relative to the range**, never as a
percentage off a midpoint:

```
▾ WERDYKT
  Powyżej górnej granicy zakresu przepływu (96–141)
  Podstawa: 23 oferty, ta sama gmina, 1 600–4 800 m², ostatnie 90 dni
  [ pokaż wszystkie 23 ]   [ zgadzam się / nie zgadzam się / nie wiem ]
```

The agree/disagree control is one click and feeds V51b. No numbers to write, no
homework — that was the point of D57.

### 2.2 The area view — the map

A choropleth of the two rings, one metric at a time, with a hard rule: **the
price-type and price-kind selector is always visible**, because a map that silently
switches between asking and transaction prices is the most dangerous screen in the
product.

- Gminas below n=5 render **hatched, not solid** (O13). The colour still appears —
  rule 6 forbids hiding — but the hatch says "thin" without needing to be read.
- "No listings at all" is visually distinct from "few listings". These are
  different facts and must not share a treatment.
- Every gmina label carries `n` inline.
- Clicking a gmina opens its panel: flow and stock medians with ranges and counts,
  the GUS sales figure with its as-of date, and the standard-plot benchmark (O7) —
  *"3 000 m² buildable here ≈ X zł"* — which is the one number that compares
  cleanly across areas.

### 2.3 The coverage view — where the tool admits its limits

Per gmina: listings collected, last crawl, source breakdown (portal / KOWR /
auction / BIP), and — crucially — **which gminas are uncovered and why** (V55).

This is not an afterthought screen. Given D54 (a number you know is wrong destroys
trust), the fastest way to lose you is a gmina that looks cheap because we failed
to parse its bulletin. The coverage view is what makes that visible instead.

## 3. Interaction rules

These are testable (V59) and each exists because of a specific way the interface
could mislead.

| # | Rule | Why |
|---|---|---|
| U1 | No aggregate renders without `n` **and** its range, at equal prominence | Rule 6. Not a tooltip, not on hover |
| U2 | Every price shows **type** (ofertowa/transakcyjna) and **kind** (asking/licytacja/przetarg) | FR-64. An auction start price next to an asking price without labels is actively misleading |
| U3 | Flow and stock always both shown, always labelled, flow first | D56, FR-67 |
| U4 | The flow window length appears next to every flow figure | O27/V62 — "mediana przepływu" means nothing without "ostatnie 90 dni" |
| U5 | Verdict collapsed until expanded | V51b |
| U6 | `unknown` renders as explicit text, never as blank or dash | A blank reads as "nothing to worry about" |
| U7 | Absence states are distinguished: not-yet-crawled / no-listings / out-of-scope / too-few-comparables | Each implies a different action |
| U8 | Stale data shows its age **on the number**, not in a corner | FR-8/V8 |
| U9 | Every number is one click from source + as-of + method | Rule 6 |

## 4. What v0's UI deliberately does not have

No accounts, no saved searches, no alerts, no comparison board, no trends charts,
no what-if calculator, no mobile layout. All are specified in `09` and `13` for
later; none earns its place in a local notebook for one person.

**One consequence worth naming:** without trends, v0 cannot show you whether prices
are moving. Given a six-month horizon (D45) and no accrued history, that is the
right trade — but it means v0 answers "is this fair *now*", never "is now a good
time".

## 5. Look and feel

Polish throughout (D15), using [`12-glossary.md`](./12-glossary.md) terms exactly.
Polish number formatting: space thousands separator, comma decimal, `zł/m²`. Dates
`DD.MM.YYYY`.

Visual restraint is deliberate. The product's credibility rests on numbers looking
carefully handled rather than attractively presented — and a notebook that looks
like a notebook sets honest expectations about what it is.

## 6. Open UI questions

| # | Question |
|---|---|
| **O28** | **Notebook vs small web app.** A notebook is ~1 day and zero infrastructure; a minimal Streamlit app is ~2–3 days, is far easier to use repeatedly, and is what you would show a friend. Given D1 (shared with a few people), Streamlit may be worth the extra days |
| **O29** | **Map necessity.** With only two 25 km rings — maybe 50 gminas — a sorted table may beat a choropleth entirely. The map costs ~1 day; a table costs hours and may read better at this scale |
| **O30** | Should the plot check accept a **pasted listing URL** (needs per-portal parsing of an arbitrary page) or only manual entry of area + gmina? URL paste is much nicer and somewhat more work |
| **O31** | Does the **agree/disagree control** (V51b) belong in v0, or does it feel like homework despite being one click? It is the only human signal left after D57 |
