"""Purchase restrictions: the farmland badge and the forest badge.

Two acts, two pre-emption holders, two badges (D106). The register class picks
one regime, and the regime picks the act, the holder and the copy. Neither badge
ever renders on the other's land (V63).

Nothing here decides what the law says. The register class table and the citation
record carry that, and both refuse to serve content nobody has checked. The
forest badge is blocked today, because `19` §2a marks all three of its legal
claims unverified (D122).
"""

from __future__ import annotations

from .badge import (
    Alarm,
    Badge,
    PurchaseRestrictionRenderer,
    PurchaseSection,
)
from .citations import (
    BADGE_REGIMES,
    CLAIM_KINDS,
    CitationRecord,
    Claim,
    RegimeCitation,
    load_citations,
)
from .errors import (
    BadgeCopyUnratified,
    CitationRecordError,
    LegalError,
    RegisterClassTableError,
    ThresholdCopyUnwritten,
    UnknownRegisterClass,
)
from .prompt import ReverificationSession
from .regime import (
    REGIMES,
    RegisterClass,
    RegisterClassTable,
    load_register_classes,
)
from .wording import (
    BADGE_NOTARY_LINE,
    NEVER_VERIFIED,
    NOTARY_LINE,
    NOTARY_LINE_PREFIX,
    PREEMPTION_TEMPLATES,
    RESTRICTION_TEMPLATE,
    REVERIFY_PROMPT_TEMPLATE,
    TITLE_TEMPLATES,
    UNKNOWN_CLASS_STATEMENT,
    UNRECOGNISED_CLASS_ALARM,
)

__all__ = [
    "BADGE_NOTARY_LINE",
    "BADGE_REGIMES",
    "CLAIM_KINDS",
    "NEVER_VERIFIED",
    "NOTARY_LINE",
    "NOTARY_LINE_PREFIX",
    "PREEMPTION_TEMPLATES",
    "REGIMES",
    "RESTRICTION_TEMPLATE",
    "REVERIFY_PROMPT_TEMPLATE",
    "TITLE_TEMPLATES",
    "UNKNOWN_CLASS_STATEMENT",
    "UNRECOGNISED_CLASS_ALARM",
    "Alarm",
    "Badge",
    "BadgeCopyUnratified",
    "CitationRecord",
    "CitationRecordError",
    "Claim",
    "LegalError",
    "PurchaseRestrictionRenderer",
    "PurchaseSection",
    "RegimeCitation",
    "RegisterClass",
    "RegisterClassTable",
    "RegisterClassTableError",
    "ReverificationSession",
    "ThresholdCopyUnwritten",
    "UnknownRegisterClass",
    "load_citations",
    "load_register_classes",
]
