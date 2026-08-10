"""The refusals of the render layer.

Every error here makes one dishonest rendering unrepresentable. A payload that
would produce a bare number does not produce a bare number with a warning; it
produces no tree at all. The caller must fix the payload.
"""

from __future__ import annotations


class RenderError(Exception):
    """Base class, so a caller can catch the whole layer."""


class InvalidNodeError(RenderError):
    """A role, prominence or disclosure outside the closed vocabulary."""


class UnknownMetaKeyError(RenderError):
    """A ``meta`` key outside the closed vocabulary.

    A private key name is how an unqualified figure would enter the tree
    unnoticed by every sweep.
    """


class BareAggregateError(RenderError):
    """An aggregate with no sample size or no range (U1)."""


class UnlabelledAggregateError(RenderError):
    """An aggregate with no basis, so the reader cannot tell flow from stock."""


class UnlabelledPriceError(RenderError):
    """A price with no type or no kind (U2, FR-64)."""


class IllegalPriceCombinationError(RenderError):
    """A price type and kind that D68 does not permit together."""


class MixedPriceKindError(RenderError):
    """One aggregate built from more than one price kind (F9)."""


class UnknownAbsenceReasonError(RenderError):
    """An absence reason outside the four the surface renders (U7)."""


class UnknownFieldError(RenderError):
    """An attribute with no written sentence of its own (U6, U13)."""


class GlossaryParseError(RenderError):
    """The glossary carries no readable protected-term list (D99)."""


class UnknownProtectedTermError(RenderError):
    """A protected term the lint has no forbidden renderings for (D99)."""
