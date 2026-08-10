"""The errors this package raises instead of guessing.

Every message names the file and the next action. A badge that names the wrong
act is worse than no badge, so each error here stops a render rather than
softening it.
"""

from __future__ import annotations

from dzialki.config.errors import ConfigError


class LegalError(Exception):
    """The purchase-restriction layer refuses to answer."""


class RegisterClassTableError(ConfigError):
    """``config/register_classes.yml`` is absent, malformed, or incomplete.

    A table that half loads is worse than one that does not load. A missing row
    reads as "no regime", and no regime renders as no badge.
    """


class UnknownRegisterClass(KeyError, LegalError):
    """No row in the table carries this symbol.

    Deliberately not a lookup that returns ``None``. A caller who forgets to
    check ``None`` treats an unrecognised symbol as an unrestricted plot, which
    is the failure V61 exists to prevent.
    """


class CitationRecordError(ConfigError):
    """``config/legal_citations.yml`` is absent, malformed, or incomplete."""


class BadgeCopyUnratified(CitationRecordError):
    """The regime's act title and pre-emption holder are not ratified.

    The record holds the two names, and nobody has confirmed them. Serving them
    would put a real act and a real authority on the screen, both possibly the
    wrong ones for the land in front of the reader.
    """


class ThresholdCopyUnwritten(LegalError):
    """A threshold claim is verified, and no document states how to render it.

    Two wrong answers sit either side of this error. Dropping the claim hides a
    fact the owner has just checked. Writing a sentence here invents legal copy
    nobody ratified. The badge refuses and names the claim.
    """
