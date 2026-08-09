# Source access — what to do if `robots.txt` says no

O10 has been treated as a binary gate that either opens or kills the offering-price
layer. That framing is too crude. This document sets out what `robots.txt` actually
is, what genuinely changes because this is a private tool, and the routes available
in each outcome.

Nothing here is legal advice.

---

## 1. What `robots.txt` is, precisely

It is a **voluntary convention**, published for automated crawlers. It is not law,
in Poland or the EU, and disregarding it is not by itself an offence.

Three things it *is*, which is why it still matters:

1. **Evidence of intent.** If a dispute ever arose, "we read the file that said no
   and proceeded anyway" is the worst possible fact.
2. **Usually a proxy for the Terms of Service**, which *are* contractual, and which
   bind you whether or not a robot reads them.
3. **Our own rule.** FR-2 says we honour it. That is a choice we made, not an
   external constraint — and we can revisit our own choice deliberately.

So the honest position: this is mostly about **terms of service and the database
right**, and `robots.txt` is the visible signal of both.

## 2. What genuinely changes because it's private

Your framing is legally relevant, not just sentiment. Three real factors:

| Factor | Effect |
|---|---|
| **Volume** | The *sui generis* database right is infringed by extracting a **substantial part** of a database. v0 covers two 25 km rings — likely hundreds to a few thousand listings out of a portal's hundreds of thousands. That is a thin slice by any reading |
| **No competing product** | The aggravating factor in every practitioner summary is commercial reuse that competes with the source. Absent here |
| **Personal use** | GDPR has a household exemption. **But** D1 shares this with a few friends, which weakens it — and we store seller contacts only as salted hashes anyway, so little personal data is involved |

What does **not** change: terms of service still apply to you as a user, and
"private" is not a defence against a contractual term you agreed to.

**Net:** the realistic risk for a personal tool at this scale is low. It is not
zero, and it is mostly reputational and contractual rather than criminal.

## 3. The gate probably opens anyway

Worth saying before designing around a problem we may not have. Portals *want*
their listings in Google. A typical portal `robots.txt` allows listing detail pages
and disallows things like `/api/`, user profiles, and parameterised search URLs.

**But note the asymmetry, which matters for our design:** the pages most likely to
be **disallowed** are exactly the **search and list pages** that the list-page-first
strategy (D40) depends on. Detail pages are the ones most likely to be allowed.

So a "partial" outcome would not be a minor inconvenience — it would invert the
crawl strategy. Which brings us to the route the plan had missed entirely.

## 4. Route A — `sitemap.xml`, the sanctioned discovery mechanism

**A sitemap is published *for* crawlers.** It is an explicit invitation listing the
URLs a site wants fetched, and it is usually referenced from `robots.txt` itself.

If search pages are disallowed but detail pages are allowed, the sitemap replaces
the list-page pass entirely:

- Discovery comes from the sitemap rather than from scraping search results.
- Sitemaps carry `lastmod`, so change detection — the whole point of the
  list-page-first strategy — works *better* than paging through search results.
- It is unambiguously permitted, because it exists to be read by machines.

This is the first thing to try in the partial case, and arguably worth using even
in the fully-allowed case. It is cheaper and more polite than crawling search
pages, and it makes the D40 budget arithmetic easier rather than harder.

## 5. Route B — you browse, the tool parses

If a portal disallows automated fetching outright, there is a clean separation:

**`robots.txt` governs robots. It does not govern you.**

You may look at listings in your browser as any user does. A tool that parses pages
*your browser already fetched* is not crawling — no automated agent requested
anything.

Two shapes:

| Shape | How | Effort |
|---|---|---|
| **Save-and-parse** | You browse normally, save pages (or use "save as"), drop them in a watched folder; the pipeline parses them | Low to build, tedious to use |
| **Browser extension** | A local extension extracts structured data from listing pages as you visit them, posting to your local database | ~2–3 days, pleasant to use |

At v0's scale this is genuinely viable. You are looking at a few hundred relevant
plots across two rings, and you would be browsing many of them anyway.

The trade-off is real and worth stating: **no daily automated refresh**, so price
history accrues only where you happen to look. Given D45 — buying within six
months, history demoted to insurance — that costs less than it would have before.

## 6. Route C — lean on sources with no such constraint

Already half the plan, and it becomes the centre of gravity if portals close:

- **GUS BDL** — a public API, built to be consumed.
- **KOWR, bailiff auctions, gmina BIP** — public-sector publishers whose statutory
  purpose *is* dissemination. Notices are published to be read.
- **ULDK, EGiB, PRG, the Urban Registry** — open data.

Worth remembering that D47 put the off-portal sources in scope precisely because
rural land often never reaches a portal. If portals close, the plan loses less than
it would have before batch 11.

## 7. Route D — just ask

An email asking permission for personal, non-commercial research use costs nothing
and takes ten minutes. A written "yes" removes every question in this document.
Portals do sometimes grant this, particularly for small-scale academic or personal
use with no republication.

Low probability of reply, but the expected value is high because the downside is
zero.

## 8. Route E — a licensed feed

Ruled out by D2 (zero budget), and mentioned only for completeness: commercial
providers sell structured feeds, which removes the question entirely.

## 9. What I will not do

Stated plainly so it does not have to be re-litigated:

- **Rotating user agents, IP pools or proxies to evade blocking.** This is
  circumvention of an access control, not a grey area.
- **Defeating CAPTCHAs or anti-bot measures.**
- **Impersonating a browser to avoid detection** while an automated agent does the
  fetching.
- **Reading `robots.txt` and ignoring it while the code claims to honour it.**

The first three are how a low-risk personal project becomes a genuinely
indefensible one. The fourth is worse in a different way: it would make our own
documentation lie, and every honesty rule in this project would be worth nothing.

**If we decide to crawl in spite of a disallow, that is a decision to record
openly** — FR-2 amended, the reasoning written down — not something to bury behind
a user-agent string.

## 10. Recommended sequence

1. **Read the files** (10 minutes, needs you — the proxy blocks me). Record them
   verbatim with the date in `docs/evidence/`.
2. **If listing pages are allowed** — proceed as planned, and still prefer the
   sitemap for discovery (§4).
3. **If search pages are disallowed but detail pages are not** — sitemap discovery
   plus detail fetches. Materially better than the current D40 plan.
4. **If everything is disallowed** — Route B (browser-assisted) for that portal,
   Route C for everything else, Route D in parallel because it is free.
5. **Only if all of the above fail** does the question "do we crawl anyway?" arise,
   and it is yours to answer with the risk written down (§2), not mine to assume.

## 11. What this changes in the plan

- The `robots.txt` gate is **no longer binary**. Four outcomes, each with a route.
- **Sitemap discovery is added** as the preferred mechanism regardless of outcome
  (new FR needed — see O32).
- The **connector contract is unaffected**: `fetch → parse → emit` with a pure
  `parse` means Route B reuses the same parsers. A browser extension changes only
  where bytes come from, which is precisely why that contract was worth having.
