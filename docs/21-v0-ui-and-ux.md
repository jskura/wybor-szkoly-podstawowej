# v0 UI & UX

What you actually look at. [`09-ux-specification.md`](./09-ux-specification.md)
describes the eventual full interface; this describes what v0 ships — a **Streamlit
app** with a plot check, a **map**, and a **coverage view** — and the interaction
design that makes them honest.

Requirements: FR-71, FR-67, FR-25. Validation: V59, V51c, V45, V62.

---

## 1. What the interface is for

One question (D52): **is this plot's price fair?** Everything else is supporting
evidence. So the design principle is not "show the data" but:

> **Answer first, evidence immediately under it, provenance one step away.**

A dashboard that makes you assemble the answer yourself has failed, even if every
number on it is correct.

**Settled (D59–D63):** a **Streamlit app**, not a notebook. **Choropleth plus
gmina table**. **Paste a listing URL** to check a plot. The agree/disagree control
is **withdrawn** — see §7, which is the most important section here and worth
reading before the surfaces it constrains.

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
│  Podobne oferty (przepływ, ostatnie 90 dni)             │
│    mediana 118 · zakres międzykwartylowy 96–141 · n = 23│
│  Podobne oferty (stan, wszystkie aktywne)               │
│    mediana 127 · zakres międzykwartylowy 99–168 · n = 61│
│                                                          │
│  Ceny transakcyjne · powiat skierniewicki · GUS 2025Q4  │
│    średnia 104 · transakcja · n = 312                   │
│    zakres: brak — GUS nie podaje rozrzutu               │
│    poziom powiatu, dane kwartalne                       │
│                                                          │
│  ⚠ Nie sprawdzamy planu — nie wiemy, czy można budować  │
├─────────────────────────────────────────────────────────┤
│  ▸ WERDYKT                                    [rozwiń]  │   ← last, and shut (D98)
└─────────────────────────────────────────────────────────┘
```

The **verdict is collapsed by default** so the evidence is read before the
conclusion. With tier-C judgement unavailable (D63) this no longer captures an
unbiased price impression — it simply stops the headline number from being the only
thing anyone reads.

Expanding shows the verdict phrased **relative to the range**, never as a
percentage off a midpoint:

```
▾ WERDYKT
  Powyżej górnej granicy zakresu przepływu (96–141)
  Podstawa: 23 oferty, ta sama gmina, 1 600–4 800 m², ostatnie 90 dni
  [ pokaż wszystkie 23 ]        każda z nich: [ nie pasuje ]
```

Instead of an agree/disagree control on the verdict (withdrawn, D63), each
comparable carries a **"nie pasuje"** control. You may not be able to price a plot,
but you can see that a comparable sits on a main road while yours is in forest.
That is a layperson-answerable judgement, and because the comparable set *is* the
estimate, it improves the answer directly. See §7.

### 2.2 The area view — the map

A choropleth of the two rings, one metric at a time, with a hard rule: **the
price-type and price-kind selector is always visible**, because a map that silently
switches between asking and transaction prices is the most dangerous screen in the
product.

- Gminas below n=5 render **faded, not solid** (D113). The colour still appears —
  rule 7 forbids hiding. Fading can read as "less of something" rather than "less
  certain", so the `n` on the label carries the meaning.
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
| U1 | No aggregate renders without `n` **and** its range, at equal prominence | Rule 7. Not a tooltip, not on hover |
| U1a | Where the source publishes no spread (`range_kind = 'unavailable'`, D69), the interface says so in words. It never omits the range line | A missing range line reads as "no uncertainty". GUS is the case that forces this |
| U2 | Every price shows **type** (ofertowa/transakcyjna) and **kind** (asking/licytacja/przetarg) | FR-64. An auction start price next to an asking price without labels is actively misleading |
| U3 | Flow and stock always both shown, always labelled, flow first | D56, FR-67 |
| U4 | The flow window length appears next to every flow figure | O27/V62 — "mediana przepływu" means nothing without "ostatnie 90 dni" |
| U5 | Verdict collapsed until expanded | Evidence before conclusion (§7) |
| U6 | `unknown` renders as explicit text, never as blank or dash | A blank reads as "nothing to worry about" |
| U7 | Absence states are distinguished: not-yet-crawled / no-listings / out-of-scope / too-few-comparables | Each implies a different action |
| U8 | Stale data shows its age **on the number**, not in a corner | FR-8/V8 |
| U9 | Every number is one click from source + as-of + method | Rule 7 |

## 4. What v0's UI deliberately does not have

No accounts, no saved searches, no alerts, no comparison board, no trends charts,
no what-if calculator, no mobile layout. All are specified in `09` and `13` for
later; none earns its place in a first version for one person.

**One consequence worth naming:** without trends, v0 cannot show you whether prices
are moving. Given a six-month horizon (D45) and no accrued history, that is the
right trade — but it means v0 answers "is this fair *now*", never "is now a good
time".

## 5. Look and feel

Polish throughout (D15), using [`12-glossary.md`](./12-glossary.md) terms exactly.
Polish number formatting: space thousands separator, comma decimal, `zł/m²`. Dates
`DD.MM.YYYY`.

Visual restraint is deliberate. The product's credibility rests on numbers looking
carefully handled rather than attractively presented, and a plain interface sets
honest expectations about what this is — especially given §7.

## 6. Effort

Streamlit app with URL paste and comparable exclusion ≈ 3 days; choropleth plus
gmina table ≈ 1 day. Reflected in [`18`](./18-v0-scope.md) §6 items 11–12.

## 7. Designing for a user who cannot check the answer (D63)

You told me you will not be able to price plots yourself. That is the single most
important input to this design, and it inverts an assumption every earlier document
made — that the tool was a *second* opinion, checked against your own.

It is the only opinion. So the interface has to do work that would otherwise be
done by your scepticism.

### 7.1 Rules that follow

| # | Rule | Why |
|---|---|---|
| U10 | **Uncertainty is stated in words, not only in numbers.** "Zakres szeroki — mało podobnych ofert" alongside `n=4`, because a range is only legible to someone who already has a prior | You cannot supply the missing judgement |
| U11 | **The tool must volunteer when it is out of its depth.** Below a comparable threshold it leads with *"za mało danych, żeby ocenić — to jest orientacja, nie wycena"* rather than presenting a confident-looking band | Silence would read as confidence |
| U12 | **Never a single unqualified number**, anywhere, in any export or screenshot | A figure separated from its caveats is what gets acted on |
| U13 | **Show what would change the answer** — "gdyby ta działka miała plan miejscowy, porównania byłyby inne" — so the limits are concrete rather than abstract | Turns an unknown into a question you can take to the gmina |
| U14 | **The comparable set is shown before the verdict**, not after — and §2.1's layout follows this order | If the comparables look wrong to you, the verdict is wrong, and that judgement you *can* make |

### 7.2 The honest disclosure

Somewhere you will actually read it — not a footer:

> *Ten tool porównuje ceny ofertowe. Nie jest wyceną rzeczoznawcy i nie sprawdza,
> czy na działce można budować. Przy małej liczbie porównań wynik jest orientacyjny.*

This matters more than usual precisely because you cannot catch our errors.
Overstating confidence to a user who can verify is a nuisance; to a user who
cannot, it is the whole failure mode.

### 7.3 What we lose, and cannot recover

Tier C is gone (`20` §2). There is no longer any check on the *level* of our
estimates except the GUS sales cross-check — which is powiat-level and quarterly.
If our entire corpus were biased upward, LOOCV would score perfectly and nothing
else would notice except a coarse comparison against GUS.

**That makes the GUS cross-check (V16) the most important single check in the
system**, and it was previously treated as a sanity test. It is promoted.
