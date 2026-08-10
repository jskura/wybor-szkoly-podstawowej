"""The two purchase-restriction badges.

The register class picks the regime, and the regime picks everything else. The
badge helper takes a regime and never a class symbol, so it cannot re-derive the
regime and therefore cannot re-derive it wrongly (F16).

Three rules the section obeys, all from `19` §2.2 and §2a.2:

* a class in the `none` regime produces no badge and no sentence about
  acquisition at all — absence of a badge is not a statement;
* an unknown class produces no badge and no reassurance, and says so;
* a symbol the table does not carry additionally alarms, because a missing value
  is a known state and an unrecognised one is a surprise (FR-49).

The badge is never a filter. It carries no query and this package imports no
database module, so a badged plot cannot be dropped from a result set (D51).
"""

from __future__ import annotations

import dataclasses
import datetime

from dzialki.render import Formatter

from .citations import CitationRecord, RegimeCitation
from .errors import LegalError, ThresholdCopyUnwritten
from .prompt import ReverificationSession
from .regime import RegisterClassTable
from .wording import (
    NOTARY_LINE,
    PREEMPTION_TEMPLATES,
    RESTRICTION_TEMPLATE,
    TITLE_TEMPLATES,
    UNKNOWN_CLASS_STATEMENT,
    UNRECOGNISED_CLASS_ALARM,
)

NO_BADGE_REGIME = "none"


@dataclasses.dataclass(frozen=True)
class Alarm:
    """An operator signal. It never reaches the page."""

    code: str
    symbol: str


@dataclasses.dataclass(frozen=True)
class Badge:
    """Four lines, and where the area figure came from (rule 7, V28)."""

    regime: str
    lines: tuple[str, ...]
    area_m2: int
    area_source: str
    as_of: datetime.date
    degraded: bool


@dataclasses.dataclass(frozen=True)
class PurchaseSection:
    """What one plot page says about buying the land.

    Empty for a class in the `none` regime. That emptiness is deliberate: the
    page states a restriction or states that it does not know, and it never
    states that a plot is free of restrictions.
    """

    badge: Badge | None
    statement: str | None
    alarm: Alarm | None
    prompt: str | None

    @property
    def text(self) -> str:
        """Everything a reader sees, for the whole-page scans."""
        lines: list[str] = []
        if self.badge is not None:
            lines.extend(self.badge.lines)
        if self.statement is not None:
            lines.append(self.statement)
        if self.prompt is not None:
            lines.append(self.prompt)
        return "\n".join(lines)


class PurchaseRestrictionRenderer:
    """Builds the section for one plot."""

    def __init__(
        self,
        *,
        table: RegisterClassTable,
        citations: CitationRecord,
        formatter: Formatter,
    ) -> None:
        self._table = table
        self._citations = citations
        self._formatter = formatter

    def citation_for(self, regime: str) -> RegimeCitation:
        """The record entry for this regime, or a refusal.

        One seam, so a test can wire it to the wrong entry on purpose and prove
        the crossing scans are not vacuous.
        """
        return self._citations.for_regime(regime)

    def badge(
        self,
        *,
        regime: str,
        area_m2: int,
        area_source: str,
        as_of: datetime.date,
    ) -> Badge:
        """The badge for a regime. It never sees a class symbol."""
        if regime not in TITLE_TEMPLATES:
            raise LegalError(f"no badge copy exists for the regime {regime!r}")
        citation = self.citation_for(regime)
        verified = citation.verified_thresholds
        if verified:
            raise ThresholdCopyUnwritten(
                f"the claim {verified[0].claim_id!r} is verified and no document "
                "states the sentence that renders it. Write the copy in doc 19 "
                "and hash it in the test plan, then render it here."
            )
        lines = (
            TITLE_TEMPLATES[regime].format(area=self._formatter.format_int(area_m2)),
            RESTRICTION_TEMPLATE.format(act_title=citation.act_title),
            PREEMPTION_TEMPLATES[regime].format(holder=citation.preemption_holder),
            NOTARY_LINE,
        )
        return Badge(
            regime=regime,
            lines=lines,
            area_m2=area_m2,
            area_source=area_source,
            as_of=as_of,
            degraded=True,
        )

    def section(
        self,
        *,
        register_class: object,
        area_m2: int,
        area_source: str,
        as_of: datetime.date,
        advert_claim: str | None = None,
        session: ReverificationSession | None = None,
    ) -> PurchaseSection:
        """The section for one plot.

        ``advert_claim`` is accepted and ignored. The register decides, and the
        advert's word is not evidence (FR-48, V25). The argument exists so a
        caller cannot pass the advert's claim where the register class belongs.
        """
        del advert_claim

        if not isinstance(register_class, str) or register_class.strip() == "":
            return PurchaseSection(
                badge=None, statement=UNKNOWN_CLASS_STATEMENT, alarm=None, prompt=None
            )

        row = self._table.get(register_class)
        if row is None:
            return PurchaseSection(
                badge=None,
                statement=UNKNOWN_CLASS_STATEMENT,
                alarm=Alarm(code=UNRECOGNISED_CLASS_ALARM, symbol=register_class),
                prompt=None,
            )

        if row.regime == NO_BADGE_REGIME:
            return PurchaseSection(badge=None, statement=None, alarm=None, prompt=None)

        badge = self.badge(
            regime=row.regime,
            area_m2=area_m2,
            area_source=area_source,
            as_of=as_of,
        )
        prompt = (
            None
            if session is None
            else session.prompt_for(self.citation_for(row.regime))
        )
        return PurchaseSection(badge=badge, statement=None, alarm=None, prompt=prompt)
